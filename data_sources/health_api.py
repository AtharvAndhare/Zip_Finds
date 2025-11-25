# data_sources/health_api.py

import requests
from config.settings import settings
from core.geo_utils import zip_to_latlon
#from data_sources.osm_api import query_overpass
from data_sources.osm_api import fetch_osm_poi_data

# =============================
# HRSA ENDPOINTS (No key needed)
# =============================

HPSA_URL = "https://data.hrsa.gov/resource/gt7t-n7q6.json"
PRIMARY_CARE_URL = "https://data.hrsa.gov/resource/44px-5di8.json"


def fetch_hpsa_status(zip_code: str) -> bool:
    """
    Returns True if ZIP is a Health Professional Shortage Area (HPSA).
    """
    try:
        resp = requests.get(HPSA_URL, params={"zip": zip_code}, timeout=10)
        if resp.status_code != 200:
            return False

        data = resp.json()
        # any record with a score > 0 indicates shortage
        for row in data:
            score = row.get("hpsa_score")
            if score and float(score) > 0:
                return True
    except Exception:
        pass

    return False


def fetch_primary_care_centers(zip_code: str) -> int:
    """
    Count primary care facilities from HRSA data.
    """
    try:
        resp = requests.get(PRIMARY_CARE_URL, params={"zip": zip_code}, timeout=10)
        if resp.status_code != 200:
            return 0

        data = resp.json()
        count = 0
        for row in data:
            # Check keywords
            name = (row.get("facility_name") or "").lower()
            if any(x in name for x in ["clinic", "health", "medical", "primary"]):
                count += 1
        return count
    except Exception:
        return 0


def fetch_hospitals_osm(zip_code: str) -> int:
    """
    Use OSM cached lookup to count hospitals.
    """
    try:
        data = fetch_osm_poi_data(zip_code)
        return data.get("clinics", 0)  # or "hospitals" once we add it
    except Exception:
        return 0



def fetch_health_data(zip_code: str) -> dict:
    """
    Unified API returning health metrics.
    """
    if settings.USE_MOCK_DATA:
        return {
            "primary_care_centers": 5,
            "hospitals": 1,
            "is_hpsa": False,
        }

    # Live Mode
    clinics = fetch_primary_care_centers(zip_code)
    hospitals = fetch_hospitals_osm(zip_code)
    is_hpsa = fetch_hpsa_status(zip_code)

    return {
        "primary_care_centers": clinics,
        "hospitals": hospitals,
        "is_hpsa": is_hpsa,
    }
