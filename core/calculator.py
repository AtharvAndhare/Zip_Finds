# core/calculator.py

def _normalize(value, vmin=0, vmax=100, invert=False):
    """
    Fully safe normalization.
    Accepts numbers, strings, dicts, None, booleans, or error messages.
    Will NEVER throw.
    """

    #Handling None or missing data 
    if value is None:
        return 50

    # Convert to float safely
    try:
        # If value is dict, list, boolean, error text → fallback
        if isinstance(value, (dict, list, bool)):
            raise ValueError()

        # Strings like "123", "12.5"
        value = float(value)

    except Exception:
        return 50  # neutral score

    #If vmin == vmax 
    if vmax == vmin:
        return 50

    # Clamp the value
    try:
        value_clamped = max(min(value, float(vmax)), float(vmin))
    except Exception:
        return 50

    #Normalize 0–1
    score = (value_clamped - vmin) / (vmax - vmin)

    #Invert if necessary
    if invert:
        score = 1 - score

    #Scale to 0–100
    return score * 100
