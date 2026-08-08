"""Run backtests for individual strategies using real downloaded data.

Usage:
    python scripts/run_backtest.py [--strategy all|momentum|mean_reversion|stat_arb]
"""
import argparse
import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

from src.backtest.engine import BacktestConfig, BacktestEngine
from src.data.parquet_store import ParquetStore
from src.strategy.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from src.strategy.meta import MetaStrategy, MetaStrategyConfig
from src.strategy.momentum import MomentumConfig, MomentumStrategy
from src.strategy.stat_arb import StatArbConfig, StatArbStrategy


def load_data(symbols: list[str], timeframe: str = "1d") -> dict[str, pd.DataFrame]:
    """Load OHLCV data from Parquet store for given symbols."""
    store = ParquetStore(base_dir="data/parquet")
    data = {}
    for sym in symbols:
        df = store.read(sym, timeframe)
        if df.empty:
            print(f"  No data for {sym}")
            continue
        # Set index to open_time and ensure OHLCV columns
        df = df.set_index("open_time")
        df.index = df.index.tz_localize(None)  # remove tz for consistency
        # Ensure required columns
        required = ["open", "high", "low", "close", "volume"]
        if not all(c in df.columns for c in required):
            print(f"  Missing columns for {sym}")
            continue
        data[sym] = df[required].dropna()
        print(f"  Loaded {sym}: {len(data[sym])} bars ({data[sym].index[0]} to {data[sym].index[-1]})")
    return data


def run_momentum_backtest(data: dict[str, pd.DataFrame]) -> dict:
    """Run momentum strategy backtest."""
    config = MomentumConfig(
        formation_period=30,
        ema_fast=10,
        ema_slow=20,
        adx_threshold=20,
        min_confirmation=2,
        use_regime_filter=True,
    )
    strategy = MomentumStrategy(config)
    bt_config = BacktestConfig(
        initial_capital=10000.0,
        risk_per_trade=0.02,
        fee_rate=0.001,
        slippage_rate=0.0005,
        max_positions=5,
    )
    engine = BacktestEngine(strategy, bt_config)
    return engine.run(data)


def run_mean_reversion_backtest(data: dict[str, pd.DataFrame]) -> dict:
    """Run mean reversion strategy backtest."""
    config = MeanReversionConfig(
        correlation_window=60,
        zscore_window=20,
        entry_zscore=2.0,
        exit_zscore=0.5,
        correlation_threshold=0.5,
        min_cluster_size=2,
    )
    strategy = MeanReversionStrategy(config)
    bt_config = BacktestConfig(
        initial_capital=10000.0,
        risk_per_trade=0.02,
        fee_rate=0.001,
        slippage_rate=0.0005,
        max_positions=5,
    )
    engine = BacktestEngine(strategy, bt_config)
    return engine.run(data)


def run_stat_arb_backtest(data: dict[str, pd.DataFrame]) -> dict:
    """Run statistical arbitrage strategy backtest."""
    config = StatArbConfig(
        lookback_window=100,
        zscore_window=20,
        entry_zscore=2.0,
        exit_zscore=0.5,
        min_correlation=0.5,
        min_half_life=1.0,
        max_half_life=50,
        adf_pvalue_threshold=0.05,
        max_pairs=5,
    )
    strategy = StatArbStrategy(config)
    bt_config = BacktestConfig(
        initial_capital=10000.0,
        risk_per_trade=0.02,
        fee_rate=0.001,
        slippage_rate=0.0005,
        max_positions=10,
    )
    engine = BacktestEngine(strategy, bt_config)
    return engine.run(data)


def run_meta_backtest(data: dict[str, pd.DataFrame]) -> dict:
    """Run combined meta-strategy backtest with regime filtering."""
    config = MetaStrategyConfig(
        momentum_config=MomentumConfig(
            formation_period=30,
            ema_fast=10,
            ema_slow=20,
            adx_threshold=20,
            min_confirmation=2,
            use_regime_filter=False,  # meta-strategy handles regime filtering
        ),
        mean_reversion_config=MeanReversionConfig(
            correlation_window=60,
            zscore_window=20,
            entry_zscore=2.0,
            exit_zscore=0.5,
            correlation_threshold=0.5,
            min_cluster_size=2,
        ),
        stat_arb_config=StatArbConfig(
            lookback_window=100,
            zscore_window=20,
            entry_zscore=2.0,
            exit_zscore=0.5,
            min_correlation=0.5,
            min_half_life=1.0,
            max_half_life=50,
            adf_pvalue_threshold=0.05,
            max_pairs=5,
        ),
        max_signals_per_bar=5,
        min_confidence=0.3,
    )
    strategy = MetaStrategy(config)
    bt_config = BacktestConfig(
        initial_capital=10000.0,
        risk_per_trade=0.02,
        fee_rate=0.001,
        slippage_rate=0.0005,
        max_positions=10,
    )
    engine = BacktestEngine(strategy, bt_config)
    return engine.run(data)


def print_metrics(name: str, metrics: dict):
    """Print backtest metrics in a readable format."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Total Return:     {metrics.get('total_return', 0):.2%}")
    print(f"  Sharpe Ratio:     {metrics.get('sharpe', 0):.4f}")
    print(f"  Max Drawdown:     {metrics.get('max_drawdown', 0):.2%}")
    print(f"  Total Trades:     {metrics.get('num_trades', 0)}")
    print(f"  Win Rate:         {metrics.get('win_rate', 0):.2%}")
    print(f"  Profit Factor:    {metrics.get('profit_factor', 0):.4f}")
    print(f"  Avg Bars Held:    {metrics.get('avg_bars_held', 0):.1f}")
    print(f"  Final Capital:    ${metrics.get('final_capital', 0):.2f}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Run strategy backtests")
    parser.add_argument(
        "--strategy", type=str, default="all",
        choices=["all", "momentum", "mean_reversion", "stat_arb", "meta"],
        help="Which strategy to backtest",
    )
    parser.add_argument("--timeframe", type=str, default="1d", help="Data timeframe")
    args = parser.parse_args()

    # Load available symbols
    store = ParquetStore(base_dir="data/parquet")
    symbols = store.get_available_symbols()
    if not symbols:
        print("No data found. Run scripts/download_historical.py first.")
        sys.exit(1)

    print(f"\nLoading data for {len(symbols)} symbols ({args.timeframe})...")
    data = load_data(symbols, args.timeframe)
    if not data:
        print("No data could be loaded.")
        sys.exit(1)

    print(f"\nLoaded {len(data)} symbols with data")

    # Run requested backtests
    results = {}
    if args.strategy in ("all", "momentum"):
        print("\nRunning Momentum backtest...")
        results["Momentum (STRAT-06)"] = run_momentum_backtest(data)

    if args.strategy in ("all", "mean_reversion"):
        print("\nRunning Mean Reversion backtest...")
        results["Mean Reversion (STRAT-01)"] = run_mean_reversion_backtest(data)

    if args.strategy in ("all", "stat_arb"):
        print("\nRunning Statistical Arbitrage backtest...")
        results["Stat Arb (STRAT-03)"] = run_stat_arb_backtest(data)

    if args.strategy in ("all", "meta"):
        print("\nRunning Meta-Strategy (combined) backtest...")
        results["Meta-Strategy (combined)"] = run_meta_backtest(data)

    # Print results
    print("\n" + "#" * 60)
    print("# BACKTEST RESULTS SUMMARY")
    print("#" * 60)
    for name, metrics in results.items():
        print_metrics(name, metrics)


if __name__ == "__main__":
    main()
