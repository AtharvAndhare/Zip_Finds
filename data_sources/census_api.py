# data_sources/census_api.py
import random
import time
import requests
from config.settings import settings

# =============================
# API KEY (Optional but helps)
# =============================
CENSUS_API_KEY = settings.CENSUS_API_KEY or None

# =============================
# Fallback years (Newest → Oldest)
# =============================
ACS_YEARS = ["2022", "2021", "2020"]


# ============================================================
# SAFE REQUEST WRAPPER (Retries + Timeout + Friendly Fail)
# ============================================================
def _safe_req(url, retries=3, timeout=12):
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            sleep = random.uniform(0.8, 2.0)
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

    return None  # ❗ no valid response across all years


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
# MAIN FETCH FUNCTION
# ============================================================
def fetch_census_data(zip_code: str) -> dict:
    """
    Fetch Census ZIP-level:

    - Median household income  (B19013_001E)
    - Education: % bachelor's or higher (B15003)
    - Weighted resident base (population × household size adjustment)
    """

    # --------------------------------------------------------
    # 1) MEDIAN INCOME
    # --------------------------------------------------------
    inc_resp = _census("B19013_001E", zip_code)
    median_income = _clean(inc_resp[1][0]) if inc_resp else None

    # --------------------------------------------------------
    # 2) EDUCATION (Bachelor's + Postgraduate %)
    # --------------------------------------------------------
    edu_vars = ",".join([
        "B15003_001E",  # total 25+
        "B15003_022E",  # Bachelor's
        "B15003_023E",  # Master's
        "B15003_024E",  # Professional degree
        "B15003_025E"   # Doctorate
    ])
    edu_resp = _census(edu_vars, zip_code)

    bachelors_rate = None
    if edu_resp:
        total = _clean(edu_resp[1][0])
        if total and total > 0:
            bach_plus = sum(_clean(v) or 0 for v in edu_resp[1][1:5])
            bachelors_rate = round((bach_plus / total) * 100, 2)

    # --------------------------------------------------------
    # 3) RESIDENT BASE (Population Weighted by Household Size)
    # --------------------------------------------------------
    pop_resp = _census("B01003_001E", zip_code)
    hh_resp = _census("S1101_C01_002E", zip_code)

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
