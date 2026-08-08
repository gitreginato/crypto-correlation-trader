"""Tests for WalkForwardAnalyzer and walk-forward validation.

Covers happy path, edge cases, overfit detection, no look-ahead
integrity, and summary aggregation.
"""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import BacktestConfig, BacktestEngine
from src.backtest.walk_forward import (
    WalkForwardAnalyzer,
    WalkForwardConfig,
    WalkForwardResult,
    print_walk_forward,
)
from src.strategy.base import BaseStrategy, Direction, Signal, StrategyConfig


class AlwaysLongStrategy(BaseStrategy):
    """Stateless strategy that always generates a long signal on the last bar.

    Unlike SimpleBuyHoldStrategy, this does not track signaled state,
    so it works correctly across multiple walk-forward windows.
    """

    def __init__(self) -> None:
        super().__init__(StrategyConfig(strategy_id="always_long"))

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        signals: list[Signal] = []
        for symbol, df in data.items():
            if len(df) > 0:
                price = float(df["close"].iloc[-1])
                signals.append(Signal(
                    timestamp=df.index[-1],
                    symbol=symbol,
                    direction=Direction.LONG,
                    price=price,
                    stop_loss=price * 0.95,
                    take_profit=price * 1.10,
                    strategy_id="always_long",
                ))
        return signals


def make_ohlcv(n: int, trend: float = 0.001, start: float = 100.0) -> pd.DataFrame:
    """Build synthetic OHLCV with a slight trend and fixed seed=42."""
    np.random.seed(42)
    returns = np.random.randn(n) * 0.005 + trend
    prices = start * np.cumprod(1 + returns)
    return pd.DataFrame({
        "open": prices,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": 1000.0,
    }, index=pd.date_range("2024-01-01", periods=n, freq="1D"))


def make_regime_ohlcv(
    n_is: int,
    n_oos: int,
    is_trend: float = 0.008,
    oos_trend: float = -0.008,
) -> pd.DataFrame:
    """Build OHLCV with a regime change: uptrend in IS, downtrend in OOS.

    Used to simulate overfit: strategy profits in IS, loses in OOS.
    """
    np.random.seed(42)
    is_returns = np.random.randn(n_is) * 0.005 + is_trend
    oos_returns = np.random.randn(n_oos) * 0.005 + oos_trend
    all_returns = np.concatenate([is_returns, oos_returns])
    prices = 100.0 * np.cumprod(1 + all_returns)
    return pd.DataFrame({
        "open": prices,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": 1000.0,
    }, index=pd.date_range("2024-01-01", periods=n_is + n_oos, freq="1D"))


# Small config used across most tests for speed.
SMALL_WF = WalkForwardConfig(is_window=50, oos_window=40, step=40)


class TestWalkForwardConfig:
    """Tests for WalkForwardConfig defaults."""

    def test_default_config(self):
        """WalkForwardConfig should have sensible defaults."""
        config = WalkForwardConfig()
        assert config.is_window == 180
        assert config.oos_window == 60
        assert config.step == 60
        assert config.min_is_sharpe == 0.5
        assert config.max_degradation == 0.50


class TestWalkForwardAnalyzer:
    """Tests for WalkForwardAnalyzer.run and .summarize."""

    def test_happy_path_returns_results(self):
        """Walk-forward with sufficient data should return results."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(130, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) >= 1
        assert all(isinstance(r, WalkForwardResult) for r in results)

    def test_insufficient_data_returns_empty(self):
        """Data shorter than is_window + oos_window should return empty list."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(50, trend=0.003)}
        results = analyzer.run(data)
        assert results == []

    def test_empty_data_returns_empty(self):
        """Empty data dict should return empty list."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy)
        results = analyzer.run({})
        assert results == []

    def test_window_too_small_for_signals(self):
        """Windows smaller than engine 30-bar minimum should still return results with zero trades."""
        strategy = AlwaysLongStrategy()
        wf_config = WalkForwardConfig(is_window=10, oos_window=5, step=5)
        analyzer = WalkForwardAnalyzer(strategy, wf_config=wf_config)
        data = {"BTC": make_ohlcv(15, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) == 1
        assert results[0].is_trades == 0
        assert results[0].oos_trades == 0

    def test_single_window(self):
        """Data exactly fitting one window should produce exactly one result."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(90, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) == 1

    def test_multiple_windows(self):
        """Data spanning multiple windows should return a list of results."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(170, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) >= 2
        assert all(isinstance(r, WalkForwardResult) for r in results)

    def test_is_and_oos_metrics_both_returned(self):
        """Each result should contain both IS and OOS metrics."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(90, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) == 1
        r = results[0]
        assert hasattr(r, "is_sharpe")
        assert hasattr(r, "oos_sharpe")
        assert hasattr(r, "is_return")
        assert hasattr(r, "oos_return")
        assert hasattr(r, "is_max_dd")
        assert hasattr(r, "oos_max_dd")
        assert hasattr(r, "is_trades")
        assert hasattr(r, "oos_trades")
        assert hasattr(r, "degradation")
        assert hasattr(r, "passed")

    def test_result_field_types(self):
        """WalkForwardResult fields should have correct types."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(90, trend=0.003)}
        results = analyzer.run(data)
        r = results[0]
        assert isinstance(r.is_sharpe, (float, np.floating))
        assert isinstance(r.oos_sharpe, (float, np.floating))
        assert isinstance(r.is_return, (float, np.floating))
        assert isinstance(r.oos_return, (float, np.floating))
        assert isinstance(r.is_max_dd, (float, np.floating))
        assert isinstance(r.oos_max_dd, (float, np.floating))
        assert isinstance(r.is_trades, (int, np.integer))
        assert isinstance(r.oos_trades, (int, np.integer))
        assert isinstance(r.degradation, (float, np.floating))
        assert isinstance(r.passed, (bool, np.bool_))

    def test_overfit_detection_high_degradation(self):
        """When IS >> OOS, degradation should be high and passed should be False."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_regime_ohlcv(50, 40, is_trend=0.01, oos_trend=-0.01)}
        results = analyzer.run(data)
        assert len(results) == 1
        r = results[0]
        assert r.is_sharpe > r.oos_sharpe
        assert r.degradation > 0.5
        assert not r.passed

    def test_overfit_oos_sharpe_negative(self):
        """OOS Sharpe should be negative in a downtrend when always long."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_regime_ohlcv(50, 40, is_trend=0.01, oos_trend=-0.01)}
        results = analyzer.run(data)
        r = results[0]
        assert r.oos_sharpe <= 0

    def test_no_look_ahead_windows_disjoint(self):
        """IS and OOS windows must not overlap (no look-ahead bias)."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(130, trend=0.003)}

        captured: list[set[pd.Timestamp]] = []
        original_run = BacktestEngine.run

        def spy_run(engine: BacktestEngine, run_data: dict[str, pd.DataFrame]) -> dict:
            all_ts: set[pd.Timestamp] = set()
            for df in run_data.values():
                all_ts.update(df.index)
            captured.append(all_ts)
            return original_run(engine, run_data)

        with patch.object(BacktestEngine, "run", spy_run):
            results = analyzer.run(data)

        assert len(results) >= 1
        assert len(captured) >= 2
        for i in range(0, len(captured) - 1, 2):
            is_ts = captured[i]
            oos_ts = captured[i + 1]
            assert is_ts.isdisjoint(oos_ts), "IS and OOS windows overlap"
            assert max(is_ts) < min(oos_ts), "OOS data starts before IS data ends"

    def test_degradation_formula(self):
        """Degradation should equal (IS - OOS) / |IS| when IS Sharpe != 0."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(90, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) == 1
        r = results[0]
        if r.is_sharpe != 0:
            expected = (r.is_sharpe - r.oos_sharpe) / abs(r.is_sharpe)
            assert abs(r.degradation - expected) < 1e-10

    def test_multiple_symbols(self):
        """Walk-forward should handle multiple symbols."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {
            "BTC": make_ohlcv(90, trend=0.003),
            "ETH": make_ohlcv(90, trend=0.003),
        }
        results = analyzer.run(data)
        assert len(results) == 1

    def test_custom_bt_config(self):
        """Walk-forward should respect custom BacktestConfig."""
        strategy = AlwaysLongStrategy()
        bt_config = BacktestConfig(initial_capital=50000, fee_rate=0.002)
        analyzer = WalkForwardAnalyzer(strategy, bt_config=bt_config, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(90, trend=0.003)}
        results = analyzer.run(data)
        assert len(results) == 1

    def test_passed_true_when_oos_positive_and_low_degradation(self):
        """Result should pass when IS Sharpe is high, OOS is positive, and degradation is low."""
        strategy = AlwaysLongStrategy()
        wf_config = WalkForwardConfig(
            is_window=50, oos_window=40, step=40,
            min_is_sharpe=0.0, max_degradation=10.0,
        )
        analyzer = WalkForwardAnalyzer(strategy, wf_config=wf_config)
        data = {"BTC": make_ohlcv(90, trend=0.005)}
        results = analyzer.run(data)
        assert len(results) == 1
        r = results[0]
        if r.oos_sharpe > 0 and r.is_sharpe >= 0.0:
            assert r.passed

    def test_summarize_empty_results(self):
        """Summarize with empty results should return defaults."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy)
        summary = analyzer.summarize([])
        assert summary["passed_windows"] == 0
        assert summary["total_windows"] == 0
        assert summary["pass_rate"] == 0

    def test_summarize_with_results(self):
        """Summarize with results should compute averages and pass rate."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(130, trend=0.003)}
        results = analyzer.run(data)
        summary = analyzer.summarize(results)
        assert summary["total_windows"] == len(results)
        assert summary["passed_windows"] <= summary["total_windows"]
        assert 0 <= summary["pass_rate"] <= 1
        assert "avg_is_sharpe" in summary
        assert "avg_oos_sharpe" in summary
        assert "avg_degradation" in summary
        assert "avg_oos_return" in summary
        assert "avg_oos_max_dd" in summary
        assert "avg_oos_trades" in summary

    def test_print_walk_forward_does_not_crash(self):
        """print_walk_forward should not raise."""
        strategy = AlwaysLongStrategy()
        analyzer = WalkForwardAnalyzer(strategy, wf_config=SMALL_WF)
        data = {"BTC": make_ohlcv(90, trend=0.003)}
        results = analyzer.run(data)
        summary = analyzer.summarize(results)
        print_walk_forward(results, summary)
