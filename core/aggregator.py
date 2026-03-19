# core/aggregator.py

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from data_sources.census_api import fetch_census_data
from data_sources.health_api import fetch_health_data
from data_sources.crime_api import fetch_crime_data, compute_crime_score
from data_sources.osm_api import fetch_osm_poi_data
from data_sources.housing_api import fetch_housing_data
from data_sources.broadband_api import fetch_broadband_data
from data_sources.air_quality_api import fetch_air_quality_data

from db.zip_cache import get_cached_zip, store_zip_data

# Import instant aggregator for fast mode
from core.instant_aggregator import collect_all_data_instant


def collect_all_data(zip_code: str, fast_mode: bool = False) -> dict:
    """
    Unified data collector with Supabase caching.
    
    Args:
        zip_code: The ZIP code to fetch data for
        fast_mode: If True, uses instant aggregator (~0.5-1.5s, estimated data)
                   If False (default), uses full API calls (~5-15s but accurate)
    
    Steps:
      1) Check cache first.
      2) If cached → return quickly.
      3) If fast_mode → use instant aggregator (1-2 seconds)
      4) If not → fetch APIs IN PARALLEL (5-15 seconds, more detailed)
      5) Store result into Supabase.
      6) Return final aggregated dataset.
    """

    # =========================================
    # STEP 1: Try Cache First
    # =========================================
    cached = get_cached_zip(zip_code)
    if cached:
        print(f"[CACHE] Returning cached data for ZIP {zip_code}")
        return cached

    # =========================================
    # STEP 2: Use Fast Mode if enabled (DEFAULT)
    # =========================================
    if fast_mode:
        return collect_all_data_instant(zip_code)

    # =========================================
    # STEP 2: Fetch Live Data IN PARALLEL
    # =========================================
    print(f"[LIVE] Fetching fresh data for ZIP {zip_code}")
    start_time = time.time()

    # Define independent API calls (crime is computed later to avoid duplicate calls)
    api_tasks = {
        "census": lambda: fetch_census_data(zip_code),
        "health": lambda: fetch_health_data(zip_code),
        "osm": lambda: fetch_osm_poi_data(zip_code),
        "housing": lambda: fetch_housing_data(zip_code),
        "broadband": lambda: fetch_broadband_data(zip_code),
        "air_quality": lambda: fetch_air_quality_data(zip_code),
    }

    live_data = {}

    # Execute all API calls in parallel using ThreadPool
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_key = {executor.submit(task): key for key, task in api_tasks.items()}
        
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                live_data[key] = future.result()
            except Exception as e:
                print(f"[API] ERROR fetching {key}: {e}")
                live_data[key] = {}

    # =========================================
    # STEP 3: Compute Crime Score (reuse census + osm data)
    # =========================================
    # This avoids duplicate API calls - crime_api was calling census + osm again!
    live_data["crime"] = compute_crime_score(
        zip_code,
        census_data=live_data.get("census", {}),
        osm_data=live_data.get("osm", {})
    )

    elapsed = time.time() - start_time
    print(f"[LIVE] All APIs fetched in {elapsed:.2f}s (parallel)")

    # =========================================
    # STEP 4: Store into Supabase
    # =========================================
    try:
        store_zip_data(zip_code, live_data)
        print(f"[CACHE] Stored ZIP {zip_code} data in Supabase")
    except Exception as e:
        print(f"[CACHE] WARNING: Failed to cache ZIP {zip_code}: {e}")

    # =========================================
    # STEP 5: Return Live Output
    # =========================================
    return live_data
