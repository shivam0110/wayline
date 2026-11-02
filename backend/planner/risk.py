import math

LEVELS = ["Low", "Moderate", "High", "Severe", "No Travel"]


def classify(weather, load):
    if weather is None or any(weather.get(k) is None or not math.isfinite(weather[k]) or weather[k] < 0 for k in ("wind", "rain", "snow")):
        return {"level": None, "label": "Unknown", "reasons": ["Required weather forecast unavailable"]}
    wind, rain, snow = (weather[k] for k in ("wind", "rain", "snow"))
    wind_risk = sum(wind >= x for x in (25, 35, 45, 55))
    rain_risk = 4 if rain > 1 else sum(rain >= x for x in (.1, .25, .5))
    snow_risk = 4 if snow > 3 else sum(snow >= x for x in (.5, 1, 2))
    override = 4 if wind >= 45 and load > 30000 else 3 if wind >= 35 and load > 40000 else 0
    level = max(wind_risk, rain_risk, snow_risk, override)
    reasons = [f"{name} {value:g} {unit}: {LEVELS[risk]}" for name, value, unit, risk in (
        ("Wind", wind, "mph", wind_risk), ("Rain", rain, "in/hr", rain_risk), ("Snow", snow, "in/hr", snow_risk)
    ) if risk == level and risk > 0]
    if override and override == level:
        reasons.append(f"Wind/load rule: {wind:g} mph with {load:,.0f} lb → {LEVELS[override]}")
    return {"level": level, "label": LEVELS[level], "reasons": reasons or ["All weather values below Moderate thresholds"]}


def summarize(segments):
    miles = [0.0] * 5
    unknown = 0.0
    for segment in segments:
        if segment["risk"] is None:
            unknown += segment["miles"]
        else:
            miles[segment["risk"]] += segment["miles"]
    total = sum(miles) + unknown
    reasons = []
    if miles[4] > 0:
        reasons.append(f"{miles[4]:.1f} No Travel miles")
    if unknown > 0:
        reasons.append(f"{unknown:.1f} miles with unavailable forecasts")
    return {
        "risk_miles": dict(zip(LEVELS, miles)), "unknown_miles": unknown,
        "average_risk": None if unknown or not total else sum(i * value for i, value in enumerate(miles)) / total,
        "eligible": not reasons and total > 0, "exclusion_reasons": reasons,
    }


def recommend(routes):
    eligible = [r for r in routes if r["eligible"]]
    best = min(eligible, key=lambda r: (r["risk_miles"]["Severe"], r["risk_miles"]["High"], r["average_risk"], r["duration_seconds"], r["id"]), default=None)
    return best["id"] if best else None
