# Plan 006: Add chunked Parquet reading with column filtering

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report: do not improvise. When done, update the status row for this plan
> in `plans/README.md`: unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- src/data/parquet_store.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

`ParquetStore.read()` loads every Parquet file for a symbol fully into
memory with `pd.read_parquet(f)`, then concatenates all of them before
filtering by date range. For a symbol with years of 5-minute data (over
100,000 rows per month, millions per year), this causes OOM risk and
wasted I/O on columns the caller never uses. Switching to the pyarrow
ParquetDataset API with column projection and row-group filtering lets
pandas read only the needed columns and partitions, cutting memory usage
by 5x to 10x for typical analysis workloads that only need `open_time`
and `close`.

## Current state

The relevant files:

- `src/data/parquet_store.py`: Parquet I/O store. The `read` method
  (lines 64-91) is the target. It already imports `pyarrow.parquet as pq`
  (line 11) and `pyarrow as pa` (line 10).

Code as it exists today (`src/data/parquet_store.py:64-91`):

```python
def read(
    self,
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """Read OHLCV data from Parquet, optionally filtered by date range."""
    symbol_dir = self.base_dir / symbol / timeframe
    if not symbol_dir.exists():
        return pd.DataFrame(columns=KLINE_COLUMNS)

    parquet_files = list(symbol_dir.rglob("*.parquet"))
    if not parquet_files:
        return pd.DataFrame(columns=KLINE_COLUMNS)

    dfs = [pd.read_parquet(f) for f in parquet_files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values("open_time").drop_duplicates(subset=["open_time"]).reset_index(drop=True)

    if start:
        start_dt = pd.Timestamp(start, tz="UTC")
        df = df[df["open_time"] >= start_dt]
    if end:
        end_dt = pd.Timestamp(end, tz="UTC")
        df = df[df["open_time"] <= end_dt]

    return df.reset_index(drop=True)
```

The partition layout (from `_get_partition_dir`, line 27):

```python
def _get_partition_dir(self, symbol: str, timeframe: str, year: int, month: int) -> Path:
    return self.base_dir / symbol / timeframe / f"year={year}" / f"month={month:02d}"
```

So files live under `base_dir/symbol/timeframe/year=YYYY/month=MM/*.parquet`.
The `year=` and `month=` directory names are Hive-style partitions that
pyarrow can use for partition pruning.

`KLINE_COLUMNS` is defined at line 13:

```python
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote",
]
```

Repo conventions (from `AGENTS.md`):

- Python 3.11+, type hints required.
- 4-space indent, 120 char max line.
- Functions max 30 lines (ideal < 15). Extract helpers if needed.
- snake_case for functions/variables, PascalCase for classes.
- NUNCA usar travessao (em-dash). Use ":" or "." or "," instead.
- Error handling: raise with context (which symbol, which period). No
  empty `except: pass`.

Exemplar for test structure: `tests/test_parquet_store.py` uses
`tmp_path` fixture, synthetic data with `rng = np.random.default_rng(seed=42)`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests   | `pytest tests/test_parquet_store.py -v` | all pass, exit 0 |
| Lint    | `ruff check src/data/parquet_store.py` | exit 0, no errors |
| Type    | `mypy src/data/parquet_store.py` | exit 0, no errors |

## Scope

**In scope** (the only files you should modify):
- `src/data/parquet_store.py`

**Out of scope** (do NOT touch):
- `tests/test_parquet_store.py`: existing tests must keep passing unchanged.
  They verify behavior, not implementation.
- `scripts/download_historical.py`: uses `ParquetStore.write` only, not
  `read`.
- Any other file in `src/` or `scripts/`.

## Git workflow

- Branch: `advisor/006-chunked-parquet-reading`
- Commit per step. Message style: `perf(parquet_store): <description>`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add a `columns` parameter to `read()`

Add an optional `columns: Optional[list[str]] = None` parameter to the
`read` method signature, after `end`. When `columns` is `None`, read all
columns (current behavior). When provided, only those columns plus
`open_time` are read from disk.

The signature becomes:

```python
def read(
    self,
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    columns: Optional[list[str]] = None,
) -> pd.DataFrame:
```

If `columns` is provided, always include `"open_time"` in the projection
list (needed for date filtering and sorting). Deduplicate if the caller
already included it.

**Verify**: `ruff check src/data/parquet_store.py` exits 0.

### Step 2: Replace `pd.read_parquet` list comprehension with pyarrow ParquetDataset

Replace the current read logic (lines 76-82 in the excerpt above) with a
pyarrow-based approach that:

1. Builds a `pyarrow.dataset.Dataset` from the partition directory using
   `pq.ParquetDataset` or `pa.dataset.dataset` with Hive partitioning.
   The directory structure uses `year=YYYY/month=MM` which pyarrow
   recognizes as Hive partitions automatically.
2. Applies a filter expression when `start` and/or `end` are provided,
   using `open_time >= start_dt` and `open_time <= end_dt` as
   `pyarrow.compute.field` filter expressions. This pushes the date
   filter into the scan, so only matching row groups are read.
3. Applies column projection when `columns` is provided, so only the
   needed columns are read from disk.
4. Reads the result into a pandas DataFrame with `.to_pandas()`.

Reference implementation shape (adapt as needed, keep functions under 30
lines by extracting helpers):

```python
import pyarrow.dataset as ds
import pyarrow.compute as pc

def _build_filter(
    self, start: Optional[str], end: Optional[str]
) -> Optional[pc.Expression]:
    """Build a pyarrow filter expression for the date range."""
    filters = []
    if start:
        start_dt = pd.Timestamp(start, tz="UTC")
        filters.append(pc.field("open_time") >= start_dt.asm8)
    if end:
        end_dt = pd.Timestamp(end, tz="UTC")
        filters.append(pc.field("open_time") <= end_dt.asm8)
    if not filters:
        return None
    expr = filters[0]
    for f in filters[1:]:
        expr = expr & f
    return expr

def _resolve_columns(self, columns: Optional[list[str]]) -> Optional[list[str]]:
    """Ensure open_time is always in the projection list."""
    if columns is None:
        return None
    result = list(columns)
    if "open_time" not in result:
        result.insert(0, "open_time")
    return result
```

Then in `read`:

```python
    dataset = ds.dataset(
        str(symbol_dir),
        format="parquet",
        partitioning="hive",
    )
    filter_expr = self._build_filter(start, end)
    proj_cols = self._resolve_columns(columns)

    table = dataset.to_table(
        filter=filter_expr,
        columns=proj_cols,
    )
    df = table.to_pandas()
```

Keep the existing post-read logic: sort by `open_time`, drop duplicates
on `open_time`, reset index. The date filtering is now done by pyarrow
but keeping the pandas-side filter as a safety net is acceptable (it is
cheap on the already-filtered set).

IMPORTANT: if `parquet_files` is empty (no files found), return an empty
DataFrame with `KLINE_COLUMNS` (or the requested columns) as before.
Check `symbol_dir.exists()` and whether any `.parquet` files exist
before constructing the dataset, to avoid pyarrow errors on empty dirs.

**Verify**: `pytest tests/test_parquet_store.py -v` exits 0, all tests
pass. `ruff check src/data/parquet_store.py` exits 0.

### Step 3: Verify column filtering works end to end

Run a quick manual check that the new `columns` parameter works. Add a
temporary inline check (do NOT commit a new test file, just verify):

```bash
python -c "
from src.data.parquet_store import ParquetStore
import pandas as pd, numpy as np, tempfile, os
rng = np.random.default_rng(seed=42)
n = 100
ts = pd.date_range('2024-01-01', periods=n, freq='5min', tz='UTC')
df = pd.DataFrame({
    'open_time': ts, 'open': rng.uniform(40000,42000,n),
    'high': rng.uniform(42000,43000,n), 'low': rng.uniform(39000,40000,n),
    'close': rng.uniform(40000,42000,n), 'volume': rng.uniform(1,100,n),
    'close_time': ts + pd.Timedelta(minutes=5),
    'quote_volume': rng.uniform(50000,500000,n),
    'trades': rng.integers(10,500,n),
    'taker_buy_base': rng.uniform(0.5,50,n),
    'taker_buy_quote': rng.uniform(25000,250000,n),
})
with tempfile.TemporaryDirectory() as d:
    s = ParquetStore(base_dir=d)
    s.write('BTCUSDT','5m',df)
    out = s.read('BTCUSDT','5m',columns=['close'])
    print('Columns:', list(out.columns))
    assert 'close' in out.columns
    assert 'open_time' in out.columns
    assert 'open' not in out.columns
    print('OK: column filtering works')
"
```

**Verify**: the script prints `OK: column filtering works` and exits 0.

### Step 4: Run full verification suite

**Verify**:
- `pytest tests/test_parquet_store.py -v` exits 0, all tests pass.
- `ruff check src/data/parquet_store.py` exits 0.
- `mypy src/data/parquet_store.py` exits 0.

## Test plan

No new test files are created in this plan. The existing
`tests/test_parquet_store.py` (11 tests covering write, read, date range
filtering, idempotency, roundtrip, available symbols, date range) must
all continue to pass unchanged. This validates that the refactor
preserves behavior.

If a reviewer wants explicit coverage of the new `columns` parameter,
that can be added as a follow-up, but it is out of scope here to avoid
touching test files.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_parquet_store.py -v` exits 0, all tests pass.
- [ ] `ruff check src/data/parquet_store.py` exits 0.
- [ ] `mypy src/data/parquet_store.py` exits 0.
- [ ] `grep -n "pd.read_parquet(f)" src/data/parquet_store.py` returns no
      matches (the old full-read pattern is gone).
- [ ] No files outside `src/data/parquet_store.py` are modified
      (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back (do not improvise) if:

- The code at `src/data/parquet_store.py:64-91` does not match the
  excerpt in "Current state" (the codebase has drifted).
- `pyarrow.dataset` is not available in the installed pyarrow version
  (check `python -c "import pyarrow.dataset"`). If it fails, report the
  pyarrow version and stop: the fallback approach would require a
  different plan.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- Existing tests in `tests/test_parquet_store.py` fail after the change
  and the failure is not a simple fix within `parquet_store.py`.

## Maintenance notes

- If new columns are added to the Parquet schema in the future, the
  `KLINE_COLUMNS` list and the `_resolve_columns` helper should be
  updated. The column projection only affects what is read from disk,
  not what is written.
- If partitioning scheme changes (e.g. adding `day=` partitions), the
  `partitioning="hive"` argument in `ds.dataset` should still work, but
  the date-range filter may need adjustment to leverage the new
  partition level.
- A reviewer should scrutinize: (1) that the pyarrow filter expression
  correctly handles timezone-aware timestamps, (2) that the empty-dir
  guard returns the right empty DataFrame shape, (3) that no
  `pd.read_parquet` calls remain in the `read` method.
