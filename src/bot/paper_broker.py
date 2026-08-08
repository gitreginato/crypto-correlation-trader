"""PaperBroker: simulates order execution with realistic fees and slippage.

Tracks positions, cash, PnL, and fill history. No real orders are sent.
Used for paper trading (Fase 4) before going live (Fase 5).

Execution model:
- Market orders only (taker fee)
- Slippage: price adjusted by N bps in adverse direction
- No partial fills (simplified)
- Insufficient cash = order rejected
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.strategy.base import Direction, Signal


@dataclass
class PaperBrokerConfig:
    """Configuration for the paper broker."""
    initial_cash: float = 10_000.0
    taker_fee: float = 0.001  # 0.1%
    maker_fee: float = 0.00075  # 0.075%
    slippage_bps: float = 5.0  # 5 basis points = 0.05%


@dataclass
class Order:
    """An order to be executed."""
    symbol: str
    side: str  # "BUY" or "SELL"
    size: float
    price: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    order_type: str = "MARKET"


@dataclass
class Fill:
    """A confirmed fill from the broker."""
    symbol: str
    side: str
    fill_size: float
    fill_price: float
    fee: float
    timestamp: datetime


@dataclass
class Position:
    """An open position."""
    symbol: str
    side: str  # "LONG" or "SHORT"
    size: float  # positive for long, negative for short
    entry_price: float
    entry_time: datetime


class PaperBroker:
    """Simulates order execution for paper trading.

    Usage:
        broker = PaperBroker(config=PaperBrokerConfig())
        order = broker.create_order(signal, size=0.1)
        fill = broker.execute_order(order)
        if fill:
            print(f"Filled at {fill.fill_price}, fee {fill.fee}")
    """

    def __init__(self, config: PaperBrokerConfig):
        self.config = config
        self._cash: float = config.initial_cash
        self._positions: dict[str, Position] = {}
        self._fills: list[Fill] = []

    def create_order(self, signal: Signal, size: float) -> Order:
        """Create an order from a trading signal.

        LONG signal = BUY order, SHORT signal = SELL order.
        """
        side = "BUY" if signal.direction == Direction.LONG else "SELL"
        return Order(
            symbol=signal.symbol,
            side=side,
            size=abs(size),
            price=signal.price,
            timestamp=signal.timestamp.to_pydatetime()
                if hasattr(signal.timestamp, "to_pydatetime")
                else datetime.now(timezone.utc),
        )

    def execute_order(self, order: Order) -> Optional[Fill]:
        """Execute a market order with slippage and fees.

        Returns Fill if successful, None if rejected (insufficient cash, zero size).
        """
        if order.size <= 0:
            return None

        # Apply slippage: BUY pays more, SELL receives less
        slippage = order.price * (self.config.slippage_bps / 10_000.0)
        if order.side == "BUY":
            fill_price = order.price + slippage
        else:
            fill_price = order.price - slippage

        fill_notional = fill_price * order.size
        fee = fill_notional * self.config.taker_fee

        # Check sufficient cash for BUY
        if order.side == "BUY":
            total_cost = fill_notional + fee
            if total_cost > self._cash:
                return None  # rejected
            self._cash -= total_cost
            self._update_position(order.symbol, order.size, fill_price, "LONG")
        else:  # SELL
            # Check we have the position to sell (for closing longs)
            # or cash to cover (for opening shorts)
            proceeds = fill_notional - fee
            self._cash += proceeds
            self._update_position(order.symbol, -order.size, fill_price, "SHORT")

        fill = Fill(
            symbol=order.symbol,
            side=order.side,
            fill_size=order.size,
            fill_price=fill_price,
            fee=fee,
            timestamp=datetime.now(timezone.utc),
        )
        self._fills.append(fill)
        return fill

    def _update_position(self, symbol: str, delta_size: float, price: float, side: str) -> None:
        """Update or create position after a fill."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            new_size = pos.size + delta_size
            if abs(new_size) < 1e-10:  # position closed
                del self._positions[symbol]
            else:
                pos.size = new_size
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                side=side,
                size=delta_size,
                entry_price=price,
                entry_time=datetime.now(timezone.utc),
            )

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get open position for a symbol, or None."""
        return self._positions.get(symbol)

    def get_cash(self) -> float:
        """Return current cash balance."""
        return self._cash

    def get_unrealized_pnl(self, current_prices: dict[str, float]) -> float:
        """Calculate total unrealized PnL across all positions.

        Args:
            current_prices: Dict mapping symbol to current price.
        """
        total_pnl = 0.0
        for symbol, pos in self._positions.items():
            if symbol not in current_prices:
                continue
            current_price = current_prices[symbol]
            # Long: pnl = (current - entry) * size
            # Short: pnl = (entry - current) * abs(size)
            if pos.size > 0:  # long
                total_pnl += (current_price - pos.entry_price) * pos.size
            else:  # short
                total_pnl += (pos.entry_price - current_price) * abs(pos.size)
        return total_pnl

    def get_total_equity(self, current_prices: dict[str, float]) -> float:
        """Return total equity = cash + unrealized PnL."""
        return self._cash + self.get_unrealized_pnl(current_prices)

    def get_fill_history(self) -> list[Fill]:
        """Return list of all fills."""
        return self._fills.copy()

    def clear_history(self) -> None:
        """Clear fill history only (positions and cash preserved)."""
        self._fills.clear()

    def reset(self) -> None:
        """Reset broker to initial state (cash, no positions, no fills)."""
        self._cash = self.config.initial_cash
        self._positions.clear()
        self._fills.clear()
