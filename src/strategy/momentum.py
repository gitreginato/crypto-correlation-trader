"""STRAT-06: Momentum / Trend Following.

Time-series momentum strategy: buy assets with positive momentum,
sell assets with negative momentum. Uses RSI, EMA crossover, and ADX
as confirmation filters. Regime-filtered to only operate in trending markets.

Signal logic:
    - Return over formation_period > 0: bullish momentum
    - RSI > 50: confirms bullish strength
    - EMA_fast > EMA_slow: confirms trend direction
    - ADX > 25: confirms trend strength
    - Hurst > 0.55: confirms trending regime
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.strategy.base import BaseStrategy, Direction, Signal, StrategyConfig
from src.strategy.regime_filter import Regime, RegimeFilter


@dataclass
class MomentumConfig(StrategyConfig):
    strategy_id: str = "STRAT-06"
    formation_period: int = 90
    rsi_period: int = 14
    rsi_trend_level: float = 50.0
    rsi_overbought: float = 95.0  # only skip extreme overbought (momentum = strength)
    rsi_oversold: float = 5.0   # only skip extreme oversold
    ema_fast: int = 20
    ema_slow: int = 50
    adx_period: int = 14
    adx_threshold: float = 25.0
    atr_period: int = 14
    atr_trailing_mult: float = 3.0
    min_confirmation: int = 2  # min indicators confirming (of 3)
    use_regime_filter: bool = True


class MomentumStrategy(BaseStrategy):
    """Time-series momentum strategy with multi-indicator confirmation."""

    def __init__(self, config: MomentumConfig | None = None):
        config = config or MomentumConfig()
        super().__init__(config)
        self.config: MomentumConfig = config
        self.regime_filter = RegimeFilter()
        self._trailing_stops: dict[str, float] = {}

    @staticmethod
    def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Compute RSI using Wilder's smoothing."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Compute MACD line, signal line, and histogram."""
        ema_fast = close.ewm(span=fast).mean()
        ema_slow = close.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        return macd_line, signal_line, macd_line - signal_line

    @staticmethod
    def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute ADX (Average Directional Index) using Wilder's method."""
        high, low, close = df["high"], df["low"], df["close"]

        # True Range
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, min_periods=period).mean()

        # Directional Movement (Wilder's formula)
        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = pd.Series(0.0, index=df.index)
        minus_dm = pd.Series(0.0, index=df.index)
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

        # Smoothed DI
        plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr.replace(0, np.nan))

        # DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1 / period, min_periods=period).mean()
        return adx

    @staticmethod
    def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute Average True Range."""
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / period, min_periods=period).mean()

    def _check_long_conditions(self, df: pd.DataFrame) -> tuple[bool, int, dict]:
        """Check if long momentum conditions are met.

        Returns (should_enter, confirmation_count, metadata).
        """
        close = df["close"]
        confirmations = 0
        meta = {}

        # 1. Momentum: positive return over formation period
        if len(close) > self.config.formation_period:
            momentum = (close.iloc[-1] - close.iloc[-self.config.formation_period]) / \
                close.iloc[-self.config.formation_period]
            meta["momentum"] = float(momentum)
            if momentum > 0:
                confirmations += 1

        # 2. RSI > trend level
        rsi = self.compute_rsi(close, self.config.rsi_period)
        current_rsi = rsi.iloc[-1]
        meta["rsi"] = float(current_rsi) if not np.isnan(current_rsi) else 50.0
        if current_rsi > self.config.rsi_trend_level:
            confirmations += 1

        # 3. EMA fast > EMA slow
        ema_f = close.ewm(span=self.config.ema_fast).mean()
        ema_s = close.ewm(span=self.config.ema_slow).mean()
        meta["ema_fast"] = float(ema_f.iloc[-1])
        meta["ema_slow"] = float(ema_s.iloc[-1])
        if ema_f.iloc[-1] > ema_s.iloc[-1]:
            confirmations += 1

        # ADX filter (not counted as confirmation, but as gate)
        adx = self.compute_adx(df, self.config.adx_period)
        current_adx = adx.iloc[-1]
        meta["adx"] = float(current_adx) if not np.isnan(current_adx) else 0.0
        adx_ok = current_adx >= self.config.adx_threshold

        should_enter = confirmations >= self.config.min_confirmation and adx_ok
        return should_enter, confirmations, meta

    def _check_short_conditions(self, df: pd.DataFrame) -> tuple[bool, int, dict]:
        """Check if short momentum conditions are met."""
        close = df["close"]
        confirmations = 0
        meta = {}

        # 1. Momentum: negative return
        if len(close) > self.config.formation_period:
            momentum = (close.iloc[-1] - close.iloc[-self.config.formation_period]) / \
                close.iloc[-self.config.formation_period]
            meta["momentum"] = float(momentum)
            if momentum < 0:
                confirmations += 1

        # 2. RSI < trend level
        rsi = self.compute_rsi(close, self.config.rsi_period)
        current_rsi = rsi.iloc[-1]
        meta["rsi"] = float(current_rsi) if not np.isnan(current_rsi) else 50.0
        if current_rsi < self.config.rsi_trend_level:
            confirmations += 1

        # 3. EMA fast < EMA slow
        ema_f = close.ewm(span=self.config.ema_fast).mean()
        ema_s = close.ewm(span=self.config.ema_slow).mean()
        meta["ema_fast"] = float(ema_f.iloc[-1])
        meta["ema_slow"] = float(ema_s.iloc[-1])
        if ema_f.iloc[-1] < ema_s.iloc[-1]:
            confirmations += 1

        # ADX filter
        adx = self.compute_adx(df, self.config.adx_period)
        current_adx = adx.iloc[-1]
        meta["adx"] = float(current_adx) if not np.isnan(current_adx) else 0.0
        adx_ok = current_adx >= self.config.adx_threshold

        should_enter = confirmations >= self.config.min_confirmation and adx_ok
        return should_enter, confirmations, meta

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate momentum signals from OHLCV data."""
        signals = []

        for symbol, df in data.items():
            if len(df) < max(self.config.formation_period, self.config.ema_slow + 10):
                continue

            # Regime filter: only trade in trending regime
            returns = df["close"].pct_change().dropna()
            if self.config.use_regime_filter:
                regime = self.regime_filter.classify(returns)
                if not self.regime_filter.should_trade(regime, "momentum"):
                    continue
            else:
                regime = Regime.TRENDING  # assume trending when filter disabled

            # Check RSI for trend confirmation (not overbought/oversold filter)
            # In momentum, high RSI confirms strength, not a reason to skip
            rsi = self.compute_rsi(df["close"], self.config.rsi_period)
            current_rsi = rsi.iloc[-1]
            if np.isnan(current_rsi):
                continue

            # Check conditions
            long_ok, long_conf, long_meta = self._check_long_conditions(df)
            short_ok, short_conf, short_meta = self._check_short_conditions(df)

            size_mult = self.regime_filter.position_size_multiplier(regime)
            current_price = float(df["close"].iloc[-1])
            timestamp = df.index[-1]

            # ATR for stop
            atr = self.compute_atr(df, self.config.atr_period)
            current_atr = atr.iloc[-1]
            if np.isnan(current_atr) or current_atr == 0:
                continue
            stop_distance = self.config.atr_trailing_mult * current_atr

            if long_ok and not short_ok:
                confidence = (long_conf / 3.0) * size_mult
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    direction=Direction.LONG,
                    price=current_price,
                    confidence=confidence,
                    stop_loss=current_price - stop_distance,
                    take_profit=current_price + 2 * stop_distance,
                    strategy_id=self.name,
                    metadata={**long_meta, "regime": regime.value, "atr": float(current_atr)},
                ))
            elif short_ok and not long_ok:
                confidence = (short_conf / 3.0) * size_mult
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    direction=Direction.SHORT,
                    price=current_price,
                    confidence=confidence,
                    stop_loss=current_price + stop_distance,
                    take_profit=current_price - 2 * stop_distance,
                    strategy_id=self.name,
                    metadata={**short_meta, "regime": regime.value, "atr": float(current_atr)},
                ))

        return signals

    def update_trailing_stop(self, symbol: str, current_price: float, current_atr: float) -> float:
        """Update and return the trailing stop for a position."""
        if symbol not in self.positions:
            return 0.0

        signal = self.positions[symbol]
        new_stop = current_price - self.config.atr_trailing_mult * current_atr

        if signal.is_long:
            # Only move stop up
            if symbol not in self._trailing_stops:
                self._trailing_stops[symbol] = signal.stop_loss or new_stop
            self._trailing_stops[symbol] = max(self._trailing_stops[symbol], new_stop)
            return self._trailing_stops[symbol]
        elif signal.is_short:
            new_stop = current_price + self.config.atr_trailing_mult * current_atr
            if symbol not in self._trailing_stops:
                self._trailing_stops[symbol] = signal.stop_loss or new_stop
            self._trailing_stops[symbol] = min(self._trailing_stops[symbol], new_stop)
            return self._trailing_stops[symbol]

        return 0.0
