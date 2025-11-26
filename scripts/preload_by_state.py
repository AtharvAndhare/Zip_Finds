import sys, time, random
from pathlib import Path

# --- allow imports of app modules ---
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.aggregator import collect_all_data
from db.zip_cache import store_zip_data, get_cached_zip
from scripts.utils.load_zip_csv import load_zips_by_state


def preload_state(state: str):
    zips = load_zips_by_state(state)

    total = len(zips)
    print(f"\n🚀 Starting preload for state {state} ({total} ZIP codes)\n")

    for idx, zip_code in enumerate(zips, start=1):

        # Skip if already cached
        if get_cached_zip(zip_code):
            print(f"⏩ [{idx}/{total}] {zip_code} – already cached, skipping")
            continue

        try:
            print(f"📌 [{idx}/{total}] Fetching {zip_code} ...", end=" ")
            data = collect_all_data(zip_code)
            store_zip_data(zip_code, data)
            print("💾 stored")

        except Exception as e:
            print(f"❌ failed: {e}")

        # Sleep to prevent API bans (randomized)
        time.sleep(1.0 + random.random() * 1.0)  # 1.0–2.0 seconds


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❗ Usage: python preload_by_state.py <STATE_ABBR>\nExample: python preload_by_state.py NJ\n")
        sys.exit(1)

    preload_state(sys.argv[1].upper())
