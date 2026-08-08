# Plan 009: Write tests for risk/PnL + add network mocks

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report: do not improvise. When done, update the status row for this plan
> in `plans/README.md`: unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- src/backtest/engine.py scripts/download_historical.py`
> If either file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. Note: this plan only creates
> new test files, it does not modify source files.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans/002-backtest-correctness-bugs.md
- **Category**: tests
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The backtest engine has zero unit tests for its risk and PnL logic:
stop loss, take profit, position sizing, slippage, fee deduction, and
unrealized PnL computation. These are the most financially critical
calculations in the system: a bug in position sizing or PnL means
backtest results are wrong, leading to bad trading decisions. The
existing `tests/test_backtest_engine.py` tests behavior end to end but
does not isolate these methods, so a regression in `_check_exits` or
`_compute_unrealized_pnl` could be masked by other logic.

Additionally, `scripts/download_historical.py` makes real HTTP requests
to Binance Vision and Binance REST API with no test coverage and no
mocking. Any test that accidentally hits the real API is flaky and
depends on Binance availability. This plan adds unit tests for the
download functions with `responses` (for the `requests` library) to
mock all HTTP calls.

This plan depends on plan 002 because the position close logic and
division-by-zero guards must be correct before writing tests against
them: testing broken code validates the wrong behavior.

## Current state

The relevant files (read only, do NOT modify):

- `src/backtest/engine.py`: backtest engine. Key methods to test:
  - `_open_position` (line 137): applies slippage, computes position
    size from risk and stop distance, caps at 20% of capital, deducts
    entry fee, creates `Position` object, calls `strategy.on_fill`.
  - `_close_position` (line 171): applies slippage, computes PnL
    (long: `(exit - entry) * size`, short: `(entry - exit) * size`),
    deducts exit fee, adds PnL to capital, records `Trade`.
  - `_check_exits` (line 212): checks stop loss and take profit for
    each open position, collects close list, closes them.
  - `_compute_unrealized_pnl` (line 240): sums unrealized PnL across
    all open positions at current prices.
- `scripts/download_historical.py`: download script. Key functions:
  - `download_from_vision` (line 38): GET to
    `https://data.binance.vision/data/spot/monthly/klines/{symbol}/{timeframe}/{symbol}-{timeframe}-{year}-{month}.zip`,
    returns DataFrame or empty DataFrame on 404.
  - `download_from_api` (line 75): paginated GET to
    `https://api.binance.com/api/v3/klines`, returns DataFrame.
  - `download_symbol` (line 133): orchestrates vision or api download,
    stores via `ParquetStore`.

Key code excerpts:

`_open_position` (line 137):

```python
    def _open_position(self, signal: Signal, fill_price: float, capital: float) -> float:
        if signal.is_long:
            actual_price = fill_price * (1 + self.config.slippage_rate)
        else:
            actual_price = fill_price * (1 - self.config.slippage_rate)

        risk_amount = capital * self.config.risk_per_trade * signal.confidence
        if signal.stop_loss and signal.stop_loss > 0:
            stop_distance = abs(actual_price - signal.stop_loss)
            size = risk_amount / stop_distance if stop_distance > 0 else risk_amount / actual_price
        else:
            size = risk_amount / actual_price

        max_position_value = capital * 0.20
        if size * actual_price > max_position_value:
            size = max_position_value / actual_price

        fee = size * actual_price * self.config.fee_rate
        capital -= fee

        self.positions[signal.symbol] = Position(
            signal=signal, size=size, entry_price=actual_price,
            entry_time=signal.timestamp,
        )
        self.strategy.on_fill(signal, actual_price)
        return capital
```

`_check_exits` (line 212):

```python
    def _check_exits(self, timestamp, current_prices, capital):
        to_close = []
        for symbol, pos in self.positions.items():
            if symbol not in current_prices:
                continue
            price = current_prices[symbol]
            if pos.signal.stop_loss is not None:
                if pos.signal.is_long and price <= pos.signal.stop_loss:
                    to_close.append((symbol, "stop_loss"))
                elif pos.signal.is_short and price >= pos.signal.stop_loss:
                    to_close.append((symbol, "stop_loss"))
            if pos.signal.take_profit is not None:
                if pos.signal.is_long and price >= pos.signal.take_profit:
                    to_close.append((symbol, "take_profit"))
                elif pos.signal.is_short and price <= pos.signal.take_profit:
                    to_close.append((symbol, "take_profit"))
        for symbol, reason in to_close:
            capital = self._close_position(symbol, current_prices[symbol], timestamp, capital, reason)
        return capital
```

`_compute_unrealized_pnl` (line 240):

```python
    def _compute_unrealized_pnl(self, current_prices):
        total = 0.0
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                if pos.signal.is_long:
                    total += (price - pos.entry_price) * pos.size
                else:
                    total += (pos.entry_price - price) * pos.size
        return total
```

`download_from_vision` (line 38):

```python
def download_from_vision(symbol, timeframe, year, month):
    url = f"{VISION_BASE}/monthly/klines/{symbol}/{timeframe}/{year}-{month:02d}.zip"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return pd.DataFrame()
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] Vision download failed for {symbol} {year}-{month:02d}: {e}")
        return pd.DataFrame()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as f:
            df = pd.read_csv(f, header=None, names=KLINE_COLUMNS)
    # ... type conversions ...
    return df
```

Constants in `scripts/download_historical.py` (lines 27-29):

```python
VISION_BASE = "https://data.binance.vision/data/spot"
API_BASE = "https://api.binance.com/api/v3"
```

`KLINE_COLUMNS` in `scripts/download_historical.py` (line 31):

```python
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]
```

Data classes needed for tests (`src/backtest/engine.py`):

```python
@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    risk_per_trade: float = 0.01
    fee_rate: float = 0.001
    slippage_rate: float = 0.0005
    max_positions: int = 10
    funding_rate_per_8h: float = 0.0

@dataclass
class Position:
    signal: Signal
    size: float
    entry_price: float
    entry_time: pd.Timestamp
    bars_held: int = 0
```

`Signal` from `src/strategy/base.py` (line 27):

```python
@dataclass
class Signal:
    timestamp: pd.Timestamp
    symbol: str
    direction: Direction
    price: float
    confidence: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_id: str = ""
    metadata: dict = field(default_factory=dict)
```

Repo conventions (from `AGENTS.md`):

- Python 3.11+, type hints required.
- 4-space indent, 120 char max line.
- Functions max 30 lines (ideal < 15).
- Test data: fixtures with synthetic data (seed fixo).
- NUNCA usar travessao (em-dash). Use ":" or "." or "," instead.
- NUNCA simular ou fabricar dados de preco. Test data must be synthetic.

Exemplar for test structure: `tests/test_backtest_engine.py` uses
`SimpleBuyHoldStrategy` and `make_ohlcv(n, trend)` helper.

For HTTP mocking of the `requests` library, use `responses` package.
Check if installed: `pip show responses`. If not, install:
`pip install responses`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests   | `pytest tests/test_risk_pnl.py tests/test_download_historical.py -v` | all pass, exit 0 |
| Lint    | `ruff check tests/test_risk_pnl.py tests/test_download_historical.py` | exit 0 |
| Check dep | `pip show responses` | installed |

## Suggested executor toolkit

- Use `responses` package for mocking `requests.get` calls in
  `download_historical.py`. It patches at the adapter level, so no
  code changes are needed in the script.
- Use `unittest.mock.MagicMock` for mocking `BaseStrategy` in risk/PnL
  tests (to avoid depending on a real strategy implementation).
- Reference: `tests/test_backtest_engine.py` for `BacktestEngine` setup
  patterns and `make_ohlcv` helper.

## Scope

**In scope** (the only files you should create):
- `tests/test_risk_pnl.py` (create new)
- `tests/test_download_historical.py` (create new)

**Out of scope** (do NOT touch):
- `src/backtest/engine.py`: only read it to understand the methods. Do
  NOT modify it. If a bug is found, report it but do not fix it.
- `scripts/download_historical.py`: only read it. Do NOT modify it.
- Any other source file.
- `requirements.txt`: do NOT add `responses` to requirements.txt.
  Install in dev environment only.

## Git workflow

- Branch: `advisor/009-risk-pnl-download-tests`
- Commit per test file. Message style:
  `test(risk_pnl): <description>` and
  `test(download_historical): <description>`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Verify plan 002 is complete and install test dependency

Confirm plan 002 (backtest correctness bugs) is DONE. If not, STOP.

```bash
pip install responses
```

**Verify**:
- `grep "| 002 |" plans/README.md` shows `DONE`.
- `pip show responses` exits 0.

### Step 2: Create `tests/test_risk_pnl.py` with fixtures

Create the file with imports, a mock strategy fixture, and an engine
fixture:

```python
"""Unit tests for backtest risk and PnL calculations.

Tests _open_position, _close_position, _check_exits,
_compute_unrealized_pnl in isolation. All data is synthetic.
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from src.backtest.engine import BacktestEngine, BacktestConfig, Position
from src.strategy.base import Signal, Direction, StrategyConfig


@pytest.fixture
def mock_strategy():
    """A mock strategy that records on_fill and on_close calls."""
    strategy = MagicMock()
    strategy.config = StrategyConfig(strategy_id="test")
    strategy.positions = {}
    strategy.on_fill = MagicMock()
    strategy.on_close = MagicMock()
    return strategy


@pytest.fixture
def engine(mock_strategy) -> BacktestEngine:
    """BacktestEngine with zero fees and slippage for clean math."""
    return BacktestEngine(mock_strategy, BacktestConfig(
        initial_capital=10000.0,
        risk_per_trade=0.01,
        fee_rate=0.0,
        slippage_rate=0.0,
        max_positions=10,
    ))


def make_long_signal(symbol: str = "BTC", price: float = 100.0,
                     stop_loss: float = 95.0, take_profit: float = 110.0) -> Signal:
    return Signal(
        timestamp=pd.Timestamp("2024-01-01", tz="UTC"),
        symbol=symbol,
        direction=Direction.LONG,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy_id="test",
    )


def make_short_signal(symbol: str = "BTC", price: float = 100.0,
                      stop_loss: float = 105.0, take_profit: float = 90.0) -> Signal:
    return Signal(
        timestamp=pd.Timestamp("2024-01-01", tz="UTC"),
        symbol=symbol,
        direction=Direction.SHORT,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy_id="test",
    )
```

**Verify**: `ruff check tests/test_risk_pnl.py` exits 0.

### Step 3: Write tests for `_open_position`

Add `TestOpenPosition` class with:

1. `test_open_long_position_creates_position`: open a long at price
   100, assert `engine.positions["BTC"]` exists with `entry_price=100`,
   `size > 0`.
2. `test_open_short_position_creates_position`: open a short, assert
   position exists with correct direction.
3. `test_slippage_increases_long_entry_price`: set
   `slippage_rate=0.001`, open long at 100, assert
   `entry_price == 100 * 1.001`.
4. `test_slippage_decreases_short_entry_price`: set
   `slippage_rate=0.001`, open short at 100, assert
   `entry_price == 100 * 0.999`.
5. `test_entry_fee_deducted_from_capital`: set `fee_rate=0.001`, open
   position, assert capital decreased by `size * entry_price * 0.001`.
6. `test_position_size_from_risk_and_stop_distance`: with
   `risk_per_trade=0.01`, capital=10000, confidence=1.0, entry=100,
   stop=95 (distance=5), assert `size == 100 / 5 == 20.0`.
7. `test_position_size_capped_at_20pct`: with very wide stop (distance
   = 1), the raw size would be huge. Assert
   `size * entry_price <= capital * 0.20`.
8. `test_on_fill_called_with_actual_price`: assert
   `mock_strategy.on_fill` was called with the signal and the actual
   (post-slippage) price.
9. `test_no_stop_loss_uses_price_based_sizing`: signal with
   `stop_loss=None`, assert size is `risk_amount / entry_price`.

**Verify**: `pytest tests/test_risk_pnl.py::TestOpenPosition -v` exits
0, all 9 tests pass.

### Step 4: Write tests for `_close_position` and PnL

Add `TestClosePosition` class with:

1. `test_close_long_with_profit`: open long at 100, close at 110,
   assert `pnl == (110 - 100) * size` and capital increased.
2. `test_close_long_with_loss`: open long at 100, close at 90, assert
   `pnl == (90 - 100) * size` (negative) and capital decreased.
3. `test_close_short_with_profit`: open short at 100, close at 90,
   assert `pnl == (100 - 90) * size` (positive).
4. `test_close_short_with_loss`: open short at 100, close at 110,
   assert `pnl == (100 - 110) * size` (negative).
5. `test_exit_fee_deducted`: set `fee_rate=0.001`, close position,
   assert `pnl` is reduced by `size * exit_price * 0.001`.
6. `test_close_records_trade`: after closing, assert
   `len(engine.trades) == 1` and the `Trade` has correct
   `entry_price`, `exit_price`, `direction`, `pnl`.
7. `test_close_calls_on_close`: assert `mock_strategy.on_close` was
   called with the symbol.
8. `test_pnl_pct_calculated`: assert `trade.pnl_pct` equals
   `pnl / (size * entry_price)`.

To set up a position for close tests, manually insert a `Position` into
`engine.positions` before calling `_close_position`:

```python
engine.positions["BTC"] = Position(
    signal=make_long_signal(price=100.0),
    size=10.0,
    entry_price=100.0,
    entry_time=pd.Timestamp("2024-01-01", tz="UTC"),
)
capital = engine._close_position("BTC", 110.0, pd.Timestamp("2024-01-02", tz="UTC"), 10000.0)
```

**Verify**: `pytest tests/test_risk_pnl.py::TestClosePosition -v` exits
0, all 8 tests pass.

### Step 5: Write tests for `_check_exits`

Add `TestCheckExits` class with:

1. `test_stop_loss_triggers_for_long`: insert a long position with
   stop=95, current_price=94. Assert position is closed with reason
   `"stop_loss"`.
2. `test_stop_loss_triggers_for_short`: insert a short position with
   stop=105, current_price=106. Assert closed with `"stop_loss"`.
3. `test_take_profit_triggers_for_long`: insert long with TP=110,
   current_price=111. Assert closed with `"take_profit"`.
4. `test_take_profit_triggers_for_short`: insert short with TP=90,
   current_price=89. Assert closed with `"take_profit"`.
5. `test_no_exit_when_price_between_stop_and_tp`: insert long with
   stop=95, TP=110, current_price=100. Assert position remains open.
6. `test_missing_price_skips_position`: insert position for "ETH" but
   only provide price for "BTC". Assert ETH position is not closed.
7. `test_multiple_positions_closed_in_one_call`: insert 2 positions
   both hitting stop loss. Assert both are closed.

**Verify**: `pytest tests/test_risk_pnl.py::TestCheckExits -v` exits 0,
all 7 tests pass.

### Step 6: Write tests for `_compute_unrealized_pnl`

Add `TestUnrealizedPnl` class with:

1. `test_no_positions_returns_zero`: empty positions dict, assert
   returns 0.0.
2. `test_long_unrealized_profit`: long at 100, current 110, size=10,
   assert `== (110 - 100) * 10 == 100.0`.
3. `test_long_unrealized_loss`: long at 100, current 90, size=10,
   assert `== (90 - 100) * 10 == -100.0`.
4. `test_short_unrealized_profit`: short at 100, current 90, size=10,
   assert `== (100 - 90) * 10 == 100.0`.
5. `test_mixed_positions_summed`: one long profitable, one short
   profitable, assert total is the sum.
6. `test_position_without_price_skipped`: position for "ETH" but no
   price provided, assert it contributes 0 to the total.

**Verify**: `pytest tests/test_risk_pnl.py::TestUnrealizedPnl -v` exits
0, all 6 tests pass.

### Step 7: Create `tests/test_download_historical.py` with vision mocks

Create the file with imports and a helper to build a valid ZIP response:

```python
"""Tests for download_historical.py with mocked HTTP calls.

All Binance API calls are mocked with the `responses` library.
No real network requests are made. Test data is synthetic.
"""
import io
import zipfile

import pandas as pd
import pytest
import responses

from scripts.download_historical import (
    download_from_vision,
    download_from_api,
    download_symbol,
    VISION_BASE,
    API_BASE,
    KLINE_COLUMNS,
)


def make_klines_zip(symbol: str, timeframe: str, year: int, month: int,
                    n_rows: int = 5) -> bytes:
    """Build a ZIP file containing a CSV with synthetic kline data."""
    csv_lines = []
    for i in range(n_rows):
        open_ts = int(pd.Timestamp(f"{year}-{month:02d}-01", tz="UTC").timestamp() * 1000) + i * 300000
        close_ts = open_ts + 300000
        row = [
            open_ts, "100.0", "105.0", "95.0", "102.0", "1000.0",
            close_ts, "102000.0", "50", "500.0", "51000.0", "0",
        ]
        csv_lines.append(",".join(str(v) for v in row))
    csv_content = "\n".join(csv_lines) + "\n"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{symbol}-{timeframe}-{year}-{month:02d}.csv", csv_content)
    return buf.getvalue()
```

Add `TestDownloadFromVision` class with:

1. `test_vision_success_returns_dataframe`: mock
   `GET {VISION_BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2024-01.zip`
   to return the ZIP bytes with status 200. Call
   `download_from_vision("BTCUSDT", "5m", 2024, 1)`. Assert the result
   is a non-empty DataFrame with `KLINE_COLUMNS` (minus "ignore").
2. `test_vision_404_returns_empty_dataframe`: mock the URL to return
   404. Assert the result is an empty DataFrame.
3. `test_vision_connection_error_returns_empty`: mock the URL to raise
   `requests.ConnectionError`. Assert the result is an empty DataFrame
   and no exception propagates.
4. `test_vision_parses_open_time_as_datetime`: assert the
   `open_time` column is datetime64 with UTC timezone.

Use `@responses.activate` decorator on each test.

**Verify**: `pytest tests/test_download_historical.py::TestDownloadFromVision -v`
exits 0, all 4 tests pass.

### Step 8: Write tests for `download_from_api` with mocked REST

Add `TestDownloadFromApi` class with:

1. `test_api_success_returns_dataframe`: mock
   `GET {API_BASE}/klines` to return a list of kline arrays (the
   Binance API format: list of lists). Assert the result is a
   non-empty DataFrame.
2. `test_api_pagination`: mock the first response with 1000 rows (full
   page) and the second with 100 rows. Assert the total DataFrame has
   1100 rows. This tests the pagination loop.
3. `test_api_empty_response_returns_empty`: mock to return empty list
   `[]`. Assert the result is an empty DataFrame.
4. `test_api_connection_error_continues_and_returns_empty`: mock to
   raise `requests.ConnectionError`. Assert the result is an empty
   DataFrame (the code does `time.sleep(2)` and `continue`, then the
   loop exits because `current_start` does not advance). NOTE: patch
   `time.sleep` to avoid real delays:
   `@patch("scripts.download_historical.time.sleep")`.

Example Binance kline response format (list of lists):

```python
kline_data = [
    [1700000000000, "100.0", "105.0", "95.0", "102.0", "1000.0",
     1700000300000, "102000.0", "50", "500.0", "51000.0", "0"],
]
```

**Verify**: `pytest tests/test_download_historical.py::TestDownloadFromApi -v`
exits 0, all 4 tests pass.

### Step 9: Write tests for `download_symbol` integration

Add `TestDownloadSymbol` class with:

1. `test_download_symbol_vision_source`: mock the Vision URL, call
   `download_symbol("BTCUSDT", "5m", "2024-01-01", "2024-01-31",
   store, source="vision")`. Assert the return value is the number of
   candles and the store has data. Use a `ParquetStore` with `tmp_path`.
2. `test_download_symbol_api_source`: mock the API URL, call with
   `source="api"`. Assert candles are stored.
3. `test_download_symbol_no_data_returns_zero`: mock Vision to return
   404 for all months. Assert return value is 0.

Use `@responses.activate` and `ParquetStore(base_dir=str(tmp_path))`.

**Verify**: `pytest tests/test_download_historical.py::TestDownloadSymbol -v`
exits 0, all 3 tests pass.

### Step 10: Run full test suite and lint

**Verify**:
- `pytest tests/test_risk_pnl.py tests/test_download_historical.py -v`
  exits 0, all tests pass (expect approximately 30 tests total: 30 in
  risk_pnl + 11 in download_historical).
- `ruff check tests/test_risk_pnl.py tests/test_download_historical.py`
  exits 0.

## Test plan

New test files:

1. `tests/test_risk_pnl.py`: 30 unit tests for backtest risk/PnL.
   - `TestOpenPosition` (9 tests): position creation, slippage, fee
     deduction, sizing from risk/stop, 20% cap, on_fill callback,
     no-stop-loss sizing.
   - `TestClosePosition` (8 tests): long/short profit/loss, exit fee,
     trade recording, on_close callback, pnl_pct.
   - `TestCheckExits` (7 tests): stop loss long/short, take profit
     long/short, no-exit range, missing price, multiple closes.
   - `TestUnrealizedPnl` (6 tests): empty, long profit/loss, short
     profit/loss, mixed sum, missing price.

2. `tests/test_download_historical.py`: 11 tests for download script.
   - `TestDownloadFromVision` (4 tests): success, 404, connection
     error, datetime parsing.
   - `TestDownloadFromApi` (4 tests): success, pagination, empty
     response, connection error.
   - `TestDownloadSymbol` (3 tests): vision source, api source, no
     data.

Structural pattern: model after `tests/test_backtest_engine.py` for
risk/PnL (class-based, helper functions for signals). Model after
`tests/test_parquet_store.py` for download tests (tmp_path fixture,
synthetic data).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pytest tests/test_risk_pnl.py tests/test_download_historical.py -v`
      exits 0, all tests pass.
- [ ] `ruff check tests/test_risk_pnl.py tests/test_download_historical.py`
      exits 0.
- [ ] `tests/test_risk_pnl.py` exists with at least 25 test functions.
- [ ] `tests/test_download_historical.py` exists with at least 10 test
      functions.
- [ ] No files outside the two new test files are modified
      (`git status`).
- [ ] No test makes a real HTTP call (all mocked with `responses`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back (do not improvise) if:

- `src/backtest/engine.py` lines 137-250 do not match the excerpts in
  "Current state" (the codebase has drifted, or plan 002 changed the
  methods).
- `scripts/download_historical.py` lines 38-130 do not match the
  excerpts (URLs, function signatures, or KLINE_COLUMNS changed).
- Plan 002 is not DONE (check `plans/README.md`). The position close
  logic and division-by-zero guards must be fixed before testing.
- `responses` package cannot be installed (report the error).
- A method being tested has a different signature or behavior than
  documented. This would mean plan 002 changed it: compare and adjust,
  or STOP if the change is too large.
- You discover a bug in `engine.py` or `download_historical.py` while
  writing tests. Report it as a finding but do NOT fix it (out of
  scope). If the bug prevents writing a valid test, STOP and report.
- A step's verification fails twice after a reasonable fix attempt.

## Maintenance notes

- The risk/PnL tests use a `MagicMock` strategy. If the
  `BaseStrategy` interface changes (e.g. `on_fill` signature), the
  mock setup must be updated.
- The download tests mock specific Binance URL patterns. If Binance
  changes their API endpoints or response format, the mocks must be
  updated to match.
- The `make_klines_zip` helper builds synthetic CSV data. If
  `KLINE_COLUMNS` in `download_historical.py` changes (e.g. columns
  added or reordered), the helper must be updated.
- A reviewer should scrutinize: (1) that all PnL math is verified with
  exact numeric assertions (not just "positive" or "negative"), (2)
  that the slippage direction is correct (long pays more, short
  receives less), (3) that the 20% position cap is tested, (4) that no
  download test makes a real network call, (5) that `time.sleep` is
  patched in API tests to avoid real delays.
- Follow-up deferred: integration test that runs a full backtest with
  known data and verifies the final capital matches a hand-calculated
  expected value. This is out of scope because it requires careful
  manual PnL computation.
