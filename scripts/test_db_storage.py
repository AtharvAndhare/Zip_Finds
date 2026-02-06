# scripts/test_db_storage.py
"""
Quick test to verify that new ZIPs are stored in Supabase.
Run: python scripts/test_db_storage.py
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from db.supabase_client import supabase
from db.zip_cache import get_cached_zip, store_zip_data
from core.aggregator import collect_all_data


def test_supabase_connection():
    """Test basic Supabase connectivity."""
    print("\n" + "="*50)
    print("TEST 1: Supabase Connection")
    print("="*50)
    
    try:
        # Try to count records in zip_cache
        result = supabase.table("zip_cache").select("zip_code", count="exact").limit(5).execute()
        print(f"[OK] Connected to Supabase!")
        print(f"   Total ZIPs in cache: {result.count}")
        if result.data:
            print(f"   Sample ZIPs: {[r['zip_code'] for r in result.data[:5]]}")
        return True
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return False


def test_cache_retrieval(zip_code: str):
    """Test retrieving a ZIP from cache."""
    print("\n" + "="*50)
    print(f"TEST 2: Cache Retrieval for ZIP {zip_code}")
    print("="*50)
    
    cached = get_cached_zip(zip_code)
    if cached:
        print(f"[OK] ZIP {zip_code} found in cache!")
        print(f"   Keys: {list(cached.keys())}")
        return True
    else:
        print(f"[INFO] ZIP {zip_code} NOT in cache (will be fetched fresh)")
        return False


def test_full_flow(zip_code: str):
    """Test the complete data collection and storage flow."""
    print("\n" + "="*50)
    print(f"TEST 3: Full Data Collection for ZIP {zip_code}")
    print("="*50)
    
    # Check if already cached
    was_cached = get_cached_zip(zip_code) is not None
    
    # Fetch data (will use cache if available, otherwise fetch + store)
    print(f"\nCalling collect_all_data('{zip_code}')...")
    data = collect_all_data(zip_code)
    
    if data:
        print(f"\n[OK] Data collected successfully!")
        print(f"   Keys: {list(data.keys())}")
        
        # Show sample of each data source
        for key, value in data.items():
            if isinstance(value, dict):
                sample = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
                print(f"   {key}: {sample}")
    else:
        print(f"[FAIL] No data returned!")
        return False
    
    # Verify it's now in the database
    print(f"\nVerifying ZIP {zip_code} is stored in database...")
    cached_after = get_cached_zip(zip_code)
    
    if cached_after:
        print(f"[OK] ZIP {zip_code} is now in Supabase cache!")
        if not was_cached:
            print(f"   (This was a NEW entry - successfully stored!)")
        return True
    else:
        print(f"[FAIL] ZIP {zip_code} was NOT stored in database!")
        return False


def main():
    print("\n" + "#"*60)
    print("#  ZIP FINDS - Database Storage Test")
    print("#"*60)
    
    # Test 1: Connection
    if not test_supabase_connection():
        print("\n[WARN] Cannot continue without Supabase connection.")
        return
    
    # Test 2 & 3: Use a test ZIP
    test_zip = "10001"  # NYC ZIP - commonly available data
    
    test_cache_retrieval(test_zip)
    test_full_flow(test_zip)
    
    print("\n" + "="*50)
    print("TEST COMPLETE")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
