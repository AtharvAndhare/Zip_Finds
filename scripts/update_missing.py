import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import time
from db.supabase_client import supabase
from core.aggregator import collect_all_data
from db.zip_cache import store_zip_data

def fetch_missing():
    # get rows where data IS NULL
    res = supabase.table("zip_cache").select("zip_code").is_(
        "data", None).limit(1).execute()

    if not res.data:
        print("✨ All ZIPs loaded!")
        return False

    zip_code = res.data[0]["zip_code"]
    print(f"🌎 Fetching ZIP {zip_code}")

    try:
        data = collect_all_data(zip_code)  # pull APIs
        store_zip_data(zip_code, data)     # save to DB
        print(f"   ✔ Cached {zip_code}")
    except Exception as e:
        print(f"   ❌ Failed {zip_code}: {e}")

    time.sleep(1.5)  # throttle to avoid API bans
    return True


if __name__ == "__main__":
    while fetch_missing():
        pass
