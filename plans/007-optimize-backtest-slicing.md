# Plan 007: Optimize backtest loop slicing

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report: do not improvise. When done, update the status row for this plan
> in `plans/README.md`: unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- src/backtest/engine.py src/strategy/base.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/002-backtest-correctness-bugs.md
- **Category**: perf
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The backtest engine copies a DataFrame slice for every symbol on every
bar: `data_up_to = {s: data[s].loc[:timestamp] for s in symbols}`. With
1000 bars and 5 symbols, that is 5000 slice copies, each up to the full
DataFrame size. This is O(n_bars * n_symbols * df_size) in memory and
CPU, making backtests of long histories (years of 5-minute data) slow
and memory-hungry. Passing a reference to the full DataFrame plus the
current integer index avoids the copy entirely, while preserving
look-ahead protection by only exposing data up to the current bar index.

This plan depends on plan 002 because the correctness bugs (position
close logic, division by zero, `.iloc` guards) must be fixed first:
optimizing broken code makes the bugs harder to find and fix later.

## Current state

The relevant files:

- `src/backtest/engine.py`: backtest engine. The `run` method (lines
  65-135) is the hot loop. Line 95 is the slicing hotspot.
- `src/strategy/base.py`: strategy interface. The `generate_signals`
  method (line 70) receives `data: dict[str, pd.DataFrame]`. This
  signature may need to change to accept a row count or end index.

Code as it exists today (`src/backtest/engine.py:83-99`):

```python
    for i, timestamp in enumerate(all_indices):
        # 1. Update existing positions with current prices
        current_prices = {}
        for symbol in symbols:
            df = data[symbol]
            if timestamp in df.index:
                current_prices[symbol] = float(df.loc[timestamp, "close"])

        # 2. Check exits for open positions
        capital = self._check_exits(timestamp, current_prices, capital)

        # 3. Generate signals from data up to current bar
        data_up_to = {s: data[s].loc[:timestamp] for s in symbols if timestamp in data[s].index}
        if i >= 30:  # need enough data for indicators
            signals = self.strategy.generate_signals(data_up_to)
        else:
            signals = []
```

The strategy interface (`src/strategy/base.py:70-79`):

```python
    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate trading signals from market data.

        Args:
            data: Dict mapping symbol to OHLCV DataFrame.

        Returns:
            List of Signal objects.
        """
        raise NotImplementedError
```

How strategies use the data dict (they read `df["close"]`, `df.index`,
`len(df)`, `.iloc[-1]`, `.pct_change()`, `.tail()`, `.set_index()`):

- `src/strategy/mean_reversion.py:84-87`: iterates `data.items()`, reads
  `df["close"]`, checks `len(df)`.
- `src/strategy/momentum.py:193-219`: iterates `data.items()`, reads
  `df["close"]`, `len(df)`, `df.index[-1]`, `.iloc[-1]`.
- `src/strategy/stat_arb.py:174-176`: iterates `data.items()`, reads
  `df["close"]`, checks `len(df)`.
- `src/strategy/meta.py:72`: delegates to sub-strategies.

None of these strategies mutate the DataFrame. They all read from it.
This means passing a view (not a copy) is safe for the existing
strategies. BUT the STOP condition below handles the case where a
strategy does depend on receiving a copy.

Repo conventions (from `AGENTS.md`):

- Python 3.11+, type hints required.
- 4-space indent, 120 char max line.
- Functions max 30 lines (ideal < 15).
- NUNCA usar travessao (em-dash). Use ":" or "." or "," instead.
- Backtest rule: NUNCA usar dados futuros (look-ahead bias). This plan
  MUST preserve look-ahead protection.

Exemplar for tests: `tests/test_backtest_engine.py` uses
`SimpleBuyHoldStrategy` and `make_ohlcv(n, trend)` helper.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests   | `pytest tests/test_backtest_engine.py -v` | all pass, exit 0 |
| Lint    | `ruff check src/backtest/engine.py src/strategy/base.py` | exit 0 |
| Type    | `mypy src/backtest/engine.py src/strategy/base.py` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `src/backtest/engine.py`
- `src/strategy/base.py` (only if the interface signature needs updating)

**Out of scope** (do NOT touch, even though they look related):
- `src/strategy/mean_reversion.py`: only update if the interface
  signature changes AND it breaks. If the signature change is backward
  compatible (e.g. adding an optional parameter), do NOT touch these.
- `src/strategy/momentum.py`: same as above.
- `src/strategy/stat_arb.py`: same as above.
- `src/strategy/meta.py`: same as above.
- `tests/test_backtest_engine.py`: existing tests must pass unchanged.

## Git workflow

- Branch: `advisor/007-optimize-backtest-slicing`
- Commit per step. Message style: `perf(backtest): <description>`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Verify plan 002 is complete

Before starting, confirm that plan 002 (backtest correctness bugs) has
been completed. Check `plans/README.md` for the status row of plan 002.
If it is not DONE, STOP and report: this plan depends on 002.

**Verify**: `grep "| 002 |" plans/README.md` shows `DONE` in the status
column. If not, stop and report.

### Step 2: Choose the approach: integer-index slicing with `.iloc`

The safest optimization that preserves look-ahead protection is to
replace `data[s].loc[:timestamp]` (which copies and does a label-based
scan) with `data[s].iloc[:row_count]` (which returns a view or shallow
copy and uses integer position).

To do this, precompute for each symbol the integer row index
corresponding to each timestamp. Build a mapping once before the loop:

```python
# Precompute integer index positions for each symbol
symbol_indices: dict[str, dict[pd.Timestamp, int]] = {}
for symbol in symbols:
    df = data[symbol]
    symbol_indices[symbol] = {ts: i for i, ts in enumerate(df.index)}
```

Then in the loop, instead of:

```python
data_up_to = {s: data[s].loc[:timestamp] for s in symbols if timestamp in data[s].index}
```

Use:

```python
data_up_to = {}
for s in symbols:
    if timestamp in symbol_indices[s]:
        row_count = symbol_indices[s][timestamp] + 1
        data_up_to[s] = data[s].iloc[:row_count]
```

`df.iloc[:row_count]` returns a view (not a copy) in pandas when the
dtypes are homogeneous, which avoids the O(n * symbols * df_size) copy.
Even when pandas returns a copy, `.iloc` is faster than `.loc[:label]`
because it avoids the label-based binary search.

CRITICAL: look-ahead protection is preserved because `row_count` is
`current_row_index + 1`, so only rows up to and including the current
timestamp are exposed. The strategy never sees rows beyond
`row_count`.

**Verify**: `ruff check src/backtest/engine.py` exits 0.

### Step 3: Keep the strategy interface unchanged

The `generate_signals` method signature in `src/strategy/base.py` stays
as `data: dict[str, pd.DataFrame]`. The strategies receive a DataFrame
that is a view/slice up to the current bar. They already use `len(df)`,
`df["close"]`, `df.index[-1]`, `.iloc[-1]`, `.tail()`, `.pct_change()`,
all of which work correctly on a view.

Do NOT change `src/strategy/base.py` unless a test fails because a
strategy received a view instead of a copy and broke. In that case, see
the STOP condition.

**Verify**: `ruff check src/strategy/base.py` exits 0 (should be
unchanged, so this is a sanity check).

### Step 4: Run the full backtest test suite

**Verify**: `pytest tests/test_backtest_engine.py -v` exits 0, all 10
tests pass. Pay special attention to:
- `test_stop_loss_triggers`: validates exit logic still works.
- `test_take_profit_triggers`: validates exit logic still works.
- `test_equity_curve_is_built`: validates the loop runs all bars.
- `test_multiple_symbols`: validates multi-symbol slicing.
- `test_momentum_strategy_in_backtest`: validates a real strategy works
  with the new slicing.

If any of these fail, check whether the strategy received a view and
broke on it. If so, STOP and report (see STOP conditions).

### Step 5: Run lint and type checks

**Verify**:
- `ruff check src/backtest/engine.py src/strategy/base.py` exits 0.
- `mypy src/backtest/engine.py src/strategy/base.py` exits 0.

## Test plan

No new test files are created. The existing
`tests/test_backtest_engine.py` (10 tests) must all pass unchanged.
This validates that the optimization preserves behavior, including:
- Signal generation works with views.
- Stop loss and take profit exits trigger correctly.
- Equity curve is built for every bar.
- Multiple symbols work.
- The real `MomentumStrategy` works end to end.

The key regression risk is look-ahead bias: if the slicing exposes
future data, backtest results would change (typically improve
artificially). The existing `test_positive_return_in_uptrend` and
`test_fees_reduce_returns` tests provide a behavioral baseline. If
returns change significantly after this optimization, that is a red
flag for look-ahead leakage.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_backtest_engine.py -v` exits 0, all 10 tests
      pass.
- [ ] `ruff check src/backtest/engine.py src/strategy/base.py` exits 0.
- [ ] `mypy src/backtest/engine.py src/strategy/base.py` exits 0.
- [ ] `grep -n "data\[s\]\.loc\[:timestamp\]" src/backtest/engine.py`
      returns no matches (the old slicing pattern is gone).
- [ ] No files outside `src/backtest/engine.py` and
      `src/strategy/base.py` are modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back (do not improvise) if:

- The code at `src/backtest/engine.py:83-99` does not match the excerpt
  in "Current state" (the codebase has drifted, or plan 002 changed it).
- Plan 002 is not DONE (check `plans/README.md`).
- Any strategy in `src/strategy/` depends on receiving a copy (not a
  view) of the DataFrame. Signs: a test fails with a
  `SettingWithCopyWarning` or a `ValueError` about modifying a view, or
  a strategy mutates the DataFrame (e.g. `df["new_col"] = ...`). If
  this happens, STOP and report which strategy and which line. Do NOT
  add `.copy()` calls to work around it: that would defeat the
  optimization.
- A step's verification fails twice after a reasonable fix attempt.
- The backtest results (total_return, num_trades) change significantly
  after the optimization on the same test data, which would indicate
  look-ahead leakage or a slicing bug.
- The fix appears to require touching an out-of-scope file (e.g. a
  strategy file needs modification to work with views).

## Maintenance notes

- If a new strategy is added that mutates the DataFrame passed to
  `generate_signals`, it will break with the view-based approach. New
  strategies must treat the input DataFrame as read-only. Document this
  in the `BaseStrategy.generate_signals` docstring.
- If the backtest engine is ever vectorized (as the original design
  intended with VectorBT), this slicing optimization becomes moot. See
  the decision in `AGENTS.md`: "VectorBT como engine de backtest
  principal". This plan is a stopgap for the current bar-by-bar loop.
- A reviewer should scrutinize: (1) that `row_count` is always
  `current_index + 1` (off-by-one would cause look-ahead or missing
  data), (2) that the `symbol_indices` precomputation handles symbols
  with different date ranges correctly, (3) that no strategy mutates
  the passed DataFrame.
