# Plan 013: Consolidate statistical/correlation analysis into src/

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/analyze_correlations.py scripts/statistical_analyzer.py scripts/analyze_microstructure.py src/analysis/correlation.py src/analysis/statistical.py src/analysis/microstructure.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: plans/011-extract-analyze-live-into-src-modules.md
- **Category**: tech-debt
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

Three analysis scripts (`analyze_correlations.py` 580 lines, `statistical_analyzer.py` 788 lines, `analyze_microstructure.py` 692 lines) contain significant logic that overlaps with `src/analysis/` modules but doesn't use them. This means the same computations exist in multiple places with subtly different implementations, making bug fixes and behavior changes require editing multiple files. Consolidating shared logic into `src/` modules and updating scripts to import from them eliminates duplication and ensures consistent behavior. The risk is that numerical results may change if the implementations differ, so this plan includes a STOP condition if results diverge.

## Current state

The relevant files, each with one line on its role:

- `scripts/analyze_correlations.py` (580 lines) : comprehensive correlation analysis across crypto assets. Computes Pearson/Spearman correlations, lagged correlations, time-of-day patterns, lead-lag relationships, volatility/volume/drawdown correlations, regime-dependent correlations, cross-asset momentum. Outputs JSON.
- `scripts/statistical_analyzer.py` (788 lines) : advanced statistical analysis module. Has `MarketRegime` enum, `StatisticalResult`/`MicrostructureMetrics` dataclasses, and a class with methods for stationarity, autocorrelation, Hurst, half-life, regime detection (GMM), microstructure (VPIN, Kyle's lambda), volume profile, correlation, risk metrics.
- `scripts/analyze_microstructure.py` (692 lines) : microstructure analysis: taker buy/sell ratio, volume profile, gap analysis, wick analysis, round number clustering, order flow imbalance, accumulation/distribution, price magnetism, time-of-day order flow, candle anatomy.
- `src/analysis/correlation.py` (91 lines) : `CorrelationMatrix` class with `compute`, `compute_rolling`, `to_distance_matrix`, `extract_edges` methods.
- `src/analysis/statistical.py` : created in plan 011. Contains `test_stationarity_adf`, `test_stationarity_kpss`, `calc_hurst`, `calc_half_life`, `calc_var_cvar`, `calc_drawdowns`.
- `src/analysis/microstructure.py` : created in plan 011. Contains `calc_cvd`, `calc_kyle_lambda`, `calc_amihud`, `calc_volume_profile`, `calc_order_book_metrics`.

### Overlap analysis

**scripts/analyze_correlations.py vs src/analysis/correlation.py:**

`scripts/analyze_correlations.py:53-79` (`compute_return_correlations`) computes Pearson and Spearman correlation matrices manually:
```python
def compute_return_correlations(data: dict[str, pd.DataFrame]) -> dict:
    returns = pd.DataFrame({sym: df["close"].pct_change() for sym, df in data.items()})
    returns = returns.dropna()
    pearson_mat = returns.corr(method="pearson")
    spearman_mat = returns.corr(method="spearman")
    ...
```

`src/analysis/correlation.py:22-31` (`CorrelationMatrix.compute`) does the same:
```python
def compute(self, returns: pd.DataFrame) -> pd.DataFrame:
    return returns.corr(method=self.method)
```

The script computes returns inline; the `src/` module expects pre-computed returns. The consolidation is to have the script use `CorrelationMatrix` and `calculate_returns` from `src/analysis/`.

**scripts/statistical_analyzer.py vs src/analysis/statistical.py and src/strategy/regime_filter.py:**

`scripts/statistical_analyzer.py:200-248` (`hurst_exponent` method) duplicates `src/analysis/statistical.py:calc_hurst` (consolidated in plan 012).

`scripts/statistical_analyzer.py:260+` (`half_life_mean_reversion`) duplicates `src/analysis/statistical.py:calc_half_life`.

`scripts/statistical_analyzer.py` has stationarity tests (ADF, KPSS) that duplicate `src/analysis/statistical.py:test_stationarity_adf` and `test_stationarity_kpss`.

`scripts/statistical_analyzer.py` has a `MarketRegime` enum (lines 40-48) and regime detection via GMM (GaussianMixture) that overlaps with `src/strategy/regime_filter.py:RegimeFilter` (which uses entropy + Hurst). These are different approaches to regime detection and may not be directly consolidable.

**scripts/analyze_microstructure.py vs src/analysis/microstructure.py:**

`scripts/analyze_microstructure.py:49-80` (`compute_taker_buy_sell_ratio`) computes taker buy/sell ratio. This is related to but not identical to `src/analysis/microstructure.py:calc_cvd` (which computes cumulative volume delta from trades). The script works with OHLCV `taker_buy_base` column; the `src/` function works with trade-level data. These are different data formats and may not be directly consolidable.

`scripts/analyze_microstructure.py` has volume profile analysis that overlaps with `src/analysis/microstructure.py:calc_volume_profile` (which works with trade-level data, not OHLCV).

### Key constraint: numerical results must not change

The scripts produce JSON output that may be consumed by dashboards or reports. If consolidating changes the numerical results (even slightly, due to different default parameters or algorithms), downstream outputs will change. This plan includes a STOP condition: if numerical results change after consolidation, stop and report. It may be necessary to keep both implementations if they are genuinely different algorithms.

### Repo conventions that apply

- Python 3.11+, type hints required.
- 4-space indentation, 120 char max line length.
- `snake_case` for functions/variables, `PascalCase` for classes.
- Functions max 30 lines.
- Imports: stdlib first, third-party second, project imports third.
- No em-dash (the character `:`). Use `:`, `.`, or `,` instead.
- No hardcoded API keys or secrets.
- No `try/except pass` (empty catch).

## Commands you will need

| Purpose          | Command                              | Expected on success |
|------------------|--------------------------------------|---------------------|
| Tests            | `pytest tests/ -v`                   | all pass            |
| Lint             | `ruff check src/ scripts/`           | exit 0              |
| Type check       | `mypy src/`                          | exit 0 (or same as before) |

## Scope

**In scope** (the only files you should modify):
- `scripts/analyze_correlations.py` (modify to import from `src/`)
- `scripts/statistical_analyzer.py` (modify to import from `src/`)
- `scripts/analyze_microstructure.py` (modify to import from `src/`)
- `src/analysis/correlation.py` (may add helper functions if needed)
- `src/analysis/statistical.py` (may add helper functions if needed)
- `src/analysis/microstructure.py` (may add helper functions if needed)

**Out of scope** (do NOT touch):
- `scripts/analyze_live.py` : already refactored in plan 011.
- `scripts/generate_report.py`, `scripts/generate_scientific_report.py` : fixed in plan 012.
- `src/strategy/regime_filter.py` : different regime detection approach, not consolidated.
- Any test files.
- Any other scripts.

## Git workflow

- Branch: `advisor/013-consolidate-analysis-scripts`
- Commit per script consolidation. Message style: `refactor: consolidate <script> with src/analysis/ modules`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Audit overlap in scripts/analyze_correlations.py

Read `scripts/analyze_correlations.py` in full (580 lines). For each function, determine:

1. Does it duplicate a function in `src/analysis/correlation.py` or `src/analysis/returns.py`?
2. If yes, are the inputs/outputs compatible (same data format, same return structure)?
3. If compatible, can the script function be replaced with a call to the `src/` function?
4. If not compatible (different inputs/outputs), can a thin adapter be written?

Document the findings. The key functions to audit:

- `compute_return_correlations` (line 53) : uses `returns.corr(method="pearson")` and `returns.corr(method="spearman")`. Can use `CorrelationMatrix(method="pearson").compute(returns)` and `CorrelationMatrix(method="spearman").compute(returns)`.
- `compute_lagged_correlations` (search for it) : lagged cross-correlations. May overlap with `src/analysis/cross_sectional.py:cross_correlation` (from plan 011).
- Other functions (time-of-day patterns, day-of-week, volatility correlations, etc.) : likely unique to this script, no `src/` equivalent.

For functions that can be consolidated, replace the inline computation with a call to the `src/` function. For functions that are unique, leave them in the script.

**Verify**: `pytest tests/ -v` exits 0. `ruff check scripts/analyze_correlations.py` exits 0.

### Step 2: Consolidate scripts/analyze_correlations.py

For each function identified in step 1 as duplicating `src/` logic:

1. Add the appropriate import at the top of `scripts/analyze_correlations.py`:
```python
from src.analysis.correlation import CorrelationMatrix
from src.analysis.returns import calculate_returns
from src.analysis.cross_sectional import cross_correlation
```

2. Replace the inline computation with a call to the `src/` function. For example, in `compute_return_correlations`:
```python
# Before:
pearson_mat = returns.corr(method="pearson")
spearman_mat = returns.corr(method="spearman")

# After:
pearson_mat = CorrelationMatrix(method="pearson").compute(returns)
spearman_mat = CorrelationMatrix(method="spearman").compute(returns)
```

3. For `compute_lagged_correlations`, if it duplicates `cross_correlation` from `src/analysis/cross_sectional.py`, check if the return format matches. The `src/` function returns a dict with `correlations`, `lags`, `max_correlation`, `optimal_lag`. If the script expects a different format, write an adapter or keep the inline implementation. If the formats are incompatible and an adapter would be complex, STOP and report.

4. After each replacement, verify the function still produces the same output by running the script on test data (if available) or by manual inspection of the logic.

IMPORTANT: Do NOT change the JSON output format of the script. Downstream consumers (HTML dashboard) depend on the exact structure.

**Verify**: `pytest tests/ -v` exits 0. `ruff check scripts/analyze_correlations.py` exits 0. `python -c "import scripts.analyze_correlations; print('OK')"` prints `OK`, exit 0.

### Step 3: Audit overlap in scripts/statistical_analyzer.py

Read `scripts/statistical_analyzer.py` in full (788 lines). For each method, determine overlap with `src/analysis/statistical.py` (created in plan 011) and `src/strategy/regime_filter.py`.

Key methods to audit:

- `hurst_exponent` (line 200) : already consolidated in plan 012 (wraps `calc_hurst`).
- `half_life_mean_reversion` (line 260) : duplicates `src/analysis/statistical.py:calc_half_life`. Compare the implementations.
- Stationarity tests (ADF, KPSS) : duplicate `src/analysis/statistical.py:test_stationarity_adf` and `test_stationarity_kpss`.
- `var_cvar` or risk metrics : may duplicate `src/analysis/statistical.py:calc_var_cvar`.
- Regime detection via GMM (GaussianMixture) : different from `src/strategy/regime_filter.py:RegimeFilter` (which uses entropy + Hurst). Likely NOT consolidable.
- Microstructure metrics (VPIN, Kyle's lambda) : `calc_kyle_lambda` is in `src/analysis/microstructure.py`. VPIN may be unique.

For each duplicating method, check if the return format is compatible. The `src/` functions return plain dicts. The `statistical_analyzer.py` methods may return `StatisticalResult` dataclass instances (line 52) or dicts. If the return formats differ, an adapter is needed.

**Verify**: No code changes yet. This step is audit only. Document findings.

### Step 4: Consolidate scripts/statistical_analyzer.py

For each method identified in step 3 as duplicating `src/` logic with compatible return formats:

1. Add imports:
```python
from src.analysis.statistical import (
    test_stationarity_adf, test_stationarity_kpss, calc_hurst,
    calc_half_life, calc_var_cvar, calc_drawdowns,
)
from src.analysis.microstructure import calc_kyle_lambda, calc_amihud
```

2. Replace the method body with a call to the `src/` function, wrapping in an adapter if needed for return format compatibility.

3. For methods that return `StatisticalResult` dataclass (line 52), the adapter should construct a `StatisticalResult` from the dict returned by the `src/` function:
```python
def _to_statistical_result(result_dict: dict, test_name: str) -> StatisticalResult:
    return StatisticalResult(
        test_name=test_name,
        statistic=result_dict.get("statistic", 0.0),
        p_value=result_dict.get("p_value", 1.0),
        critical_values=result_dict.get("critical_values", {}),
        interpretation=result_dict.get("interpretation", ""),
        significant=result_dict.get("stationary", result_dict.get("significant", False)),
    )
```

4. For methods with incompatible return formats or different algorithms (e.g. GMM regime detection), leave them as-is and add a comment: `# NOTE: does not use src/analysis/ because <reason>`.

IMPORTANT: After each replacement, verify the method still produces the same numerical results. If results change, STOP and report.

**Verify**: `pytest tests/ -v` exits 0. `ruff check scripts/statistical_analyzer.py` exits 0. `python -c "import scripts.statistical_analyzer; print('OK')"` prints `OK`, exit 0.

### Step 5: Audit overlap in scripts/analyze_microstructure.py

Read `scripts/analyze_microstructure.py` in full (692 lines). For each function, determine overlap with `src/analysis/microstructure.py` (created in plan 011).

Key functions to audit:

- `compute_taker_buy_sell_ratio` (line 49) : works with OHLCV `taker_buy_base` column. `src/analysis/microstructure.py:calc_cvd` works with trade-level data (different input format). Likely NOT directly consolidable, but the logic (buy vs sell volume) is conceptually similar.
- Volume profile functions : `src/analysis/microstructure.py:calc_volume_profile` works with trade-level data. The script may work with OHLCV data. Check if the inputs are compatible.
- Other functions (gap analysis, wick analysis, round number clustering, etc.) : likely unique to this script.

For functions that work with different data formats (OHLCV vs trades), consolidation would require adding a new function to `src/analysis/microstructure.py` that accepts OHLCV data, or adapting the script to convert OHLCV to the trade-level format. If the data formats are fundamentally different, keep both implementations and add a comment explaining why.

**Verify**: No code changes yet. This step is audit only. Document findings.

### Step 6: Consolidate scripts/analyze_microstructure.py

For each function identified in step 5 as duplicating `src/` logic with compatible inputs:

1. Add imports:
```python
from src.analysis.microstructure import calc_cvd, calc_kyle_lambda, calc_amihud, calc_volume_profile
```

2. Replace inline computations with calls to `src/` functions.

3. For functions with incompatible data formats, leave them as-is with a comment: `# NOTE: uses OHLCV data, not trade-level data expected by src/analysis/microstructure.py`.

IMPORTANT: Do NOT change the JSON output format of the script.

**Verify**: `pytest tests/ -v` exits 0. `ruff check scripts/analyze_microstructure.py` exits 0. `python -c "import scripts.analyze_microstructure; print('OK')"` prints `OK`, exit 0.

### Step 7: Final verification

Run all verification commands:
```bash
pytest tests/ -v
ruff check src/ scripts/
mypy src/
```

Check that no new ruff or mypy errors were introduced.

Run import checks for all three modified scripts:
```bash
python -c "import scripts.analyze_correlations; print('OK')"
python -c "import scripts.statistical_analyzer; print('OK')"
python -c "import scripts.analyze_microstructure; print('OK')"
```

**Verify**: All commands exit 0. All three import checks print `OK`.

## Test plan

No new tests are written in this plan. The existing test suite must continue to pass. The key risk is numerical result changes, which is covered by the STOP condition.

If the operator wants to verify numerical correctness, they can run each script on test data before and after consolidation and diff the JSON output:
```bash
# Before consolidation (save baseline)
python scripts/analyze_correlations.py --output /tmp/baseline_corr.json
# After consolidation
python scripts/analyze_correlations.py --output /tmp/new_corr.json
diff /tmp/baseline_corr.json /tmp/new_corr.json
```

If the diff shows numerical differences (not just formatting), STOP and report.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/ -v` exits 0
- [ ] `ruff check src/ scripts/` exits 0
- [ ] `python -c "import scripts.analyze_correlations; print('OK')"` prints `OK`, exit 0
- [ ] `python -c "import scripts.statistical_analyzer; print('OK')"` prints `OK`, exit 0
- [ ] `python -c "import scripts.analyze_microstructure; print('OK')"` prints `OK`, exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts. Run `grep -n "def compute_return_correlations" scripts/analyze_correlations.py` and confirm it returns line 53. If not, STOP.
- Plan 011 has not been completed (the `src/analysis/` modules don't exist). Run `ls src/analysis/statistical.py src/analysis/microstructure.py src/analysis/cross_sectional.py`. If any are missing, STOP.
- Plan 012 has not been completed (the `hurst_exponent` wrapper in `statistical_analyzer.py` may not exist). Run `grep -n "calc_hurst" scripts/statistical_analyzer.py`. If no matches, plan 012 may not be done. Proceed with caution but report.
- Numerical results change after consolidation. This is the most important STOP condition. If the JSON output of any script differs from the pre-consolidation baseline (beyond formatting), STOP and report the differences. It may be necessary to keep both implementations.
- A function's input/output format is incompatible with the `src/` equivalent and an adapter would be complex (more than 10 lines). STOP and report, keep both implementations.
- The GMM regime detection in `scripts/statistical_analyzer.py` appears to overlap with `src/strategy/regime_filter.py:RegimeFilter`. These are different algorithms (GMM vs entropy+Hurst). Do NOT consolidate them. If you are unsure whether two regime detection approaches are the same, STOP and report.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- After this plan, the three analysis scripts should be thinner, delegating shared logic to `src/analysis/` modules. Functions that are unique to each script (e.g. time-of-day patterns in `analyze_correlations.py`, wick analysis in `analyze_microstructure.py`) remain in the scripts.
- If future analysis functions are needed, they should be added to `src/analysis/` modules, not to scripts. Scripts should be thin orchestration layers.
- The GMM regime detection in `scripts/statistical_analyzer.py` and the entropy+Hurst regime detection in `src/strategy/regime_filter.py` are intentionally kept separate. They serve different purposes: GMM is for exploratory analysis, `RegimeFilter` is for strategy filtering. A future plan could unify them if needed.
- A reviewer should scrutinize: (1) that no numerical results changed (diff JSON outputs before and after), (2) that functions left in scripts with `# NOTE:` comments are genuinely unique, and (3) that no JSON output format changed.
- Follow-up: if many functions in `scripts/analyze_microstructure.py` are unique (working with OHLCV data while `src/` works with trade data), consider adding OHLCV-compatible functions to `src/analysis/microstructure.py` in a future plan.
