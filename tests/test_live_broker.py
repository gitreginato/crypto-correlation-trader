"""Tests for src/bot/live_broker.py.

TDD: tests written before implementation. Covers the stub for Fase 5
(live trading). All operations are safe by default: enabled=False,
dry_run=True, testnet=True. No real exchange calls are made.
"""
import logging

import pytest

from src.bot.live_broker import LiveBroker, LiveBrokerConfig
from src.bot.paper_broker import Fill


@pytest.fixture
def config() -> LiveBrokerConfig:
    return LiveBrokerConfig()


@pytest.fixture
def broker(config: LiveBrokerConfig) -> LiveBroker:
    return LiveBroker(config=config)


@pytest.fixture
def enabled_dry_run_config() -> LiveBrokerConfig:
    return LiveBrokerConfig(
        enabled=True,
        dry_run=True,
        api_key="test_key",
        api_secret="test_secret",
        testnet=True,
    )


@pytest.fixture
def enabled_dry_run_broker(enabled_dry_run_config: LiveBrokerConfig) -> LiveBroker:
    return LiveBroker(config=enabled_dry_run_config)


class TestLiveBrokerConfig:
    """Config defaults must be safe by design."""

    def test_defaults_are_safe(self, config: LiveBrokerConfig) -> None:
        assert config.enabled is False
        assert config.dry_run is True
        assert config.testnet is True

    def test_api_credentials_empty_by_default(self, config: LiveBrokerConfig) -> None:
        assert config.api_key == ""
        assert config.api_secret == ""


class TestLiveBrokerConnection:
    """Connection state and credential validation."""

    def test_init_does_not_connect(self, broker: LiveBroker) -> None:
        assert broker.is_connected() is False

    def test_validate_credentials_false_when_api_key_empty(
        self, broker: LiveBroker
    ) -> None:
        assert broker.validate_credentials() is False

    def test_validate_credentials_false_when_disabled(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        # Even with credentials, disabled broker cannot validate.
        cfg = enabled_dry_run_broker.config
        assert cfg.api_key != ""
        # Force disabled but keep credentials.
        disabled_cfg = LiveBrokerConfig(
            enabled=False,
            dry_run=True,
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
        )
        disabled_broker = LiveBroker(config=disabled_cfg)
        assert disabled_broker.validate_credentials() is False

    def test_is_connected_false_by_default(self, broker: LiveBroker) -> None:
        assert broker.is_connected() is False


class TestPlaceMarketOrder:
    """Market order placement in dry_run and disabled modes."""

    def test_dry_run_returns_fill_no_real_order(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        fill = enabled_dry_run_broker.place_market_order(
            symbol="BTCUSDT", side="BUY", size=0.1
        )
        assert fill is not None
        assert isinstance(fill, Fill)
        assert fill.symbol == "BTCUSDT"
        assert fill.side == "BUY"
        assert fill.fill_size == 0.1

    def test_returns_none_when_disabled(self, broker: LiveBroker) -> None:
        fill = broker.place_market_order(
            symbol="BTCUSDT", side="BUY", size=0.1
        )
        assert fill is None

    def test_returns_none_when_size_le_zero(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        assert enabled_dry_run_broker.place_market_order(
            symbol="BTCUSDT", side="BUY", size=0.0
        ) is None
        assert enabled_dry_run_broker.place_market_order(
            symbol="BTCUSDT", side="BUY", size=-1.0
        ) is None

    def test_returns_none_when_symbol_empty(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        fill = enabled_dry_run_broker.place_market_order(
            symbol="", side="BUY", size=0.1
        )
        assert fill is None


class TestPlaceLimitOrder:
    """Limit order placement in dry_run and disabled modes."""

    def test_dry_run_returns_fill(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        fill = enabled_dry_run_broker.place_limit_order(
            symbol="ETHUSDT", side="SELL", size=0.5, price=3000.0
        )
        assert fill is not None
        assert isinstance(fill, Fill)
        assert fill.symbol == "ETHUSDT"
        assert fill.side == "SELL"
        assert fill.fill_size == 0.5
        assert fill.fill_price == 3000.0

    def test_returns_none_when_disabled(self, broker: LiveBroker) -> None:
        fill = broker.place_limit_order(
            symbol="ETHUSDT", side="SELL", size=0.5, price=3000.0
        )
        assert fill is None


class TestCancelOrder:
    """Order cancellation in dry_run and disabled modes."""

    def test_dry_run_returns_true(self, enabled_dry_run_broker: LiveBroker) -> None:
        assert enabled_dry_run_broker.cancel_order(order_id="fake_123") is True

    def test_returns_false_when_disabled(self, broker: LiveBroker) -> None:
        assert broker.cancel_order(order_id="fake_123") is False


class TestGetBalance:
    """Balance retrieval in dry_run and disabled modes."""

    def test_returns_empty_dict_when_disabled(self, broker: LiveBroker) -> None:
        assert broker.get_balance() == {}

    def test_returns_dry_run_balance_when_dry_run(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        balance = enabled_dry_run_broker.get_balance()
        assert isinstance(balance, dict)
        assert len(balance) > 0


class TestGetOpenOrders:
    """Open orders retrieval in dry_run mode."""

    def test_returns_empty_list_when_dry_run(
        self, enabled_dry_run_broker: LiveBroker
    ) -> None:
        orders = enabled_dry_run_broker.get_open_orders()
        assert isinstance(orders, list)
        assert orders == []


class TestNoSecretLogging:
    """API keys and secrets must NEVER appear in logs."""

    def test_never_logs_api_key_or_secret(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        secret_key = "SUPER_SECRET_KEY_12345"
        secret_val = "SUPER_SECRET_VAL_67890"
        cfg = LiveBrokerConfig(
            enabled=True,
            dry_run=True,
            api_key=secret_key,
            api_secret=secret_val,
            testnet=True,
        )
        broker = LiveBroker(config=cfg)

        with caplog.at_level(logging.DEBUG, logger="src.bot.live_broker"):
            broker.validate_credentials()
            broker.place_market_order(symbol="BTCUSDT", side="BUY", size=0.1)
            broker.place_limit_order(
                symbol="ETHUSDT", side="SELL", size=0.5, price=3000.0
            )
            broker.cancel_order(order_id="fake_123")
            broker.get_balance()
            broker.get_open_orders()
            broker.is_connected()

        full_log = caplog.text
        assert secret_key not in full_log
        assert secret_val not in full_log
