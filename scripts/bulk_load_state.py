# scripts/bulk_load_state.py
"""
Bulk load FULL accurate data (Census + OSM + AirNow + HRSA) for all ZIPs in a state.

Usage:
    python scripts/bulk_load_state.py NJ
    python scripts/bulk_load_state.py CA
    python scripts/bulk_load_state.py NY

Features:
- Fetches real data from all APIs (not estimates)
- Throttled to ~600 ZIPs/day to stay under OSM Overpass rate limits
- Auto-resumes from where it left off (skips already cached ZIPs)
- Saves progress to a local file
- Shows estimated time remaining

Rate limits respected:
- Census API: unlimited with API key
- Overpass (OSM): ~10,000 queries/day (13 per ZIP = ~770 ZIPs/day, we do ~600)
- AirNow: conservative pacing
- HRSA: no published limits, conservative pacing
"""

import sys
import os
import time
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

# Fix imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import settings
from core.aggregator import collect_all_data
from core.scoring_engine import compute_scores
from db.zip_cache import get_cached_zip, store_zip_data

# =============================================================================
# CONFIGURATION
# =============================================================================
DELAY_BETWEEN_ZIPS = 90          # seconds between each ZIP (safe for OSM)
PROGRESS_FILE = ROOT / "scripts" / "bulk_progress.json"
CENSUS_API_KEY = settings.CENSUS_API_KEY

# State FIPS codes for Census API
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


# =============================================================================
# GET ALL ZIPS FOR A STATE (via pgeocode)
# =============================================================================
def get_zips_for_state(state_abbr: str) -> list[str]:
    """Get all ZIP codes for a state using pgeocode."""
    import pgeocode
    
    nomi = pgeocode.Nominatim("us")
    
    # Get all US ZCTAs from Census API
    import requests
    print(f"[INIT] Fetching all US ZIP codes from Census API...")
    
    url = "https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E&for=zip%20code%20tabulation%20area:*"
    if CENSUS_API_KEY:
        url += f"&key={CENSUS_API_KEY}"
    
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    # data[0] is header, data[1:] are rows
    # Each row: [NAME, population, zip_code]
    all_zips = []
    for row in data[1:]:
        zip_code = row[-1]  # last element is the ZCTA
        all_zips.append(zip_code)
    
    print(f"[INIT] Found {len(all_zips)} total US ZIP codes")
    
    # Filter by state using pgeocode
    print(f"[INIT] Filtering for state: {state_abbr}...")
    state_zips = []
    
    for zip_code in all_zips:
        try:
            result = nomi.query_postal_code(zip_code)
            if hasattr(result, 'state_code') and str(result.state_code) == state_abbr:
                state_zips.append(zip_code)
        except Exception:
            continue
    
    # Sort by ZIP code
    state_zips.sort()
    print(f"[INIT] Found {len(state_zips)} ZIPs for {state_abbr}")
    
    return state_zips


# =============================================================================
# PROGRESS TRACKING
# =============================================================================
def load_progress() -> dict:
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(state: str, completed: list[str], failed: list[str]):
    """Save progress to file."""
    progress = load_progress()
    progress[state] = {
        "completed": completed,
        "failed": failed,
        "last_updated": datetime.now().isoformat(),
    }
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


# =============================================================================
# MAIN BULK LOADER
# =============================================================================
def bulk_load_state(state_abbr: str):
    """Load all ZIPs for a state with full accurate data."""
    
    state_abbr = state_abbr.upper()
    if state_abbr not in STATE_FIPS:
        print(f"[ERROR] Unknown state: {state_abbr}")
        print(f"[ERROR] Valid states: {', '.join(sorted(STATE_FIPS.keys()))}")
        return
    
    print("=" * 60)
    print(f"  BULK LOAD: {state_abbr}")
    print(f"  Mode: Full data (Census + OSM + AirNow + HRSA)")
    print(f"  Delay: {DELAY_BETWEEN_ZIPS}s between ZIPs")
    print("=" * 60)
    
    # Get all ZIPs for this state
    all_zips = get_zips_for_state(state_abbr)
    
    if not all_zips:
        print(f"[ERROR] No ZIPs found for {state_abbr}")
        return
    
    # Load previous progress
    progress = load_progress()
    state_progress = progress.get(state_abbr, {})
    previously_completed = set(state_progress.get("completed", []))
    
    # Check which ZIPs are already cached in Supabase
    print(f"[INIT] Checking Supabase cache...")
    already_cached = set()
    for z in all_zips:
        if get_cached_zip(z) is not None:
            already_cached.add(z)
    
    # Combine: skip anything already done
    skip = previously_completed | already_cached
    remaining = [z for z in all_zips if z not in skip]
    
    print(f"\n[STATUS] Total ZIPs for {state_abbr}: {len(all_zips)}")
    print(f"[STATUS] Already cached: {len(already_cached)}")
    print(f"[STATUS] Previously completed: {len(previously_completed)}")
    print(f"[STATUS] Remaining to process: {len(remaining)}")
    
    if not remaining:
        print(f"\n[DONE] All ZIPs for {state_abbr} are already loaded!")
        return
    
    # Estimate time
    est_seconds = len(remaining) * (DELAY_BETWEEN_ZIPS + 20)  # 20s avg API time
    est_hours = est_seconds / 3600
    est_days = est_hours / 24
    print(f"[TIME] Estimated time: {est_hours:.1f} hours ({est_days:.1f} days)")
    print(f"\n[START] Beginning bulk load... (Ctrl+C to pause safely)\n")
    
    completed = list(previously_completed)
    failed = list(state_progress.get("failed", []))
    
    start_time = time.time()
    
    for idx, zip_code in enumerate(remaining, start=1):
        try:
            # Progress display
            elapsed = time.time() - start_time
            avg_per_zip = elapsed / idx if idx > 1 else DELAY_BETWEEN_ZIPS + 20
            eta_seconds = avg_per_zip * (len(remaining) - idx)
            eta_str = str(timedelta(seconds=int(eta_seconds)))
            
            print(f"[{idx}/{len(remaining)}] ZIP {zip_code} | "
                  f"ETA: {eta_str} | "
                  f"Done: {len(completed)}/{len(all_zips)}", end=" ... ")
            
            # Fetch FULL data (Census + OSM + AirNow + HRSA)
            data = collect_all_data(zip_code, fast_mode=False)
            
            # Verify we got real data
            income = data.get("census", {}).get("median_income")
            if income and income > 0:
                print(f"OK (income=${income:,.0f})")
                completed.append(zip_code)
            else:
                print(f"WARN (no income data, still cached)")
                completed.append(zip_code)
            
        except KeyboardInterrupt:
            print(f"\n\n[PAUSED] Stopping gracefully...")
            print(f"[PAUSED] Completed {len(completed)} ZIPs so far.")
            print(f"[PAUSED] Run the same command to resume.")
            save_progress(state_abbr, completed, failed)
            return
            
        except Exception as e:
            print(f"FAILED ({e})")
            failed.append(zip_code)
        
        # Save progress every 10 ZIPs
        if idx % 10 == 0:
            save_progress(state_abbr, completed, failed)
        
        # Throttle: wait before next ZIP
        if idx < len(remaining):
            jitter = random.uniform(-10, 10)  # +/- 10s randomization
            wait = max(DELAY_BETWEEN_ZIPS + jitter, 60)  # minimum 60s
            time.sleep(wait)
    
    # Final save
    save_progress(state_abbr, completed, failed)
    
    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  COMPLETE: {state_abbr}")
    print(f"  Loaded: {len(completed)} ZIPs")
    print(f"  Failed: {len(failed)} ZIPs")
    print(f"  Time: {timedelta(seconds=int(total_time))}")
    print(f"{'=' * 60}")
    
    if failed:
        print(f"\nFailed ZIPs: {', '.join(failed)}")
        print("Run the script again to retry failed ZIPs.")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    STATES_ORDER = ["NJ", "MD", "MA", "AZ", "WA", "NY", "CA", "TX"]
    
    if len(sys.argv) < 2:
        print("\nUSAGE: python scripts/bulk_load_state.py <STATE>")
        print(f"\nRecommended order (smallest first):")
        for i, s in enumerate(STATES_ORDER, 1):
            print(f"  {i}. {s}")
        print(f"\nExample: python scripts/bulk_load_state.py NJ")
        sys.exit(1)
    
    state = sys.argv[1].upper()
    bulk_load_state(state)
