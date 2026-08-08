# Plan 020: Replace Any types with specific types

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/analyze_live.py scripts/statistical_analyzer.py scripts/generate_report.py scripts/generate_scientific_report.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. Also check if plan 011 has been
> executed (look for new modules in `src/analysis/` or `src/viz/` that
> came from `analyze_live.py`).

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans/011-extract-analyze-live-god-file.md (code should
  be in proper modules first, not a 1,945-line script)
- **Category**: tech-debt
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

Four scripts import `Any` from `typing` and use it (or import it unused)
in function signatures. `Any` disables mypy's type checking for that
parameter or return value, which means type errors pass silently. In two
scripts (`generate_report.py` and `generate_scientific_report.py`),
`Dict[str, Any]` is used as the type for the `analysis` parameter, which
is a complex dict returned by `analyze_all()`. Replacing `Any` with a
`TypedDict` that describes the actual structure enables mypy to catch
key mismatches and missing fields. In the other two scripts
(`analyze_live.py` and `statistical_analyzer.py`), `Any` is imported but
never used, which is dead code that ruff should flag.

## Current state

### scripts/analyze_live.py (1,945 lines)

Line 26 imports `Any` but it is never used anywhere in the file:

```python
from typing import Dict, List, Optional, Any
```

A grep for `Any` in the file confirms only the import line matches. The
import is dead code.

The file also uses bare `Dict` (without type parameters) in 17 function
return types. Examples:

- Line 644: `def analyze_symbol(...) -> Dict:`
- Line 764: `def analyze_all(data: Dict[str, pd.DataFrame]) -> Dict:`
- Line 164: `def calc_volume_profile(trades: pd.DataFrame, bins: int = 50) -> Dict:`
- Line 210: `def calc_order_book_metrics(ob: pd.DataFrame) -> Dict:`
- Line 239: `def test_stationarity_adf(series: pd.Series) -> Dict:`
- Line 486: `def cross_sectional_analysis(symbols_data: Dict[str, pd.DataFrame]) -> Dict:`

The `analyze_all()` function (line 764) returns a dict with this structure
(visible from lines 768-808):

```python
results = {'symbols': symbols, 'analyses': {}, 'cross_sectional': {}}
# ...
results['analyses'][sym] = analyze_symbol(...)  # Dict per symbol
results['cross_sectional'] = cross_sectional_analysis(...)  # Dict
results['fear_greed'] = {'current': int, 'classification': str, 'history_values': list, 'history_dates': list}
results['liquidations'] = {'total_usd': float, 'long_usd': float, 'short_usd': float, 'max_single_usd': float, 'timestamp': str}
```

The `analyze_symbol()` function (line 638) returns a dict with keys
visible at lines 689-762, including: `symbol` (str), `current_price`
(float), `rsi` (float), `macd` (float), `supertrend_trend` (str),
`funding_rate` (float), `chart_data` (dict with list values), etc.

### scripts/statistical_analyzer.py (788 lines)

Line 34 imports `Any` but it is never used anywhere in the file:

```python
from typing import Dict, List, Tuple, Optional, Any
```

A grep for `Any` in the file confirms only the import line matches. The
import is dead code.

### scripts/generate_report.py (433 lines)

Line 21 imports `Any`:

```python
from typing import Dict, Any, List
```

Line 85 uses `Any` in a function signature:

```python
def generate_scientific_report(analysis: Dict[str, Any]) -> str:
```

The function body (lines 85-129) accesses these keys from `analysis`:
- `analysis['symbols']` (list of str)
- `analysis['analyses']` (dict of {str: dict})
- `analysis.get('cross_sectional', {})` (dict)
- `analysis.get('fear_greed', {})` (dict with 'current', 'classification')
- `analysis.get('liquidations', {})` (dict with 'total_usd', 'long_usd', 'short_usd')

From `analyses[sym]` it accesses: `supertrend_trend`, `rsi`,
`funding_rate`, `current_price`, `bb_lower`, `bb_upper`, `macd`,
`macd_signal`.

### scripts/generate_scientific_report.py (392 lines)

Line 21 imports `Any`:

```python
from typing import Dict, Any, List
```

Line 74 uses `Any` in a function signature:

```python
def generate_scientific_report(analysis: Dict[str, Any]) -> str:
```

The function body accesses the same keys as `generate_report.py` (the
two files are near-duplicates, which is a separate issue tracked by plan
011/012).

### If plan 011 has been executed

Plan 011 extracts `analyze_live.py` into `src/` modules. If that plan has
been completed, the `Any` import and bare `Dict` types may have moved to
new modules. Check:

```bash
grep -rn "from typing import.*Any" src/
grep -rn "-> Dict\b" src/
```

If matches exist in `src/`, those files are also in scope (see Scope
section).

### Repo conventions (AGENTS.md)

- Python 3.11+, type hints obligatory (line 44)
- 4-space indent, 120 char max line (lines 45-46)
- snake_case for functions/variables, PascalCase for classes (line 47)
- No em-dash in any file (line 9)
- TypedDict is available from `typing` in Python 3.11+ (no need for
  `typing_extensions`)

## Commands you will need

| Purpose          | Command                                              | Expected on success |
|-----------------|------------------------------------------------------|---------------------|
| Lint            | `ruff check src/ scripts/`                           | exit 0              |
| Typecheck       | `mypy src/`                                          | exit 0, no errors   |
| Typecheck (scripts) | `mypy scripts/analyze_live.py scripts/statistical_analyzer.py scripts/generate_report.py scripts/generate_scientific_report.py` | exit 0, no errors |
| Verify no Any   | `grep -rn "\bAny\b" scripts/analyze_live.py scripts/statistical_analyzer.py scripts/generate_report.py scripts/generate_scientific_report.py` | no matches (or only in TypedDict fields if needed) |

## Scope

**In scope** (the only files you should modify):
- `scripts/analyze_live.py`
- `scripts/statistical_analyzer.py`
- `scripts/generate_report.py`
- `scripts/generate_scientific_report.py`
- Any new `src/` modules created by plan 011 that contain `Any` imports
  or bare `Dict` types (check with `grep -rn "from typing import.*Any" src/`)

**Out of scope** (do NOT touch):
- `src/` files that already use specific types (no `Any` or bare `Dict`)
- All test files
- `pyproject.toml` (owned by plan 015)
- Any file not listed above

## Git workflow

- Branch: `advisor/020-replace-any-types`
- Commit per step or per logical unit; message style: conventional commits
  (e.g. `refactor: replace Any types with TypedDict in report generators`)
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Remove unused `Any` import from `scripts/analyze_live.py`

Line 26 currently reads:

```python
from typing import Dict, List, Optional, Any
```

Change it to:

```python
from typing import Dict, List, Optional
```

`Any` is imported but never used in this file (confirmed by grep). This
is dead code.

**Verify**: `grep -n "\bAny\b" scripts/analyze_live.py` returns no matches. `ruff check scripts/analyze_live.py` exits 0.

### Step 2: Remove unused `Any` import from `scripts/statistical_analyzer.py`

Line 34 currently reads:

```python
from typing import Dict, List, Tuple, Optional, Any
```

Change it to:

```python
from typing import Dict, List, Tuple, Optional
```

`Any` is imported but never used in this file (confirmed by grep). This
is dead code.

**Verify**: `grep -n "\bAny\b" scripts/statistical_analyzer.py` returns no matches. `ruff check scripts/statistical_analyzer.py` exits 0.

### Step 3: Define a TypedDict for the analysis result structure

The `analyze_all()` function returns a dict with a well-defined structure.
Both `generate_report.py` and `generate_scientific_report.py` receive
this dict as their `analysis` parameter. Define a `TypedDict` to replace
`Dict[str, Any]`.

Add the TypedDict definitions to `scripts/analyze_live.py` (since that
is where `analyze_all` and `analyze_symbol` are defined, and the report
generators import from `scripts.analyze_live`). Place them near the top
of the file, after the imports and before the constants section (after
line 34, before line 36).

```python
from typing import Dict, List, Optional, TypedDict


class ChartData(TypedDict, total=False):
    """Chart data for a single symbol, used by the HTML dashboard."""
    timestamps: list[str]
    close: list[float]
    close_series: list[float]
    rsi: list[float]
    rsi_series: list[float]
    macd: list[float]
    macd_series: list[float]
    macd_signal: list[float]
    macd_sig_series: list[float]
    macd_hist: list[float]
    bb_upper: list[float]
    bb_upper_series: list[float]
    bb_lower: list[float]
    bb_lower_series: list[float]
    vwap: list[float]
    vwap_series: list[float]
    supertrend: list[float]
    supertrend_series: list[float]
    volume: list[float]
    buy_vol_series: list[float]
    sell_vol_series: list[float]
    imbalance_series: list[float]
    cvd_series: list[float]


class SymbolAnalysis(TypedDict, total=False):
    """Analysis result for a single symbol, returned by analyze_symbol()."""
    symbol: str
    current_price: float
    price_change_pct: float
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_lower: float
    bb_mid: float
    atr: float
    vwap: float
    supertrend: float
    supertrend_trend: str
    fib_levels: Dict[str, float]
    cvd: float
    kyle_lambda: float
    amihud: float
    volume_profile: Dict
    order_book: Dict
    stationarity: Dict[str, Dict]
    hurst: Dict
    half_life: Dict
    risk: Dict
    drawdowns: Dict
    regimes: Dict
    breakpoints: list
    funding_rate: float
    funding_class: str
    open_interest: float
    oi_change_24h: float
    long_short_ratio: float
    long_pct: float
    chart_data: ChartData


class FearGreedData(TypedDict, total=False):
    """Fear and Greed index data."""
    current: int
    classification: str
    history_values: list[int]
    history_dates: list[str]


class LiquidationData(TypedDict, total=False):
    """Liquidation summary data."""
    total_usd: float
    long_usd: float
    short_usd: float
    max_single_usd: float
    timestamp: str


class MarketAnalysis(TypedDict, total=False):
    """Top-level analysis result returned by analyze_all()."""
    symbols: list[str]
    analyses: Dict[str, SymbolAnalysis]
    cross_sectional: Dict
    fear_greed: FearGreedData
    liquidations: LiquidationData
```

Key design decisions:
- `total=False` is used on all TypedDicts because the dict keys are
  conditionally present (e.g. `fear_greed` and `liquidations` are only
  set if the data is available, see analyze_live.py lines 787-807).
- Nested dicts that have less predictable structures (like
  `stationarity`, `hurst`, `risk`, `drawdowns`, `regimes`) are typed as
  `Dict` or `Dict[str, Dict]` rather than fully specified TypedDicts.
  This is a pragmatic choice: fully specifying every nested dict would
  require dozens of TypedDicts for marginal benefit. The goal is to
  eliminate `Any`, not to achieve 100% type completeness. These can be
  refined in future plans.
- `ChartData` and `SymbolAnalysis` are separated because `ChartData` is
  nested inside `SymbolAnalysis`.

**Verify**: `ruff check scripts/analyze_live.py` exits 0. `python -c "from scripts.analyze_live import MarketAnalysis"` exits 0 (may need `sys.path` setup).

### Step 4: Update `analyze_all()` and `analyze_symbol()` return types in `analyze_live.py`

Update the return type annotations to use the new TypedDicts.

Line 644 (analyze_symbol return type):
```python
                   ls: pd.DataFrame) -> Dict:
```
Change to:
```python
                   ls: pd.DataFrame) -> SymbolAnalysis:
```

Line 764 (analyze_all return type):
```python
def analyze_all(data: Dict[str, pd.DataFrame]) -> Dict:
```
Change to:
```python
def analyze_all(data: Dict[str, pd.DataFrame]) -> MarketAnalysis:
```

Also update `generate_html()` at line 820:
```python
def generate_html(analysis: Dict) -> str:
```
Change to:
```python
def generate_html(analysis: MarketAnalysis) -> str:
```

**Verify**: `ruff check scripts/analyze_live.py` exits 0. `mypy scripts/analyze_live.py` exits 0 (or only pre-existing errors, no new ones).

### Step 5: Replace `Dict[str, Any]` in `scripts/generate_report.py`

Line 21 currently reads:
```python
from typing import Dict, Any, List
```

Change to:
```python
from typing import Dict, List
```

Line 28 currently reads:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS
```

Change to:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS, MarketAnalysis
```

Line 85 currently reads:
```python
def generate_scientific_report(analysis: Dict[str, Any]) -> str:
```

Change to:
```python
def generate_scientific_report(analysis: MarketAnalysis) -> str:
```

**Verify**: `grep -n "\bAny\b" scripts/generate_report.py` returns no matches. `ruff check scripts/generate_report.py` exits 0.

### Step 6: Replace `Dict[str, Any]` in `scripts/generate_scientific_report.py`

Line 21 currently reads:
```python
from typing import Dict, Any, List
```

Change to:
```python
from typing import Dict, List
```

Line 27 currently reads:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS
```

Change to:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS, MarketAnalysis
```

Line 74 currently reads:
```python
def generate_scientific_report(analysis: Dict[str, Any]) -> str:
```

Change to:
```python
def generate_scientific_report(analysis: MarketAnalysis) -> str:
```

**Verify**: `grep -n "\bAny\b" scripts/generate_scientific_report.py` returns no matches. `ruff check scripts/generate_scientific_report.py` exits 0.

### Step 7: Fix any new `src/` modules from plan 011 (if applicable)

If plan 011 has been executed and code from `analyze_live.py` was moved
to `src/` modules, check those modules for `Any` imports or bare `Dict`
types:

```bash
grep -rn "from typing import.*Any" src/
grep -rn "-> Dict\b" src/
```

For each match:
1. If `Any` is imported but unused, remove it from the import.
2. If `Any` is used in a function signature, replace it with the specific
   type (import the TypedDict from the module where it was defined, or
   define a new TypedDict if the structure is different).
3. If `-> Dict` is used without type parameters, add the appropriate
   type parameter (e.g. `-> Dict[str, float]` or `-> SymbolAnalysis`).

If plan 011 has NOT been executed (no new `src/` modules from
`analyze_live.py`), skip this step.

**Verify**: `grep -rn "\bAny\b" src/` returns no matches (or only in
legitimate contexts like `Any` in a type bound, which should not exist
in this codebase). `mypy src/` exits 0.

### Step 8: Run full lint and typecheck

Run the project's standard commands to verify no regressions:

```bash
ruff check src/ scripts/
mypy src/
```

If plan 015 has been executed and `mypy scripts/` is configured, also
run:

```bash
mypy scripts/
```

If there are mypy errors related to the TypedDict (e.g. "Key X of
TypedDict Y is not assignable"), this likely means the TypedDict
definition does not match the actual dict structure. Compare the
TypedDict fields against the `analyze_symbol()` return dict (lines
689-762) and adjust the TypedDict accordingly.

**Verify**: `ruff check src/ scripts/` exits 0. `mypy src/` exits 0 (or only pre-existing errors, no new ones from this plan).

## Test plan

No new tests to write. This plan changes type annotations only, not
runtime behavior. The existing test suite verifies behavior:

```bash
pytest tests/ -v
```

All 52 existing tests should still pass. Type annotation changes do not
affect runtime behavior in Python.

If any test fails after these changes, it means a type annotation change
accidentally modified runtime behavior (e.g. a typo in an import). Fix
the typo and re-run.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -n "\bAny\b" scripts/analyze_live.py` returns no matches
- [ ] `grep -n "\bAny\b" scripts/statistical_analyzer.py` returns no matches
- [ ] `grep -n "\bAny\b" scripts/generate_report.py` returns no matches
- [ ] `grep -n "\bAny\b" scripts/generate_scientific_report.py` returns no matches
- [ ] `grep -rn "\bAny\b" src/` returns no matches (if plan 011 was executed)
- [ ] `ruff check src/ scripts/` exits 0
- [ ] `mypy src/` exits 0 (or only pre-existing errors, no new ones)
- [ ] `pytest tests/ -v` all pass (no regressions)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Plan 011 has NOT been executed and you find that the 1,945-line
  `analyze_live.py` is too large to safely add TypedDict definitions
  (e.g. the file has syntax errors, or the structure has changed
  significantly). Report this so plan 011 can be executed first.
- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.
- mypy reports errors that cannot be resolved by adjusting the TypedDict
  definitions (e.g. the actual dict structure is fundamentally different
  from what is documented in "Current state"). Report the specific mypy
  errors.
- You discover that `analyze_all()` or `analyze_symbol()` return
  additional keys not documented in "Current state" that would require
  expanding the TypedDict. Add the missing keys and re-verify.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- The TypedDicts defined in this plan (`MarketAnalysis`, `SymbolAnalysis`,
  `ChartData`, `FearGreedData`, `LiquidationData`) are intentionally
  incomplete for nested dicts (e.g. `stationarity`, `hurst`, `risk`,
  `drawdowns`, `regimes` are typed as `Dict` without full structure).
  These can be refined in future plans by defining additional TypedDicts
  for each nested structure.
- If `analyze_symbol()` or `analyze_all()` gain new return keys, update
  the corresponding TypedDict. The `total=False` flag means missing keys
  are allowed, but new keys should be documented for type safety.
- If plan 011 moves the TypedDicts to a `src/` module (e.g.
  `src/analysis/types.py`), update the imports in `generate_report.py`
  and `generate_scientific_report.py` to import from the new location.
- The bare `Dict` return types in `analyze_live.py` (17 functions with
  `-> Dict`) are partially addressed by this plan (only `analyze_symbol`,
  `analyze_all`, and `generate_html` are updated). The remaining 14
  functions still use bare `Dict`. A follow-up plan could address these,
  but they are lower priority since they do not use `Any`.
- A reviewer should verify that the TypedDict fields match the actual
  dict keys by comparing against the `analyze_symbol()` return statement
  (lines 689-762) and the `analyze_all()` return statement (lines
  768-808).
