"""Tests for MetaStrategy: combined meta-strategy with regime filtering.

Covers MetaStrategy and MetaStrategyConfig, including regime-based
delegation to sub-strategies, regime filter integration, multi-asset
support, and edge cases.
"""
import numpy as np
import pandas as pd
import pytest

from src.strategy.base import Direction, Signal
from src.strategy.mean_reversion import MeanReversionConfig
from src.strategy.meta import MetaStrategy, MetaStrategyConfig
from src.strategy.momentum import MomentumConfig
from src.strategy.regime_filter import Regime, RegimeFilter
from src.strategy.stat_arb import StatArbConfig


# ---------------------------------------------------------------------------
# Data generators (synthetic, seed=42)
# ---------------------------------------------------------------------------

def make_trending_ohlcv(
    n: int,
    trend: float = 0.005,
    start: float = 100.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Build OHLCV with a clear uptrend or downtrend."""
    np.random.seed(seed)
    returns = np.random.randn(n) * 0.002 + trend
    prices = start * np.cumprod(1 + returns)
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.005,
            "low": prices * 0.995,
            "close": prices,
            "volume": np.random.randint(1000, 10000, n).astype(float),
        },
        index=pd.date_range("2024-01-01", periods=n, freq="1D"),
    )


def make_correlated_assets(
    n: int = 200,
    n_assets: int = 5,
    common_std: float = 0.01,
    noise_std: float = 0.003,
    deviation_asset: str | None = None,
    deviation: float = 0.0,
) -> dict[str, pd.DataFrame]:
    """Build multiple correlated OHLCV assets from a common factor.

    If deviation_asset is set, that asset's last 5 bars are shifted
    by deviation to create a z-score spike for mean reversion testing.
    """
    np.random.seed(42)
    common = np.random.randn(n) * common_std
    names = ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOT"][:n_assets]
    assets: dict[str, pd.DataFrame] = {}
    for i, name in enumerate(names):
        noise = np.random.randn(n) * noise_std
        rets = common + noise
        if deviation_asset is not None and name == deviation_asset:
            rets[-5:] = common[-5:] + deviation
        prices = (100.0 + i * 10) * np.cumprod(1 + rets)
        assets[name] = pd.DataFrame(
            {
                "open": prices,
                "high": prices * 1.005,
                "low": prices * 0.995,
                "close": prices,
                "volume": 1000.0,
            },
            index=pd.date_range("2024-01-01", periods=n, freq="1D"),
        )
    return assets


def make_chaotic_ohlcv(
    n: int,
    start: float = 100.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Build OHLCV with very high noise (chaotic regime)."""
    np.random.seed(seed)
    returns = np.random.randn(n) * 0.05
    prices = start * np.cumprod(1 + returns)
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.02,
            "low": prices * 0.98,
            "close": prices,
            "volume": 1000.0,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="1D"),
    )


# ---------------------------------------------------------------------------
# Custom RegimeFilter subclasses for deterministic testing
# ---------------------------------------------------------------------------

class FixedRegimeFilter(RegimeFilter):
    """RegimeFilter that always returns a fixed regime."""

    def __init__(self, fixed_regime: Regime) -> None:
        super().__init__()
        self.fixed_regime = fixed_regime

    def classify(self, returns: pd.Series) -> Regime:
        return self.fixed_regime


class SpyRegimeFilter(RegimeFilter):
    """RegimeFilter that records classify calls for verification."""

    def __init__(self) -> None:
        super().__init__()
        self.classify_calls: list[str] = []

    def classify(self, returns: pd.Series) -> Regime:
        self.classify_calls.append("called")
        return super().classify(returns)


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def meta_config() -> MetaStrategyConfig:
    """Build a MetaStrategyConfig with relaxed sub-strategy configs."""
    return MetaStrategyConfig(
        momentum_config=MomentumConfig(
            formation_period=30,
            ema_fast=10,
            ema_slow=20,
            adx_threshold=15,
            min_confirmation=2,
            use_regime_filter=False,
        ),
        mean_reversion_config=MeanReversionConfig(
            correlation_window=50,
            zscore_window=10,
            entry_zscore=1.5,
            min_cluster_size=3,
            hurst_threshold=0.65,
        ),
        stat_arb_config=StatArbConfig(
            lookback_window=100,
            zscore_window=20,
            entry_zscore=1.5,
            min_correlation=0.3,
            min_half_life=0.5,
            max_half_life=100,
            adf_pvalue_threshold=0.10,
            hurst_threshold=0.55,
        ),
        min_confidence=0.1,
    )


# ---------------------------------------------------------------------------
# Tests: MetaStrategyConfig
# ---------------------------------------------------------------------------

class TestMetaStrategyConfig:
    def test_default_config_values(self):
        """Default MetaStrategyConfig should have valid values."""
        config = MetaStrategyConfig()
        assert config.strategy_id == "META"
        assert config.max_signals_per_bar == 5
        assert config.min_confidence == 0.3
        assert config.momentum_config is None
        assert config.mean_reversion_config is None
        assert config.stat_arb_config is None
        assert config.regime_filter is None

    def test_strategy_type_map_defaults(self):
        """Default strategy_type_map should map strategy IDs to types."""
        config = MetaStrategyConfig()
        assert config.strategy_type_map["STRAT-06"] == "momentum"
        assert config.strategy_type_map["STRAT-01"] == "mean_reversion"
        assert config.strategy_type_map["STRAT-03"] == "stat_arb"

    def test_custom_config_values(self):
        """Custom values should be respected."""
        regime_filter = RegimeFilter()
        config = MetaStrategyConfig(
            max_signals_per_bar=3,
            min_confidence=0.5,
            regime_filter=regime_filter,
        )
        assert config.max_signals_per_bar == 3
        assert config.min_confidence == 0.5
        assert config.regime_filter is regime_filter

    def test_inherits_from_strategy_config(self):
        """MetaStrategyConfig should inherit risk_per_trade and max_positions."""
        config = MetaStrategyConfig()
        assert config.risk_per_trade == 0.01
        assert config.max_positions == 5


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------

class TestMetaStrategyEdgeCases:
    def setup_method(self) -> None:
        self.config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                use_regime_filter=False,
            ),
            min_confidence=0.1,
        )
        self.strategy = MetaStrategy(self.config)

    def test_no_signals_with_empty_data(self):
        """Empty data dict should return no signals."""
        signals = self.strategy.generate_signals({})
        assert signals == []

    def test_no_signals_with_single_asset(self):
        """Single asset (len < 2) should return no signals."""
        data = {"BTC": make_trending_ohlcv(200)}
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_no_signals_with_insufficient_bars(self):
        """Assets with < 20 bars should not be classified, no signals."""
        data = {
            "BTC": make_trending_ohlcv(15),
            "ETH": make_trending_ohlcv(15),
        }
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_no_signals_with_empty_dataframe(self):
        """Empty DataFrames should produce no signals."""
        empty_df = pd.DataFrame(
            {"open": [], "high": [], "low": [], "close": [], "volume": []},
            index=pd.DatetimeIndex([]),
        )
        data = {"BTC": empty_df, "ETH": empty_df}
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_strategy_name(self):
        """Strategy name should be the config strategy_id."""
        assert self.strategy.name == "META"


# ---------------------------------------------------------------------------
# Tests: Trending regime
# ---------------------------------------------------------------------------

class TestMetaStrategyTrendingRegime:
    def setup_method(self) -> None:
        self.config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                min_confirmation=2,
                use_regime_filter=False,
            ),
            regime_filter=FixedRegimeFilter(Regime.TRENDING),
            min_confidence=0.1,
        )
        self.strategy = MetaStrategy(self.config)

    def test_trending_regime_delegates_to_momentum(self):
        """In trending regime, momentum signals should pass through."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, start=100.0, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, start=200.0, seed=99),
        }
        signals = self.strategy.generate_signals(data)
        assert len(signals) >= 1
        for s in signals:
            assert s.metadata.get("source_strategy") == "STRAT-06"

    def test_trending_signals_have_regime_metadata(self):
        """Signals in trending regime should have regime in metadata."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
        }
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.metadata.get("regime") == Regime.TRENDING.value
            assert "regime_size_mult" in s.metadata

    def test_trending_signals_have_correct_strategy_id(self):
        """Momentum signals should retain STRAT-06 strategy_id."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
        }
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.strategy_id == "STRAT-06"

    def test_trending_long_signal_in_uptrend(self):
        """Strong uptrend should produce LONG momentum signals."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
        }
        signals = self.strategy.generate_signals(data)
        long_signals = [s for s in signals if s.direction == Direction.LONG]
        assert len(long_signals) >= 1

    def test_trending_blocks_mean_reversion_signals(self):
        """In trending regime, mean reversion signals should be blocked."""
        data = make_correlated_assets(
            n=200, n_assets=5, deviation_asset="BTC", deviation=-0.05,
        )
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.metadata.get("source_strategy") != "STRAT-01"


# ---------------------------------------------------------------------------
# Tests: Mean-reverting regime
# ---------------------------------------------------------------------------

class TestMetaStrategyMeanRevertingRegime:
    def setup_method(self) -> None:
        self.config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                min_confirmation=2,
                use_regime_filter=False,
            ),
            mean_reversion_config=MeanReversionConfig(
                correlation_window=50,
                zscore_window=10,
                entry_zscore=1.5,
                min_cluster_size=3,
                hurst_threshold=0.65,
            ),
            regime_filter=FixedRegimeFilter(Regime.MEAN_REVERT),
            min_confidence=0.1,
        )
        self.strategy = MetaStrategy(self.config)

    def test_mean_reverting_blocks_momentum_signals(self):
        """In mean-reverting regime, momentum signals should be blocked."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
        }
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.metadata.get("source_strategy") != "STRAT-06"

    def test_mean_reverting_no_momentum_in_output(self):
        """No momentum signals should survive regime filtering."""
        data = make_correlated_assets(n=200, n_assets=5)
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.metadata.get("source_strategy") != "STRAT-06"

    def test_mean_reverting_processes_without_crash(self):
        """MetaStrategy should process correlated assets without crashing."""
        data = make_correlated_assets(
            n=200, n_assets=5, deviation_asset="BTC", deviation=-0.05,
        )
        signals = self.strategy.generate_signals(data)
        assert isinstance(signals, list)

    def test_mean_reverting_regime_in_metadata(self):
        """Any signals in mean-reverting regime should have MEAN_REVERT."""
        data = make_correlated_assets(
            n=200, n_assets=5, deviation_asset="BTC", deviation=-0.05,
        )
        signals = self.strategy.generate_signals(data)
        for s in signals:
            assert s.metadata.get("regime") == Regime.MEAN_REVERT.value


# ---------------------------------------------------------------------------
# Tests: Chaotic regime
# ---------------------------------------------------------------------------

class TestMetaStrategyChaoticRegime:
    def setup_method(self) -> None:
        self.config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                min_confirmation=2,
                use_regime_filter=False,
            ),
            regime_filter=FixedRegimeFilter(Regime.CHAOTIC),
            min_confidence=0.1,
        )
        self.strategy = MetaStrategy(self.config)

    def test_chaotic_regime_no_signals(self):
        """In chaotic regime, no signals should be generated."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
        }
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_chaotic_regime_with_correlated_assets(self):
        """Chaotic regime should block all signals even with correlated assets."""
        data = make_correlated_assets(n=200, n_assets=5)
        signals = self.strategy.generate_signals(data)
        assert signals == []

    def test_chaotic_regime_blocks_all_strategy_types(self):
        """Chaotic regime should block momentum, mean reversion, and stat arb."""
        data = make_correlated_assets(
            n=200, n_assets=5, deviation_asset="BTC", deviation=-0.05,
        )
        signals = self.strategy.generate_signals(data)
        assert signals == []


# ---------------------------------------------------------------------------
# Tests: RegimeFilter integration
# ---------------------------------------------------------------------------

class TestMetaStrategyRegimeFilterIntegration:
    def test_regime_filter_called_for_each_symbol(self):
        """RegimeFilter.classify should be called once per eligible symbol."""
        spy = SpyRegimeFilter()
        config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                use_regime_filter=False,
            ),
            regime_filter=spy,
            min_confidence=0.1,
        )
        strategy = MetaStrategy(config)
        data = {
            "BTC": make_trending_ohlcv(200, seed=42),
            "ETH": make_trending_ohlcv(200, seed=99),
        }
        strategy.generate_signals(data)
        assert len(spy.classify_calls) == 2

    def test_regime_filter_not_called_for_short_data(self):
        """RegimeFilter.classify should not be called for assets with < 20 bars."""
        spy = SpyRegimeFilter()
        config = MetaStrategyConfig(
            regime_filter=spy,
            min_confidence=0.1,
        )
        strategy = MetaStrategy(config)
        data = {
            "BTC": make_trending_ohlcv(15),
            "ETH": make_trending_ohlcv(15),
        }
        strategy.generate_signals(data)
        assert len(spy.classify_calls) == 0

    def test_last_regimes_populated_after_generate(self):
        """last_regimes should contain regimes for eligible symbols."""
        config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                use_regime_filter=False,
            ),
            regime_filter=FixedRegimeFilter(Regime.TRENDING),
            min_confidence=0.1,
        )
        strategy = MetaStrategy(config)
        data = {
            "BTC": make_trending_ohlcv(200, seed=42),
            "ETH": make_trending_ohlcv(200, seed=99),
        }
        strategy.generate_signals(data)
        assert "BTC" in strategy.last_regimes
        assert "ETH" in strategy.last_regimes
        assert strategy.last_regimes["BTC"] == Regime.TRENDING
        assert strategy.last_regimes["ETH"] == Regime.TRENDING

    def test_custom_regime_filter_used(self):
        """MetaStrategy should use the regime_filter from config."""
        custom_filter = FixedRegimeFilter(Regime.CHAOTIC)
        config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                use_regime_filter=False,
            ),
            regime_filter=custom_filter,
            min_confidence=0.1,
        )
        strategy = MetaStrategy(config)
        assert strategy.regime_filter is custom_filter

    def test_default_regime_filter_created_when_none(self):
        """MetaStrategy should create a default RegimeFilter when none provided."""
        config = MetaStrategyConfig()
        strategy = MetaStrategy(config)
        assert isinstance(strategy.regime_filter, RegimeFilter)


# ---------------------------------------------------------------------------
# Tests: Multi-asset support
# ---------------------------------------------------------------------------

class TestMetaStrategyMultiAsset:
    def setup_method(self) -> None:
        self.config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                min_confirmation=2,
                use_regime_filter=False,
            ),
            regime_filter=FixedRegimeFilter(Regime.TRENDING),
            min_confidence=0.1,
        )
        self.strategy = MetaStrategy(self.config)

    def test_multiple_assets_handled(self):
        """MetaStrategy should handle multiple assets without error."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
            "SOL": make_trending_ohlcv(200, trend=0.005, seed=123),
        }
        signals = self.strategy.generate_signals(data)
        assert isinstance(signals, list)
        symbols = {s.symbol for s in signals}
        assert symbols.issubset({"BTC", "ETH", "SOL"})

    def test_signals_sorted_by_confidence(self):
        """Output signals should be sorted by confidence descending."""
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
            "SOL": make_trending_ohlcv(200, trend=0.005, seed=123),
        }
        signals = self.strategy.generate_signals(data)
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                assert signals[i].confidence >= signals[i + 1].confidence

    def test_max_signals_per_bar_limit(self):
        """Output should respect max_signals_per_bar limit."""
        config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                min_confirmation=2,
                use_regime_filter=False,
            ),
            regime_filter=FixedRegimeFilter(Regime.TRENDING),
            max_signals_per_bar=2,
            min_confidence=0.01,
        )
        strategy = MetaStrategy(config)
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
            "SOL": make_trending_ohlcv(200, trend=0.005, seed=123),
        }
        signals = strategy.generate_signals(data)
        assert len(signals) <= 2

    def test_min_confidence_filters_low_confidence(self):
        """Signals below min_confidence should be filtered out."""
        config = MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30,
                ema_fast=10,
                ema_slow=20,
                adx_threshold=15,
                min_confirmation=2,
                use_regime_filter=False,
            ),
            regime_filter=FixedRegimeFilter(Regime.TRENDING),
            min_confidence=0.99,
        )
        strategy = MetaStrategy(config)
        data = {
            "BTC": make_trending_ohlcv(200, trend=0.005, seed=42),
            "ETH": make_trending_ohlcv(200, trend=0.005, seed=99),
        }
        signals = strategy.generate_signals(data)
        for s in signals:
            assert s.confidence >= 0.99


# ---------------------------------------------------------------------------
# Tests: on_fill / on_close propagation
# ---------------------------------------------------------------------------

class TestMetaStrategyOnFillOnClose:
    def setup_method(self) -> None:
        self.config = MetaStrategyConfig(
            momentum_config=MomentumConfig(use_regime_filter=False),
            min_confidence=0.1,
        )
        self.strategy = MetaStrategy(self.config)

    def test_on_fill_propagates_to_momentum(self):
        """on_fill should propagate to MomentumStrategy for STRAT-06 signals."""
        sig = Signal(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="BTC",
            direction=Direction.LONG,
            price=100.0,
            strategy_id="STRAT-06",
            metadata={"source_strategy": "STRAT-06"},
        )
        self.strategy.on_fill(sig, 100.0)
        assert "BTC" in self.strategy.momentum.positions
        assert "BTC" in self.strategy.positions

    def test_on_fill_propagates_to_mean_reversion(self):
        """on_fill should propagate to MeanReversionStrategy for STRAT-01."""
        sig = Signal(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="ETH",
            direction=Direction.SHORT,
            price=200.0,
            strategy_id="STRAT-01",
            metadata={"source_strategy": "STRAT-01"},
        )
        self.strategy.on_fill(sig, 200.0)
        assert "ETH" in self.strategy.mean_reversion.positions

    def test_on_fill_propagates_to_stat_arb(self):
        """on_fill should propagate to StatArbStrategy for STRAT-03."""
        sig = Signal(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="SOL",
            direction=Direction.LONG,
            price=50.0,
            strategy_id="STRAT-03",
            metadata={"source_strategy": "STRAT-03"},
        )
        self.strategy.on_fill(sig, 50.0)
        assert "SOL" in self.strategy.stat_arb.positions

    def test_on_close_propagates_to_all(self):
        """on_close should propagate to all sub-strategies."""
        sig = Signal(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="BTC",
            direction=Direction.LONG,
            price=100.0,
            strategy_id="META",
            metadata={"source_strategy": "STRAT-06"},
        )
        self.strategy.momentum.positions["BTC"] = sig
        self.strategy.mean_reversion.positions["BTC"] = sig
        self.strategy.stat_arb.positions["BTC"] = sig
        self.strategy.positions["BTC"] = sig
        self.strategy.on_close("BTC")
        assert "BTC" not in self.strategy.momentum.positions
        assert "BTC" not in self.strategy.mean_reversion.positions
        assert "BTC" not in self.strategy.stat_arb.positions
        assert "BTC" not in self.strategy.positions

    def test_on_fill_without_source_strategy(self):
        """on_fill should still work when source_strategy is missing."""
        sig = Signal(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="BTC",
            direction=Direction.LONG,
            price=100.0,
            strategy_id="META",
            metadata={},
        )
        self.strategy.on_fill(sig, 100.0)
        assert "BTC" in self.strategy.positions
