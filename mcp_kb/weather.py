"""Weather lookup: an offline canned table by default, a real keyless
Open-Meteo call when MCP_KB_LIVE_WEATHER=1.

Same offline/live split used across the AI-track roadmap (see project
11-function-calling-assistant): the demo runs with no key and no network by
default, and one env var swaps in a genuine HTTP call, keyless because
Open-Meteo needs no API key or signup.
"""

from __future__ import annotations

import os

# WMO weather codes -> plain-English description (subset covering common cases)
_WMO_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    95: "thunderstorm",
}

OFFLINE_WEATHER = {
    "paris": ("clear sky", 18),
    "london": ("light rain", 14),
    "tokyo": ("partly cloudy", 24),
    "new york": ("overcast", 12),
    "sydney": ("clear sky", 22),
    "oslo": ("light snow", -2),
}


def _describe_code(code: int) -> str:
    return _WMO_CODES.get(code, f"weather code {code}")


def _fetch_live(city: str) -> str | None:
    """Real, keyless Open-Meteo lookup. Returns None on any failure so
    callers can fall back to offline data instead of crashing a tool call."""
    try:
        import requests
    except ImportError:
        return None
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=5,
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            return None
        lat, lon = results[0]["latitude"], results[0]["longitude"]
        resolved_name = results[0]["name"]

        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": "temperature_2m,weather_code"},
            timeout=5,
        )
        forecast.raise_for_status()
        current = forecast.json()["current"]
        temp_c = current["temperature_2m"]
        description = _describe_code(int(current["weather_code"]))
        return f"{resolved_name}: {description}, {temp_c:.0f}C (live, open-meteo.com)"
    except Exception:
        return None


def get_weather(city: str, live: bool | None = None) -> str:
    """Return a one-line weather report for `city`.

    `live=None` (the default) reads MCP_KB_LIVE_WEATHER from the
    environment so the MCP server's behavior is controlled by how it's
    launched, not by a per-call argument the model would have to guess.
    """
    if live is None:
        live = os.environ.get("MCP_KB_LIVE_WEATHER", "0") == "1"

    if live:
        result = _fetch_live(city)
        if result is not None:
            return result
        # live requested but failed (offline machine, bad city name, etc.) --
        # fall through to the offline table rather than erroring the tool call

    key = city.strip().lower()
    if key in OFFLINE_WEATHER:
        description, temp_c = OFFLINE_WEATHER[key]
        return f"{city.title()}: {description}, {temp_c}C (offline demo data)"
    return f"No offline weather data for '{city}' -- known cities: {', '.join(sorted(OFFLINE_WEATHER))}"
