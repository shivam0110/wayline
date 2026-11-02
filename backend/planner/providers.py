import json
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from django.core.cache import cache

from .routing import MILE, cumulative


class ProviderError(Exception):
    pass


def fetch(url, params, name):
    try:
        response = requests.get(url, params=params, timeout=(5, 25), headers={"User-Agent": "WaylineAssignment/1.0"})
        data = response.json()
    except (requests.RequestException, ValueError):
        raise ProviderError(f"{name} is unavailable or rate limited. Please try again shortly.") from None
    if isinstance(data, dict) and data.get("code") in ("NoRoute", "NoSegment", "NoTrips"):
        raise ValueError("No road route found between these locations.")
    if not response.ok:
        raise ProviderError(f"{name} is unavailable or rate limited. Please try again shortly.")
    return data


def geocode(query):
    key = "geocode:" + sha256(query.casefold().encode()).hexdigest()
    result = cache.get(key)
    if result is None:
        data = fetch("https://geocoding-api.open-meteo.com/v1/search", {"name": query, "count": 6, "language": "en", "format": "json"}, "Place search")
        result = [{"label": ", ".join(dict.fromkeys(str(p[k]) for k in ("name", "admin1", "country") if p.get(k))), "coordinate": [p["longitude"], p["latitude"]]} for p in data.get("results", [])]
        cache.set(key, result, 3600)
    return result


def decode_shape(encoded):
    values, number, shift = [], 0, 0
    for char in encoded:
        value = ord(char) - 63
        number |= (value & 31) << shift
        if value < 32:
            values.append(~(number >> 1) if number & 1 else number >> 1)
            number, shift = 0, 0
        else:
            shift += 5
    lat, lon, points = 0, 0, []
    for dy, dx in zip(values[::2], values[1::2]):
        lat, lon = lat + dy, lon + dx
        points.append([lon / 1e6, lat / 1e6])
    return points


def truck_route(trip):
    leg = trip["legs"][0]  # Exactly two input locations: one leg.
    points = decode_shape(leg["shape"])
    lengths = cumulative(points)
    seconds, elapsed = [0.0] * len(points), 0.0
    for maneuver in leg["maneuvers"]:
        a, b = maneuver["begin_shape_index"], maneuver["end_shape_index"]
        span = lengths[b] - lengths[a]
        for i in range(a, b + 1):
            seconds[i] = elapsed + maneuver["time"] * ((lengths[i] - lengths[a]) / span if span else 0)
        elapsed += maneuver["time"]
    if seconds[-1]:
        seconds = [value * trip["summary"]["time"] / seconds[-1] for value in seconds]
    return {"geometry": points, "distance_meters": trip["summary"]["length"] * MILE, "duration_seconds": trip["summary"]["time"], "vertex_seconds": seconds}


def routes(origin, destination, departure):
    key = "routes:" + ",".join(str(value) for point in (origin, destination) for value in point)
    cached = cache.get(key)
    if cached:
        return cached
    warnings = ["Travel times exclude live traffic, driver breaks and hours-of-service limits."]
    try:
        body = {"locations": [{"lon": p[0], "lat": p[1]} for p in (origin, destination)], "costing": "truck", "alternates": 2, "directions_options": {"units": "miles"}}
        data = fetch("https://valhalla1.openstreetmap.de/route", {"json": json.dumps(body, separators=(",", ":"))}, "Truck routing")
        result = [truck_route(item["trip"]) for item in [data, *data.get("alternates", [])]]
        warnings.append("Valhalla uses default truck dimensions and gross weight. Cargo weight applies only to weather risk rules.")
        response = result[:3], "Valhalla · truck", warnings
    except ProviderError:
        locations = ";".join(f"{p[0]},{p[1]}" for p in (origin, destination))
        data = fetch(f"https://router.project-osrm.org/route/v1/driving/{locations}", {"alternatives": "2", "overview": "full", "geometries": "geojson", "annotations": "duration,distance", "steps": "false"}, "Road routing")
        if data.get("code") != "Ok":
            raise ValueError("No road route found between these locations.")
        result = []
        for route in data.get("routes", [])[:3]:
            seconds = [0.0]
            for leg in route["legs"]:
                for duration in leg.get("annotation", {}).get("duration", []):
                    seconds.append(seconds[-1] + duration)
            result.append({"geometry": route["geometry"]["coordinates"], "distance_meters": route["distance"], "duration_seconds": route["duration"], "vertex_seconds": seconds})
        warnings.append("Truck routing is unavailable or this trip exceeds its limits. Showing standard road routes: truck restrictions are NOT checked.")
        response = result, "OSRM · standard roads", warnings
    cache.set(key, response, 600)
    return response


def forecasts(coordinates):
    """Cache per location; at most three concurrent batches of twenty locations."""
    day = datetime.now(timezone.utc).date().isoformat()
    locations = list(dict.fromkeys((round(p[0], 3), round(p[1], 3)) for p in coordinates))
    keys = {p: f"weather:{day}:{p[0]}:{p[1]}" for p in locations}
    cached = cache.get_many(keys.values())
    result = {p: cached[keys[p]] for p in locations if keys[p] in cached}
    missing = [p for p in locations if p not in result]

    def batch(points):
        try:
            data = fetch("https://api.open-meteo.com/v1/forecast", {"latitude": ",".join(str(p[1]) for p in points), "longitude": ",".join(str(p[0]) for p in points), "hourly": "wind_speed_10m,rain,showers,snowfall", "wind_speed_unit": "mph", "timezone": "GMT", "timeformat": "unixtime", "forecast_days": 7}, "Weather forecast")
            items = data if isinstance(data, list) else [data]
            if len(items) != len(points):
                return [(p, None) for p in points]
            return [(p, item.get("hourly")) for p, item in zip(points, items)]
        except ProviderError:
            return [(p, None) for p in points]

    if missing:
        with ThreadPoolExecutor(max_workers=3) as executor:
            for items in executor.map(batch, [missing[i:i + 20] for i in range(0, len(missing), 20)]):
                for point, hourly in items:
                    result[point] = hourly
                    if hourly:
                        cache.set(keys[point], hourly, 900)
    return [result.get((round(p[0], 3), round(p[1], 3))) for p in coordinates]
