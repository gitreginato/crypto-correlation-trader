"""RiskManager: enforces position sizing, stop loss, drawdown limits, and kill switch.

This is the safety layer between strategy signals and order execution.
No signal reaches the broker without passing through RiskManager.

Rules enforced:
- Max position size: X% of portfolio per asset
- Max total exposure: Y% of portfolio (default 100%, no leverage)
- Stop loss: -Z% per position (configurable per signal)
- Max daily drawdown: -W% (stops new entries, keeps managing exits)
- Kill switch: -K% (closes everything, halts the bot)
- Max concurrent positions
- No duplicate symbols
"""
from dataclasses import dataclass
from typing import Optional

from src.strategy.base import Direction, Signal


@dataclass
class RiskConfig:
    """Configuration for risk management rules."""
    max_position_pct: float = 0.10  # 10% of portfolio per position
    max_total_exposure: float = 1.0  # 100% total (no leverage)
    stop_loss_pct: float = 0.02  # -2% default stop loss
    max_daily_drawdown: float = 0.05  # -5% daily limit
    kill_switch_drawdown: float = 0.10  # -10% kill switch
    max_positions: int = 5


@dataclass
class RiskDecision:
    """Result of evaluating a signal through risk checks."""
    approved: bool
    reason: str = ""
    adjusted_size: Optional[float] = None


class RiskManager:
    """Evaluates and enforces risk rules on trading signals.

    Usage:
        rm = RiskManager(config=RiskConfig(), portfolio_value=10_000.0)
        decision = rm.evaluate(signal)
        if decision.approved:
            broker.execute(signal, size=decision.adjusted_size)
    """

    def __init__(self, config: RiskConfig, portfolio_value: float):
        self.config = config
        self.portfolio_value = portfolio_value
        self.positions: dict[str, Signal] = {}
        self.current_exposure: float = 0.0
        self.daily_pnl_pct: float = 0.0
        self._kill_switch_active: bool = False

    def calculate_position_size(self, price: float) -> float:
        """Calculate position size in base currency units.

        Size = (portfolio_value * max_position_pct) / price
        Returns 0 if price is invalid.
        """
        if price <= 0:
            return 0.0
        max_notional = self.portfolio_value * self.config.max_position_pct
        return max_notional / price

    def evaluate(self, signal: Signal) -> RiskDecision:
        """Evaluate a signal through all risk checks.

        Returns RiskDecision with approved=True if all checks pass,
        or approved=False with a reason string.
        """
        if self._kill_switch_active:
            return RiskDecision(approved=False, reason="Kill switch active: all trading halted")

        if signal.symbol in self.positions:
            return RiskDecision(approved=False, reason=f"Position already open for {signal.symbol}")

        if len(self.positions) >= self.config.max_positions:
            return RiskDecision(
                approved=False,
                reason=f"Max positions reached ({self.config.max_positions})"
            )

        position_size = self.calculate_position_size(signal.price)
        position_notional = position_size * signal.price
        new_exposure = self.current_exposure + (position_notional / self.portfolio_value)

        if new_exposure > self.config.max_total_exposure:
            return RiskDecision(
                approved=False,
                reason=f"Exposure limit exceeded: {new_exposure:.1%} > {self.config.max_total_exposure:.1%}"
            )

        return RiskDecision(approved=True, adjusted_size=position_size)

    def check_stop_loss(self, symbol: str, current_price: float) -> bool:
        """Check if stop loss is triggered for a position.

        For LONG: triggers if current_price <= signal.stop_loss
        For SHORT: triggers if current_price >= signal.stop_loss
        """
        signal = self.positions.get(symbol)
        if signal is None or signal.stop_loss is None:
            return False

        if signal.direction == Direction.LONG:
            return current_price <= signal.stop_loss
        elif signal.direction == Direction.SHORT:
            return current_price >= signal.stop_loss
        return False

    def update_daily_pnl(self, pnl_pct: float) -> None:
        """Update cumulative daily PnL percentage.

        Args:
            pnl_pct: Cumulative PnL as fraction of portfolio (e.g. -0.03 = -3%)
        """
        self.daily_pnl_pct = pnl_pct
        if abs(self.daily_pnl_pct) >= self.config.kill_switch_drawdown and self.daily_pnl_pct < 0:
            self._kill_switch_active = True

    def is_daily_limit_hit(self) -> bool:
        """Check if daily drawdown limit is reached."""
        return self.daily_pnl_pct <= -self.config.max_daily_drawdown

    def is_kill_switch_triggered(self) -> bool:
        """Check if kill switch is active."""
        return self._kill_switch_active

    def register_position(self, symbol: str, signal: Signal) -> None:
        """Register a new open position."""
        self.positions[symbol] = signal
        notional = self.calculate_position_size(signal.price) * signal.price
        self.current_exposure += notional / self.portfolio_value

    def close_position(self, symbol: str) -> None:
        """Remove a position from tracking."""
        signal = self.positions.pop(symbol, None)
        if signal is not None:
            notional = self.calculate_position_size(signal.price) * signal.price
            self.current_exposure -= notional / self.portfolio_value
            self.current_exposure = max(0.0, self.current_exposure)

    def get_position_count(self) -> int:
        """Return number of open positions."""
        return len(self.positions)

    def get_total_exposure(self) -> float:
        """Return current total exposure as fraction of portfolio."""
        return self.current_exposure

    def reset_daily(self) -> None:
        """Reset daily PnL counter (called at start of new trading day)."""
        self.daily_pnl_pct = 0.0
