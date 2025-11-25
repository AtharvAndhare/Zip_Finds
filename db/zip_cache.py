from .supabase_client import supabase
from datetime import datetime, timezone

def get_cached_zip(zip_code: str):
    try:
        res = supabase.table("zip_cache").select("data").eq("zip_code", zip_code).execute()
        if res.data and len(res.data):
            return res.data[0]["data"]
    except Exception as e:
        print(f"[CACHE] WARNING: Failed to fetch cache for {zip_code}: {e}")
    return None


def store_zip_data(zip_code: str, data: dict):
    try:
        supabase.table("zip_cache").upsert({
            "zip_code": zip_code,
            "data": data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        print(f"[CACHE] STORED ZIP {zip_code}")
    except Exception as e:
        print(f"[CACHE] WARNING: Failed to cache ZIP {zip_code}: {e}")
