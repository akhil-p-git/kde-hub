from kdehub.core import CRIT, OK, WARN, Reading, get_json

NAME = "Air quality"
INTERVAL = 900

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
# US AQI bands: (upper bound, category, level)
BANDS = [
    (50, "Good", OK), (100, "Moderate", OK), (150, "Unhealthy for sensitive groups", WARN),
    (200, "Unhealthy", CRIT), (300, "Very unhealthy", CRIT), (float("inf"), "Hazardous", CRIT),
]


def classify(aqi):
    for upper, category, level in BANDS:
        if aqi <= upper:
            return category, level


def parse(payload):
    cur = payload["current"]
    category, level = classify(cur["us_aqi"])
    return [
        Reading("US AQI", f"{cur['us_aqi']:.0f} ({category})", level),
        Reading("PM2.5", f"{cur['pm2_5']:.1f} µg/m³"),
    ]


def read(cfg):
    return parse(get_json(URL, {
        "latitude": cfg["latitude"], "longitude": cfg["longitude"], "current": "us_aqi,pm2_5"}))
