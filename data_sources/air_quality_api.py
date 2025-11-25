# data_sources/air_quality_api.py

import requests
from config.settings import settings

def fetch_air_quality_data(zip_code: str) -> dict:
    """
    Fetch AQI from AirNow API. If API fails, return fallback.
    """
    api_key = settings.AIRNOW_API_KEY
    if not api_key:
        print("[AirNow] ERROR: AIRNOW_API_KEY not set in .env or settings.py")
        return fallback(zip_code)

    try:
        url = (
            "https://www.airnowapi.org/aq/observation/zipCode/current/"
            f"?format=application/json&zipCode={zip_code}&distance=25&API_KEY={api_key}"
        )
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        if not data or not isinstance(data, list):
            return fallback(zip_code)

        # Pick PM2.5 or O3 if available, otherwise the first available pollutant
        preferred = next((x for x in data if x.get("ParameterName") in ["PM2.5", "O3"]), data[0])

        aqi = preferred.get("AQI", 0)
        category = preferred.get("Category", {}).get("Name", "Unknown")
        pollutant = preferred.get("ParameterName", "Unknown")

        return {
            "aqi": aqi,
            "category": category,
            "pollutant": pollutant,
        }

    except Exception as e:
        print("[AirNow] ERROR:", e)
        return fallback(zip_code)


def fallback(zip_code):
    """
    Fallback when API fails. Uses a generic safe AQI placeholder.
    """
    return {
        "aqi": 55,  # moderate
        "category": "Moderate",
        "pollutant": "Unknown",
    }
