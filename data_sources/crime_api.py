# data_sources/crime_api.py

import functools
import requests
from data_sources.census_api import fetch_census_data
from data_sources.osm_api import fetch_osm_poi_data


# ======================================================
# FBI Violent Crime Rate (per 100k) — 2023 Snapshot
# Source: FBI Crime Data Explorer
# ======================================================
FBI_STATE_CRIME = {
    "Alabama": 458, "Alaska": 837, "Arizona": 483, "Arkansas": 645, "California": 442,
    "Colorado": 423, "Connecticut": 184, "Delaware": 488, "DC": 996, "Florida": 258,
    "Georgia": 400, "Hawaii": 254, "Idaho": 242, "Illinois": 425, "Indiana": 358,
    "Iowa": 290, "Kansas": 416, "Kentucky": 222, "Louisiana": 639, "Maine": 108,
    "Maryland": 454, "Massachusetts": 308, "Michigan": 500, "Minnesota": 260,
    "Mississippi": 277, "Missouri": 612, "Montana": 406, "Nebraska": 284,
    "Nevada": 492, "New Hampshire": 113, "New Jersey": 195, "New Mexico": 781,
    "New York": 356, "North Carolina": 370, "North Dakota": 265, "Ohio": 308,
    "Oklahoma": 440, "Oregon": 291, "Pennsylvania": 315, "Rhode Island": 228,
    "South Carolina": 559, "South Dakota": 351, "Tennessee": 608, "Texas": 435,
    "Utah": 251, "Vermont": 190, "Virginia": 208, "Washington": 294,
    "West Virginia": 272, "Wisconsin": 283, "Wyoming": 319
}


# ======================================================
# Cached State Lookup (avoids repeated API calls)
# ======================================================
@functools.lru_cache(maxsize=500)
def get_state_from_zip(zip_code: str) -> str | None:
    """Get state name from ZIP code. Cached to avoid repeat calls."""
    try:
        url = f"https://api.census.gov/data/2023/acs/acs5?get=NAME&for=zip%20code%20tabulation%20area:{zip_code}"
        data = requests.get(url, timeout=10).json()
        if len(data) > 1 and "," in data[1][0]:
            return data[1][0].split(",")[-1].strip()
    except Exception:
        pass
    return None


# ======================================================
# OPTIMIZED: Compute crime score with pre-fetched data
# ======================================================
def compute_crime_score(zip_code: str, census_data: dict = None, osm_data: dict = None) -> dict:
    """
    Compute crime proxy score using pre-fetched data.
    
    OPTIMIZED: Accepts census_data and osm_data to avoid duplicate API calls
    when called from aggregator (which already fetched these).
    
    Args:
        zip_code: The ZIP code
        census_data: Pre-fetched census data (optional, will fetch if None)
        osm_data: Pre-fetched OSM data (optional, will fetch if None)
    
    Returns:
        { "crime_per_1k": <score 0–100> }
    """
    # 1) State-level violent crime baseline
    state = get_state_from_zip(zip_code)
    baseline = FBI_STATE_CRIME.get(state, 400)  # national avg fallback

    # 2) Use provided census data or fetch if not provided
    census = census_data if census_data else fetch_census_data(zip_code)
    income = census.get("median_income", None)
    edu = census.get("bachelors_rate", None)

    # Local signals (stronger indicators of neighborhood safety)
    # High income and education strongly correlate with lower local crime
    income_safety = min(max((income or 0) / 150000, 0), 1)   # 0=poor, 1=wealthy
    edu_safety = min(max((edu or 0) / 65, 0), 1)             # 0=low edu, 1=high edu

    # 3) Use provided OSM data or fetch if not provided
    osm = osm_data if osm_data else fetch_osm_poi_data(zip_code)
    police_count = osm.get("police_stations", 0)
    police_presence = min(police_count / 10, 1)  # normalized

    # -------------------------------------------------
    # Crime risk index (higher = more crime)
    # Local signals weighted much more than state baseline
    # -------------------------------------------------
    state_risk = baseline / 1000  # scale FBI rate to 0-1 range

    # Blend: 25% state baseline, 40% income signal, 25% education signal, 10% police
    crime_risk = (
        0.25 * state_risk +
        0.40 * (1 - income_safety) +
        0.25 * (1 - edu_safety) +
        0.10 * (1 - police_presence)
    )

    # Scale to 0-100 (crime_per_1k is used as a 0-100 risk score)
    score_scaled = max(0, min(crime_risk * 100, 100))

    return {"crime_per_1k": round(score_scaled, 1)}


# ======================================================
# Legacy function (for backwards compatibility)
# ======================================================
def fetch_crime_data(zip_code: str) -> dict:
    """
    Returns { "crime_per_1k": <score 0–100> } 
    Uses proxy model if police data unavailable.
    
    NOTE: For better performance, use compute_crime_score() with pre-fetched data.
    """
    return compute_crime_score(zip_code)
