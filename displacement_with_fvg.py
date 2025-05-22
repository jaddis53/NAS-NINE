import pandas as pd

def detect_fvg(df):
    fvgs = []

    for i in range(2, len(df)):
        prev1 = df.iloc[i - 1]
        prev2 = df.iloc[i - 2]
        curr = df.iloc[i]

        # Bullish FVG: current low > high two candles back
        if curr['low'] > prev2['high']:
            fvgs.append({'index': i, 'type': 'bullish', 'time': curr['time']})

        # Bearish FVG: current high < low two candles back
        elif curr['high'] < prev2['low']:
            fvgs.append({'index': i, 'type': 'bearish', 'time': curr['time']})

    return pd.DataFrame(fvgs)

def detect_displacements_with_fvg(df, swing_lookback=5, body_multiplier=1.5):
    displacements = []

    df = df.copy()
    df['body'] = abs(df['close'] - df['open'])
    df['avg_body'] = df['body'].rolling(window=swing_lookback).mean()

    # Detect swing highs/lows
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]

    # Detect FVGs first
    fvgs = detect_fvg(df)

    # Safe check for 'index' column and empty DataFrame
    if fvgs.empty or 'index' not in fvgs.columns:
        fvg_indices = set()
    else:
        fvg_indices = set(fvgs['index'])

    last_swing_high = None
    last_swing_low = None

    for i in range(swing_lookback + 1, len(df)):
        row = df.iloc[i]

        # Update swing levels
        if not pd.isna(df.iloc[i - 1]['swing_high']):
            last_swing_high = df.iloc[i - 1]['swing_high']
        if not pd.isna(df.iloc[i - 1]['swing_low']):
            last_swing_low = df.iloc[i - 1]['swing_low']

        if last_swing_high is None or last_swing_low is None or pd.isna(row['avg_body']):
            continue

        # Check if there's an FVG near this index (i, i-1, or i+1)
        has_fvg_nearby = any(idx in fvg_indices for idx in [i, i - 1, i + 1])
        if not has_fvg_nearby:
            continue  # Skip if no FVG

        # Bullish MSS with FVG
        if (row['close'] > row['open'] and
            row['body'] > body_multiplier * row['avg_body'] and
            row['close'] > last_swing_high):
            displacements.append({
                "index": i,
                "type": "bullish",
                "body_size": row['body'],
                "close": row['close'],
                "broke_level": last_swing_high,
                "time": row['time']
            })

        # Bearish MSS with FVG
        elif (row['open'] > row['close'] and
              row['body'] > body_multiplier * row['avg_body'] and
              row['close'] < last_swing_low):
            displacements.append({
                "index": i,
                "type": "bearish",
                "body_size": row['body'],
                "close": row['close'],
                "broke_level": last_swing_low,
                "time": row['time']
            })

    return pd.DataFrame(displacements)

def calculate_trade_levels(setup, nine_am_range):
    # Entry at 50% between close (displacement candle close) and broke_level (last swing high/low)
    entry = (setup['close'] + setup['broke_level']) / 2

    if setup['type'] == 'bullish':
        # SL is at the low of the displacement (which should be the lower of the two levels)
        sl = min(setup['close'], setup['broke_level'])
        # TP is the high of the 9AM candle (opposite side)
        tp = nine_am_range['high']
    else:  # bearish
        # SL is at the high of the displacement (higher of the two)
        sl = max(setup['close'], setup['broke_level'])
        # TP is the low of the 9AM candle
        tp = nine_am_range['low']

    return {
        'entry': entry,
        'stop_loss': sl,
        'take_profit': tp,
        'direction': setup['type'],
        'time': setup['time']
    }
