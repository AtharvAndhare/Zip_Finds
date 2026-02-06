# scripts/load_state_batch.py

import os, sys, time
from pathlib import Path

# Fix imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import pandas as pd
from db.supabase_client import supabase
from core.aggregator import collect_all_data
from db.zip_cache import store_zip_data

# === USER SETTINGS HERE ===
STATE_CODE = "NY"         # CHANGE manually
BATCH_SIZE = 10
SLEEP_BETWEEN = 1.2

# === LOAD ZIP LIST FROM CSV ===
df = pd.read_csv(r"D:\Zip_Finds\simplemaps_uszips_basicv1.92\uszips.csv")
state_zips = df[df["state_id"] == STATE_CODE]["zip"].astype(str).tolist()


def get_cached_zips():
    res = supabase.table("zip_cache").select("zip_code").execute()
    if res.data:
        return set([row["zip_code"] for row in res.data])
    return set()


def batch_load_state():
    print(f"\n🌎 Preloading ZIPs for {STATE_CODE}...")

    cached = get_cached_zips()
    remaining = [z for z in state_zips if z not in cached]
    chunk = remaining[:BATCH_SIZE]

    if not chunk:
        print(f"🎉 All ZIPs for {STATE_CODE} are already loaded!")
        return

    print(f"📌 Loading {len(chunk)} ZIPs out of {len(remaining)} remaining.")

    for zip_code in chunk:
        try:
            print(f"➡️ Fetching {zip_code} ...")
            data = collect_all_data(zip_code)
            store_zip_data(zip_code, data)
        except Exception as e:
            print(f"⚠️ Error {zip_code}: {e}")
        time.sleep(SLEEP_BETWEEN)

    print(f"\n✅ Loaded {len(chunk)} ZIPs for {STATE_CODE}.")
    print(f"⏳ Remaining for later: {len(remaining) - len(chunk)}")


if __name__ == "__main__":
    batch_load_state()
