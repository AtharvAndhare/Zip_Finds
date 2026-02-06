# core/calculator.py

from config.constants import NORMALIZATION_BOUNDS


def _normalize(value, metric_or_vmin=0, vmax=100, invert=False):
    """
    Fully safe normalization to 0-100 scale.

    Can be called two ways:
        _normalize(value, "metric_name", invert=True)   # lookup bounds
        _normalize(value, vmin, vmax, invert)            # explicit bounds

    If *metric_or_vmin* is a string it is treated as a metric name and
    the (vmin, vmax) pair is looked up from NORMALIZATION_BOUNDS.
    """

    # Handling None or missing data
    if value is None:
        return 50

    # Convert to float safely
    try:
        if isinstance(value, (dict, list, bool)):
            raise ValueError()
        value = float(value)
    except Exception:
        return 50  # neutral score

    # Resolve bounds – string → look up, number → use directly
    if isinstance(metric_or_vmin, str):
        bounds = NORMALIZATION_BOUNDS.get(metric_or_vmin, (0, 100))
        vmin, vmax = bounds
    else:
        vmin = metric_or_vmin

    # Safety: equal bounds
    if vmax == vmin:
        return 50

    # Clamp the value
    try:
        value_clamped = max(min(value, float(vmax)), float(vmin))
    except Exception:
        return 50

    # Normalize 0–1
    score = (value_clamped - vmin) / (vmax - vmin)

    # Invert if necessary
    if invert:
        score = 1 - score

    # Scale to 0–100
    return score * 100
