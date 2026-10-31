from kdehub.core import CRIT, WARN, Reading, get_json

NAME = "Weather alerts"
INTERVAL = 600

URL = "https://api.weather.gov/alerts/active"
SEVERE = {"Extreme", "Severe"}


def parse(payload):
    features = payload["features"]
    if not features:
        return [Reading("Alerts", "none active")]
    return [
        Reading(f["properties"]["event"], f["properties"].get("headline") or "",
                CRIT if f["properties"].get("severity") in SEVERE else WARN)
        for f in features
    ]


def read(cfg):
    # api.weather.gov requires a User-Agent; it is deliberately generic
    return parse(get_json(URL, {"point": f"{cfg['latitude']},{cfg['longitude']}"},
                          headers={"User-Agent": "kde-hub personal desktop monitor",
                                   "Accept": "application/geo+json"}))
