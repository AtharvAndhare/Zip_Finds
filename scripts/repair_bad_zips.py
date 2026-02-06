import os, sys, time
from pathlib import Path

# Add project root to path
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
    """
    Identify ZIPs with missing or invalid data.
    """
    res = supabase.table("zip_cache").select("zip_code, data").execute()
    bad = []

    if not res.data:
        return bad

    for row in res.data:
        z = row["zip_code"]
        d = row.get("data", {})

        # protect from missing keys
        cen = d.get("census", {})
        house = d.get("housing", {})
        bb = d.get("broadband", {})

        median_income = cen.get("median_income")

        # ---- Conditions that mark a ZIP as incomplete ----
        if (
            # missing or invalid income
            median_income is None or
            (isinstance(median_income, (int, float)) and median_income < 1000) or

            # invalid population
            cen.get("resident_base") in [None, 0] or

            # missing housing rent
            house.get("median_rent") is None or

            # broadband appears absent (likely failed)
            bb.get("broadband_pct") == 0
        ):
            bad.append(z)

    return list(set(bad))


def repair_bad_zips():
    """
    Fix bad ZIPs in batches.
    """
    bad = fetch_bad_zips()

    if not bad:
        print("🎉 No bad ZIPs found. All data valid!")
        return

    # Limit to batch size
    chunk = bad[:BATCH_SIZE]
    print(f"\n🔧 Found {len(bad)} bad ZIPs. Processing {len(chunk)} now...\n")

    for i, zip_code in enumerate(chunk, start=1):
        print(f"[{i}/{len(chunk)}] 🔄 Repairing {zip_code} ...")
        try:
            data = collect_all_data(zip_code)
            store_zip_data(zip_code, data)
            print(f"   ✔ Updated {zip_code}")
        except Exception as e:
            print(f"   ❗ Error on {zip_code}: {e}")
        time.sleep(SLEEP_TIME)

    print("\n✅ Repair batch complete!")
    print(f"🕗 Remaining to fix next run: {len(bad) - len(chunk)}")


if __name__ == "__main__":
    repair_bad_zips()
