"""STRAT-01: Mean Reversion by Correlation.

Identifies assets that deviate significantly from their correlation
cluster and trades the reversion. Uses the existing CorrelationMatrix
and CorrelationGraph infrastructure.

Signal logic:
    z_score = (asset_return - cluster_mean_return) / rolling_std
    If z < -entry_threshold: LONG (asset underperformed, expect reversion)
    If z > +entry_threshold: SHORT (asset overperformed, expect reversion)
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.analysis.correlation import CorrelationMatrix
from src.analysis.graph import CorrelationGraph
from src.strategy.base import BaseStrategy, Direction, Signal, StrategyConfig
from src.strategy.regime_filter import Regime, RegimeFilter


@dataclass
class MeanReversionConfig(StrategyConfig):
    strategy_id: str = "STRAT-01"
    correlation_threshold: float = 0.5
    correlation_window: int = 90
    zscore_window: int = 20
    entry_zscore: float = 2.0
    exit_zscore: float = 0.5
    stop_zscore: float = 4.0
    min_cluster_size: int = 3
    max_position_per_asset: float = 0.10
    hurst_threshold: float = 0.55  # skip if trending


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy based on correlation clusters."""

    def __init__(self, config: MeanReversionConfig | None = None):
        config = config or MeanReversionConfig()
        super().__init__(config)
        self.config: MeanReversionConfig = config
        self.regime_filter = RegimeFilter()

    def _rolling_zscore(self, series: pd.Series, window: int) -> pd.Series:
        """Compute rolling z-score."""
        mean = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (series - mean) / std.replace(0, np.nan)

    def _get_clusters(self, returns: pd.DataFrame) -> dict[str, list[str]]:
        """Detect correlation clusters (communities).

        Returns dict mapping community_id to list of symbols.
        """
        window_data = returns.tail(self.config.correlation_window)
        if len(window_data) < 20:
            return {}

        cm = CorrelationMatrix(method="pearson")
        corr = cm.compute(window_data)

        cg = CorrelationGraph(threshold=self.config.correlation_threshold)
        graph = cg.build(corr)
        communities = cg.detect_communities(graph)

        # Group by community
        clusters: dict[int, list[str]] = {}
        for symbol, comm_id in communities.items():
            clusters.setdefault(comm_id, []).append(symbol)

        return {f"cluster_{k}": v for k, v in clusters.items()}

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate mean reversion signals from OHLCV data.

        Args:
            data: Dict mapping symbol to OHLCV DataFrame with 'close' column.

        Returns:
            List of Signal objects.
        """
        # Build returns DataFrame
        prices = {}
        for symbol, df in data.items():
            if "close" in df.columns and len(df) > self.config.correlation_window:
                prices[symbol] = df.set_index(df.index)["close"]

        if len(prices) < self.config.min_cluster_size:
            return []

        price_df = pd.DataFrame(prices)
        returns = price_df.pct_change().dropna()

        if len(returns) < self.config.zscore_window + 10:
            return []

        # Get clusters
        clusters = self._get_clusters(returns)
        if not clusters:
            return []

        # Regime filter
        regimes = self.regime_filter.classify_all(returns)

        signals = []
        for cluster_name, members in clusters.items():
            if len(members) < self.config.min_cluster_size:
                continue

            for asset in members:
                # Check regime
                regime = regimes.get(asset, Regime.RANDOM)
                if not self.regime_filter.should_trade(regime, "mean_reversion"):
                    continue

                # Check Hurst (skip trending)
                hurst = self.regime_filter.compute_hurst(returns[asset])
                if hurst > self.config.hurst_threshold:
                    continue

                # Compute deviation from cluster
                cluster_others = [m for m in members if m != asset]
                if not cluster_others:
                    continue
                cluster_return = returns[cluster_others].mean(axis=1)
                deviation = returns[asset] - cluster_return
                zscore = self._rolling_zscore(deviation, self.config.zscore_window)

                current_z = zscore.iloc[-1]
                if np.isnan(current_z):
                    continue

                # Position size multiplier from regime
                size_mult = self.regime_filter.position_size_multiplier(regime)
                confidence = min(1.0, abs(current_z) / self.config.entry_zscore) * size_mult

                current_price = price_df[asset].iloc[-1]
                timestamp = price_df.index[-1]

                if current_z < -self.config.entry_zscore:
                    signals.append(Signal(
                        timestamp=timestamp,
                        symbol=asset,
                        direction=Direction.LONG,
                        price=float(current_price),
                        confidence=confidence,
                        strategy_id=self.name,
                        metadata={
                            "zscore": float(current_z),
                            "cluster": cluster_name,
                            "hurst": float(hurst),
                            "regime": regime.value,
                        },
                    ))
                elif current_z > self.config.entry_zscore:
                    signals.append(Signal(
                        timestamp=timestamp,
                        symbol=asset,
                        direction=Direction.SHORT,
                        price=float(current_price),
                        confidence=confidence,
                        strategy_id=self.name,
                        metadata={
                            "zscore": float(current_z),
                            "cluster": cluster_name,
                            "hurst": float(hurst),
                            "regime": regime.value,
                        },
                    ))

        return signals

    def check_exit(self, symbol: str, current_returns: pd.Series, cluster_returns: pd.Series) -> bool:
        """Check if an existing position should be closed.

        Args:
            symbol: The asset symbol.
            current_returns: Recent returns for the asset.
            cluster_returns: Recent returns for the cluster (excluding asset).

        Returns:
            True if position should be closed.
        """
        if symbol not in self.positions:
            return False

        deviation = current_returns - cluster_returns
        zscore = self._rolling_zscore(deviation, self.config.zscore_window)
        current_z = zscore.iloc[-1]

        if np.isnan(current_z):
            return False

        # Exit when z-score reverts to exit threshold
        if abs(current_z) < self.config.exit_zscore:
            return True

        # Stop loss when z-score diverges further
        if abs(current_z) > self.config.stop_zscore:
            return True

        return False
