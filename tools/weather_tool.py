"""Weather tool — current temperature and conditions for a city.

FR-TOOL-03: Uses wttr.in/{city}?format=j1 (free, no auth required).
Handles city-not-found gracefully.
"""

from __future__ import annotations

# TODO (Phase 1): uncomment once langchain + requests are installed
# import requests
# from langchain_core.tools import tool
#
# WTTR_URL = "https://wttr.in/{city}?format=j1"
#
# @tool
# def get_weather(city: str) -> str:
#     """Return current temperature and weather condition for a city name."""
#     try:
#         resp = requests.get(WTTR_URL.format(city=city), timeout=5)
#         resp.raise_for_status()
#         data = resp.json()
#         current = data["current_condition"][0]
#         temp_c = current["temp_C"]
#         desc = current["weatherDesc"][0]["value"]
#         humidity = current["humidity"]
#         return f"{temp_c}°C, {desc}, humidity {humidity}%"
#     except requests.exceptions.HTTPError as e:
#         if e.response is not None and e.response.status_code == 404:
#             return f"City not found: {city!r}"
#         return f"Weather service error: {e}"
#     except Exception as e:
#         return f"Could not fetch weather: {e}"


def get_weather(city: str) -> str:
    """Return current weather for *city*. (stub — Phase 1)"""
    raise NotImplementedError("Phase 1 — get_weather")
