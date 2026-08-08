"""Backtest engine for strategy evaluation.

Vectorized backtest that processes signals bar-by-bar, tracks positions,
and computes performance metrics. Supports transaction costs and slippage.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.strategy.base import BaseStrategy, Direction, Signal


@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    risk_per_trade: float = 0.01  # 1% of capital
    fee_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005  # 0.05% per trade
    max_positions: int = 10
    funding_rate_per_8h: float = 0.0  # set for futures backtest


@dataclass
class Trade:
    """Represents a completed trade."""
    symbol: str
    direction: Direction
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    bars_held: int
    strategy_id: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Position:
    """An open position."""
    signal: Signal
    size: float
    entry_price: float
    entry_time: pd.Timestamp
    bars_held: int = 0


class BacktestEngine:
    """Vectorized backtest engine.

    Iterates through historical data bar-by-bar, generates signals at each bar,
    and simulates position entry/exit with transaction costs.
    """

    def __init__(self, strategy: BaseStrategy, config: BacktestConfig | None = None):
        self.strategy = strategy
        self.config = config or BacktestConfig()
        self.trades: list[Trade] = []
        self.positions: dict[str, Position] = {}
        self.equity_curve: list[dict] = []

    def run(self, data: dict[str, pd.DataFrame]) -> dict:
        """Run the backtest.

        Args:
            data: Dict mapping symbol to OHLCV DataFrame.

        Returns:
            Dict with trades, equity curve, and performance metrics.
        """
        # Align all DataFrames on the same index
        all_indices = pd.DatetimeIndex(sorted(set().union(*[df.index for df in data.values()])))
        symbols = list(data.keys())
        self.trades = []
        self.positions = {}
        self.equity_curve = []
        capital = self.config.initial_capital
        peak_equity = capital

        for i, timestamp in enumerate(all_indices):
            # 1. Update existing positions with current prices
            current_prices = {}
            for symbol in symbols:
                df = data[symbol]
                if timestamp in df.index:
                    current_prices[symbol] = float(str(df.loc[timestamp, "close"]))

            # 2. Check exits for open positions
            capital = self._check_exits(timestamp, current_prices, capital)

            # 3. Generate signals from data up to current bar
            data_up_to = {s: data[s].loc[:timestamp] for s in symbols if timestamp in data[s].index}
            if i >= 30:  # need enough data for indicators
                signals = self.strategy.generate_signals(data_up_to)
            else:
                signals = []

            # 4. Execute new signals
            for signal in signals:
                if signal.symbol not in current_prices:
                    continue
                if signal.symbol in self.positions:
                    continue
                if len(self.positions) >= self.config.max_positions:
                    continue
                capital = self._open_position(signal, current_prices[signal.symbol], capital)

            # 5. Update bars held
            for pos in self.positions.values():
                pos.bars_held += 1

            # 6. Compute current equity (unrealized + cash)
            unrealized = self._compute_unrealized_pnl(current_prices)
            total_equity = capital + unrealized
            peak_equity = max(peak_equity, total_equity)
            drawdown = (peak_equity - total_equity) / peak_equity if peak_equity > 0 else 0

            self.equity_curve.append({
                "timestamp": timestamp,
                "capital": capital,
                "unrealized": unrealized,
                "equity": total_equity,
                "drawdown": drawdown,
                "open_positions": len(self.positions),
            })

        # Close all remaining positions at last prices
        for symbol in list(self.positions.keys()):
            if symbol in current_prices:
                capital = self._close_position(symbol, current_prices[symbol], timestamp, capital, "end_of_data")

        return self._compute_metrics(capital)

    def _open_position(self, signal: Signal, fill_price: float, capital: float) -> float:
        """Open a new position based on a signal."""
        # Apply slippage
        if signal.is_long:
            actual_price = fill_price * (1 + self.config.slippage_rate)
        else:
            actual_price = fill_price * (1 - self.config.slippage_rate)

        # Position size based on risk
        risk_amount = capital * self.config.risk_per_trade * signal.confidence
        if signal.stop_loss and signal.stop_loss > 0:
            stop_distance = abs(actual_price - signal.stop_loss)
            size = risk_amount / stop_distance if stop_distance > 0 else risk_amount / actual_price
        else:
            size = risk_amount / actual_price

        # Cap position size
        max_position_value = capital * 0.20  # max 20% per position
        if size * actual_price > max_position_value:
            size = max_position_value / actual_price

        # Deduct entry fee
        fee = size * actual_price * self.config.fee_rate
        capital -= fee

        self.positions[signal.symbol] = Position(
            signal=signal,
            size=size,
            entry_price=actual_price,
            entry_time=signal.timestamp,
        )
        self.strategy.on_fill(signal, actual_price)
        return capital

    def _close_position(self, symbol: str, fill_price: float, timestamp: pd.Timestamp,
                        capital: float, reason: str = "") -> float:
        """Close a position and record the trade."""
        pos = self.positions.pop(symbol)
        self.strategy.on_close(symbol)

        # Apply slippage
        if pos.signal.is_long:
            actual_price = fill_price * (1 - self.config.slippage_rate)
        else:
            actual_price = fill_price * (1 + self.config.slippage_rate)

        # Compute PnL
        if pos.signal.is_long:
            pnl = (actual_price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - actual_price) * pos.size

        # Exit fee
        fee = pos.size * actual_price * self.config.fee_rate
        pnl -= fee
        capital += pnl

        pnl_pct = pnl / (pos.size * pos.entry_price) if pos.size * pos.entry_price > 0 else 0

        trade = Trade(
            symbol=symbol,
            direction=pos.signal.direction,
            entry_time=pos.entry_time,
            entry_price=pos.entry_price,
            exit_time=timestamp,
            exit_price=actual_price,
            size=pos.size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            bars_held=pos.bars_held,
            strategy_id=pos.signal.strategy_id,
            metadata={"exit_reason": reason, **pos.signal.metadata},
        )
        self.trades.append(trade)
        return capital

    def _check_exits(self, timestamp: pd.Timestamp, current_prices: dict[str, float], capital: float) -> float:
        """Check if any positions should be closed (stop loss, take profit)."""
        to_close = []

        for symbol, pos in self.positions.items():
            if symbol not in current_prices:
                continue
            price = current_prices[symbol]

            # Stop loss
            if pos.signal.stop_loss is not None:
                if pos.signal.is_long and price <= pos.signal.stop_loss:
                    to_close.append((symbol, "stop_loss"))
                elif pos.signal.is_short and price >= pos.signal.stop_loss:
                    to_close.append((symbol, "stop_loss"))

            # Take profit
            if pos.signal.take_profit is not None:
                if pos.signal.is_long and price >= pos.signal.take_profit:
                    to_close.append((symbol, "take_profit"))
                elif pos.signal.is_short and price <= pos.signal.take_profit:
                    to_close.append((symbol, "take_profit"))

        for symbol, reason in to_close:
            capital = self._close_position(symbol, current_prices[symbol], timestamp, capital, reason)

        return capital

    def _compute_unrealized_pnl(self, current_prices: dict[str, float]) -> float:
        """Compute total unrealized PnL of open positions."""
        total = 0.0
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                if pos.signal.is_long:
                    total += (price - pos.entry_price) * pos.size
                else:
                    total += (pos.entry_price - price) * pos.size
        return total

    def _compute_metrics(self, final_capital: float) -> dict:
        """Compute performance metrics from backtest results."""
        equity_df = pd.DataFrame(self.equity_curve)
        if equity_df.empty:
            return {
                "total_return": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "num_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "final_capital": final_capital,
            }

        # Returns
        equity_df["returns"] = equity_df["equity"].pct_change().fillna(0)

        # Total return
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital

        # Sharpe ratio (annualized, assuming daily bars)
        if equity_df["returns"].std() > 0:
            sharpe = equity_df["returns"].mean() / equity_df["returns"].std() * np.sqrt(365)
        else:
            sharpe = 0.0

        # Max drawdown
        max_dd = equity_df["drawdown"].max()

        # Trade statistics
        num_trades = len(self.trades)
        if num_trades > 0:
            wins = [t for t in self.trades if t.pnl > 0]
            losses = [t for t in self.trades if t.pnl <= 0]
            win_rate = len(wins) / num_trades
            gross_profit = sum(t.pnl for t in wins)
            gross_loss = abs(sum(t.pnl for t in losses))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
            avg_win = np.mean([t.pnl for t in wins]) if wins else 0
            avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
            avg_bars_held = float(np.mean([t.bars_held for t in self.trades]))
        else:
            win_rate = 0
            profit_factor = 0
            avg_win = 0
            avg_loss = 0
            expectancy = 0
            avg_bars_held = 0

        return {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "num_trades": num_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "final_capital": final_capital,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": expectancy,
            "avg_bars_held": avg_bars_held,
            "trades": self.trades,
            "equity_curve": equity_df,
        }


def print_metrics(metrics: dict) -> None:
    """Print backtest metrics in a readable format."""
    print(f"\n{'='*60}")
    print("  BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"  Initial Capital:  ${10000:>12,.2f}")
    print(f"  Final Capital:    ${metrics['final_capital']:>12,.2f}")
    print(f"  Total Return:      {metrics['total_return']:>12.2%}")
    print(f"  Sharpe Ratio:      {metrics['sharpe']:>12.2f}")
    print(f"  Max Drawdown:      {metrics['max_drawdown']:>12.2%}")
    print(f"  Num Trades:        {metrics['num_trades']:>12}")
    print(f"  Win Rate:          {metrics['win_rate']:>12.2%}")
    print(f"  Profit Factor:     {metrics['profit_factor']:>12.2f}")
    print(f"  Expectancy:        ${metrics['expectancy']:>11.2f}")
    print(f"  Avg Bars Held:     {metrics['avg_bars_held']:>12.1f}")
    print(f"{'='*60}")
