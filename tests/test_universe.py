"""Tests for Universe: definition of tradable assets."""
from pathlib import Path

import pandas as pd
import pytest

from src.data.universe import Universe


@pytest.fixture
def mock_ticker_data() -> list[dict]:
    """Mock 24h ticker data from Binance API."""
    return [
        {"symbol": "BTCUSDT", "quoteVolume": "50000000000"},  # $50B
        {"symbol": "ETHUSDT", "quoteVolume": "20000000000"},  # $20B
        {"symbol": "BNBUSDT", "quoteVolume": "5000000000"},   # $5B
        {"symbol": "SOLUSDT", "quoteVolume": "3000000000"},   # $3B
        {"symbol": "XRPUSDT", "quoteVolume": "2000000000"},   # $2B
        {"symbol": "ADAUSDT", "quoteVolume": "1000000000"},   # $1B
        {"symbol": "DOGEUSDT", "quoteVolume": "800000000"},   # $800M
        {"symbol": "AVAXUSDT", "quoteVolume": "500000000"},   # $500M
        {"symbol": "LINKUSDT", "quoteVolume": "300000000"},   # $300M
        {"symbol": "DOTUSDT", "quoteVolume": "200000000"},    # $200M
        {"symbol": "MATICUSDT", "quoteVolume": "150000000"},  # $150M
        {"symbol": "SHIBUSDT", "quoteVolume": "50000000"},    # $50M (below threshold)
        {"symbol": "PEPEUSDT", "quoteVolume": "30000000"},    # $30M (below threshold)
        {"symbol": "BTCBRL", "quoteVolume": "1000000000"},    # Not USDT pair
        {"symbol": "ETHBTC", "quoteVolume": "500000000"},     # Not USDT pair
    ]


class TestUniverse:
    def test_filter_by_usdt_only(self, mock_ticker_data: list[dict]):
        """Universe should only include USDT pairs."""
        universe = Universe(min_volume_usd=1e8, min_history_days=0)
        symbols = universe.filter_symbols(mock_ticker_data)
        for s in symbols:
            assert s.endswith("USDT")

    def test_filter_by_volume(self, mock_ticker_data: list[dict]):
        """Universe should exclude symbols below volume threshold."""
        universe = Universe(min_volume_usd=1e8, min_history_days=0)  # $100M
        symbols = universe.filter_symbols(mock_ticker_data)
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "SHIBUSDT" not in symbols  # $50M < $100M
        assert "PEPEUSDT" not in symbols  # $30M < $100M

    def test_sort_by_volume_desc(self, mock_ticker_data: list[dict]):
        """Symbols should be sorted by volume descending."""
        universe = Universe(min_volume_usd=1e8, min_history_days=0)
        symbols = universe.filter_symbols(mock_ticker_data)
        assert symbols[0] == "BTCUSDT"
        assert symbols[1] == "ETHUSDT"

    def test_limit_count(self, mock_ticker_data: list[dict]):
        """Should respect max_symbols limit."""
        universe = Universe(min_volume_usd=1e8, min_history_days=0, max_symbols=5)
        symbols = universe.filter_symbols(mock_ticker_data)
        assert len(symbols) == 5

    def test_default_universe(self):
        """Default universe should return a predefined list of major pairs."""
        universe = Universe()
        default = universe.get_default_universe()
        assert "BTCUSDT" in default
        assert "ETHUSDT" in default
        assert "BNBUSDT" in default
        assert "SOLUSDT" in default
        assert len(default) >= 10

    def test_get_metadata(self):
        """Should return metadata for known symbols."""
        universe = Universe()
        meta = universe.get_metadata("BTCUSDT")
        assert meta is not None
        assert meta["symbol"] == "BTCUSDT"
        assert "category" in meta

    def test_get_metadata_unknown(self):
        """Should return None for unknown symbols."""
        universe = Universe()
        meta = universe.get_metadata("UNKNOWNUSDT")
        assert meta is None
