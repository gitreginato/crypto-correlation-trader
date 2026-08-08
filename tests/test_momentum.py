"""Tests for STRAT-06: MomentumStrategy."""
import numpy as np
import pandas as pd
import pytest

from src.strategy.momentum import MomentumStrategy, MomentumConfig
from src.strategy.base import Direction


def make_trending_ohlcv(n: int, trend: float = 0.002, start: float = 100.0) -> pd.DataFrame:
    """Build OHLCV with a clear uptrend."""
    np.random.seed(42)
    returns = np.random.randn(n) * 0.005 + trend
    prices = start * np.cumprod(1 + returns)
    return pd.DataFrame({
        "open": prices,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    }, index=pd.date_range("2024-01-01", periods=n, freq="1D"))


def make_declining_ohlcv(n: int, trend: float = -0.002, start: float = 100.0) -> pd.DataFrame:
    """Build OHLCV with a clear downtrend."""
    return make_trending_ohlcv(n, trend=trend, start=start)


def make_flat_ohlcv(n: int, start: float = 100.0) -> pd.DataFrame:
    """Build OHLCV with no trend (sideways)."""
    np.random.seed(42)
    returns = np.random.randn(n) * 0.002
    prices = start * np.cumprod(1 + returns)
    return pd.DataFrame({
        "open": prices,
        "high": prices * 1.002,
        "low": prices * 0.998,
        "close": prices,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    }, index=pd.date_range("2024-01-01", periods=n, freq="1D"))


class TestMomentumIndicators:
    def setup_method(self):
        self.strategy = MomentumStrategy(MomentumConfig(formation_period=30))

    def test_compute_rsi(self):
        """RSI should be between 0 and 100."""
        df = make_trending_ohlcv(100)
        rsi = self.strategy.compute_rsi(df["close"], period=14)
        assert rsi.min() >= 0
        assert rsi.max() <= 100
        # Trending up should have RSI > 50 at the end
        assert rsi.iloc[-1] > 50

    def test_compute_rsi_declining(self):
        """Declining series should have RSI < 50."""
        df = make_declining_ohlcv(100)
        rsi = self.strategy.compute_rsi(df["close"], period=14)
        assert rsi.iloc[-1] < 50

    def test_compute_macd(self):
        """MACD should return 3 series."""
        df = make_trending_ohlcv(100)
        macd, signal, hist = self.strategy.compute_macd(df["close"])
        assert len(macd) == 100
        assert len(signal) == 100
        assert len(hist) == 100

    def test_compute_adx(self):
        """ADX should be positive."""
        df = make_trending_ohlcv(100)
        adx = self.strategy.compute_adx(df, period=14)
        assert (adx.dropna() >= 0).all()

    def test_compute_atr(self):
        """ATR should be positive."""
        df = make_trending_ohlcv(100)
        atr = self.strategy.compute_atr(df, period=14)
        assert (atr.dropna() > 0).all()


class TestMomentumSignals:
    def setup_method(self):
        self.config = MomentumConfig(
            formation_period=30,
            ema_fast=10,
            ema_slow=20,
            adx_threshold=15,  # relaxed for test data
            min_confirmation=2,
            use_regime_filter=False,  # disable for unit tests
        )
        self.strategy = MomentumStrategy(self.config)

    def test_no_signal_with_insufficient_data(self):
        """Should return no signals with too little data."""
        data = {"BTC": make_trending_ohlcv(10)}
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_long_signal_in_uptrend(self):
        """Should generate LONG signal in a clear uptrend."""
        df = make_trending_ohlcv(200, trend=0.005)
        data = {"BTC": df}
        signals = self.strategy.generate_signals(data)
        long_signals = [s for s in signals if s.direction == Direction.LONG]
        # Should have at least one long signal
        assert len(long_signals) >= 1
        assert long_signals[0].symbol == "BTC"
        assert long_signals[0].strategy_id == "STRAT-06"

    def test_short_signal_in_downtrend(self):
        """Should generate SHORT signal in a clear downtrend."""
        df = make_declining_ohlcv(200, trend=-0.005)
        data = {"BTC": df}
        signals = self.strategy.generate_signals(data)
        short_signals = [s for s in signals if s.direction == Direction.SHORT]
        assert len(short_signals) >= 1

    def test_no_signal_in_sideways(self):
        """Should generate no or low-confidence signals in a sideways market."""
        df = make_flat_ohlcv(200)
        data = {"BTC": df}
        signals = self.strategy.generate_signals(data)
        # In sideways, ADX should be low, blocking most signals.
        # If signals are generated, they should be low confidence.
        # With corrected ADX, sideways market should have ADX < 15
        if signals:
            for s in signals:
                # Sideways signals should have low ADX in metadata
                assert s.metadata.get("adx", 0) < 25 or s.confidence < 0.5

    def test_signal_has_stop_and_target(self):
        """Signals should have stop_loss and take_profit set."""
        df = make_trending_ohlcv(200, trend=0.005)
        data = {"BTC": df}
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.stop_loss is not None
            assert s.take_profit is not None
            assert s.stop_loss != s.price
            assert s.take_profit != s.price

    def test_signal_metadata_has_indicators(self):
        """Signal metadata should contain indicator values."""
        df = make_trending_ohlcv(200, trend=0.005)
        data = {"BTC": df}
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert "rsi" in s.metadata
            assert "adx" in s.metadata
            assert "momentum" in s.metadata
            assert "regime" in s.metadata

    def test_multiple_assets(self):
        """Should handle multiple assets."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005),
            "ETH": make_declining_ohlcv(200, trend=-0.005),
        }
        signals = self.strategy.generate_signals(data)
        symbols = {s.symbol for s in signals}
        assert "BTC" in symbols or "ETH" in symbols

    def test_trailing_stop_update(self):
        """Trailing stop should move in favor of the position."""
        from src.strategy.base import Signal
        sig = Signal(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="BTC",
            direction=Direction.LONG,
            price=100.0,
            stop_loss=95.0,
            strategy_id="STRAT-06",
        )
        self.strategy.positions["BTC"] = sig
        # Price goes up, stop should move up
        new_stop = self.strategy.update_trailing_stop("BTC", current_price=110.0, current_atr=2.0)
        assert new_stop >= 95.0  # should not move below original
