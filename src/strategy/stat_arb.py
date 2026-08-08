"""STRAT-03: Statistical Arbitrage (Cointegration).

Identifies cointegrated pairs of crypto assets and trades the
mean-reverting spread. Uses Engle-Granger methodology:
    1. OLS regression to find hedge ratio
    2. ADF test on spread residuals
    3. Half-life calculation
    4. Hurst exponent filter (spread must be mean-reverting)
    5. Z-score entry/exit

Signal logic:
    spread = price_A - beta * price_B
    z_score = (spread - rolling_mean) / rolling_std
    If z < -entry: LONG A, SHORT B (spread will increase)
    If z > +entry: SHORT A, LONG B (spread will decrease)
"""
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.stattools import adfuller

from src.strategy.base import BaseStrategy, Direction, Signal, StrategyConfig
from src.strategy.regime_filter import RegimeFilter, compute_hurst

logger = logging.getLogger(__name__)


@dataclass
class StatArbConfig(StrategyConfig):
    strategy_id: str = "STRAT-03"
    adf_pvalue_threshold: float = 0.05
    lookback_window: int = 100
    zscore_window: int = 20
    entry_zscore: float = 2.0
    exit_zscore: float = 0.5
    stop_zscore: float = 4.0
    min_half_life: float = 1.0
    max_half_life: float = 50.0
    max_pairs: int = 10
    min_correlation: float = 0.5
    hurst_threshold: float = 0.5  # spread must be mean-reverting (H < 0.5)


class StatArbStrategy(BaseStrategy):
    """Statistical arbitrage using cointegration."""

    def __init__(self, config: StatArbConfig | None = None):
        config = config or StatArbConfig()
        super().__init__(config)
        self.config: StatArbConfig = config
        self.regime_filter = RegimeFilter()
        self._cached_pairs: list[tuple] = []  # (asset_a, asset_b, beta)
        self._last_pair_scan: Optional[pd.Timestamp] = None

    @staticmethod
    def calculate_half_life(spread: pd.Series) -> float:
        """Calculate half-life of mean reversion.

        Regress delta_spread on lagged_spread:
            delta_spread = alpha + beta * lagged_spread
            half_life = -ln(2) / beta
        """
        spread_lag = spread.shift(1).dropna()
        spread_diff = spread.diff().dropna()
        spread_lag, spread_diff = spread_lag.align(spread_diff)

        if len(spread_lag) < 10:
            return float("inf")

        model = LinearRegression()
        model.fit(np.asarray(spread_lag.values).reshape(-1, 1), np.asarray(spread_diff.values))
        beta = model.coef_[0]

        if beta >= 0:
            return float("inf")  # not mean-reverting

        return float(-np.log(2) / beta)

    def _test_cointegration(self, prices_a: pd.Series, prices_b: pd.Series) -> Optional[dict]:
        """Test if two price series are cointegrated.

        Returns dict with beta, p_value, half_life, hurst if cointegrated, else None.
        """
        # Pre-filter: correlation
        rets_a = prices_a.pct_change().dropna()
        rets_b = prices_b.pct_change().dropna()
        corr = rets_a.corr(rets_b)
        if abs(corr) < self.config.min_correlation:
            return None

        # OLS hedge ratio
        model = LinearRegression()
        model.fit(np.asarray(prices_b.values).reshape(-1, 1), np.asarray(prices_a.values))
        beta = model.coef_[0]
        alpha = model.intercept_
        spread = prices_a - beta * prices_b - alpha

        # ADF test
        try:
            adf_result = adfuller(spread.dropna(), maxlag=1)
            p_value = adf_result[1]
        except (ValueError, np.linalg.LinAlgError) as e:
            logger.warning("ADF test failed for pair: %s", e)
            return None

        if p_value > self.config.adf_pvalue_threshold:
            return None

        # Half-life
        half_life = self.calculate_half_life(spread)
        if half_life < self.config.min_half_life or half_life > self.config.max_half_life:
            return None

        # Hurst exponent (spread should be mean-reverting)
        # Use first differences of spread for R/S analysis (spread itself
        # can have excursions that mislead R/S, but its differences
        # should show anti-persistence if mean-reverting)
        spread_diffs = spread.diff().dropna().values
        hurst = compute_hurst(spread_diffs)
        if hurst > self.config.hurst_threshold:
            return None

        return {
            "beta": float(beta),
            "alpha": float(alpha),
            "p_value": float(p_value),
            "half_life": float(half_life),
            "hurst": float(hurst),
            "correlation": float(corr),
        }

    def find_pairs(self, prices: pd.DataFrame) -> list[tuple[str, str, float, dict]]:
        """Find cointegrated pairs from a price DataFrame.

        Returns list of (asset_a, asset_b, beta, metadata).
        """
        assets = prices.columns.tolist()
        pairs = []

        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                a, b = assets[i], assets[j]
                window_a = prices[a].tail(self.config.lookback_window).dropna()
                window_b = prices[b].tail(self.config.lookback_window).dropna()

                if len(window_a) < 30 or len(window_b) < 30:
                    continue

                # Align
                common_idx = window_a.index.intersection(window_b.index)
                if len(common_idx) < 30:
                    continue
                wa = window_a.loc[common_idx]
                wb = window_b.loc[common_idx]

                result = self._test_cointegration(wa, wb)
                if result is not None:
                    pairs.append((a, b, result["beta"], result))

        # Sort by p-value (lower = more cointegrated)
        pairs.sort(key=lambda x: x[3]["p_value"])
        return pairs[: self.config.max_pairs]

    def _rolling_zscore(self, series: pd.Series, window: int) -> pd.Series:
        """Compute rolling z-score."""
        mean = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (series - mean) / std.replace(0, np.nan)

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate stat arb signals from OHLCV data."""
        # Build price DataFrame
        prices = {}
        for symbol, df in data.items():
            if "close" in df.columns and len(df) >= self.config.lookback_window:
                prices[symbol] = df["close"]

        if len(prices) < 2:
            return []

        price_df = pd.DataFrame(prices)

        # Find pairs (cached if recent)
        pairs = self.find_pairs(price_df)
        self._cached_pairs = [(a, b, beta) for a, b, beta, _ in pairs]

        if not pairs:
            return []

        signals = []
        timestamp = price_df.index[-1]

        for asset_a, asset_b, beta, meta in pairs:
            # Compute spread
            pa = price_df[asset_a].tail(self.config.lookback_window)
            pb = price_df[asset_b].tail(self.config.lookback_window)
            spread = pa - beta * pb
            zscore = self._rolling_zscore(spread, self.config.zscore_window)

            current_z = zscore.iloc[-1]
            if np.isnan(current_z):
                continue

            current_price_a = float(pa.iloc[-1])
            current_price_b = float(pb.iloc[-1])
            confidence = min(1.0, abs(current_z) / self.config.entry_zscore)

            if current_z < -self.config.entry_zscore:
                # Spread too low: LONG A, SHORT B
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=asset_a,
                    direction=Direction.LONG,
                    price=current_price_a,
                    confidence=confidence,
                    strategy_id=self.name,
                    metadata={
                        "zscore": float(current_z),
                        "hedge_symbol": asset_b,
                        "hedge_direction": Direction.SHORT.value,
                        "hedge_ratio": float(beta),
                        "hedge_price": current_price_b,
                        "half_life": meta["half_life"],
                        "p_value": meta["p_value"],
                        "hurst": meta["hurst"],
                    },
                ))
            elif current_z > self.config.entry_zscore:
                # Spread too high: SHORT A, LONG B
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=asset_a,
                    direction=Direction.SHORT,
                    price=current_price_a,
                    confidence=confidence,
                    strategy_id=self.name,
                    metadata={
                        "zscore": float(current_z),
                        "hedge_symbol": asset_b,
                        "hedge_direction": Direction.LONG.value,
                        "hedge_ratio": float(beta),
                        "hedge_price": current_price_b,
                        "half_life": meta["half_life"],
                        "p_value": meta["p_value"],
                        "hurst": meta["hurst"],
                    },
                ))

        return signals

    def check_exit(
        self,
        asset_a: str,
        asset_b: str,
        beta: float,
        prices: pd.DataFrame,
    ) -> bool:
        """Check if a pairs position should be closed."""
        spread = prices[asset_a] - beta * prices[asset_b]
        zscore = self._rolling_zscore(spread, self.config.zscore_window)
        current_z = zscore.iloc[-1]

        if np.isnan(current_z):
            return False

        # Exit when z-score reverts
        if abs(current_z) < self.config.exit_zscore:
            return True

        # Stop loss
        if abs(current_z) > self.config.stop_zscore:
            return True

        return False
