# Plan 012: Fix layering violations + duplicate functions + __init__.py exports

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/generate_report.py scripts/generate_scientific_report.py scripts/statistical_analyzer.py src/__init__.py src/analysis/__init__.py src/backtest/__init__.py src/data/__init__.py src/strategy/__init__.py src/viz/__init__.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/011-extract-analyze-live-into-src-modules.md
- **Category**: tech-debt
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

Three problems create maintenance friction and testability gaps. First, two report scripts import from `scripts.analyze_live`, which is a layering violation: scripts should depend on `src/`, not on other scripts. Second, five utility functions (`format_pct`, `format_num`, `format_sci`, `regime_name`, `signal_interpretation`) are duplicated verbatim across both report scripts, meaning bug fixes must be applied twice. Third, all 6 `__init__.py` files in `src/` are empty, so there are no package-level exports, making imports verbose and preventing `from src.analysis import CorrelationMatrix` style usage. Fixing all three makes the codebase DRY, properly layered, and easier to import from.

## Current state

The relevant files, each with one line on its role:

- `scripts/generate_report.py` (433 lines) : markdown report generator. Imports from `scripts.analyze_live` at line 28.
- `scripts/generate_scientific_report.py` (392 lines) : scientific markdown report generator. Imports from `scripts.analyze_live` at line 27.
- `scripts/statistical_analyzer.py` (788 lines) : advanced statistical analysis module. Has a duplicate Hurst implementation.
- `src/__init__.py` : empty (0 lines).
- `src/analysis/__init__.py` : empty (0 lines).
- `src/backtest/__init__.py` : empty (0 lines).
- `src/data/__init__.py` : empty (0 lines).
- `src/strategy/__init__.py` : empty (0 lines).
- `src/viz/__init__.py` : empty (0 lines).

### Layering violation: scripts importing from scripts

`scripts/generate_report.py:28`:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS
```

`scripts/generate_scientific_report.py:27`:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS
```

After plan 011, `load_live_data`, `analyze_all`, and `SYMBOLS` are re-exported from `scripts/analyze_live` but actually live in `src/analysis/live_analysis.py`. These imports should point to `src/analysis/live_analysis.py` directly.

### Duplicate utility functions in both report scripts

Both `scripts/generate_report.py` (lines 31-80) and `scripts/generate_scientific_report.py` (lines 30-71) define these 5 functions with identical logic:

`scripts/generate_report.py:31-50`:
```python
def format_pct(x: float) -> str:
    return f"{x*100:.2f}%"

def format_num(x: float, decimals: int = 4) -> str:
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f}M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.2f}K"
    return f"{x:.{decimals}f}"

def format_sci(x: float) -> str:
    if x == 0:
        return "0.00"
    return f"{x:.2e}"

def regime_name(regime: int) -> str:
    return {0: "Bear (Low Vol)", 1: "Neutral", 2: "Bull (High Vol)"}.get(regime, f"State {regime}")

def signal_interpretation(rsi: float, macd: float, macd_sig: float, bb_pos: float, st_trend: str) -> Dict[str, str]:
    ...
```

`scripts/generate_scientific_report.py:30-71` has the same 5 functions with the same signatures and same logic (minor formatting differences in `signal_interpretation` body, but same output).

### Duplicate Hurst implementation

There are three Hurst exponent implementations in the codebase:

1. `scripts/analyze_live.py:265` (`calc_hurst`) : now in `src/analysis/statistical.py` after plan 011. R/S analysis with logspace lags, returns dict with `hurst`, `r_squared`, `p_value`, `interpretation`.
2. `scripts/statistical_analyzer.py:200` (`hurst_exponent` method on a class) : R/S analysis with logspace lags, returns dict with `hurst`, `r_squared`, `p_value`, `method`, `interpretation`. Nearly identical logic.
3. `src/strategy/regime_filter.py:78` (`compute_hurst`) : R/S analysis with fixed chunk sizes `[8, 16, 32, 64, 128, 256]`, returns a single float. Different interface, used by `RegimeFilter` class.

This plan consolidates #1 and #2. Implementation #3 (`compute_hurst` in `regime_filter.py`) has a different interface (returns float, not dict) and is tightly coupled to `RegimeFilter`. It is out of scope.

### Existing src/ modules (for __init__.py exports)

The public symbols that should be exported from each package:

- `src/analysis/`: `CorrelationMatrix` (from `correlation.py`), `calculate_returns`, `align_returns` (from `returns.py`), `CorrelationGraph` (from `graph.py`), plus all new modules from plan 011: `calc_rsi`, `calc_macd`, etc. (from `indicators.py`), `calc_cvd`, etc. (from `microstructure.py`), `test_stationarity_adf`, `calc_hurst`, etc. (from `statistical.py`), `detect_regimes_hmm`, `detect_breakpoints` (from `regime.py`), `cross_sectional_analysis`, `cross_correlation`, `granger_causality` (from `cross_sectional.py`), `load_live_data`, `analyze_all`, `analyze_symbol`, `build_ohlcv_from_trades`, `SYMBOLS` (from `live_analysis.py`).
- `src/backtest/`: `BacktestEngine`, `BacktestConfig`, `Trade`, `Position` (from `engine.py`), `WalkForwardAnalyzer`, `WalkForwardConfig`, `WalkForwardResult` (from `walk_forward.py`).
- `src/data/`: `ParquetStore` (from `parquet_store.py`), `DEFAULT_UNIVERSE`, `SYMBOL_METADATA` (from `universe.py`), `LiveCollector` (from `live_collector.py`).
- `src/strategy/`: `BaseStrategy`, `Signal`, `Direction`, `Regime` (from `base.py`), `MeanReversionStrategy`, `MeanReversionConfig` (from `mean_reversion.py`), `MomentumStrategy`, `MomentumConfig` (from `momentum.py`), `StatArbStrategy`, `StatArbConfig` (from `stat_arb.py`), `RegimeFilter` (from `regime_filter.py`), `MetaStrategy`, `MetaStrategyConfig` (from `meta.py`).
- `src/viz/`: `GraphVisualizer` (from `graph_visualizer.py`), `generate_html` (from `dashboard.py`, created in plan 011).
- `src/`: re-export the subpackages.

### Repo conventions that apply

- Python 3.11+, type hints required.
- 4-space indentation, 120 char max line length.
- `snake_case` for functions/variables, `PascalCase` for classes.
- Functions max 30 lines.
- Imports: stdlib first, third-party second, project imports third. See `src/analysis/correlation.py:1-10` for the exemplar pattern.
- No em-dash (the character `:`). Use `:`, `.`, or `,` instead.
- No hardcoded API keys or secrets.
- No `try/except pass` (empty catch).

## Commands you will need

| Purpose          | Command                                                      | Expected on success |
|------------------|--------------------------------------------------------------|---------------------|
| Tests            | `pytest tests/ -v`                                           | all pass            |
| Lint             | `ruff check src/ scripts/`                                   | exit 0              |
| Import check     | `python -c "from src.analysis import CorrelationMatrix"`    | exit 0, no output   |
| Import check     | `python -c "from src.utils.formatting import format_pct"`   | exit 0, no output   |

## Scope

**In scope** (the only files you should modify or create):
- `src/utils/formatting.py` (create)
- `src/utils/__init__.py` (create, empty or with exports)
- `scripts/generate_report.py` (modify imports, remove duplicate functions)
- `scripts/generate_scientific_report.py` (modify imports, remove duplicate functions)
- `scripts/statistical_analyzer.py` (modify to import Hurst from `src/analysis/statistical.py`)
- `src/__init__.py` (add exports)
- `src/analysis/__init__.py` (add exports)
- `src/backtest/__init__.py` (add exports)
- `src/data/__init__.py` (add exports)
- `src/strategy/__init__.py` (add exports)
- `src/viz/__init__.py` (add exports)

**Out of scope** (do NOT touch):
- `scripts/analyze_live.py` : already refactored in plan 011.
- `src/strategy/regime_filter.py` : its `compute_hurst` has a different interface (returns float, not dict). Do not consolidate it.
- `src/analysis/statistical.py` : created in plan 011. Do not modify its `calc_hurst` implementation. Only import from it.
- `src/analysis/correlation.py`, `src/analysis/returns.py`, `src/analysis/graph.py` : existing modules, not modified.
- Any test files.

## Git workflow

- Branch: `advisor/012-fix-layering-init-exports`
- Commit per logical unit: (1) create `src/utils/formatting.py`, (2) update report scripts, (3) consolidate Hurst, (4) add `__init__.py` exports. Message style: `refactor: <what changed>`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Create src/utils/formatting.py with the 5 utility functions

Create `src/utils/__init__.py` (empty file).

Create `src/utils/formatting.py` with these 5 functions, taken from `scripts/generate_report.py:31-80`:

```python
"""Formatting utilities for reports and dashboards.

Shared formatting functions used by generate_report.py and
generate_scientific_report.py to avoid duplication.
"""
from typing import Dict


def format_pct(x: float) -> str:
    """Format a ratio as a percentage string."""
    return f"{x*100:.2f}%"


def format_num(x: float, decimals: int = 4) -> str:
    """Format a number with K/M suffixes for large values."""
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f}M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.2f}K"
    return f"{x:.{decimals}f}"


def format_sci(x: float) -> str:
    """Format a number in scientific notation."""
    if x == 0:
        return "0.00"
    return f"{x:.2e}"


def regime_name(regime: int) -> str:
    """Map a regime integer to a human-readable name."""
    return {0: "Bear (Low Vol)", 1: "Neutral", 2: "Bull (High Vol)"}.get(regime, f"State {regime}")


def signal_interpretation(
    rsi: float,
    macd: float,
    macd_sig: float,
    bb_pos: float,
    st_trend: str,
) -> Dict[str, str]:
    """Generate signal interpretations for a symbol."""
    signals: Dict[str, str] = {}

    if rsi > 70:
        signals["RSI"] = "Overbought, potential sell"
    elif rsi < 30:
        signals["RSI"] = "Oversold, potential buy"
    else:
        signals["RSI"] = "Neutral"

    signals["MACD"] = "Bullish (MACD > Signal)" if macd > macd_sig else "Bearish (MACD < Signal)"

    if bb_pos > 0.8:
        signals["BB"] = "Near upper band, overbought"
    elif bb_pos < 0.2:
        signals["BB"] = "Near lower band, oversold"
    else:
        signals["BB"] = "Within bands"

    signals["SuperTrend"] = "Uptrend" if st_trend == "UP" else "Downtrend"
    return signals
```

IMPORTANT: The original `signal_interpretation` in both report scripts contains emoji characters (red/green/white circles) and Portuguese text. Check the actual source files for the exact strings. Use the version from `scripts/generate_report.py:53-80` as the canonical version. Do NOT change the output strings, only the function structure. The executor must read `scripts/generate_report.py:53-80` and copy the exact body, adapting only the formatting (removing the emoji if they cause encoding issues is NOT allowed, keep them verbatim).

**Verify**: `python -c "from src.utils.formatting import format_pct, format_num, format_sci, regime_name, signal_interpretation; print('OK')"` prints `OK`, exit 0. `ruff check src/utils/formatting.py` exits 0.

### Step 2: Update scripts/generate_report.py to import from src/

In `scripts/generate_report.py`:

1. Replace line 28:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS
```
with:
```python
from src.analysis.live_analysis import load_live_data, analyze_all, SYMBOLS
```

2. Remove the 5 duplicate function definitions (lines 31-80: `format_pct`, `format_num`, `format_sci`, `regime_name`, `signal_interpretation`).

3. Add this import after the existing project imports:
```python
from src.utils.formatting import (
    format_pct, format_num, format_sci, regime_name, signal_interpretation,
)
```

4. Run `grep -n "format_pct\|format_num\|format_sci\|regime_name\|signal_interpretation" scripts/generate_report.py` to confirm all call sites still resolve (they should, since the function names are identical).

**Verify**: `python -c "import scripts.generate_report; print('OK')"` prints `OK`, exit 0. `ruff check scripts/generate_report.py` exits 0.

### Step 3: Update scripts/generate_scientific_report.py to import from src/

In `scripts/generate_scientific_report.py`:

1. Replace line 27:
```python
from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS
```
with:
```python
from src.analysis.live_analysis import load_live_data, analyze_all, SYMBOLS
```

2. Remove the 5 duplicate function definitions (lines 30-71: `format_pct`, `format_num`, `format_sci`, `regime_name`, `signal_interpretation`).

3. Add this import:
```python
from src.utils.formatting import (
    format_pct, format_num, format_sci, regime_name, signal_interpretation,
)
```

4. Check that `signal_interpretation` in `scripts/generate_scientific_report.py:52-71` has the same output as the one in `src/utils/formatting.py`. If there are differences in the output strings (e.g. different emoji or text), STOP and report. The canonical version is from `scripts/generate_report.py`. If the scientific report version differs, the executor must decide which to keep. Default: keep the `generate_report.py` version (it is the original). Report any difference as a deviation.

**Verify**: `python -c "import scripts.generate_scientific_report; print('OK')"` prints `OK`, exit 0. `ruff check scripts/generate_scientific_report.py` exits 0.

### Step 4: Consolidate Hurst in scripts/statistical_analyzer.py

The `hurst_exponent` method in `scripts/statistical_analyzer.py:200-248` duplicates `calc_hurst` in `src/analysis/statistical.py` (created in plan 011). Both use R/S analysis with logspace lags and return a dict with `hurst`, `r_squared`, `p_value`, `interpretation`.

The difference: `hurst_exponent` is a method on a class (line 200) and includes a `method` key (`'R/S'`) in its return dict. `calc_hurst` is a standalone function and does not include `method`.

To consolidate:

1. In `scripts/statistical_analyzer.py`, add this import near the top (after existing imports, around line 37):
```python
from src.analysis.statistical import calc_hurst
```

2. Replace the `hurst_exponent` method body (lines 200-248) with a call to `calc_hurst`, adding the `method` key for backward compatibility:
```python
def hurst_exponent(self, series: pd.Series, min_lag: int = 2, max_lag: int = 100) -> Dict:
    """Calculate Hurst exponent using R/S analysis (Rescaled Range).

    Delegates to src.analysis.statistical.calc_hurst for the core
    computation. The min_lag and max_lag parameters are accepted for
    backward compatibility but the underlying implementation uses its
    own lag selection.
    """
    result = calc_hurst(series)
    result["method"] = "R/S"
    return result
```

3. Remove the `_interpret_hurst` method (lines 250-258) if it is no longer called. Check with `grep -n "_interpret_hurst" scripts/statistical_analyzer.py`. If it is only called from the old `hurst_exponent` body (which is now replaced), remove it. If it is called elsewhere, keep it.

IMPORTANT: The `calc_hurst` in `src/analysis/statistical.py` does not accept `min_lag` and `max_lag` parameters (it computes `max_lag` internally as `min(100, len(series) // 4)`). The wrapper accepts them for backward compatibility but ignores them. This is a known limitation. If the caller passes custom `min_lag`/`max_lag` values and expects them to be used, the results may differ. Check all call sites of `hurst_exponent` in `scripts/statistical_analyzer.py` with `grep -n "hurst_exponent" scripts/statistical_analyzer.py`. If any call site passes custom `min_lag` or `max_lag`, STOP and report.

**Verify**: `python -c "import scripts.statistical_analyzer; print('OK')"` prints `OK`, exit 0. `ruff check scripts/statistical_analyzer.py` exits 0.

### Step 5: Add exports to all 6 __init__.py files

Add `__all__` and explicit re-exports to each `__init__.py`. Use explicit imports (not `*`) to keep ruff happy.

**`src/__init__.py`**:
```python
"""crypto-correl-bot: correlation-based crypto trading bot."""
from src import analysis, backtest, data, strategy, viz

__all__ = ["analysis", "backtest", "data", "strategy", "viz"]
```

**`src/analysis/__init__.py`**:
```python
"""Analysis modules: returns, correlation, graph, indicators, microstructure, statistics, regime, cross-sectional, live analysis."""
from src.analysis.correlation import CorrelationMatrix
from src.analysis.returns import calculate_returns, align_returns
from src.analysis.graph import CorrelationGraph
from src.analysis.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr,
    calc_vwap, calc_supertrend, calc_fibonacci,
)
from src.analysis.microstructure import (
    calc_cvd, calc_kyle_lambda, calc_amihud,
    calc_volume_profile, calc_order_book_metrics,
)
from src.analysis.statistical import (
    test_stationarity_adf, test_stationarity_kpss, calc_hurst,
    calc_half_life, calc_var_cvar, calc_drawdowns,
)
from src.analysis.regime import detect_regimes_hmm, detect_breakpoints
from src.analysis.cross_sectional import (
    cross_sectional_analysis, cross_correlation, granger_causality,
)
from src.analysis.live_analysis import (
    SYMBOLS, load_live_data, build_ohlcv_from_trades,
    analyze_symbol, analyze_all,
)

__all__ = [
    "CorrelationMatrix", "calculate_returns", "align_returns", "CorrelationGraph",
    "calc_rsi", "calc_macd", "calc_bollinger", "calc_atr", "calc_vwap",
    "calc_supertrend", "calc_fibonacci",
    "calc_cvd", "calc_kyle_lambda", "calc_amihud", "calc_volume_profile",
    "calc_order_book_metrics",
    "test_stationarity_adf", "test_stationarity_kpss", "calc_hurst",
    "calc_half_life", "calc_var_cvar", "calc_drawdowns",
    "detect_regimes_hmm", "detect_breakpoints",
    "cross_sectional_analysis", "cross_correlation", "granger_causality",
    "SYMBOLS", "load_live_data", "build_ohlcv_from_trades",
    "analyze_symbol", "analyze_all",
]
```

**`src/backtest/__init__.py`**:
```python
"""Backtest modules: engine and walk-forward analysis."""
from src.backtest.engine import BacktestEngine, BacktestConfig, Trade, Position
from src.backtest.walk_forward import (
    WalkForwardAnalyzer, WalkForwardConfig, WalkForwardResult,
)

__all__ = [
    "BacktestEngine", "BacktestConfig", "Trade", "Position",
    "WalkForwardAnalyzer", "WalkForwardConfig", "WalkForwardResult",
]
```

**`src/data/__init__.py`**:
```python
"""Data modules: Parquet storage, universe definition, live collector."""
from src.data.parquet_store import ParquetStore
from src.data.universe import DEFAULT_UNIVERSE, SYMBOL_METADATA
from src.data.live_collector import LiveCollector

__all__ = ["ParquetStore", "DEFAULT_UNIVERSE", "SYMBOL_METADATA", "LiveCollector"]
```

**`src/strategy/__init__.py`**:
```python
"""Strategy modules: base interface and implementations."""
from src.strategy.base import BaseStrategy, Signal, Direction, Regime
from src.strategy.mean_reversion import MeanReversionStrategy, MeanReversionConfig
from src.strategy.momentum import MomentumStrategy, MomentumConfig
from src.strategy.stat_arb import StatArbStrategy, StatArbConfig
from src.strategy.regime_filter import RegimeFilter
from src.strategy.meta import MetaStrategy, MetaStrategyConfig

__all__ = [
    "BaseStrategy", "Signal", "Direction", "Regime",
    "MeanReversionStrategy", "MeanReversionConfig",
    "MomentumStrategy", "MomentumConfig",
    "StatArbStrategy", "StatArbConfig",
    "RegimeFilter",
    "MetaStrategy", "MetaStrategyConfig",
]
```

**`src/viz/__init__.py`**:
```python
"""Visualization modules: graph visualizer and dashboard generator."""
from src.viz.graph_visualizer import GraphVisualizer
from src.viz.dashboard import generate_html

__all__ = ["GraphVisualizer", "generate_html"]
```

IMPORTANT: Before writing these files, verify that all imported symbols actually exist in their source modules. Run these commands to check:
```bash
grep -n "^class CorrelationMatrix" src/analysis/correlation.py
grep -n "^def calculate_returns\|^def align_returns" src/analysis/returns.py
grep -n "^class CorrelationGraph" src/analysis/graph.py
grep -n "^def calc_rsi" src/analysis/indicators.py
grep -n "^class BacktestEngine\|^class BacktestConfig\|^class Trade\|^class Position" src/backtest/engine.py
grep -n "^class WalkForwardAnalyzer\|^class WalkForwardConfig\|^class WalkForwardResult" src/backtest/walk_forward.py
grep -n "^class ParquetStore" src/data/parquet_store.py
grep -n "^DEFAULT_UNIVERSE\|^SYMBOL_METADATA" src/data/universe.py
grep -n "^class LiveCollector" src/data/live_collector.py
grep -n "^class BaseStrategy\|^class Signal\|^class Direction\|^class Regime" src/strategy/base.py
grep -n "^class MeanReversionStrategy\|^class MeanReversionConfig" src/strategy/mean_reversion.py
grep -n "^class MomentumStrategy\|^class MomentumConfig" src/strategy/momentum.py
grep -n "^class StatArbStrategy\|^class StatArbConfig" src/strategy/stat_arb.py
grep -n "^class RegimeFilter" src/strategy/regime_filter.py
grep -n "^class MetaStrategy\|^class MetaStrategyConfig" src/strategy/meta.py
grep -n "^class GraphVisualizer" src/viz/graph_visualizer.py
grep -n "^def generate_html" src/viz/dashboard.py
```

If any of these return no matches, the symbol name is wrong or the module doesn't exist (plan 011 may not have been completed). STOP and report.

**Verify**: `python -c "from src.analysis import CorrelationMatrix; print('OK')"` prints `OK`, exit 0. `python -c "from src.backtest import BacktestEngine; print('OK')"` prints `OK`, exit 0. `python -c "from src.data import ParquetStore; print('OK')"` prints `OK`, exit 0. `python -c "from src.strategy import BaseStrategy; print('OK')"` prints `OK`, exit 0. `python -c "from src.viz import GraphVisualizer; print('OK')"` prints `OK`, exit 0. `ruff check src/` exits 0.

### Step 6: Verify no remaining layering violations

Run:
```bash
grep -rn "from scripts.analyze_live" scripts/
```

This should return no matches. If it returns any matches, there are remaining layering violations. STOP and report.

Run:
```bash
grep -rn "from scripts\." scripts/
```

This should also return no matches (no script should import from another script). If it does, report the findings (they may be pre-existing and out of scope, but report them).

**Verify**: `grep -rn "from scripts.analyze_live" scripts/` returns no matches. `pytest tests/ -v` exits 0. `ruff check src/ scripts/` exits 0.

## Test plan

No new tests are written in this plan. The existing test suite must continue to pass. The key verification is that imports resolve correctly and no duplicate function definitions remain.

- `grep -rn "def format_pct" scripts/` should return 0 matches (the function is now only in `src/utils/formatting.py`).
- `grep -rn "def format_num" scripts/` should return 0 matches.
- `grep -rn "def format_sci" scripts/` should return 0 matches.
- `grep -rn "def regime_name" scripts/` should return 0 matches.
- `grep -rn "def signal_interpretation" scripts/` should return 0 matches.
- `grep -rn "from scripts.analyze_live" scripts/` should return 0 matches.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/ -v` exits 0
- [ ] `ruff check src/ scripts/` exits 0
- [ ] `python -c "from src.analysis import CorrelationMatrix"` exits 0
- [ ] `python -c "from src.utils.formatting import format_pct"` exits 0
- [ ] `grep -rn "from scripts.analyze_live" scripts/` returns no matches
- [ ] `grep -rn "def format_pct\|def format_num\|def format_sci\|def regime_name\|def signal_interpretation" scripts/` returns no matches
- [ ] All 6 `__init__.py` files in `src/` are non-empty (have exports)
- [ ] `src/utils/formatting.py` exists and has 5 functions
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts. Run `grep -n "from scripts.analyze_live import" scripts/generate_report.py` and confirm it returns line 28. If not, STOP.
- Plan 011 has not been completed (the `src/analysis/` modules don't exist). Run `ls src/analysis/indicators.py src/analysis/live_analysis.py src/viz/dashboard.py`. If any are missing, STOP.
- The `signal_interpretation` function in `scripts/generate_scientific_report.py` has different output strings than the one in `scripts/generate_report.py`. STOP and report the differences so a human can decide which to keep.
- The `hurst_exponent` method in `scripts/statistical_analyzer.py` is called with custom `min_lag` or `max_lag` values that would be ignored by the wrapper. STOP and report the call sites.
- Any symbol name in the `__init__.py` exports doesn't exist in its source module (the grep checks in step 5 fail). STOP and report which symbol is missing.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- After this plan, `src/utils/formatting.py` is the single source of truth for formatting utilities. Any new report or dashboard script should import from there.
- The `hurst_exponent` method in `scripts/statistical_analyzer.py` is now a thin wrapper around `src/analysis/statistical.calc_hurst`. If the wrapper's `min_lag`/`max_lag` parameters are needed in the future, `calc_hurst` must be extended to accept them. This is a known limitation.
- The `__init__.py` exports make imports shorter (`from src.analysis import CorrelationMatrix` instead of `from src.analysis.correlation import CorrelationMatrix`). Future code should use the short form.
- `src/strategy/regime_filter.py:compute_hurst` (returns float) is intentionally NOT consolidated with `calc_hurst` (returns dict) because they have different interfaces. A future plan could unify them by making `compute_hurst` call `calc_hurst` and extract the float, but this requires changing `RegimeFilter` callers and is out of scope.
- A reviewer should scrutinize: (1) that the `signal_interpretation` output strings are identical to the originals (no emoji or text changes), (2) that the `hurst_exponent` wrapper preserves backward compatibility (returns a dict with the same keys), and (3) that all `__init__.py` exports resolve without circular import errors.
