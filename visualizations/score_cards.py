# visualizations/score_cards.py

import streamlit as st
from config.constants import NORMALIZATION_BOUNDS
from config.settings import settings


def safe_number(value, default=0.0):
    """Safely convert value to float."""
    try:
        if value is None or value == "null":
            return default
        return float(value)
    except Exception:
        return default


def normalize(value, metric_name, invert=False):
    """Normalize a value to 0-100 scale using bounds from constants."""
    if value is None:
        return 50.0
    
    try:
        value = float(value)
    except (ValueError, TypeError):
        return 50.0
    
    # Get bounds from constants
    if metric_name in NORMALIZATION_BOUNDS:
        vmin, vmax = NORMALIZATION_BOUNDS[metric_name]
    else:
        vmin, vmax = 0, 100
    
    if vmax == vmin:
        return 50.0
    
    # Clamp value
    value_clamped = max(min(value, vmax), vmin)
    
    # Normalize to 0-1
    score = (value_clamped - vmin) / (vmax - vmin)
    
    # Invert if needed
    if invert:
        score = 1 - score
    
    # Scale to 0-100
    return score * 100


def compute_scores_from_raw(raw_data: dict) -> dict:
    """Compute scores directly from raw_data using the same math as scoring_engine."""
    census = raw_data.get("census", {}) or {}
    health = raw_data.get("health", {}) or {}
    crime = raw_data.get("crime", {}) or {}
    housing = raw_data.get("housing", {}) or {}
    broadband = raw_data.get("broadband", {}) or {}
    air = raw_data.get("air_quality", {}) or {}
    osm = raw_data.get("osm", {}) or {}
    
    # 1. SAFETY SCORE
    crime_rate = safe_number(crime.get("crime_per_1k", 0))
    safety = normalize(crime_rate, "crime_per_1k", invert=True)
    
    # 2. HEALTH SCORE
    primary_care_points = min(safe_number(health.get("primary_care_centers", 0)) * 3, 40)
    hospital_points = min(safe_number(health.get("hospitals", 0)) * 10, 30)
    raw_health = primary_care_points + hospital_points
    
    if health.get("is_hpsa", False):
        raw_health -= 15
    
    health_score = min(max(raw_health * 2.5, 0), 100)
    
    # 3. EDUCATION SCORE
    bachelors = safe_number(census.get("bachelors_rate", 0))
    education = normalize(bachelors, "bachelors_rate")
    
    # 4. ECONOMIC OPPORTUNITY
    median_income = safe_number(census.get("median_income", 0))
    income_score = normalize(median_income, "median_income")
    economic = round((education + income_score) / 2.0, 1)
    
    # 5. HOUSING AFFORDABILITY
    median_rent = safe_number(housing.get("median_rent", 0))
    rent_burden = housing.get("rent_to_income")
    
    if rent_burden is not None and rent_burden > 0:
        housing_aff = normalize(rent_burden, "rent_to_income", invert=True)
    else:
        rent_to_income = (median_rent / median_income if median_income > 0 else 0.6)
        rent_to_income = safe_number(rent_to_income)
        housing_aff = normalize(rent_to_income, "rent_to_income", invert=True)
    
    # 6. DIGITAL ACCESS
    broadband_pct = safe_number(broadband.get("broadband_pct", 0))
    digital = normalize(broadband_pct, "broadband_pct")
    
    # 7. ENVIRONMENT
    aqi = safe_number(air.get("aqi", 0))
    environment = normalize(aqi, "aqi", invert=True)
    
    # 8. ACCESSIBILITY
    parks = safe_number(osm.get("parks", 0))
    grocery = safe_number(osm.get("grocery_stores", 0))
    clinics = safe_number(osm.get("clinics", 0))
    transit = safe_number(osm.get("transit_stops", 0))
    poi_total = parks * 3 + grocery * 2 + clinics * 4 + transit * 1
    accessibility = min(round((poi_total / 200) * 100, 1), 100)
    
    # Collect scores
    metric_scores = {
        "Safety": round(safety, 1),
        "Health": round(health_score, 1),
        "Education": round(education, 1),
        "EconomicOpportunity": round(economic, 1),
        "HousingAffordability": round(housing_aff, 1),
        "DigitalAccess": round(digital, 1),
        "Environment": round(environment, 1),
        "Accessibility": round(accessibility, 1),
    }
    
    # Calculate overall weighted score
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
    
    for metric, value in metric_scores.items():
        w = float(weights.get(metric, 1.0))
        weighted_sum += value * w
        weight_total += w
    
    overall = weighted_sum / max(weight_total, 0.00001)
    metric_scores["OverallCivicScore"] = round(overall, 1)
    
    return metric_scores


def render_scorecard(scores: dict, raw_data: dict, zip_code: str) -> dict:
    """
    Render a dynamic scorecard showing computed scores and underlying raw data.
    Computes scores directly from raw_data using math.
    
    Args:
        scores: Dictionary of computed scores (from compute_scores) - not used, computed fresh
        raw_data: Dictionary of raw API data (from collect_all_data)
        zip_code: ZIP code being analyzed
    """
    # Compute scores directly from raw_data using math
    computed_scores = compute_scores_from_raw(raw_data)
    
    st.caption(f"ZIP {zip_code} | Each metric normalized to 0-100 from raw data")

    overall = computed_scores.get("OverallCivicScore", 0)
    metric_scores = {k: v for k, v in computed_scores.items() if k != "OverallCivicScore"}

    if not computed_scores or len(computed_scores) == 0:
        st.warning("No scores computed. Check raw data collection.")
        return

    st.metric("Overall Civic Score", f"{overall:.1f} / 100")

    st.markdown("#### Individual Metrics")

    mcols = st.columns(4)

    # Each entry: (display_name, source_dict_key, raw_key, format_fn)
    # format_fn turns the raw value into a readable string
    metric_raw_map = {
        "Safety": ("crime", "crime_per_1k",
                   lambda v: f"Crime rate: {v:.1f} per 1k"),
        "Health": ("health", None,
                   None),
        "Education": ("census", "bachelors_rate",
                      lambda v: f"Bachelor's: {v:.1f}%"),
        "EconomicOpportunity": ("census", "median_income",
                                lambda v: f"Income: ${v:,.0f}"),
        "HousingAffordability": ("housing", "rent_to_income",
                                 lambda v: f"Rent-to-income: {v*100:.1f}%"),
        "DigitalAccess": ("broadband", "broadband_pct",
                          lambda v: f"Broadband: {v:.1f}%"),
        "Environment": ("air_quality", "aqi",
                        lambda v: f"AQI: {v:.0f}"),
        "Accessibility": ("osm", None,
                          None),
    }

    items = list(metric_scores.items())
    for idx, (metric_name, score_value) in enumerate(items):
        with mcols[idx % 4]:
            st.metric(metric_name, f"{score_value:.1f}")

            entry = metric_raw_map.get(metric_name)
            if entry:
                src_key, raw_key, fmt_fn = entry
                source_data = raw_data.get(src_key, {}) or {}

                if raw_key and raw_key in source_data and fmt_fn:
                    raw_value = source_data[raw_key]
                    if raw_value is not None:
                        try:
                            st.caption(fmt_fn(float(raw_value)))
                        except (ValueError, TypeError):
                            st.caption(str(raw_value))
                elif metric_name == "Health":
                    pc = source_data.get("primary_care_centers", 0)
                    hosp = source_data.get("hospitals", 0)
                    st.caption(f"PC: {pc}, Hosp: {hosp}")
                elif metric_name == "Accessibility":
                    parks = source_data.get("parks", 0)
                    grocery = source_data.get("grocery_stores", 0)
                    transit = source_data.get("transit_stops", 0)
                    st.caption(f"Parks: {parks}, Groc: {grocery}, Trans: {transit}")
    
    # Return computed scores for use in other components
    return computed_scores

