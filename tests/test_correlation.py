"""Tests for Correlation: correlation matrix computation."""
import numpy as np
import pandas as pd
import pytest

from src.analysis.correlation import CorrelationMatrix


@pytest.fixture
def returns_df() -> pd.DataFrame:
    """Generate correlated return data for testing."""
    rng = np.random.default_rng(seed=42)
    n = 200
    ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    # BTC and ETH are highly correlated
    btc = rng.normal(0, 0.02, n)
    eth = btc * 0.8 + rng.normal(0, 0.01, n)
    # SOL is moderately correlated
    sol = btc * 0.4 + rng.normal(0, 0.03, n)
    # DOGE is uncorrelated
    doge = rng.normal(0, 0.05, n)
    return pd.DataFrame({
        "BTCUSDT": btc,
        "ETHUSDT": eth,
        "SOLUSDT": sol,
        "DOGEUSDT": doge,
    }, index=ts)


class TestCorrelationMatrix:
    def test_pearson_correlation(self, returns_df: pd.DataFrame):
        """Pearson correlation should produce a symmetric matrix."""
        cm = CorrelationMatrix(method="pearson")
        matrix = cm.compute(returns_df)
        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (4, 4)
        # Diagonal should be 1.0
        for col in matrix.columns:
            assert np.isclose(matrix.loc[col, col], 1.0)
        # Symmetric
        assert np.allclose(matrix.values, matrix.values.T)

    def test_spearman_correlation(self, returns_df: pd.DataFrame):
        """Spearman correlation should work and produce valid values."""
        cm = CorrelationMatrix(method="spearman")
        matrix = cm.compute(returns_df)
        assert matrix.shape == (4, 4)
        for col in matrix.columns:
            assert np.isclose(matrix.loc[col, col], 1.0)

    def test_kendall_correlation(self, returns_df: pd.DataFrame):
        """Kendall correlation should work."""
        cm = CorrelationMatrix(method="kendall")
        matrix = cm.compute(returns_df)
        assert matrix.shape == (4, 4)

    def test_invalid_method_raises(self, returns_df: pd.DataFrame):
        """Invalid method should raise ValueError."""
        with pytest.raises(ValueError, match="method"):
            CorrelationMatrix(method="invalid")

    def test_btc_eth_highly_correlated(self, returns_df: pd.DataFrame):
        """BTC and ETH should have high positive correlation."""
        cm = CorrelationMatrix(method="pearson")
        matrix = cm.compute(returns_df)
        assert matrix.loc["BTCUSDT", "ETHUSDT"] > 0.7

    def test_doge_uncorrelated(self, returns_df: pd.DataFrame):
        """DOGE should have low correlation with BTC."""
        cm = CorrelationMatrix(method="pearson")
        matrix = cm.compute(returns_df)
        assert abs(matrix.loc["BTCUSDT", "DOGEUSDT"]) < 0.3

    def test_rolling_correlation(self, returns_df: pd.DataFrame):
        """Rolling correlation should produce a time series of matrices."""
        cm = CorrelationMatrix(method="pearson")
        rolling = cm.compute_rolling(returns_df, window=60)
        assert isinstance(rolling, dict)
        assert len(rolling) > 0
        # Each entry should be a correlation matrix
        for date, matrix in rolling.items():
            assert matrix.shape == (4, 4)

    def test_distance_matrix(self, returns_df: pd.DataFrame):
        """Distance matrix should be sqrt(2 * (1 - corr))."""
        cm = CorrelationMatrix(method="pearson")
        corr = cm.compute(returns_df)
        dist = cm.to_distance_matrix(corr)
        # Diagonal should be 0
        for col in dist.columns:
            assert np.isclose(dist.loc[col, col], 0.0)
        # All values should be non-negative
        assert (dist.values >= 0).all()

    def test_threshold_edges(self, returns_df: pd.DataFrame):
        """Threshold filtering should return only strong correlations."""
        cm = CorrelationMatrix(method="pearson")
        matrix = cm.compute(returns_df)
        edges = cm.get_edges(matrix, threshold=0.5)
        assert isinstance(edges, list)
        for (sym1, sym2, corr) in edges:
            assert abs(corr) >= 0.5
            assert sym1 != sym2
