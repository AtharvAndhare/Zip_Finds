# scripts/repair_bad_zips.py

import os, sys, time
from pathlib import Path

# --- Fix Python path to root ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.aggregator import collect_all_data
from db.zip_cache import store_zip_data
from db.supabase_client import supabase

# -------------- CONFIG -----------------
BATCH_SIZE = 500        # repair max per run
SLEEP_TIME = 1.5        # avoid API rate limit
# ---------------------------------------


def fetch_bad_zips():
    """Return ZIPs where key data is missing or clearly incorrect."""
    res = supabase.table("zip_cache").select("zip_code, data").execute()
    bad = []

    for row in res.data:
        z = row["zip_code"]
        d = row["data"]

        if not d:
            bad.append(z)
            continue

        if (
            not d["census"]["median_income"] or
            not d["census"]["resident_base"] or
            d["housing"]["median_rent"] is None or
            d["broadband"]["broadband_pct"] == 0 or
            d["census"]["bachelors_rate"] == 0
        ):
            bad.append(z)

    return list(set(bad))


def repair_bad_zips():
    bad = fetch_bad_zips()

    if not bad:
        print("🎉 No bad ZIPs found. All fixed!")
        return

    chunk = bad[:BATCH_SIZE]
    print(f"\n🔧 Found {len(bad)} bad ZIPs. Repairing {len(chunk)}...\n")

    for i, zip_code in enumerate(chunk, start=1):
        print(f"[{i}/{len(chunk)}] 🔄 Fixing {zip_code} ...")

        try:
            data = collect_all_data(zip_code)
            store_zip_data(zip_code, data)
            print(f"   ✔ Updated {zip_code}")

        except Exception as e:
            print(f"   ❗ Error on {zip_code}: {e}")

        time.sleep(SLEEP_TIME)

    print("\n🚀 Repair batch complete!")
    print(f"🕗 Remaining: {len(bad) - len(chunk)}")


if __name__ == "__main__":
    repair_bad_zips()
