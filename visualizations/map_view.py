# visualizations/map_view.py
import pandas as pd
from core.geo_utils import zip_to_latlon


def make_map_df(zip_code: str) -> pd.DataFrame:
    lat, lon = zip_to_latlon(zip_code)
    return pd.DataFrame({"lat": [lat], "lon": [lon]})
