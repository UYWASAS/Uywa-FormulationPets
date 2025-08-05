def fmt2(x):
    try:
        return f"{float(x):.2f}"
    except Exception:
        return x

def fmt2_df(df):
    import pandas as pd
    import numpy as np
    df_fmt = df.copy()
    for col in df_fmt.select_dtypes(include=[np.number]).columns:
        df_fmt[col] = df_fmt[col].apply(fmt2)
    return df_fmt
