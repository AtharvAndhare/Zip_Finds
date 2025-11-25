

import pgeocode

# Initialize US geocoder once (fast)
nomi = pgeocode.Nominatim("us")


def zip_to_latlon(zip_code: str) -> tuple[float, float]:
    """
    Converts a ZIP Code to (latitude, longitude) using pgeocode.
    Returns a tuple (lat, lon). If ZIP not found → fallback coordinates.

    Example:
        zip_to_latlon("07306") -> (40.733, -74.065)
    """

    try:
        info = nomi.query_postal_code(zip_code)

        # pgeocode returns a Pandas Series with fields:
        # latitude, longitude, place_name, state_name, county_name

        lat = float(info.latitude) if info.latitude is not None else None
        lon = float(info.longitude) if info.longitude is not None else None

        if lat is None or lon is None:
            raise ValueError("Invalid coordinates from pgeocode")

        return lat, lon

    except Exception as e:
        print(f"[geo_utils] Error retrieving lat/lon for ZIP {zip_code}: {e}")

        # Fallback to NYC (safe default)
        return 40.7128, -74.0060
