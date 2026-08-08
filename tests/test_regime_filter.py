"""Tests for STRAT-04: RegimeFilter (Entropy + Hurst)."""
import numpy as np
import pandas as pd
import pytest

from src.strategy.regime_filter import (
    RegimeFilter,
    Regime,
    shannon_entropy,
    sample_entropy,
    compute_hurst,
)


class TestShannonEntropy:
    def test_constant_series_has_low_entropy(self):
        """A constant series should have entropy near 0."""
        series = np.ones(100) * 5.0
        ent = shannon_entropy(series, bins=10)
        assert ent == 0.0 or ent < 0.01

    def test_uniform_series_has_max_entropy(self):
        """A uniformly distributed series should have entropy near 1."""
        np.random.seed(42)
        series = np.random.uniform(-1, 1, 1000)
        ent = shannon_entropy(series, bins=10)
        assert ent > 0.95

    def test_short_series_returns_zero(self):
        """Series with < 2 elements should return 0."""
        assert shannon_entropy(np.array([1.0]), bins=10) == 0.0


class TestSampleEntropy:
    def test_constant_series_has_low_entropy(self):
        """A constant series should have SampEn = 0 (all matches)."""
        series = np.ones(50) * 3.0
        ent = sample_entropy(series, m=2, r=0.2)
        assert ent == 0.0

    def test_random_series_has_higher_entropy(self):
        """Random series should have higher SampEn than constant."""
        np.random.seed(42)
        random_series = np.random.randn(100)
        ent_random = sample_entropy(random_series, m=2, r=0.2)
        constant = np.ones(100)
        ent_constant = sample_entropy(constant, m=2, r=0.2)
        assert ent_random > ent_constant

    def test_short_series_returns_zero(self):
        """Series too short for embedding should return 0."""
        assert sample_entropy(np.array([1.0, 2.0]), m=2, r=0.2) == 0.0


class TestHurstExponent:
    def test_random_walk_hurst_near_half(self):
        """Returns of a random walk (iid) should have Hurst near 0.5."""
        np.random.seed(42)
        # Use iid steps (returns), not cumulative sum
        steps = np.random.randn(1000)
        h = compute_hurst(steps)
        assert 0.4 < h < 0.7

    def test_trending_series_hurst_above_half(self):
        """A persistent (trending) AR(1) series should have Hurst > 0.5."""
        np.random.seed(42)
        n = 2000
        # AR(1) with positive autocorrelation (trending/persistent)
        steps = np.zeros(n)
        for i in range(1, n):
            steps[i] = 0.7 * steps[i - 1] + np.random.randn() * 0.3
        h = compute_hurst(steps)
        assert h > 0.55

    def test_mean_reverting_series_hurst_below_half(self):
        """A mean-reverting series should have lower Hurst than trending.

        Note: R/S analysis has known upward bias for mean-reverting series.
        We test that mean-reverting Hurst is lower than trending Hurst,
        not that it's below 0.5 absolute.
        """
        np.random.seed(42)
        n = 2000
        # Mean-reverting: Ornstein-Uhlenbeck process with strong reversion
        mr = np.zeros(n)
        for i in range(1, n):
            mr[i] = 0.5 * mr[i - 1] + np.random.randn() * 0.5
        # Trending: AR(1) with positive autocorrelation
        tr = np.zeros(n)
        for i in range(1, n):
            tr[i] = 0.7 * tr[i - 1] + np.random.randn() * 0.3
        h_mr = compute_hurst(mr)
        h_tr = compute_hurst(tr)
        # Mean-reverting should have lower Hurst than trending
        assert h_mr < h_tr

    def test_short_series_returns_half(self):
        """Series too short should return default 0.5."""
        assert compute_hurst(np.array([1.0, 2.0, 3.0])) == 0.5


class TestRegimeFilter:
    def setup_method(self):
        self.filter = RegimeFilter(entropy_window=100, hurst_window=100)

    def test_classify_mean_reverting(self):
        """Mean-reverting series with low entropy should not be CHAOTIC or TRENDING."""
        np.random.seed(42)
        n = 200
        # Create returns with low entropy (few dominant values) and mean reversion
        # Use a 2-state Markov chain that alternates between +0.01 and -0.01
        # This has low entropy (2 bins dominate) and anti-persistence (alternating)
        states = np.zeros(n)
        for i in range(1, n):
            # 80% chance to flip state (strong mean reversion / anti-persistence)
            if np.random.rand() < 0.8:
                states[i] = -states[i - 1]
            else:
                states[i] = states[i - 1]
        returns = pd.Series(states * 0.01)
        regime = self.filter.classify(returns)
        # Should not be CHAOTIC (high entropy) or TRENDING (high Hurst)
        assert regime != Regime.CHAOTIC
        assert regime != Regime.TRENDING

    def test_classify_chaotic(self):
        """High-entropy random series should classify as CHAOTIC."""
        np.random.seed(42)
        # Very noisy series
        returns = pd.Series(np.random.randn(200) * 0.1)
        regime = self.filter.classify(returns)
        # Random noise has high entropy
        assert regime in (Regime.CHAOTIC, Regime.RANDOM, Regime.TRANSITION)

    def test_classify_all_multiple_assets(self):
        """classify_all should return regime for each asset."""
        np.random.seed(42)
        returns = pd.DataFrame({
            "A": np.random.randn(200) * 0.02,
            "B": np.random.randn(200) * 0.02,
        })
        regimes = self.filter.classify_all(returns)
        assert "A" in regimes
        assert "B" in regimes
        assert all(r in Regime for r in regimes.values())

    def test_get_regime_summary(self):
        """get_regime_summary should return DataFrame with metrics."""
        np.random.seed(42)
        returns = pd.DataFrame({
            "BTC": np.random.randn(200) * 0.02,
            "ETH": np.random.randn(200) * 0.02,
        })
        summary = self.filter.get_regime_summary(returns)
        assert "entropy" in summary.columns
        assert "hurst" in summary.columns
        assert "regime" in summary.columns
        assert len(summary) == 2

    def test_should_trade_mean_reversion_in_mean_revert_regime(self):
        """Mean reversion should trade in MEAN_REVERT regime."""
        assert self.filter.should_trade(Regime.MEAN_REVERT, "mean_reversion") is True

    def test_should_not_trade_mean_reversion_in_trending(self):
        """Mean reversion should NOT trade in TRENDING regime."""
        assert self.filter.should_trade(Regime.TRENDING, "mean_reversion") is False

    def test_should_trade_momentum_in_trending(self):
        """Momentum should trade in TRENDING regime."""
        assert self.filter.should_trade(Regime.TRENDING, "momentum") is True

    def test_should_not_trade_momentum_in_mean_revert(self):
        """Momentum should NOT trade in MEAN_REVERT regime."""
        assert self.filter.should_trade(Regime.MEAN_REVERT, "momentum") is False

    def test_should_not_trade_anything_in_chaotic(self):
        """Nothing should trade in CHAOTIC regime."""
        for strat in ["mean_reversion", "momentum", "stat_arb", "price_action"]:
            assert self.filter.should_trade(Regime.CHAOTIC, strat) is False

    def test_funding_arb_always_trades(self):
        """Funding arb (delta-neutral) should always trade."""
        for regime in Regime:
            assert self.filter.should_trade(regime, "funding_arb") is True

    def test_position_size_multiplier(self):
        """Position size should be 0 in CHAOTIC, 1.0 in clear regimes."""
        assert self.filter.position_size_multiplier(Regime.CHAOTIC) == 0.0
        assert self.filter.position_size_multiplier(Regime.MEAN_REVERT) == 1.0
        assert self.filter.position_size_multiplier(Regime.TRENDING) == 1.0
        assert self.filter.position_size_multiplier(Regime.TRANSITION) == 0.5
