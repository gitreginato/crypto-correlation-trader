#!/usr/bin/env python3
"""Continuously refresh the live dashboard while the collector runs.

Runs analyze_live.py in a loop, regenerating the dashboard every N seconds.
This keeps the HTML dashboard fresh without manual intervention.

Usage:
    python scripts/refresh_dashboard.py --interval 30
    python scripts/refresh_dashboard.py --interval 15 --recent-hours 0.5
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent


def main():
    parser = argparse.ArgumentParser(description="Continuously refresh live dashboard")
    parser.add_argument("--interval", type=int, default=30, help="Refresh interval in seconds (default: 30)")
    parser.add_argument("--recent-hours", type=float, default=4.0, help="Hours of data to load (default: 4h)")
    parser.add_argument("--data-dir", type=str, default="data/live")
    parser.add_argument("--output", type=str, default="data/live/dashboard.html")
    args = parser.parse_args()

    print(f"Dashboard auto-refresh started (every {args.interval}s, last {args.recent_hours}h of data)")
    print("Press Ctrl+C to stop.")
    print()

    iteration = 0
    while True:
        iteration += 1
        start = time.time()

        cmd = [
            sys.executable,
            str(project_root / "scripts" / "analyze_live.py"),
            "--data-dir", args.data_dir,
            "--output", args.output,
            "--recent-hours", str(args.recent_hours),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(project_root))
            elapsed = time.time() - start
            if result.returncode == 0:
                # Extract file size
                out_path = Path(args.output)
                size_kb = out_path.stat().st_size / 1024 if out_path.exists() else 0
                print(f"[{time.strftime('%H:%M:%S')}] #{iteration} OK ({elapsed:.1f}s, {size_kb:.0f}KB)")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] #{iteration} ERROR: {result.stderr.strip()[:200]}")
        except subprocess.TimeoutExpired:
            print(f"[{time.strftime('%H:%M:%S')}] #{iteration} TIMEOUT (>120s)")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] #{iteration} EXCEPTION: {e}")

        # Wait for next interval (minus time spent)
        wait = max(1, args.interval - (time.time() - start))
        time.sleep(wait)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
