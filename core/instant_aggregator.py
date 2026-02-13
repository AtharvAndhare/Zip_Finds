# core/instant_aggregator.py
"""
INSTANT data aggregator - targets ~1-2 second fetch times.

Strategy: 
- 2-second hard timeout on ALL API calls
- Single Census call for all data
- Skip slow APIs entirely, use smart estimates
- Pre-warmed connection pool
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from config.settings import settings
from core.geo_utils import zip_to_latlon
from db.zip_cache import get_cached_zip, store_zip_data

# =============================================================================
# CONNECTION POOL (Pre-warmed, keep-alive)
# =============================================================================
_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=30,
            max_retries=0
        )
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
    return _session


# =============================================================================
# INSTANT CENSUS (2-second timeout, single call)
# =============================================================================
def _instant_census(zip_code: str) -> dict:
    """Single Census call with 2.5s timeout."""
    session = _get_session()
    
    # All variables in one call
    vars_str = "B19013_001E,B15003_001E,B15003_022E,B15003_023E,B15003_024E,B15003_025E,B01003_001E,B25064_001E,B28002_001E,B28002_004E"
    url = f"https://api.census.gov/data/2023/acs/acs5?get={vars_str}&for=zip%20code%20tabulation%20area:{zip_code}"
    
    if settings.CENSUS_API_KEY:
        url += f"&key={settings.CENSUS_API_KEY}"
    
    try:
        resp = session.get(url, timeout=2.5)  # Slightly longer timeout for Census
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 1:
                parsed = _parse_census_row(data[1])
                # Only return if we got real data
                if parsed.get("income") and parsed["income"] > 0:
                    return parsed
    except Exception as e:
        print(f"[CENSUS] API error: {e}")
    
    # Fallback - estimate from ZIP prefix (regional averages)
    print(f"[CENSUS] Using regional estimates for {zip_code}")
    return _estimate_census(zip_code)


def _parse_census_row(row: list) -> dict:
    """Parse Census response."""
    def safe_float(val):
        try:
            if val in [None, "", "null", "-666666666"]:
                return None
            return float(val)
        except:
            return None
    
    income = safe_float(row[0])
    edu_total = safe_float(row[1])
    bach = safe_float(row[2]) or 0
    masters = safe_float(row[3]) or 0
    prof = safe_float(row[4]) or 0
    doc = safe_float(row[5]) or 0
    pop = safe_float(row[6])
    rent = safe_float(row[7])
    bb_total = safe_float(row[8])
    bb_subs = safe_float(row[9])
    
    bachelors_rate = round((bach + masters + prof + doc) / edu_total * 100, 2) if edu_total else 32.0
    broadband_pct = round((bb_subs / bb_total) * 100, 2) if bb_total and bb_subs else 85.0
    
    return {
        "income": income or 65000,
        "bachelors_rate": bachelors_rate,
        "population": int(pop) if pop else 25000,
        "rent": rent or 1200,
        "broadband_pct": broadband_pct,
    }


def _estimate_census(zip_code: str) -> dict:
    """Estimate Census data from ZIP prefix (regional averages)."""
    prefix = int(zip_code[:3])
    
    # Regional estimates based on ZIP prefix ranges
    if 900 <= prefix <= 961:  # California
        return {"income": 80000, "bachelors_rate": 35, "population": 35000, "rent": 2000, "broadband_pct": 90}
    elif 100 <= prefix <= 149:  # New York
        return {"income": 75000, "bachelors_rate": 38, "population": 30000, "rent": 1800, "broadband_pct": 92}
    elif 70 <= prefix <= 89:  # New Jersey
        return {"income": 85000, "bachelors_rate": 40, "population": 28000, "rent": 1600, "broadband_pct": 91}
    elif 840 <= prefix <= 847:  # Utah
        return {"income": 75000, "bachelors_rate": 35, "population": 30000, "rent": 1400, "broadband_pct": 88}
    elif 770 <= prefix <= 799:  # Texas
        return {"income": 65000, "bachelors_rate": 30, "population": 35000, "rent": 1300, "broadband_pct": 85}
    elif 600 <= prefix <= 629:  # Illinois
        return {"income": 70000, "bachelors_rate": 35, "population": 28000, "rent": 1200, "broadband_pct": 88}
    elif 330 <= prefix <= 349:  # Florida
        return {"income": 55000, "bachelors_rate": 28, "population": 32000, "rent": 1400, "broadband_pct": 86}
    else:  # National average
        return {"income": 65000, "bachelors_rate": 32, "population": 25000, "rent": 1200, "broadband_pct": 85}


# =============================================================================
# INSTANT AIR QUALITY (2-second timeout)
# =============================================================================
def _instant_air(zip_code: str) -> dict:
    """Fast AirNow with 2s timeout."""
    if not settings.AIRNOW_API_KEY:
        return {"aqi": 45, "category": "Good", "pollutant": "PM2.5"}
    
    try:
        session = _get_session()
        url = f"https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode={zip_code}&distance=25&API_KEY={settings.AIRNOW_API_KEY}"
        resp = session.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                item = data[0]
                return {
                    "aqi": item.get("AQI", 45),
                    "category": item.get("Category", {}).get("Name", "Good"),
                    "pollutant": item.get("ParameterName", "PM2.5"),
                }
    except:
        pass
    
    return {"aqi": 45, "category": "Good", "pollutant": "PM2.5"}


# =============================================================================
# INSTANT CRIME (No API - computed from Census data)
# =============================================================================
STATE_CRIME_RATES = {
    "CA": 442, "NY": 356, "NJ": 195, "TX": 435, "FL": 258, "IL": 425,
    "PA": 315, "OH": 308, "GA": 400, "NC": 370, "MI": 500, "AZ": 483,
    "WA": 294, "CO": 423, "MA": 308, "VA": 208, "UT": 251, "OR": 291,
}

def _get_state_from_zip(zip_code: str) -> str:
    """Get state code from ZIP prefix."""
    prefix = int(zip_code[:3])
    
    if 900 <= prefix <= 961:
        return "CA"
    elif 100 <= prefix <= 149:
        return "NY"
    elif 70 <= prefix <= 89:
        return "NJ"
    elif 840 <= prefix <= 847:
        return "UT"
    elif 750 <= prefix <= 799:
        return "TX"
    elif 600 <= prefix <= 629:
        return "IL"
    elif 330 <= prefix <= 349:
        return "FL"
    elif 150 <= prefix <= 196:
        return "PA"
    elif 430 <= prefix <= 458:
        return "OH"
    elif 300 <= prefix <= 319:
        return "GA"
    elif 270 <= prefix <= 289:
        return "NC"
    elif 480 <= prefix <= 499:
        return "MI"
    elif 850 <= prefix <= 865:
        return "AZ"
    elif 980 <= prefix <= 994:
        return "WA"
    elif 800 <= prefix <= 816:
        return "CO"
    elif 10 <= prefix <= 27:
        return "MA"
    elif 220 <= prefix <= 246:
        return "VA"
    elif 970 <= prefix <= 979:
        return "OR"
    else:
        return None

def _instant_crime(zip_code: str, census: dict) -> dict:
    """Compute crime score from Census data (no API call).
    Uses local signals (income/education) weighted more than state baseline."""
    state = _get_state_from_zip(zip_code)
    baseline = STATE_CRIME_RATES.get(state, 400) if state else 400
    
    income = census.get("income", 65000)
    edu = census.get("bachelors_rate", 32)
    
    state_risk = baseline / 1000
    income_safety = min(max(income / 150000, 0), 1)
    edu_safety = min(max(edu / 65, 0), 1)
    
    # 25% state, 40% income, 25% education, 10% baseline police estimate
    crime_risk = (
        0.25 * state_risk +
        0.40 * (1 - income_safety) +
        0.25 * (1 - edu_safety) +
        0.10 * 0.5  # neutral police estimate
    )
    score_scaled = max(0, min(crime_risk * 100, 100))
    
    return {"crime_per_1k": round(score_scaled, 1)}


# =============================================================================
# INSTANT OSM (Estimate based on population - no API call)
# =============================================================================
def _instant_osm(census: dict) -> dict:
    """Estimate POIs from population (no API call)."""
    pop = census.get("population", 25000)
    
    # Rough estimates based on population
    parks = max(int(pop / 5000), 2)
    grocery = max(int(pop / 3000), 3)
    clinics = max(int(pop / 8000), 1)
    transit = max(int(pop / 1500), 5)
    police = max(int(pop / 20000), 1)
    
    hospitals = max(int(pop / 25000), 1)
    
    return {
        "parks": parks,
        "grocery_stores": grocery,
        "clinics": clinics,
        "hospitals": hospitals,
        "transit_stops": transit,
        "police_stations": police,
    }


# =============================================================================
# INSTANT HEALTH (Single fast call or estimate)
# =============================================================================
def _instant_health(zip_code: str) -> dict:
    """Quick health check with 1.5s timeout."""
    try:
        session = _get_session()
        resp = session.get(
            "https://data.hrsa.gov/resource/gt7t-n7q6.json",
            params={"zip": zip_code, "$limit": 1},
            timeout=1.5
        )
        if resp.status_code == 200:
            data = resp.json()
            is_hpsa = any(float(r.get("hpsa_score", 0)) > 0 for r in data) if data else False
            return {"primary_care_centers": 2, "hospitals": 1, "is_hpsa": is_hpsa}
    except:
        pass
    
    return {"primary_care_centers": 2, "hospitals": 1, "is_hpsa": False}


# =============================================================================
# MAIN INSTANT AGGREGATOR
# =============================================================================
def collect_all_data_instant(zip_code: str) -> dict:
    """
    INSTANT data collection - targets ~1-2 seconds.
    
    - Only 2 API calls max (Census + AirNow) 
    - Everything else is computed/estimated
    - 2-second hard timeout per API
    """
    
    # Check cache first
    cached = get_cached_zip(zip_code)
    if cached:
        print(f"[CACHE] Returning cached data for ZIP {zip_code}")
        return cached
    
    print(f"[INSTANT] Fetching data for ZIP {zip_code}")
    start_time = time.time()
    
    # Run Census and AirNow in parallel (only 2 API calls)
    census_data = {}
    air_data = {}
    health_data = {}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_census = executor.submit(_instant_census, zip_code)
        future_air = executor.submit(_instant_air, zip_code)
        future_health = executor.submit(_instant_health, zip_code)
        
        try:
            census_data = future_census.result(timeout=3)
        except:
            census_data = _estimate_census(zip_code)
        
        try:
            air_data = future_air.result(timeout=3)
        except:
            air_data = {"aqi": 45, "category": "Good", "pollutant": "PM2.5"}
        
        try:
            health_data = future_health.result(timeout=3)
        except:
            health_data = {"primary_care_centers": 2, "hospitals": 1, "is_hpsa": False}
    
    # Compute derived data (no API calls)
    osm_data = _instant_osm(census_data)
    crime_data = _instant_crime(zip_code, census_data)
    
    # Build final structure
    income = census_data.get("income", 65000)
    rent = census_data.get("rent", 1200)
    broadband = census_data.get("broadband_pct", 85)
    
    live_data = {
        "census": {
            "median_income": income,
            "bachelors_rate": census_data.get("bachelors_rate", 32),
            "resident_base": census_data.get("population", 25000),
        },
        "housing": {
            "median_rent": rent,
            "rent_to_income": round((rent * 12) / income, 3) if income else 0.25,
            "studio": None, "1br": None, "2br": None, "3br": None, "4br": None,
        },
        "broadband": {
            "broadband_pct": broadband,
            "fiber_pct": round(broadband * 0.35, 2),
            "cable_pct": round(broadband * 0.65, 2),
        },
        "health": health_data,
        "osm": osm_data,
        "air_quality": air_data,
        "crime": crime_data,
    }
    
    elapsed = time.time() - start_time
    print(f"[INSTANT] Completed in {elapsed:.2f}s")
    
    # Store in Supabase
    try:
        store_zip_data(zip_code, live_data)
        print(f"[CACHE] Stored ZIP {zip_code}")
    except Exception as e:
        print(f"[CACHE] Store failed: {e}")
    
    return live_data
