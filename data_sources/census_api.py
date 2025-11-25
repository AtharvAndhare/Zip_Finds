# data_sources/census_api.py

import time
import requests
from config.settings import settings

# =============================
# API KEY (optional, but helps)
# =============================
CENSUS_API_KEY = settings.CENSUS_API_KEY or None

# =============================
# Fallback years (Newest → Oldest)
# =============================
ACS_YEARS = ["2022", "2021", "2020"]


# ============================================================
# SAFE REQUEST WRAPPER (Retries + Timeout)
# ============================================================
def _safe_req(url, retries=3, timeout=12):
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.6)
            else:
                raise


# ============================================================
# GENERIC CENSUS QUERY WITH YEAR FALLBACK
# ============================================================
def _census(vars: str, zip_code: str):
    for year in ACS_YEARS:
        try:
            base = f"https://api.census.gov/data/{year}/acs/acs5"
            params = {
                "get": vars,
                "for": f"zip code tabulation area:{zip_code}",
            }
            if CENSUS_API_KEY:
                params["key"] = CENSUS_API_KEY

            # Build URL manually (avoids urlencode issues)
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{base}?{param_str}"
            return _safe_req(url)
        except Exception:
            continue
    return None


# ============================================================
# MAIN FETCH FUNCTION
# ============================================================
def fetch_census_data(zip_code: str) -> dict:
    """
    Fetch Census ZIP-level:

    - Median household income  (B19013_001E)
    - Education: % bachelor's or higher (B15003)
    - Weighted population / resident base (option C)
    """

    # --------------------------------------------------------
    # 1) MEDIAN INCOME
    # --------------------------------------------------------
    inc_resp = _census("B19013_001E", zip_code)
    median_income = None
    if inc_resp and len(inc_resp) > 1:
        try:
            median_income = float(inc_resp[1][0])
        except Exception:
            median_income = None

    # --------------------------------------------------------
    # 2) EDUCATION B15003 (Degrees Count + Total Base)
    # --------------------------------------------------------
    edu_vars = ",".join([
        "B15003_001E",  # total 25+
        "B15003_022E",  # Bachelor's
        "B15003_023E",  # Master's
        "B15003_024E",  # Professional degree
        "B15003_025E"   # Doctorate
    ])
    edu_resp = _census(edu_vars, zip_code)

    bachelors_rate = 0.0
    if edu_resp and len(edu_resp) > 1:
        try:
            total = float(edu_resp[1][0])  # total population 25+
            bachelors_plus = sum(float(v) for v in edu_resp[1][1:5])
            if total > 0:
                bachelors_rate = round((bachelors_plus / total) * 100, 2)
        except Exception:
            bachelors_rate = 0.0

    # --------------------------------------------------------
    # 3) RESIDENT BASE (Weighted Population)
    # total_population × (household_size / 2.5)
    # --------------------------------------------------------
    pop_resp = _census("B01003_001E", zip_code)  # total population
    hh_resp = _census("S1101_C01_002E", zip_code)  # average household size

    total_pop = None
    hh_size = 2.5  # baseline fallback

    if pop_resp and len(pop_resp) > 1:
        try:
            total_pop = float(pop_resp[1][0])
        except Exception:
            total_pop = None

    if hh_resp and len(hh_resp) > 1:
        try:
            hh_size = float(hh_resp[1][0])
        except Exception:
            hh_size = hh_size  # keep fallback

    resident_base = None
    if total_pop and total_pop > 0:
        # Weighted adjustment
        resident_base = round(total_pop * (hh_size / 2.5))

    # --------------------------------------------------------
    # RETURN PACKAGE
    # --------------------------------------------------------
    return {
        "median_income": median_income,
        "bachelors_rate": bachelors_rate,
        "resident_base": resident_base,
    }
