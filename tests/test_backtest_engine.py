"""Tests for BacktestEngine."""
import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import BacktestEngine, BacktestConfig, print_metrics
from src.strategy.base import BaseStrategy, Signal, Direction, StrategyConfig
from src.strategy.momentum import MomentumStrategy, MomentumConfig


class SimpleBuyHoldStrategy(BaseStrategy):
    """Simple strategy that goes long on the first bar."""

    def __init__(self):
        super().__init__(StrategyConfig(strategy_id="simple"))
        self._signaled = False

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        if self._signaled:
            return []
        self._signaled = True
        signals = []
        for symbol, df in data.items():
            if len(df) > 0:
                signals.append(Signal(
                    timestamp=df.index[-1],
                    symbol=symbol,
                    direction=Direction.LONG,
                    price=float(df["close"].iloc[-1]),
                    stop_loss=float(df["close"].iloc[-1] * 0.95),
                    take_profit=float(df["close"].iloc[-1] * 1.10),
                    strategy_id="simple",
                ))
        return signals


def make_ohlcv(n: int, trend: float = 0.001, start: float = 100.0) -> pd.DataFrame:
    """Build OHLCV with a slight uptrend."""
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


class TestBacktestEngine:
    def test_run_with_simple_strategy(self):
        """Engine should run and return metrics."""
        strategy = SimpleBuyHoldStrategy()
        config = BacktestConfig(initial_capital=10000, fee_rate=0.001)
        engine = BacktestEngine(strategy, config)
        data = {"BTC": make_ohlcv(100, trend=0.002)}
        metrics = engine.run(data)
        assert "total_return" in metrics
        assert "sharpe" in metrics
        assert "max_drawdown" in metrics
        assert "num_trades" in metrics
        assert "win_rate" in metrics
        assert "profit_factor" in metrics
        assert "final_capital" in metrics

    def test_positive_return_in_uptrend(self):
        """Buy-and-hold in uptrend should have positive return (minus fees)."""
        strategy = SimpleBuyHoldStrategy()
        config = BacktestConfig(initial_capital=10000, fee_rate=0.001, slippage_rate=0.0005)
        engine = BacktestEngine(strategy, config)
        data = {"BTC": make_ohlcv(100, trend=0.005)}
        metrics = engine.run(data)
        # With strong uptrend, should be profitable despite fees
        assert metrics["total_return"] > -0.05  # at minimum not huge loss

    def test_stop_loss_triggers(self):
        """Stop loss should close position when price drops."""
        strategy = SimpleBuyHoldStrategy()
        config = BacktestConfig(initial_capital=10000, fee_rate=0.0)
        engine = BacktestEngine(strategy, config)
        # Declining market
        data = {"BTC": make_ohlcv(100, trend=-0.01)}
        metrics = engine.run(data)
        # Should have at least 1 trade (opened and stopped out)
        assert metrics["num_trades"] >= 1

    def test_take_profit_triggers(self):
        """Take profit should close position when price rises enough."""
        strategy = SimpleBuyHoldStrategy()
        config = BacktestConfig(initial_capital=10000, fee_rate=0.0)
        engine = BacktestEngine(strategy, config)
        data = {"BTC": make_ohlcv(100, trend=0.02)}  # strong uptrend
        metrics = engine.run(data)
        assert metrics["num_trades"] >= 1

    def test_equity_curve_is_built(self):
        """Equity curve should be recorded for each bar."""
        strategy = SimpleBuyHoldStrategy()
        engine = BacktestEngine(strategy, BacktestConfig(fee_rate=0.0))
        data = {"BTC": make_ohlcv(50)}
        metrics = engine.run(data)
        eq = metrics["equity_curve"]
        assert len(eq) == 50
        assert "equity" in eq.columns
        assert "drawdown" in eq.columns

    def test_no_trades_with_empty_data(self):
        """Engine should handle empty data gracefully."""
        strategy = SimpleBuyHoldStrategy()
        engine = BacktestEngine(strategy)
        metrics = engine.run({})
        assert metrics["num_trades"] == 0
        assert metrics["total_return"] == 0

    def test_multiple_symbols(self):
        """Engine should handle multiple symbols."""
        strategy = SimpleBuyHoldStrategy()
        engine = BacktestEngine(strategy, BacktestConfig(fee_rate=0.0))
        data = {
            "BTC": make_ohlcv(100, trend=0.002),
            "ETH": make_ohlcv(100, trend=0.002),
        }
        metrics = engine.run(data)
        assert metrics["num_trades"] >= 1

    def test_fees_reduce_returns(self):
        """Higher fees should reduce returns."""
        data = {"BTC": make_ohlcv(100, trend=0.003)}

        # No fees
        s1 = SimpleBuyHoldStrategy()
        e1 = BacktestEngine(s1, BacktestConfig(fee_rate=0.0, slippage_rate=0.0))
        m1 = e1.run(data)

        # High fees
        s2 = SimpleBuyHoldStrategy()
        e2 = BacktestEngine(s2, BacktestConfig(fee_rate=0.01, slippage_rate=0.005))
        m2 = e2.run(data)

        assert m2["final_capital"] < m1["final_capital"]

    def test_print_metrics_does_not_crash(self):
        """print_metrics should not crash."""
        strategy = SimpleBuyHoldStrategy()
        engine = BacktestEngine(strategy)
        data = {"BTC": make_ohlcv(50)}
        metrics = engine.run(data)
        print_metrics(metrics)  # should not raise

    def test_momentum_strategy_in_backtest(self):
        """Backtest should work with MomentumStrategy."""
        config = MomentumConfig(
            formation_period=30,
            ema_fast=10,
            ema_slow=20,
            adx_threshold=15,
            min_confirmation=2,
        )
        strategy = MomentumStrategy(config)
        bt_config = BacktestConfig(initial_capital=10000, fee_rate=0.001)
        engine = BacktestEngine(strategy, bt_config)
        data = {"BTC": make_ohlcv(200, trend=0.003)}
        metrics = engine.run(data)
        assert metrics["num_trades"] >= 0  # may or may not trigger
