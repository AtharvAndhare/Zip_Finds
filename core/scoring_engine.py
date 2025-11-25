# core/scoring_engine.py

from config.settings import settings
from core.calculator import _normalize


def safe_number(value, default=0.0):
    """
    Converts value to float safely.
    Prevents errors when the API returns None or strings.
    """
    try:
        if value is None or value == "null":
            return default
        return float(value)
    except Exception:
        return default


def compute_scores(data: dict) -> dict:
    # =========================================================================
    # EXTRACT RAW DATA
    # =========================================================================
    census = data.get("census", {}) or {}
    health = data.get("health", {}) or {}
    crime = data.get("crime", {}) or {}
    housing = data.get("housing", {}) or {}
    broadband = data.get("broadband", {}) or {}
    air = data.get("air_quality", {}) or {}
    osm = data.get("osm", {}) or {}

    #SAFETY SCORE
   
    crime_rate = safe_number(crime.get("crime_per_1k", 0))
    safety = _normalize(crime_rate, "crime_per_1k", invert=True)

    
    # HEALTH SCORE
   
    primary_care_points = min(safe_number(health.get("primary_care_centers", 0)) * 3, 40)
    hospital_points = min(safe_number(health.get("hospitals", 0)) * 10, 30)
    raw_health = primary_care_points + hospital_points

    if health.get("is_hpsa", False):
        raw_health -= 15

    health_score = min(max(raw_health * 2.5, 0), 100)

    
    # EDUCATION SCORE
    
    bachelors = safe_number(census.get("bachelors_rate", 0))
    education = _normalize(bachelors, "bachelors_rate")

  
    # ECONOMIC OPPORTUNITY
   
    median_income = safe_number(census.get("median_income", 0))
    income_score = _normalize(median_income, "median_income")

    economic = round((education + income_score) / 2.0, 1)


    # 5. HOUSING AFFORDABILITY (Census-based)
   
    median_rent = safe_number(housing.get("median_rent", 0))
    rent_burden = housing.get("rent_to_income")  # already a ratio 0–1

    # 5A. Prefer rent burden if present from Census B25070
    if rent_burden is not None and rent_burden > 0:
        housing_aff = _normalize(rent_burden, "rent_to_income", invert=True)
    else:
        # 5B. Fallback: derive rent burden from income & rent
        rent_to_income = (
            median_rent / median_income if median_income > 0 else 0.6
        )
        rent_to_income = safe_number(rent_to_income)
        housing_aff = _normalize(rent_to_income, "rent_to_income", invert=True)

    
    # DIGITAL ACCESS

    broadband_pct = safe_number(broadband.get("broadband_pct", 0))
    digital = _normalize(broadband_pct, "broadband_pct")


    #ENVIRONMENT (AIR QUALITY)
   
    aqi = safe_number(air.get("aqi", 0))
    environment = _normalize(aqi, "aqi", invert=True)

    
    # ACCESSIBILITY (OSM Points)
   
    parks = safe_number(osm.get("parks", 0))
    grocery = safe_number(osm.get("grocery_stores", 0))
    clinics = safe_number(osm.get("clinics", 0))
    transit = safe_number(osm.get("transit_stops", 0))

    poi_total = parks * 3 + grocery * 2 + clinics * 4 + transit * 1
    accessibility = min(round((poi_total / 200) * 100, 1), 100)


    # COLLECT METRIC SCORES
   
    scores = {
        "Safety": round(safety, 1),
        "Health": round(health_score, 1),
        "Education": round(education, 1),
        "EconomicOpportunity": round(economic, 1),
        "HousingAffordability": round(housing_aff, 1),
        "DigitalAccess": round(digital, 1),
        "Environment": round(environment, 1),
        "Accessibility": round(accessibility, 1),
    }

    #OVERALL SCORE (WEIGHTED AVERAGE)

    weights = {
        "Safety": settings.SAFETY_WEIGHT,
        "Health": settings.HEALTH_WEIGHT,
        "Education": settings.EDUCATION_WEIGHT,
        "EconomicOpportunity": settings.ECONOMIC_WEIGHT,
        "HousingAffordability": settings.HOUSING_WEIGHT,
        "DigitalAccess": settings.DIGITAL_ACCESS_WEIGHT,
        "Environment": settings.ENVIRONMENT_WEIGHT,
        "Accessibility": settings.ACCESSIBILITY_WEIGHT,
    }

    weighted_sum = 0.0
    weight_total = 0.0

    for metric, value in scores.items():
        w = float(weights.get(metric, 1.0))
        weighted_sum += value * w
        weight_total += w

    overall = weighted_sum / max(weight_total, 0.00001)
    scores["OverallCivicScore"] = round(overall, 1)

    return scores
