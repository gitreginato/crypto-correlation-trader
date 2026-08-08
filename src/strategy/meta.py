"""Meta-strategy that combines multiple strategies with regime filtering.

The meta-strategy runs all sub-strategies, collects their signals,
and filters them through the RegimeFilter (STRAT-04) to decide which
signals to execute based on the current market regime.

Architecture (Level 2 from docs/STRATEGIES.md):
    1. RegimeFilter classifies each asset into a regime
    2. Each sub-strategy generates signals independently
    3. Meta-strategy filters signals: only keep signals from strategies
       that are allowed in the current regime
    4. Position size is adjusted by regime confidence multiplier
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from src.strategy.base import BaseStrategy, Signal, StrategyConfig
from src.strategy.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from src.strategy.momentum import MomentumConfig, MomentumStrategy
from src.strategy.regime_filter import Regime, RegimeFilter
from src.strategy.stat_arb import StatArbConfig, StatArbStrategy

logger = logging.getLogger(__name__)


@dataclass
class MetaStrategyConfig(StrategyConfig):
    strategy_id: str = "META"
    # Sub-strategy configs
    momentum_config: Optional[MomentumConfig] = None
    mean_reversion_config: Optional[MeanReversionConfig] = None
    stat_arb_config: Optional[StatArbConfig] = None
    # Regime filter
    regime_filter: Optional[RegimeFilter] = None
    # Signal selection
    max_signals_per_bar: int = 5
    min_confidence: float = 0.3
    # Strategy type mapping for regime filtering
    strategy_type_map: dict = field(default_factory=lambda: {
        "STRAT-06": "momentum",
        "STRAT-01": "mean_reversion",
        "STRAT-03": "stat_arb",
    })


class MetaStrategy(BaseStrategy):
    """Combined meta-strategy with regime-aware signal filtering."""

    def __init__(self, config: MetaStrategyConfig | None = None):
        config = config or MetaStrategyConfig()
        super().__init__(config)
        self.config: MetaStrategyConfig = config

        # Initialize sub-strategies with provided or default configs
        self.momentum = MomentumStrategy(
            config.momentum_config or MomentumConfig(use_regime_filter=False)
        )
        self.mean_reversion = MeanReversionStrategy(
            config.mean_reversion_config or MeanReversionConfig()
        )
        self.stat_arb = StatArbStrategy(
            config.stat_arb_config or StatArbConfig()
        )

        # Regime filter
        self.regime_filter = config.regime_filter or RegimeFilter()

        # Track regimes for debugging
        self.last_regimes: dict[str, Regime] = {}

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate signals from all sub-strategies, filtered by regime."""
        if len(data) < 2:
            return []

        # 1. Classify regime for each symbol
        regimes = {}
        for symbol, df in data.items():
            if len(df) < 20:
                continue
            returns = df["close"].pct_change().dropna()
            if len(returns) < 20:
                continue
            regimes[symbol] = self.regime_filter.classify(returns)
        self.last_regimes = regimes

        # 2. Generate signals from each sub-strategy
        all_signals = []

        # Momentum signals
        try:
            mom_signals = self.momentum.generate_signals(data)
            for s in mom_signals:
                s.metadata["source_strategy"] = "STRAT-06"
                all_signals.append(s)
        except Exception as e:
            logger.warning("Momentum sub-strategy failed: %s", e)

        # Mean reversion signals
        try:
            mr_signals = self.mean_reversion.generate_signals(data)
            for s in mr_signals:
                s.metadata["source_strategy"] = "STRAT-01"
                all_signals.append(s)
        except Exception as e:
            logger.warning("Mean reversion sub-strategy failed: %s", e)

        # Stat arb signals
        try:
            sa_signals = self.stat_arb.generate_signals(data)
            for s in sa_signals:
                s.metadata["source_strategy"] = "STRAT-03"
                all_signals.append(s)
        except Exception as e:
            logger.warning("Stat arb sub-strategy failed: %s", e)

        # 3. Filter signals by regime
        filtered = []
        for signal in all_signals:
            symbol = signal.symbol
            if symbol not in regimes:
                continue

            regime = regimes[symbol]
            strategy_type = self.config.strategy_type_map.get(
                signal.metadata.get("source_strategy", ""), ""
            )

            if not self.regime_filter.should_trade(regime, strategy_type):
                continue

            # Adjust confidence by regime position size multiplier
            size_mult = self.regime_filter.position_size_multiplier(regime)
            signal.confidence = signal.confidence * size_mult

            # Filter by minimum confidence
            if signal.confidence < self.config.min_confidence:
                continue

            # Add regime to metadata
            signal.metadata["regime"] = regime.value
            signal.metadata["regime_size_mult"] = size_mult

            filtered.append(signal)

        # 4. Sort by confidence and limit
        filtered.sort(key=lambda s: s.confidence, reverse=True)
        return filtered[: self.config.max_signals_per_bar]

    def on_fill(self, signal: Signal, fill_price: float) -> None:
        """Propagate fill to relevant sub-strategy."""
        super().on_fill(signal, fill_price)
        source = signal.metadata.get("source_strategy", "")
        if source == "STRAT-06":
            self.momentum.on_fill(signal, fill_price)
        elif source == "STRAT-01":
            self.mean_reversion.on_fill(signal, fill_price)
        elif source == "STRAT-03":
            self.stat_arb.on_fill(signal, fill_price)

    def on_close(self, symbol: str) -> None:
        """Propagate close to all sub-strategies."""
        super().on_close(symbol)
        self.momentum.on_close(symbol)
        self.mean_reversion.on_close(symbol)
        self.stat_arb.on_close(symbol)
