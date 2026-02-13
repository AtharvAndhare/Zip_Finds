# data_sources/broadband_api.py

import functools
import requests
from concurrent.futures import ThreadPoolExecutor
from config.settings import settings

# Use Census API key if available
CENSUS_KEY = settings.CENSUS_API_KEY or None

# Shared session for connection pooling
_session = None

def _get_session():
    """Reuse HTTP session for connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


# ============================================================
# SAFE REQUEST (Connection Pooling + Timeout)
# ============================================================
def _safe_json(url):
    """OPTIMIZED: Uses connection pooling."""
    try:
        session = _get_session()
        resp = session.get(url, timeout=8)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ============================================================
# PUBLIC: FETCH BROADBAND METRICS (CACHED)
# ============================================================
@functools.lru_cache(maxsize=500)
def fetch_broadband_data(zip_code: str) -> dict:
    """
    1) Fetch broadband subscription rate (ACS B28002)
    2) Estimate fiber/cable only if broadband is known
    3) Use ALAND + population to estimate fiber share
    """

    broadband_pct = _fetch_broadband_pct(zip_code)

    # If we cannot get broadband reliably → don't estimate
    if broadband_pct is None:
        return {
            "broadband_pct": None,
            "fiber_pct": None,
            "cable_pct": None
        }

    # Estimate fiber & cable only if broadband_pct > 0
    density_factor = _get_density_factor(zip_code)

    # Fiber estimation rules
    if density_factor > 0.75:      # dense urban
        fiber_pct = broadband_pct * 0.50
    elif density_factor > 0.40:    # suburban
        fiber_pct = broadband_pct * 0.35
    else:                          # rural
        fiber_pct = broadband_pct * 0.20

    fiber_pct = round(fiber_pct, 2)

    cable_pct = round(broadband_pct - fiber_pct, 2)
    cable_pct = max(cable_pct, 0)

    return {
        "broadband_pct": broadband_pct,
        "fiber_pct": fiber_pct,
        "cable_pct": cable_pct
    }


# ============================================================
# STEP 1: Reliable broadband subscription % (ACS B28002)
# ============================================================
def _fetch_broadband_pct(zip_code: str):
    """
    Returns broadband subscription percentage or None if unknown.
    """

    vars = "B28002_004E,B28002_001E"  # broadband households / total households

    # Construct URL manually (avoid encoding ambiguity)
    url = (
        f"https://api.census.gov/data/2023/acs/acs5"
        f"?get={vars}&for=zip%20code%20tabulation%20area:{zip_code}"
    )
    if CENSUS_KEY:
        url += f"&key={CENSUS_KEY}"

    data = _safe_json(url)
    if not data or len(data) < 2:
        return None

    try:
        broadband, total, *_ = data[1]
        broadband, total = int(broadband), int(total)

        if total == 0:
            return None

        pct = round((broadband / total) * 100, 2)

        # If pct is 0 → treat as unknown, not zero
        return pct if pct > 0 else None
    except Exception:
        return None


# ============================================================
# STEP 2: Estimate density factor (ALAND + population, ACS)
# ============================================================
def _get_density_factor(zip_code: str):
    """
    Normalized 0–1 score estimating residential density.
    Used only to scale fiber.
    """

    vars = "ALAND,B01003_001E"  # land area + population
    url = (
        f"https://api.census.gov/data/2023/acs/acs5"
        f"?get={vars}&for=zip%20code%20tabulation%20area:{zip_code}"
    )
    if CENSUS_KEY:
        url += f"&key={CENSUS_KEY}"

    data = _safe_json(url)
    if not data or len(data) < 2:
        return 0.5  # neutral fallback

    try:
        land, pop, *_ = data[1]
        land = int(land) / 1_000_000  # sq km
        pop = int(pop)

        if land <= 0:
            return 0.5

        density = pop / land  # people/km²

        # Normalize: anything above 10k/km² considered max dense
        factor = min(density / 10000, 1.0)
        return round(factor, 2)
    except Exception:
        return 0.5
