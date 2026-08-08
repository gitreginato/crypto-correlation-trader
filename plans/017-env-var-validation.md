# Plan 017: Add .env.example + env var validation at startup

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- .env.example src/config.py scripts/download_historical.py scripts/run_collector.py scripts/run_backtest.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

AGENTS.md line 16 mandates: "Validar presenca de env vars no startup (fail
fast)". The project lists `python-dotenv>=1.0` in requirements.txt (line 33)
but no code ever calls `load_dotenv()` or reads environment variables. There
is no `.env.example` file to guide developers on which variables are needed.
This means if someone tries to run a script that needs API keys, it fails
with a cryptic error deep in the call stack instead of a clear message at
startup. Adding `.env.example` and a `load_env()` function that validates
required variables makes the project's configuration contract explicit and
fails fast with a helpful message.

## Current state

**No `.env.example` exists:**

```
$ ls .env.example
ls: .env.example: No such file or directory
```

**`python-dotenv` is in requirements.txt but never used:**

requirements.txt line 33:
```
python-dotenv>=1.0
```

A search for `os.getenv`, `os.environ`, `load_dotenv` across the entire
codebase returns zero matches. No code reads environment variables.

**AGENTS.md mandates env var validation (line 16):**

```
- Validar presenca de env vars no startup (fail fast)
```

**Entry point scripts that need env vars:**

1. `scripts/download_historical.py` (275 lines): Downloads data from Binance.
   Currently uses no API keys (Vision + public REST), but may need them for
   higher rate limits. Lines 9-14 show the import block:

   ```python
   import argparse
   import io
   import sys
   import time
   import zipfile
   from pathlib import Path
   ```

   The `sys.path` insertion happens at lines 20-21:
   ```python
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root))
   ```

   The `main()` function starts at line 222.

2. `scripts/run_collector.py` (154 lines): Runs the real-time WebSocket
   collector. Lines 19-24 show the import block:

   ```python
   import argparse
   import asyncio
   import logging
   import signal
   import sys
   from pathlib import Path
   ```

   The `sys.path` insertion happens at lines 26-27:
   ```python
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root))
   ```

   The `main()` function starts at line 85.

3. `scripts/run_backtest.py` (230 lines): Runs strategy backtests. Lines 6-12
   show the import block:

   ```python
   import argparse
   import sys
   from pathlib import Path

   # Ensure project root is in path
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root))
   ```

   The `main()` function starts at line 178.

**No `src/config.py` exists:**

```
$ ls src/config.py
ls: src/config.py: No such file or directory
```

**`.gitignore` already covers `.env`:**

The `.gitignore` file includes standard Python patterns. Verify that `.env`
is covered. If it is not, add it (but this is a STOP condition, not an
in-scope fix, since `.gitignore` is out of scope for this plan).

**Repo conventions (AGENTS.md):**
- Python 3.11+, type hints obligatory (line 44)
- 4-space indent, 120 char max line (lines 45-46)
- snake_case for functions/variables (line 47)
- No em-dash in any file (line 9)
- NUNCA hardcodear API keys (line 13)
- SEMPRE usar `.env` com `python-dotenv` (line 14)

## Commands you will need

| Purpose          | Command                                              | Expected on success |
|-----------------|------------------------------------------------------|---------------------|
| Import check    | `python -c "from src.config import load_env"`        | exit 0              |
| Lint            | `ruff check src/config.py`                           | exit 0              |
| Lint (scripts)  | `ruff check scripts/download_historical.py scripts/run_collector.py scripts/run_backtest.py` | exit 0 |
| Typecheck       | `mypy src/config.py`                                 | exit 0, no errors   |

## Scope

**In scope** (the only files you should create or modify):
- `.env.example` (create)
- `src/config.py` (create)
- `scripts/download_historical.py` (add import + call)
- `scripts/run_collector.py` (add import + call)
- `scripts/run_backtest.py` (add import + call)

**Out of scope** (do NOT touch, even though they look related):
- All other source files in `src/` and `scripts/`
- `requirements.txt` (python-dotenv is already listed)
- `.gitignore` (if `.env` is not covered, report it as a STOP condition)
- Any test files

## Git workflow

- Branch: `advisor/017-env-var-validation`
- Commit per step or per logical unit; message style: conventional commits
  (e.g. `feat: add env var validation at startup with .env.example`)
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Create `.env.example`

Create the file `.env.example` at the project root with placeholder values
for all environment variables the project expects. Use clearly fake
placeholder values, never real secrets.

```env
# Binance API credentials
# Required for: live trading, higher rate limits on REST API
# Get them at: https://www.binance.com/en/my/settings/api-management
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# Telegram bot notifications
# Required for: trade alerts, error notifications, kill switch alerts
# Create a bot: https://t.me/botfather
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

**Verify**: `cat .env.example` shows the 4 variables with placeholder values. Confirm no real secrets are present.

### Step 2: Create `src/config.py`

Create the file `src/config.py` with a `load_env()` function that:
1. Calls `load_dotenv()` from python-dotenv to load `.env` if it exists.
2. Validates that required environment variables are present.
3. Raises `RuntimeError` with a clear message listing missing variables if
   any are absent.

```python
"""Environment variable loading and validation at startup.

Calls load_dotenv() to load .env if present, then validates that required
environment variables are set. Fails fast with a clear message if any are
missing.
"""
import os
from typing import NoReturn

from dotenv import load_dotenv

# Variables required for live trading and notifications.
# Download-only scripts (Vision, public REST) do not need these.
REQUIRED_VARS: list[str] = [
    "BINANCE_API_KEY",
    "BINANCE_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def load_env(required: bool = True) -> None:
    """Load .env file and validate required environment variables.

    Args:
        required: If True, raise RuntimeError when required vars are missing.
            If False, load .env but do not validate (for scripts that only
            use public endpoints and do not need API keys).

    Raises:
        RuntimeError: If required is True and one or more required
            environment variables are not set.
    """
    load_dotenv()

    if not required:
        return

    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your values."
        )


def fail_fast_missing_env(missing_vars: list[str]) -> NoReturn:
    """Raise a RuntimeError listing missing environment variables.

    Args:
        missing_vars: List of variable names that are not set.

    Raises:
        RuntimeError: Always, with a descriptive message.
    """
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}. "
        f"Copy .env.example to .env and fill in your values."
    )
```

Key design decisions:
- `load_env(required=True)` is the default for scripts that need API keys.
  Scripts that only use public endpoints (like `download_historical.py`
  which uses Binance Vision) can call `load_env(required=False)` to load
  `.env` without requiring keys.
- The `REQUIRED_VARS` list is a module-level constant so it can be inspected
  and tested.
- The error message tells the user to copy `.env.example`, which makes the
  fix actionable.
- `fail_fast_missing_env` is a separate utility function for code that
  validates env vars outside of `load_env()`.

**Verify**: `python -c "from src.config import load_env"` exits 0. Then `ruff check src/config.py` exits 0. Then `mypy src/config.py` exits 0.

### Step 3: Add `load_env()` call to `scripts/download_historical.py`

This script uses Binance Vision (public data) and the public REST API. It
does not strictly require API keys, so it should call `load_env(required=False)`
to load `.env` if present (for optional rate-limit benefits) without failing
if keys are absent.

Add the import after the existing `sys.path.insert` line (line 21). The
current import block is:

```python
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.parquet_store import ParquetStore
from src.data.universe import Universe
```

Change it to:

```python
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import load_env
from src.data.parquet_store import ParquetStore
from src.data.universe import Universe
```

Then add the `load_env()` call at the beginning of `main()`, before
`argparse`. The current `main()` starts at line 222:

```python
def main():
    parser = argparse.ArgumentParser(description="Download historical OHLCV data from Binance")
```

Change it to:

```python
def main():
    load_env(required=False)
    parser = argparse.ArgumentParser(description="Download historical OHLCV data from Binance")
```

**Verify**: `ruff check scripts/download_historical.py` exits 0. `python scripts/download_historical.py --help` exits 0 (shows argparse help, no env error).

### Step 4: Add `load_env()` call to `scripts/run_collector.py`

This script runs the real-time WebSocket collector. It uses public
WebSocket streams but may need API keys for authenticated streams. Call
`load_env(required=False)` to load `.env` without failing if keys are
absent (public streams work without keys).

Add the import after the existing `sys.path.insert` line (line 27). The
current import block is:

```python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.live_collector import LiveCollector, CollectorConfig
```

Change it to:

```python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import load_env
from src.data.live_collector import LiveCollector, CollectorConfig
```

Then add the `load_env()` call at the beginning of `main()`, before
`argparse`. The current `main()` starts at line 85:

```python
def main():
    parser = argparse.ArgumentParser(description="Real-time Binance Futures data collector")
```

Change it to:

```python
def main():
    load_env(required=False)
    parser = argparse.ArgumentParser(description="Real-time Binance Futures data collector")
```

**Verify**: `ruff check scripts/run_collector.py` exits 0. `python scripts/run_collector.py --help` exits 0 (shows argparse help, no env error).

### Step 5: Add `load_env()` call to `scripts/run_backtest.py`

This script runs backtests on local data. It does not need API keys, so
call `load_env(required=False)` to load `.env` if present without requiring
keys.

Add the import after the existing `sys.path.insert` line (line 12). The
current import block is:

```python
# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

from src.data.parquet_store import ParquetStore
```

Change it to:

```python
# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

from src.config import load_env
from src.data.parquet_store import ParquetStore
```

Then add the `load_env()` call at the beginning of `main()`, before
`argparse`. The current `main()` starts at line 178:

```python
def main():
    parser = argparse.ArgumentParser(description="Run strategy backtests")
```

Change it to:

```python
def main():
    load_env(required=False)
    parser = argparse.ArgumentParser(description="Run strategy backtests")
```

**Verify**: `ruff check scripts/run_backtest.py` exits 0. `python scripts/run_backtest.py --help` exits 0 (shows argparse help, no env error).

## Test plan

No new test files are required for this plan (the `load_env` function is
simple enough that the import check and manual verification suffice). If a
reviewer requests tests, they can be added in a follow-up plan. The
verification commands above confirm:

- `load_env` is importable from `src.config`.
- `load_env(required=False)` does not raise when env vars are missing.
- All three entry-point scripts still run `--help` without errors.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `.env.example` exists at project root with 4 placeholder variables
- [ ] `python -c "from src.config import load_env"` exits 0
- [ ] `ruff check src/config.py` exits 0
- [ ] `mypy src/config.py` exits 0
- [ ] `ruff check scripts/download_historical.py scripts/run_collector.py scripts/run_backtest.py` exits 0
- [ ] `python scripts/download_historical.py --help` exits 0
- [ ] `python scripts/run_collector.py --help` exits 0
- [ ] `python scripts/run_backtest.py --help` exits 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The file `.gitignore` does not contain `.env` (or a pattern that covers
  it). If `.env` is not gitignored, creating `.env.example` is safe but
  developers might accidentally commit real `.env` files. Report this so
  `.gitignore` can be updated (it is out of scope for this plan).
- `python-dotenv` is not installed and cannot be installed (check
  `requirements.txt` line 33). The `load_env` function imports from
  `dotenv`, so it will fail at import time if the package is missing.
- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- When new scripts are added that need API keys, call `load_env(required=True)`
  at the start of their `main()` function. When scripts only use public
  endpoints, call `load_env(required=False)`.
- If new required environment variables are added (e.g. database URL,
  Redis URL), add them to the `REQUIRED_VARS` list in `src/config.py` and
  to `.env.example`.
- A reviewer should verify that `.env` is in `.gitignore` before merging,
  to prevent accidental secret exposure.
- Future plan: add unit tests for `load_env()` (test that it raises with
  missing vars, test that it passes when all vars are set, test
  `required=False` path). This was deferred to keep the plan small.
