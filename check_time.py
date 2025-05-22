from datetime import datetime
import pytz

def print_current_times():
    UTC_TZ = pytz.utc
    NY_TZ = pytz.timezone('America/New_York')

    # Get current time in UTC (timezone aware)
    now_utc = datetime.now(UTC_TZ)

    # Convert UTC time to New York time
    now_ny = now_utc.astimezone(NY_TZ)

    print(f"Current time UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z %z')}")
    print(f"Current time New York: {now_ny.strftime('%Y-%m-%d %I:%M:%S %p %Z %z')}")

    # Additional: localize naive datetime (now naive) to NY time (if you have naive time)
    naive_now = datetime.now()
    try:
        localized_ny = NY_TZ.localize(naive_now)
        print(f"Naive now localized to NY: {localized_ny.strftime('%Y-%m-%d %I:%M:%S %p %Z %z')}")
    except Exception as e:
        print(f"Error localizing naive datetime: {e}")

if __name__ == "__main__":
    print_current_times()
