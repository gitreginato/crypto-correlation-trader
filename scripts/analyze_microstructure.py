#!/usr/bin/env python3
"""Microstructure analysis: extract the "game" behind the candles.

This goes beyond OHLCV to analyze:
1. Taker buy/sell ratio: who was the aggressor at each moment
2. Volume profile: at what price levels did volume concentrate
3. Gap analysis: open vs previous close (sudden moves)
4. Wick analysis: rejection zones (buying/selling pressure that failed)
5. Round number clustering: are prices drawn to psychological levels?
6. Order flow imbalance: net aggression by hour/day
7. Accumulation/distribution: volume-weighted price zones
8. Price magnetism: do prices get "pulled" toward certain levels?
9. Time-of-day order flow: when do buyers vs sellers dominate?
10. Candle anatomy: body vs wick ratios by time and direction

The key insight: taker_buy_base tells us how much volume was from
aggressive BUYERS (market buys). The rest is aggressive SELLERS.
This ratio reveals who is in control.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

from src.data.parquet_store import ParquetStore


def load_data(symbols: list[str], timeframe: str = "15m") -> dict[str, pd.DataFrame]:
    """Load OHLCV data with taker buy fields."""
    store = ParquetStore(base_dir="data/parquet")
    data = {}
    for sym in symbols:
        df = store.read(sym, timeframe)
        if df.empty:
            continue
        df = df.set_index("open_time")
        df.index = df.index.tz_localize(None)
        data[sym] = df.dropna()
    return data


def compute_taker_buy_sell_ratio(data: dict[str, pd.DataFrame]) -> dict:
    """Compute taker buy/sell ratio for each symbol.

    taker_buy_base = volume from aggressive buyers (market buys)
    taker_sell_base = total_volume - taker_buy_base (market sells)
    ratio > 1 = buyers dominant, < 1 = sellers dominant
    """
    results = {"symbols": {}, "by_hour": {}, "by_day": {}}

    for sym, df in data.items():
        if "taker_buy_base" not in df.columns or "volume" not in df.columns:
            continue

        taker_buy = df["taker_buy_base"]
        taker_sell = df["volume"] - df["taker_buy_base"]
        ratio = taker_buy / taker_sell.replace(0, np.nan)

        # Overall stats
        results["symbols"][sym] = {
            "avg_ratio": float(ratio.mean()),
            "median_ratio": float(ratio.median()),
            "std_ratio": float(ratio.std()),
            "pct_buy_dominant": float((ratio > 1).mean()),
            "total_buy_volume": float(taker_buy.sum()),
            "total_sell_volume": float(taker_sell.sum()),
            "net_aggression": float((taker_buy.sum() - taker_sell.sum()) / df["volume"].sum()),
        }

        # By hour of day
        df = df.copy()
        df["hour"] = df.index.hour
        df["ratio"] = ratio
        df["buy_vol"] = taker_buy
        df["sell_vol"] = taker_sell

        hourly = df.groupby("hour").agg({
            "ratio": "mean",
            "buy_vol": "sum",
            "sell_vol": "sum",
        })
        hourly["net"] = hourly["buy_vol"] - hourly["sell_vol"]
        hourly["net_pct"] = hourly["net"] / (hourly["buy_vol"] + hourly["sell_vol"])

        results["by_hour"][sym] = {
            "hours": list(hourly.index),
            "ratio": [float(x) for x in hourly["ratio"].values],
            "net_pct": [float(x) for x in hourly["net_pct"].values],
        }

        # By day of week
        df["dow"] = df.index.dayofweek
        daily = df.groupby("dow").agg({
            "ratio": "mean",
            "buy_vol": "sum",
            "sell_vol": "sum",
        })
        daily["net_pct"] = (daily["buy_vol"] - daily["sell_vol"]) / (daily["buy_vol"] + daily["sell_vol"])

        results["by_day"][sym] = {
            "days": list(daily.index),
            "ratio": [float(x) for x in daily["ratio"].values],
            "net_pct": [float(x) for x in daily["net_pct"].values],
        }

    # Aggregate by hour across all symbols
    all_hours = defaultdict(lambda: {"ratios": [], "net_pcts": []})
    for sym_data in results["by_hour"].values():
        for i, h in enumerate(sym_data["hours"]):
            all_hours[h]["ratios"].append(sym_data["ratio"][i])
            all_hours[h]["net_pcts"].append(sym_data["net_pct"][i])

    results["avg_by_hour"] = {
        "hours": sorted(all_hours.keys()),
        "ratio": [float(np.mean(all_hours[h]["ratios"])) for h in sorted(all_hours.keys())],
        "net_pct": [float(np.mean(all_hours[h]["net_pcts"])) for h in sorted(all_hours.keys())],
    }

    return results


def compute_gap_analysis(data: dict[str, pd.DataFrame]) -> dict:
    """Analyze gaps: open vs previous close.

    Large gaps indicate overnight/news moves or manipulation.
    """
    results = {"symbols": {}}

    for sym, df in data.items():
        gaps = (df["open"] / df["close"].shift(1) - 1) * 100  # percent gap
        gaps = gaps.dropna()

        # Classify gaps
        small = gaps.abs() < 0.5
        medium = (gaps.abs() >= 0.5) & (gaps.abs() < 2.0)
        large = gaps.abs() >= 2.0

        results["symbols"][sym] = {
            "avg_gap_pct": float(gaps.mean()),
            "avg_abs_gap_pct": float(gaps.abs().mean()),
            "max_gap_pct": float(gaps.max()),
            "min_gap_pct": float(gaps.min()),
            "pct_small_gaps": float(small.mean()),
            "pct_medium_gaps": float(medium.mean()),
            "pct_large_gaps": float(large.mean()),
            "num_large_gaps": int(large.sum()),
            "large_gap_examples": [
                {"date": str(gaps.index[i].date()), "gap_pct": float(gaps.iloc[i])}
                for i in gaps[large].index.argsort()[-10:]
            ] if large.sum() > 0 else [],
        }

    return results


def compute_wick_analysis(data: dict[str, pd.DataFrame]) -> dict:
    """Analyze wicks: rejection zones.

    Upper wick = price went up but was rejected (selling pressure)
    Lower wick = price went down but was rejected (buying pressure)
    Large wicks relative to body = strong rejection
    """
    results = {"symbols": {}, "by_hour": {}}

    for sym, df in data.items():
        body = (df["close"] - df["open"]).abs()
        upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
        lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
        total_range = df["high"] - df["low"]

        # Wick ratios (0-1, higher = more rejection)
        upper_wick_ratio = (upper_wick / total_range.replace(0, np.nan)).fillna(0)
        lower_wick_ratio = (lower_wick / total_range.replace(0, np.nan)).fillna(0)

        # Body ratio (1 - wicks, higher = more conviction)
        body_ratio = (body / total_range.replace(0, np.nan)).fillna(0)

        # Rejection signal: wick > 2x body
        upper_rejection = upper_wick > 2 * body
        lower_rejection = lower_wick > 2 * body

        results["symbols"][sym] = {
            "avg_upper_wick_ratio": float(upper_wick_ratio.mean()),
            "avg_lower_wick_ratio": float(lower_wick_ratio.mean()),
            "avg_body_ratio": float(body_ratio.mean()),
            "pct_upper_rejection": float(upper_rejection.mean()),
            "pct_lower_rejection": float(lower_rejection.mean()),
            "upper_rejection_count": int(upper_rejection.sum()),
            "lower_rejection_count": int(lower_rejection.sum()),
        }

        # By hour
        df_w = df.copy()
        df_w["hour"] = df_w.index.hour
        df_w["upper_wick_ratio"] = upper_wick_ratio
        df_w["lower_wick_ratio"] = lower_wick_ratio
        df_w["body_ratio"] = body_ratio

        hourly = df_w.groupby("hour").agg({
            "upper_wick_ratio": "mean",
            "lower_wick_ratio": "mean",
            "body_ratio": "mean",
        })

        results["by_hour"][sym] = {
            "hours": list(hourly.index),
            "upper_wick": [float(x) for x in hourly["upper_wick_ratio"].values],
            "lower_wick": [float(x) for x in hourly["lower_wick_ratio"].values],
            "body": [float(x) for x in hourly["body_ratio"].values],
        }

    # Aggregate
    all_hours = defaultdict(lambda: {"upper": [], "lower": [], "body": []})
    for sym_data in results["by_hour"].values():
        for i, h in enumerate(sym_data["hours"]):
            all_hours[h]["upper"].append(sym_data["upper_wick"][i])
            all_hours[h]["lower"].append(sym_data["lower_wick"][i])
            all_hours[h]["body"].append(sym_data["body"][i])

    results["avg_by_hour"] = {
        "hours": sorted(all_hours.keys()),
        "upper_wick": [float(np.mean(all_hours[h]["upper"])) for h in sorted(all_hours.keys())],
        "lower_wick": [float(np.mean(all_hours[h]["lower"])) for h in sorted(all_hours.keys())],
        "body": [float(np.mean(all_hours[h]["body"])) for h in sorted(all_hours.keys())],
    }

    return results


def compute_volume_profile(data: dict[str, pd.DataFrame], num_bins: int = 50) -> dict:
    """Compute volume profile: volume traded at each price level.

    This reveals where the "battle" happened - price levels with most volume
    are support/resistance zones.
    """
    results = {"symbols": {}}

    for sym, df in data.items():
        if len(df) < 100:
            continue

        price_min = df["low"].min()
        price_max = df["high"].max()
        bins = np.linspace(price_min, price_max, num_bins + 1)

        # For each candle, distribute volume across the price range it traded
        volume_profile = np.zeros(num_bins)
        for _, row in df.iterrows():
            low = row["low"]
            high = row["high"]
            vol = row["volume"]

            # Find which bins this candle spans
            for i in range(num_bins):
                bin_low = bins[i]
                bin_high = bins[i + 1]
                overlap = min(high, bin_high) - max(low, bin_low)
                if overlap > 0:
                    candle_range = high - low
                    if candle_range > 0:
                        volume_profile[i] += vol * (overlap / candle_range)

        # Find high volume nodes (HVN) and low volume nodes (LVN)
        threshold_hvn = np.percentile(volume_profile[volume_profile > 0], 80)
        threshold_lvn = np.percentile(volume_profile[volume_profile > 0], 20)

        hvn_levels = []
        lvn_levels = []
        for i in range(num_bins):
            if volume_profile[i] > threshold_hvn:
                hvn_levels.append(float((bins[i] + bins[i + 1]) / 2))
            elif volume_profile[i] < threshold_lvn and volume_profile[i] > 0:
                lvn_levels.append(float((bins[i] + bins[i + 1]) / 2))

        # Point of Control (POC) - price level with highest volume
        poc_idx = np.argmax(volume_profile)
        poc = float((bins[poc_idx] + bins[poc_idx + 1]) / 2)

        results["symbols"][sym] = {
            "price_levels": [float((bins[i] + bins[i + 1]) / 2) for i in range(num_bins)],
            "volume": [float(v) for v in volume_profile],
            "poc": poc,
            "hvn_levels": hvn_levels[:10],  # top high volume nodes
            "lvn_levels": lvn_levels[:10],  # top low volume nodes
            "price_min": float(price_min),
            "price_max": float(price_max),
            "current_price": float(df["close"].iloc[-1]),
        }

    return results


def compute_round_number_clustering(data: dict[str, pd.DataFrame]) -> dict:
    """Check if prices cluster at round numbers (psychological levels).

    If prices are manipulated/directed, they may cluster at round numbers
    like $100, $1000, $50000, etc.
    """
    results = {"symbols": {}}

    for sym, df in data.items():
        close = df["close"]
        current_price = close.iloc[-1]

        # Determine round number scale based on price
        if current_price > 10000:
            round_levels = [x * 1000 for x in range(1, 200)]  # every $1000
            tolerance = 0.005  # 0.5%
        elif current_price > 1000:
            round_levels = [x * 100 for x in range(1, 200)]  # every $100
            tolerance = 0.005
        elif current_price > 100:
            round_levels = [x * 10 for x in range(1, 200)]  # every $10
            tolerance = 0.005
        elif current_price > 10:
            round_levels = [x * 1 for x in range(1, 200)]  # every $1
            tolerance = 0.005
        elif current_price > 1:
            round_levels = [x * 0.1 for x in range(1, 200)]  # every $0.10
            tolerance = 0.005
        else:
            round_levels = [x * 0.01 for x in range(1, 200)]
            tolerance = 0.005

        # Count how often price is near a round number
        near_round = 0
        total = 0
        distances = []

        for price in close:
            for level in round_levels:
                if level > price * 2:
                    break
                dist_pct = abs(price - level) / price
                if dist_pct < tolerance:
                    near_round += 1
                    distances.append(float(dist_pct))
                    break
            total += 1

        # Expected clustering if random
        expected_pct = len(round_levels) * tolerance * 2 / 100  # rough estimate

        results["symbols"][sym] = {
            "pct_near_round": float(near_round / total) if total > 0 else 0,
            "expected_random_pct": float(min(expected_pct, 1.0)),
            "clustering_factor": float((near_round / total) / max(expected_pct, 0.001)) if total > 0 else 0,
            "current_price": float(current_price),
            "tolerance": tolerance,
        }

    return results


def compute_order_flow_imbalance(data: dict[str, pd.DataFrame]) -> dict:
    """Compute order flow imbalance: net buying vs selling pressure over time.

    Combines taker buy/sell with price direction to identify:
    - True buying pressure (taker buy > sell AND price up)
    - True selling pressure (taker sell > buy AND price down)
    - Divergence (volume up but price doesn't follow = absorption)
    """
    results = {"symbols": {}, "patterns": {}}

    for sym, df in data.items():
        if "taker_buy_base" not in df.columns:
            continue

        taker_buy = df["taker_buy_base"]
        taker_sell = df["volume"] - df["taker_buy_base"]
        ofi = (taker_buy - taker_sell) / df["volume"].replace(0, np.nan)  # -1 to 1
        price_change = df["close"].pct_change()

        # Classify each bar
        true_buy = (ofi > 0.1) & (price_change > 0)  # buying + price up
        true_sell = (ofi < -0.1) & (price_change < 0)  # selling + price down
        absorption_buy = (ofi > 0.1) & (price_change <= 0)  # buying but price doesn't up
        absorption_sell = (ofi < -0.1) & (price_change >= 0)  # selling but price doesn't down

        results["symbols"][sym] = {
            "pct_true_buy": float(true_buy.mean()),
            "pct_true_sell": float(true_sell.mean()),
            "pct_absorption_buy": float(absorption_buy.mean()),
            "pct_absorption_sell": float(absorption_sell.mean()),
            "avg_ofi": float(ofi.mean()),
            "ofi_std": float(ofi.std()),
        }

        # By hour
        df_o = df.copy()
        df_o["hour"] = df_o.index.hour
        df_o["ofi"] = ofi

        hourly = df_o.groupby("hour")["ofi"].agg(["mean", "std"])

        results["patterns"][sym] = {
            "hours": list(hourly.index),
            "ofi_mean": [float(x) for x in hourly["mean"].values],
            "ofi_std": [float(x) for x in hourly["std"].values],
        }

    # Aggregate OFI by hour
    all_hours = defaultdict(list)
    for sym_data in results["patterns"].values():
        for i, h in enumerate(sym_data["hours"]):
            all_hours[h].append(sym_data["ofi_mean"][i])

    results["avg_ofi_by_hour"] = {
        "hours": sorted(all_hours.keys()),
        "ofi": [float(np.mean(all_hours[h])) for h in sorted(all_hours.keys())],
    }

    return results


def compute_price_magnetism(data: dict[str, pd.DataFrame]) -> dict:
    """Analyze if prices are "pulled" toward certain levels.

    Tests: after a move away from VWAP, does price tend to return?
    This measures mean-reversion magnetism.
    """
    results = {"symbols": {}}

    for sym, df in data.items():
        if len(df) < 100:
            continue

        # Rolling VWAP (volume-weighted average price)
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        vol = df["volume"]

        # 24-period VWAP
        rolling_vp = (typical_price * vol).rolling(24).sum()
        rolling_v = vol.rolling(24).sum()
        vwap = rolling_vp / rolling_v

        # Distance from VWAP
        dist_from_vwap = (df["close"] - vwap) / vwap

        # Does price revert to VWAP? Check if next N bars move toward VWAP
        reversion_1 = []
        reversion_3 = []
        reversion_6 = []

        for i in range(len(df) - 6):
            if np.isnan(dist_from_vwap.iloc[i]):
                continue
            dist = dist_from_vwap.iloc[i]

            # 1 bar later: did distance shrink?
            if not np.isnan(dist_from_vwap.iloc[i + 1]):
                reversion_1.append(abs(dist_from_vwap.iloc[i + 1]) < abs(dist))

            # 3 bars later
            if i + 3 < len(df) and not np.isnan(dist_from_vwap.iloc[i + 3]):
                reversion_3.append(abs(dist_from_vwap.iloc[i + 3]) < abs(dist))

            # 6 bars later
            if i + 6 < len(df) and not np.isnan(dist_from_vwap.iloc[i + 6]):
                reversion_6.append(abs(dist_from_vwap.iloc[i + 6]) < abs(dist))

        results["symbols"][sym] = {
            "avg_dist_from_vwap": float(dist_from_vwap.dropna().mean()),
            "std_dist_from_vwap": float(dist_from_vwap.dropna().std()),
            "reversion_rate_1bar": float(np.mean(reversion_1)) if reversion_1 else 0,
            "reversion_rate_3bar": float(np.mean(reversion_3)) if reversion_3 else 0,
            "reversion_rate_6bar": float(np.mean(reversion_6)) if reversion_6 else 0,
        }

    return results


def compute_candle_anatomy(data: dict[str, pd.DataFrame]) -> dict:
    """Analyze candle anatomy: body vs wick by direction and time.

    Bullish candles with large bodies = strong buying
    Bearish candles with large bodies = strong selling
    Large wicks = rejection/indecision
    """
    results = {"symbols": {}, "by_hour": {}}

    for sym, df in data.items():
        body = df["close"] - df["open"]
        body_abs = body.abs()
        total_range = (df["high"] - df["low"]).replace(0, np.nan)

        body_ratio = (body_abs / total_range).fillna(0)
        is_bull = body > 0
        is_bear = body < 0

        # Bull vs bear body ratios
        bull_body_ratio = body_ratio[is_bull].mean()
        bear_body_ratio = body_ratio[is_bear].mean()

        results["symbols"][sym] = {
            "pct_bull_candles": float(is_bull.mean()),
            "pct_bear_candles": float(is_bear.mean()),
            "avg_bull_body_ratio": float(bull_body_ratio),
            "avg_bear_body_ratio": float(bear_body_ratio),
            "avg_body_ratio": float(body_ratio.mean()),
            "bull_bear_body_diff": float(bull_body_ratio - bear_body_ratio),
        }

        # By hour
        df_c = df.copy()
        df_c["hour"] = df_c.index.hour
        df_c["body_ratio"] = body_ratio
        df_c["is_bull"] = is_bull

        hourly = df_c.groupby("hour").agg({
            "body_ratio": "mean",
            "is_bull": "mean",
        })

        results["by_hour"][sym] = {
            "hours": list(hourly.index),
            "body_ratio": [float(x) for x in hourly["body_ratio"].values],
            "bull_pct": [float(x) for x in hourly["is_bull"].values],
        }

    # Aggregate
    all_hours = defaultdict(lambda: {"body": [], "bull": []})
    for sym_data in results["by_hour"].values():
        for i, h in enumerate(sym_data["hours"]):
            all_hours[h]["body"].append(sym_data["body_ratio"][i])
            all_hours[h]["bull"].append(sym_data["bull_pct"][i])

    results["avg_by_hour"] = {
        "hours": sorted(all_hours.keys()),
        "body_ratio": [float(np.mean(all_hours[h]["body"])) for h in sorted(all_hours.keys())],
        "bull_pct": [float(np.mean(all_hours[h]["bull"])) for h in sorted(all_hours.keys())],
    }

    return results


def compute_accumulation_distribution(data: dict[str, pd.DataFrame]) -> dict:
    """Identify accumulation vs distribution phases.

    Accumulation: price flat/slightly down but volume increasing (smart money buying)
    Distribution: price flat/slightly up but volume increasing (smart money selling)
    """
    results = {"symbols": {}}

    for sym, df in data.items():
        if len(df) < 100:
            continue

        # Use 20-bar windows
        window = 20
        price_change = df["close"].pct_change(window)
        volume_change = df["volume"].rolling(window).mean() / df["volume"].rolling(window * 2).mean()

        # Accumulation: low price change, high volume
        accumulation = (price_change.abs() < 0.02) & (volume_change > 1.2)
        # Distribution: moderate price change, high volume, slightly up
        distribution = (price_change > 0.01) & (price_change < 0.05) & (volume_change > 1.2)

        # Mark up: strong price up with volume
        markup = (price_change > 0.05) & (volume_change > 1.0)
        # Mark down: strong price down with volume
        markdown = (price_change < -0.05) & (volume_change > 1.0)

        results["symbols"][sym] = {
            "pct_accumulation": float(accumulation.mean()),
            "pct_distribution": float(distribution.mean()),
            "pct_markup": float(markup.mean()),
            "pct_markdown": float(markdown.mean()),
        }

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Microstructure analysis")
    parser.add_argument("--timeframe", type=str, default="15m", help="Data timeframe")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols (default: all)")
    parser.add_argument("--output", type=str, default="data/analysis/microstructure_analysis.json", help="Output JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("  MICROSTRUCTURE ANALYSIS: THE GAME BEHIND THE CANDLES")
    print("=" * 60)

    # Load data
    print(f"\n[1/9] Loading {args.timeframe} data...")
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        store = ParquetStore(base_dir="data/parquet")
        symbols = store.get_available_symbols()

    data = load_data(symbols, args.timeframe)
    print(f"  Loaded {len(data)} symbols")
    for sym, df in list(data.items())[:5]:
        print(f"    {sym}: {len(df)} bars, {df.index[0]} to {df.index[-1]}")

    if not data:
        print("ERROR: No data found")
        sys.exit(1)

    # 1. Taker buy/sell ratio
    print("\n[2/9] Computing taker buy/sell ratio (aggressor analysis)...")
    taker = compute_taker_buy_sell_ratio(data)
    for sym, info in list(taker["symbols"].items())[:5]:
        print(f"  {sym}: avg ratio={info['avg_ratio']:.3f}, buy dominant {info['pct_buy_dominant']:.1%}, net aggression={info['net_aggression']:.4f}")

    # 2. Gap analysis
    print("\n[3/9] Computing gap analysis...")
    gaps = compute_gap_analysis(data)
    for sym, info in list(gaps["symbols"].items())[:5]:
        print(f"  {sym}: avg gap={info['avg_gap_pct']:.3f}%, large gaps={info['num_large_gaps']}")

    # 3. Wick analysis
    print("\n[4/9] Computing wick/rejection analysis...")
    wicks = compute_wick_analysis(data)
    for sym, info in list(wicks["symbols"].items())[:5]:
        print(f"  {sym}: upper rejection={info['pct_upper_rejection']:.1%}, lower rejection={info['pct_lower_rejection']:.1%}")

    # 4. Volume profile
    print("\n[5/9] Computing volume profile (price level concentration)...")
    vol_profile = compute_volume_profile(data)
    for sym, info in list(vol_profile["symbols"].items())[:5]:
        print(f"  {sym}: POC={info['poc']:.2f}, current={info['current_price']:.2f}, HVN nodes={len(info['hvn_levels'])}")

    # 5. Round number clustering
    print("\n[6/9] Computing round number clustering (psychological levels)...")
    round_num = compute_round_number_clustering(data)
    for sym, info in list(round_num["symbols"].items())[:5]:
        print(f"  {sym}: near round {info['pct_near_round']:.1%}, clustering factor={info['clustering_factor']:.2f}x")

    # 6. Order flow imbalance
    print("\n[7/9] Computing order flow imbalance...")
    ofi = compute_order_flow_imbalance(data)
    for sym, info in list(ofi["symbols"].items())[:5]:
        print(f"  {sym}: true buy={info['pct_true_buy']:.1%}, true sell={info['pct_true_sell']:.1%}, absorption buy={info['pct_absorption_buy']:.1%}")

    # 7. Price magnetism (VWAP reversion)
    print("\n[8/9] Computing price magnetism (VWAP reversion)...")
    magnetism = compute_price_magnetism(data)
    for sym, info in list(magnetism["symbols"].items())[:5]:
        print(f"  {sym}: reversion 1bar={info['reversion_rate_1bar']:.1%}, 3bar={info['reversion_rate_3bar']:.1%}, 6bar={info['reversion_rate_6bar']:.1%}")

    # 8. Candle anatomy
    print("\n[9/9] Computing candle anatomy...")
    anatomy = compute_candle_anatomy(data)
    for sym, info in list(anatomy["symbols"].items())[:5]:
        print(f"  {sym}: bull {info['pct_bull_candles']:.1%}, bear {info['pct_bear_candles']:.1%}, bull body={info['avg_bull_body_ratio']:.3f}, bear body={info['avg_bear_body_ratio']:.3f}")

    # 9. Accumulation/Distribution
    print("\n[Extra] Computing accumulation/distribution phases...")
    acc_dist = compute_accumulation_distribution(data)
    for sym, info in list(acc_dist["symbols"].items())[:5]:
        print(f"  {sym}: accumulation={info['pct_accumulation']:.1%}, distribution={info['pct_distribution']:.1%}, markup={info['pct_markup']:.1%}, markdown={info['pct_markdown']:.1%}")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_results = {
        "timeframe": args.timeframe,
        "symbols": list(data.keys()),
        "taker_buy_sell": taker,
        "gap_analysis": gaps,
        "wick_analysis": wicks,
        "volume_profile": vol_profile,
        "round_number_clustering": round_num,
        "order_flow_imbalance": ofi,
        "price_magnetism": magnetism,
        "candle_anatomy": anatomy,
        "accumulation_distribution": acc_dist,
    }

    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  Analysis complete! Saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
