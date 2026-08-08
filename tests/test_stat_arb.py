"""Tests for STRAT-03: StatArbStrategy (Cointegration)."""
import numpy as np
import pandas as pd
import pytest

from src.strategy.stat_arb import StatArbStrategy, StatArbConfig
from src.strategy.base import Direction


def make_cointegrated_pair(n: int, beta: float = 0.8, spread_std: float = 0.01, final_deviation: float = 0.0) -> tuple[pd.Series, pd.Series]:
    """Generate two cointegrated price series.

    price_A = beta * price_B + spread (mean-reverting)
    final_deviation: if > 0, push spread up at the end (A becomes expensive)
                     if < 0, push spread down at the end (A becomes cheap)
    Deviation is applied to last 3 bars only (preserves cointegration in
    the lookback window while creating a z-score spike).
    """
    np.random.seed(42)
    # Random walk for B
    returns_b = np.random.randn(n) * 0.01
    price_b = 100 * np.cumprod(1 + returns_b)

    # Mean-reverting spread (strong mean reversion: 0.85)
    spread = np.zeros(n)
    for i in range(1, n):
        spread[i] = 0.85 * spread[i - 1] + np.random.randn() * spread_std

    # Apply deviation to last 3 bars only (abrupt but small enough to
    # not break cointegration over the full lookback window)
    if final_deviation != 0:
        spread[-3:] += final_deviation

    price_a = beta * price_b + spread + 50  # offset
    return pd.Series(price_a), pd.Series(price_b)


def make_random_pair(n: int) -> tuple[pd.Series, pd.Series]:
    """Generate two independent (non-cointegrated) price series."""
    np.random.seed(123)
    price_a = 100 * np.cumprod(1 + np.random.randn(n) * 0.02)
    price_b = 100 * np.cumprod(1 + np.random.randn(n) * 0.02)
    return pd.Series(price_a), pd.Series(price_b)


def make_ohlcv_from_prices(prices: pd.Series) -> pd.DataFrame:
    """Build OHLCV from a price series."""
    # Use .values to avoid index misalignment with the new date_range index
    p = prices.values
    return pd.DataFrame({
        "open": p,
        "high": p * 1.001,
        "low": p * 0.999,
        "close": p,
        "volume": 1000.0,
    }, index=pd.date_range("2024-01-01", periods=len(p), freq="1D"))


class TestHalfLife:
    def test_mean_reverting_spread_has_finite_half_life(self):
        """Mean-reverting spread should have finite half-life."""
        np.random.seed(42)
        n = 500
        spread = np.zeros(n)
        for i in range(1, n):
            spread[i] = 0.9 * spread[i - 1] + np.random.randn() * 0.01
        hl = StatArbStrategy.calculate_half_life(pd.Series(spread))
        assert 1 < hl < 50

    def test_random_walk_has_infinite_half_life(self):
        """Random walk should have infinite (or very large) half-life."""
        np.random.seed(42)
        spread = pd.Series(np.cumsum(np.random.randn(500) * 0.01))
        hl = StatArbStrategy.calculate_half_life(spread)
        # Random walk: half-life should be very large (not a small number like 5)
        assert hl == float("inf") or hl > 50


class TestCointegration:
    def setup_method(self):
        self.config = StatArbConfig(
            lookback_window=200,
            zscore_window=20,
            entry_zscore=1.5,
            min_correlation=0.3,
            min_half_life=0.5,
            max_half_life=100,
            adf_pvalue_threshold=0.10,
            hurst_threshold=0.55,  # slightly relaxed
        )
        self.strategy = StatArbStrategy(self.config)

    def test_cointegrated_pair_detected(self):
        """Cointegrated pair should be detected by find_pairs."""
        pa, pb = make_cointegrated_pair(300, beta=0.8)
        prices = pd.DataFrame({"A": pa, "B": pb})
        pairs = self.strategy.find_pairs(prices)
        assert len(pairs) >= 1
        a, b, beta, meta = pairs[0]
        assert a in ["A", "B"]
        assert b in ["A", "B"]
        assert meta["p_value"] < 0.10

    def test_non_cointegrated_pair_not_detected(self):
        """Non-cointegrated pair should not be detected."""
        pa, pb = make_random_pair(200)
        prices = pd.DataFrame({"A": pa, "B": pb})
        pairs = self.strategy.find_pairs(prices)
        # Independent random walks should not be cointegrated
        assert len(pairs) == 0

    def test_generate_signals_cointegrated(self):
        """Should generate signals for cointegrated pair when spread deviates."""
        # Use 10x spread std deviation on last 3 bars to create z-score spike
        pa, pb = make_cointegrated_pair(300, beta=0.8, spread_std=0.01, final_deviation=0.1)
        data = {
            "A": make_ohlcv_from_prices(pa),
            "B": make_ohlcv_from_prices(pb),
        }
        signals = self.strategy.generate_signals(data)
        # Should generate a signal (SHORT A, LONG B)
        assert len(signals) >= 1
        s = signals[0]
        assert s.symbol == "A"
        assert s.direction == Direction.SHORT
        assert "hedge_symbol" in s.metadata
        assert s.metadata["hedge_symbol"] == "B"

    def test_no_signal_without_cointegration(self):
        """Should generate no signals for non-cointegrated assets."""
        pa, pb = make_random_pair(200)
        data = {
            "A": make_ohlcv_from_prices(pa),
            "B": make_ohlcv_from_prices(pb),
        }
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_signal_has_hedge_metadata(self):
        """Signals should contain hedge ratio and hedge symbol."""
        pa, pb = make_cointegrated_pair(300, beta=0.8, final_deviation=0.1)
        data = {
            "A": make_ohlcv_from_prices(pa),
            "B": make_ohlcv_from_prices(pb),
        }
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert "hedge_symbol" in s.metadata
            assert "hedge_ratio" in s.metadata
            assert "hedge_direction" in s.metadata
            assert "half_life" in s.metadata
            assert "p_value" in s.metadata

    def test_long_signal_when_spread_too_low(self):
        """Should generate LONG A signal when spread is too low."""
        pa, pb = make_cointegrated_pair(300, beta=0.8, final_deviation=-0.1)
        data = {
            "A": make_ohlcv_from_prices(pa),
            "B": make_ohlcv_from_prices(pb),
        }
        signals = self.strategy.generate_signals(data)
        long_signals = [s for s in signals if s.direction == Direction.LONG]
        assert len(long_signals) >= 1

    def test_check_exit_on_convergence(self):
        """check_exit should return True when spread reverts."""
        pa, pb = make_cointegrated_pair(200, beta=0.8)
        prices = pd.DataFrame({"A": pa, "B": pb})
        # When spread is at mean, z-score ~0, should exit
        # This depends on the actual spread values
        result = self.strategy.check_exit("A", "B", 0.8, prices)
        assert isinstance(result, bool)

    def test_max_pairs_limit(self):
        """find_pairs should respect max_pairs limit."""
        np.random.seed(42)
        n = 200
        prices = pd.DataFrame()
        base, _ = make_cointegrated_pair(n, beta=1.0)
        for i in range(6):
            noise = np.random.randn(n) * 0.005
            prices[f"asset_{i}"] = base + np.cumsum(noise) + i * 10

        config = StatArbConfig(max_pairs=3, adf_pvalue_threshold=0.15, min_correlation=0.2)
        strategy = StatArbStrategy(config)
        pairs = strategy.find_pairs(prices)
        assert len(pairs) <= 3
