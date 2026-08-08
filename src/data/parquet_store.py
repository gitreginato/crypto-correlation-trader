"""ParquetStore: read/write OHLCV data in Parquet format.

Partitions data by exchange/market/symbol/timeframe/year/month.
Supports incremental writes (idempotent) and date-range reads.
"""
from pathlib import Path
from typing import Optional

import pandas as pd

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote",
]


class ParquetStore:
    """Store and retrieve OHLCV data in Parquet format."""

    def __init__(self, base_dir: str = "data/parquet", exchange: str = "binance", market: str = "spot"):
        self.base_dir = Path(base_dir) / exchange / market
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_partition_dir(self, symbol: str, timeframe: str, year: int, month: int) -> Path:
        return self.base_dir / symbol / timeframe / f"year={year}" / f"month={month:02d}"

    def _get_partition_file(self, symbol: str, timeframe: str, year: int, month: int) -> Path:
        return self._get_partition_dir(symbol, timeframe, year, month) / \
            f"{symbol}-{timeframe}-{year}-{month:02d}.parquet"

    def write(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        """Write OHLCV data to Parquet, partitioned by year/month.

        If data for the same partition already exists, it is merged
        and deduplicated by open_time (idempotent).
        """
        if df.empty:
            return

        df = df.copy()
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
        df["close_time"] = pd.to_datetime(df["close_time"], utc=True)
        df = df.sort_values("open_time").drop_duplicates(subset=["open_time"])

        df["year"] = df["open_time"].dt.year
        df["month"] = df["open_time"].dt.month

        for (year, month), group in df.groupby(["year", "month"]):
            year, month = int(str(year)), int(str(month))
            group = group.drop(columns=["year", "month"])
            file_path = self._get_partition_file(symbol, timeframe, year, month)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, group], ignore_index=True)
                combined = combined.sort_values("open_time").drop_duplicates(subset=["open_time"])
                combined.to_parquet(file_path, index=False)
            else:
                group.to_parquet(file_path, index=False)

    def read(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read OHLCV data from Parquet, optionally filtered by date range."""
        symbol_dir = self.base_dir / symbol / timeframe
        if not symbol_dir.exists():
            return pd.DataFrame(columns=KLINE_COLUMNS)

        parquet_files = list(symbol_dir.rglob("*.parquet"))
        if not parquet_files:
            return pd.DataFrame(columns=KLINE_COLUMNS)

        dfs = [pd.read_parquet(f) for f in parquet_files]
        df = pd.concat(dfs, ignore_index=True)
        df = df.sort_values("open_time").drop_duplicates(subset=["open_time"]).reset_index(drop=True)

        if start:
            start_dt = pd.Timestamp(start, tz="UTC")
            df = df[df["open_time"] >= start_dt]
        if end:
            end_dt = pd.Timestamp(end, tz="UTC")
            df = df[df["open_time"] <= end_dt]

        return df.reset_index(drop=True)

    def get_available_symbols(self) -> list[str]:
        """Return list of symbols that have data stored."""
        if not self.base_dir.exists():
            return []
        symbols = []
        for entry in self.base_dir.iterdir():
            if entry.is_dir():
                symbols.append(entry.name)
        return sorted(symbols)

    def get_date_range(self, symbol: str, timeframe: str) -> Optional[tuple[pd.Timestamp, pd.Timestamp]]:
        """Return (min_date, max_date) for a symbol, or None if no data."""
        df = self.read(symbol, timeframe)
        if df.empty:
            return None
        return df["open_time"].min(), df["open_time"].max()

    def get_available_timeframes(self, symbol: str) -> list[str]:
        """Return list of timeframes available for a symbol."""
        symbol_dir = self.base_dir / symbol
        if not symbol_dir.exists():
            return []
        return sorted([d.name for d in symbol_dir.iterdir() if d.is_dir()])
