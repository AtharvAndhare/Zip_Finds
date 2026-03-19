"""Quick OSM Overpass connectivity test."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

query = '[out:json][timeout:10]; node["shop"="supermarket"](around:5000,40.71,-74.00); out count;'

for url in SERVERS:
    try:
        print(f"Testing {url}... ", end="", flush=True)
        r = requests.post(url, data={"data": query}, timeout=15)
        print(f"status={r.status_code}")
        if r.status_code == 200:
            d = r.json()
            print(f"  elements: {len(d.get('elements', []))}")
            if d.get("elements"):
                print(f"  first: {d['elements'][0]}")
    except Exception as e:
        print(f"ERROR: {e}")
