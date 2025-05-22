from datetime import datetime, timedelta
import pytz
import MetaTrader5 as mt5
import pandas as pd

NY_TZ = pytz.timezone("America/New_York")
UTC_TZ = pytz.utc

def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")

def get_mt5_server_utc_time():
    tick = mt5.symbol_info_tick("EURUSD")
    if tick is None:
        raise RuntimeError("Failed to get MT5 server tick")
    return datetime.utcfromtimestamp(tick.time).replace(tzinfo=UTC_TZ)

def get_mt5_timezone_offset_vs_ny():
    now_utc = datetime.now(UTC_TZ)
    now_ny = now_utc.astimezone(NY_TZ)
    now_mt5 = get_mt5_server_utc_time()
    server_offset = (now_mt5 - now_utc).total_seconds() / 3600
    ny_offset = (now_ny - now_utc).total_seconds() / 3600
    return server_offset - ny_offset

def get_2am_ny_candle(symbol="EURUSD"):
    offset_hours = get_mt5_timezone_offset_vs_ny()
    today_ny = datetime.now(NY_TZ).replace(hour=2, minute=0, second=0, microsecond=0)
    server_time = today_ny + timedelta(hours=offset_hours)

    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_H1, server_time, 1)
    if rates is None or len(rates) == 0:
        raise RuntimeError("Failed to fetch 2AM NY candle")

    candle = rates[0]
    ny_candle_time = datetime.utcfromtimestamp(candle['time']).replace(tzinfo=UTC_TZ).astimezone(NY_TZ)
    return {
        "ny_time": ny_candle_time,
        "open": candle['open'],
        "high": candle['high'],
        "low": candle['low'],
        "close": candle['close']
    }

def was_2am_high_or_low_taken(symbol="EURUSD", bars_to_check=30):
    initialize_mt5()
    candle = get_2am_ny_candle(symbol)
    print(f"2AM NY Candle at {candle['ny_time'].strftime('%Y-%m-%d %I:%M %p')} | High: {candle['high']}, Low: {candle['low']}, Open:{candle['open']}, Close:{candle['close']}")

    now = datetime.now()
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, now, bars_to_check)
    if rates is None or len(rates) == 0:
        raise RuntimeError("Failed to fetch M1 data")

    df = pd.DataFrame(rates)

    high_taken = df['high'].max() > candle['high']
    low_taken = df['low'].min() < candle['low']

    print(f"High taken out? {'YES ✅' if high_taken else 'NO ❌'}")
    print(f"Low taken out? {'YES ✅' if low_taken else 'NO ❌'}")

    return high_taken, low_taken

# Run it as a script
if __name__ == "__main__":
    was_2am_high_or_low_taken("EURUSD")
    mt5.shutdown()
