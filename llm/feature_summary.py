# llm/feature_summary.py

def describe_metric(name: str, score: float) -> str:
    if score >= 85:
        grade = "Excellent"
    elif score >= 70:
        grade = "Strong"
    elif score >= 50:
        grade = "Moderate"
    elif score >= 30:
        grade = "Weak"
    else:
        grade = "Very Low"

    return f"{name}: {score}/100 ({grade})"


def build_feature_summary(scores: dict) -> str:
    summary_lines = []

    for key, value in scores.items():
        if key == "OverallCivicScore":
            continue
        summary_lines.append(describe_metric(key, value))

    return "\n".join(summary_lines)


def _money(value) -> str:
    return f"${value:,}" if value is not None else "N/A"


def _pct(value) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%" if value > 1 else f"{value * 100:.1f}%"


def build_raw_data_summary(raw_data: dict | None, location: dict | None = None) -> str:
    """Format structured ZIP metrics for LLM context."""
    if not raw_data:
        return "Raw metrics: unavailable"

    lines = []
    if location and location.get("lat") is not None and location.get("lon") is not None:
        lines.append(f"Coordinates: {location['lat']:.4f}, {location['lon']:.4f}")

    census = raw_data.get("census") or {}
    housing = raw_data.get("housing") or {}
    broadband = raw_data.get("broadband") or {}
    health = raw_data.get("health") or {}
    crime = raw_data.get("crime") or {}
    osm = raw_data.get("osm") or {}
    air = raw_data.get("air_quality") or {}

    pop = census.get("resident_base")
    pop_str = f"{pop:,}" if pop is not None else "N/A"

    lines.extend([
        "",
        "Census & Economy:",
        f"- Median income: {_money(census.get('median_income'))}",
        f"- Population: {pop_str}",
        f"- Bachelor's degree rate: {_pct(census.get('bachelors_rate'))}",
        "",
        "Housing:",
        f"- Median rent: {_money(housing.get('median_rent'))}",
        f"- Rent-to-income ratio: {_pct(housing.get('rent_to_income'))}",
        "",
        "Broadband:",
        f"- Coverage: {_pct(broadband.get('broadband_pct'))}",
        f"- Fiber: {_pct(broadband.get('fiber_pct'))}",
        f"- Cable: {_pct(broadband.get('cable_pct'))}",
        "",
        "Health:",
        f"- Hospitals (HRSA): {health.get('hospitals', 'N/A')}",
        f"- Primary care centers: {health.get('primary_care_centers', 'N/A')}",
        f"- HPSA designation: {'Yes' if health.get('is_hpsa') else 'No'}",
        "",
        "Safety:",
        f"- Crime rate: {crime.get('crime_per_1k', 'N/A')} per 1k residents",
        "",
        "Points of Interest (7 km radius):",
        f"- Parks: {osm.get('parks', 'N/A')}",
        f"- Grocery stores: {osm.get('grocery_stores', 'N/A')}",
        f"- Clinics: {osm.get('clinics', 'N/A')}",
        f"- Hospitals: {osm.get('hospitals', 'N/A')}",
        f"- Transit stops: {osm.get('transit_stops', 'N/A')}",
        f"- Police stations: {osm.get('police_stations', 'N/A')}",
        "",
        "Environment:",
        f"- AQI: {air.get('aqi', 'N/A')}",
        f"- Category: {air.get('category', 'N/A')}",
        f"- Primary pollutant: {air.get('pollutant', 'N/A')}",
    ])

    return "\n".join(lines)
