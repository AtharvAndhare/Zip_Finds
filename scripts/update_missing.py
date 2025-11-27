# scripts/update_missing.py

import os, sys, time
from pathlib import Path

# fix imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from db.supabase_client import supabase
from core.aggregator import collect_all_data
from db.zip_cache import store_zip_data


def fetch_missing():
    res = supabase.table("zip_cache").select("zip_code").is_("data", None).limit(1).execute()

    if not res.data:
        print("✨ No missing records! All good.")
        return False

    zip_code = res.data[0]["zip_code"]
    print(f"🌎 Processing ZIP {zip_code}")

    try:
        data = collect_all_data(zip_code)
        store_zip_data(zip_code, data)
        print(f"   ✔ Cached {zip_code}")
    except Exception as e:
        print(f"   ❌ Failed {zip_code}: {e}")

    time.sleep(1.5)
    return True


if __name__ == "__main__":
    while fetch_missing():
        pass
