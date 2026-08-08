#!/usr/bin/env python3
"""Comprehensive correlation analysis across crypto assets.

Analyzes multiple types of correlations:
1. Return correlations (Pearson, Spearman) between all pairs
2. Lagged correlations (does BTC lead altcoins?)
3. Time-of-day volatility patterns
4. Day-of-week patterns
5. Lead-lag relationships (large caps -> small caps)
6. Volatility correlations
7. Volume correlations
8. Drawdown correlations
9. Regime-dependent correlations (bull vs bear)
10. Cross-asset momentum (BTC momentum -> altcoin returns)

Outputs results as JSON for the HTML dashboard generator.
"""
import json
import sys
from itertools import combinations
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

from src.data.parquet_store import ParquetStore
from src.data.universe import SYMBOL_METADATA


def load_all_data(timeframe: str = "1d") -> dict[str, pd.DataFrame]:
    """Load all available OHLCV data."""
    store = ParquetStore(base_dir="data/parquet")
    symbols = store.get_available_symbols()
    data = {}
    for sym in symbols:
        df = store.read(sym, timeframe)
        if df.empty:
            continue
        df = df.set_index("open_time")
        df.index = df.index.tz_localize(None)
        required = ["open", "high", "low", "close", "volume"]
        if not all(c in df.columns for c in required):
            continue
        data[sym] = df[required + ["quote_volume"] if "quote_volume" in df.columns else required].dropna()
    return data


def compute_return_correlations(data: dict[str, pd.DataFrame]) -> dict:
    """Compute Pearson and Spearman return correlations between all pairs."""
    # Build returns DataFrame
    returns = pd.DataFrame({sym: df["close"].pct_change() for sym, df in data.items()})
    returns = returns.dropna()

    results = {
        "pearson": {},
        "spearman": {},
        "symbols": list(returns.columns),
        "matrix_pearson": None,
        "matrix_spearman": None,
    }

    # Full correlation matrices
    pearson_mat = returns.corr(method="pearson")
    spearman_mat = returns.corr(method="spearman")

    results["matrix_pearson"] = pearson_mat.round(4).to_dict()
    results["matrix_spearman"] = spearman_mat.round(4).to_dict()

    # Top correlated pairs
    pairs = []
    for a, b in combinations(returns.columns, 2):
        p_corr = pearson_mat.loc[a, b]
        s_corr = spearman_mat.loc[a, b]
        pairs.append({"a": a, "b": b, "pearson": float(p_corr), "spearman": float(s_corr)})

    pairs.sort(key=lambda x: x["pearson"], reverse=True)
    results["top_correlated"] = pairs[:15]
    results["least_correlated"] = pairs[-15:]
    results["all_pairs"] = pairs

    return results


def compute_lagged_correlations(data: dict[str, pd.DataFrame], max_lag: int = 10) -> dict:
    """Compute lagged correlations: does asset A's return predict asset B's return N bars later?

    This is the key analysis for lead-lag relationships (BTC -> altcoins).
    """
    returns = pd.DataFrame({sym: df["close"].pct_change() for sym, df in data.items()})
    returns = returns.dropna()

    symbols = list(returns.columns)
    results = {"max_lag": max_lag, "leaders": {}, "lagged_matrix": {}}

    # For each pair (A, B), compute corr(A_t, B_{t+lag}) for lag = 0..max_lag
    # If corr is high for lag > 0, A leads B
    lag_data = []

    for a in symbols:
        for b in symbols:
            if a == b:
                continue
            corrs = []
            for lag in range(0, max_lag + 1):
                if lag == 0:
                    c = returns[a].corr(returns[b])
                else:
                    c = returns[a].iloc[:-lag].corr(returns[b].iloc[lag:].reset_index(drop=True))
                corrs.append(float(c) if not np.isnan(c) else 0.0)
            lag_data.append({"leader": a, "follower": b, "correlations": corrs})

            # Track best lag
            best_lag = int(np.argmax(np.abs(corrs[1:]))) + 1  # skip lag 0
            best_corr = corrs[best_lag]
            if abs(best_corr) > 0.3:
                if a not in results["leaders"]:
                    results["leaders"][a] = []
                results["leaders"][a].append({
                    "follower": b,
                    "best_lag": best_lag,
                    "correlation": best_corr,
                })

    results["lagged_matrix"] = lag_data

    # Sort leaders by number of followers
    for a in results["leaders"]:
        results["leaders"][a].sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return results


def compute_time_of_day_patterns(data: dict[str, pd.DataFrame], timeframe: str = "1h") -> dict:
    """Analyze volatility and volume patterns by hour of day."""
    results = {"by_hour": {}, "by_day_of_week": {}, "symbols": []}

    for sym, df in data.items():
        if len(df) < 100:
            continue

        results["symbols"].append(sym)

        # Hour of day analysis (only for intraday data)
        if timeframe in ("1h", "4h", "15m", "5m", "1m"):
            df = df.copy()
            df["hour"] = df.index.hour
            df["day_of_week"] = df.index.dayofweek
            df["return"] = df["close"].pct_change()
            df["volatility"] = (df["high"] - df["low"]) / df["close"]

            # By hour
            hourly = df.groupby("hour").agg({
                "return": lambda x: float(np.std(x)),
                "volatility": "mean",
                "volume": "mean",
            }).rename(columns={"return": "return_std"})

            if sym not in results["by_hour"]:
                results["by_hour"][sym] = {}
            results["by_hour"][sym] = {
                "hours": list(hourly.index),
                "return_std": [float(x) for x in hourly["return_std"].values],
                "volatility": [float(x) for x in hourly["volatility"].values],
                "volume": [float(x) for x in hourly["volume"].values],
            }

        # Day of week (works for any timeframe)
        df_d = df.copy()
        df_d["day_of_week"] = df_d.index.dayofweek
        df_d["return"] = df_d["close"].pct_change()

        daily = df_d.groupby("day_of_week").agg({
            "return": lambda x: float(np.std(x)),
            "volume": "mean",
        }).rename(columns={"return": "return_std"})

        if "by_day_of_week" not in results:
            results["by_day_of_week"] = {}
        results["by_day_of_week"][sym] = {
            "days": list(daily.index),
            "return_std": [float(x) for x in daily["return_std"].values],
            "volume": [float(x) for x in daily["volume"].values],
        }

    # Aggregate: average volatility by hour across all symbols
    if results["by_hour"]:
        all_hours = {}
        for sym_data in results["by_hour"].values():
            for i, h in enumerate(sym_data["hours"]):
                if h not in all_hours:
                    all_hours[h] = {"volatility": [], "volume": []}
                all_hours[h]["volatility"].append(sym_data["volatility"][i])
                all_hours[h]["volume"].append(sym_data["volume"][i])

        results["avg_by_hour"] = {
            "hours": sorted(all_hours.keys()),
            "volatility": [float(np.mean(all_hours[h]["volatility"])) for h in sorted(all_hours.keys())],
            "volume": [float(np.mean(all_hours[h]["volume"])) for h in sorted(all_hours.keys())],
        }

    return results


def compute_volatility_correlations(data: dict[str, pd.DataFrame]) -> dict:
    """Compute correlations between volatilities of different assets."""
    vol_data = {}
    for sym, df in data.items():
        returns = df["close"].pct_change().dropna()
        vol = returns.rolling(window=20).std().dropna()
        vol_data[sym] = vol

    vol_df = pd.DataFrame(vol_data).dropna()
    corr = vol_df.corr(method="pearson").round(4)

    return {
        "matrix": corr.to_dict(),
        "symbols": list(vol_df.columns),
        "description": "20-day rolling volatility correlations",
    }


def compute_volume_correlations(data: dict[str, pd.DataFrame]) -> dict:
    """Compute correlations between trading volumes of different assets."""
    vol_data = {}
    for sym, df in data.items():
        vol = df["volume"].pct_change().dropna()
        vol_data[sym] = vol

    vol_df = pd.DataFrame(vol_data).dropna()
    corr = vol_df.corr(method="pearson").round(4)

    return {
        "matrix": corr.to_dict(),
        "symbols": list(vol_df.columns),
    }


def compute_drawdown_correlations(data: dict[str, pd.DataFrame]) -> dict:
    """Compute correlations between drawdowns of different assets."""
    dd_data = {}
    for sym, df in data.items():
        close = df["close"]
        running_max = close.cummax()
        drawdown = (close - running_max) / running_max
        dd_data[sym] = drawdown

    dd_df = pd.DataFrame(dd_data).dropna()
    corr = dd_df.corr(method="pearson").round(4)

    return {
        "matrix": corr.to_dict(),
        "symbols": list(dd_df.columns),
    }


def compute_regime_correlations(data: dict[str, pd.DataFrame]) -> dict:
    """Compute correlations in bull vs bear regimes.

    Bull regime: BTC return > 0 over 30-day window
    Bear regime: BTC return < 0 over 30-day window
    """
    if "BTCUSDT" not in data:
        return {"error": "BTCUSDT not in data"}

    btc = data["BTCUSDT"]["close"].pct_change()
    btc_30d = btc.rolling(window=30).sum()

    returns = pd.DataFrame({sym: df["close"].pct_change() for sym, df in data.items()})

    # Bull mask: BTC 30d return > 0
    bull_mask = btc_30d > 0
    bear_mask = btc_30d < 0

    results = {}
    if bull_mask.sum() > 30:
        bull_returns = returns[bull_mask].dropna(axis=1, how="all")
        if len(bull_returns.columns) > 1:
            results["bull"] = {
                "matrix": bull_returns.corr().round(4).to_dict(),
                "symbols": list(bull_returns.columns),
                "num_bars": int(bull_mask.sum()),
            }

    if bear_mask.sum() > 30:
        bear_returns = returns[bear_mask].dropna(axis=1, how="all")
        if len(bear_returns.columns) > 1:
            results["bear"] = {
                "matrix": bear_returns.corr().round(4).to_dict(),
                "symbols": list(bear_returns.columns),
                "num_bars": int(bear_mask.sum()),
            }

    return results


def compute_cross_asset_momentum(data: dict[str, pd.DataFrame]) -> dict:
    """Does BTC (or other large cap) momentum predict altcoin returns?

    Tests: if BTC was up N% in last K days, are altcoins more likely to be up
    in the next K days?
    """
    if "BTCUSDT" not in data:
        return {"error": "BTCUSDT not in data"}

    results = {"predictors": {}}
    predictors = ["BTCUSDT", "ETHUSDT"]
    lookback_periods = [7, 14, 30]
    target_symbols = [s for s in data.keys() if s not in predictors]

    for predictor in predictors:
        if predictor not in data:
            continue
        pred_returns = data[predictor]["close"].pct_change()

        for lookback in lookback_periods:
            pred_momentum = pred_returns.rolling(lookback).sum()

            for target in target_symbols:
                if target not in data:
                    continue
                target_forward = data[target]["close"].pct_change(lookback).shift(-lookback)

                # Align
                df = pd.DataFrame({"momentum": pred_momentum, "forward": target_forward}).dropna()
                if len(df) < 50:
                    continue

                # Split into BTC up / BTC down
                up_mask = df["momentum"] > 0
                down_mask = df["momentum"] < 0

                up_forward = df.loc[up_mask, "forward"]
                down_forward = df.loc[down_mask, "forward"]

                key = f"{predictor}_{lookback}d"
                if key not in results["predictors"]:
                    results["predictors"][key] = []

                results["predictors"][key].append({
                    "target": target,
                    "predictor": predictor,
                    "lookback": lookback,
                    "up_mean_return": float(up_forward.mean()) if len(up_forward) > 0 else 0,
                    "down_mean_return": float(down_forward.mean()) if len(down_forward) > 0 else 0,
                    "up_win_rate": float((up_forward > 0).mean()) if len(up_forward) > 0 else 0,
                    "down_win_rate": float((down_forward > 0).mean()) if len(down_forward) > 0 else 0,
                    "up_count": int(len(up_forward)),
                    "down_count": int(len(down_forward)),
                    "correlation": float(df["momentum"].corr(df["forward"])),
                })

    return results


def compute_category_correlations(data: dict[str, pd.DataFrame]) -> dict:
    """Average correlation within and between categories."""
    returns = pd.DataFrame({sym: df["close"].pct_change() for sym, df in data.items()}).dropna()
    corr_mat = returns.corr()

    # Group by category
    categories = {}
    for sym in returns.columns:
        meta = SYMBOL_METADATA.get(sym, {})
        cat = meta.get("category", "unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(sym)

    results = {"categories": categories, "within_category": {}, "between_category": {}}

    # Within category average correlation
    for cat, syms in categories.items():
        if len(syms) < 2:
            continue
        corrs = []
        for a, b in combinations(syms, 2):
            if a in corr_mat.index and b in corr_mat.columns:
                corrs.append(float(corr_mat.loc[a, b]))
        if corrs:
            results["within_category"][cat] = {
                "avg_correlation": float(np.mean(corrs)),
                "min": float(np.min(corrs)),
                "max": float(np.max(corrs)),
                "pairs": len(corrs),
            }

    # Between category average correlation
    cat_list = list(categories.keys())
    for i, cat_a in enumerate(cat_list):
        for cat_b in cat_list[i + 1:]:
            syms_a = [s for s in categories[cat_a] if s in corr_mat.index]
            syms_b = [s for s in categories[cat_b] if s in corr_mat.index]
            if not syms_a or not syms_b:
                continue
            corrs = []
            for a in syms_a:
                for b in syms_b:
                    corrs.append(float(corr_mat.loc[a, b]))
            key = f"{cat_a}_vs_{cat_b}"
            results["between_category"][key] = {
                "avg_correlation": float(np.mean(corrs)),
                "pairs": len(corrs),
            }

    return results


def compute_movement_following(data: dict[str, pd.DataFrame]) -> dict:
    """When BTC moves > X% in one bar, what do altcoins do in the next bar?

    This tests the 'large cap leads small cap' hypothesis directly.
    """
    if "BTCUSDT" not in data:
        return {"error": "BTCUSDT not in data"}

    btc_returns = data["BTCUSDT"]["close"].pct_change()
    thresholds = [0.03, 0.05, 0.07, 0.10]  # 3%, 5%, 7%, 10% moves

    results = {"thresholds": {}}

    for threshold in thresholds:
        # BTC up big
        btc_up = btc_returns > threshold
        btc_down = btc_returns < -threshold

        up_following = {}
        down_following = {}

        for sym, df in data.items():
            if sym == "BTCUSDT":
                continue
            ret = df["close"].pct_change()
            # Next bar return
            next_ret = ret.shift(-1)

            # When BTC was up big, what did this coin do next?
            up_next = next_ret[btc_up].dropna()
            down_next = next_ret[btc_down].dropna()

            if len(up_next) > 0:
                up_following[sym] = {
                    "avg_next_return": float(up_next.mean()),
                    "win_rate": float((up_next > 0).mean()),
                    "count": int(len(up_next)),
                }
            if len(down_next) > 0:
                down_following[sym] = {
                    "avg_next_return": float(down_next.mean()),
                    "win_rate": float((down_next > 0).mean()),
                    "count": int(len(down_next)),
                }

        results["thresholds"][f"{threshold:.0%}"] = {
            "btc_up_big": {
                "count": int(btc_up.sum()),
                "followers": up_following,
            },
            "btc_down_big": {
                "count": int(btc_down.sum()),
                "followers": down_following,
            },
        }

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Comprehensive correlation analysis")
    parser.add_argument("--timeframe", type=str, default="1d", help="Data timeframe")
    parser.add_argument("--intraday-tf", type=str, default="1h", help="Intraday timeframe for hour analysis")
    parser.add_argument("--output", type=str, default="data/analysis/correlation_analysis.json", help="Output JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("  COMPREHENSIVE CORRELATION ANALYSIS")
    print("=" * 60)

    # Load data
    print(f"\n[1/10] Loading {args.timeframe} data...")
    data = load_all_data(args.timeframe)
    print(f"  Loaded {len(data)} symbols: {', '.join(list(data.keys())[:5])}...")

    if len(data) < 2:
        print("ERROR: Need at least 2 symbols for correlation analysis")
        sys.exit(1)

    # 1. Return correlations
    print("\n[2/10] Computing return correlations (Pearson + Spearman)...")
    return_corr = compute_return_correlations(data)
    print(f"  Top pair: {return_corr['top_correlated'][0]['a']} - {return_corr['top_correlated'][0]['b']} (r={return_corr['top_correlated'][0]['pearson']:.3f})")

    # 2. Lagged correlations
    print("\n[3/10] Computing lagged correlations (lead-lag relationships)...")
    lagged = compute_lagged_correlations(data, max_lag=10)
    print(f"  Leaders found: {len(lagged['leaders'])}")

    # 3. Time of day patterns
    print(f"\n[4/10] Computing time-of-day patterns ({args.intraday_tf})...")
    intraday_data = load_all_data(args.intraday_tf)
    time_patterns = compute_time_of_day_patterns(intraday_data, args.intraday_tf)
    print(f"  Symbols with hourly data: {len(time_patterns['symbols'])}")

    # 4. Volatility correlations
    print("\n[5/10] Computing volatility correlations...")
    vol_corr = compute_volatility_correlations(data)

    # 5. Volume correlations
    print("\n[6/10] Computing volume correlations...")
    volume_corr = compute_volume_correlations(data)

    # 6. Drawdown correlations
    print("\n[7/10] Computing drawdown correlations...")
    dd_corr = compute_drawdown_correlations(data)

    # 7. Regime correlations
    print("\n[8/10] Computing regime-dependent correlations (bull vs bear)...")
    regime_corr = compute_regime_correlations(data)
    if "bull" in regime_corr:
        print(f"  Bull bars: {regime_corr['bull']['num_bars']}, Bear bars: {regime_corr.get('bear', {}).get('num_bars', 0)}")

    # 8. Cross-asset momentum
    print("\n[9/10] Computing cross-asset momentum predictions...")
    cross_momentum = compute_cross_asset_momentum(data)
    for key, preds in cross_momentum.get("predictors", {}).items():
        if preds:
            best = max(preds, key=lambda x: abs(x["correlation"]))
            print(f"  {key}: best target {best['target']} (r={best['correlation']:.3f})")

    # 9. Movement following (BTC big move -> altcoin next bar)
    print("\n[10/10] Computing movement-following analysis (BTC leads altcoins?)...")
    movement = compute_movement_following(data)
    for thresh, data_thresh in movement["thresholds"].items():
        up_count = data_thresh["btc_up_big"]["count"]
        down_count = data_thresh["btc_down_big"]["count"]
        print(f"  {thresh}: BTC up {up_count}x, BTC down {down_count}x")

    # 10. Category correlations
    print("\n[Extra] Computing category-based correlations...")
    category_corr = compute_category_correlations(data)
    for cat, info in category_corr.get("within_category", {}).items():
        print(f"  {cat}: avg r={info['avg_correlation']:.3f} ({info['pairs']} pairs)")

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_results = {
        "timeframe": args.timeframe,
        "intraday_tf": args.intraday_tf,
        "symbols": list(data.keys()),
        "symbol_metadata": {s: SYMBOL_METADATA.get(s, {"category": "unknown"}) for s in data.keys()},
        "return_correlations": return_corr,
        "lagged_correlations": lagged,
        "time_patterns": time_patterns,
        "volatility_correlations": vol_corr,
        "volume_correlations": volume_corr,
        "drawdown_correlations": dd_corr,
        "regime_correlations": regime_corr,
        "cross_asset_momentum": cross_momentum,
        "movement_following": movement,
        "category_correlations": category_corr,
    }

    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  Analysis complete! Results saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
