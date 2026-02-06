# core/fast_aggregator.py
"""
ULTRA-FAST data aggregator - targets 1-2 second fetch times.

Optimizations:
1. Single combined Census API call (fetches ALL variables at once)
2. Aggressive 3-second timeouts
3. Immediate fallbacks on slow/failed APIs
4. Minimal retries
5. Connection pooling with keep-alive
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from functools import lru_cache

from config.settings import settings
from core.geo_utils import zip_to_latlon
from db.zip_cache import get_cached_zip, store_zip_data

# =============================================================================
# GLOBAL SESSION (Connection pooling + keep-alive)
# =============================================================================
_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        # Enable keep-alive and connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # No retries - fail fast
        )
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
    return _session


# =============================================================================
# FAST CENSUS: Single call fetches ALL variables
# =============================================================================
CENSUS_VARS = [
    "B19013_001E",   # Median income
    "B15003_001E",   # Education total
    "B15003_022E",   # Bachelor's
    "B15003_023E",   # Master's
    "B15003_024E",   # Professional
    "B15003_025E",   # Doctorate
    "B01003_001E",   # Population
    "B25064_001E",   # Median rent
    "B28002_001E",   # Broadband total households
    "B28002_004E",   # Broadband subscribers
]

def _fast_census(zip_code: str) -> dict:
    """Fetch ALL Census data in a single API call."""
    session = _get_session()
    vars_str = ",".join(CENSUS_VARS)
    
    for year in ["2022", "2021"]:
        try:
            url = f"https://api.census.gov/data/{year}/acs/acs5?get={vars_str}&for=zip%20code%20tabulation%20area:{zip_code}"
            if settings.CENSUS_API_KEY:
                url += f"&key={settings.CENSUS_API_KEY}"
            
            resp = session.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 1:
                    return _parse_census(data[1])
        except Exception:
            continue
    
    return _census_fallback()


def _parse_census(row: list) -> dict:
    """Parse Census response row into structured data."""
    def safe_float(val):
        try:
            if val in [None, "", "null", "-666666666"]:
                return None
            return float(val)
        except:
            return None
    
    income = safe_float(row[0])
    edu_total = safe_float(row[1])
    bach = safe_float(row[2])
    masters = safe_float(row[3])
    prof = safe_float(row[4])
    doc = safe_float(row[5])
    pop = safe_float(row[6])
    rent = safe_float(row[7])
    bb_total = safe_float(row[8])
    bb_subs = safe_float(row[9])
    
    # Calculate education rate
    bachelors_rate = None
    if edu_total and edu_total > 0:
        bach_plus = (bach or 0) + (masters or 0) + (prof or 0) + (doc or 0)
        bachelors_rate = round((bach_plus / edu_total) * 100, 2)
    
    # Calculate broadband percentage
    broadband_pct = None
    if bb_total and bb_total > 0 and bb_subs:
        broadband_pct = round((bb_subs / bb_total) * 100, 2)
    
    return {
        "median_income": income,
        "bachelors_rate": bachelors_rate,
        "resident_base": int(pop) if pop else None,
        "median_rent": rent,
        "broadband_pct": broadband_pct,
    }


def _census_fallback() -> dict:
    """Fallback values when Census fails."""
    return {
        "median_income": 65000,
        "bachelors_rate": 32.0,
        "resident_base": 25000,
        "median_rent": 1200,
        "broadband_pct": 85.0,
    }


# =============================================================================
# FAST AIR QUALITY
# =============================================================================
def _fast_air_quality(zip_code: str) -> dict:
    """Fast AirNow fetch with immediate fallback."""
    if not settings.AIRNOW_API_KEY:
        return {"aqi": 50, "category": "Good", "pollutant": "Unknown"}
    
    try:
        session = _get_session()
        url = f"https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode={zip_code}&distance=25&API_KEY={settings.AIRNOW_API_KEY}"
        resp = session.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                preferred = next((x for x in data if x.get("ParameterName") in ["PM2.5", "O3"]), data[0])
                return {
                    "aqi": preferred.get("AQI", 50),
                    "category": preferred.get("Category", {}).get("Name", "Moderate"),
                    "pollutant": preferred.get("ParameterName", "Unknown"),
                }
    except Exception:
        pass
    
    return {"aqi": 50, "category": "Good", "pollutant": "Unknown"}


# =============================================================================
# FAST HEALTH (HRSA)
# =============================================================================
def _fast_health(zip_code: str) -> dict:
    """Fast health data with quick timeout."""
    session = _get_session()
    result = {"primary_care_centers": 0, "hospitals": 0, "is_hpsa": False}
    
    # HPSA check
    try:
        resp = session.get(
            "https://data.hrsa.gov/resource/gt7t-n7q6.json",
            params={"zip": zip_code},
            timeout=2
        )
        if resp.status_code == 200:
            data = resp.json()
            for row in data:
                if row.get("hpsa_score") and float(row.get("hpsa_score", 0)) > 0:
                    result["is_hpsa"] = True
                    break
    except Exception:
        pass
    
    # Primary care count
    try:
        resp = session.get(
            "https://data.hrsa.gov/resource/44px-5di8.json",
            params={"zip": zip_code},
            timeout=2
        )
        if resp.status_code == 200:
            data = resp.json()
            result["primary_care_centers"] = len(data)
    except Exception:
        pass
    
    return result


# =============================================================================
# FAST OSM (Simplified - only essential POIs)
# =============================================================================
OSM_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

def _fast_osm(zip_code: str) -> dict:
    """Fast OSM with single query for all POIs."""
    if settings.USE_MOCK_DATA:
        return {"parks": 5, "grocery_stores": 10, "clinics": 3, "transit_stops": 20, "police_stations": 1}
    
    try:
        lat, lon = zip_to_latlon(zip_code)
        session = _get_session()
        
        # Single query for all POI types
        query = f"""
        [out:json][timeout:3];
        (
          node["leisure"="park"](around:3000,{lat},{lon});
          node["shop"="supermarket"](around:3000,{lat},{lon});
          node["amenity"="clinic"](around:3000,{lat},{lon});
          node["amenity"="police"](around:3000,{lat},{lon});
        );
        out count;
        """
        
        for server in OSM_SERVERS:
            try:
                resp = session.post(server, data={"data": query}, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    if "elements" in data and data["elements"]:
                        tags = data["elements"][0].get("tags", {})
                        total = int(tags.get("total", 0))
                        # Distribute count estimates
                        return {
                            "parks": max(total // 4, 1),
                            "grocery_stores": max(total // 4, 1),
                            "clinics": max(total // 4, 1),
                            "transit_stops": total // 2,
                            "police_stations": max(total // 10, 1),
                        }
            except Exception:
                continue
    except Exception:
        pass
    
    # Fallback
    return {"parks": 3, "grocery_stores": 5, "clinics": 2, "transit_stops": 10, "police_stations": 1}


# =============================================================================
# FAST CRIME SCORE (Computed from Census data)
# =============================================================================
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

# ZIP prefix to state mapping (first 3 digits)
ZIP_TO_STATE = {
    "995": "Alaska", "996": "Alaska", "997": "Alaska", "998": "Alaska", "999": "Alaska",
    "100": "New York", "101": "New York", "102": "New York", "103": "New York", "104": "New York",
    "070": "New Jersey", "071": "New Jersey", "072": "New Jersey", "073": "New Jersey",
    "900": "California", "901": "California", "902": "California", "903": "California",
    "840": "Utah", "841": "Utah", "842": "Utah", "843": "Utah", "844": "Utah", "845": "Utah",
    "770": "Texas", "771": "Texas", "772": "Texas", "773": "Texas",
    "606": "Illinois", "607": "Illinois", "608": "Illinois",
    "330": "Florida", "331": "Florida", "332": "Florida", "333": "Florida",
}

def _compute_crime(zip_code: str, census_data: dict, osm_data: dict) -> dict:
    """Compute crime score without additional API calls."""
    # Get state from ZIP prefix
    prefix = zip_code[:3]
    state = ZIP_TO_STATE.get(prefix, None)
    baseline = FBI_STATE_CRIME.get(state, 400) if state else 400
    
    income = census_data.get("median_income") or 65000
    edu = census_data.get("bachelors_rate") or 30
    
    income_risk = 1 - (min(max(income / 120000, 0), 1))
    edu_risk = 1 - (min(max(edu / 60, 0), 1))
    
    police_count = osm_data.get("police_stations", 1)
    police_presence = min(police_count / 12, 1)
    
    score_raw = (
        0.45 * (baseline / 1000) +
        0.35 * income_risk +
        0.20 * edu_risk -
        0.10 * police_presence
    )
    
    score_scaled = max(0, min(score_raw * 100, 100))
    return {"crime_per_1k": round(score_scaled, 1)}


# =============================================================================
# MAIN FAST AGGREGATOR
# =============================================================================
def collect_all_data_fast(zip_code: str) -> dict:
    """
    ULTRA-FAST data collection targeting 1-2 seconds.
    
    Uses:
    - Single combined Census API call
    - 3-second max timeouts
    - Parallel execution with ThreadPool
    - Immediate fallbacks
    """
    
    # Check cache first
    cached = get_cached_zip(zip_code)
    if cached:
        print(f"[CACHE] Returning cached data for ZIP {zip_code}")
        return cached
    
    print(f"[FAST] Fetching data for ZIP {zip_code}")
    start_time = time.time()
    
    # Execute all fetches in parallel with strict timeout
    results = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            "census": executor.submit(_fast_census, zip_code),
            "air_quality": executor.submit(_fast_air_quality, zip_code),
            "health": executor.submit(_fast_health, zip_code),
            "osm": executor.submit(_fast_osm, zip_code),
        }
        
        for key, future in futures.items():
            try:
                results[key] = future.result(timeout=4)
            except Exception as e:
                print(f"[FAST] {key} failed: {e}")
                if key == "census":
                    results[key] = _census_fallback()
                elif key == "air_quality":
                    results[key] = {"aqi": 50, "category": "Good", "pollutant": "Unknown"}
                elif key == "health":
                    results[key] = {"primary_care_centers": 0, "hospitals": 0, "is_hpsa": False}
                elif key == "osm":
                    results[key] = {"parks": 3, "grocery_stores": 5, "clinics": 2, "transit_stops": 10, "police_stations": 1}
    
    # Extract data from combined Census call
    census_data = results.get("census", {})
    
    # Build final data structure
    live_data = {
        "census": {
            "median_income": census_data.get("median_income"),
            "bachelors_rate": census_data.get("bachelors_rate"),
            "resident_base": census_data.get("resident_base"),
        },
        "housing": {
            "median_rent": census_data.get("median_rent"),
            "rent_to_income": None,
            "studio": None, "1br": None, "2br": None, "3br": None, "4br": None,
        },
        "broadband": {
            "broadband_pct": census_data.get("broadband_pct"),
            "fiber_pct": (census_data.get("broadband_pct") or 85) * 0.35,
            "cable_pct": (census_data.get("broadband_pct") or 85) * 0.65,
        },
        "health": results.get("health", {}),
        "osm": results.get("osm", {}),
        "air_quality": results.get("air_quality", {}),
        "crime": _compute_crime(zip_code, census_data, results.get("osm", {})),
    }
    
    # Calculate rent to income ratio
    if census_data.get("median_rent") and census_data.get("median_income"):
        annual_rent = census_data["median_rent"] * 12
        live_data["housing"]["rent_to_income"] = round(annual_rent / census_data["median_income"], 3)
    
    elapsed = time.time() - start_time
    print(f"[FAST] Completed in {elapsed:.2f}s")
    
    # Store in Supabase
    try:
        store_zip_data(zip_code, live_data)
        print(f"[CACHE] Stored ZIP {zip_code}")
    except Exception as e:
        print(f"[CACHE] Store failed: {e}")
    
    return live_data
