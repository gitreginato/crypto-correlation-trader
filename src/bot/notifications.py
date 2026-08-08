"""NotificationManager: Telegram notification stub for Phase 4.

This module is a stub. It does NOT make real HTTP calls to the Telegram
Bot API. Messages are logged via the stdlib logging module and stored in
an internal history list so tests and dashboards can inspect what would
have been sent.

The real Telegram transport will be implemented in Phase 5 (live trading).

Security:
- The bot token and chat id are NEVER logged.
- Only the notification level and message body are recorded.
- Secrets must come from environment variables via NotificationConfig,
  never hardcoded.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """Severity levels for notifications, ordered low to high."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Numeric weight for level comparison. Higher = more severe.
_LEVEL_WEIGHT: dict[NotificationLevel, int] = {
    NotificationLevel.DEBUG: 10,
    NotificationLevel.INFO: 20,
    NotificationLevel.WARNING: 30,
    NotificationLevel.ERROR: 40,
    NotificationLevel.CRITICAL: 50,
}


@dataclass
class NotificationConfig:
    """Configuration for the notification subsystem.

    Attributes:
        enabled: Master switch. When False, send() always returns False.
        telegram_bot_token: Telegram bot token. Comes from env var, never hardcoded.
        telegram_chat_id: Target Telegram chat id. Comes from env var.
        min_level: Minimum level required for a message to be delivered.
    """

    enabled: bool = True
    telegram_bot_token: str = ""  # never hardcoded, comes from env var
    telegram_chat_id: str = ""
    min_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL


@dataclass
class NotificationEntry:
    """A single recorded notification (internal history record)."""

    timestamp: str
    level: str
    message: str

    def to_dict(self) -> dict:
        """Serialize to a plain dict for get_history()."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
        }


class NotificationManager:
    """Stub notification manager that logs messages and keeps an in-memory history.

    No real Telegram delivery happens here. This is intentional for Phase 4.
    """

    def __init__(self, config: NotificationConfig) -> None:
        self._config = config
        self._min_level = self._parse_level(config.min_level)
        self._history: list[NotificationEntry] = []

    @staticmethod
    def _parse_level(level: str) -> NotificationLevel:
        """Parse a level string into a NotificationLevel, defaulting to INFO."""
        try:
            return NotificationLevel(level.upper())
        except ValueError:
            logger.warning("Invalid min_level '%s', falling back to INFO", level)
            return NotificationLevel.INFO

    def _passes_filter(self, level: NotificationLevel) -> bool:
        """Return True if the level is at or above the configured minimum."""
        return _LEVEL_WEIGHT[level] >= _LEVEL_WEIGHT[self._min_level]

    def send(self, level: NotificationLevel, message: str) -> bool:
        """Log and record a notification if it passes filters.

        Returns True when the message was recorded, False when it was
        discarded (disabled, filtered by level, or empty body).
        """
        if not self._config.enabled:
            return False
        if not message or not message.strip():
            return False
        if not self._passes_filter(level):
            return False

        entry = NotificationEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            message=message,
        )
        self._history.append(entry)
        # Only log level + body. Never log token or chat id.
        logger.info("[notify] %s: %s", level.value, message)
        return True

    def send_order_fill(
        self, symbol: str, side: str, size: float, price: float
    ) -> bool:
        """Notify about a filled order."""
        message = (
            f"Order filled: {side} {size} {symbol} @ {price}"
        )
        return self.send(NotificationLevel.INFO, message)

    def send_stop_loss_hit(self, symbol: str, price: float) -> bool:
        """Notify that a stop loss was triggered for a position."""
        message = f"Stop loss hit: {symbol} @ {price}"
        return self.send(NotificationLevel.WARNING, message)

    def send_kill_switch_triggered(self, drawdown: float) -> bool:
        """Notify that the kill switch fired due to max drawdown."""
        message = f"KILL SWITCH triggered: drawdown {drawdown:.2%}"
        return self.send(NotificationLevel.CRITICAL, message)

    def send_daily_summary(self, pnl: float, positions: int) -> bool:
        """Notify the daily PnL summary and open position count."""
        message = f"Daily summary: PnL {pnl} | open positions {positions}"
        return self.send(NotificationLevel.INFO, message)

    def get_history(self) -> list[dict]:
        """Return a copy of the recorded notifications as plain dicts."""
        return [entry.to_dict() for entry in self._history]

    def clear_history(self) -> None:
        """Remove all recorded notifications."""
        self._history.clear()
