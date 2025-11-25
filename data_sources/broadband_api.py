# data_sources/broadband_api.py

import requests

def fetch_broadband_data(zip_code: str) -> dict:
    """
    Uses ACS Census Broadband Subscription (B28002) for broadband_pct.
    Fiber/cable percentages estimated from urban density + broadband_pct.
    """

    try:
        # =======================
        # 1) ACS Census Query
        # =======================
        url = (
            "https://api.census.gov/data/2022/acs/acs5"
            f"?get=B28002_004E,B28002_001E&for=zip%20code%20tabulation%20area:{zip_code}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        broadband, total, _ = data[1]

        if not broadband or not total or total == "0":
            return _fallback()

        broadband_pct = round((int(broadband) / int(total)) * 100, 2)

        # =======================
        # 2) Estimate fiber vs cable
        # =======================
        density_factor = _get_density_factor(zip_code)

        # Fiber scaling based on urbanization
        if density_factor > 0.75:      # urban core
            fiber_pct = round(broadband_pct * 0.50, 2)
        elif density_factor > 0.40:    # suburban
            fiber_pct = round(broadband_pct * 0.35, 2)
        else:                           # rural/low-density
            fiber_pct = round(broadband_pct * 0.20, 2)

        cable_pct = round(broadband_pct - fiber_pct, 2)
        if cable_pct < 0:
            cable_pct = 0

        return {
            "broadband_pct": broadband_pct,
            "fiber_pct": fiber_pct,
            "cable_pct": cable_pct
        }

    except Exception as e:
        print("[Census Broadband] ERROR:", e)
        return _fallback()


def _fallback():
    return {"broadband_pct": 0, "fiber_pct": 0, "cable_pct": 0}


def _get_density_factor(zip_code: str) -> float:
    """
    Estimate population density using ACS land area (in square km).
    A normalized 0–1 factor is used for fiber estimation.
    """

    try:
        # ACS PL 2020 land area (in square meters, convert to sq km)
        url = (
            "https://api.census.gov/data/2020/acs/acs5"
            f"?get=ALAND,B01003_001E&for=zip%20code%20tabulation%20area:{zip_code}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        land, pop, _ = data[1]
        if not land or not pop:
            return 0.5

        land_km = int(land) / 1_000_000  # sq km
        pop = int(pop)

        if land_km <= 0:
            return 0.5

        density = pop / land_km  # people per km²

        # Normalize: 0–1 scale (0 rural → 1 dense)
        # 10k per km² = city-like
        factor = min(density / 10000, 1.0)
        return round(factor, 2)

    except Exception:
        return 0.5
