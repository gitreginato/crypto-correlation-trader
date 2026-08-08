# Plan 005: Vectorize pandas hotspots (iterrows + rolling correlation)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/analyze_live.py src/analysis/correlation.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

Two pandas hotspots use slow Python-level loops where vectorized C/Cython
operations are available. First, `calc_volume_profile` in
`scripts/analyze_live.py` uses `iterrows()` to assign each trade to a
price bin one row at a time. For a DataFrame with thousands of trades,
this is 10-100x slower than `pd.cut` + `groupby`. Second,
`CorrelationMatrix.compute_rolling` in `src/analysis/correlation.py`
recomputes the full correlation matrix from scratch for each window by
slicing and calling `.corr()`. For M assets and W windows, this is
O(W * M^2 * window_size) in Python. Using `returns.rolling(window).corr()`
pushes the inner loop into pandas' C/Cython code and is dramatically
faster. Both functions are called frequently in the analysis pipeline, so
the speedup compounds.

## Current state

The relevant files and their roles:

- `scripts/analyze_live.py` (1945 lines): live market analysis dashboard.
  Contains `calc_volume_profile` (line 164).
- `src/analysis/correlation.py` (91 lines): `CorrelationMatrix` class with
  `compute` and `compute_rolling` methods.

### Finding 1: iterrows in calc_volume_profile

`scripts/analyze_live.py:164-199`:
```python
def calc_volume_profile(trades: pd.DataFrame, bins: int = 50) -> Dict:
    if trades.empty:
        return {}
    
    price_min = trades['price'].min()
    price_max = trades['price'].max()
    bin_edges = np.linspace(price_min, price_max, bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    volume_profile = np.zeros(bins)
    for _, row in trades.iterrows():
        idx = np.searchsorted(bin_edges, row['price']) - 1
        if 0 <= idx < bins:
            volume_profile[idx] += row['quantity']
    
    poc_idx = np.argmax(volume_profile)
    poc_price = bin_centers[poc_idx]
    
    total_vol = volume_profile.sum()
    target_vol = total_vol * 0.7
    cum_vol = volume_profile[poc_idx]
    low_idx = high_idx = poc_idx
    
    while cum_vol < target_vol and (low_idx > 0 or high_idx < bins - 1):
        if low_idx > 0 and (high_idx >= bins - 1 or volume_profile[low_idx-1] >= volume_profile[high_idx+1]):
            low_idx -= 1
            cum_vol += volume_profile[low_idx]
        elif high_idx < bins - 1:
            high_idx += 1
            cum_vol += volume_profile[high_idx]
        else:
            break
    
    return {
        'poc_price': float(poc_price),
        'vah_price': float(bin_centers[high_idx]),
```

The slow part is lines 173-177: the `iterrows()` loop that accumulates
quantity into bins. The rest (the Value Area calculation) operates on the
already-computed `volume_profile` array and is fine.

### Finding 2: rolling correlation recomputed from scratch

`src/analysis/correlation.py:33-54`:
```python
    def compute_rolling(
        self,
        returns: pd.DataFrame,
        window: int = 30,
        step: int = 1,
    ) -> dict[pd.Timestamp, pd.DataFrame]:
        """Compute rolling correlation matrices over time.

        Args:
            returns: DataFrame of asset returns.
            window: Rolling window size (number of periods).
            step: Step size between windows (to reduce computation).

        Returns:
            Dict mapping the end-timestamp of each window to its correlation matrix.
        """
        results: dict[pd.Timestamp, pd.DataFrame] = {}
        n = len(returns)
        for i in range(window, n, step):
            window_data = returns.iloc[i - window : i]
            results[returns.index[i]] = window_data.corr(method=self.method)
        return results
```

The slow part: for each window, `returns.iloc[i - window : i].corr()`
recomputes the full pairwise correlation from scratch. For a DataFrame
with M columns and N rows, each `.corr()` call is O(M^2 * window). With
`step=1`, this is called N-window times.

The vectorized alternative: `returns.rolling(window).corr()` computes all
rolling pairwise correlations in one call using pandas' C/Cython
implementation. It returns a MultiIndex DataFrame (level 0 = timestamp,
level 1 = asset). We then sample every `step`-th timestamp to match the
existing `step` behavior.

Repo conventions (from `AGENTS.md`):
- Python 3.11+, 4-space indent, 120 char lines, functions max 30 lines.
- `numpy` and `pandas` are already imported in both files.
- Correlation rule: "SEMPRE usar janela deslizante, nunca correlacao
  estatica sobre todo o periodo". This plan preserves sliding windows.

## Commands you will need

| Purpose   | Command                                              | Expected on success |
|-----------|------------------------------------------------------|---------------------|
| Tests     | `pytest tests/test_correlation.py -v`                | all pass            |
| Lint      | `ruff check src/analysis/correlation.py`             | exit 0              |
| Lint      | `ruff check scripts/analyze_live.py`                 | exit 0              |
| Typecheck | `mypy src/analysis/correlation.py`                   | exit 0              |

## Scope

**In scope** (the only files you should modify):
- `scripts/analyze_live.py`
- `src/analysis/correlation.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/backtest/engine.py` (loop slicing optimization is plan 007).
- Any other file in `src/` or `scripts/`.
- Do not change the function signatures or return types. The output must
  be identical in structure to the current implementation.

## Git workflow

- Branch: `advisor/005-vectorize-pandas-hotspots`
- Commit per file or per finding. Message style: conventional commits,
  e.g. `perf(analysis): vectorize rolling correlation with pandas
  rolling.corr`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Vectorize calc_volume_profile in scripts/analyze_live.py

Replace the `iterrows()` loop (lines 173-177) with a vectorized
`pd.cut` + `groupby` approach. The current code:
```python
    volume_profile = np.zeros(bins)
    for _, row in trades.iterrows():
        idx = np.searchsorted(bin_edges, row['price']) - 1
        if 0 <= idx < bins:
            volume_profile[idx] += row['quantity']
```

Replace with:
```python
    bin_indices = pd.cut(
        trades["price"], bins=bin_edges, include_lowest=True, labels=False
    )
    valid = bin_indices.notna()
    volume_profile = (
        trades.loc[valid, "quantity"]
        .groupby(bin_indices[valid])
        .sum()
        .reindex(range(bins), fill_value=0.0)
        .to_numpy()
    )
```

This produces the same `volume_profile` array: quantity summed per bin,
with zeros for empty bins. The `include_lowest=True` ensures the minimum
price is included in the first bin (matching the `np.searchsorted` behavior
where `idx = 0` for the lowest price). The `labels=False` returns integer
bin indices. The `reindex(range(bins), fill_value=0.0)` ensures all bins
are present even if no trades fall in them.

Do NOT change the Value Area calculation (lines 179-195) or the return
dict. Only replace the loop.

**Verify**: `ruff check scripts/analyze_live.py` -> exit 0

### Step 2: Verify volume_profile output matches

Run a quick equivalence check to confirm the vectorized version produces
the same result as the old loop for a synthetic dataset:
```bash
python -c "
import numpy as np
import pandas as pd
np.random.seed(42)
trades = pd.DataFrame({
    'price': np.random.uniform(100, 200, 1000),
    'quantity': np.random.uniform(0.1, 5.0, 1000),
})
bins = 50
price_min = trades['price'].min()
price_max = trades['price'].max()
bin_edges = np.linspace(price_min, price_max, bins + 1)

# Old method
vp_old = np.zeros(bins)
for _, row in trades.iterrows():
    idx = np.searchsorted(bin_edges, row['price']) - 1
    if 0 <= idx < bins:
        vp_old[idx] += row['quantity']

# New method
bin_indices = pd.cut(trades['price'], bins=bin_edges, include_lowest=True, labels=False)
valid = bin_indices.notna()
vp_new = trades.loc[valid, 'quantity'].groupby(bin_indices[valid]).sum().reindex(range(bins), fill_value=0.0).to_numpy()

assert np.allclose(vp_old, vp_new), f'Mismatch: {vp_old} vs {vp_new}'
print('OK: volume profiles match')
"
```

**Verify**: the command prints `OK: volume profiles match` and exits 0. If
it does not match, STOP and report. The mismatch likely means the bin
boundary handling differs; adjust `include_lowest` or the edge case
handling until they match.

### Step 3: Vectorize compute_rolling in src/analysis/correlation.py

Replace the `compute_rolling` method (lines 33-54) with a vectorized
implementation using `returns.rolling(window).corr()`.

The current method:
```python
    def compute_rolling(
        self,
        returns: pd.DataFrame,
        window: int = 30,
        step: int = 1,
    ) -> dict[pd.Timestamp, pd.DataFrame]:
        results: dict[pd.Timestamp, pd.DataFrame] = {}
        n = len(returns)
        for i in range(window, n, step):
            window_data = returns.iloc[i - window : i]
            results[returns.index[i]] = window_data.corr(method=self.method)
        return results
```

Replace with:
```python
    def compute_rolling(
        self,
        returns: pd.DataFrame,
        window: int = 30,
        step: int = 1,
    ) -> dict[pd.Timestamp, pd.DataFrame]:
        rolling_corr = returns.rolling(window, min_periods=window).corr(
            method=self.method
        )
        results: dict[pd.Timestamp, pd.DataFrame] = {}
        timestamps = returns.index[window::step]
        for ts in timestamps:
            matrix = rolling_corr.loc[ts]
            if isinstance(matrix, pd.Series):
                matrix = matrix.unstack()
            results[ts] = matrix
        return results
```

Explanation: `returns.rolling(window).corr()` returns a DataFrame with a
MultiIndex (level 0 = timestamp, level 1 = the asset column). For each
timestamp `ts`, `rolling_corr.loc[ts]` returns the correlation matrix for
that window. When there is only one asset, it returns a Series, so the
`unstack()` handles that edge case.

The `min_periods=window` ensures that windows with fewer than `window`
non-NaN values produce NaN correlations, matching the original behavior
(the original `iloc[i - window : i]` slice always has exactly `window`
rows, and `.corr()` skips NaN pairwise).

The `timestamps = returns.index[window::step]` samples every `step`-th
timestamp starting from index `window`, matching the original
`range(window, n, step)` indexing.

**Verify**: `ruff check src/analysis/correlation.py` -> exit 0

### Step 4: Verify rolling correlation output matches

Run an equivalence check:
```bash
python -c "
import numpy as np
import pandas as pd
np.random.seed(42)
returns = pd.DataFrame(
    np.random.randn(100, 3) * 0.02,
    columns=['A', 'B', 'C'],
    index=pd.date_range('2024-01-01', periods=100, freq='D'),
)

# Old method
results_old = {}
for i in range(30, 100, 1):
    window_data = returns.iloc[i - 30 : i]
    results_old[returns.index[i]] = window_data.corr()

# New method
rolling_corr = returns.rolling(30, min_periods=30).corr()
results_new = {}
for ts in returns.index[30::1]:
    matrix = rolling_corr.loc[ts]
    if isinstance(matrix, pd.Series):
        matrix = matrix.unstack()
    results_new[ts] = matrix

assert set(results_old.keys()) == set(results_new.keys()), 'Key mismatch'
for ts in results_old:
    old = results_old[ts]
    new = results_new[ts]
    assert old.shape == new.shape, f'Shape mismatch at {ts}: {old.shape} vs {new.shape}'
    assert np.allclose(old.values, new.values, equal_nan=True), f'Value mismatch at {ts}'
print('OK: rolling correlations match')
"
```

**Verify**: the command prints `OK: rolling correlations match` and exits
0. If it does not match, STOP and report. Check the `step` indexing and
the `min_periods` setting.

### Step 5: Full verification

**Verify**:
- `pytest tests/test_correlation.py -v` -> all pass
- `ruff check src/analysis/correlation.py scripts/analyze_live.py` -> exit 0
- `mypy src/analysis/correlation.py` -> exit 0

## Test plan

Existing tests in `tests/test_correlation.py` must continue to pass. If
they break, the vectorized output differs from the original, which is a
bug in the implementation, not the test. Fix the implementation.

If you want to add a regression test (optional, only if the operator
approves):
- `tests/test_correlation.py`: add a test that calls `compute_rolling`
  with a known small DataFrame and asserts the output dict has the correct
  keys and matrix shapes. Model after the existing test structure in that
  file.
- `tests/test_correlation.py`: add a test with `step=5` to verify the
  step sampling works correctly.

Verification: `pytest tests/test_correlation.py -v` -> all pass.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_correlation.py -v` exits 0
- [ ] `ruff check src/analysis/correlation.py scripts/analyze_live.py` exits 0
- [ ] `mypy src/analysis/correlation.py` exits 0
- [ ] `grep -n "iterrows" scripts/analyze_live.py` does NOT return a match in `calc_volume_profile` (line 174 area)
- [ ] `grep -n "for i in range(window" src/analysis/correlation.py` returns no matches
- [ ] The equivalence checks in steps 2 and 4 pass (outputs match)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.
- The equivalence check (step 2 or step 4) fails and cannot be reconciled.
  This means the vectorized version produces different results than the
  original, which is a correctness issue. Do not ship a faster version
  that gives wrong numbers.
- The fix appears to require touching an out-of-scope file.
- You discover that `compute_rolling` is called with a `step` value that
  does not evenly divide the data, and the `returns.index[window::step]`
  slicing produces different timestamps than the original
  `range(window, n, step)` indexing. (They should be equivalent, but if
  the index is not a simple RangeIndex, verify carefully.)

## Maintenance notes

- The `pd.cut` approach in `calc_volume_profile` handles the edge case
  where `price_min == price_max` (all trades at the same price) by putting
  all trades in the first bin. The original `np.searchsorted` approach had
  the same behavior. If this edge case matters, a future test should
  cover it.
- The `returns.rolling(window).corr()` approach uses more memory than the
  loop approach because it computes all rolling correlations at once
  (MultiIndex DataFrame of size N * M * M). For very large N or M, this
  could be significant. If memory becomes an issue, a future plan could
  add chunking. For the current use case (30-50 assets, hundreds to
  thousands of bars), this is fine.
- A reviewer should verify that the `min_periods=window` setting matches
  the original behavior. The original used `.iloc[i - window : i]` which
  always has exactly `window` rows, and `.corr()` does pairwise
  complete-obs. If the input has NaN values, the behavior should be
  identical, but verify with the equivalence check.
- Follow-up deferred: the `get_edges` method (line 70-91) uses a nested
  Python loop over the upper triangle. For large correlation matrices,
  `np.triu_indices` + vectorized comparison would be faster. This is low
  priority (M is typically 30-50) and out of scope for this plan.
