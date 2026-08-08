# Plan 016: Setup CI/CD pipeline + pre-commit hooks

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- .github/workflows/ci.yml .pre-commit-config.yaml`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans/015-setup-project-tooling.md (pyproject.toml and tool config must exist first)
- **Category**: dx
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The project has no CI pipeline and no pre-commit hooks. Every lint, typecheck,
and test run is manual. This means broken code can land without anyone noticing
until a runtime failure. A CI pipeline that runs ruff, mypy, and pytest on
every push/PR catches regressions automatically. Pre-commit hooks catch
whitespace, trailing newline, and lint issues before code even reaches a
commit. Together they enforce the quality bar defined in AGENTS.md without
relying on developer discipline.

## Current state

The repository has no `.github/` directory at all:

```
$ ls .github/workflows/
ls: .github/workflows/: No such file or directory
```

No `.pre-commit-config.yaml` exists at the project root:

```
$ ls .pre-commit-config.yaml
ls: .pre-commit-config.yaml: No such file or directory
```

The project commands (from AGENTS.md, lines 117-123) are:

```bash
# Testes
pytest tests/ -v

# Lint
ruff check src/ scripts/
mypy src/
```

Plan 015 creates `pyproject.toml` with ruff and mypy configuration. This plan
depends on that config existing so the CI jobs and pre-commit hooks can invoke
the tools with consistent settings.

The project uses Python 3.11+ (AGENTS.md line 44). The `.gitignore` already
covers standard Python artifacts (`.venv/`, `__pycache__/`, etc.).

Requirements include ruff and mypy as dev dependencies (requirements.txt
lines 40-41):

```
ruff>=0.5
mypy>=1.10
```

## Commands you will need

| Purpose          | Command                                      | Expected on success |
|-----------------|----------------------------------------------|---------------------|
| Lint            | `ruff check src/ scripts/`                   | exit 0              |
| Typecheck       | `mypy src/`                                  | exit 0, no errors   |
| Tests           | `pytest tests/ -v`                           | all pass            |
| YAML lint       | `yamllint .github/workflows/ci.yml`          | exit 0 (if installed) |
| Pre-commit run  | `pre-commit run --all-files`                 | exit 0 (if installed) |

## Scope

**In scope** (the only files you should create or modify):
- `.github/workflows/ci.yml` (create)
- `.pre-commit-config.yaml` (create)

**Out of scope** (do NOT touch, even though they look related):
- All Python source files in `src/` and `scripts/`
- `pyproject.toml` (owned by plan 015)
- `requirements.txt`
- Any test files

## Git workflow

- Branch: `advisor/016-setup-ci-cd-pipeline`
- Commit per step or per logical unit; message style: conventional commits
  (e.g. `ci: add GitHub Actions workflow for lint, typecheck, test`)
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Create the GitHub Actions CI workflow

Create the file `.github/workflows/ci.yml` with the following content. This
workflow runs on every push to `main` and every pull request targeting `main`.
It has three jobs that run in parallel: `lint`, `typecheck`, and `test`.

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff
      - run: ruff check src/ scripts/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install mypy pandas numpy pyarrow
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

Key design decisions:
- Python 3.11 is the minimum supported version per AGENTS.md line 44.
- The `typecheck` job installs only the packages mypy needs to resolve stubs
  (pandas, numpy, pyarrow). Installing the full requirements.txt there would
  be slower. If mypy reports missing stubs, add those packages to the install
  line.
- The `test` job installs the full `requirements.txt` because tests import
  from all modules.
- Jobs run in parallel to minimize total CI time.

**Verify**: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0 (valid YAML). If `yamllint` is installed, also run `yamllint .github/workflows/ci.yml` and confirm exit 0.

### Step 2: Create the pre-commit configuration

Create the file `.pre-commit-config.yaml` at the project root with the
following content:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--check]
        files: ^(src|scripts)/.*\.py$

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Key design decisions:
- The ruff hook uses `--check` (non-fixing mode) so it reports issues without
  modifying files. This matches the CI behavior where `ruff check` is
  non-fixing.
- The ruff hook is scoped to `src/` and `scripts/` via the `files` regex,
  matching the project's lint command from AGENTS.md line 122.
- `check-yaml` validates YAML files (including the CI workflow from step 1).
- `check-added-large-files` prevents accidental commits of large data files
  (the project stores Parquet data locally).
- `trailing-whitespace` and `end-of-file-fixer` enforce basic formatting.
- The rev pins match the minimum versions in requirements.txt (ruff>=0.5).
  If a newer version is available, the executor may update the rev, but must
  verify `pre-commit run --all-files` still passes.

**Verify**: `python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"` exits 0 (valid YAML).

### Step 3: Verify pre-commit hooks run (if pre-commit is installed)

If `pre-commit` is installed in the environment:

```bash
pre-commit install
pre-commit run --all-files
```

If pre-commit is not installed, skip this step and note it in the done
criteria. The CI workflow (step 1) is the primary enforcement mechanism;
pre-commit is a local convenience layer.

**Verify**: If pre-commit is installed, `pre-commit run --all-files` exits 0. If not installed, skip and note it.

## Test plan

No new tests to write. This plan creates infrastructure files (YAML), not
Python code. Verification is structural:

- The CI workflow YAML parses without errors.
- The pre-commit config YAML parses without errors.
- The ruff hook in pre-commit config targets the same paths as the project's
  lint command (`src/ scripts/`).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `.github/workflows/ci.yml` exists and is valid YAML (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0)
- [ ] `.pre-commit-config.yaml` exists and is valid YAML (`python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"` exits 0)
- [ ] The CI workflow has three jobs: `lint`, `typecheck`, `test`
- [ ] The CI workflow triggers on push and PR to `main`
- [ ] The pre-commit config includes ruff check, trailing-whitespace, and end-of-file-fixer hooks
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The file `pyproject.toml` does not exist (plan 015 has not been executed
  yet). The CI workflow and pre-commit hooks depend on ruff/mypy config
  being in `pyproject.toml`.
- The YAML files fail to parse after a reasonable fix attempt.
- You discover that `requirements.txt` does not exist or is empty (the
  `test` job in the CI workflow installs from it).
- The project's lint or typecheck commands (`ruff check src/ scripts/`,
  `mypy src/`) do not pass locally, which means the CI workflow would fail
  on every run. Report this so the underlying issues can be fixed first.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- If plan 015 adds or changes ruff/mypy config in `pyproject.toml`, the CI
  jobs and pre-commit hooks will automatically pick up the new config
  (they invoke the tools without overriding settings).
- If new Python source directories are added beyond `src/` and `scripts/`,
  update the `files` regex in `.pre-commit-config.yaml` and the `ruff check`
  command in the CI workflow.
- The `typecheck` job installs a minimal set of packages for mypy stub
  resolution. If mypy reports "Cannot find implementation or library stub
  for module named X", add X to the `pip install` line in the `typecheck`
  job.
- Pre-commit hook versions (`rev`) should be updated periodically. Run
  `pre-commit autoupdate` and verify `pre-commit run --all-files` still
  passes before committing the update.
- A reviewer should verify the CI workflow YAML is syntactically correct
  and that the job names match the commands in AGENTS.md.
