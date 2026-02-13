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

# Min/max for normalization — tuned to realistic US national ranges
# Sources: ACS 2023 national distributions, EPA AQI scale
NORMALIZATION_BOUNDS = {
    "median_income": (25000, 200000),       # bottom ZCTA ~$25k, top ~$200k
    "bachelors_rate": (5.0, 75.0),          # rural low ~5%, affluent suburbs ~75%
    "crime_per_1k": (0.0, 80.0),            # proxy score range (lower is better)
    "primary_care_per_10k": (0.0, 40.0),
    "aqi": (0, 200),                        # EPA AQI scale (lower is better)
    "broadband_pct": (50.0, 100.0),         # most ZCTAs above 50%
    "rent_to_income": (0.10, 0.55),         # HUD: 30%+ is burdened (lower is better)
}
