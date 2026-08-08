"""Tests for src/bot/engine.py.

TDD: tests written before implementation. Covers the main bot loop,
signal processing, and integration of strategy + risk_manager + broker.
"""
import pandas as pd
import pytest

from src.bot.engine import BotEngine, BotConfig, BotState
from src.bot.paper_broker import PaperBroker, PaperBrokerConfig
from src.bot.risk_manager import RiskManager, RiskConfig
from src.strategy.base import BaseStrategy, Direction, Signal, StrategyConfig


@pytest.fixture
def simple_strategy() -> BaseStrategy:
    """A minimal strategy that always generates a long signal for BTCUSDT."""

    class AlwaysLongStrategy(BaseStrategy):
        def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
            if "BTCUSDT" not in data:
                return []
            df = data["BTCUSDT"]
            if df.empty:
                return []
            return [Signal(
                timestamp=df.index[-1],
                symbol="BTCUSDT",
                direction=Direction.LONG,
                price=float(df["close"].iloc[-1]),
                stop_loss=float(df["close"].iloc[-1]) * 0.98,
                take_profit=float(df["close"].iloc[-1]) * 1.04,
                strategy_id="always_long",
            )]

    return AlwaysLongStrategy(StrategyConfig(strategy_id="always_long", max_positions=5))


@pytest.fixture
def market_data() -> dict[str, pd.DataFrame]:
    """Synthetic OHLCV data for BTCUSDT."""
    dates = pd.date_range("2024-01-15", periods=10, freq="1h", tz="UTC")
    return {
        "BTCUSDT": pd.DataFrame({
            "open": [50_000 + i * 100 for i in range(10)],
            "high": [50_100 + i * 100 for i in range(10)],
            "low": [49_900 + i * 100 for i in range(10)],
            "close": [50_050 + i * 100 for i in range(10)],
            "volume": [100.0] * 10,
        }, index=dates)
    }


@pytest.fixture
def bot_config() -> BotConfig:
    return BotConfig(
        portfolio_value=10_000.0,
        poll_interval_seconds=1.0,
    )


@pytest.fixture
def bot(bot_config: BotConfig, simple_strategy: BaseStrategy) -> BotEngine:
    risk_manager = RiskManager(
        config=RiskConfig(max_positions=5),
        portfolio_value=bot_config.portfolio_value,
    )
    broker = PaperBroker(PaperBrokerConfig(initial_cash=bot_config.portfolio_value))
    return BotEngine(
        config=bot_config,
        strategy=simple_strategy,
        risk_manager=risk_manager,
        broker=broker,
    )


class TestBotConfig:
    """Test bot configuration defaults."""

    def test_defaults_are_valid(self):
        cfg = BotConfig()
        assert cfg.portfolio_value > 0
        assert cfg.poll_interval_seconds > 0

    def test_custom_config(self):
        cfg = BotConfig(portfolio_value=50_000.0, poll_interval_seconds=5.0)
        assert cfg.portfolio_value == 50_000.0
        assert cfg.poll_interval_seconds == 5.0


class TestBotState:
    """Test bot state enum."""

    def test_all_states_exist(self):
        assert BotState.INIT
        assert BotState.RUNNING
        assert BotState.PAUSED
        assert BotState.STOPPED


class TestBotEngineInit:
    """Test bot engine initialization."""

    def test_initial_state_is_init(self, bot: BotEngine):
        assert bot.state == BotState.INIT

    def test_components_are_set(self, bot: BotEngine):
        assert bot.strategy is not None
        assert bot.risk_manager is not None
        assert bot.broker is not None

    def test_initial_cycle_count_zero(self, bot: BotEngine):
        assert bot.cycle_count == 0


class TestSignalProcessing:
    """Test the signal processing pipeline (strategy -> risk -> broker)."""

    def test_process_cycle_generates_order(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.RUNNING
        bot.process_cycle(market_data)
        assert bot.cycle_count == 1
        # Should have opened a position
        assert bot.broker.get_position("BTCUSDT") is not None

    def test_process_cycle_no_signals_with_empty_data(self, bot: BotEngine):
        bot.state = BotState.RUNNING
        bot.process_cycle({})
        assert bot.cycle_count == 1
        assert bot.broker.get_position("BTCUSDT") is None

    def test_process_cycle_skipped_when_not_running(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.INIT
        bot.process_cycle(market_data)
        assert bot.cycle_count == 0

    def test_process_cycle_skipped_when_stopped(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.STOPPED
        bot.process_cycle(market_data)
        assert bot.cycle_count == 0

    def test_risk_manager_rejects_signal(self, bot: BotEngine, market_data: dict):
        """When risk manager rejects, broker should not receive order."""
        bot.state = BotState.RUNNING
        # Fill up positions to max
        for i in range(5):
            bot.risk_manager.register_position(
                f"SYM{i}USDT",
                Signal(
                    timestamp=pd.Timestamp("2024-01-15", tz="UTC"),
                    symbol=f"SYM{i}USDT",
                    direction=Direction.LONG,
                    price=100.0,
                    strategy_id="test",
                )
            )
        bot.process_cycle(market_data)
        # Signal was generated but rejected by risk manager
        assert bot.broker.get_position("BTCUSDT") is None


class TestStopLossManagement:
    """Test stop loss checking during bot cycle."""

    def test_stop_loss_closes_position(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.RUNNING
        bot.process_cycle(market_data)
        assert bot.broker.get_position("BTCUSDT") is not None

        # Price drops below stop loss
        current_prices = {"BTCUSDT": 45_000.0}  # well below entry
        bot.check_stop_losses(current_prices)
        # Position should be closed
        pos = bot.broker.get_position("BTCUSDT")
        assert pos is None or pos.size == 0


class TestKillSwitch:
    """Test kill switch integration."""

    def test_kill_switch_stops_bot(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.RUNNING
        bot.risk_manager.update_daily_pnl(pnl_pct=-0.12)  # trigger kill switch
        bot.process_cycle(market_data)
        # Bot should not process when kill switch is active
        assert bot.cycle_count == 0 or bot.broker.get_position("BTCUSDT") is None

    def test_kill_switch_closes_all_positions(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.RUNNING
        bot.process_cycle(market_data)
        assert bot.broker.get_position("BTCUSDT") is not None

        bot.risk_manager.update_daily_pnl(pnl_pct=-0.12)
        current_prices = {"BTCUSDT": 50_000.0}
        bot.handle_kill_switch(current_prices)
        assert bot.broker.get_position("BTCUSDT") is None
        assert bot.state == BotState.STOPPED


class TestStateTransitions:
    """Test bot state transitions."""

    def test_start_transition(self, bot: BotEngine):
        bot.start()
        assert bot.state == BotState.RUNNING

    def test_stop_transition(self, bot: BotEngine):
        bot.start()
        bot.stop()
        assert bot.state == BotState.STOPPED

    def test_pause_transition(self, bot: BotEngine):
        bot.start()
        bot.pause()
        assert bot.state == BotState.PAUSED

    def test_resume_from_pause(self, bot: BotEngine):
        bot.start()
        bot.pause()
        bot.resume()
        assert bot.state == BotState.RUNNING

    def test_cannot_start_from_stopped(self, bot: BotEngine):
        bot.stop()
        bot.start()
        # Should remain stopped (need explicit reset)
        assert bot.state == BotState.STOPPED


class TestMetrics:
    """Test bot metrics and reporting."""

    def test_get_metrics_after_cycle(self, bot: BotEngine, market_data: dict):
        bot.state = BotState.RUNNING
        bot.process_cycle(market_data)
        metrics = bot.get_metrics()
        assert "cycle_count" in metrics
        assert "state" in metrics
        assert "positions" in metrics
        assert "cash" in metrics
        assert metrics["cycle_count"] == 1

    def test_get_metrics_initial(self, bot: BotEngine):
        metrics = bot.get_metrics()
        assert metrics["cycle_count"] == 0
        assert metrics["state"] == BotState.INIT.value
        assert metrics["positions"] == 0
