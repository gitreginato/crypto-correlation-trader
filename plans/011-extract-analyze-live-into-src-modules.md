# Plan 011: Extract analyze_live.py god file into src/ modules

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/analyze_live.py src/analysis/ src/viz/dashboard.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

`scripts/analyze_live.py` is a 1,945-line god file containing 30+ functions spanning technical indicators, microstructure metrics, statistical tests, regime detection, cross-sectional analysis, data loading, and 1,097 lines of HTML/JS generation. This makes the file impossible to test in isolation, impossible to reuse from other scripts, and a maintenance hazard. Extracting each concern into a dedicated `src/` module makes the code importable, testable, and reusable. The script itself shrinks to a thin orchestration layer that calls `main()`.

## Current state

The relevant files, each with one line on its role:

- `scripts/analyze_live.py` (1,945 lines) : the god file. Contains all analysis logic and HTML generation. Only `main()` (lines 1918-1945) is orchestration.
- `src/analysis/__init__.py` : empty (0 lines).
- `src/analysis/correlation.py` (91 lines) : existing `CorrelationMatrix` class. Not touched by this plan.
- `src/analysis/returns.py` (64 lines) : existing `calculate_returns` function. Not touched by this plan.
- `src/analysis/graph.py` (122 lines) : existing `CorrelationGraph` class. Not touched by this plan.
- `src/viz/__init__.py` : empty (0 lines).
- `src/viz/graph_visualizer.py` (108 lines) : existing `GraphVisualizer` class. Not touched by this plan.

### Function inventory in scripts/analyze_live.py

The 30 functions are grouped by concern. Line numbers are from the current file:

**Technical indicators (lines 65-136):**
```python
def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:          # line 65
def calc_macd(series: pd.Series, fast=12, slow=26, signal=9):            # line 74
def calc_bollinger(series: pd.Series, period=20, std_dev=2):             # line 81
def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:           # line 86
def calc_vwap(df: pd.DataFrame) -> pd.Series:                            # line 93
def calc_supertrend(df: pd.DataFrame, atr_period=10, multiplier=3):     # line 97
def calc_fibonacci(high: float, low: float) -> Dict[str, float]:        # line 126
```

**Microstructure metrics (lines 140-235):**
```python
def calc_cvd(trades: pd.DataFrame) -> float:                             # line 140
def calc_kyle_lambda(returns: pd.Series, volumes: pd.Series) -> float:  # line 147
def calc_amihud(returns: pd.Series, volumes: pd.Series, window=20):     # line 157
def calc_volume_profile(trades: pd.DataFrame, bins: int = 50) -> Dict:  # line 164
def calc_order_book_metrics(ob: pd.DataFrame) -> Dict:                   # line 210
```

**Statistical analysis (lines 239-404):**
```python
def test_stationarity_adf(series: pd.Series) -> Dict:                   # line 239
def test_stationarity_kpss(series: pd.Series) -> Dict:                  # line 252
def calc_hurst(series: pd.Series) -> Dict:                              # line 265
def calc_half_life(series: pd.Series) -> Dict:                          # line 320
def calc_var_cvar(returns: pd.Series, confidence=0.95) -> Dict:        # line 349
def calc_drawdowns(prices: pd.Series) -> Dict:                          # line 370
```

**Regime detection (lines 406-482):**
```python
def detect_regimes_hmm(returns: pd.Series, n_states=3) -> Dict:        # line 406
def detect_breakpoints(series: pd.Series) -> List[int]:                # line 469
```

**Cross-sectional analysis (lines 486-581):**
```python
def cross_sectional_analysis(symbols_data: Dict[str, pd.DataFrame]) -> Dict:  # line 486
def cross_correlation(s1: pd.Series, s2: pd.Series, max_lag=20) -> Dict:     # line 536
def granger_causality(s1: pd.Series, s2: pd.Series, max_lag=10) -> Dict:     # line 561
```

**Data loading (lines 585-634):**
```python
def load_live_data(data_dir="data/live", recent_hours=1.0) -> Dict:    # line 585
def build_ohlcv_from_trades(trades: pd.DataFrame, freq="1min") -> Dict: # line 604
```

**Analysis pipeline (lines 638-809):**
```python
def analyze_symbol(symbol, ohlcv, trades, order_book, funding, oi, ls) -> Dict:  # line 638 (125 lines)
def analyze_all(data: Dict[str, pd.DataFrame]) -> Dict:                          # line 764
```

**HTML generation (lines 813-1917):**
```python
def fmt_usd(v: float) -> str:                 # line 813
def generate_html(analysis: Dict) -> str:     # line 820 (1,097 lines, contains nested fmt_usd, badge, class_for_value)
```

**Orchestration (lines 1918-1945):**
```python
def main():  # line 1918, calls load_live_data, analyze_all, generate_html
```

### Module-level constants (lines 36-61)

```python
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
DATA_DIR = Path("data/live")
UPDATE_INTERVAL_MS = 10000
WS_BATCH_MS = 50
COLORS = { 'bg': '#0B0E14', 'surface': '#131722', ... }  # 14 color keys
SYM_COLORS = ['#42A5F5', '#26A69A', '#AB47BC', '#FF9800', '#26C6DA', '#FF7043', '#66BB6A', '#EC407A']
```

### External callers

Two scripts import from this file (handled in plan 012, NOT this plan):
- `scripts/generate_report.py:28` : `from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS`
- `scripts/generate_scientific_report.py:27` : `from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS`

These imports must continue to work after this plan. The simplest way: keep `load_live_data`, `analyze_all`, and `SYMBOLS` importable from `scripts/analyze_live` by re-exporting them (import into the script from the new `src/` modules and leave them at module scope). Plan 012 will fix the layering violation properly.

### Repo conventions that apply

- Python 3.11+, type hints required on all functions.
- 4-space indentation, 120 char max line length.
- `snake_case` for functions/variables, `PascalCase` for classes.
- Functions max 30 lines (ideal < 15). The `generate_html` function (1,097 lines) and `analyze_symbol` (125 lines) both violate this. When extracting, break `generate_html` into smaller helper functions within `src/viz/dashboard.py`. Break `analyze_symbol` into sub-functions if it exceeds 30 lines after extraction (it calls the extracted functions, so it should shrink).
- Imports: stdlib first, third-party second, project imports third. See `src/analysis/correlation.py:1-10` for the exemplar pattern.
- No em-dash (the character `:`) anywhere. Use `:`, `.`, or `,` instead.
- No hardcoded API keys or secrets.
- No `try/except pass` (empty catch). The existing code has bare `except:` clauses in `calc_kyle_lambda` (line 154), `detect_breakpoints` (line 481), `cross_sectional_analysis` (line 523), `granger_causality` (line 580). When extracting, keep the existing error handling behavior but replace bare `except:` with `except Exception:` to satisfy ruff. Do NOT add new error handling logic.

## Commands you will need

| Purpose          | Command                              | Expected on success |
|------------------|--------------------------------------|---------------------|
| Run script help  | `python scripts/analyze_live.py --help` | exit 0, prints usage |
| Tests            | `pytest tests/ -v`                   | all pass            |
| Lint             | `ruff check src/`                    | exit 0              |
| Type check       | `mypy src/`                          | exit 0 (or same as before) |

## Scope

**In scope** (the only files you should modify or create):
- `scripts/analyze_live.py` (modify, shrink to orchestration)
- `src/analysis/indicators.py` (create)
- `src/analysis/microstructure.py` (create)
- `src/analysis/statistical.py` (create)
- `src/analysis/regime.py` (create)
- `src/analysis/cross_sectional.py` (create)
- `src/analysis/live_analysis.py` (create)
- `src/viz/dashboard.py` (create)

**Out of scope** (do NOT touch, even though they look related):
- `scripts/generate_report.py` : layering fix is plan 012.
- `scripts/generate_scientific_report.py` : layering fix is plan 012.
- `scripts/statistical_analyzer.py` : consolidation is plan 013.
- `scripts/analyze_correlations.py` : consolidation is plan 013.
- `scripts/analyze_microstructure.py` : consolidation is plan 013.
- `src/analysis/correlation.py`, `src/analysis/returns.py`, `src/analysis/graph.py` : existing modules, not touched.
- `src/analysis/__init__.py` : exports are plan 012.
- `src/viz/__init__.py` : exports are plan 012.
- Any test files : new tests are out of scope for this plan (testing the extracted modules is a follow-up).

## Git workflow

- Branch: `advisor/011-extract-analyze-live`
- Commit per step (one commit per module extraction). Message style: `refactor: extract <module> from analyze_live.py into src/analysis/<module>.py`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Create src/analysis/indicators.py with technical indicators

Create `src/analysis/indicators.py`. Move these 7 functions from `scripts/analyze_live.py` into it, verbatim (same logic, same signatures, same return types):

- `calc_rsi` (line 65)
- `calc_macd` (line 74)
- `calc_bollinger` (line 81)
- `calc_atr` (line 86)
- `calc_vwap` (line 93)
- `calc_supertrend` (line 97)
- `calc_fibonacci` (line 126)

Add proper imports at the top of the new file:
```python
"""Technical indicators: RSI, MACD, Bollinger, ATR, VWAP, SuperTrend, Fibonacci."""
from typing import Dict, Tuple

import numpy as np
import pandas as pd
```

In `scripts/analyze_live.py`, remove the 7 function definitions and add this import block after the existing third-party imports (around line 31):
```python
from src.analysis.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr,
    calc_vwap, calc_supertrend, calc_fibonacci,
)
```

The `calc_supertrend` function calls `calc_atr` internally (line 98). Since both are now in the same file, this works without changes.

**Verify**: `python scripts/analyze_live.py --help` exits 0. `ruff check src/` exits 0.

### Step 2: Create src/analysis/microstructure.py with microstructure metrics

Create `src/analysis/microstructure.py`. Move these 5 functions from `scripts/analyze_live.py`:

- `calc_cvd` (line 140)
- `calc_kyle_lambda` (line 147)
- `calc_amihud` (line 157)
- `calc_volume_profile` (line 164)
- `calc_order_book_metrics` (line 210)

Imports for the new file:
```python
"""Microstructure metrics: CVD, Kyle's lambda, Amihud illiquidity, volume profile, order book."""
from typing import Dict

import numpy as np
import pandas as pd
```

Replace the bare `except:` in `calc_kyle_lambda` (line 154) with `except Exception:` to satisfy ruff. Keep the same return value (`0.0`).

In `scripts/analyze_live.py`, remove the 5 function definitions and add:
```python
from src.analysis.microstructure import (
    calc_cvd, calc_kyle_lambda, calc_amihud,
    calc_volume_profile, calc_order_book_metrics,
)
```

**Verify**: `python scripts/analyze_live.py --help` exits 0. `ruff check src/` exits 0.

### Step 3: Create src/analysis/statistical.py with statistical analysis

Create `src/analysis/statistical.py`. Move these 6 functions from `scripts/analyze_live.py`:

- `test_stationarity_adf` (line 239)
- `test_stationarity_kpss` (line 252)
- `calc_hurst` (line 265)
- `calc_half_life` (line 320)
- `calc_var_cvar` (line 349)
- `calc_drawdowns` (line 370)

Imports for the new file:
```python
"""Statistical analysis: stationarity tests, Hurst exponent, half-life, VaR/CVaR, drawdowns."""
from typing import Dict

import numpy as np
import pandas as pd
```

Note: `calc_hurst` (line 301) and `calc_var_cvar` (line 358) have inline imports (`from statsmodels.tsa.stattools import adfuller`, `from scipy.stats import norm`). Move these inline imports to the top of the new file as module-level imports:
```python
from scipy.stats import linregress, norm
from statsmodels.tsa.stattools import adfuller, kpss
```

Then update the call sites: replace `__import__('scipy.stats').stats.linregress` (line 301) with `linregress`, and remove the inline `from scipy.stats import norm` (line 358) and `from statsmodels.tsa.stattools import adfuller` (line 240) / `kpss` (line 253) since they are now at module level.

Replace the bare `except:` in `calc_half_life` (line 346) with `except Exception:`.

In `scripts/analyze_live.py`, remove the 6 function definitions and add:
```python
from src.analysis.statistical import (
    test_stationarity_adf, test_stationarity_kpss, calc_hurst,
    calc_half_life, calc_var_cvar, calc_drawdowns,
)
```

**Verify**: `python scripts/analyze_live.py --help` exits 0. `ruff check src/` exits 0.

### Step 4: Create src/analysis/regime.py with regime detection

Create `src/analysis/regime.py`. Move these 2 functions from `scripts/analyze_live.py`:

- `detect_regimes_hmm` (line 406)
- `detect_breakpoints` (line 469)

Imports for the new file:
```python
"""Regime detection: HMM hidden states and structural breakpoints."""
from typing import Dict, List

import numpy as np
import pandas as pd
```

Note: `detect_regimes_hmm` has inline imports (`from sklearn.preprocessing import StandardScaler`, `from hmmlearn import hmm` at lines 418-419) and `detect_breakpoints` has `import ruptures as rpt` (line 475). Keep these as inline imports inside the function bodies (they are optional dependencies with try/except fallback). Replace the bare `except:` in `detect_breakpoints` (line 481) with `except Exception:`. The `detect_regimes_hmm` already uses `except Exception as e:` (line 460), keep it.

Replace `__import__('scipy.stats').stats.skew` (line 444) with a top-level import: add `from scipy.stats import skew` to the file imports and call `skew(reg_returns)` directly.

In `scripts/analyze_live.py`, remove the 2 function definitions and add:
```python
from src.analysis.regime import detect_regimes_hmm, detect_breakpoints
```

**Verify**: `python scripts/analyze_live.py --help` exits 0. `ruff check src/` exits 0.

### Step 5: Create src/analysis/cross_sectional.py with cross-sectional analysis

Create `src/analysis/cross_sectional.py`. Move these 3 functions from `scripts/analyze_live.py`:

- `cross_sectional_analysis` (line 486)
- `cross_correlation` (line 536)
- `granger_causality` (line 561)

Imports for the new file:
```python
"""Cross-sectional analysis: correlation, lead-lag, Granger causality, PCA."""
from typing import Dict

import numpy as np
import pandas as pd
```

Note: `cross_sectional_analysis` has an inline import `from sklearn.decomposition import PCA` (line 516) inside a try/except. Keep it inline. `granger_causality` has `from statsmodels.tsa.stattools import grangercausalitytests` (line 562). Move this to the module-level imports.

Replace the bare `except:` in `cross_sectional_analysis` (line 523) and `granger_causality` (line 580) with `except Exception:`.

In `scripts/analyze_live.py`, remove the 3 function definitions and add:
```python
from src.analysis.cross_sectional import (
    cross_sectional_analysis, cross_correlation, granger_causality,
)
```

**Verify**: `python scripts/analyze_live.py --help` exits 0. `ruff check src/` exits 0.

### Step 6: Create src/analysis/live_analysis.py with data loading and analysis pipeline

Create `src/analysis/live_analysis.py`. Move these 4 functions from `scripts/analyze_live.py`:

- `load_live_data` (line 585)
- `build_ohlcv_from_trades` (line 604)
- `analyze_symbol` (line 638, 125 lines)
- `analyze_all` (line 764)

Also move the `SYMBOLS` constant (line 38) into this file.

Imports for the new file:
```python
"""Live data loading and per-symbol analysis pipeline."""
import glob
import time
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

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
from src.analysis.cross_sectional import cross_sectional_analysis
```

The `analyze_symbol` function is 125 lines. After extraction it will still be 125 lines because it calls the extracted functions. Break it into sub-functions if it exceeds 30 lines. The function body has clear sections: technical indicators (lines 650-657), microstructure (lines 660-664), statistical (lines 667-675), funding/OI/LS (lines 678-680), chart sampling (lines 682-687), and return dict construction (lines 689-762). Extract each section into a helper function (e.g. `_compute_technical(ohlcv)`, `_compute_microstructure(trades, returns, ohlcv)`, `_compute_statistical(close, returns)`, `_compute_positioning(funding, oi, ls, symbol)`, `_build_chart_data(ohlcv, rsi, macd, ...)`). Each helper should be under 30 lines.

In `scripts/analyze_live.py`, remove the 4 function definitions and the `SYMBOLS` constant. Add:
```python
from src.analysis.live_analysis import (
    SYMBOLS, load_live_data, build_ohlcv_from_trades,
    analyze_symbol, analyze_all,
)
```

Keep `SYMBOLS` importable at the `scripts.analyze_live` module scope so that `scripts/generate_report.py:28` and `scripts/generate_scientific_report.py:27` continue to work (they import `SYMBOLS` from `scripts.analyze_live`). This re-export is intentional and will be fixed in plan 012.

**Verify**: `python scripts/analyze_live.py --help` exits 0. `pytest tests/ -v` exits 0. `ruff check src/` exits 0.

### Step 7: Create src/viz/dashboard.py with HTML generation

Create `src/viz/dashboard.py`. Move these 2 functions from `scripts/analyze_live.py`:

- `fmt_usd` (line 813, module-level version)
- `generate_html` (line 820, 1,097 lines)

Also move the `COLORS` constant (lines 44-59) and `SYM_COLORS` constant (line 61) into this file, since they are only used by `generate_html`.

Imports for the new file:
```python
"""HTML dashboard generation for the live analysis terminal."""
from typing import Dict

import numpy as np

COLORS = {
    'bg': '#0B0E14',
    'surface': '#131722',
    'surface2': '#1A1E2D',
    'border': '#232838',
    'text': '#D1D4DC',
    'text_dim': '#787B86',
    'bull': '#26A69A',
    'bear': '#EF5350',
    'warn': '#FF9800',
    'info': '#42A5F5',
    'purple': '#AB47BC',
    'cyan': '#26C6DA',
    'orange': '#FF7043',
    'grid': '#1E222D',
}

SYM_COLORS = ['#42A5F5', '#26A69A', '#AB47BC', '#FF9800', '#26C6DA', '#FF7043', '#66BB6A', '#EC407A']
```

The `generate_html` function is 1,097 lines and contains nested helper functions (`badge` at line 827, `fmt_usd` at line 830, `class_for_value` at line 836, and likely more). Move the entire function as-is into `src/viz/dashboard.py`. The nested `fmt_usd` (line 830) shadows the module-level `fmt_usd` (line 813). Keep both: the module-level one is for external use, the nested one is internal to `generate_html`.

IMPORTANT: `generate_html` at 1,097 lines violates the 30-line function rule. However, refactoring the HTML template string construction into smaller functions is a large effort that risks breaking the HTML output. For this plan, move it as-is. A follow-up plan can break it down. Add a `# noqa: C901, PLR0915` comment on the `def generate_html` line to suppress ruff complexity/length warnings, with a `# TODO: break into smaller functions` comment explaining the deferral.

In `scripts/analyze_live.py`, remove the `COLORS`, `SYM_COLORS` constants, the `fmt_usd` function, and the `generate_html` function. Add:
```python
from src.viz.dashboard import generate_html
```

Note: `COLORS` and `SYM_COLORS` may be referenced elsewhere in `scripts/analyze_live.py` (e.g. in `main()` or other functions). Check with `grep -n "COLORS\|SYM_COLORS" scripts/analyze_live.py` before removing. If they are only used in `generate_html`, remove them from the script. If used elsewhere, add `from src.viz.dashboard import COLORS, SYM_COLORS` to the script.

**Verify**: `python scripts/analyze_live.py --help` exits 0. `pytest tests/ -v` exits 0. `ruff check src/` exits 0.

### Step 8: Clean up remaining imports in scripts/analyze_live.py

After all extractions, `scripts/analyze_live.py` should contain only:
- The module docstring (lines 1-18)
- `sys.path.insert` (lines 33-34)
- Import statements (stdlib + third-party + the new `from src.analysis.*` and `from src.viz.dashboard` imports)
- The `main()` function (lines 1918-1945)
- `if __name__ == "__main__": main()` (lines 1944-1945)

Remove any now-unused imports. For example, if `glob`, `time`, `defaultdict`, `warnings`, `np`, `pd` are no longer used directly in the script (only used in extracted modules), remove them from the script's imports. Run `ruff check scripts/analyze_live.py` to identify unused imports (F401).

The `main()` function calls `load_live_data`, `analyze_all`, and `generate_html`. These are now imported from `src/`. Verify the call sites match.

Remove the `DATA_DIR`, `UPDATE_INTERVAL_MS`, `WS_BATCH_MS` constants (lines 39-41) if they are only used in `generate_html` (which is now in `src/viz/dashboard.py`). Check with grep first.

**Verify**: `python scripts/analyze_live.py --help` exits 0. `pytest tests/ -v` exits 0. `ruff check src/ scripts/analyze_live.py` exits 0.

### Step 9: Verify external callers still work

Run a quick import check to confirm the two report scripts can still import from `scripts.analyze_live`:
```bash
python -c "from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS; print('OK')"
```

This should print `OK` and exit 0. If it fails, the re-exports in step 6 are missing or broken.

**Verify**: `python -c "from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS; print('OK')"` prints `OK`, exit 0.

## Test plan

No new tests are written in this plan. The existing test suite (`pytest tests/ -v`) must continue to pass after each step. New tests for the extracted modules are a follow-up (out of scope).

The key regression risk is that the extracted functions produce identical outputs. Since the functions are moved verbatim (same logic, same signatures), the outputs should be identical. If any function's behavior changes, `pytest tests/ -v` or `python scripts/analyze_live.py --help` will catch import errors. However, there are no existing tests that exercise the analysis pipeline end-to-end. If the operator wants to verify numerical correctness, they can run `python scripts/analyze_live.py --data-dir data/live --output /tmp/test_dashboard.html` and compare the output to a pre-extraction baseline.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `python scripts/analyze_live.py --help` exits 0
- [ ] `pytest tests/ -v` exits 0
- [ ] `ruff check src/` exits 0
- [ ] `ruff check scripts/analyze_live.py` exits 0 (no unused imports)
- [ ] `python -c "from scripts.analyze_live import load_live_data, analyze_all, SYMBOLS; print('OK')"` prints `OK`, exit 0
- [ ] `grep -c "^def " scripts/analyze_live.py` returns 1 (only `main`)
- [ ] `wc -l scripts/analyze_live.py` returns under 80 lines
- [ ] All 7 new files exist: `src/analysis/indicators.py`, `src/analysis/microstructure.py`, `src/analysis/statistical.py`, `src/analysis/regime.py`, `src/analysis/cross_sectional.py`, `src/analysis/live_analysis.py`, `src/viz/dashboard.py`
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts (the codebase has drifted since this plan was written). Run `grep -n "^def calc_rsi" scripts/analyze_live.py` and confirm it returns line 65. If not, STOP.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file (e.g. you need to modify `scripts/generate_report.py` to make imports work).
- You discover that `generate_html` cannot be moved without also moving constants (`COLORS`, `SYM_COLORS`, `DATA_DIR`, `UPDATE_INTERVAL_MS`, `WS_BATCH_MS`) that are used by other functions still in the script. In that case, STOP and report which constants are shared.
- You discover that `analyze_symbol` cannot be broken into sub-functions under 30 lines without changing its return dict structure. In that case, keep it as one function with a `# noqa: C901` comment and report this deviation.

## Maintenance notes

- After this plan lands, `scripts/analyze_live.py` is a thin orchestrator. Future changes to analysis logic should go in `src/analysis/*.py`, not the script.
- `generate_html` in `src/viz/dashboard.py` is still 1,097 lines. A follow-up plan should break it into smaller template functions (e.g. `_render_kpi_cards`, `_render_correlation_matrix`, `_render_microstructure_panel`). This is deferred because the HTML template strings are fragile and breaking them risks visual regressions.
- `analyze_symbol` in `src/analysis/live_analysis.py` may still exceed 30 lines if the sub-function extraction in step 6 is not possible. Review the function after extraction and file a follow-up if it remains over 30 lines.
- Plan 012 depends on this plan: it fixes the layering violations in `scripts/generate_report.py` and `scripts/generate_scientific_report.py` by updating them to import from `src/` instead of `scripts.analyze_live`. Do not start plan 012 until this plan is done.
- Plan 013 depends on this plan: it consolidates `scripts/statistical_analyzer.py`, `scripts/analyze_correlations.py`, and `scripts/analyze_microstructure.py` into the new `src/analysis/` modules.
- A reviewer should scrutinize: (1) that no function logic changed during the move (diff should be pure code movement), (2) that bare `except:` clauses were replaced with `except Exception:` without changing behavior, (3) that inline imports were moved to module level only where the plan specified, and (4) that `SYMBOLS` is still importable from `scripts.analyze_live`.
