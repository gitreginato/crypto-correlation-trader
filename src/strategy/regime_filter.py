"""STRAT-04: Entropy-Based Regime Detection.

Meta-filter that classifies market regime using Shannon entropy,
Sample Entropy, and Hurst exponent. Does not generate signals directly
but determines which other strategies should operate.

Regime classification:
    Entropy low + Hurst < 0.45  -> MEAN_REVERT
    Entropy low + Hurst > 0.55  -> TRENDING
    Entropy low + 0.45-0.55     -> RANDOM
    Entropy medium              -> TRANSITION
    Entropy high                -> CHAOTIC
"""
from typing import Literal

import numpy as np
import pandas as pd

try:
    import nolds  # noqa: F401
    _HAS_NOLDS = True
except ImportError:
    _HAS_NOLDS = False

from src.strategy.base import Regime

EntropyMethod = Literal["shannon", "sample", "approximate"]


def shannon_entropy(series: np.ndarray, bins: int = 10) -> float:
    """Compute Shannon entropy of a time series.

    H(X) = -sum(p(xi) * log2(p(xi)))

    Returns normalized entropy (0 to 1), where 1 = maximum uncertainty.
    """
    if len(series) < 2:
        return 0.0
    hist, _ = np.histogram(series, bins=bins, density=False)
    p = hist / hist.sum()
    p = p[p > 0]
    raw_entropy = -np.sum(p * np.log2(p))
    max_entropy = np.log2(bins)
    return raw_entropy / max_entropy if max_entropy > 0 else 0.0


def sample_entropy(series: np.ndarray, m: int = 2, r: float = 0.2) -> float:
    """Compute Sample Entropy (SampEn) of a time series.

    SampEn(m, r, N) = -ln(A^m(r) / B^m(r))

    Measures regularity: low = regular/predictable, high = chaotic.
    """
    n = len(series)
    if n < m + 2:
        return 0.0
    r = r * np.std(series)
    if r == 0:
        return 0.0

    def _count_matches(dim: int) -> int:
        vectors = np.array([series[i : i + dim] for i in range(n - dim)])
        count = 0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                if np.max(np.abs(vectors[i] - vectors[j])) <= r:
                    count += 1
        return count

    b = _count_matches(m)
    a = _count_matches(m + 1)
    if b == 0:
        return 0.0
    if a == 0:
        return float("inf")
    return float(-np.log(a / b))


def compute_hurst(series: np.ndarray, max_window: int = 100) -> float:
    """Compute Hurst exponent using R/S analysis.

    H < 0.5: mean-reverting (anti-persistent)
    H ~ 0.5: random walk
    H > 0.5: trending (persistent)

    The input should be a stationary series (returns, spread residuals, etc.).
    If you have price data, compute returns first before calling this function.
    """
    if len(series) < 20:
        return 0.5

    # Remove NaN/inf
    series = np.asarray(series, dtype=float)
    series = series[np.isfinite(series)]
    if len(series) < 20:
        return 0.5

    n = len(series)
    rs_values = []
    ns = []

    for size in [8, 16, 32, 64, 128, 256]:
        if size > n or size < 4:
            continue
        num_chunks = n // size
        if num_chunks < 2:
            continue
        rs_chunk = []
        for i in range(num_chunks):
            chunk = series[i * size : (i + 1) * size]
            mean = np.mean(chunk)
            deviations = np.cumsum(chunk - mean)
            r = np.max(deviations) - np.min(deviations)
            s = np.std(chunk, ddof=1)
            if s > 0:
                rs_chunk.append(r / s)
        if rs_chunk:
            rs_values.append(np.mean(rs_chunk))
            ns.append(size)

    if len(ns) < 2:
        return 0.5

    log_ns = np.log(ns)
    log_rs = np.log(rs_values)
    hurst = np.polyfit(log_ns, log_rs, 1)[0]
    return float(np.clip(hurst, 0.0, 1.0))


class RegimeFilter:
    """Classify market regime using entropy and Hurst exponent."""

    def __init__(
        self,
        entropy_window: int = 100,
        entropy_method: EntropyMethod = "shannon",
        sampen_m: int = 2,
        sampen_r: float = 0.2,
        shannon_bins: int = 10,
        regime_threshold_low: float = 0.5,
        regime_threshold_high: float = 0.9,
        hurst_window: int = 100,
    ):
        self.entropy_window = entropy_window
        self.entropy_method = entropy_method
        self.sampen_m = sampen_m
        self.sampen_r = sampen_r
        self.shannon_bins = shannon_bins
        self.regime_threshold_low = regime_threshold_low
        self.regime_threshold_high = regime_threshold_high
        self.hurst_window = hurst_window

    def compute_entropy(self, returns: pd.Series) -> float:
        """Compute normalized entropy for a return series."""
        window = returns.tail(self.entropy_window).dropna().values
        if len(window) < 10:
            return 0.5  # default to medium uncertainty

        window_arr = np.asarray(window)
        if self.entropy_method == "shannon":
            return shannon_entropy(window_arr, bins=self.shannon_bins)
        elif self.entropy_method == "sample":
            ent = sample_entropy(window_arr, m=self.sampen_m, r=self.sampen_r)
            # Normalize: SampEn typically 0-2 for financial data
            return min(ent / 2.0, 1.0)
        else:
            return shannon_entropy(window_arr, bins=self.shannon_bins)

    def compute_hurst(self, returns: pd.Series) -> float:
        """Compute Hurst exponent for a return series."""
        window = returns.tail(self.hurst_window).dropna().values
        if len(window) < 20:
            return 0.5
        return compute_hurst(np.asarray(window))

    def classify(self, returns: pd.Series) -> Regime:
        """Classify the market regime for a single asset.

        Args:
            returns: Return series for one asset.

        Returns:
            Regime enum value.
        """
        entropy = self.compute_entropy(returns)
        hurst = self.compute_hurst(returns)

        if entropy > self.regime_threshold_high:
            return Regime.CHAOTIC
        elif entropy < self.regime_threshold_low:
            if hurst < 0.45:
                return Regime.MEAN_REVERT
            elif hurst > 0.55:
                return Regime.TRENDING
            else:
                return Regime.RANDOM
        else:
            return Regime.TRANSITION

    def classify_all(self, returns: pd.DataFrame) -> dict[str, Regime]:
        """Classify regime for each column in a returns DataFrame.

        Args:
            returns: DataFrame where each column is an asset's returns.

        Returns:
            Dict mapping symbol to Regime.
        """
        return {symbol: self.classify(returns[symbol]) for symbol in returns.columns}

    def get_regime_summary(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Get a summary DataFrame with entropy, Hurst, and regime per asset."""
        rows = []
        for symbol in returns.columns:
            ent = self.compute_entropy(returns[symbol])
            hurst = self.compute_hurst(returns[symbol])
            regime = self.classify(returns[symbol])
            rows.append({
                "symbol": symbol,
                "entropy": ent,
                "hurst": hurst,
                "regime": regime.value,
            })
        return pd.DataFrame(rows).set_index("symbol")

    def should_trade(self, regime: Regime, strategy_type: str) -> bool:
        """Check if a strategy type should operate in the given regime.

        Args:
            regime: Current market regime.
            strategy_type: "mean_reversion", "momentum", "price_action", etc.

        Returns:
            True if the strategy should operate.
        """
        if regime == Regime.CHAOTIC:
            # Funding arb is delta-neutral, can operate even in chaotic regime
            return strategy_type == "funding_arb"

        if strategy_type in ("mean_reversion", "stat_arb", "vwap_reversion"):
            return regime in (Regime.MEAN_REVERT, Regime.RANDOM, Regime.TRANSITION)
        elif strategy_type in ("momentum", "trend_following"):
            return regime in (Regime.TRENDING, Regime.TRANSITION)
        elif strategy_type == "price_action":
            return regime in (Regime.MEAN_REVERT, Regime.TRENDING, Regime.RANDOM, Regime.TRANSITION)
        elif strategy_type == "funding_arb":
            return True  # delta-neutral, always ok
        elif strategy_type == "liquidity_sweep":
            return regime != Regime.CHAOTIC
        return False

    def position_size_multiplier(self, regime: Regime) -> float:
        """Get position size multiplier based on regime confidence."""
        if regime == Regime.CHAOTIC:
            return 0.0
        elif regime == Regime.TRANSITION:
            return 0.5
        elif regime == Regime.RANDOM:
            return 0.7
        else:
            return 1.0
