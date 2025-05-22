import pandas as pd

def detect_swings(df, window=3):
    """
    Detects swing highs and lows in the DataFrame.
    Returns a DataFrame with columns ['swing_high', 'swing_low'] boolean flags.
    """
    df = df.copy()
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & 
                                  (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & 
                                (df['low'].shift(-1) > df['low'])]
    return df

def get_nearest_swings(df_swings):
    """
    Returns the last detected swing high and swing low as pd.Series.
    Returns (swing_high, swing_low)
    """
    swing_highs = df_swings.dropna(subset=['swing_high'])
    swing_lows = df_swings.dropna(subset=['swing_low'])

    if swing_highs.empty or swing_lows.empty:
        return None, None
    
    latest_swing_high = swing_highs.iloc[-1]
    latest_swing_low = swing_lows.iloc[-1]

    return latest_swing_high, latest_swing_low
