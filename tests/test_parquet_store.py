"""Tests for ParquetStore: read/write OHLCV data in Parquet format."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.parquet_store import ParquetStore


@pytest.fixture
def sample_klines_df() -> pd.DataFrame:
    """Generate a small synthetic OHLCV DataFrame for testing."""
    rng = np.random.default_rng(seed=42)
    n = 100
    base_ts = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    timestamps = pd.date_range(base_ts, periods=n, freq="5min", tz="UTC")
    return pd.DataFrame({
        "open_time": timestamps,
        "open": rng.uniform(40000, 42000, n),
        "high": rng.uniform(42000, 43000, n),
        "low": rng.uniform(39000, 40000, n),
        "close": rng.uniform(40000, 42000, n),
        "volume": rng.uniform(1, 100, n),
        "close_time": timestamps + pd.Timedelta(minutes=5),
        "quote_volume": rng.uniform(50000, 500000, n),
        "trades": rng.integers(10, 500, n),
        "taker_buy_base": rng.uniform(0.5, 50, n),
        "taker_buy_quote": rng.uniform(25000, 250000, n),
    })


@pytest.fixture
def store(tmp_path: Path) -> ParquetStore:
    """Create a ParquetStore with a temporary directory."""
    return ParquetStore(base_dir=str(tmp_path))


class TestParquetStoreWrite:
    def test_write_single_month(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Writing data should create a Parquet file in the correct partition."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        files = list(Path(store.base_dir).rglob("*.parquet"))
        assert len(files) == 1
        assert "BTCUSDT" in str(files[0])
        assert "5m" in str(files[0])

    def test_write_creates_correct_partition(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Data from January 2024 should be in year=2024/month=01 partition."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        files = list(Path(store.base_dir).rglob("*.parquet"))
        assert any("year=2024" in str(f) for f in files)
        assert any("month=01" in str(f) for f in files)

    def test_write_multiple_months(self, store: ParquetStore):
        """Data spanning multiple months should be split into multiple files."""
        rng = np.random.default_rng(seed=99)
        n = 1500  # ~62 days at 1h freq, spans Jan + Feb
        ts = pd.date_range("2024-01-15", periods=n, freq="1h", tz="UTC")
        df = pd.DataFrame({
            "open_time": ts,
            "open": rng.uniform(100, 200, n),
            "high": rng.uniform(200, 210, n),
            "low": rng.uniform(90, 100, n),
            "close": rng.uniform(100, 200, n),
            "volume": rng.uniform(1, 50, n),
            "close_time": ts + pd.Timedelta(hours=1),
            "quote_volume": rng.uniform(100, 10000, n),
            "trades": rng.integers(5, 100, n),
            "taker_buy_base": rng.uniform(0.5, 25, n),
            "taker_buy_quote": rng.uniform(50, 5000, n),
        })
        store.write("ETHUSDT", "1h", df)
        files = list(Path(store.base_dir).rglob("*.parquet"))
        assert len(files) >= 2

    def test_write_is_idempotent(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Writing the same data twice should not duplicate rows."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        store.write("BTCUSDT", "5m", sample_klines_df)
        df_read = store.read("BTCUSDT", "5m")
        assert len(df_read) == len(sample_klines_df)


class TestParquetStoreRead:
    def test_read_returns_dataframe(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Reading should return a DataFrame with the written data."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        df = store.read("BTCUSDT", "5m")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_klines_df)

    def test_read_nonexistent_returns_empty(self, store: ParquetStore):
        """Reading a symbol that doesn't exist should return an empty DataFrame."""
        df = store.read("NONEXIST", "5m")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_read_preserves_columns(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Read data should have the same columns as written data."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        df = store.read("BTCUSDT", "5m")
        for col in sample_klines_df.columns:
            assert col in df.columns

    def test_read_with_date_range(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Reading with a date range should filter correctly."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        df = store.read(
            "BTCUSDT", "5m",
            start="2024-01-01 00:10:00",
            end="2024-01-01 00:30:00",
        )
        assert len(df) == 5  # 5 candles between 00:10 and 00:30 at 5min


class TestParquetStoreIntegrity:
    def test_data_roundtrip_preserves_values(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Values should be preserved after write and read."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        df = store.read("BTCUSDT", "5m").sort_values("open_time").reset_index(drop=True)
        expected = sample_klines_df.sort_values("open_time").reset_index(drop=True)
        pd.testing.assert_frame_equal(df, expected, check_dtype=False)

    def test_get_available_symbols(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Should return list of symbols that have data."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        store.write("ETHUSDT", "5m", sample_klines_df)
        symbols = store.get_available_symbols()
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols

    def test_get_date_range(self, store: ParquetStore, sample_klines_df: pd.DataFrame):
        """Should return the min and max dates for a symbol."""
        store.write("BTCUSDT", "5m", sample_klines_df)
        date_range = store.get_date_range("BTCUSDT", "5m")
        assert date_range is not None
        start, end = date_range
        assert start.year == 2024
        assert end.year == 2024
