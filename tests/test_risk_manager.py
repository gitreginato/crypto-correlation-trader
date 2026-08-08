"""Tests for src/bot/risk_manager.py.

TDD: tests written before implementation. Covers position sizing,
stop loss, max drawdown, kill switch, and exposure limits.
"""
import numpy as np
import pytest

from src.bot.risk_manager import RiskConfig, RiskManager, RiskDecision
from src.strategy.base import Direction, Signal


@pytest.fixture
def risk_config() -> RiskConfig:
    """Standard risk config for testing."""
    return RiskConfig(
        max_position_pct=0.10,  # 10% per position
        max_total_exposure=1.0,  # 100% total
        stop_loss_pct=0.02,  # -2% per position
        max_daily_drawdown=0.05,  # -5% daily
        kill_switch_drawdown=0.10,  # -10% kill
        max_positions=5,
    )


@pytest.fixture
def risk_manager(risk_config: RiskConfig) -> RiskManager:
    """RiskManager with standard config and $10k portfolio."""
    return RiskManager(config=risk_config, portfolio_value=10_000.0)


@pytest.fixture
def long_signal() -> Signal:
    """A long signal for BTCUSDT at $50k."""
    return Signal(
        timestamp=pytest.ts if hasattr(pytest, "ts") else __import__("pandas").Timestamp("2024-01-15"),
        symbol="BTCUSDT",
        direction=Direction.LONG,
        price=50_000.0,
        stop_loss=49_000.0,
        take_profit=52_000.0,
        strategy_id="test",
    )


@pytest.fixture
def short_signal() -> Signal:
    """A short signal for ETHUSDT at $3k."""
    return Signal(
        timestamp=pytest.ts if hasattr(pytest, "ts") else __import__("pandas").Timestamp("2024-01-15"),
        symbol="ETHUSDT",
        direction=Direction.SHORT,
        price=3_000.0,
        stop_loss=3_060.0,
        take_profit=2_900.0,
        strategy_id="test",
    )


class TestRiskConfig:
    """Test RiskConfig defaults and validation."""

    def test_defaults_are_valid(self):
        cfg = RiskConfig()
        assert cfg.max_position_pct > 0
        assert cfg.max_total_exposure > 0
        assert cfg.stop_loss_pct > 0
        assert cfg.max_daily_drawdown > 0
        assert cfg.kill_switch_drawdown > cfg.max_daily_drawdown
        assert cfg.max_positions > 0

    def test_custom_config(self):
        cfg = RiskConfig(max_position_pct=0.05, max_positions=3)
        assert cfg.max_position_pct == 0.05
        assert cfg.max_positions == 3


class TestPositionSizing:
    """Test position size calculation."""

    def test_position_size_within_limit(self, risk_manager: RiskManager):
        size = risk_manager.calculate_position_size(price=50_000.0)
        # 10% of 10k = 1000 / 50000 = 0.02 BTC
        assert size > 0
        assert size * 50_000.0 <= 10_000.0 * 0.10

    def test_position_size_zero_for_zero_price(self, risk_manager: RiskManager):
        size = risk_manager.calculate_position_size(price=0.0)
        assert size == 0.0

    def test_position_size_zero_for_negative_price(self, risk_manager: RiskManager):
        size = risk_manager.calculate_position_size(price=-100.0)
        assert size == 0.0

    def test_position_size_scales_with_portfolio(self, risk_config: RiskConfig):
        rm_small = RiskManager(config=risk_config, portfolio_value=1_000.0)
        rm_large = RiskManager(config=risk_config, portfolio_value=100_000.0)
        size_small = rm_small.calculate_position_size(price=50_000.0)
        size_large = rm_large.calculate_position_size(price=50_000.0)
        assert size_large > size_small


class TestRiskDecision:
    """Test approve/reject of signals based on risk rules."""

    def test_approve_valid_signal(self, risk_manager: RiskManager, long_signal: Signal):
        decision = risk_manager.evaluate(long_signal)
        assert decision.approved
        assert decision.reason == ""

    def test_reject_when_max_positions_reached(self, risk_manager: RiskManager, long_signal: Signal):
        # Fill up to max positions
        for i in range(5):
            sig = Signal(
                timestamp=long_signal.timestamp,
                symbol=f"SYM{i}USDT",
                direction=Direction.LONG,
                price=100.0,
                strategy_id="test",
            )
            risk_manager.register_position(sig.symbol, sig)
        decision = risk_manager.evaluate(long_signal)
        assert not decision.approved
        assert "max" in decision.reason.lower() or "position" in decision.reason.lower()

    def test_reject_duplicate_symbol(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        decision = risk_manager.evaluate(long_signal)
        assert not decision.approved
        assert "already" in decision.reason.lower() or "duplicate" in decision.reason.lower()

    def test_reject_when_exposure_exceeded(self, risk_manager: RiskManager, long_signal: Signal):
        # Simulate 95% exposure already
        risk_manager.current_exposure = 0.95
        # A signal at high price would push over 100%
        big_signal = Signal(
            timestamp=long_signal.timestamp,
            symbol="NEWUSDT",
            direction=Direction.LONG,
            price=50_000.0,
            strategy_id="test",
        )
        decision = risk_manager.evaluate(big_signal)
        assert not decision.approved
        assert "exposure" in decision.reason.lower()


class TestStopLoss:
    """Test stop loss tracking and triggering."""

    def test_stop_loss_triggers_on_long(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        # Price drops below stop loss
        should_stop = risk_manager.check_stop_loss("BTCUSDT", current_price=48_500.0)
        assert should_stop

    def test_stop_loss_not_triggered_on_long(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        should_stop = risk_manager.check_stop_loss("BTCUSDT", current_price=49_500.0)
        assert not should_stop

    def test_stop_loss_triggers_on_short(self, risk_manager: RiskManager, short_signal: Signal):
        risk_manager.register_position("ETHUSDT", short_signal)
        # Price rises above stop loss for short
        should_stop = risk_manager.check_stop_loss("ETHUSDT", current_price=3_100.0)
        assert should_stop

    def test_stop_loss_not_triggered_on_short(self, risk_manager: RiskManager, short_signal: Signal):
        risk_manager.register_position("ETHUSDT", short_signal)
        should_stop = risk_manager.check_stop_loss("ETHUSDT", current_price=2_950.0)
        assert not should_stop

    def test_stop_loss_unknown_symbol_returns_false(self, risk_manager: RiskManager):
        should_stop = risk_manager.check_stop_loss("UNKNOWN", current_price=100.0)
        assert not should_stop


class TestDrawdownAndKillSwitch:
    """Test daily drawdown limit and kill switch."""

    def test_daily_drawdown_within_limit(self, risk_manager: RiskManager):
        # -3% drawdown, limit is -5%
        risk_manager.update_daily_pnl(pnl_pct=-0.03)
        assert not risk_manager.is_daily_limit_hit()

    def test_daily_drawdown_limit_hit(self, risk_manager: RiskManager):
        risk_manager.update_daily_pnl(pnl_pct=-0.06)
        assert risk_manager.is_daily_limit_hit()

    def test_kill_switch_triggered(self, risk_manager: RiskManager):
        risk_manager.update_daily_pnl(pnl_pct=-0.12)
        assert risk_manager.is_kill_switch_triggered()

    def test_kill_switch_not_triggered(self, risk_manager: RiskManager):
        risk_manager.update_daily_pnl(pnl_pct=-0.08)
        assert not risk_manager.is_kill_switch_triggered()

    def test_kill_switch_rejects_all_signals(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.update_daily_pnl(pnl_pct=-0.12)
        decision = risk_manager.evaluate(long_signal)
        assert not decision.approved
        assert "kill" in decision.reason.lower()


class TestPositionTracking:
    """Test position registration and removal."""

    def test_register_position(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        assert "BTCUSDT" in risk_manager.positions
        assert risk_manager.get_position_count() == 1

    def test_close_position(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        risk_manager.close_position("BTCUSDT")
        assert "BTCUSDT" not in risk_manager.positions
        assert risk_manager.get_position_count() == 0

    def test_close_unknown_position_no_error(self, risk_manager: RiskManager):
        risk_manager.close_position("UNKNOWN")
        assert risk_manager.get_position_count() == 0

    def test_reset_daily(self, risk_manager: RiskManager):
        risk_manager.update_daily_pnl(pnl_pct=-0.03)
        risk_manager.reset_daily()
        assert risk_manager.daily_pnl_pct == 0.0
        assert not risk_manager.is_daily_limit_hit()


class TestExposureCalculation:
    """Test total exposure tracking."""

    def test_initial_exposure_zero(self, risk_manager: RiskManager):
        assert risk_manager.current_exposure == 0.0

    def test_exposure_increases_with_position(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        exposure = risk_manager.get_total_exposure()
        assert exposure > 0.0

    def test_exposure_decreases_on_close(self, risk_manager: RiskManager, long_signal: Signal):
        risk_manager.register_position("BTCUSDT", long_signal)
        exposure_before = risk_manager.get_total_exposure()
        risk_manager.close_position("BTCUSDT")
        exposure_after = risk_manager.get_total_exposure()
        assert exposure_after < exposure_before
