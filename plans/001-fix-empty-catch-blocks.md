# Plan 001: Fix empty catch blocks in financial calculations

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- scripts/analyze_live.py scripts/statistical_analyzer.py src/strategy/meta.py src/strategy/stat_arb.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

There are 10 bare `except:` and `except Exception: pass` blocks across
financial calculation code. They silently swallow errors and return fallback
values (0.0, empty dict, None) with no log, no context, and no signal that
something went wrong. In a trading bot this is dangerous: a failed Kyle
lambda or half-life calculation looks identical to a legitimate zero, so
downstream signal generation and risk sizing operate on garbage data without
anyone knowing. Replacing bare catches with specific exception types and
adding `logger.warning()` with context makes failures observable and
prevents unrelated exceptions (bugs, KeyboardInterrupt) from being masked.

## Current state

The relevant files and their roles:

- `scripts/analyze_live.py` (1945 lines): live market analysis dashboard
  generator. Contains standalone calculation functions.
- `scripts/statistical_analyzer.py` (788 lines): statistical analysis class
  `StatisticalAnalyzer` with methods for half-life, Kyle lambda, Granger,
  PCA.
- `src/strategy/meta.py` (167 lines): `MetaStrategy` that combines momentum,
  mean reversion, and stat arb sub-strategies.
- `src/strategy/stat_arb.py` (274 lines): pairs/stat-arb strategy with OLS
  hedge ratio and ADF cointegration test.

Excerpts of each bare catch as it exists today:

**scripts/analyze_live.py:151-155** (calc_kyle_lambda):
```python
    try:
        lambda_est = np.linalg.lstsq(aligned[['vol']], aligned['ret'], rcond=None)[0][0]
        return float(lambda_est)
    except:
        return 0.0
```

**scripts/analyze_live.py:331-347** (calc_half_life):
```python
    try:
        X = np.column_stack([x, np.ones_like(x)])
        theta_mu, theta, *_ = np.linalg.lstsq(X, y, rcond=None)[0]
        theta = -theta
        ...
        return {
            'half_life': float(hl),
            ...
        }
    except:
        return {'half_life': float('inf'), 'interpretation': 'Calculation failed'}
```

**scripts/analyze_live.py:474-482** (detect_breakpoints):
```python
    try:
        import ruptures as rpt
        ...
        return [int(b) for b in bkps[:-1]]
    except:
        return []
```

**scripts/analyze_live.py:580-581** (granger_causality):
```python
    except:
        return {'error': 'Test failed'}
```

**scripts/statistical_analyzer.py:291-292** (calculate_half_life):
```python
        except:
            return {'half_life': np.inf, 'error': 'Calculation failed'}
```

**scripts/statistical_analyzer.py:393-394** (calculate_kyle_lambda):
```python
        except:
            return 0.0
```

**scripts/statistical_analyzer.py:525-526** (granger_causality):
```python
        except:
            return {'error': 'Test failed'}
```

**scripts/statistical_analyzer.py:731-733** (cross_sectional_analysis, PCA):
```python
        except:
            explained_var = []
            components = []
```

**src/strategy/meta.py:92-98** (momentum sub-strategy):
```python
        try:
            mom_signals = self.momentum.generate_signals(data)
            for s in mom_signals:
                s.metadata["source_strategy"] = "STRAT-06"
                all_signals.append(s)
        except Exception:
            pass
```

**src/strategy/meta.py:101-107** (mean reversion sub-strategy):
```python
        try:
            mr_signals = self.mean_reversion.generate_signals(data)
            for s in mr_signals:
                s.metadata["source_strategy"] = "STRAT-01"
                all_signals.append(s)
        except Exception:
            pass
```

**src/strategy/meta.py:110-116** (stat arb sub-strategy):
```python
        try:
            sa_signals = self.stat_arb.generate_signals(data)
            for s in sa_signals:
                s.metadata["source_strategy"] = "STRAT-03"
                all_signals.append(s)
        except Exception:
            pass
```

**src/strategy/stat_arb.py:100-104** (ADF test in _find_cointegrated_pair):
```python
        try:
            adf_result = adfuller(spread.dropna(), maxlag=1)
            p_value = adf_result[1]
        except Exception:
            return None
```

Repo conventions that apply here (from `AGENTS.md`):
- "NAO usar try/except pass (empty catch)" is an explicit rule.
- "Erros de dados: raise com contexto (qual symbol, qual periodo)".
- Logging: structured logging with `logging` module, WARNING level for
  alerts. Use `logger = logging.getLogger(__name__)` or the existing module
  logger.
- Python 3.11+, 4-space indent, 120 char lines, snake_case, functions max
  30 lines.

Check if a logger already exists in each file before adding one. For
`scripts/analyze_live.py` and `scripts/statistical_analyzer.py`, grep for
`logger` or `logging` at the top of the file. For `src/strategy/meta.py`
and `src/strategy/stat_arb.py`, same. If no logger exists, add
`import logging` and `logger = logging.getLogger(__name__)` near the top
imports.

## Commands you will need

| Purpose   | Command                          | Expected on success |
|-----------|----------------------------------|---------------------|
| Lint      | `ruff check src/ scripts/`       | exit 0              |
| Tests     | `pytest tests/ -v`               | all pass            |
| Typecheck | `mypy src/`                      | exit 0, no errors   |

## Scope

**In scope** (the only files you should modify):
- `scripts/analyze_live.py`
- `scripts/statistical_analyzer.py`
- `src/strategy/meta.py`
- `src/strategy/stat_arb.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/data/live_collector.py` (resource leak fix is plan 003).
- Any other file in `src/` or `scripts/`.
- Do not change the return values or fallback values themselves, only the
  exception handling and logging around them.

## Git workflow

- Branch: `advisor/001-fix-empty-catch-blocks`
- Commit per file or per logical unit. Message style: conventional commits,
  e.g. `fix(strategy): replace bare except in stat_arb ADF test with specific
  exception and warning log`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add logger to files that lack one

For each in-scope file, check if a module-level `logger` exists. If not,
add `import logging` (in the stdlib import group) and
`logger = logging.getLogger(__name__)` after the imports.

Files that need this check: `scripts/analyze_live.py`,
`scripts/statistical_analyzer.py`, `src/strategy/meta.py`,
`src/strategy/stat_arb.py`.

**Verify**: `python -c "import ast; ast.parse(open('scripts/analyze_live.py').read()); ast.parse(open('scripts/statistical_analyzer.py').read()); ast.parse(open('src/strategy/meta.py').read()); ast.parse(open('src/strategy/stat_arb.py').read())"` -> exit 0

### Step 2: Fix bare except in scripts/analyze_live.py

Replace each bare `except:` with a specific exception type and add a
`logger.warning()` call with context before the fallback return. The
specific types for each location:

- **Line 154** (calc_kyle_lambda): `except (np.linalg.LinAlgError, ValueError, IndexError):`. Log: `logger.warning("Kyle lambda calculation failed: %s", e)`.
- **Line 346** (calc_half_life): `except (np.linalg.LinAlgError, ValueError, IndexError):`. Log: `logger.warning("Half-life calculation failed: %s", e)`.
- **Line 481** (detect_breakpoints): `except (ImportError, ValueError, RuntimeError):`. Log: `logger.warning("Breakpoint detection failed: %s", e)`.
- **Line 580** (granger_causality): `except (ValueError, ImportError, RuntimeError):`. Log: `logger.warning("Granger causality test failed for symbols: %s", e)`.

Pattern to produce for each block:
```python
    except (np.linalg.LinAlgError, ValueError, IndexError) as e:
        logger.warning("Kyle lambda calculation failed: %s", e)
        return 0.0
```

Keep the same fallback return value. Only change the except clause and add
the log line.

**Verify**: `ruff check scripts/analyze_live.py` -> exit 0

### Step 3: Fix bare except in scripts/statistical_analyzer.py

Replace each bare `except:` with specific types and warning logs:

- **Line 291** (calculate_half_life): `except (np.linalg.LinAlgError, ValueError, IndexError) as e:`. Log: `logger.warning("Half-life calculation failed: %s", e)`.
- **Line 393** (calculate_kyle_lambda): `except (np.linalg.LinAlgError, ValueError, IndexError) as e:`. Log: `logger.warning("Kyle lambda calculation failed: %s", e)`.
- **Line 525** (granger_causality): `except (ValueError, ImportError, RuntimeError) as e:`. Log: `logger.warning("Granger causality test failed: %s", e)`.
- **Line 731** (PCA in cross_sectional_analysis): `except (ValueError, np.linalg.LinAlgError) as e:`. Log: `logger.warning("PCA fit failed: %s", e)`.

**Verify**: `ruff check scripts/statistical_analyzer.py` -> exit 0

### Step 4: Fix except-pass in src/strategy/meta.py

Replace each `except Exception: pass` block (lines 97, 106, 115) with a
warning log. These are sub-strategy calls, so the exception type should
remain `Exception` (sub-strategies can fail for many reasons), but the
`pass` must become a log:

- **Line 97** (momentum): `except Exception as e: logger.warning("Momentum sub-strategy failed: %s", e)`.
- **Line 106** (mean reversion): `except Exception as e: logger.warning("Mean reversion sub-strategy failed: %s", e)`.
- **Line 115** (stat arb): `except Exception as e: logger.warning("Stat arb sub-strategy failed: %s", e)`.

**Verify**: `ruff check src/strategy/meta.py` -> exit 0

### Step 5: Fix except in src/strategy/stat_arb.py

Replace the `except Exception: return None` at line 103 with a specific
type and warning log:

- **Line 103** (ADF test): `except (ValueError, np.linalg.LinAlgError) as e:`. Log: `logger.warning("ADF test failed for pair: %s", e)`.

**Verify**: `ruff check src/strategy/stat_arb.py` -> exit 0

### Step 6: Full verification

Run all three quality gates.

**Verify**:
- `ruff check src/ scripts/` -> exit 0
- `pytest tests/ -v` -> all pass
- `mypy src/` -> exit 0

## Test plan

No new tests are required for this plan. The existing test suite must
continue to pass. The changes are behavioral only in the error path (adding
logs), so existing tests should be unaffected.

If you want to add a regression test, model after `tests/test_stat_arb.py`
for the ADF test error path, but this is optional and out of scope unless
the operator requests it.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `ruff check src/ scripts/` exits 0
- [ ] `pytest tests/ -v` exits 0
- [ ] `mypy src/` exits 0
- [ ] `grep -rn "except:" scripts/analyze_live.py scripts/statistical_analyzer.py src/strategy/meta.py src/strategy/stat_arb.py` returns no matches
- [ ] `grep -rn "except Exception:" src/strategy/meta.py` returns no matches with bare `pass` (all have `as e` and a logger call)
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover that a fallback return value is load-bearing for downstream
  logic in a way that changing the exception type would alter behavior
  (e.g. a downstream caller catches the same exception and relies on the
  silent swallow).

## Maintenance notes

- After this plan lands, any new financial calculation function should
  follow the pattern: specific exception types, `as e`, `logger.warning`
  with context, then fallback return. Do not add new bare `except:` blocks.
- A reviewer should verify that the specific exception types chosen are
  correct for each calculation. If a calculation can raise an exception not
  listed, the catch will miss it and it will propagate. That is preferable
  to silent swallowing, but the types should be as complete as practical.
- Follow-up deferred: adding unit tests that trigger each error path and
  assert the warning is logged. This is plan 008/009 territory (test
  coverage for live_collector and risk/PnL).
