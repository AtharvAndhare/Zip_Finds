# core/aggregator.py

from data_sources.census_api import fetch_census_data
from data_sources.health_api import fetch_health_data
from data_sources.crime_api import fetch_crime_data
from data_sources.osm_api import fetch_osm_poi_data  
from data_sources.housing_api import fetch_housing_data
from data_sources.broadband_api import fetch_broadband_data
from data_sources.air_quality_api import fetch_air_quality_data

from db.zip_cache import get_cached_zip, store_zip_data


def collect_all_data(zip_code: str) -> dict:
    """
    Unified data collector with Supabase caching.
    Steps:
      1) Check cache first.
      2) If cached → return quickly.
      3) If not → fetch each data source live.
      4) Store result into Supabase.
      5) Return final aggregated dataset.
    """

   
    # STEP 1: Try Cache First 
   
    cached = get_cached_zip(zip_code)
    if cached:
        print(f"[CACHE] Returning cached data for ZIP {zip_code}")
        return cached

 
    # STEP 2: Fetch Live Data 
 
    print(f"[LIVE] Fetching fresh data for ZIP {zip_code}")

    live_data = {
        "census": fetch_census_data(zip_code),
        "health": fetch_health_data(zip_code),
        "crime": fetch_crime_data(zip_code),
        "osm": fetch_osm_poi_data(zip_code),
        "housing": fetch_housing_data(zip_code),
        "broadband": fetch_broadband_data(zip_code),
        "air_quality": fetch_air_quality_data(zip_code),
    }

  
    # STEP 3: Store into Supabase 

    try:
        store_zip_data(zip_code, live_data)
        print(f"[CACHE] Stored ZIP {zip_code} data in Supabase")
    except Exception as e:
        print(f"[CACHE] WARNING: Failed to cache ZIP {zip_code}: {e}")

    
    # STEP 4: Return Live Output
   
    return live_data
