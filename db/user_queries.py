from .supabase_client import supabase

def save_query(zip_code, persona, narrative):
    supabase.table("user_queries").insert({
        "zip": zip_code,
        "persona": persona,
        "narrative": narrative
    }).execute()
