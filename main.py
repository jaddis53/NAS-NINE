from datetime import time, datetime
import pytz
import pandas as pd
import MetaTrader5 as mt5
from data_fetch import fetch_data
from displacement_with_fvg import detect_displacements_with_fvg, calculate_trade_levels

NY_TZ = pytz.timezone('America/New_York')
UTC_TZ = pytz.utc

def print_times(label, utc_ts):
    ny_ts = utc_ts.astimezone(NY_TZ)
    print(f"{label} | UTC: {utc_ts.strftime('%Y-%m-%d %H:%M:%S %Z%z')} | NY: {ny_ts.strftime('%Y-%m-%d %I:%M:%S %p %Z%z')}")

def print_mt5_time_info():
    if not mt5.initialize():
        print("MT5 initialization failed")
        return None, None

    symbol = "EURUSD"
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("Failed to get tick data")
        mt5.shutdown()
        return None, None

    server_timestamp = tick.time
    mt5.shutdown()

    server_dt = datetime.utcfromtimestamp(server_timestamp).replace(tzinfo=UTC_TZ)
    print_times("🕒 MT5 Server Time", server_dt)

    return server_dt, server_dt.astimezone(NY_TZ)

def get_3am_h1_range(symbol):
    df_h1 = fetch_data(symbol, mt5.TIMEFRAME_H1, bars=10)
    if df_h1 is None or df_h1.empty:
        print("Failed to fetch H1 data")
        return None

    df_h1['time'] = pd.to_datetime(df_h1['time'], utc=True)
    df_h1['ny_time'] = df_h1['time'].dt.tz_convert(NY_TZ)
    df_h1['hour'] = df_h1['ny_time'].dt.hour
    df_h1['date'] = df_h1['ny_time'].dt.date

    today = datetime.now(NY_TZ).date()
    target_candle = df_h1[(df_h1['date'] == today) & (df_h1['hour'] == 3)]  # <-- Changed here: 3 AM candle

    if target_candle.empty:
        print("No 3:00 AM NY H1 candle found.")
        return None

    candle = target_candle.iloc[0]

    print_times("\n🕒 3AM NY H1 Candle", candle['time'])
    print(f"Open: {candle['open']}")
    print(f"High: {candle['high']}")
    print(f"Low: {candle['low']}")
    print(f"Close: {candle['close']}")

    df_m1 = fetch_data(symbol, mt5.TIMEFRAME_M1, bars=300)
    df_m1['time'] = pd.to_datetime(df_m1['time'], utc=True)
    df_m1['ny_time'] = df_m1['time'].dt.tz_convert(NY_TZ)

    candle_start = candle['ny_time']
    candle_end = candle_start + pd.Timedelta(hours=1)
    df_3am = df_m1[(df_m1['ny_time'] >= candle_start) & (df_m1['ny_time'] < candle_end)]

    high_row = df_3am[df_3am['high'] == df_3am['high'].max()].iloc[0]
    low_row = df_3am[df_3am['low'] == df_3am['low'].min()].iloc[0]

    print_times(f"High of 3AM formed at", high_row['time'])
    print(f"Price: {high_row['high']}")

    print_times(f"Low of 3AM formed at", low_row['time'])
    print(f"Price: {low_row['low']}")

    return {
        'high': candle['high'],
        'low': candle['low'],
        'end_time': candle['time'] + pd.Timedelta(hours=1)
    }

def detect_1m_breakout(df_m1, high, low, start_time):
    df_m1['time'] = pd.to_datetime(df_m1['time'], utc=True)
    df_m1['ny_time'] = df_m1['time'].dt.tz_convert(NY_TZ)

    start_ny = start_time.astimezone(NY_TZ)
    # Look for breakout between 4:00 and 5:00 AM NY time (shifted 1 hour later)
    end_ny = start_ny.replace(hour=5, minute=0, second=0, microsecond=0)

    df_filtered = df_m1[(df_m1['ny_time'] >= start_ny) & (df_m1['ny_time'] < end_ny)]

    for _, row in df_filtered.iterrows():
        if row['close'] > high:
            print_times("[1M] Bullish breakout at", row['time'])
            return 'bullish', row['ny_time']
        elif row['close'] < low:
            print_times("[1M] Bearish breakout at", row['time'])
            return 'bearish', row['ny_time']
    return None, None

def filter_hunt_window(df_m1, breakout_time):
    df_m1['time'] = pd.to_datetime(df_m1['time'], utc=True)
    df_m1['ny_time'] = df_m1['time'].dt.tz_convert(NY_TZ)
    hunt_day = breakout_time.date()

    # Hunt between 4:00 and 5:00 AM NY time (changed from 3-4 AM)
    df_filtered = df_m1[
        (df_m1['ny_time'].dt.date == hunt_day) &
        (df_m1['ny_time'].dt.time >= time(4, 0)) &
        (df_m1['ny_time'].dt.time < time(5, 0))
    ]
    return df_filtered

def main():
    print("\n--- Timezone Info ---")
    print_mt5_time_info()

    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    symbol = "EURUSD"

    df_m1 = fetch_data(symbol, mt5.TIMEFRAME_M1, bars=2000)
    if df_m1 is None:
        print("Failed to fetch M1 data")
        mt5.shutdown()
        return

    df_m1['time'] = pd.to_datetime(df_m1['time'], utc=True)

    print("Sample 1M candle times:")
    for _, row in df_m1.head(5).iterrows():
        ny_time = row['time'].tz_convert(NY_TZ)
        print(f"UTC: {row['time']} | NY: {ny_time}")

    range_info = get_3am_h1_range(symbol)  # <-- changed to 3am
    if range_info is None:
        print("No 3AM H1 range info.")
        mt5.shutdown()
        return

    bias, breakout_time = detect_1m_breakout(df_m1, range_info['high'], range_info['low'], range_info['end_time'])
    if breakout_time is None:
        print("No breakout occurred during 4:00-5:00 AM NY time.")  # changed time here
        mt5.shutdown()
        return

    print_times(f"Breakout detected: {bias.upper()} at", breakout_time.tz_convert(UTC_TZ))

    df_hunt = filter_hunt_window(df_m1, breakout_time)
    print(f"\n--- HUNTING SETUPS ({bias.upper()}) from 4:00 to 5:00 AM NY ---")  # changed window time here
    print(f"Candles in 4-5 AM NY window: {len(df_hunt)}")
    print(df_hunt.head())

    if df_hunt.empty:
        print("No candles in the 4-5 AM NY hunting window.")
        mt5.shutdown()
        return

    df_setups = detect_displacements_with_fvg(df_hunt)
    print(f"Number of setups detected: {len(df_setups)}")

    if df_setups.empty:
        print("No setups detected.")
        mt5.shutdown()
        return

    trades = []
    for _, setup in df_setups.iterrows():
        trade = calculate_trade_levels(setup, range_info)
        trades.append(trade)

    trades_df = pd.DataFrame(trades)
    print("\n--- Trade Ideas ---")
    print(trades_df)

    print("\n--- DETECTED SETUPS ---")
    print(df_setups)

    mt5.shutdown()

if __name__ == "__main__":
    main()
