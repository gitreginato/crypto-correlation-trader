# Plan 010: Add correlation edge case tests (NaN, gaps, short series)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report: do not improvise. When done, update the status row for this plan
> in `plans/README.md`: unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- tests/test_correlation.py src/analysis/correlation.py`
> If either file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. Note: this plan modifies
> `tests/test_correlation.py` only. `src/analysis/correlation.py` is read
> only.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The existing correlation tests use perfectly aligned synthetic data:
200 rows, 4 columns, no NaN, no gaps, all series the same length. Real
crypto data has missing bars (exchange downtime), misaligned timestamps
(different listing dates), and short series (newly listed assets). The
correlation code uses `pandas.DataFrame.corr()` which handles NaN
pairwise, but this behavior is not tested. If a future change switches
to a different correlation method or adds preprocessing (e.g.
dropna()), the edge case behavior could silently change. This plan adds
explicit tests for NaN handling, non-overlapping indices, and short
series so the behavior is documented and protected against regressions.

## Current state

The relevant files:

- `tests/test_correlation.py`: existing test file, 103 lines, 9 tests.
  The `returns_df` fixture (line 9) generates perfect data: 200 rows,
  4 columns, no NaN, `pd.date_range` with no gaps.
- `src/analysis/correlation.py`: the module under test, 91 lines. Key
  methods:
  - `compute` (line 22): calls `returns.corr(method=self.method)`.
  - `compute_rolling` (line 33): loops `range(window, n, step)`, slices
    `returns.iloc[i-window:i]`, calls `.corr()`.
  - `to_distance_matrix` (line 56): `np.sqrt(np.clip(2*(1-corr), 0, None))`.
  - `get_edges` (line 70): iterates upper triangle, filters by
    threshold.

Existing fixture (`tests/test_correlation.py:9-27`):

```python
@pytest.fixture
def returns_df() -> pd.DataFrame:
    """Generate correlated return data for testing."""
    rng = np.random.default_rng(seed=42)
    n = 200
    ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    btc = rng.normal(0, 0.02, n)
    eth = btc * 0.8 + rng.normal(0, 0.01, n)
    sol = btc * 0.4 + rng.normal(0, 0.03, n)
    doge = rng.normal(0, 0.05, n)
    return pd.DataFrame({
        "BTCUSDT": btc,
        "ETHUSDT": eth,
        "SOLUSDT": sol,
        "DOGEUSDT": doge,
    }, index=ts)
```

Existing test class structure (`tests/test_correlation.py:30`):

```python
class TestCorrelationMatrix:
    def test_pearson_correlation(self, returns_df: pd.DataFrame):
        ...
```

`compute` method (`src/analysis/correlation.py:22-31`):

```python
    def compute(self, returns: pd.DataFrame) -> pd.DataFrame:
        return returns.corr(method=self.method)
```

`compute_rolling` method (`src/analysis/correlation.py:33-54`):

```python
    def compute_rolling(self, returns, window=30, step=1):
        results = {}
        n = len(returns)
        for i in range(window, n, step):
            window_data = returns.iloc[i - window : i]
            results[returns.index[i]] = window_data.corr(method=self.method)
        return results
```

Repo conventions (from `AGENTS.md`):

- Python 3.11+, type hints required.
- 4-space indent, 120 char max line.
- Functions max 30 lines (ideal < 15).
- Test data: fixtures with synthetic data (seed fixo).
- NUNCA usar travessao (em-dash). Use ":" or "." or "," instead.
- NUNCA simular ou fabricar dados de preco. Test data must be synthetic
  with fixed seed and marked as such.
- Correlacao: SEMPRE usar janela deslizante, nunca correlacao estatica
  sobre todo o periodo.

Exemplar: the existing `returns_df` fixture uses
`np.random.default_rng(seed=42)` for reproducibility. New fixtures must
follow the same pattern.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests   | `pytest tests/test_correlation.py -v` | all pass, exit 0 |
| Lint    | `ruff check tests/test_correlation.py` | exit 0 |

## Scope

**In scope** (the only file you should modify):
- `tests/test_correlation.py`

**Out of scope** (do NOT touch):
- `src/analysis/correlation.py`: only read it to understand the
  behavior. Do NOT modify it. If a bug is found (e.g. `compute_rolling`
  crashes on short data), report it but do not fix it.
- Any other file.

## Git workflow

- Branch: `advisor/010-correlation-edge-case-tests`
- Single commit. Message: `test(correlation): add edge case tests for
  NaN, gaps, and short series`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add a fixture for data with NaN values

Add a new fixture `returns_df_with_nan` after the existing `returns_df`
fixture. It should produce a DataFrame where some columns have NaN
values at specific positions, simulating missing bars:

```python
@pytest.fixture
def returns_df_with_nan() -> pd.DataFrame:
    """Returns data with NaN values in some columns (missing bars)."""
    rng = np.random.default_rng(seed=42)
    n = 200
    ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    btc = rng.normal(0, 0.02, n)
    eth = btc * 0.8 + rng.normal(0, 0.01, n)
    sol = btc * 0.4 + rng.normal(0, 0.03, n)
    doge = rng.normal(0, 0.05, n)

    # Insert NaN: SOL missing 10 bars in the middle, DOGE missing 5 at start
    sol[95:105] = np.nan
    doge[:5] = np.nan

    return pd.DataFrame({
        "BTCUSDT": btc,
        "ETHUSDT": eth,
        "SOLUSDT": sol,
        "DOGEUSDT": doge,
    }, index=ts)
```

**Verify**: `ruff check tests/test_correlation.py` exits 0.

### Step 2: Add a fixture for non-overlapping indices

Add a fixture `returns_df_misaligned` where two columns have
non-overlapping date ranges (simulating different listing dates):

```python
@pytest.fixture
def returns_df_misaligned() -> pd.DataFrame:
    """Returns data with non-overlapping indices for some columns."""
    rng = np.random.default_rng(seed=42)
    # BTC: full range
    ts_btc = pd.date_range("2024-01-01", periods=200, freq="1D", tz="UTC")
    btc = rng.normal(0, 0.02, 200)
    eth = btc * 0.8 + rng.normal(0, 0.01, 200)
    # SOL: starts 50 days later
    ts_sol = pd.date_range("2024-02-20", periods=150, freq="1D", tz="UTC")
    sol = rng.normal(0, 0.03, 150)

    df = pd.DataFrame({
        "BTCUSDT": btc,
        "ETHUSDT": eth,
    }, index=ts_btc)
    df["SOLUSDT"] = pd.Series(sol, index=ts_sol)
    return df
```

This creates a DataFrame where SOLUSDT has NaN for the first 50 rows
(because its index starts later) and BTCUSDT/ETHUSDT have NaN for the
last 0 rows (they cover the full range). When pandas aligns on the
union of indices, the non-overlapping parts become NaN.

**Verify**: `ruff check tests/test_correlation.py` exits 0.

### Step 3: Add a fixture for short series

Add a fixture `returns_df_short` with fewer rows than the typical
rolling window (e.g. 10 rows, window=30):

```python
@pytest.fixture
def returns_df_short() -> pd.DataFrame:
    """Returns data with very few rows (shorter than typical window)."""
    rng = np.random.default_rng(seed=42)
    n = 10
    ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({
        "BTCUSDT": rng.normal(0, 0.02, n),
        "ETHUSDT": rng.normal(0, 0.01, n),
    }, index=ts)
```

**Verify**: `ruff check tests/test_correlation.py` exits 0.

### Step 4: Add NaN handling tests

Add a new test class `TestCorrelationEdgeCases` after the existing
`TestCorrelationMatrix` class. Add these NaN tests:

1. `test_compute_with_nan_does_not_crash`: call
   `CorrelationMatrix(method="pearson").compute(returns_df_with_nan)`.
   Assert it returns a 4x4 DataFrame without raising.
2. `test_compute_with_nan_produces_valid_matrix`: assert the result is
   symmetric (or NaN-symmetric: `np.allclose(matrix.values,
   matrix.values.T, equal_nan=True)`). Assert the diagonal is 1.0
   (pandas `corr` always produces 1.0 on the diagonal even with NaN).
3. `test_compute_with_nan_btc_eth_still_correlated`: BTC and ETH have
   no NaN (only SOL and DOGE have NaN). Assert
   `matrix.loc["BTCUSDT", "ETHUSDT"] > 0.7` (the correlation should be
   unaffected by NaN in other columns because pandas uses pairwise
   deletion).
4. `test_compute_with_all_nan_column`: create a DataFrame where one
   column is entirely NaN. Assert `compute` does not crash and the
   correlation for that column is NaN (pandas returns NaN when a
   column has zero variance or all NaN).

```python
class TestCorrelationEdgeCases:
    def test_compute_with_nan_does_not_crash(self, returns_df_with_nan):
        cm = CorrelationMatrix(method="pearson")
        matrix = cm.compute(returns_df_with_nan)
        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (4, 4)
```

**Verify**: `pytest tests/test_correlation.py::TestCorrelationEdgeCases -k nan -v`
exits 0, all 4 NaN tests pass.

### Step 5: Add non-overlapping index tests

Add these tests to `TestCorrelationEdgeCases`:

5. `test_compute_with_misaligned_indices_does_not_crash`: call
   `compute(returns_df_misaligned)`. Assert it returns a 3x3 DataFrame
   without raising.
6. `test_compute_with_misaligned_btc_eth_correlation`: BTC and ETH
   share the full index. Assert their correlation is still high
   (`> 0.7`).
7. `test_compute_with_misaligned_sol_has_nan_correlation_or_valid`:
   SOL overlaps with BTC/ETH for 150 days. Assert the SOL-BTC
   correlation is a valid float (not NaN), because there is overlap.
   If it is NaN, that would indicate no overlap, which is a bug in the
   test data.

**Verify**: `pytest tests/test_correlation.py::TestCorrelationEdgeCases -k misaligned -v`
exits 0, all 3 misaligned tests pass.

### Step 6: Add short series tests

Add these tests to `TestCorrelationEdgeCases`:

8. `test_compute_short_series_does_not_crash`: call
   `compute(returns_df_short)`. Assert it returns a 2x2 DataFrame
   with 1.0 on the diagonal.
9. `test_rolling_with_window_larger_than_data_returns_empty`: call
   `compute_rolling(returns_df_short, window=30)`. Assert the result
   is an empty dict (because `range(30, 10, 1)` produces no
   iterations).
10. `test_rolling_with_window_equal_to_data_returns_empty`: call
    `compute_rolling(returns_df_short, window=10)`. Assert the result
    is an empty dict (because `range(10, 10, 1)` produces no
    iterations).
11. `test_rolling_with_window_smaller_than_data_returns_results`:
    call `compute_rolling(returns_df_short, window=5)`. Assert the
    result dict has entries (because `range(5, 10, 1)` produces 5
    iterations).

**Verify**: `pytest tests/test_correlation.py::TestCorrelationEdgeCases -k short -v`
exits 0, all 4 short series tests pass.

### Step 7: Add edge case tests for `to_distance_matrix` and `get_edges`

Add these tests to `TestCorrelationEdgeCases`:

12. `test_distance_matrix_with_nan_correlation`: compute correlation
    on `returns_df_with_nan`, then call `to_distance_matrix`. Assert
    it does not crash and the diagonal is 0.0 (or NaN where corr is
    NaN). The `np.clip` in the code prevents negative values, so
    assert all non-NaN values are >= 0.
13. `test_get_edges_with_nan_correlation`: compute correlation on
    `returns_df_with_nan`, call `get_edges(matrix, threshold=0.5)`.
    Assert it returns a list (may be empty if no pairs exceed
    threshold). Assert no edge has a NaN correlation value.
14. `test_get_edges_empty_matrix`: call `get_edges` on a 1x1
    correlation matrix. Assert it returns an empty list (no pairs in
    a 1-asset matrix).

**Verify**: `pytest tests/test_correlation.py::TestCorrelationEdgeCases -k "distance or edges" -v`
exits 0, all 3 tests pass.

### Step 8: Run the full test suite and lint

**Verify**:
- `pytest tests/test_correlation.py -v` exits 0, all tests pass
  (existing 9 + new 14 = 23 total).
- `ruff check tests/test_correlation.py` exits 0.

## Test plan

Modified file: `tests/test_correlation.py`. New fixtures and tests:

New fixtures:
- `returns_df_with_nan`: 200 rows, 4 columns, NaN in SOL (rows 95-104)
  and DOGE (rows 0-4).
- `returns_df_misaligned`: BTC/ETH full 200-day range, SOL starts 50
  days later (150 rows).
- `returns_df_short`: 10 rows, 2 columns.

New test class `TestCorrelationEdgeCases` (14 tests):
- NaN handling (4 tests): no crash, valid matrix, BTC-ETH unaffected,
  all-NaN column.
- Misaligned indices (3 tests): no crash, BTC-ETH correlation, SOL
  overlap correlation.
- Short series (4 tests): no crash, rolling window > data, rolling
  window = data, rolling window < data.
- Distance/edges with NaN (3 tests): distance matrix with NaN, edges
  with NaN, edges on 1x1 matrix.

Structural pattern: model after the existing `TestCorrelationMatrix`
class in the same file. Use `@pytest.fixture` for data, class-based
test grouping, `np.random.default_rng(seed=42)` for reproducibility.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_correlation.py -v` exits 0, all tests pass
      (23 total: 9 existing + 14 new).
- [ ] `ruff check tests/test_correlation.py` exits 0.
- [ ] `grep -c "def test_" tests/test_correlation.py` returns at least
      23.
- [ ] No files outside `tests/test_correlation.py` are modified
      (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back (do not improvise) if:

- `tests/test_correlation.py` lines 1-103 do not match the excerpts in
  "Current state" (the file has drifted, new tests were added, or the
  fixture changed).
- `src/analysis/correlation.py` lines 22-91 do not match the excerpts
  (the `compute`, `compute_rolling`, `to_distance_matrix`, or
  `get_edges` methods changed).
- `compute` raises an exception on data with NaN (this would mean
  `pandas.corr` behavior changed or the code was modified to add
  preprocessing). Report the exception and stop.
- `compute_rolling` crashes on short data with an `IndexError` or
  similar (this would be a bug in the code). Report it but do NOT fix
  it (out of scope). Adjust the test to expect the crash if it is the
  current behavior, or STOP if the crash prevents meaningful testing.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching `src/analysis/correlation.py`
  (out of scope).

## Maintenance notes

- These tests document the current behavior of `pandas.corr` with NaN
  (pairwise deletion). If the code is ever changed to use
  `dropna()` before correlation, these tests will catch the behavior
  change.
- The `returns_df_misaligned` fixture tests index alignment. If the
  code is changed to reindex or resample before correlation, the
  expected behavior may change.
- The short series tests document that `compute_rolling` returns an
  empty dict when the window is >= the data length. This is the
  current behavior of `range(window, n, step)` when `window >= n`. If
  the loop bounds change, these tests must be updated.
- A reviewer should scrutinize: (1) that NaN tests use
  `equal_nan=True` in `np.allclose` comparisons, (2) that the
  misaligned fixture actually produces non-overlapping indices (verify
  with `df.isna().sum()`), (3) that no test fabricates price data (all
  fixtures generate returns, not prices, consistent with the existing
  fixture).
