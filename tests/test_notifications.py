"""Tests for src/bot/notifications.py.

TDD: tests written before implementation. Covers NotificationConfig defaults,
NotificationLevel enum, level filtering, disabled state, formatted helpers,
history management, and edge cases (empty message).

The Telegram transport is a stub in Phase 4: no real HTTP calls are made.
Messages are logged and stored in an internal history list for inspection.
"""
import pytest

from src.bot.notifications import (
    NotificationConfig,
    NotificationLevel,
    NotificationManager,
)


@pytest.fixture
def config() -> NotificationConfig:
    """Default enabled config with INFO as minimum level."""
    return NotificationConfig(
        enabled=True,
        telegram_bot_token="",  # never hardcoded, comes from env var
        telegram_chat_id="",
        min_level="INFO",
    )


@pytest.fixture
def manager(config: NotificationConfig) -> NotificationManager:
    """NotificationManager backed by the default config."""
    return NotificationManager(config=config)


# --- NotificationConfig -------------------------------------------------


class TestNotificationConfig:
    def test_defaults_are_valid(self) -> None:
        cfg = NotificationConfig()
        assert cfg.enabled is True
        assert cfg.telegram_bot_token == ""
        assert cfg.telegram_chat_id == ""
        assert cfg.min_level == "INFO"

    def test_disabled_flag(self) -> None:
        cfg = NotificationConfig(enabled=False)
        assert cfg.enabled is False


# --- NotificationLevel --------------------------------------------------


class TestNotificationLevel:
    def test_enum_has_all_levels(self) -> None:
        assert NotificationLevel.DEBUG.value == "DEBUG"
        assert NotificationLevel.INFO.value == "INFO"
        assert NotificationLevel.WARNING.value == "WARNING"
        assert NotificationLevel.ERROR.value == "ERROR"
        assert NotificationLevel.CRITICAL.value == "CRITICAL"

    def test_enum_is_str(self) -> None:
        assert isinstance(NotificationLevel.INFO, str)


# --- NotificationManager.send ------------------------------------------


class TestSend:
    def test_message_registered_in_history(self, manager: NotificationManager) -> None:
        ok = manager.send(NotificationLevel.INFO, "hello world")
        assert ok is True
        history = manager.get_history()
        assert len(history) == 1
        assert history[0]["level"] == "INFO"
        assert history[0]["message"] == "hello world"

    def test_respects_min_level_debug_below_info_discarded(
        self, manager: NotificationManager
    ) -> None:
        # min_level is INFO, so DEBUG must be discarded
        ok = manager.send(NotificationLevel.DEBUG, "debug noise")
        assert ok is False
        assert manager.get_history() == []

    def test_returns_false_when_disabled(self) -> None:
        cfg = NotificationConfig(enabled=False)
        mgr = NotificationManager(config=cfg)
        ok = mgr.send(NotificationLevel.ERROR, "should not send")
        assert ok is False
        assert mgr.get_history() == []

    def test_empty_message_not_sent(self, manager: NotificationManager) -> None:
        ok = manager.send(NotificationLevel.INFO, "")
        assert ok is False
        assert manager.get_history() == []

    def test_whitespace_only_message_not_sent(self, manager: NotificationManager) -> None:
        ok = manager.send(NotificationLevel.INFO, "   ")
        assert ok is False
        assert manager.get_history() == []


# --- Formatted helpers --------------------------------------------------


class TestOrderFill:
    def test_format_contains_fields(self, manager: NotificationManager) -> None:
        ok = manager.send_order_fill(
            symbol="BTCUSDT", side="BUY", size=0.5, price=42000.0
        )
        assert ok is True
        entry = manager.get_history()[0]
        text = entry["message"]
        assert "BTCUSDT" in text
        assert "BUY" in text
        assert "0.5" in text
        assert "42000" in text
        assert entry["level"] == "INFO"


class TestStopLossHit:
    def test_format_contains_fields(self, manager: NotificationManager) -> None:
        ok = manager.send_stop_loss_hit(symbol="ETHUSDT", price=2500.0)
        assert ok is True
        entry = manager.get_history()[0]
        text = entry["message"]
        assert "ETHUSDT" in text
        assert "2500" in text
        assert entry["level"] == "WARNING"


class TestKillSwitchTriggered:
    def test_format_contains_drawdown(self, manager: NotificationManager) -> None:
        ok = manager.send_kill_switch_triggered(drawdown=0.12)
        assert ok is True
        entry = manager.get_history()[0]
        text = entry["message"]
        assert "0.12" in text or "12" in text
        assert entry["level"] == "CRITICAL"


class TestDailySummary:
    def test_format_contains_pnl_and_positions(self, manager: NotificationManager) -> None:
        ok = manager.send_daily_summary(pnl=150.75, positions=3)
        assert ok is True
        entry = manager.get_history()[0]
        text = entry["message"]
        assert "150.75" in text
        assert "3" in text
        assert entry["level"] == "INFO"


# --- History management -------------------------------------------------


class TestHistory:
    def test_get_history_returns_all_sent(self, manager: NotificationManager) -> None:
        manager.send(NotificationLevel.INFO, "first")
        manager.send(NotificationLevel.WARNING, "second")
        history = manager.get_history()
        assert len(history) == 2
        assert history[0]["message"] == "first"
        assert history[1]["message"] == "second"

    def test_clear_history_empties_list(self, manager: NotificationManager) -> None:
        manager.send(NotificationLevel.INFO, "one")
        manager.send(NotificationLevel.ERROR, "two")
        assert len(manager.get_history()) == 2
        manager.clear_history()
        assert manager.get_history() == []

    def test_history_entries_have_timestamp(self, manager: NotificationManager) -> None:
        manager.send(NotificationLevel.INFO, "with timestamp")
        entry = manager.get_history()[0]
        assert "timestamp" in entry
        assert entry["timestamp"] is not None
