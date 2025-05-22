from data_fetch import initialize_mt5, fetch_data, shutdown_mt5
import MetaTrader5 as mt5

# Replace these with your actual login details
login = 10006453376
password = "@x4uBnFp"
server = "MetaQuotes-Demo"

if not initialize_mt5(login, password, server):
    print("Failed to initialize MT5")
else:
    df = fetch_data("EURUSD", mt5.TIMEFRAME_H1, bars=10)
    if df is not None:
        print(df.head())
    else:
        print("Failed to fetch data")

    shutdown_mt5()
