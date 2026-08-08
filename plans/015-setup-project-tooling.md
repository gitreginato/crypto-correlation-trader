# Plan 015: Setup project tooling (pyproject.toml, ruff, mypy, fix deps)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- pyproject.toml requirements.txt`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The project has no `pyproject.toml`, no ruff config, and no mypy config. Ruff and mypy run with default settings, which do not match the project conventions (120 char line length, Python 3.11 target, strict typing). Additionally, `requirements.txt` has a duplicate `statsmodels` entry (line 16: `>=0.14` and line 42: `==0.14.6`), which causes pip to install the pinned version while the unpinned version creates ambiguity. Creating `pyproject.toml` with proper `[tool.ruff]`, `[tool.mypy]`, and `[tool.pytest.ini_options]` sections standardizes the tooling, makes linting and type checking consistent across developers, and fixes the dependency conflict.

## Current state

The relevant files, each with one line on its role:

- `requirements.txt` (43 lines) : the only dependency file. No `pyproject.toml` exists.
- No `ruff.toml`, no `mypy.ini`, no `setup.cfg`, no `pyproject.toml` in the project root.

### requirements.txt contents (full file)

```
# Core data
pandas>=2.2
numpy>=2.0
pyarrow>=17.0

# Exchange data
ccxt>=4.5
python-binance>=1.0.37
aiohttp>=3.9
websockets>=12.0
requests>=2.32

# Analysis
networkx>=3.3
scipy>=1.13
statsmodels>=0.14          # line 16: unpinned
scikit-learn>=1.5
hmmlearn>=0.3
ruptures>=1.5

# Visualization
pyvis>=0.3
plotly>=5.22
matplotlib>=3.9
seaborn>=0.13

# Backtest
vectorbt>=0.26

# Config & utils
pydantic>=2.7
pyyaml>=6.0
python-dotenv>=1.0

# Testing
pytest>=8.2
pytest-asyncio>=0.23

# Lint (dev only)
ruff>=0.5
mypy>=1.10
statsmodels==0.14.6        # line 42: DUPLICATE, pinned
nolds==0.6.3
```

The duplicate: `statsmodels>=0.14` on line 16 and `statsmodels==0.14.6` on line 42. The pinned version on line 42 wins (pip processes top-to-bottom, last one wins for the same package). This is confusing and should be a single entry.

### No tool config exists

Run these commands to confirm:
```bash
ls pyproject.toml ruff.toml mypy.ini setup.cfg .ruff.toml 2>&1
```

All should return "No such file or directory". If any config file exists, STOP and report (the project may have been partially configured since this plan was written).

### Existing code conventions (from AGENTS.md)

- Python 3.11+ (type hints required)
- Indentation: 4 spaces
- Line max: 120 characters
- Naming: `snake_case` for functions/variables, `PascalCase` for classes
- Functions: max 30 lines (ideal < 15)

### Project metadata

- Name: crypto-correl-bot
- Python: 3.11+
- Description: Bot de trading em criptomoedas baseado em grafos de correlacao. Dados da Binance (Vision + API + WebSocket).
- Dependencies: as listed in `requirements.txt` (minus the duplicate)

### Repo conventions that apply

- No em-dash (the character `:`). Use `:`, `.`, or `,` instead.
- No hardcoded API keys or secrets.
- `AGENTS.md` specifies: `ruff check src/ scripts/` and `mypy src/` as the lint commands.

## Commands you will need

| Purpose          | Command                              | Expected on success |
|------------------|--------------------------------------|---------------------|
| Lint             | `ruff check src/ scripts/`           | exit 0              |
| Type check       | `mypy src/`                          | exit 0 (or same as before) |
| Tests            | `pytest tests/ -v`                   | all pass            |

## Scope

**In scope** (the only files you should modify or create):
- `pyproject.toml` (create)
- `requirements.txt` (fix duplicate statsmodels entry)

**Out of scope** (do NOT touch):
- All Python source files (`src/`, `scripts/`, `tests/`).
- Any other config files (`.gitignore`, `AGENTS.md`, etc.).
- `requirements-dev.txt` or similar (not creating new files beyond `pyproject.toml`).

## Git workflow

- Branch: `advisor/015-project-tooling`
- Single commit. Message: `chore: add pyproject.toml with ruff/mypy/pytest config, fix duplicate statsmodels`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix requirements.txt duplicate

In `requirements.txt`, remove the duplicate `statsmodels` entry on line 42. Keep the pinned version on line 16 (change `>=0.14` to `==0.14.6`) OR keep the unpinned version and remove line 42.

Recommended: keep the pinned version for reproducibility. Change line 16 from:
```
statsmodels>=0.14
```
to:
```
statsmodels==0.14.6
```

Then remove line 42 (`statsmodels==0.14.6`).

The `nolds==0.6.3` entry on line 43 should remain (it is a separate package, not a duplicate).

After the fix, `grep -c "statsmodels" requirements.txt` should return 1.

**Verify**: `grep -c "statsmodels" requirements.txt` returns 1. `pip install -r requirements.txt --dry-run` exits 0 (if pip supports `--dry-run`; otherwise skip this check).

### Step 2: Create pyproject.toml

Create `pyproject.toml` in the project root with the following content:

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "crypto-correl-bot"
version = "0.1.0"
description = "Bot de trading em criptomoedas baseado em grafos de correlacao. Dados da Binance (Vision + API + WebSocket)."
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "crypto-correl-bot" }]

[project.optional-dependencies]
dev = [
    "ruff>=0.5",
    "mypy>=1.10",
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.ruff]
line-length = 120
target-version = "py311"
src = ["src", "scripts"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes (unused imports, etc.)
    "I",    # isort (import sorting)
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by formatter, not linter)
]

[tool.ruff.lint.isort]
known-first-party = ["src"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
indent-width = 4

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
show_error_codes = true
namespace_packages = true
explicit_package_bases = true

[[tool.mypy.overrides]]
module = [
    "ccxt.*",
    "binance.*",
    "hmmlearn.*",
    "ruptures.*",
    "nolds.*",
    "arch.*",
    "pyvis.*",
    "vectorbt.*",
    "plotly.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

IMPORTANT notes about this config:

1. The `[tool.ruff.lint]` section selects a reasonable set of rules. The `E501` (line too long) rule is ignored because the formatter handles line length. If `ruff check src/ scripts/` reports many new errors after this config is applied (because the codebase was not linted with these rules before), you may need to add more rules to `ignore` temporarily. However, the goal is to have the config in place, not to fix all lint errors in this plan. If `ruff check src/ scripts/` exits non-zero, see the STOP condition below.

2. The `[tool.mypy]` section uses `strict = true`. The existing codebase may not pass strict mypy (there are likely `Any` types, missing type hints, etc.). If `mypy src/` reports many new errors, change `strict = true` to `strict = false` and keep the individual `warn_*` and `disallow_*` flags. The goal is to have the config in place with strict settings as a target, not to fix all type errors in this plan. If `mypy src/` exits non-zero with many errors, see the STOP condition below.

3. The `[[tool.mypy.overrides]]` section ignores missing imports for third-party packages that don't ship type stubs. Add or remove packages as needed based on the actual mypy output.

4. The `[tool.setuptools.packages.find]` section tells setuptools where to find the `src` package. This makes `pip install -e .` work if the operator wants editable installs in the future.

5. The `[project.optional-dependencies]` section lists dev tools. The main dependencies remain in `requirements.txt` for now. A future plan can migrate them to `[project.dependencies]` in `pyproject.toml`.

**Verify**: `python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('OK')"` prints `OK`, exit 0 (valid TOML). `ruff check src/ scripts/ --show-settings` exits 0 (ruff reads the config). `mypy src/ --help` exits 0.

### Step 3: Verify ruff works with new config

Run:
```bash
ruff check src/ scripts/
```

If this exits 0, great. If it exits non-zero with errors:

1. Check if the errors are pre-existing (would have been caught by default ruff) or new (introduced by the config's rule selection).
2. If the errors are new (from rules like `B`, `C4`, `SIM`, `UP`), add those rules to the `ignore` list in `[tool.ruff.lint]`. For example:
```toml
ignore = [
    "E501",
    "B008",  # function call in default argument
    "SIM102", # nested if can be combined
]
```
3. Re-run `ruff check src/ scripts/` and confirm it exits 0.
4. If you need to add more than 10 rules to `ignore`, STOP and report. The config may be too strict for the current codebase state.

IMPORTANT: Do NOT fix lint errors in source files. This plan only creates the config. Fixing lint errors is out of scope (and would modify out-of-scope files).

**Verify**: `ruff check src/ scripts/` exits 0.

### Step 4: Verify mypy works with new config

Run:
```bash
mypy src/
```

If this exits 0, great. If it exits non-zero with errors:

1. Check if the errors are pre-existing or new (from `strict = true`).
2. If there are many errors (more than 20), change `strict = true` to `strict = false` in `[tool.mypy]`:
```toml
[tool.mypy]
python_version = "3.11"
strict = false
```
3. Keep the individual `warn_*` and `disallow_*` flags as-is. These provide useful warnings without being as strict as `strict = true`.
4. Re-run `mypy src/` and check the error count.
5. If there are still many errors, add `ignore_errors = true` to a `[[tool.mypy.overrides]]` section for specific modules that have known type issues. But prefer reducing strictness globally over ignoring modules.
6. If `mypy src/` still exits non-zero after reducing strictness, STOP and report the error count and a sample of errors.

IMPORTANT: Do NOT fix type errors in source files. This plan only creates the config. Fixing type errors is out of scope (and would modify out-of-scope files).

**Verify**: `mypy src/` exits 0 (or exits with the same error count as before the config was added, if the codebase already had mypy errors).

### Step 5: Verify pytest works with new config

Run:
```bash
pytest tests/ -v
```

The `[tool.pytest.ini_options]` section adds `addopts = "-v --tb=short"`. This should not break any existing tests. If tests fail, check if the `addopts` caused the issue (e.g. if a test relies on specific output format). If so, remove `addopts` from the config.

**Verify**: `pytest tests/ -v` exits 0, all tests pass.

### Step 6: Final verification

Run all three commands:
```bash
ruff check src/ scripts/
mypy src/
pytest tests/ -v
```

**Verify**: All three exit 0 (or mypy exits with the same error count as before).

## Test plan

No new tests are written in this plan. The existing test suite must continue to pass with the new pytest config.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pyproject.toml` exists in the project root
- [ ] `python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('OK')"` prints `OK`, exit 0 (valid TOML)
- [ ] `grep -c "statsmodels" requirements.txt` returns 1 (duplicate fixed)
- [ ] `ruff check src/ scripts/` exits 0
- [ ] `mypy src/` exits 0 (or same error count as before)
- [ ] `pytest tests/ -v` exits 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts. Run `grep -n "statsmodels" requirements.txt` and confirm it returns lines 16 and 42. If not, STOP.
- A `pyproject.toml`, `ruff.toml`, `mypy.ini`, or `setup.cfg` already exists in the project root. STOP and report (the project may have been partially configured).
- `ruff check src/ scripts/` reports more than 50 new errors after applying the config, and adding rules to `ignore` doesn't bring it below 50. STOP and report. The config may need to be less strict.
- `mypy src/` reports more than 50 errors after setting `strict = false`. STOP and report the error count and a sample.
- `pytest tests/ -v` fails after adding `[tool.pytest.ini_options]`. STOP and report which test failed and why.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file (e.g. you need to fix a lint error in a source file).

## Maintenance notes

- After this plan, `pyproject.toml` is the single source of truth for tool config. Future changes to ruff/mypy/pytest settings should go in `pyproject.toml`, not in separate config files.
- The `[tool.mypy]` section may start with `strict = false` if the codebase has many type errors. The goal is to eventually set `strict = true` once type errors are fixed (plan 020 addresses this).
- The `[project.optional-dependencies]` dev section lists ruff, mypy, pytest. A future plan can migrate all dependencies from `requirements.txt` to `[project.dependencies]` in `pyproject.toml`, making `requirements.txt` generated/optional.
- The `[[tool.mypy.overrides]]` section ignores missing imports for packages without type stubs. If a new third-party package is added that lacks stubs, add it to the override list.
- Plan 016 (CI/CD) depends on this plan: the CI pipeline will use the ruff and mypy configs from `pyproject.toml`.
- A reviewer should scrutinize: (1) that the ruff rule selection is reasonable (not too strict, not too lenient), (2) that the mypy strictness level matches the current codebase state, and (3) that the duplicate `statsmodels` entry is truly fixed (only one entry remains).
