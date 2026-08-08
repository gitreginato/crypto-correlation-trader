"""Real-time data collector for Binance Futures.

Captures multiple data streams via WebSocket and REST API:
- Order book depth (top 20 levels, 100ms updates)
- Aggregated trades (tick-by-tick aggressor data)
- Mark price + funding rate (1s updates)
- Liquidation events (force orders)
- Open interest (REST, polled every 30s)
- Long/Short ratio (REST, polled every 1m)

Data is stored as Parquet files partitioned by date for efficient analysis.

Architecture:
    LiveCollector
    ├── WebSocket streams (async, multiplexed)
    │   ├── depth20@100ms  -> order_book buffer
    │   ├── aggTrade       -> trades buffer
    │   ├── markPrice@1s   -> funding buffer
    │   └── !forceOrder    -> liquidations buffer
    ├── REST pollers (async, periodic)
    │   ├── openInterest (every 30s)
    │   └── longShortRatio (every 60s)
    └── Storage flusher (every 10s -> Parquet)
"""
import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
import pandas as pd
import websockets

from src.data.universe import Universe

logger = logging.getLogger(__name__)

# Binance endpoints
# Spot WebSocket for order book and trades (futures WS may be regionally blocked)
WS_SPOT_BASE = "wss://stream.binance.com:9443"
# Futures REST for open interest, long/short ratio, funding rate
REST_FUTURES_BASE = "https://fapi.binance.com"
# Spot REST for exchange info
REST_SPOT_BASE = "https://api.binance.com"


@dataclass
class CollectorConfig:
    """Configuration for the live collector."""
    symbols: list[str] = field(default_factory=lambda: Universe().get_default_universe()[:5])
    output_dir: str = "data/live"
    # Flush interval: write buffered data to Parquet every N seconds
    flush_interval: float = 10.0
    # REST polling intervals
    open_interest_interval: float = 30.0
    long_short_interval: float = 60.0
    # Order book depth levels to capture
    depth_levels: int = 20
    # Reconnect settings
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 100
    # Max buffer size before forced flush (prevent memory issues)
    max_buffer_size: int = 100_000


class LiveCollector:
    """Collects real-time data from Binance Futures via WebSocket and REST.

    Usage:
        collector = LiveCollector(config)
        await collector.start()  # runs until cancelled
    """

    def __init__(self, config: CollectorConfig):
        self.config = config
        self.symbols = [s.lower() for s in config.symbols]

        # Buffers: list of dicts, each dict = one row
        self._buffers: dict[str, list[dict]] = {
            "order_book": [],
            "trades": [],
            "funding": [],
            "liquidations": [],
            "open_interest": [],
            "long_short": [],
            "fear_greed": [],
        }
        self._buffer_lock = asyncio.Lock()

        # Stats
        self._stats: defaultdict[str, int] = defaultdict(int)
        self._running = False
        self._ws_session: Optional[websockets.WebSocketClientProtocol] = None  # type: ignore

        # Ensure output dir exists
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    async def start(self):
        """Start all collectors and storage flusher. Runs until cancelled."""
        self._running = True
        logger.info(f"Starting live collector for {len(self.symbols)} symbols: {self.symbols}")

        tasks = [
            self._run_websocket(),
            self._run_rest_poller("open_interest", self._poll_open_interest,
                                  self.config.open_interest_interval),
            self._run_rest_poller("long_short", self._poll_long_short,
                                  self.config.long_short_interval),
            self._run_rest_poller("funding_rate", self._poll_funding_rate,
                                  self.config.long_short_interval),
            self._run_rest_poller("liquidations", self._poll_liquidations,
                                  self.config.open_interest_interval),
            self._run_rest_poller("fear_greed", self._poll_fear_greed,
                                  600),  # 10 min
            self._run_flusher(),
            self._run_stats_printer(),
        ]

        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop the collector and flush remaining data."""
        self._running = False
        if self._ws_session:
            await self._ws_session.close()
        await self._flush_all()
        logger.info("Collector stopped. Final stats:")
        self._print_stats()

    def _print_stats(self):
        for key, count in sorted(self._stats.items()):
            logger.info(f"  {key}: {count:,} messages")

    # ─── WebSocket ───────────────────────────────────────────────

    async def _run_websocket(self):
        """Connect to Binance Spot WebSocket and handle messages.

        Uses spot endpoint because futures WebSocket may be regionally blocked.
        Funding rate and liquidations are polled via REST instead.
        """
        stream_names = []

        for sym in self.symbols:
            stream_names.append(f"{sym}@depth{self.config.depth_levels}@100ms")
            stream_names.append(f"{sym}@aggTrade")

        # Build combined stream URL (spot endpoint)
        url = f"{WS_SPOT_BASE}/stream?streams=" + "/".join(stream_names)

        attempt = 0
        while self._running:
            try:
                logger.info(f"Connecting to WebSocket ({len(stream_names)} streams)...")
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    max_size=2**24,  # 16MB max message
                ) as ws:
                    self._ws_session = ws
                    attempt = 0
                    logger.info("WebSocket connected!")

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        await self._handle_ws_message(raw_msg)

            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket closed: {e}. Reconnecting in {self.config.reconnect_delay}s...")
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Reconnecting in {self.config.reconnect_delay}s...")

            attempt += 1
            if attempt > self.config.max_reconnect_attempts:
                logger.error(f"Max reconnection attempts ({self.config.max_reconnect_attempts}) reached. Stopping.")
                break

            await asyncio.sleep(self.config.reconnect_delay)

    async def _handle_ws_message(self, raw_msg: str):
        """Parse and route a WebSocket message to the appropriate buffer."""
        try:
            msg = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        # Combined stream format: {"stream": "btcusdt@aggTrade", "data": {...}}
        stream = msg.get("stream", "")
        data = msg.get("data", msg)

        if not stream:
            return

        self._stats["total_messages"] += 1

        # Route by stream type
        if "@depth" in stream:
            await self._handle_depth(data, stream)
        elif "@aggTrade" in stream:
            await self._handle_agg_trade(data, stream)

    async def _handle_depth(self, data: dict, stream: str):
        """Handle order book depth update."""
        # depth20 stream: {lastUpdateId, bids: [[price, qty]...], asks: [[price, qty]...]}
        symbol = data.get("s", stream.split("@")[0].upper())
        ts = datetime.now(timezone.utc)

        row = {
            "timestamp": ts,
            "symbol": symbol,
            "last_update_id": data.get("lastUpdateId", data.get("u", 0)),
        }

        # Store top 5 levels (compact enough for analysis)
        bids = data.get("bids", data.get("b", []))
        asks = data.get("asks", data.get("a", []))

        for i in range(min(5, len(bids))):
            row[f"bid_{i}_price"] = float(bids[i][0])
            row[f"bid_{i}_qty"] = float(bids[i][1])

        for i in range(min(5, len(asks))):
            row[f"ask_{i}_price"] = float(asks[i][0])
            row[f"ask_{i}_qty"] = float(asks[i][1])

        # Compute spread and imbalance
        if bids and asks:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            row["spread"] = best_ask - best_bid
            row["spread_pct"] = (best_ask - best_bid) / best_bid if best_bid > 0 else 0
            row["mid_price"] = (best_bid + best_ask) / 2

            # Order book imbalance: (bid_qty - ask_qty) / (bid_qty + ask_qty)
            bid_qty_5 = sum(float(b[1]) for b in bids[:5])
            ask_qty_5 = sum(float(a[1]) for a in asks[:5])
            total = bid_qty_5 + ask_qty_5
            row["imbalance_5"] = (bid_qty_5 - ask_qty_5) / total if total > 0 else 0
            row["bid_qty_5"] = bid_qty_5
            row["ask_qty_5"] = ask_qty_5

        await self._add_to_buffer("order_book", row)
        self._stats["order_book_msgs"] += 1

    async def _handle_agg_trade(self, data: dict, stream: str):
        """Handle aggregated trade (tick)."""
        # aggTrade: {e, E, s, a, p, q, f, l, T, m}
        # m = true means buyer is market maker (SELLER aggressed)
        # m = false means buyer is aggressor (BUYER aggressed)
        row = {
            "timestamp": datetime.fromtimestamp(data.get("T", 0) / 1000, tz=timezone.utc),
            "symbol": data.get("s", stream.split("@")[0].upper()),
            "agg_id": data.get("a", 0),
            "price": float(data.get("p", 0)),
            "quantity": float(data.get("q", 0)),
            "is_buyer_maker": data.get("m", False),  # True = sell aggression, False = buy aggression
            "trade_time_ms": data.get("T", 0),
        }

        await self._add_to_buffer("trades", row)
        self._stats["trade_msgs"] += 1

    async def _handle_mark_price(self, data: dict, stream: str):
        """Handle mark price + funding rate update."""
        # markPrice: {e, E, s, p, i, P, r, T}
        row = {
            "timestamp": datetime.fromtimestamp(data.get("E", 0) / 1000, tz=timezone.utc),
            "symbol": data.get("s", stream.split("@")[0].upper()),
            "mark_price": float(data.get("p", 0)),
            "index_price": float(data.get("i", 0)),
            "funding_rate": float(data.get("r", 0)),
            "next_funding_time": datetime.fromtimestamp(
                data.get("T", 0) / 1000, tz=timezone.utc
            ) if data.get("T") else None,
        }

        await self._add_to_buffer("funding", row)
        self._stats["funding_msgs"] += 1

    async def _handle_liquidation(self, data: dict, stream: str):
        """Handle liquidation event."""
        # forceOrder: {e: "forceOrder", E, o: {s, S, o, f, q, p, ap, T, ...}}
        order = data.get("o", data)
        row = {
            "timestamp": datetime.fromtimestamp(order.get("T", 0) / 1000, tz=timezone.utc),
            "symbol": order.get("s", ""),
            "side": order.get("S", ""),  # BUY or SELL
            "position_side": order.get("ps", ""),
            "order_type": order.get("o", ""),
            "time_in_force": order.get("f", ""),
            "quantity": float(order.get("q", 0)),
            "price": float(order.get("p", 0)),
            "avg_price": float(order.get("ap", 0)),
            "trade_time_ms": order.get("T", 0),
        }

        await self._add_to_buffer("liquidations", row)
        self._stats["liquidation_msgs"] += 1
        logger.info(
            f"LIQUIDATION: {row['symbol']} {row['side']} "
            f"qty={row['quantity']} @ {row['avg_price']}"
        )

    # ─── REST Pollers ────────────────────────────────────────────

    async def _run_rest_poller(self, name: str, poll_func, interval: float):
        """Run a REST API poller at a fixed interval."""
        while self._running:
            try:
                await poll_func()
            except Exception as e:
                logger.error(f"REST poller {name} error: {e}")
            await asyncio.sleep(interval)

    async def _poll_open_interest(self):
        """Poll open interest for all symbols."""
        async with aiohttp.ClientSession() as session:
            for symbol in self.config.symbols:
                sym_upper = symbol.upper()
                url = f"{REST_FUTURES_BASE}/fapi/v1/openInterest?symbol={sym_upper}"
                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            row = {
                                "timestamp": datetime.now(timezone.utc),
                                "symbol": sym_upper,
                                "open_interest": float(data.get("openInterest", 0)),
                            }
                            await self._add_to_buffer("open_interest", row)
                            self._stats["open_interest_msgs"] += 1
                except Exception as e:
                    logger.debug(f"OI poll error for {sym_upper}: {e}")

    async def _poll_long_short(self):
        """Poll long/short ratio (global account ratio) for all symbols."""
        async with aiohttp.ClientSession() as session:
            for symbol in self.config.symbols:
                sym_upper = symbol.upper()
                # Global account long/short ratio
                url = f"{REST_FUTURES_BASE}/futures/data/globalLongShortAccountRatio?symbol={sym_upper}&period=5m"
                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data:
                                latest = data[-1]
                                row = {
                                    "timestamp": datetime.fromtimestamp(
                                        latest.get("timestamp", 0) / 1000, tz=timezone.utc
                                    ),
                                    "symbol": sym_upper,
                                    "long_short_ratio": float(latest.get("longShortRatio", 0)),
                                    "long_account_pct": float(latest.get("longAccount", 0)),
                                    "short_account_pct": float(latest.get("shortAccount", 0)),
                                }
                                await self._add_to_buffer("long_short", row)
                                self._stats["long_short_msgs"] += 1
                except Exception as e:
                    logger.debug(f"L/S poll error for {sym_upper}: {e}")

    async def _poll_funding_rate(self):
        """Poll funding rate and mark price via futures REST API."""
        async with aiohttp.ClientSession() as session:
            for symbol in self.config.symbols:
                sym_upper = symbol.upper()
                url = f"{REST_FUTURES_BASE}/fapi/v1/premiumIndex?symbol={sym_upper}"
                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            row = {
                                "timestamp": datetime.now(timezone.utc),
                                "symbol": sym_upper,
                                "mark_price": float(data.get("markPrice", 0)),
                                "index_price": float(data.get("indexPrice", 0)),
                                "funding_rate": float(data.get("lastFundingRate", 0)),
                                "next_funding_time": datetime.fromtimestamp(
                                    data.get("nextFundingTime", 0) / 1000, tz=timezone.utc
                                ) if data.get("nextFundingTime") else None,
                            }
                            await self._add_to_buffer("funding", row)
                            self._stats["funding_msgs"] += 1
                except Exception as e:
                    logger.debug(f"Funding poll error for {sym_upper}: {e}")

    async def _poll_liquidations(self):
        """Poll liquidation summary via Xoomar free API (no key required).

        Binance futures REST requires API key for forceOrders (401),
        and the futures WebSocket is geo-blocked. Xoomar aggregates
        liquidation data from Binance, OKX, Gate.io, and HTX.
        """
        async with aiohttp.ClientSession() as session:
            url = "https://xoomar.com/api/markets/liquidations"
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        d = data.get("data", {})
                        row = {
                            "timestamp": datetime.now(timezone.utc),
                            "total_usd": float(d.get("totalUsd", 0)),
                            "long_usd": float(d.get("longUsd", 0)),
                            "short_usd": float(d.get("shortUsd", 0)),
                            "max_single_usd": float(d.get("maxSingleUsd", 0)),
                        }
                        await self._add_to_buffer("liquidations", row)
                        self._stats["liquidation_msgs"] += 1
            except Exception as e:
                logger.debug(f"Liquidation poll error: {e}")

    async def _poll_fear_greed(self):
        """Poll Fear & Greed Index from alternative.me (free, no key)."""
        async with aiohttp.ClientSession() as session:
            url = "https://api.alternative.me/fng/?limit=30"
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        entries = data.get("data", [])
                        for entry in entries:
                            row = {
                                "timestamp": datetime.fromtimestamp(
                                    int(entry.get("timestamp", 0)), tz=timezone.utc
                                ),
                                "value": int(entry.get("value", 0)),
                                "classification": entry.get("value_classification", ""),
                            }
                            await self._add_to_buffer("fear_greed", row)
                            self._stats["fear_greed_msgs"] += 1
            except Exception as e:
                logger.debug(f"Fear/Greed poll error: {e}")

    # ─── Buffer & Storage ────────────────────────────────────────

    async def _add_to_buffer(self, buffer_name: str, row: dict):
        """Add a row to a buffer. Flush if buffer is too large."""
        async with self._buffer_lock:
            self._buffers[buffer_name].append(row)
            if len(self._buffers[buffer_name]) >= self.config.max_buffer_size:
                # Force flush this buffer
                buf = self._buffers[buffer_name]
                self._buffers[buffer_name] = []
        # If we extracted a buffer, flush it outside the lock
        if "buf" in locals() and buf:
            await self._flush_buffer(buffer_name, buf)

    async def _run_flusher(self):
        """Periodically flush all buffers to Parquet."""
        while self._running:
            await asyncio.sleep(self.config.flush_interval)
            await self._flush_all()

    async def _flush_all(self):
        """Flush all non-empty buffers to Parquet."""
        async with self._buffer_lock:
            buffers_to_flush = {}
            for name, buf in self._buffers.items():
                if buf:
                    buffers_to_flush[name] = buf
                    self._buffers[name] = []

        for name, buf in buffers_to_flush.items():
            await self._flush_buffer(name, buf)

    async def _flush_buffer(self, name: str, rows: list[dict]):
        """Write a buffer to Parquet, partitioned by date."""
        if not rows:
            return

        try:
            df = pd.DataFrame(rows)
            # Ensure timestamp column is datetime
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Partition by date
            df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

            output_path = Path(self.config.output_dir) / name
            output_path.mkdir(parents=True, exist_ok=True)

            # Write as Parquet (append mode: one file per flush)
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            time_str = datetime.now(timezone.utc).strftime("%H%M%S")
            filename = f"{date_str}_{time_str}.parquet"
            filepath = output_path / filename

            df.to_parquet(filepath, index=False)
            self._stats[f"{name}_flushed"] += len(rows)
            logger.debug(f"Flushed {len(rows)} rows to {filepath}")

        except Exception as e:
            logger.error(f"Error flushing {name}: {e}")
            # Put rows back in buffer
            async with self._buffer_lock:
                self._buffers[name] = rows + self._buffers[name]

    # ─── Stats ───────────────────────────────────────────────────

    async def _run_stats_printer(self):
        """Print stats every 60 seconds."""
        while self._running:
            await asyncio.sleep(60)
            self._print_stats()
