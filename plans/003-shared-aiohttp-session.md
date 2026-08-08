# Plan 003: Fix resource leak: shared aiohttp session in live_collector

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- src/data/live_collector.py`
> If this file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

Five REST poller methods in `LiveCollector` each create a new
`aiohttp.ClientSession()` on every poll cycle. `ClientSession` holds a
connection pool and SSL context, and creating/destroying it repeatedly
leaks file descriptors and TCP connections, causes TLS handshake overhead
on every cycle, and can exhaust the OS connection limit under sustained
load. The collector is designed to run indefinitely (a trading bot), so
this leak compounds over hours and days. The fix is to create one shared
session in `start()`, pass it to all poller methods, and close it in
`stop()`.

## Current state

The file: `src/data/live_collector.py` (512 lines). Real-time data
collector for Binance Futures via WebSocket and REST.

The `LiveCollector.__init__` (line 77) sets up config and state but
creates no session:
```python
    def __init__(self, config: CollectorConfig):
        self.config = config
        self.symbols = [s.lower() for s in config.symbols]
        ...
        self._running = False
        self._ws_session: Optional[websockets.WebSocketClientProtocol] = None
```

The `start` method (line 101) launches pollers but creates no session:
```python
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
```

The `stop` method (line 124) closes the WebSocket but no HTTP session:
```python
    async def stop(self):
        """Stop the collector and flush remaining data."""
        self._running = False
        if self._ws_session:
            await self._ws_session.close()
        await self._flush_all()
        logger.info("Collector stopped. Final stats:")
        self._print_stats()
```

Each poller creates its own session. Example, `_poll_open_interest` (line
321):
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

The same `async with aiohttp.ClientSession() as session:` pattern appears
at lines 323, 343, 370, 400, 421 in these five methods:
- `_poll_open_interest` (line 321)
- `_poll_long_short` (line 341)
- `_poll_funding_rate` (line 368)
- `_poll_liquidations` (line 393)
- `_poll_fear_greed` (line 419)

The `_run_rest_poller` wrapper (line 312) calls the poll function in a
loop:
```python
    async def _run_rest_poller(self, name: str, poll_func, interval: float):
        """Run a REST API poller at a fixed interval."""
        while self._running:
            try:
                await poll_func()
            except Exception as e:
                logger.error(f"REST poller {name} error: {e}")
            await asyncio.sleep(interval)
```

Repo conventions (from `AGENTS.md`):
- Python 3.11+, type hints required, 4-space indent, 120 char lines.
- `aiohttp` is already imported (line 35: `import aiohttp`).
- `Optional` is already imported (line 33: `from typing import Optional`).

## Commands you will need

| Purpose   | Command                                                  | Expected on success |
|-----------|----------------------------------------------------------|---------------------|
| Lint      | `ruff check src/data/live_collector.py`                  | exit 0              |
| Import    | `python -c "from src.data.live_collector import LiveCollector"` | exit 0    |
| Typecheck | `mypy src/data/live_collector.py`                        | exit 0              |

## Scope

**In scope** (the only file you should modify):
- `src/data/live_collector.py`

**Out of scope** (do NOT touch, even though they look related):
- All other files. Plan 004 will parallelize the poller loops but depends
  on this plan being done first. Do not do plan 004's work here.
- Do not change the poll intervals, URLs, or data parsing logic.
- Do not change the WebSocket code.

## Git workflow

- Branch: `advisor/003-shared-aiohttp-session`
- Commit message style: conventional commits, e.g.
  `fix(data): use shared aiohttp.ClientSession in live collector pollers`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add shared session attribute to __init__

In `__init__` (around line 95-96, near `self._ws_session`), add:
```python
        self._http_session: Optional[aiohttp.ClientSession] = None
```

**Verify**: `python -c "from src.data.live_collector import LiveCollector"` -> exit 0

### Step 2: Create shared session in start()

In the `start` method (line 101), create the session before launching
tasks. Replace the beginning of `start` so it reads:
```python
    async def start(self):
        """Start all collectors and storage flusher. Runs until cancelled."""
        self._running = True
        self._http_session = aiohttp.ClientSession()
        logger.info(f"Starting live collector for {len(self.symbols)} symbols: {self.symbols}")

        tasks = [
            ...
        ]

        try:
            await asyncio.gather(*tasks)
        finally:
            await self.stop()
```

The `try/finally` ensures `stop()` is called if `asyncio.gather` is
cancelled or raises, so the session is always cleaned up.

**Verify**: `python -c "from src.data.live_collector import LiveCollector"` -> exit 0

### Step 3: Close shared session in stop()

In the `stop` method (line 124), add session cleanup. Replace it to read:
```python
    async def stop(self):
        """Stop the collector and flush remaining data."""
        self._running = False
        if self._ws_session:
            await self._ws_session.close()
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        await self._flush_all()
        logger.info("Collector stopped. Final stats:")
        self._print_stats()
```

**Verify**: `python -c "from src.data.live_collector import LiveCollector"` -> exit 0

### Step 4: Update _run_rest_poller to pass session

The poller methods need access to the shared session. The cleanest
approach: pass the session to each poll function via the
`_run_rest_poller` wrapper. Change `_run_rest_poller` (line 312) to:
```python
    async def _run_rest_poller(self, name: str, poll_func, interval: float):
        """Run a REST API poller at a fixed interval."""
        while self._running:
            try:
                await poll_func(self._http_session)
            except Exception as e:
                logger.error(f"REST poller {name} error: {e}")
            await asyncio.sleep(interval)
```

**Verify**: `ruff check src/data/live_collector.py` -> exit 0 (may show
errors until step 5 is done, that is expected)

### Step 5: Update all five poller methods to accept session

For each of the five poller methods, change the signature to accept
`session: aiohttp.ClientSession` as a parameter and remove the
`async with aiohttp.ClientSession() as session:` line, dedenting the body.

**`_poll_open_interest`** (line 321), change to:
```python
    async def _poll_open_interest(self, session: aiohttp.ClientSession):
        """Poll open interest for all symbols."""
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

**`_poll_long_short`** (line 341), same pattern: add `session` param,
remove `async with aiohttp.ClientSession() as session:`, dedent the
`for symbol in self.config.symbols:` loop body.

**`_poll_funding_rate`** (line 368), same pattern.

**`_poll_liquidations`** (line 393), same pattern. Note: this method does
not loop over symbols, it fetches a single URL. Just remove the session
creation and use the passed `session`.

**`_poll_fear_greed`** (line 419), same pattern as liquidations: single
URL fetch, remove session creation, use passed `session`.

**Verify**: `ruff check src/data/live_collector.py` -> exit 0

### Step 6: Full verification

**Verify**:
- `ruff check src/data/live_collector.py` -> exit 0
- `mypy src/data/live_collector.py` -> exit 0
- `python -c "from src.data.live_collector import LiveCollector; print('ok')"` -> prints `ok`, exit 0

## Test plan

No new tests are required for this plan (test coverage for live_collector
is plan 008, which depends on this plan). The verification is structural:
the module must import, lint must pass, and the session lifecycle must be
correct (created in `start`, closed in `stop`).

If you want to add a smoke test, model after the pattern in
`tests/test_backtest_engine.py` but this is out of scope unless the
operator approves.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `ruff check src/data/live_collector.py` exits 0
- [ ] `mypy src/data/live_collector.py` exits 0
- [ ] `python -c "from src.data.live_collector import LiveCollector"` exits 0
- [ ] `grep -n "aiohttp.ClientSession()" src/data/live_collector.py` returns exactly 1 match (in `start()`)
- [ ] `grep -n "async with aiohttp.ClientSession" src/data/live_collector.py` returns no matches
- [ ] All five poller methods accept `session: aiohttp.ClientSession` as a parameter
- [ ] `stop()` closes `self._http_session` if it exists and is not closed
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover that a poller method is called from somewhere other than
  `_run_rest_poller` (e.g. directly from a test or another module), which
  would break if the signature changes. In that case, report the caller
  rather than changing the out-of-scope file.
- The `start()` method is called in a way that does not go through
  `asyncio.gather` (e.g. tasks are awaited individually elsewhere), which
  would affect the `try/finally` cleanup logic.

## Maintenance notes

- After this plan, the shared session is created once and reused. If the
  session ever enters a bad state (e.g. server closes connection), aiohttp
  handles reconnection internally at the connection pool level, so no
  manual recreation is needed under normal operation.
- A reviewer should verify that `stop()` is always called. The
  `try/finally` in `start()` handles the cancellation case, but if the
  caller uses `asyncio.wait_for` or similar with a timeout, ensure
  `stop()` still runs.
- Follow-up: plan 004 parallelizes the per-symbol loops inside each
  poller using `asyncio.gather`. That plan depends on this one because the
  shared session must exist before concurrent fetches can share it.
- Follow-up: plan 008 adds unit tests for live_collector, including
  session lifecycle tests.
