def fmt2(val):
    try:
        return round(float(val), 2)
    except Exception:
        return val
