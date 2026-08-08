"""LiveBroker: stub for Fase 5 (live trading).

This module implements the broker interface for live order execution but
is SAFE BY DEFAULT. It never sends real orders unless explicitly enabled
AND dry_run is False. In dry_run mode it only logs operations and returns
simulated Fill objects.

Security rules (from AGENTS.md):
- NUNCA hardcodear API keys, secrets, ou tokens. Use config + env vars.
- NUNCA logar api_key, api_secret, ou tokens. Mask with "***" if needed.
- SEMPRE comecar desativado (enabled=False) e em testnet (testnet=True).

This is a STUB. No ccxt, no requests, no real exchange calls. Real
implementation will be added in Fase 5 after paper trading validation.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.bot.paper_broker import Fill

logger = logging.getLogger(__name__)

_MASK = "***"


@dataclass
class LiveBrokerConfig:
    """Configuration for the live broker.

    Attributes:
        enabled: Master switch. False = all trading ops return None/False/{}.
        dry_run: If True, log operations but never send real orders.
        exchange: Exchange identifier (e.g. "binance"). For future use.
        api_key: API key from env var. NEVER hardcode. Empty by default.
        api_secret: API secret from env var. NEVER hardcode. Empty by default.
        testnet: If True, target exchange testnet. True by default for safety.
        timeout_seconds: Timeout for exchange API calls.
        max_retries: Max retries for transient errors (exponential backoff).
    """
    enabled: bool = False
    dry_run: bool = True
    exchange: str = "binance"
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = True
    timeout_seconds: float = 30.0
    max_retries: int = 3


class LiveBroker:
    """Stub broker for live trading (Fase 5).

    Safe by default: enabled=False, dry_run=True, testnet=True.
    In dry_run mode, operations are logged and return simulated results.
    No real exchange calls are made in this stub.

    Usage:
        config = LiveBrokerConfig()  # safe defaults
        broker = LiveBroker(config=config)
        if broker.validate_credentials():
            fill = broker.place_market_order("BTCUSDT", "BUY", 0.1)
    """

    def __init__(self, config: LiveBrokerConfig) -> None:
        self.config = config
        self._connected: bool = False
        self._dry_run_balance: dict[str, float] = {"USDT": 10_000.0}
        logger.info(
            "LiveBroker initialized: enabled=%s dry_run=%s exchange=%s testnet=%s",
            self.config.enabled,
            self.config.dry_run,
            self.config.exchange,
            self.config.testnet,
        )

    def is_connected(self) -> bool:
        """Return True if broker is connected to the exchange.

        This stub never connects for real. Returns True only if enabled,
        dry_run is False, and credentials are present (future: real
        connection handshake).
        """
        if not self.config.enabled:
            return False
        if not self._has_credentials():
            return False
        # In a real implementation, this would check the websocket/rest
        # connection state. For the stub, we only report connected when
        # enabled, non-dry-run, and with credentials.
        return self._connected

    def validate_credentials(self) -> bool:
        """Validate exchange API credentials.

        Returns False if disabled or if api_key/api_secret are empty.
        In dry_run mode, returns True if credentials are present (no real
        validation is performed).
        """
        if not self.config.enabled:
            logger.warning("validate_credentials called but broker is disabled")
            return False
        if not self._has_credentials():
            logger.warning("validate_credentials: api_key or api_secret is empty")
            return False
        logger.info(
            "validate_credentials: dry_run=%s testnet=%s, credentials present",
            self.config.dry_run,
            self.config.testnet,
        )
        if self.config.dry_run:
            self._connected = True
            return True
        # Real validation (Fase 5): would call exchange.fetch_balance()
        # or similar. Not implemented in this stub.
        logger.warning("Real credential validation not implemented in stub")
        return False

    def place_market_order(
        self, symbol: str, side: str, size: float
    ) -> Optional[Fill]:
        """Place a market order.

        In dry_run mode: returns a simulated Fill with fill_price = 0.0
        (no real price feed available in stub) and logs the operation.
        When disabled or invalid input: returns None.
        """
        if not self._is_trading_enabled():
            return None
        if not self._valid_order_input(symbol, side, size):
            return None
        logger.info(
            "place_market_order [DRY_RUN]: symbol=%s side=%s size=%s",
            symbol,
            side,
            size,
        )
        return self._simulate_fill(symbol, side, size, fill_price=0.0)

    def place_limit_order(
        self, symbol: str, side: str, size: float, price: float
    ) -> Optional[Fill]:
        """Place a limit order.

        In dry_run mode: returns a simulated Fill with fill_price = price
        and logs the operation. When disabled or invalid input: returns None.
        """
        if not self._is_trading_enabled():
            return None
        if not self._valid_order_input(symbol, side, size):
            return None
        if price <= 0:
            logger.warning("place_limit_order: price must be > 0, got %s", price)
            return None
        logger.info(
            "place_limit_order [DRY_RUN]: symbol=%s side=%s size=%s price=%s",
            symbol,
            side,
            size,
            price,
        )
        return self._simulate_fill(symbol, side, size, fill_price=price)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.

        In dry_run mode: returns True (simulates success) and logs.
        When disabled: returns False.
        """
        if not self._is_trading_enabled():
            return False
        logger.info("cancel_order [DRY_RUN]: order_id=%s", order_id)
        return True

    def get_balance(self) -> dict:
        """Return account balance.

        In dry_run mode: returns a simulated balance dict.
        When disabled: returns empty dict.
        """
        if not self.config.enabled:
            return {}
        if self.config.dry_run:
            logger.info("get_balance [DRY_RUN]: returning simulated balance")
            return dict(self._dry_run_balance)
        # Real balance fetch (Fase 5): not implemented in stub.
        logger.warning("Real balance fetch not implemented in stub")
        return {}

    def get_open_orders(self) -> list:
        """Return list of open orders.

        In dry_run mode: returns empty list (no real orders are placed).
        When disabled: returns empty list.
        """
        if not self.config.enabled:
            return []
        logger.info("get_open_orders [DRY_RUN]: returning empty list")
        return []

    def _has_credentials(self) -> bool:
        """Check if api_key and api_secret are non-empty."""
        return bool(self.config.api_key) and bool(self.config.api_secret)

    def _is_trading_enabled(self) -> bool:
        """Check if trading operations are allowed.

        Trading is allowed only when enabled=True. dry_run controls whether
        real orders are sent (always simulated in this stub).
        """
        if not self.config.enabled:
            logger.warning("Trading operation rejected: broker is disabled")
            return False
        return True

    def _valid_order_input(self, symbol: str, side: str, size: float) -> bool:
        """Validate common order input parameters."""
        if not symbol or not symbol.strip():
            logger.warning("Order rejected: symbol is empty")
            return False
        if side not in ("BUY", "SELL"):
            logger.warning("Order rejected: invalid side=%s", side)
            return False
        if size <= 0:
            logger.warning("Order rejected: size must be > 0, got %s", size)
            return False
        return True

    def _simulate_fill(
        self, symbol: str, side: str, size: float, fill_price: float
    ) -> Fill:
        """Create a simulated Fill for dry_run mode."""
        return Fill(
            symbol=symbol,
            side=side,
            fill_size=size,
            fill_price=fill_price,
            fee=0.0,
            timestamp=datetime.now(timezone.utc),
        )
