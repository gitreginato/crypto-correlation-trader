#!/usr/bin/env python3
"""Run the real-time data collector.

Usage:
    # Collect top 5 symbols (default)
    python scripts/run_collector.py

    # Collect specific symbols
    python scripts/run_collector.py --symbols BTCUSDT,ETHUSDT,SOLUSDT

    # Collect with custom output dir
    python scripts/run_collector.py --output data/live_session_1

    # Collect with verbose logging
    python scripts/run_collector.py --log-level DEBUG

Press Ctrl+C to stop. Data is flushed on shutdown.
"""
import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.live_collector import CollectorConfig, LiveCollector


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_collector(config: CollectorConfig, duration: int = None):
    """Run the collector with graceful shutdown on Ctrl+C or timeout."""
    collector = LiveCollector(config)

    # Setup signal handler for graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logging.info("\nShutdown signal received. Flushing data and stopping...")
        stop_event.set()

    # Register signal handler
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows fallback
            signal.signal(sig, lambda *_: _signal_handler())

    # Start collector in a task
    collector_task = asyncio.create_task(collector.start())

    # Wait for stop signal or timeout
    if duration:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=duration)
        except asyncio.TimeoutError:
            logging.info(f"Duration of {duration}s reached. Stopping.")
    else:
        await stop_event.wait()

    # Stop collector gracefully (flushes all buffers)
    await collector.stop()

    # Cancel the collector task
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        pass

    logging.info("Collector shutdown complete.")


def main():
    parser = argparse.ArgumentParser(description="Real-time Binance Futures data collector")
    parser.add_argument(
        "--symbols", type=str, default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT",
        help="Comma-separated symbols (default: top 5)",
    )
    parser.add_argument(
        "--output", type=str, default="data/live",
        help="Output directory for Parquet files",
    )
    parser.add_argument(
        "--flush-interval", type=float, default=10.0,
        help="Flush interval in seconds (default: 10)",
    )
    parser.add_argument(
        "--depth-levels", type=int, default=20,
        help="Order book depth levels (default: 20)",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--duration", type=int, default=None,
        help="Run for N seconds then stop (default: run until Ctrl+C)",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    config = CollectorConfig(
        symbols=symbols,
        output_dir=args.output,
        flush_interval=args.flush_interval,
        depth_levels=args.depth_levels,
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("  REAL-TIME DATA COLLECTOR")
    logger.info("=" * 60)
    logger.info(f"  Symbols: {symbols}")
    logger.info(f"  Output: {args.output}")
    logger.info(f"  Flush interval: {args.flush_interval}s")
    logger.info(f"  Depth levels: {args.depth_levels}")
    logger.info(f"  Duration: {args.duration}s" if args.duration else "  Duration: until Ctrl+C")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Streams being collected:")
    logger.info("  - Order book depth (100ms updates)")
    logger.info("  - Aggregated trades (tick-by-tick)")
    logger.info("  - Mark price + funding rate (1s updates)")
    logger.info("  - Liquidation events (all symbols)")
    logger.info("  - Open interest (REST, every 30s)")
    logger.info("  - Long/Short ratio (REST, every 60s)")
    logger.info("")
    logger.info("Press Ctrl+C to stop and flush remaining data.")
    logger.info("")

    if args.duration:
        asyncio.run(run_collector(config, duration=args.duration))
    else:
        asyncio.run(run_collector(config))


if __name__ == "__main__":
    main()
