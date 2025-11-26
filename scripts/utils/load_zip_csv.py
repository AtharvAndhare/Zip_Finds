import pandas as pd

def load_zips_by_state(state_abbr: str, csv_path: str = "uszips.csv") -> list[str]:
    """
    Loads ZIP codes filtered by a specific state.
    Returns a list of zip string values (ex: "07306").
    """
    df = pd.read_csv( r"D:\Zip_Finds\simplemaps_uszips_basicv1.92\uszips.csv", dtype={'zip': str})
    
    if "state_id" not in df.columns:
        raise ValueError("CSV must contain 'state_id' column (2-letter state code)")

    # Filter by state abbreviation (e.g., 'NJ', 'CA')
    state_df = df[df["state_id"].str.upper() == state_abbr.upper()]

    return sorted(state_df["zip"].tolist())
