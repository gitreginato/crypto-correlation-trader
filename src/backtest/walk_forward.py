"""Walk-forward analysis for strategy validation.

Splits data into in-sample (IS) and out-of-sample (OOS) windows,
runs backtest on each, and validates that OOS performance is
acceptable relative to IS performance.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.backtest.engine import BacktestConfig, BacktestEngine
from src.strategy.base import BaseStrategy


@dataclass
class WalkForwardConfig:
    is_window: int = 180  # in-sample window (bars)
    oos_window: int = 60  # out-of-sample window (bars)
    step: int = 60  # step between windows (bars)
    min_is_sharpe: float = 0.5  # minimum IS Sharpe to proceed to OOS
    max_degradation: float = 0.50  # max IS-OOS Sharpe degradation (50%)


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
    degradation: float  # (IS - OOS) / IS
    passed: bool


class WalkForwardAnalyzer:
    """Walk-forward analysis for strategy validation."""

    def __init__(self, strategy: BaseStrategy, bt_config: BacktestConfig | None = None,
                 wf_config: WalkForwardConfig | None = None):
        self.strategy = strategy
        self.bt_config = bt_config or BacktestConfig()
        self.wf_config = wf_config or WalkForwardConfig()

    def run(self, data: dict[str, pd.DataFrame]) -> list[WalkForwardResult]:
        """Run walk-forward analysis.

        Args:
            data: Dict mapping symbol to OHLCV DataFrame.

        Returns:
            List of WalkForwardResult, one per window.
        """
        # Get common index
        all_indices = pd.DatetimeIndex(sorted(set().union(*[df.index for df in data.values()])))
        n = len(all_indices)
        results = []

        start = 0
        while start + self.wf_config.is_window + self.wf_config.oos_window <= n:
            is_end = start + self.wf_config.is_window
            oos_end = is_end + self.wf_config.oos_window

            is_indices = all_indices[start:is_end]
            oos_indices = all_indices[is_end:oos_end]

            is_data = {s: data[s].loc[is_indices[0]:is_indices[-1]] for s in data}
            oos_data = {s: data[s].loc[oos_indices[0]:oos_indices[-1]] for s in data}

            # Run IS backtest
            is_engine = BacktestEngine(self.strategy, self.bt_config)
            is_metrics = is_engine.run(is_data)

            # Run OOS backtest
            oos_engine = BacktestEngine(self.strategy, self.bt_config)
            oos_metrics = oos_engine.run(oos_data)

            # Compute degradation
            if is_metrics["sharpe"] != 0:
                degradation = (is_metrics["sharpe"] - oos_metrics["sharpe"]) / abs(is_metrics["sharpe"])
            else:
                degradation = 1.0 if oos_metrics["sharpe"] <= 0 else 0.0

            passed = (
                is_metrics["sharpe"] >= self.wf_config.min_is_sharpe
                and degradation <= self.wf_config.max_degradation
                and oos_metrics["sharpe"] > 0
            )

            results.append(WalkForwardResult(
                is_sharpe=is_metrics["sharpe"],
                oos_sharpe=oos_metrics["sharpe"],
                is_return=is_metrics["total_return"],
                oos_return=oos_metrics["total_return"],
                is_max_dd=is_metrics["max_drawdown"],
                oos_max_dd=oos_metrics["max_drawdown"],
                is_trades=is_metrics["num_trades"],
                oos_trades=oos_metrics["num_trades"],
                degradation=degradation,
                passed=passed,
            ))

            start += self.wf_config.step

        return results

    def summarize(self, results: list[WalkForwardResult]) -> dict:
        """Summarize walk-forward results."""
        if not results:
            return {"passed_windows": 0, "total_windows": 0, "pass_rate": 0}

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return {
            "passed_windows": passed,
            "total_windows": total,
            "pass_rate": passed / total,
            "avg_is_sharpe": np.mean([r.is_sharpe for r in results]),
            "avg_oos_sharpe": np.mean([r.oos_sharpe for r in results]),
            "avg_degradation": np.mean([r.degradation for r in results]),
            "avg_oos_return": np.mean([r.oos_return for r in results]),
            "avg_oos_max_dd": np.mean([r.oos_max_dd for r in results]),
            "avg_oos_trades": np.mean([r.oos_trades for r in results]),
        }


def print_walk_forward(results: list[WalkForwardResult], summary: dict) -> None:
    """Print walk-forward results in a readable format."""
    print(f"\n{'='*70}")
    print("  WALK-FORWARD ANALYSIS")
    print(f"{'='*70}")
    print(f"  Windows passed:    {summary['passed_windows']}/{summary['total_windows']} ({summary['pass_rate']:.0%})")
    print(f"  Avg IS Sharpe:     {summary['avg_is_sharpe']:.2f}")
    print(f"  Avg OOS Sharpe:    {summary['avg_oos_sharpe']:.2f}")
    print(f"  Avg Degradation:   {summary['avg_degradation']:.1%}")
    print(f"  Avg OOS Return:    {summary['avg_oos_return']:.2%}")
    print(f"  Avg OOS Max DD:    {summary['avg_oos_max_dd']:.2%}")
    print(f"  Avg OOS Trades:    {summary['avg_oos_trades']:.0f}")
    print(f"{'='*70}")
    print(f"\n  {'Window':>6} | {'IS Sharpe':>10} | {'OOS Sharpe':>11} | "
          f"{'IS Ret':>8} | {'OOS Ret':>8} | {'OOS DD':>8} | {'Pass':>5}")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*11}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*5}")
    for i, r in enumerate(results):
        status = "PASS" if r.passed else "FAIL"
        print(f"  {i+1:>6} | {r.is_sharpe:>10.2f} | {r.oos_sharpe:>11.2f} | "
              f"{r.is_return:>7.2%} | {r.oos_return:>7.2%} | {r.oos_max_dd:>7.2%} | {status:>5}")
