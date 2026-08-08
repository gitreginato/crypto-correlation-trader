#!/usr/bin/env python3
"""Download historical OHLCV data from Binance Vision and/or Binance REST API.

Usage:
    python scripts/download_historical.py --symbols BTCUSDT,ETHUSDT --start 2024-01-01 --end 2024-06-01 --timeframe 5m
    python scripts/download_historical.py --symbols BTCUSDT --start 2024-01-01 --timeframe 1h --source vision
    python scripts/download_historical.py --universe default --start 2024-01-01 --timeframe 1d
"""
import argparse
import io
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.parquet_store import ParquetStore
from src.data.universe import Universe

# Binance Vision base URL
VISION_BASE = "https://data.binance.vision/data/spot"
# Binance REST API
API_BASE = "https://api.binance.com/api/v3"

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def download_from_vision(symbol: str, timeframe: str, year: int, month: int) -> pd.DataFrame:
    """Download monthly klines from Binance Vision.

    Args:
        symbol: e.g. "BTCUSDT"
        timeframe: e.g. "5m", "1h", "1d"
        year: e.g. 2024
        month: 1-12

    Returns:
        DataFrame with OHLCV data, or empty DataFrame if not available.
    """
    url = f"{VISION_BASE}/monthly/klines/{symbol}/{timeframe}/{symbol}-{timeframe}-{year}-{month:02d}.zip"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return pd.DataFrame()
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] Vision download failed for {symbol} {year}-{month:02d}: {e}")
        return pd.DataFrame()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as f:
            df = pd.read_csv(f, header=None, names=KLINE_COLUMNS)

    # Convert types
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").astype(int)
    df = df.drop(columns=["ignore"])
    return df


def download_from_api(symbol: str, timeframe: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    """Download klines from Binance REST API (paginated, 1000 per request).

    Args:
        symbol: e.g. "BTCUSDT"
        timeframe: e.g. "5m", "1h", "1d"
        start_ts: Start time in milliseconds
        end_ts: End time in milliseconds

    Returns:
        DataFrame with OHLCV data.
    """
    all_data: list[list] = []
    current_start = start_ts

    while current_start < end_ts:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": current_start,
            "endTime": end_ts,
            "limit": 1000,
        }
        try:
            resp = requests.get(f"{API_BASE}/klines", params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [WARN] API request failed for {symbol}: {e}")
            time.sleep(2)
            continue

        data = resp.json()
        if not data:
            break

        all_data.extend(data)
        # Move start to after the last candle
        current_start = data[-1][6] + 1  # close_time + 1ms

        # Rate limit: stay safe
        time.sleep(0.2)

        if len(data) < 1000:
            break

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=KLINE_COLUMNS)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").astype(int)
    df = df.drop(columns=["ignore"])
    return df


def download_symbol(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    store: ParquetStore,
    source: str = "vision",
) -> int:
    """Download all historical data for a symbol and store in Parquet.

    Args:
        symbol: e.g. "BTCUSDT"
        timeframe: e.g. "5m", "1h", "1d"
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"
        store: ParquetStore instance
        source: "vision" for Binance Vision, "api" for REST API

    Returns:
        Number of candles downloaded.
    """
    start = pd.Timestamp(start_date, tz="UTC")
    end = pd.Timestamp(end_date, tz="UTC")
    total_candles = 0

    if source == "vision":
        # Download month by month from Vision
        current = start.to_period("M")
        end_period = end.to_period("M")
        while current <= end_period:
            year, month = current.year, current.month
            print(f"  Downloading {symbol} {timeframe} {year}-{month:02d} from Vision...")

            # Try monthly file first
            df = download_from_vision(symbol, timeframe, year, month)
            if df.empty:
                # Fallback to daily files
                print("    Monthly not found, trying daily files...")
                days_in_month = pd.Period(f"{year}-{month:02d}").days_in_month
                daily_dfs = []
                for day in range(1, days_in_month + 1):
                    day_str = f"{year}-{month:02d}-{day:02d}"
                    day_url = f"{VISION_BASE}/daily/klines/{symbol}/{timeframe}/{symbol}-{timeframe}-{day_str}.zip"
                    try:
                        resp = requests.get(day_url, timeout=15)
                        if resp.status_code == 404:
                            continue
                        resp.raise_for_status()
                        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                            csv_name = zf.namelist()[0]
                            with zf.open(csv_name) as f:
                                day_df = pd.read_csv(f, header=None, names=KLINE_COLUMNS)
                        daily_dfs.append(day_df)
                    except requests.RequestException:
                        continue
                    time.sleep(0.1)
                if daily_dfs:
                    df = pd.concat(daily_dfs, ignore_index=True)
                    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
                    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
                    for col in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").astype(int)
                    df = df.drop(columns=["ignore"])

            if not df.empty:
                store.write(symbol, timeframe, df)
                total_candles += len(df)
                print(f"    Stored {len(df)} candles")
            else:
                print(f"    No data found for {year}-{month:02d}")

            current = current + 1

    elif source == "api":
        print(f"  Downloading {symbol} {timeframe} from API ({start_date} to {end_date})...")
        start_ts = int(start.timestamp() * 1000)
        end_ts = int(end.timestamp() * 1000)
        df = download_from_api(symbol, timeframe, start_ts, end_ts)
        if not df.empty:
            store.write(symbol, timeframe, df)
            total_candles = len(df)
            print(f"    Stored {total_candles} candles")
        else:
            print("    No data returned from API")

    return total_candles


def main():
    parser = argparse.ArgumentParser(description="Download historical OHLCV data from Binance")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols (e.g. BTCUSDT,ETHUSDT)")
    parser.add_argument("--universe", type=str, choices=["default"], help="Use default universe of 25 symbols")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--timeframe", type=str, default="1h", help="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("--source", type=str, choices=["vision", "api"], default="vision", help="Data source")
    parser.add_argument("--data-dir", type=str, default="data/parquet", help="Parquet data directory")
    args = parser.parse_args()

    # Determine symbols
    if args.universe == "default":
        universe = Universe()
        symbols = universe.get_default_universe()
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        parser.error("Either --symbols or --universe must be specified")

    end_date = args.end or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")

    print(f"Downloading {len(symbols)} symbols: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
    print(f"Period: {args.start} to {end_date}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Source: {args.source}")
    print()

    store = ParquetStore(base_dir=args.data_dir)
    grand_total = 0

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}")
        try:
            count = download_symbol(symbol, args.timeframe, args.start, end_date, store, args.source)
            grand_total += count
        except Exception as e:
            print(f"  [ERROR] {symbol}: {e}")
        print()

    print(f"Done! Total candles downloaded: {grand_total:,}")
    print(f"Data stored in: {args.data_dir}")

    # Show what we have
    available = store.get_available_symbols()
    print(f"Available symbols in store: {len(available)}")
    for sym in available:
        date_range = store.get_date_range(sym, args.timeframe)
        if date_range:
            print(f"  {sym}: {date_range[0].date()} to {date_range[1].date()}")


if __name__ == "__main__":
    main()
