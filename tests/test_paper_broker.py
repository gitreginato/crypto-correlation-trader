"""Tests for src/bot/paper_broker.py.

TDD: tests written before implementation. Covers order execution,
PnL tracking, position management, and fee calculation.
"""
import pandas as pd
import pytest

from src.bot.paper_broker import PaperBroker, PaperBrokerConfig, Fill, Order
from src.strategy.base import Direction, Signal


@pytest.fixture
def broker_config() -> PaperBrokerConfig:
    return PaperBrokerConfig(
        initial_cash=10_000.0,
        taker_fee=0.001,  # 0.1%
        maker_fee=0.00075,  # 0.075%
        slippage_bps=5.0,  # 5 bps
    )


@pytest.fixture
def broker(broker_config: PaperBrokerConfig) -> PaperBroker:
    return PaperBroker(config=broker_config)


@pytest.fixture
def long_signal() -> Signal:
    return Signal(
        timestamp=pd.Timestamp("2024-01-15 10:00:00", tz="UTC"),
        symbol="BTCUSDT",
        direction=Direction.LONG,
        price=50_000.0,
        strategy_id="test",
    )


@pytest.fixture
def short_signal() -> Signal:
    return Signal(
        timestamp=pd.Timestamp("2024-01-15 10:00:00", tz="UTC"),
        symbol="ETHUSDT",
        direction=Direction.SHORT,
        price=3_000.0,
        strategy_id="test",
    )


class TestPaperBrokerConfig:
    """Test config defaults."""

    def test_defaults_are_valid(self):
        cfg = PaperBrokerConfig()
        assert cfg.initial_cash > 0
        assert cfg.taker_fee > 0
        assert cfg.maker_fee > 0
        assert cfg.taker_fee > cfg.maker_fee  # taker costs more
        assert cfg.slippage_bps >= 0


class TestOrderCreation:
    """Test order creation from signals."""

    def test_create_buy_order_from_long_signal(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        assert order.side == "BUY"
        assert order.symbol == "BTCUSDT"
        assert order.size == 0.1

    def test_create_sell_order_from_short_signal(self, broker: PaperBroker, short_signal: Signal):
        order = broker.create_order(short_signal, size=1.0)
        assert order.side == "SELL"
        assert order.symbol == "ETHUSDT"
        assert order.size == 1.0


class TestOrderExecution:
    """Test order filling with slippage and fees."""

    def test_buy_order_fills_with_slippage(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        fill = broker.execute_order(order)
        assert fill is not None
        # Slippage makes buy price higher
        assert fill.fill_price > long_signal.price
        assert fill.fee > 0

    def test_sell_order_fills_with_slippage(self, broker: PaperBroker, short_signal: Signal):
        order = broker.create_order(short_signal, size=1.0)
        fill = broker.execute_order(order)
        assert fill is not None
        # Slippage makes sell price lower
        assert fill.fill_price < short_signal.price
        assert fill.fee > 0

    def test_fee_calculation_taker(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        fill = broker.execute_order(order)
        expected_fee = fill.fill_price * fill.fill_size * broker.config.taker_fee
        assert abs(fill.fee - expected_fee) < 0.01

    def test_fill_has_timestamp(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        fill = broker.execute_order(order)
        assert fill.timestamp is not None


class TestPositionTracking:
    """Test position and PnL tracking."""

    def test_open_long_position(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        pos = broker.get_position("BTCUSDT")
        assert pos is not None
        assert pos.size > 0
        assert pos.side == "LONG"

    def test_open_short_position(self, broker: PaperBroker, short_signal: Signal):
        order = broker.create_order(short_signal, size=1.0)
        broker.execute_order(order)
        pos = broker.get_position("ETHUSDT")
        assert pos is not None
        assert pos.size < 0  # short = negative size
        assert pos.side == "SHORT"

    def test_close_long_position(self, broker: PaperBroker, long_signal: Signal):
        # Open
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        # Close at current price
        close_signal = Signal(
            timestamp=long_signal.timestamp,
            symbol="BTCUSDT",
            direction=Direction.SHORT,
            price=51_000.0,
            strategy_id="test",
        )
        close_order = broker.create_order(close_signal, size=0.1)
        broker.execute_order(close_order)
        pos = broker.get_position("BTCUSDT")
        assert pos is None or pos.size == 0

    def test_no_position_for_unknown_symbol(self, broker: PaperBroker):
        pos = broker.get_position("UNKNOWN")
        assert pos is None


class TestCashAndPnL:
    """Test cash balance and PnL calculation."""

    def test_initial_cash(self, broker: PaperBroker):
        assert broker.get_cash() == 10_000.0

    def test_cash_decreases_on_buy(self, broker: PaperBroker, long_signal: Signal):
        initial = broker.get_cash()
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        assert broker.get_cash() < initial

    def test_unrealized_pnl_long_in_profit(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        # Price went up
        pnl = broker.get_unrealized_pnl({"BTCUSDT": 55_000.0})
        assert pnl > 0

    def test_unrealized_pnl_long_in_loss(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        # Price went down
        pnl = broker.get_unrealized_pnl({"BTCUSDT": 45_000.0})
        assert pnl < 0

    def test_unrealized_pnl_short_in_profit(self, broker: PaperBroker, short_signal: Signal):
        order = broker.create_order(short_signal, size=1.0)
        broker.execute_order(order)
        # Price went down (good for short)
        pnl = broker.get_unrealized_pnl({"ETHUSDT": 2_500.0})
        assert pnl > 0

    def test_unrealized_pnl_no_positions(self, broker: PaperBroker):
        pnl = broker.get_unrealized_pnl({"BTCUSDT": 50_000.0})
        assert pnl == 0.0

    def test_total_equity(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        equity = broker.get_total_equity({"BTCUSDT": 50_000.0})
        # equity = cash + position_value
        assert equity > 0


class TestOrderLog:
    """Test order/fill logging."""

    def test_fill_log_recorded(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        fills = broker.get_fill_history()
        assert len(fills) == 1
        assert fills[0].symbol == "BTCUSDT"

    def test_multiple_fills_logged(self, broker: PaperBroker, long_signal: Signal, short_signal: Signal):
        o1 = broker.create_order(long_signal, size=0.1)
        broker.execute_order(o1)
        o2 = broker.create_order(short_signal, size=1.0)
        broker.execute_order(o2)
        fills = broker.get_fill_history()
        assert len(fills) == 2

    def test_clear_history(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        broker.clear_history()
        assert len(broker.get_fill_history()) == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_insufficient_cash_rejected(self, broker: PaperBroker, long_signal: Signal):
        # Try to buy more than we can afford
        order = broker.create_order(long_signal, size=10.0)  # 10 BTC = $500k
        fill = broker.execute_order(order)
        assert fill is None  # rejected

    def test_zero_size_order_rejected(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.0)
        fill = broker.execute_order(order)
        assert fill is None

    def test_reset_clears_all(self, broker: PaperBroker, long_signal: Signal):
        order = broker.create_order(long_signal, size=0.1)
        broker.execute_order(order)
        broker.reset()
        assert broker.get_cash() == broker.config.initial_cash
        assert len(broker.get_fill_history()) == 0
        assert broker.get_position("BTCUSDT") is None
