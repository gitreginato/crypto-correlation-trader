# Plan 002: Fix backtest correctness bugs (position close, div-by-zero, .iloc guards)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- src/backtest/engine.py scripts/analyze_live.py src/strategy/momentum.py src/strategy/mean_reversion.py src/strategy/stat_arb.py`
> If any in-scope file changed since this plan was written, compare the
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

Three correctness bugs affect financial results. First, the backtest engine
closes end-of-data positions using `current_prices`, which only contains
symbols that had data at the last timestamp. If a symbol's data ends early,
its position is never closed and PnL is silently wrong. Second, a
division by `open_interest.iloc[0]` has no zero check, which can raise or
produce infinity. Third, multiple `.iloc[-1]` accesses across three
strategy files have no empty-series guard, so a short or empty dataframe
causes an IndexError crash instead of a graceful skip. These are all
silent-or-crash bugs in money-handling code.

## Current state

The relevant files and their roles:

- `src/backtest/engine.py` (334 lines): `BacktestEngine` with a bar-by-bar
  loop that opens/closes positions and tracks equity.
- `scripts/analyze_live.py` (1945 lines): live analysis dashboard. Line 732
  computes 24h OI change.
- `src/strategy/momentum.py` (278 lines): momentum strategy with long/short
  condition checks using `.iloc[-1]`.
- `src/strategy/mean_reversion.py` (203 lines): mean reversion strategy
  using `.iloc[-1]` for z-score and price.
- `src/strategy/stat_arb.py` (274 lines): pairs strategy using `.iloc[-1]`
  for spread z-score and prices.

### Finding 1: Position close uses stale current_prices

`src/backtest/engine.py:83-135` (the main loop):
```python
        for i, timestamp in enumerate(all_indices):
            # 1. Update existing positions with current prices
            current_prices = {}
            for symbol in symbols:
                df = data[symbol]
                if timestamp in df.index:
                    current_prices[symbol] = float(df.loc[timestamp, "close"])
            ...
        # Close all remaining positions at last prices
        for symbol in list(self.positions.keys()):
            if symbol in current_prices:
                capital = self._close_position(symbol, current_prices[symbol], timestamp, capital, "end_of_data")

        return self._compute_metrics(capital)
```

The problem: `current_prices` is rebuilt every iteration and only contains
symbols present at the current `timestamp`. After the loop ends,
`current_prices` holds only symbols that had data at the final timestamp.
If a symbol's data ended earlier (e.g. a delisted or shorter series), it
will not be in `current_prices`, the `if symbol in current_prices` guard
fails, and the position is never closed. The position's PnL is never
realized, so `_compute_metrics` gets wrong capital.

### Finding 2: Division by open_interest without zero check

`scripts/analyze_live.py:732`:
```python
        'oi_change_24h': float(oi_latest['open_interest'] / oi['open_interest'].iloc[0] - 1) if oi_latest is not None and len(oi) > 1 else 0,
```

If `oi['open_interest'].iloc[0]` is 0, this divides by zero. In Python
float division this produces `inf` or `nan` rather than raising, which then
propagates into the dashboard as a nonsensical value.

### Finding 3: .iloc[-1] without empty checks

Locations and excerpts:

`src/strategy/momentum.py:123` (inside `_check_long_conditions`):
```python
            momentum = (close.iloc[-1] - close.iloc[-self.config.formation_period]) / close.iloc[-self.config.formation_period]
```

`src/strategy/momentum.py:130`:
```python
        current_rsi = rsi.iloc[-1]
```

`src/strategy/momentum.py:138-140`:
```python
        meta["ema_fast"] = float(ema_f.iloc[-1])
        meta["ema_slow"] = float(ema_s.iloc[-1])
        if ema_f.iloc[-1] > ema_s.iloc[-1]:
```

`src/strategy/momentum.py:145`:
```python
        current_adx = adx.iloc[-1]
```

`src/strategy/momentum.py:160` (inside `_check_short_conditions`):
```python
            momentum = (close.iloc[-1] - close.iloc[-self.config.formation_period]) / close.iloc[-self.config.formation_period]
```

`src/strategy/momentum.py:167`:
```python
        current_rsi = rsi.iloc[-1]
```

`src/strategy/momentum.py:175-177`:
```python
        meta["ema_fast"] = float(ema_f.iloc[-1])
        meta["ema_slow"] = float(ema_s.iloc[-1])
        if ema_f.iloc[-1] < ema_s.iloc[-1]:
```

`src/strategy/momentum.py:182`:
```python
        current_adx = adx.iloc[-1]
```

`src/strategy/momentum.py:209` (inside `generate_signals`):
```python
            current_rsi = rsi.iloc[-1]
```

`src/strategy/momentum.py:218`:
```python
            current_price = float(df["close"].iloc[-1])
```

`src/strategy/momentum.py:223`:
```python
            current_atr = atr.iloc[-1]
```

`src/strategy/mean_reversion.py:130`:
```python
                current_z = zscore.iloc[-1]
```

`src/strategy/mean_reversion.py:138`:
```python
                current_price = price_df[asset].iloc[-1]
```

`src/strategy/mean_reversion.py:190` (inside `check_exit`):
```python
        current_z = zscore.iloc[-1]
```

`src/strategy/stat_arb.py:200`:
```python
            current_z = zscore.iloc[-1]
```

`src/strategy/stat_arb.py:204-205`:
```python
            current_price_a = float(pa.iloc[-1])
            current_price_b = float(pb.iloc[-1])
```

`src/strategy/stat_arb.py:261` (inside `check_exit`):
```python
        current_z = zscore.iloc[-1]
```

Repo conventions (from `AGENTS.md`):
- "Erros de dados: raise com contexto". For strategy signal generation,
  the convention is to skip (return early / continue) when data is
  insufficient, not to raise. See `src/strategy/momentum.py:194` which
  already does `if len(df) < max(...): continue`.
- Python 3.11+, 4-space indent, 120 char lines, functions max 30 lines.
- Do not fabricate data. If a series is empty, skip the signal.

## Commands you will need

| Purpose   | Command                                              | Expected on success |
|-----------|------------------------------------------------------|---------------------|
| Tests     | `pytest tests/test_backtest_engine.py -v`            | all pass            |
| Tests     | `pytest tests/test_mean_reversion.py tests/test_momentum.py tests/test_stat_arb.py -v` | all pass |
| Lint      | `ruff check src/ scripts/`                           | exit 0              |
| Typecheck | `mypy src/`                                          | exit 0              |

## Scope

**In scope** (the only files you should modify):
- `src/backtest/engine.py`
- `scripts/analyze_live.py`
- `src/strategy/momentum.py`
- `src/strategy/mean_reversion.py`
- `src/strategy/stat_arb.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/data/live_collector.py` (resource leak fix is plan 003).
- `scripts/statistical_analyzer.py` (empty catch fix is plan 001).
- `src/analysis/correlation.py` (vectorization is plan 005).
- Any test files. If existing tests break, fix the source code, not the
  tests, unless the test itself encodes the bug.

## Git workflow

- Branch: `advisor/002-fix-backtest-correctness`
- Commit per finding or per file. Message style: conventional commits,
  e.g. `fix(backtest): close positions using last known price per symbol`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix position close in src/backtest/engine.py

The fix: track the last known price for each symbol throughout the loop,
then use that dict for end-of-data closes.

In the main `run` method, before the loop (after line 81 where
`peak_equity = capital`), add:
```python
        last_known_prices: dict[str, float] = {}
```

Inside the loop, after `current_prices` is built (after line 89), add:
```python
            for sym, price in current_prices.items():
                last_known_prices[sym] = price
```

Replace the end-of-data close block (lines 130-133) with:
```python
        # Close all remaining positions at last known prices
        for symbol in list(self.positions.keys()):
            if symbol in last_known_prices:
                capital = self._close_position(
                    symbol, last_known_prices[symbol], timestamp, capital, "end_of_data"
                )
```

This ensures every symbol that ever had a price during the loop gets its
position closed, even if its data ended early.

**Verify**: `pytest tests/test_backtest_engine.py -v` -> all pass

### Step 2: Fix div-by-zero in scripts/analyze_live.py

At line 732, add a zero guard. Replace:
```python
        'oi_change_24h': float(oi_latest['open_interest'] / oi['open_interest'].iloc[0] - 1) if oi_latest is not None and len(oi) > 1 else 0,
```
with:
```python
        'oi_change_24h': float(oi_latest['open_interest'] / oi['open_interest'].iloc[0] - 1) if oi_latest is not None and len(oi) > 1 and oi['open_interest'].iloc[0] != 0 else 0,
```

**Verify**: `python -c "import ast; ast.parse(open('scripts/analyze_live.py').read())"` -> exit 0

### Step 3: Add empty guards in src/strategy/momentum.py

For each `.iloc[-1]` access listed in Finding 3, add an empty check before
it. The pattern depends on context:

For `_check_long_conditions` (line 112) and `_check_short_conditions`
(line 152), add a guard at the top of each method, right after
`close = df["close"]`:
```python
        if close.empty:
            return False, 0, {}
```

For the RSI/EMA/ADX `.iloc[-1]` accesses inside those methods, the series
are derived from `close` via pandas operations. If `close` is non-empty but
short, these can still be empty or all-NaN. Add a guard after each computed
series before accessing `.iloc[-1]`:
```python
        rsi = self.compute_rsi(close, self.config.rsi_period)
        if rsi.empty:
            return False, 0, {}
        current_rsi = rsi.iloc[-1]
```

Apply the same `if <series>.empty: return False, 0, {}` guard before each
of these `.iloc[-1]` accesses: `ema_f`, `ema_s`, `adx` in both
`_check_long_conditions` and `_check_short_conditions`.

For `generate_signals` (line 189), the method already has a length check at
line 194 (`if len(df) < max(...): continue`). The `.iloc[-1]` accesses at
lines 209, 218, 223 are on series derived from `df` which is already
confirmed non-empty. Add guards for safety:
```python
            rsi = self.compute_rsi(df["close"], self.config.rsi_period)
            if rsi.empty:
                continue
            current_rsi = rsi.iloc[-1]
```
And before line 223:
```python
            atr = self.compute_atr(df, self.config.atr_period)
            if atr.empty:
                continue
            current_atr = atr.iloc[-1]
```

Line 218 (`current_price = float(df["close"].iloc[-1])`) is safe because
`df` passed the length check at line 194, but you may add
`if df["close"].empty: continue` for defensive consistency.

**Verify**: `pytest tests/test_momentum.py -v` -> all pass

### Step 4: Add empty guards in src/strategy/mean_reversion.py

For line 130 (`current_z = zscore.iloc[-1]`), add before it:
```python
                if zscore.empty:
                    continue
                current_z = zscore.iloc[-1]
```

For line 138 (`current_price = price_df[asset].iloc[-1]`), add before it:
```python
                if price_df[asset].empty:
                    continue
                current_price = price_df[asset].iloc[-1]
```

For line 190 (inside `check_exit`), add before it:
```python
        if zscore.empty:
            return False
        current_z = zscore.iloc[-1]
```

**Verify**: `pytest tests/test_mean_reversion.py -v` -> all pass

### Step 5: Add empty guards in src/strategy/stat_arb.py

For line 200 (`current_z = zscore.iloc[-1]`), add before it:
```python
            if zscore.empty:
                continue
            current_z = zscore.iloc[-1]
```

For lines 204-205 (`current_price_a = float(pa.iloc[-1])` and
`current_price_b = float(pb.iloc[-1])`), add before them:
```python
            if pa.empty or pb.empty:
                continue
            current_price_a = float(pa.iloc[-1])
            current_price_b = float(pb.iloc[-1])
```

For line 261 (inside `check_exit`), add before it:
```python
        if zscore.empty:
            return False
        current_z = zscore.iloc[-1]
```

**Verify**: `pytest tests/test_stat_arb.py -v` -> all pass

### Step 6: Full verification

**Verify**:
- `pytest tests/test_backtest_engine.py tests/test_mean_reversion.py tests/test_momentum.py tests/test_stat_arb.py -v` -> all pass
- `ruff check src/ scripts/` -> exit 0
- `mypy src/` -> exit 0

## Test plan

No new tests are strictly required, but the following regression tests
would be valuable if time permits (optional, only if the operator approves):

- `tests/test_backtest_engine.py`: add a test where one symbol's data ends
  before the other, assert that the position is closed at the last known
  price and capital reflects the realized PnL. Model after the existing
  test structure in that file.
- `tests/test_momentum.py`: add a test with a 1-row dataframe, assert that
  `generate_signals` returns an empty list (no crash).

Verification: `pytest tests/test_backtest_engine.py tests/test_mean_reversion.py tests/test_momentum.py tests/test_stat_arb.py -v` -> all pass.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_backtest_engine.py -v` exits 0
- [ ] `pytest tests/test_mean_reversion.py tests/test_momentum.py tests/test_stat_arb.py -v` exits 0
- [ ] `ruff check src/ scripts/` exits 0
- [ ] `mypy src/` exits 0
- [ ] `grep -n "current_prices\[symbol\]" src/backtest/engine.py` does NOT appear in the end-of-data close block (should use `last_known_prices`)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover that `current_prices` is used elsewhere in the loop in a way
  that depends on it only containing current-timestamp symbols (not last
  known). In that case, `last_known_prices` must be a separate dict and
  `current_prices` must stay as-is for the in-loop logic.
- An existing test encodes the buggy behavior (e.g. asserts that a position
  is NOT closed when data ends early). Do not modify the test to match the
  bug; report it instead.

## Maintenance notes

- The `last_known_prices` dict grows monotonically. For very long
  backtests with many symbols this is fine (it is one float per symbol),
  but if the symbol universe changes dynamically in the future, stale
  entries could accumulate. A future plan could add pruning.
- A reviewer should verify that `_close_position` at end-of-data uses the
  correct `timestamp`. Currently it uses the last loop `timestamp`, which
  may not be the symbol's actual last data timestamp. This is acceptable
  for now but could be improved by tracking per-symbol last timestamps.
- Follow-up deferred: plan 007 optimizes the backtest loop slicing
  (`data_up_to` at line 95 creates a copy every bar). That plan depends on
  this one (002) being done first.
