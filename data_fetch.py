import MetaTrader5 as mt5
import pandas as pd

def initialize_mt5(login=None, password=None, server=None):
    """
    Initializes connection to MetaTrader 5.
    If login, password, and server are provided, it logs in with credentials.
    """
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"MT5 initialize failed, error code: {mt5.last_error()}")
        return False
    return True

def shutdown_mt5():
    """
    Shuts down the MetaTrader 5 connection.
    """
    mt5.shutdown()

def fetch_data(symbol, timeframe, bars=500):
    """
    Fetches historical price data for the given symbol and timeframe.
    Returns a pandas DataFrame with a datetime-indexed 'time' column.
    """
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol: {symbol}, MT5 Error: {mt5.last_error()}")
        return None

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        print(f"No data for symbol: {symbol}")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df
