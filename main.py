from datetime import time, datetime
import pytz
import pandas as pd
import MetaTrader5 as mt5
from data_fetch import fetch_data
from displacement_with_fvg import detect_displacements_with_fvg, calculate_trade_levels

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

    server_dt = datetime.utcfromtimestamp(server_timestamp).replace(tzinfo=pytz.utc)
    ny_time = server_dt.astimezone(pytz.timezone('America/New_York'))

    print(f"🕒 MT5 Server Time (UTC): {server_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    print(f"🌝 MT5 Server Time in New York: {ny_time.strftime('%Y-%m-%d %I:%M:%S %p %Z%z')}")

    return server_dt, ny_time

def find_9am_range(df):
    df['ny_time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    nine_am_candle = df[df['ny_time'].dt.time == time(9, 0)]
    if nine_am_candle.empty:
        print("No 9 AM candle found (NY Time).")
        return None

    row = nine_am_candle.iloc[0]
    return {
        'time': row['time'],
        'high': row['high'],
        'low': row['low'],
        'ny_time': row['ny_time']
    }

def detect_1m_breakout(df_m1, high, low):
    df_m1['ny_time'] = df_m1['time'].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    for _, row in df_m1.iterrows():
        if row['ny_time'].time() < time(10, 0):
            continue

        if row['close'] > high:
            print(f"[1M] Bullish breakout at {row['ny_time']} (NY Time)")
            return 'bullish', row['ny_time']
        elif row['close'] < low:
            print(f"[1M] Bearish breakout at {row['ny_time']} (NY Time)")
            return 'bearish', row['ny_time']
    return None, None

def filter_hunt_window(df_m1, breakout_time):
    df_m1['ny_time'] = df_m1['time'].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    hunt_day = breakout_time.date()
    df_filtered = df_m1[
        (df_m1['ny_time'].dt.date == hunt_day) &
        (df_m1['ny_time'].dt.time >= time(10, 0)) &
        (df_m1['ny_time'].dt.time < time(11, 0))
    ]
    return df_filtered

def main():
    print("\n--- Timezone Info ---")
    print_mt5_time_info()

    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    symbol = "EURUSD"

    df_h1 = fetch_data(symbol, mt5.TIMEFRAME_H1, bars=100)
    if df_h1 is None:
        print("Failed to fetch H1 data")
        mt5.shutdown()
        return

    print("Sample H1 candle times:", df_h1['time'].head(5))
    range_info = find_9am_range(df_h1)
    if range_info is None:
        print("9 AM candle not found, exiting.")
        mt5.shutdown()
        return

    print(f"\n🕘 9 AM NY Candle: Time={range_info['ny_time']} | High={range_info['high']} | Low={range_info['low']}")

    df_m1 = fetch_data(symbol, mt5.TIMEFRAME_M1, bars=1500)
    if df_m1 is None:
        print("Failed to fetch M1 data")
        mt5.shutdown()
        return

    bias, breakout_time = detect_1m_breakout(df_m1, range_info['high'], range_info['low'])
    if breakout_time is None:
        print("No breakout occurred after 10:00 AM NY time.")
        mt5.shutdown()
        return

    print(f"Breakout detected: {bias.upper()} at {breakout_time} NY Time")

    df_hunt = filter_hunt_window(df_m1, breakout_time)
    print(f"\n--- HUNTING SETUPS ({bias.upper()}) from 10:00 to 11:00 AM NY ---")
    print(f"Candles in 10-11 AM NY window: {len(df_hunt)}")
    print(df_hunt.head())

    if df_hunt.empty:
        print("No candles in the 10-11 AM NY hunting window.")
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
