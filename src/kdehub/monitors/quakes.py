import time

from kdehub.core import CRIT, OK, WARN, Reading, get_json

NAME = "Earthquakes"
INTERVAL = 300

URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def ago(seconds):
    for unit, size in (("day", 86400), ("hour", 3600), ("min", 60)):
        if seconds >= size:
            n = int(seconds // size)
            return f"{n} {unit}{'s' if n != 1 and unit != 'min' else ''} ago"
    return "just now"


def parse(payload, now):
    features = payload["features"]
    if not features:
        return [Reading("Latest", "none in range")]
    props = features[0]["properties"]
    age = now - props["time"] / 1000
    mag = props["mag"]
    recent = age < 86400
    level = CRIT if recent and mag >= 4 else WARN if recent and mag >= 3 else OK
    return [Reading("Latest", f"M{mag:.1f}, {props['place']}, {ago(age)}", level)]


def read(cfg):
    payload = get_json(URL, {
        "format": "geojson", "latitude": cfg["latitude"], "longitude": cfg["longitude"],
        "maxradiuskm": cfg.get("radius_km", 100), "minmagnitude": cfg.get("min_magnitude", 2.5),
        "orderby": "time", "limit": 1})
    return parse(payload, time.time())
