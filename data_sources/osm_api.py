# data_sources/osm_api.py

import requests
import functools
import time
from config.settings import settings
from core.geo_utils import zip_to_latlon

# ==========================================
# 1) Overpass Mirrors (fallback + rotation)
# ==========================================
# kumi.systems deprecated - migrated to private.coffee; both can be unreliable from some regions
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",  # formerly kumi.systems
]

# ==========================================
# POIs (Including police for crime proxy)
# ==========================================
# Single-tag queries (one key=value per Overpass call)
TAGS = {
    "parks": {"leisure": "park"},
    "grocery_stores": {"shop": "supermarket"},
    "clinics": {"amenity": "clinic"},
    "hospitals": {"amenity": "hospital"},
    "transit_stops": {"public_transport": "platform"},
    "police_stations": {"amenity": "police"},
}

# Additional tags to query and merge into main categories
EXTRA_TAGS = {
    "parks": [
        {"leisure": "nature_reserve"},
        {"leisure": "playground"},
        {"leisure": "recreation_ground"},
    ],
    "grocery_stores": [
        {"shop": "convenience"},
        {"shop": "grocery"},
    ],
    "transit_stops": [
        {"highway": "bus_stop"},
        {"railway": "station"},
    ],
}

# Search radii
SEARCH_RADIUS = 5000     # 5 km — walkable / near range
SEARCH_RADIUS_WIDE = 10000  # 10 km — driving-distance range


# ==========================================
# Central Query Function (with silent fallback)
# ==========================================
def _query_osm(lat: float, lon: float, tag_key: str, tag_val: str, radius: int = SEARCH_RADIUS):
    query = f"""
    [out:json][timeout:25];
    (
      node["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
      way["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
      relation["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
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
@functools.lru_cache(maxsize=1000)
def cached_query(lat, lon, key, value, radius=SEARCH_RADIUS):
    return _query_osm(lat, lon, key, value, radius=radius)


# ==========================================
# Public function used by your app
# ==========================================
def _fetch_at_radius(lat: float, lon: float, radius: int) -> dict:
    """Fetch all POI counts at a given radius."""
    results = {}

    for label, tag in TAGS.items():
        key = list(tag.keys())[0]
        value = tag[key]
        results[label] = cached_query(lat, lon, key, value, radius)

    for label, extra_list in EXTRA_TAGS.items():
        for tag in extra_list:
            key = list(tag.keys())[0]
            value = tag[key]
            results[label] += cached_query(lat, lon, key, value, radius)

    return results


def fetch_osm_poi_data(zip_code: str) -> dict:
    """
    Returns POI counts at two radii:
      - 5km keys: parks, grocery_stores, clinics, hospitals, transit_stops, police_stations
      - 10km keys: parks_10km, grocery_stores_10km, clinics_10km, hospitals_10km, transit_stops_10km, police_stations_10km
    """
    if settings.USE_MOCK_DATA:
        return {
            "parks": 5, "grocery_stores": 12, "clinics": 4,
            "hospitals": 2, "transit_stops": 24, "police_stations": 1,
            "parks_10km": 12, "grocery_stores_10km": 28, "clinics_10km": 9,
            "hospitals_10km": 5, "transit_stops_10km": 48, "police_stations_10km": 3,
        }

    lat, lon = zip_to_latlon(zip_code)

    near = _fetch_at_radius(lat, lon, SEARCH_RADIUS)
    wide = _fetch_at_radius(lat, lon, SEARCH_RADIUS_WIDE)

    results = dict(near)
    for label, count in wide.items():
        results[f"{label}_10km"] = count

    return results
