# Plan 004: Parallelize REST pollers with asyncio.gather

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
> mismatch, treat it as a STOP condition. This plan depends on plan 003
> being done first: verify that `self._http_session` exists and poller
> methods accept a `session` parameter before starting.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/003-shared-aiohttp-session.md
- **Category**: perf
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

Three REST poller methods (`_poll_open_interest`, `_poll_long_short`,
`_poll_funding_rate`) loop over symbols sequentially, making one HTTP
request per symbol and waiting for each response before sending the next.
With N symbols, the poll cycle takes N * RTT. If RTT is 100ms and there
are 10 symbols, each poll cycle takes 1 second, which eats into the poll
interval budget and makes data less fresh. Using `asyncio.gather` to fire
all requests concurrently reduces the cycle to roughly 1 * RTT (the
slowest single request), a 10x improvement for 10 symbols. This makes the
collector more responsive and reduces the chance of overlapping cycles
when intervals are short.

## Current state

The file: `src/data/live_collector.py` (512 lines). After plan 003, the
poller methods accept a `session: aiohttp.ClientSession` parameter and use
the shared session. The per-symbol loops are still sequential.

**IMPORTANT**: This plan assumes plan 003 is already done. If plan 003 is
not done, STOP and report. The excerpts below show the post-003 expected
state (session passed as parameter, no per-method session creation).

**`_poll_open_interest`** (after plan 003, ~line 321):
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

**`_poll_long_short`** (after plan 003, ~line 341):
```python
    async def _poll_long_short(self, session: aiohttp.ClientSession):
        """Poll long/short ratio (global account ratio) for all symbols."""
        for symbol in self.config.symbols:
            sym_upper = symbol.upper()
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
```

**`_poll_funding_rate`** (after plan 003, ~line 368):
```python
    async def _poll_funding_rate(self, session: aiohttp.ClientSession):
        """Poll funding rate and mark price via futures REST API."""
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
```

The other two pollers (`_poll_liquidations`, `_poll_fear_greed`) fetch a
single URL (not per-symbol), so they do not need parallelization. Leave
them unchanged.

Repo conventions (from `AGENTS.md`):
- Python 3.11+, 4-space indent, 120 char lines, functions max 30 lines.
- `asyncio` is already imported (line 25: `import asyncio`).
- The `_add_to_buffer` method is async and uses a lock, so concurrent
  calls are safe.

## Commands you will need

| Purpose   | Command                                  | Expected on success |
|-----------|------------------------------------------|---------------------|
| Lint      | `ruff check src/data/live_collector.py`  | exit 0              |
| Import    | `python -c "from src.data.live_collector import LiveCollector"` | exit 0 |
| Typecheck | `mypy src/data/live_collector.py`        | exit 0              |

## Scope

**In scope** (the only file you should modify):
- `src/data/live_collector.py`

**Out of scope** (do NOT touch, even though they look related):
- All other files.
- `_poll_liquidations` and `_poll_fear_greed` (single URL, no
  parallelization needed).
- The `_run_rest_poller` wrapper, `start()`, `stop()` (already fixed in
  plan 003).
- Do not change poll intervals, URLs, or data parsing logic.

## Git workflow

- Branch: `advisor/004-parallelize-rest-pollers`
- Commit message style: conventional commits, e.g.
  `perf(data): parallelize per-symbol REST fetches with asyncio.gather`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Extract per-symbol fetch for _poll_open_interest

Extract the per-symbol fetch logic into a helper method. Add this new
method near `_poll_open_interest`:
```python
    async def _fetch_open_interest(self, session: aiohttp.ClientSession, symbol: str) -> None:
        """Fetch open interest for a single symbol."""
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

Then replace the body of `_poll_open_interest` to use `asyncio.gather`:
```python
    async def _poll_open_interest(self, session: aiohttp.ClientSession):
        """Poll open interest for all symbols."""
        await asyncio.gather(
            *[self._fetch_open_interest(session, sym) for sym in self.config.symbols]
        )
```

**Verify**: `ruff check src/data/live_collector.py` -> exit 0

### Step 2: Extract per-symbol fetch for _poll_long_short

Add this helper method:
```python
    async def _fetch_long_short(self, session: aiohttp.ClientSession, symbol: str) -> None:
        """Fetch long/short ratio for a single symbol."""
        sym_upper = symbol.upper()
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
```

Replace `_poll_long_short` body:
```python
    async def _poll_long_short(self, session: aiohttp.ClientSession):
        """Poll long/short ratio (global account ratio) for all symbols."""
        await asyncio.gather(
            *[self._fetch_long_short(session, sym) for sym in self.config.symbols]
        )
```

**Verify**: `ruff check src/data/live_collector.py` -> exit 0

### Step 3: Extract per-symbol fetch for _poll_funding_rate

Add this helper method:
```python
    async def _fetch_funding_rate(self, session: aiohttp.ClientSession, symbol: str) -> None:
        """Fetch funding rate and mark price for a single symbol."""
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
```

Replace `_poll_funding_rate` body:
```python
    async def _poll_funding_rate(self, session: aiohttp.ClientSession):
        """Poll funding rate and mark price via futures REST API."""
        await asyncio.gather(
            *[self._fetch_funding_rate(session, sym) for sym in self.config.symbols]
        )
```

**Verify**: `ruff check src/data/live_collector.py` -> exit 0

### Step 4: Full verification

**Verify**:
- `ruff check src/data/live_collector.py` -> exit 0
- `mypy src/data/live_collector.py` -> exit 0
- `python -c "from src.data.live_collector import LiveCollector; print('ok')"` -> prints `ok`, exit 0

## Test plan

No new tests are required for this plan (test coverage for live_collector
is plan 008). The verification is structural: the module must import, lint
and typecheck must pass, and the three poller methods must use
`asyncio.gather` with extracted helper methods.

If you want to add a test, model after `tests/test_backtest_engine.py` but
this is out of scope unless the operator approves. A good test would mock
`session.get` to return canned responses and assert that
`_poll_open_interest` calls `_add_to_buffer` once per symbol.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `ruff check src/data/live_collector.py` exits 0
- [ ] `mypy src/data/live_collector.py` exits 0
- [ ] `python -c "from src.data.live_collector import LiveCollector"` exits 0
- [ ] `grep -n "asyncio.gather" src/data/live_collector.py` returns at least 3 matches in the three poller methods (plus the existing one in `start()`)
- [ ] Three helper methods exist: `_fetch_open_interest`, `_fetch_long_short`, `_fetch_funding_rate`
- [ ] `_poll_liquidations` and `_poll_fear_greed` are unchanged (no `asyncio.gather` added to them)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Plan 003 has not been done (poller methods do not accept a `session`
  parameter, or `self._http_session` does not exist). This plan depends on
  the shared session.
- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written, or plan 003 was
  implemented differently than expected).
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover that `_add_to_buffer` is not safe for concurrent calls
  (e.g. the lock is missing or the buffer is a plain list without
  protection). The current code uses `async with self._buffer_lock`, so it
  should be safe, but if the lock was removed or changed, STOP.

## Maintenance notes

- `asyncio.gather` with `*[]` unpacking creates all coroutines before
  awaiting. For a very large symbol universe (hundreds), this could create
  a burst of simultaneous connections. The shared `aiohttp.ClientSession`
  has an internal connection limit (default 100 total, 30 per host). If
  the symbol count exceeds this, aiohttp will queue the excess requests.
  This is fine for the current 3-10 symbol universe.
- A reviewer should verify that the `_stats` counter increments are safe
  under concurrency. Python's `+=` on an integer is not atomic, but in
  asyncio (single-threaded) the increment happens between `await` points,
  so there is no race within a single gather. This is safe as long as no
  `await` occurs between reading and writing the counter.
- Follow-up: plan 008 adds unit tests for live_collector, including
  concurrent fetch tests.
