# config/constants.py

METRIC_NAMES = [
    "Safety",
    "Health",
    "Education",
    "EconomicOpportunity",
    "HousingAffordability",
    "DigitalAccess",
    "Environment",
]

# Min/max for normalization (you can tune when you plug real APIs)
NORMALIZATION_BOUNDS = {
    "median_income": (20000, 150000),
    "bachelors_rate": (0.0, 70.0),
    "crime_per_1k": (0.0, 150.0),          # lower is better
    "primary_care_per_10k": (0.0, 40.0),
    "aqi": (0, 200),                        # lower is better
    "broadband_pct": (40.0, 100.0),
    "rent_to_income": (0.1, 0.6),          # lower is better
}
