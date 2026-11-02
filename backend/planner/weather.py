from bisect import bisect_left
from datetime import datetime, timezone
from math import isfinite


def at_time(hourly, timestamp):
    if not hourly or not hourly.get("time"):
        return None
    times = hourly["time"]
    # Rain/showers/snowfall refer to the preceding hour; use the interval ending at ceil(ETA).
    i = bisect_left(times, timestamp)
    if i == len(times) or timestamp < times[0]:
        return None
    try:
        wind, rain, showers, snow = (hourly[key][i] for key in ("wind_speed_10m", "rain", "showers", "snowfall"))
        if i > 0 and timestamp != times[i]:
            before = hourly["wind_speed_10m"][i - 1]
            if before is None:
                return None
            wind = before + (wind - before) * (timestamp - times[i - 1]) / (times[i] - times[i - 1])
        if any(v is None or not isfinite(v) for v in (wind, rain, showers, snow)):
            return None
        return {"wind": wind, "rain": (rain + showers) / 25.4, "snow": snow / 2.54, "forecast_time": iso(times[i])}
    except (KeyError, IndexError, TypeError):
        return None


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
