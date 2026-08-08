# Plan 008: Write tests for live_collector (unit + error paths)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report: do not improvise. When done, update the status row for this plan
> in `plans/README.md`: unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- src/data/live_collector.py`
> If `src/data/live_collector.py` changed since this plan was written,
> compare the "Current state" excerpts against the live code before
> proceeding; on a mismatch, treat it as a STOP condition. Note: this plan
> only creates a new test file, it does not modify `live_collector.py`.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: LOW
- **Depends on**: plans/003-shared-aiohttp-session.md
- **Category**: tests
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

`src/data/live_collector.py` is 512 lines of async WebSocket and REST
code with zero test coverage. It handles real-time data collection from
Binance: order book depth, trades, funding rates, liquidations, open
interest, long/short ratios. Any bug here silently drops data or
corrupts the Parquet output. The REST pollers have no tests for error
paths (HTTP 429 rate limit, 500 server error, timeout, connection
refused). This plan adds unit tests with mocked aiohttp/websockets so
the collector can be tested without a live Binance connection, covering
happy paths and all error scenarios.

This plan depends on plan 003 because the shared aiohttp session
refactor changes the constructor and poller method signatures. Tests
written against the pre-refactor code would break.

## Current state

The relevant files:

- `src/data/live_collector.py`: the module under test. 512 lines. Key
  classes and methods:
  - `CollectorConfig` (line 50): dataclass with `symbols`,
    `output_dir`, `flush_interval`, `open_interest_interval`,
    `long_short_interval`, `depth_levels`, `reconnect_delay`,
    `max_reconnect_attempts`, `max_buffer_size`.
  - `LiveCollector` (line 69): main class.
    - `__init__` (line 77): takes `CollectorConfig`, initializes
      buffers dict with 7 keys: `order_book`, `trades`, `funding`,
      `liquidations`, `open_interest`, `long_short`, `fear_greed`.
    - `_handle_ws_message` (line 186): parses JSON, routes by stream
      type (`@depth` or `@aggTrade`).
    - `_handle_depth` (line 208): parses order book, computes spread
      and imbalance, adds to `order_book` buffer.
    - `_handle_agg_trade` (line 251): parses trade, adds to `trades`
      buffer.
    - `_poll_open_interest` (line 321): REST GET to
      `https://fapi.binance.com/fapi/v1/openInterest?symbol=SYM`.
    - `_poll_long_short` (line 341): REST GET to
      `https://fapi.binance.com/futures/data/globalLongShortAccountRatio`.
    - `_poll_funding_rate` (line 368): REST GET to
      `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=SYM`.
    - `_poll_liquidations` (line 393): REST GET to
      `https://xoomar.com/api/markets/liquidations`.
    - `_poll_fear_greed` (line 419): REST GET to
      `https://api.alternative.me/fng/?limit=30`.
    - `_add_to_buffer` (line 443): appends row, force-flushes if
      buffer exceeds `max_buffer_size`.
    - `_flush_all` (line 461): flushes all non-empty buffers.
    - `_flush_buffer` (line 473): writes buffer to Parquet, puts rows
      back on error.

Key code excerpts:

`_handle_ws_message` (line 186):

```python
    async def _handle_ws_message(self, raw_msg: str):
        """Parse and route a WebSocket message to the appropriate buffer."""
        try:
            msg = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        stream = msg.get("stream", "")
        data = msg.get("data", msg)

        if not stream:
            return

        self._stats["total_messages"] += 1

        if "@depth" in stream:
            await self._handle_depth(data, stream)
        elif "@aggTrade" in stream:
            await self._handle_agg_trade(data, stream)
```

`_poll_open_interest` (line 321):

```python
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
```

`_add_to_buffer` (line 443):

```python
    async def _add_to_buffer(self, buffer_name: str, row: dict):
        """Add a row to a buffer. Flush if buffer is too large."""
        async with self._buffer_lock:
            self._buffers[buffer_name].append(row)
            if len(self._buffers[buffer_name]) >= self.config.max_buffer_size:
                buf = self._buffers[buffer_name]
                self._buffers[buffer_name] = []
        if "buf" in locals() and buf:
            await self._flush_buffer(buffer_name, buf)
```

Constants (lines 43-47):

```python
WS_SPOT_BASE = "wss://stream.binance.com:9443"
REST_FUTURES_BASE = "https://fapi.binance.com"
REST_SPOT_BASE = "https://api.binance.com"
```

Repo conventions (from `AGENTS.md`):

- Python 3.11+, type hints required.
- 4-space indent, 120 char max line.
- Functions max 30 lines (ideal < 15).
- Test data: fixtures with synthetic data (seed fixo).
- NUNCA usar travessao (em-dash). Use ":" or "." or "," instead.
- NUNCA simular ou fabricar dados de preco. Test data must be synthetic
  with fixed seed and marked as such.

Exemplar for test structure: `tests/test_parquet_store.py` uses
`tmp_path` fixture, `@pytest.fixture` for `store` and `sample_klines_df`,
class-based test grouping (`TestParquetStoreWrite`, `TestParquetStoreRead`).

For async tests, use `pytest-asyncio` with `@pytest.mark.asyncio`
decorator. Check if it is installed: `pip show pytest-asyncio`. If not
installed, install it: `pip install pytest-asyncio aioresponses`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests   | `pytest tests/test_live_collector.py -v` | all pass, exit 0 |
| Lint    | `ruff check tests/test_live_collector.py` | exit 0 |
| Check dep | `pip show pytest-asyncio aioresponses` | both installed |

## Suggested executor toolkit

- Use `aioresponses` for mocking aiohttp HTTP responses. It patches
  `aiohttp.ClientSession.get` at the transport level, so the poller
  methods do not need to be modified.
- Use `unittest.mock.AsyncMock` and `unittest.mock.patch` for mocking
  `websockets.connect` and WebSocket messages.
- Use `pytest-asyncio` with `@pytest.mark.asyncio` for async test
  functions.
- Reference: `tests/test_parquet_store.py` for fixture and class
  structure patterns.

## Scope

**In scope** (the only files you should modify):
- `tests/test_live_collector.py` (create new)

**Out of scope** (do NOT touch):
- `src/data/live_collector.py`: only read it to understand what to test.
  Do NOT modify it. If a bug is found while writing tests, report it as
  a finding but do not fix it in this plan.
- Any other source file.
- `requirements.txt`: do NOT add `pytest-asyncio` or `aioresponses` to
  requirements.txt. Install them in the dev environment only. If they
  are not installed, install with pip directly.

## Git workflow

- Branch: `advisor/008-live-collector-tests`
- Commit per logical group of tests. Message style:
  `test(live_collector): <description>`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Verify plan 003 is complete and install test dependencies

Confirm plan 003 (shared aiohttp session refactor) is DONE by checking
`plans/README.md`. If not DONE, STOP and report.

Install test dependencies if not present:

```bash
pip install pytest-asyncio aioresponses
```

**Verify**:
- `grep "| 003 |" plans/README.md` shows `DONE`.
- `pip show pytest-asyncio` exits 0.
- `pip show aioresponses` exits 0.

### Step 2: Create the test file with fixtures and config

Create `tests/test_live_collector.py`. Start with imports, a config
fixture, and a collector fixture:

```python
"""Tests for LiveCollector: WebSocket and REST data collection.

All network calls are mocked. No real Binance connection is made.
Test data is synthetic with fixed seeds.
"""
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioresponses import aioresponses

from src.data.live_collector import (
    LiveCollector,
    CollectorConfig,
    REST_FUTURES_BASE,
)


@pytest.fixture
def collector_config(tmp_path) -> CollectorConfig:
    """Minimal config for testing with temp output dir."""
    return CollectorConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        output_dir=str(tmp_path / "live"),
        flush_interval=999.0,  # disable auto-flush in tests
        open_interest_interval=999.0,
        long_short_interval=999.0,
        max_buffer_size=10,
    )


@pytest.fixture
def collector(collector_config: CollectorConfig) -> LiveCollector:
    """Create a LiveCollector instance."""
    return LiveCollector(collector_config)
```

**Verify**: `ruff check tests/test_live_collector.py` exits 0.
`python -c "import tests.test_live_collector"` exits 0 (or at least no
import errors).

### Step 3: Write tests for `_handle_ws_message` and message routing

Add a test class `TestWsMessageRouting` with these tests:

1. `test_handle_depth_message_routes_to_order_book`: send a valid
   `@depth` message (JSON with `stream` and `data` keys), assert the
   `order_book` buffer has 1 row with `spread`, `mid_price`,
   `imbalance_5` fields.
2. `test_handle_agg_trade_routes_to_trades`: send a valid `@aggTrade`
   message, assert the `trades` buffer has 1 row with `price`,
   `quantity`, `is_buyer_maker` fields.
3. `test_invalid_json_is_ignored`: send a non-JSON string, assert no
   buffer changed and no exception raised.
4. `test_empty_stream_is_ignored`: send a message with empty `stream`
   field, assert no buffer changed.
5. `test_unknown_stream_type_is_ignored`: send a message with stream
   `btcusdt@markPrice` (not handled in `_handle_ws_message`), assert no
   buffer changed.

Example depth message payload for tests:

```python
depth_msg = json.dumps({
    "stream": "btcusdt@depth20@100ms",
    "data": {
        "lastUpdateId": 12345,
        "bids": [["50000.0", "1.5"], ["49999.0", "2.0"], ["49998.0", "0.5"],
                 ["49997.0", "1.0"], ["49996.0", "3.0"]],
        "asks": [["50001.0", "1.0"], ["50002.0", "2.5"], ["50003.0", "0.8"],
                 ["50004.0", "1.2"], ["50005.0", "0.3"]],
    },
})
```

Example aggTrade message payload:

```python
trade_msg = json.dumps({
    "stream": "btcusdt@aggTrade",
    "data": {
        "e": "aggTrade", "E": 1700000000000, "s": "BTCUSDT",
        "a": 123, "p": "50000.0", "q": "1.5",
        "f": 100, "l": 200, "T": 1700000000000, "m": False,
    },
})
```

Use `await collector._handle_ws_message(msg)` directly (the method is
async). Mark tests with `@pytest.mark.asyncio`.

**Verify**: `pytest tests/test_live_collector.py::TestWsMessageRouting -v`
exits 0, all 5 tests pass.

### Step 4: Write tests for `_handle_depth` field computation

Add a test class `TestDepthHandling` with:

1. `test_depth_computes_spread`: assert `row["spread"]` equals
   `best_ask - best_bid`.
2. `test_depth_computes_mid_price`: assert `row["mid_price"]` equals
   `(best_bid + best_ask) / 2`.
3. `test_depth_computes_imbalance`: assert `row["imbalance_5"]` is
   between -1 and 1.
4. `test_depth_with_empty_bids`: pass data with empty bids/asks lists,
   assert no `spread` key in the row (the code only computes spread
   when both bids and asks are non-empty).
5. `test_depth_extracts_symbol_from_data`: assert `row["symbol"]`
   matches `data["s"]`.

Call `await collector._handle_depth(data, stream)` directly.

**Verify**: `pytest tests/test_live_collector.py::TestDepthHandling -v`
exits 0, all 5 tests pass.

### Step 5: Write tests for REST pollers with `aioresponses`

Add a test class `TestRestPollers` with:

1. `test_poll_open_interest_success`: mock
   `GET {REST_FUTURES_BASE}/fapi/v1/openInterest?symbol=BTCUSDT` to
   return `{"openInterest": "12345.6"}` with status 200. Call
   `await collector._poll_open_interest()`. Assert the
   `open_interest` buffer has 1 row with `open_interest == 12345.6`.
2. `test_poll_open_interest_429_rate_limited`: mock the endpoint to
   return status 429. Call the poller. Assert the `open_interest`
   buffer is still empty (no row added) and no exception propagated.
3. `test_poll_open_interest_500_server_error`: mock status 500. Assert
   buffer is empty, no exception.
4. `test_poll_open_interest_timeout`: mock the endpoint to raise
   `asyncio.TimeoutError`. Assert buffer is empty, no exception. Use
   `aioresponses` with `exception=asyncio.TimeoutError`.
5. `test_poll_funding_rate_success`: mock
   `GET {REST_FUTURES_BASE}/fapi/v1/premiumIndex?symbol=BTCUSDT` to
   return `{"markPrice": "50000", "indexPrice": "49999",
   "lastFundingRate": "0.0001", "nextFundingTime": 1700000000000}`.
   Assert the `funding` buffer has a row with `funding_rate == 0.0001`.
6. `test_poll_long_short_success`: mock
   `GET {REST_FUTURES_BASE}/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m`
   to return a list with one entry. Assert the `long_short` buffer has
   a row.

Use `aioresponses` decorator/context manager:

```python
@aioresponses
async def test_poll_open_interest_success(self, m, collector):
    url = f"{REST_FUTURES_BASE}/fapi/v1/openInterest?symbol=BTCUSDT"
    m.get(url, payload={"openInterest": "12345.6"})
    await collector._poll_open_interest()
    assert len(collector._buffers["open_interest"]) == 1
    assert collector._buffers["open_interest"][0]["open_interest"] == 12345.6
```

Note: `aioresponses` by default matches any query params. If it does
not, use `match_querystring=False` or include the full URL with params.

IMPORTANT: the poller creates a new `aiohttp.ClientSession()` inside
each method (pre-refactor). After plan 003, it may use a shared
session. If the test fails because the session is not mocked, check
whether plan 003 changed the session pattern and adjust the mock
accordingly. If plan 003 is not done, STOP.

**Verify**: `pytest tests/test_live_collector.py::TestRestPollers -v`
exits 0, all 6 tests pass.

### Step 6: Write tests for buffer management and flush

Add a test class `TestBufferManagement` with:

1. `test_add_to_buffer_appends_row`: call
   `await collector._add_to_buffer("trades", {"price": 100})`. Assert
   `collector._buffers["trades"]` has 1 entry.
2. `test_buffer_force_flush_at_max_size`: set
   `max_buffer_size=3` in config. Add 3 rows. Assert the buffer was
   flushed (buffer is empty or reset) and a Parquet file was created in
   the output dir. Use `tmp_path` to check for `.parquet` files.
3. `test_flush_all_writes_non_empty_buffers`: add rows to `trades` and
   `order_book` buffers, leave `funding` empty. Call
   `await collector._flush_all()`. Assert Parquet files exist for
   `trades` and `order_book` but not for `funding`.
4. `test_flush_buffer_puts_rows_back_on_error`: mock
   `pd.DataFrame.to_parquet` to raise an exception. Call
   `_flush_buffer`. Assert the rows are put back into the buffer
   (the error handler prepends them).

**Verify**: `pytest tests/test_live_collector.py::TestBufferManagement -v`
exits 0, all 4 tests pass.

### Step 7: Write tests for reconnection logic

Add a test class `TestReconnection` with:

1. `test_ws_reconnects_on_connection_closed`: mock
   `websockets.connect` to raise `websockets.ConnectionClosed` on the
   first call and succeed on the second. Set `reconnect_delay=0.01`
   and `max_reconnect_attempts=3`. Run `_run_websocket` in a task,
   let it connect, then cancel. Assert the stats show at least 1
   reconnect attempt.
2. `test_ws_stops_after_max_reconnects`: mock
   `websockets.connect` to always raise `ConnectionClosed`. Set
   `max_reconnect_attempts=2` and `reconnect_delay=0.01`. Run
   `_run_websocket` and assert it completes (does not hang) after 2
   attempts.

Use `patch("src.data.live_collector.websockets.connect")` with
`AsyncMock`. For the success case, the mock should return an async
context manager that yields a mock WebSocket with an async iterator
that produces one message then stops.

**Verify**: `pytest tests/test_live_collector.py::TestReconnection -v`
exits 0, all 2 tests pass.

### Step 8: Run the full test suite and lint

**Verify**:
- `pytest tests/test_live_collector.py -v` exits 0, all tests pass
  (expect approximately 22 tests total).
- `ruff check tests/test_live_collector.py` exits 0.

## Test plan

New test file: `tests/test_live_collector.py`. Test classes and cases:

- `TestWsMessageRouting` (5 tests): depth routing, aggTrade routing,
  invalid JSON, empty stream, unknown stream type.
- `TestDepthHandling` (5 tests): spread, mid_price, imbalance, empty
  bids/asks, symbol extraction.
- `TestRestPollers` (6 tests): open interest success/429/500/timeout,
  funding rate success, long/short success.
- `TestBufferManagement` (4 tests): append, force flush, flush all,
  error rollback.
- `TestReconnection` (2 tests): reconnect on close, stop after max
  attempts.

Total: approximately 22 tests.

Structural pattern: model after `tests/test_parquet_store.py` (fixture
for config/collector, class-based grouping, synthetic data with fixed
seeds).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_live_collector.py -v` exits 0, all tests pass.
- [ ] `ruff check tests/test_live_collector.py` exits 0.
- [ ] `tests/test_live_collector.py` exists and has at least 20 test
      functions.
- [ ] No files outside `tests/test_live_collector.py` are modified
      (`git status`). Exception: `requirements.txt` may be touched if
      the executor added `pytest-asyncio` or `aioresponses`, but this
      is discouraged.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back (do not improvise) if:

- `src/data/live_collector.py` does not match the excerpts in "Current
  state" (the codebase has drifted, or plan 003 changed the method
  signatures).
- Plan 003 is not DONE (check `plans/README.md`). The shared session
  refactor changes how pollers create/use `aiohttp.ClientSession`, so
  tests written against the old pattern would break.
- `pytest-asyncio` or `aioresponses` cannot be installed (report the
  error). Without these, async HTTP mocking is not feasible.
- A method being tested (e.g. `_poll_open_interest`) has a different
  signature or URL pattern than what is documented in "Current state".
  This would mean plan 003 changed it: compare and adjust, or STOP if
  the change is too large.
- A step's verification fails twice after a reasonable fix attempt.
- You discover a bug in `live_collector.py` while writing tests. Report
  it as a finding but do NOT fix it (out of scope). If the bug prevents
  writing a valid test, STOP and report the bug.

## Maintenance notes

- These tests mock all network calls. If the URL patterns or API
  response shapes change (e.g. Binance changes their API), the mock
  payloads in the tests must be updated to match.
- If new REST pollers or WebSocket streams are added to
  `LiveCollector`, corresponding test cases should be added to this
  file. The pattern is established: one test class per functional area.
- A reviewer should scrutinize: (1) that no test makes a real network
  call (all must be mocked), (2) that the `aioresponses` mocks match
  the actual URLs used in the code, (3) that the reconnection tests
  do not hang (use timeouts or `max_reconnect_attempts` limits), (4)
  that test data is synthetic and marked as such.
- Follow-up deferred: integration test with a local mock WebSocket
  server (e.g. `websockets.serve`) for end-to-end message flow. This
  is out of scope because it requires more infrastructure.
