from datetime import datetime

from kdehub.core import Reading, get_json, level_for

NAME = "Weather"
INTERVAL = 900

URL = "https://api.open-meteo.com/v1/forecast"
# WMO weather interpretation codes, grouped as documented by Open-Meteo
CODES = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow",
    75: "Heavy snow", 80: "Rain showers", 81: "Rain showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail",
}
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max,sunrise,sunset"


def clock(iso):
    return datetime.fromisoformat(iso).strftime("%-I:%M %p")


def parse(payload, name, unit="fahrenheit"):
    cur, day = payload["current"], payload["daily"]
    deg = "°F" if unit == "fahrenheit" else "°C"
    uv = day["uv_index_max"][0]
    return [
        Reading(name, f"{cur['temperature_2m']:.0f}{deg}"),
        Reading("Sky", CODES.get(cur["weather_code"], f"code {cur['weather_code']}")),
        Reading("High / low", f"{day['temperature_2m_max'][0]:.0f}° / {day['temperature_2m_min'][0]:.0f}°"),
        Reading("Rain chance", f"{day['precipitation_probability_max'][0]}%"),
        Reading("UV (max today)", f"{uv:.1f}", level_for(uv, 6, 8)),
        Reading("Sun", f"{clock(day['sunrise'][0])} – {clock(day['sunset'][0])}"),
    ]


def read(cfg):
    unit = cfg.get("unit", "fahrenheit")
    payload = get_json(URL, {
        "latitude": cfg["latitude"], "longitude": cfg["longitude"],
        "current": "temperature_2m,weather_code", "daily": DAILY,
        "temperature_unit": unit, "timezone": "auto", "forecast_days": 1,
    })
    return parse(payload, cfg.get("name", "Weather"), unit)
