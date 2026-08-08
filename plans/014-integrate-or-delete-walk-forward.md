# Plan 014: Integrate or delete walk-forward module

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/run_backtest.py src/backtest/walk_forward.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

`src/backtest/walk_forward.py` (147 lines) is a complete, functional walk-forward analysis module with `WalkForwardAnalyzer`, `WalkForwardConfig`, `WalkForwardResult`, and a `print_walk_forward` helper. It is never imported anywhere in the codebase (zero references). Dead code is a maintenance burden: it rots silently, confuses readers who assume it is used, and may break when dependencies change without anyone noticing. The fix is to either integrate it into `scripts/run_backtest.py` via a `--walk-forward` flag (making it useful) or delete it (removing the burden). This plan defaults to integration since the module is complete and walk-forward validation is a documented best practice in `AGENTS.md` (section 4: "SEMPRE separar in-sample e out-of-sample").

## Current state

The relevant files, each with one line on its role:

- `src/backtest/walk_forward.py` (147 lines) : complete walk-forward analysis module. Never imported anywhere.
- `scripts/run_backtest.py` (230 lines) : backtest runner script. Supports `--strategy` flag with choices `all`, `momentum`, `mean_reversion`, `stat_arb`, `meta`. Does NOT support walk-forward analysis.

### src/backtest/walk_forward.py structure

```python
"""Walk-forward analysis for strategy validation."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Callable

from src.backtest.engine import BacktestEngine, BacktestConfig
from src.strategy.base import BaseStrategy


@dataclass
class WalkForwardConfig:
    is_window: int = 180       # in-sample window (bars)
    oos_window: int = 60       # out-of-sample window (bars)
    step: int = 60             # step between windows (bars)
    min_is_sharpe: float = 0.5
    max_degradation: float = 0.50


@dataclass
class WalkForwardResult:
    is_sharpe: float
    oos_sharpe: float
    is_return: float
    oos_return: float
    is_max_dd: float
    oos_max_dd: float
    is_trades: int
    oos_trades: int
    degradation: float
    passed: bool


class WalkForwardAnalyzer:
    def __init__(self, strategy: BaseStrategy, bt_config: BacktestConfig = None, wf_config: WalkForwardConfig = None):
        ...
    def run(self, data: dict[str, pd.DataFrame]) -> list[WalkForwardResult]:
        ...
    def summarize(self, results: list[WalkForwardResult]) -> dict:
        ...


def print_walk_forward(results: list[WalkForwardResult], summary: dict) -> None:
    ...
```

The `WalkForwardAnalyzer.run()` method (line 47) splits data into in-sample and out-of-sample windows, runs `BacktestEngine` on each, computes Sharpe degradation, and returns a list of `WalkForwardResult`. The `summarize()` method (line 109) aggregates results. The `print_walk_forward()` function (line 130) prints a formatted table.

### scripts/run_backtest.py structure

```python
"""Run backtests for individual strategies using real downloaded data."""
import argparse
import sys
from pathlib import Path

from src.data.parquet_store import ParquetStore
from src.backtest.engine import BacktestEngine, BacktestConfig
from src.strategy.momentum import MomentumStrategy, MomentumConfig
from src.strategy.mean_reversion import MeanReversionStrategy, MeanReversionConfig
from src.strategy.stat_arb import StatArbStrategy, StatArbConfig
from src.strategy.regime_filter import RegimeFilter, Regime
from src.strategy.meta import MetaStrategy, MetaStrategyConfig


def load_data(symbols: list[str], timeframe: str = "1d") -> dict[str, pd.DataFrame]:
    ...

def run_momentum_backtest(data: dict[str, pd.DataFrame]) -> dict:
    ...

def run_mean_reversion_backtest(data: dict[str, pd.DataFrame]) -> dict:
    ...

def run_stat_arb_backtest(data: dict[str, pd.DataFrame]) -> dict:
    ...

def run_meta_backtest(data: dict[str, pd.DataFrame]) -> dict:
    ...

def print_metrics(name: str, metrics: dict):
    ...

def main():
    parser = argparse.ArgumentParser(description="Run strategy backtests")
    parser.add_argument("--strategy", type=str, default="all",
        choices=["all", "momentum", "mean_reversion", "stat_arb", "meta"], ...)
    parser.add_argument("--timeframe", type=str, default="1d", ...)
    args = parser.parse_args()
    ...
```

The `main()` function (line 178) loads data, runs the requested strategy backtests, and prints results. It does NOT support walk-forward analysis.

### Verification: zero imports of walk_forward

Confirm the module is unused:
```bash
grep -rn "walk_forward\|WalkForwardAnalyzer\|WalkForwardConfig\|WalkForwardResult" --include="*.py" .
```

This should return matches only in `src/backtest/walk_forward.py` itself (and possibly `src/backtest/__init__.py` if plan 012 added exports). If it returns matches in other files, the module is already used somewhere and this plan may not be needed. STOP and report.

### Repo conventions that apply

- Python 3.11+, type hints required.
- 4-space indentation, 120 char max line length.
- `snake_case` for functions/variables, `PascalCase` for classes.
- Functions max 30 lines.
- Imports: stdlib first, third-party second, project imports third.
- No em-dash (the character `:`). Use `:`, `.`, or `,` instead.
- Backtest rules (AGENTS.md section 4): "SEMPRE separar in-sample e out-of-sample", "Reportar metricas OOS, nao IS". Walk-forward analysis directly supports this requirement.

## Commands you will need

| Purpose          | Command                                      | Expected on success |
|------------------|----------------------------------------------|---------------------|
| Tests            | `pytest tests/test_backtest_engine.py -v`    | all pass            |
| Script help      | `python scripts/run_backtest.py --help`      | exit 0, prints usage |
| Lint             | `ruff check src/ scripts/run_backtest.py`    | exit 0              |
| Type check       | `mypy src/`                                  | exit 0 (or same)    |

## Scope

**In scope** (the only files you should modify):
- `scripts/run_backtest.py` (modify to add `--walk-forward` flag)
- `src/backtest/walk_forward.py` (keep as-is, or delete if operator chooses deletion)

**Out of scope** (do NOT touch):
- `src/backtest/engine.py` : the backtest engine, not modified.
- `src/strategy/*.py` : strategy implementations, not modified.
- `src/backtest/__init__.py` : exports handled in plan 012.
- Any test files.
- Any other scripts.

## Git workflow

- Branch: `advisor/014-integrate-walk-forward`
- Single commit. Message: `feat: add --walk-forward flag to run_backtest.py` (if integrating) or `refactor: delete unused walk_forward.py` (if deleting).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Verify walk_forward.py is unused

Run:
```bash
grep -rn "walk_forward\|WalkForwardAnalyzer\|WalkForwardConfig\|WalkForwardResult" --include="*.py" /home/lucas/Projetos/crypto-correl-bot/
```

Filter out matches in `src/backtest/walk_forward.py` itself and `src/backtest/__init__.py` (if plan 012 added exports). If there are matches in any other file, the module is already used. STOP and report.

**Verify**: The grep returns matches only in `walk_forward.py` and optionally `__init__.py`.

### Step 2: Add --walk-forward flag to scripts/run_backtest.py

This is the default action (integration). Only proceed to step 3 (deletion) if the operator explicitly chose deletion.

In `scripts/run_backtest.py`:

1. Add this import after the existing `src.backtest` imports (around line 18):
```python
from src.backtest.walk_forward import (
    WalkForwardAnalyzer, WalkForwardConfig, print_walk_forward,
)
```

2. Add a `--walk-forward` flag to the argument parser in `main()` (after line 185, the `--timeframe` argument):
```python
    parser.add_argument(
        "--walk-forward", action="store_true", default=False,
        help="Run walk-forward validation (IS/OOS windows) instead of single backtest",
    )
```

3. Add a `--is-window` and `--oos-window` flag for walk-forward configuration:
```python
    parser.add_argument("--is-window", type=int, default=180, help="In-sample window size (bars)")
    parser.add_argument("--oos-window", type=int, default=60, help="Out-of-sample window size (bars)")
    parser.add_argument("--step", type=int, default=60, help="Step between walk-forward windows (bars)")
```

4. After the data loading section (around line 201) and before the backtest execution section, add a branch for walk-forward mode. The walk-forward analysis needs a strategy instance, not just the `run_*_backtest` functions (which create the strategy internally). Refactor: extract the strategy creation from each `run_*_backtest` function into a helper, or create a new function that returns the strategy and config for a given strategy name.

Add this function before `main()`:
```python
def get_strategy_and_config(name: str) -> tuple[BaseStrategy, BacktestConfig]:
    """Return strategy instance and backtest config for a given strategy name."""
    if name == "momentum":
        strategy = MomentumStrategy(MomentumConfig(
            formation_period=30, ema_fast=10, ema_slow=20,
            adx_threshold=20, min_confirmation=2, use_regime_filter=True,
        ))
    elif name == "mean_reversion":
        strategy = MeanReversionStrategy(MeanReversionConfig(
            correlation_window=60, zscore_window=20,
            entry_zscore=2.0, exit_zscore=0.5,
            correlation_threshold=0.5, min_cluster_size=2,
        ))
    elif name == "stat_arb":
        strategy = StatArbStrategy(StatArbConfig(
            lookback_window=100, zscore_window=20,
            entry_zscore=2.0, exit_zscore=0.5,
            min_correlation=0.5, min_half_life=1.0,
            max_half_life=50, adf_pvalue_threshold=0.05,
            max_pairs=5,
        ))
    elif name == "meta":
        strategy = MetaStrategy(MetaStrategyConfig(
            momentum_config=MomentumConfig(
                formation_period=30, ema_fast=10, ema_slow=20,
                adx_threshold=20, min_confirmation=2, use_regime_filter=False,
            ),
            mean_reversion_config=MeanReversionConfig(
                correlation_window=60, zscore_window=20,
                entry_zscore=2.0, exit_zscore=0.5,
                correlation_threshold=0.5, min_cluster_size=2,
            ),
            stat_arb_config=StatArbConfig(
                lookback_window=100, zscore_window=20,
                entry_zscore=2.0, exit_zscore=0.5,
                min_correlation=0.5, min_half_life=1.0,
                max_half_life=50, adf_pvalue_threshold=0.05,
                max_pairs=5,
            ),
            max_signals_per_bar=5, min_confidence=0.3,
        ))
    else:
        raise ValueError(f"Unknown strategy: {name}")

    bt_config = BacktestConfig(
        initial_capital=10000.0, risk_per_trade=0.02,
        fee_rate=0.001, slippage_rate=0.0005, max_positions=10,
    )
    return strategy, bt_config
```

IMPORTANT: This function may exceed 30 lines. If it does, break it into sub-functions: `_get_momentum()`, `_get_mean_reversion()`, `_get_stat_arb()`, `_get_meta()`, each returning `(strategy, bt_config)`. The `get_strategy_and_config` function then dispatches to the appropriate helper. Each helper should be under 30 lines.

5. Add the walk-forward execution branch in `main()`, after the data loading and before the single-backtest execution:
```python
    if args.walk_forward:
        if args.strategy == "all":
            print("Walk-forward mode requires a single strategy. Specify --strategy <name>.")
            sys.exit(1)

        print(f"\nRunning walk-forward analysis for {args.strategy}...")
        strategy, bt_config = get_strategy_and_config(args.strategy)
        wf_config = WalkForwardConfig(
            is_window=args.is_window,
            oos_window=args.oos_window,
            step=args.step,
        )
        analyzer = WalkForwardAnalyzer(strategy, bt_config, wf_config)
        wf_results = analyzer.run(data)
        summary = analyzer.summarize(wf_results)
        print_walk_forward(wf_results, summary)
        return
```

6. Add `from src.strategy.base import BaseStrategy` to the imports if not already present (needed for the type hint in `get_strategy_and_config`).

**Verify**: `python scripts/run_backtest.py --help` exits 0 and shows `--walk-forward`, `--is-window`, `--oos-window`, `--step` flags. `pytest tests/test_backtest_engine.py -v` exits 0. `ruff check scripts/run_backtest.py` exits 0.

### Step 3 (alternative): Delete walk_forward.py if not needed

ONLY execute this step if the operator explicitly chose deletion instead of integration. If step 2 was executed, skip this step entirely.

1. Delete `src/backtest/walk_forward.py`:
```bash
rm src/backtest/walk_forward.py
```

2. If `src/backtest/__init__.py` (plan 012) exports `WalkForwardAnalyzer`, `WalkForwardConfig`, or `WalkForwardResult`, remove those imports and `__all__` entries.

3. Run `grep -rn "walk_forward\|WalkForwardAnalyzer\|WalkForwardConfig\|WalkForwardResult" --include="*.py" .` to confirm no remaining references.

**Verify**: `pytest tests/test_backtest_engine.py -v` exits 0. `ruff check src/` exits 0. `grep -rn "walk_forward" --include="*.py" .` returns no matches.

### Step 4: Final verification

Run all verification commands:
```bash
pytest tests/test_backtest_engine.py -v
python scripts/run_backtest.py --help
ruff check src/ scripts/run_backtest.py
mypy src/
```

**Verify**: All commands exit 0. `--help` output includes `--walk-forward` flag (if integrating) or the file is gone (if deleting).

## Test plan

No new tests are written in this plan. The existing `tests/test_backtest_engine.py` must continue to pass. Walk-forward specific tests are a follow-up (out of scope).

If the operator wants to verify the walk-forward integration works end-to-end, they can run:
```bash
python scripts/run_backtest.py --strategy momentum --walk-forward --is-window 60 --oos-window 20 --step 20
```

This requires downloaded data in `data/parquet/`. If no data is available, the script will print "No data found" and exit 1, which is expected behavior (not a failure of this plan).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_backtest_engine.py -v` exits 0
- [ ] `python scripts/run_backtest.py --help` exits 0
- [ ] `ruff check src/ scripts/run_backtest.py` exits 0
- [ ] If integrating: `python scripts/run_backtest.py --help` output includes `--walk-forward` flag
- [ ] If integrating: `grep -n "WalkForwardAnalyzer" scripts/run_backtest.py` returns at least one match
- [ ] If deleting: `ls src/backtest/walk_forward.py` fails (file does not exist)
- [ ] If deleting: `grep -rn "walk_forward" --include="*.py" .` returns no matches
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts. Run `grep -n "class WalkForwardAnalyzer" src/backtest/walk_forward.py` and confirm it returns line 39. If not, STOP.
- The grep in step 1 shows that `walk_forward.py` is already imported somewhere (besides itself and `__init__.py`). STOP and report where it is used.
- The `get_strategy_and_config` function in step 2 cannot be broken into sub-functions under 30 lines. STOP and report.
- The `WalkForwardAnalyzer.run()` method requires a different data format than what `load_data()` in `run_backtest.py` provides. Check: `run()` expects `dict[str, pd.DataFrame]` where each DataFrame has OHLCV columns. `load_data()` returns `dict[str, pd.DataFrame]` with columns `["open", "high", "low", "close", "volume"]`. If these are incompatible, STOP and report.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- After this plan (integration path), `scripts/run_backtest.py --walk-forward` provides IS/OOS validation as required by `AGENTS.md` section 4. Future strategy development should use this flag to validate before deploying.
- The `get_strategy_and_config` function duplicates the strategy configuration that was previously inline in `run_*_backtest` functions. If a strategy config changes, it must be updated in both places. A future refactor could have `run_*_backtest` call `get_strategy_and_config` to eliminate this duplication.
- If the deletion path was chosen, walk-forward analysis is no longer available. If it is needed later, it can be recovered from git history (the `pre-commit` state).
- A reviewer should scrutinize: (1) that the `--walk-forward` flag correctly delegates to `WalkForwardAnalyzer`, (2) that the `--strategy all` guard prevents ambiguous behavior, and (3) that the walk-forward config flags (`--is-window`, `--oos-window`, `--step`) are correctly passed through.
