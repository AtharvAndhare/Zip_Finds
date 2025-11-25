# data_sources/housing_api.py
import time
from urllib.parse import urlencode
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
def safe_census_get(url, retries=3, timeout=12):
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
# FETCH ZIP DATA FROM MULTIPLE YEARS UNTIL ONE WORKS
# ============================================================
def census_query(vars: str, zip_code: str):
    """
    Query Census API with fallback to multiple years.
    Properly encodes the URL parameters.
    """
    for year in ACS_YEARS:
        try:
            base = f"https://api.census.gov/data/{year}/acs/acs5"
            params = {
                "get": vars,
                "for": f"zip code tabulation area:{zip_code}",
            }
            if CENSUS_API_KEY:
                params["key"] = CENSUS_API_KEY

            # Use urlencode for proper URL encoding
            url = base + "?" + urlencode(params)
            return safe_census_get(url)
        except Exception as e:
            # Try next year if this one fails
            continue
    return None  # all years failed


def fetch_housing_data(zip_code: str) -> dict:
    """
    Fetch housing data from Census API.
    Returns median rent and rent burden ratio.
    """
    try:
        # ===============================================
        # 1) MEDIAN GROSS RENT (B25064_001E)
        # Response format: [["B25064_001E", "state", "zip code tabulation area"], ["value", ...]]
        # Value is at index 0 of the data row
        # ===============================================
        rent_resp = census_query("B25064_001E", zip_code)
        if not rent_resp:
            print(f"[Census Housing] WARNING: No rent data found for ZIP {zip_code}")
        median_rent = _safe_extract(rent_resp, 0) if rent_resp else None

        # ===============================================
        # 2) RENT BURDEN (B25070: % of income → rent)
        #    Query includes total (001E) and categories (002E-010E)
        #    B25070_001E = Total, B25070_002E-010E = burden categories
        # ===============================================
        # Query from 1-10 (001E through 010E) - includes total + 9 categories
        burden_vars = ",".join([f"B25070_{str(i).zfill(3)}E" for i in range(1, 11)])
        burden_resp = census_query(burden_vars, zip_code)
        if not burden_resp:
            print(f"[Census Housing] WARNING: No rent burden data found for ZIP {zip_code}")
        else:
            # Debug: Check response structure
            if len(burden_resp) > 1 and len(burden_resp[1]) > 0:
                print(f"[Census Housing] DEBUG: Rent burden response received for ZIP {zip_code}, row length: {len(burden_resp[1])}")
        rent_burden_pct = _process_rent_burden(burden_resp) if burden_resp else None
        if rent_burden_pct is None and burden_resp:
            print(f"[Census Housing] WARNING: Rent burden processing returned None for ZIP {zip_code}")

        return {
            "median_rent": median_rent,
            "studio": None,
            "1br": None,
            "2br": None,
            "3br": None,
            "4br": None,
            "rent_to_income": rent_burden_pct,
        }
    except Exception as e:
        print(f"[Census Housing] ERROR for ZIP {zip_code}: {e}")
        return {
            "median_rent": None,
            "studio": None,
            "1br": None,
            "2br": None,
            "3br": None,
            "4br": None,
            "rent_to_income": None,
        }


def _safe_extract(resp, idx):
    try:
        if not resp or len(resp) < 2:
            return None
        value = resp[1][idx]
        if value in (None, "", "null"):
            return None
        v = float(value)
        # treat Census suppression codes as None
        if v < 0 or v > 100000:   # unrealistic medians
            return None
        return v
    except:
        return None


def _process_rent_burden(resp):
    """
    Process rent burden response from Census API table B25070.
    Response format: [["B25070_001E", ..., "state", "zip"], ["value", ...]]
    B25070_001E = Total, B25070_002E-B25070_010E = categories (rent as % of income)
    """
    try:
        if not resp or len(resp) < 2:
            return None
        
        # Extract data row (skip header row)
        data_row = resp[1]
        # Remove last 2 columns (geo identifiers: state, zip code tabulation area)
        row = data_row[:-2] if len(data_row) > 2 else data_row
        
        if len(row) == 0:
            return None
        
        # Convert to numbers, handling nulls and negative values (Census uses negatives for null)
        numbers = []
        for x in row:
            try:
                if x is None or x == "null" or x == "":
                    numbers.append(0)
                else:
                    val = int(x) if str(x).lstrip('-').isdigit() else 0
                    # Census null codes are large negative numbers
                    if val < 0 or val > 999999:
                        numbers.append(0)
                    else:
                        numbers.append(val)
            except (ValueError, TypeError):
                numbers.append(0)
        
        if len(numbers) == 0:
            return None
        
        # First value is total (B25070_001E), rest are categories
        total = numbers[0] if numbers[0] > 0 else sum(numbers[1:])
        
        if total == 0:
            # If total is 0, try using sum of categories
            total = sum(numbers[1:]) if len(numbers) > 1 else 0
            if total == 0:
                return None
        
        # Use categories (indices 1 onwards, but we queried 001-016, so we have 16 values)
        # B25070 categories represent rent burden ranges
        # We'll use a weighted average of the burden ranges
        categories = numbers[1:] if len(numbers) > 1 else numbers
        
        # Map categories to estimated burden percentages (midpoint of each range)
        # B25070_002E: Less than 10.0% → 5%
        # B25070_003E: 10.0 to 14.9% → 12.5%
        # B25070_004E: 15.0 to 19.9% → 17.5%
        # B25070_005E: 20.0 to 24.9% → 22.5%
        # B25070_006E: 25.0 to 29.9% → 27.5%
        # B25070_007E: 30.0 to 34.9% → 32.5%
        # B25070_008E: 35.0 to 39.9% → 37.5%
        # B25070_009E: 40.0 to 49.9% → 45%
        # B25070_010E: 50.0% or more → 60%
        category_weights = [5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 45, 60]
        
        # Use available categories (should be 9)
        num_cats = min(len(categories), len(category_weights))
        weighted_sum = sum(
            categories[i] * category_weights[i] 
            for i in range(num_cats)
        )
        
        avg_burden = weighted_sum / total if total > 0 else None
        return avg_burden / 100 if avg_burden is not None else None  # convert to ratio

    except (ValueError, IndexError, TypeError, ZeroDivisionError) as e:
        print(f"[Census Housing] DEBUG: Error processing rent burden: {type(e).__name__}: {e}")
        return None
