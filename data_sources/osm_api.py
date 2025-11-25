# data_sources/osm_api.py

import requests
import functools
import time
from config.settings import settings
from core.geo_utils import zip_to_latlon

# ==========================================
# 1) Overpass Mirrors (fallback + rotation)
# ==========================================
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# ==========================================
# POIs (Including police for crime proxy)
# ==========================================
TAGS = {
    "parks": {"leisure": "park"},
    "grocery_stores": {"shop": "supermarket"},
    "clinics": {"amenity": "clinic"},
    "transit_stops": {"public_transport": "platform"},
    "police_stations": {"amenity": "police"},
}

# Default search radius = 5000m
SEARCH_RADIUS = 5000


# ==========================================
# Central Query Function (with silent fallback)
# ==========================================
def _query_osm(lat: float, lon: float, tag_key: str, tag_val: str):
    query = f"""
    [out:json][timeout:25];
    (
      node["{tag_key}"="{tag_val}"](around:{SEARCH_RADIUS},{lat},{lon});
      way["{tag_key}"="{tag_val}"](around:{SEARCH_RADIUS},{lat},{lon});
      relation["{tag_key}"="{tag_val}"](around:{SEARCH_RADIUS},{lat},{lon});
    );
    out count;
    """

    last_error = None

    for url in OVERPASS_SERVERS:
        try:
            resp = requests.post(url, data={"data": query}, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "elements" in data and data["elements"]:
                tags = data["elements"][0].get("tags", {})
                return (
                    int(tags.get("nodes", "0"))
                    + int(tags.get("ways", "0"))
                    + int(tags.get("relations", "0"))
                )
        except Exception as e:
            last_error = e
            time.sleep(0.4)  # small cooldown to avoid throttling

    # 🚨 Only print if ALL mirrors fail
    print(f"[OSM] ERROR: All mirrors failed. Last error: {last_error}")
    return 0  # fallback if all failed


# ==========================================
# ⚡ Local Cache (Prevents repeated API hits)
# ==========================================
@functools.lru_cache(maxsize=500)
def cached_query(lat, lon, key, value):
    return _query_osm(lat, lon, key, value)


# ==========================================
# Public function used by your app
# ==========================================
def fetch_osm_poi_data(zip_code: str) -> dict:
    # MOCK MODE (unchanged behavior!)
    if settings.USE_MOCK_DATA:
        return {
            "parks": 5,
            "grocery_stores": 12,
            "clinics": 4,
            "transit_stops": 24,
            "police_stations": 1,
        }

    lat, lon = zip_to_latlon(zip_code)
    results = {}

    for label, tag in TAGS.items():
        key = list(tag.keys())[0]
        value = tag[key]

        # 🧠 Use local cache for identical queries
        results[label] = cached_query(lat, lon, key, value)

    return results
