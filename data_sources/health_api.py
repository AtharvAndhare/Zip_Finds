# data_sources/health_api.py

import functools
import requests
from concurrent.futures import ThreadPoolExecutor
from config.settings import settings
from core.geo_utils import zip_to_latlon
from data_sources.osm_api import fetch_osm_poi_data

# =============================
# HRSA ENDPOINTS (No key needed)
# =============================
HPSA_URL = "https://data.hrsa.gov/resource/gt7t-n7q6.json"
PRIMARY_CARE_URL = "https://data.hrsa.gov/resource/44px-5di8.json"

# Shared session for connection reuse
_session = None

def _get_session():
    """Reuse HTTP session for connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


@functools.lru_cache(maxsize=500)
def fetch_hpsa_status(zip_code: str) -> bool:
    """
    Returns True if ZIP is a Health Professional Shortage Area (HPSA).
    Cached to avoid redundant API calls.
    """
    try:
        session = _get_session()
        resp = session.get(HPSA_URL, params={"zip": zip_code}, timeout=10)
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


@functools.lru_cache(maxsize=500)
def fetch_primary_care_centers(zip_code: str) -> int:
    """
    Count primary care facilities from HRSA data.
    Cached to avoid redundant API calls.
    """
    try:
        session = _get_session()
        resp = session.get(PRIMARY_CARE_URL, params={"zip": zip_code}, timeout=10)
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


def fetch_hospitals_from_osm(osm_data: dict = None, zip_code: str = None) -> int:
    """
    Get hospital count from OSM data.
    
    OPTIMIZED: Accepts pre-fetched osm_data to avoid duplicate calls.
    """
    try:
        if osm_data:
            return osm_data.get("clinics", 0)
        elif zip_code:
            data = fetch_osm_poi_data(zip_code)
            return data.get("clinics", 0)
        return 0
    except Exception:
        return 0


def fetch_health_data(zip_code: str, osm_data: dict = None) -> dict:
    """
    Unified API returning health metrics.
    
    OPTIMIZED: 
    - HRSA calls run in parallel
    - Accepts optional osm_data to avoid duplicate OSM call
    """
    if settings.USE_MOCK_DATA:
        return {
            "primary_care_centers": 5,
            "hospitals": 1,
            "is_hpsa": False,
        }

    # Live Mode - Run HRSA calls in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_clinics = executor.submit(fetch_primary_care_centers, zip_code)
        future_hpsa = executor.submit(fetch_hpsa_status, zip_code)
        
        clinics = future_clinics.result()
        is_hpsa = future_hpsa.result()

    # Use provided OSM data or fetch (OSM has its own cache)
    hospitals = fetch_hospitals_from_osm(osm_data=osm_data, zip_code=zip_code)

    return {
        "primary_care_centers": clinics,
        "hospitals": hospitals,
        "is_hpsa": is_hpsa,
    }
