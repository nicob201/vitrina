from __future__ import annotations

import math
from dataclasses import dataclass
from urllib.parse import quote, urlencode

# Weather data by Open-Meteo.com (free, no key, attribution in the README).


@dataclass(frozen=True)
class Place:
    label: str
    latitude: float
    longitude: float


def geocode_url(city: str, lang: str) -> str:
    query = {"name": city, "count": 10, "language": lang, "format": "json"}
    return "https://geocoding-api.open-meteo.com/v1/search?" + _encode(query)


def parse_place(data: dict, country: str) -> Place | None:
    for r in data.get("results") or []:  # the API leaves "results" out when nothing matches
        if country and (r.get("country_code") or "").lower() != country.lower():
            continue
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        if parts[1] == parts[0]:
            parts[1] = None
        return Place(", ".join(p for p in parts if p), float(r["latitude"]), float(r["longitude"]))
    return None


def forecast_url(place: Place, units: str) -> str:
    query = {
        "latitude": place.latitude,
        "longitude": place.longitude,
        "current": "temperature_2m,weather_code,is_day",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "forecast_days": 1,
    }
    if units == "fahrenheit":
        query["temperature_unit"] = "fahrenheit"
    return "https://api.open-meteo.com/v1/forecast?" + _encode(query)


def parse_forecast(data: dict) -> dict:
    current, daily = data["current"], data["daily"]
    return {
        "temp": _round(current["temperature_2m"]),
        "max": _round(daily["temperature_2m_max"][0]),
        "min": _round(daily["temperature_2m_min"][0]),
        "condition": condition_for(current["weather_code"]),
        "is_day": bool(current["is_day"]),
    }


_CONDITIONS = [
    ({0}, "clear"),
    ({1, 2}, "partly_cloudy"),
    ({3}, "cloudy"),
    ({45, 48}, "fog"),
    ({51, 53, 55, 56, 57}, "drizzle"),
    ({61, 63, 65, 66, 67, 80, 81, 82}, "rain"),
    ({71, 73, 75, 77, 85, 86}, "snow"),
    ({95, 96, 99}, "storm"),
]


def condition_for(code: int) -> str:
    """WMO weather code → one of the eight conditions the page has icons for."""
    for codes, name in _CONDITIONS:
        if code in codes:
            return name
    return "cloudy"


def _encode(query: dict) -> str:
    return urlencode(query, safe=",", quote_via=quote)


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))
