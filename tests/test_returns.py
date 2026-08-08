"""Tests for Returns: log-return and simple-return calculations."""
import numpy as np
import pandas as pd
import pytest

from src.analysis.returns import calculate_returns, align_returns


@pytest.fixture
def price_df() -> pd.DataFrame:
    """Generate a price DataFrame with 3 assets, 100 periods."""
    rng = np.random.default_rng(seed=42)
    n = 100
    ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({
        "BTCUSDT": 40000 * np.cumprod(1 + rng.normal(0.001, 0.02, n)),
        "ETHUSDT": 2000 * np.cumprod(1 + rng.normal(0.001, 0.03, n)),
        "SOLUSDT": 100 * np.cumprod(1 + rng.normal(0.002, 0.05, n)),
    }, index=ts)


class TestCalculateReturns:
    def test_log_returns(self, price_df: pd.DataFrame):
        """Log returns should be ln(P_t / P_{t-1})."""
        returns = calculate_returns(price_df, method="log")
        assert isinstance(returns, pd.DataFrame)
        assert returns.shape == (99, 3)
        # First row should be ln(P1/P0)
        expected_btc = np.log(price_df["BTCUSDT"].iloc[1] / price_df["BTCUSDT"].iloc[0])
        assert np.isclose(returns["BTCUSDT"].iloc[0], expected_btc)

    def test_simple_returns(self, price_df: pd.DataFrame):
        """Simple returns should be (P_t - P_{t-1}) / P_{t-1}."""
        returns = calculate_returns(price_df, method="simple")
        expected_btc = (price_df["BTCUSDT"].iloc[1] - price_df["BTCUSDT"].iloc[0]) / price_df["BTCUSDT"].iloc[0]
        assert np.isclose(returns["BTCUSDT"].iloc[0], expected_btc)

    def test_invalid_method_raises(self, price_df: pd.DataFrame):
        """Invalid method should raise ValueError."""
        with pytest.raises(ValueError, match="method"):
            calculate_returns(price_df, method="invalid")

    def test_returns_no_nan(self, price_df: pd.DataFrame):
        """Returns should not have NaN values (except possibly first row)."""
        returns = calculate_returns(price_df, method="log")
        assert not returns.isna().any().any()

    def test_returns_preserve_index(self, price_df: pd.DataFrame):
        """Returns index should be aligned with price index (shifted by 1)."""
        returns = calculate_returns(price_df, method="log")
        assert returns.index[0] == price_df.index[1]


class TestAlignReturns:
    def test_align_same_index(self, price_df: pd.DataFrame):
        """Aligning data with same index should not change it."""
        aligned = align_returns(price_df)
        pd.testing.assert_frame_equal(aligned, price_df)

    def test_align_different_indices(self):
        """Aligning data with different indices should reindex and forward fill."""
        ts1 = pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")
        ts2 = pd.date_range("2024-01-02", periods=10, freq="1D", tz="UTC")
        df1 = pd.DataFrame({"A": range(10)}, index=ts1)
        df2 = pd.DataFrame({"B": range(10)}, index=ts2)
        combined = pd.concat([df1, df2], axis=1)
        aligned = align_returns(combined, max_fill_gap=1)
        assert not aligned.isna().any().any()

    def test_align_drops_sparse_columns(self):
        """Columns with too many NaN should be dropped."""
        ts = pd.date_range("2024-01-01", periods=100, freq="1D", tz="UTC")
        df = pd.DataFrame({
            "A": range(100),
            "B": [np.nan] * 90 + list(range(10)),
        }, index=ts)
        aligned = align_returns(df, min_valid_ratio=0.5)
        assert "A" in aligned.columns
        assert "B" not in aligned.columns
