"""BotEngine: main loop that integrates strategy, risk manager, and broker.

This is the orchestrator for paper trading (Fase 4). It:
1. Receives market data (from live_collector or replay)
2. Asks strategy for signals
3. Passes signals through risk manager
4. Executes approved signals via broker
5. Checks stop losses on open positions
6. Handles kill switch

The engine is synchronous for testing. In production, it runs in an
asyncio loop with the live_collector feeding data.
"""
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from src.bot.paper_broker import PaperBroker
from src.bot.risk_manager import RiskManager
from src.strategy.base import BaseStrategy, Direction, Signal


class BotState(str, Enum):
    """Bot state machine states."""
    INIT = "INIT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass
class BotConfig:
    """Configuration for the bot engine."""
    portfolio_value: float = 10_000.0
    poll_interval_seconds: float = 1.0


class BotEngine:
    """Main bot orchestrator.

    Usage:
        engine = BotEngine(
            config=BotConfig(),
            strategy=my_strategy,
            risk_manager=risk_mgr,
            broker=paper_broker,
        )
        engine.start()
        engine.process_cycle(market_data)
        engine.stop()
    """

    def __init__(
        self,
        config: BotConfig,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        broker: PaperBroker,
    ):
        self.config = config
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.broker = broker
        self.state: BotState = BotState.INIT
        self.cycle_count: int = 0

    def start(self) -> None:
        """Transition to RUNNING state."""
        if self.state == BotState.STOPPED:
            return  # cannot start from stopped without reset
        self.state = BotState.RUNNING

    def stop(self) -> None:
        """Transition to STOPPED state."""
        self.state = BotState.STOPPED

    def pause(self) -> None:
        """Transition to PAUSED state (only from RUNNING)."""
        if self.state == BotState.RUNNING:
            self.state = BotState.PAUSED

    def resume(self) -> None:
        """Resume from PAUSED to RUNNING."""
        if self.state == BotState.PAUSED:
            self.state = BotState.RUNNING

    def process_cycle(self, market_data: dict[str, pd.DataFrame]) -> None:
        """Process one trading cycle: signals -> risk -> execution.

        Args:
            market_data: Dict mapping symbol to OHLCV DataFrame.
        """
        if self.state != BotState.RUNNING:
            return

        if self.risk_manager.is_kill_switch_triggered():
            current_prices = self._extract_current_prices(market_data)
            self.handle_kill_switch(current_prices)
            return

        self.cycle_count += 1

        # 1. Generate signals from strategy
        signals = self.strategy.generate_signals(market_data)
        if not signals:
            return

        # 2. Evaluate each signal through risk manager
        for signal in signals:
            decision = self.risk_manager.evaluate(signal)
            if not decision.approved:
                continue

            # 3. Execute via broker
            size = decision.adjusted_size or 0.0
            if size > 0:
                order = self.broker.create_order(signal, size=size)
                fill = self.broker.execute_order(order)
                if fill:
                    self.risk_manager.register_position(signal.symbol, signal)

    def check_stop_losses(self, current_prices: dict[str, float]) -> None:
        """Check and close positions that hit stop loss."""
        for symbol in list(self.risk_manager.positions.keys()):
            if self.risk_manager.check_stop_loss(symbol, current_prices.get(symbol, 0.0)):
                self._close_position(symbol, current_prices.get(symbol, 0.0))

    def handle_kill_switch(self, current_prices: dict[str, float]) -> None:
        """Close all positions and stop the bot."""
        for symbol in list(self.risk_manager.positions.keys()):
            self._close_position(symbol, current_prices.get(symbol, 0.0))
        self.state = BotState.STOPPED

    def _close_position(self, symbol: str, current_price: float) -> None:
        """Close a position at current price."""
        pos = self.broker.get_position(symbol)
        if pos is None or pos.size == 0:
            return

        close_direction = Direction.SHORT if pos.size > 0 else Direction.LONG
        close_signal = Signal(
            timestamp=pd.Timestamp.now(tz="UTC"),
            symbol=symbol,
            direction=close_direction,
            price=current_price,
            strategy_id="stop_loss",
        )
        order = self.broker.create_order(close_signal, size=abs(pos.size))
        self.broker.execute_order(order)
        self.risk_manager.close_position(symbol)

    def _extract_current_prices(self, market_data: dict[str, pd.DataFrame]) -> dict[str, float]:
        """Extract latest close price for each symbol from market data."""
        prices = {}
        for symbol, df in market_data.items():
            if not df.empty and "close" in df.columns:
                prices[symbol] = float(df["close"].iloc[-1])
        return prices

    def get_metrics(self) -> dict:
        """Return current bot metrics for monitoring."""
        return {
            "cycle_count": self.cycle_count,
            "state": self.state.value,
            "positions": self.risk_manager.get_position_count(),
            "cash": self.broker.get_cash(),
            "exposure": self.risk_manager.get_total_exposure(),
            "daily_pnl_pct": self.risk_manager.daily_pnl_pct,
            "kill_switch": self.risk_manager.is_kill_switch_triggered(),
        }
