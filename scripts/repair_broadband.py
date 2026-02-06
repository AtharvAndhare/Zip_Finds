import time, sys
from pathlib import Path

# ----------------------------
# Add project ROOT to sys.path
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# ----------------------------
# Now safely import modules
# ----------------------------
from config.settings import settings
from db.supabase_client import supabase
from db.zip_cache import get_cached_zip, store_zip_data
from data_sources.broadband_api import fetch_broadband_data

# ----------------------------
# BATCH SETTINGS
# ----------------------------
BATCH_LIMIT = 500
SLEEP_TIME = 1.3


def fetch_broken_broadband():
    """Find ZIPs with missing or invalid broadband."""
    query = supabase.table("zip_cache").select("zip_code, data").execute()
    bad = []

    for row in query.data:
        z = row["zip_code"]
        d = (row["data"] or {}).get("broadband", {})

        pct = d.get("broadband_pct")

        if pct is None or pct == 0 or d.get("fiber_pct") is None:
            bad.append(z)

    return bad


def repair_broadband():
    bad_zips = fetch_broken_broadband()

    if not bad_zips:
        print("🎉 No broadband problems found!")
        return

    chunk = bad_zips[:BATCH_LIMIT]
    print(f"\n⚙️ Repairing {len(chunk)} ZIPs (out of {len(bad_zips)} bad)\n")

    for idx, zip_code in enumerate(chunk, start=1):
        print(f"[{idx}/{len(chunk)}] 🌐 Fixing {zip_code} ... ", end="")

        cached = get_cached_zip(zip_code)
        if not cached:
            print("⚠️ no base cached record — skipped")
            continue

        try:
            new_bb = fetch_broadband_data(zip_code)
            cached["broadband"] = new_bb
            store_zip_data(zip_code, cached)
            print("✔️ updated")
        except Exception as e:
            print(f"❌ failed: {e}")

        time.sleep(SLEEP_TIME)

    print("\n🎯 Batch complete!")
    print(f"⏳ Remaining for next run: {len(bad_zips) - len(chunk)}")


if __name__ == "__main__":
    repair_broadband()
