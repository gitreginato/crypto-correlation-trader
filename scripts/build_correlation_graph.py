#!/usr/bin/env python3
"""Build correlation graph from stored Parquet data.

Pipeline: Parquet -> prices -> returns -> correlation -> graph -> HTML

Usage:
    python scripts/build_correlation_graph.py --timeframe 1d --threshold 0.5
    python scripts/build_correlation_graph.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --threshold 0.3
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.correlation import CorrelationMatrix
from src.analysis.graph import CorrelationGraph
from src.analysis.returns import align_returns, calculate_returns
from src.data.parquet_store import ParquetStore
from src.viz.graph_visualizer import GraphVisualizer


def main():
    parser = argparse.ArgumentParser(description="Build correlation graph from stored data")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols (default: all in store)")
    parser.add_argument("--timeframe", type=str, default="1d", help="Timeframe to use")
    parser.add_argument("--threshold", type=float, default=0.5, help="Correlation threshold for edges")
    parser.add_argument("--method", type=str, default="pearson", choices=["pearson", "spearman", "kendall"])
    parser.add_argument("--data-dir", type=str, default="data/parquet", help="Parquet data directory")
    parser.add_argument("--output-dir", type=str, default="data/graphs", help="Output directory for HTML")
    parser.add_argument("--start", type=str, default=None, help="Start date filter")
    parser.add_argument("--end", type=str, default=None, help="End date filter")
    parser.add_argument("--node-size-by", type=str, default="degree", choices=["volume", "degree"])
    args = parser.parse_args()

    store = ParquetStore(base_dir=args.data_dir)

    # Determine symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        symbols = store.get_available_symbols()

    if not symbols:
        print("No symbols found in store. Run download_historical.py first.")
        sys.exit(1)

    print(f"Building correlation graph for {len(symbols)} symbols: {', '.join(symbols)}")
    print(f"Timeframe: {args.timeframe}, Method: {args.method}, Threshold: {args.threshold}")
    print()

    # Load price data for all symbols
    prices_dict: dict[str, pd.Series] = {}
    for symbol in symbols:
        df = store.read(symbol, args.timeframe, start=args.start, end=args.end)
        if df.empty:
            print(f"  [WARN] No data for {symbol}, skipping")
            continue
        prices_dict[symbol] = df.set_index("open_time")["close"]
        print(f"  {symbol}: {len(df)} candles ({df['open_time'].iloc[0].date()} to {df['open_time'].iloc[-1].date()})")

    if len(prices_dict) < 2:
        print("Need at least 2 symbols with data to build a correlation graph.")
        sys.exit(1)

    # Build price DataFrame
    prices = pd.DataFrame(prices_dict)
    print(f"\nPrice matrix: {prices.shape[0]} rows x {prices.shape[1]} columns")

    # Align and compute returns
    prices = align_returns(prices, max_fill_gap=2, min_valid_ratio=0.8)
    returns = calculate_returns(prices, method="log")
    print(f"Returns matrix: {returns.shape[0]} rows x {returns.shape[1]} columns")

    # Compute correlation
    cm = CorrelationMatrix(method=args.method)
    corr = cm.compute(returns)
    print("\nCorrelation matrix:")
    print(corr.round(3))

    # Build graph
    cg = CorrelationGraph(threshold=args.threshold, corr_method=args.method)
    graph = cg.build(corr)

    # Compute metrics
    metrics = cg.compute_metrics(graph)
    print("\nGraph metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Detect communities
    communities = cg.detect_communities(graph)
    print("\nCommunities:")
    comm_groups: dict[int, list[str]] = {}
    for node, comm_id in communities.items():
        comm_groups.setdefault(comm_id, []).append(node)
    for comm_id, members in comm_groups.items():
        print(f"  Community {comm_id}: {', '.join(members)}")

    # Centrality
    centrality = cg.compute_centrality(graph)
    print("\nCentrality (sorted by degree):")
    sorted_nodes = sorted(centrality.items(), key=lambda x: x[1]["degree_raw"], reverse=True)
    for node, metrics_node in sorted_nodes:
        print(f"  {node}: degree={metrics_node['degree_raw']}, betweenness={metrics_node['betweenness']:.3f}")

    # Add volume attribute for visualization
    for symbol in graph.nodes():
        df = store.read(symbol, args.timeframe)
        if not df.empty:
            graph.nodes[symbol]["volume"] = float(df["quote_volume"].sum())
        else:
            graph.nodes[symbol]["volume"] = 1e9

    # Visualize
    viz = GraphVisualizer(
        output_dir=args.output_dir,
        node_size_by=args.node_size_by,
        edge_threshold=args.threshold,
    )
    title = f"Correlation Graph {args.method} threshold {args.threshold} ({len(symbols)} assets)"
    output_path = viz.visualize(graph, title=title)
    print(f"\nGraph visualization saved to: {output_path}")

    # Save correlation matrix as CSV
    corr_path = Path(args.output_dir) / f"correlation_matrix_{args.method}.csv"
    corr.to_csv(corr_path)
    print(f"Correlation matrix saved to: {corr_path}")


if __name__ == "__main__":
    main()
