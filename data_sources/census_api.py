# data_sources/census_api.py

import functools
import random
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from config.settings import settings

# =============================
# API KEY (Optional but helps)
# =============================
CENSUS_API_KEY = settings.CENSUS_API_KEY or None

# =============================
# Fallback years (Newest → Oldest)
# =============================
ACS_YEARS = ["2022", "2021", "2020"]

# =============================
# Shared session for connection pooling
# =============================
_session = None

def _get_session():
    """Reuse HTTP session for connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


# ============================================================
# SAFE REQUEST WRAPPER (Retries + Timeout + Connection Reuse)
# ============================================================
def _safe_req(url, retries=2, timeout=10):
    """
    OPTIMIZED: Reduced retries (2 vs 3), shorter timeout, connection pooling.
    """
    session = _get_session()
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt < retries - 1:
                sleep = random.uniform(0.3, 0.8)  # Reduced sleep time
                time.sleep(sleep)
    return None


# ============================================================
# GENERIC CENSUS QUERY WITH YEAR FALLBACK
# ============================================================
def _census(vars: str, zip_code: str):
    """
    Try multiple ACS years until one returns valid data.
    Returns parsed JSON or None.
    """
    for year in ACS_YEARS:
        base = f"https://api.census.gov/data/{year}/acs/acs5"
        params = {
            "get": vars,
            "for": f"zip code tabulation area:{zip_code}",
        }
        if CENSUS_API_KEY:
            params["key"] = CENSUS_API_KEY

        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{base}?{query}"

        data = _safe_req(url)
        if data and len(data) > 1:
            return data

    return None  # no valid response across all years


# ============================================================
# CLEAN NUMERIC HELPER
# ============================================================
def _clean(value):
    """
    Normalizes Census values: converts 'null', '' and weird values.
    Returns float or None.
    """
    try:
        if value is None:
            return None
        if value in ["", "null", "-666666666", "-666666"]:
            return None
        return float(value)
    except Exception:
        return None


# ============================================================
# MAIN FETCH FUNCTION (OPTIMIZED with Parallel Calls + Cache)
# ============================================================
@functools.lru_cache(maxsize=500)
def fetch_census_data(zip_code: str) -> dict:
    """
    Fetch Census ZIP-level data.
    
    OPTIMIZED:
    - LRU cache prevents redundant fetches for same ZIP
    - All 4 Census queries run IN PARALLEL (saves ~60% time)
    - Connection pooling for faster HTTP
    
    Returns:
        - median_income: Median household income (B19013_001E)
        - bachelors_rate: % with bachelor's or higher (B15003)
        - resident_base: Population weighted by household size
    """
    
    # Define all Census variable queries
    edu_vars = ",".join([
        "B15003_001E",  # total 25+
        "B15003_022E",  # Bachelor's
        "B15003_023E",  # Master's
        "B15003_024E",  # Professional degree
        "B15003_025E"   # Doctorate
    ])
    
    # Run all 4 Census queries in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_income = executor.submit(_census, "B19013_001E", zip_code)
        future_edu = executor.submit(_census, edu_vars, zip_code)
        future_pop = executor.submit(_census, "B01003_001E", zip_code)
        future_hh = executor.submit(_census, "S1101_C01_002E", zip_code)
        
        inc_resp = future_income.result()
        edu_resp = future_edu.result()
        pop_resp = future_pop.result()
        hh_resp = future_hh.result()

    # --------------------------------------------------------
    # 1) MEDIAN INCOME
    # --------------------------------------------------------
    median_income = _clean(inc_resp[1][0]) if inc_resp else None

    # --------------------------------------------------------
    # 2) EDUCATION (Bachelor's + Postgraduate %)
    # --------------------------------------------------------
    bachelors_rate = None
    if edu_resp:
        total = _clean(edu_resp[1][0])
        if total and total > 0:
            bach_plus = sum(_clean(v) or 0 for v in edu_resp[1][1:5])
            bachelors_rate = round((bach_plus / total) * 100, 2)

    # --------------------------------------------------------
    # 3) RESIDENT BASE (Population Weighted by Household Size)
    # --------------------------------------------------------
    total_pop = _clean(pop_resp[1][0]) if pop_resp else None
    hh_size = _clean(hh_resp[1][0]) if hh_resp else 2.5  # fallback

    resident_base = None
    if total_pop and total_pop > 0:
        resident_base = round(total_pop * (hh_size / 2.5))

    # --------------------------------------------------------
    # RETURN PACKAGE (Always consistent keys)
    # --------------------------------------------------------
    return {
        "median_income": median_income,
        "bachelors_rate": bachelors_rate,
        "resident_base": resident_base,
    }
