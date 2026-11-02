import json
import math
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from . import providers
from .risk import classify, recommend, summarize
from .routing import MILE, corridor_grid, distance, sample_route
from .weather import at_time, iso


def endpoint(method):
    def decorate(fn):
        @csrf_exempt
        @wraps(fn)
        def wrapped(request):
            if request.method != method:
                return JsonResponse({"error": f"Use {method}."}, status=405)
            try:
                if method == "POST":
                    data = json.loads(request.body)
                    if not isinstance(data, dict):
                        raise ValueError("Expected a JSON object.")
                    return JsonResponse(fn(data))
                return JsonResponse(fn(request))
            except (ValueError, TypeError, KeyError, OverflowError) as error:
                return JsonResponse({"error": str(error) if isinstance(error, ValueError) else "Missing or invalid request fields."}, status=400)
            except providers.ProviderError as error:
                return JsonResponse({"error": str(error)}, status=502)
            except RequestDataTooBig:
                return JsonResponse({"error": "Request is too large. Shorten the route geometry."}, status=413)
        return wrapped
    return decorate


def coordinate(value):
    if not isinstance(value, list) or len(value) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value):
        raise ValueError("Select a valid origin and destination from the search results.")
    if not -180 <= value[0] <= 180 or not -75 <= value[1] <= 75:
        raise ValueError("Coordinates must be within ±180° longitude and ±75° latitude.")
    return value


@endpoint("GET")
def health(request):
    return {"status": "ok"}


@endpoint("GET")
def geocode(request):
    query = request.GET.get("q", "").strip()
    if not 2 <= len(query) <= 120:
        raise ValueError("Enter a city or place name between 2 and 120 characters.")
    return {"candidates": providers.geocode(query)}


@endpoint("POST")
def plan(data):
    origin, destination = coordinate(data["origin"]), coordinate(data["destination"])
    if distance(origin, destination) < 50:
        raise ValueError("Choose different locations at least 50 meters apart.")
    load = data["load_lb"]
    if isinstance(load, bool) or not isinstance(load, (int, float)) or not math.isfinite(load) or not 0 <= load <= 200000:
        raise ValueError("Cargo weight must be between 0 and 200,000 lb.")
    interval = data["interval_miles"]
    if isinstance(interval, bool) or interval not in (10, 25, 50):
        raise ValueError("Checkpoint spacing must be 10, 25 or 50 miles.")
    if not isinstance(data["departure"], str):
        raise ValueError("Departure must be an ISO timestamp with a timezone.")
    departure = datetime.fromisoformat(data["departure"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if departure.utcoffset() is None:
        raise ValueError("Departure must include a timezone.")
    departure = departure.astimezone(timezone.utc)
    if departure < now:
        raise ValueError("Choose a departure in the future.")
    if departure > now + timedelta(days=6):
        raise ValueError("Choose a departure within the next six days.")
    raw, provider, warnings = providers.routes(origin, destination, departure)
    if not raw:
        raise ValueError("No road routes are available for this trip.")
    unique = []
    for r in raw:
        if r["geometry"] not in [u["geometry"] for u in unique]:
            unique.append(r)
    if len(unique) < 3:
        warnings.append(f"The provider returned {len(unique)} distinct route{'s' if len(unique) != 1 else ''}; no alternatives were fabricated.")
    if any(r["distance_meters"] > 2500 * MILE for r in unique):
        raise ValueError("This demo supports road trips up to 2,500 miles. Choose a closer destination.")
    sampled = [sample_route(r, interval) for r in unique]
    all_checkpoints = [p for checkpoints, _ in sampled for p in checkpoints]
    if len(all_checkpoints) > 600:
        raise ValueError("Too many weather checkpoints. Increase spacing to 25 or 50 miles.")
    forecasts = iter(providers.forecasts([p["coordinate"] for p in all_checkpoints]))
    routes = []
    for i, (r, (checkpoints, segments)) in enumerate(zip(unique, sampled)):
        for p in checkpoints:
            timestamp = departure.timestamp() + p.pop("elapsed_seconds")
            weather = at_time(next(forecasts), timestamp)
            p.update(eta=iso(timestamp), weather=weather, risk=classify(weather, load))
        for segment, a, b in zip(segments, checkpoints, checkpoints[1:]):
            levels = [a["risk"]["level"], b["risk"]["level"]]
            segment["risk"] = None if None in levels else max(levels)
        # Keep the map/corridor payload bounded; checkpoint sampling uses the full road geometry.
        stride = max(1, math.ceil(len(r["geometry"]) / 4000))
        geometry = r["geometry"][::stride]
        if geometry[-1] != r["geometry"][-1]:
            geometry.append(r["geometry"][-1])
        routes.append({"id": f"route-{i + 1}", "name": f"Route {i + 1}", "geometry": geometry, "distance_miles": r["distance_meters"] / MILE, "duration_seconds": r["duration_seconds"], "arrival": checkpoints[-1]["eta"], "checkpoints": checkpoints, "segments": segments, **summarize(segments)})
    if any(r["unknown_miles"] for r in routes):
        warnings.append("Some arrival forecasts are unavailable or outside the forecast window. Those routes cannot be recommended.")
    return {"routes": routes, "recommendation_id": recommend(routes), "provider": provider, "warnings": warnings, "departure": departure.isoformat(), "generated_at": now.isoformat()}


@endpoint("POST")
def corridor_weather(data):
    geometries = data["routes"]
    if not isinstance(geometries, list) or not 1 <= len(geometries) <= 3 or any(not isinstance(r, list) or not 2 <= len(r) <= 4500 for r in geometries):
        raise ValueError("Provide one to three route geometries, with at most 4,500 vertices each.")
    for route in geometries:
        for point in route:
            coordinate(point)
    # Cap geographic work before external calls; only driveable local/regional corridors.
    if any(sum(distance(a, b) for a, b in zip(r, r[1:])) > 3000 * MILE for r in geometries):
        raise ValueError("This corridor exceeds the demo's trip limit.")
    cells, resolution = corridor_grid(geometries)
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).timestamp()
    timestamps = [base + i * 3600 for i in range(49)]
    for cell, hourly in zip(cells, providers.forecasts([c["coordinate"] for c in cells])):
        cell["values"] = [at_time(hourly, t) for t in timestamps]
    return {"cells": cells, "timestamps": [iso(t) for t in timestamps], "resolution_miles": resolution, "buffer_miles": 25, "units": {"wind": "mph", "rain": "in/hr", "snow": "in/hr"}, "unavailable_cells": sum(not any(c["values"]) for c in cells)}


def frontend(request):
    index = Path(settings.BASE_DIR).parent / "frontend/dist/index.html"
    if not index.exists():
        return JsonResponse({"service": "Wayline API", "health": "/api/health"}, status=200 if request.path == "/" else 404)
    return FileResponse(index.open("rb"), content_type="text/html")
