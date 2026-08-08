# Plan 018: Fix stale docs (README, ROADMAP, CHECKUP alignment)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- README.md ROADMAP.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: docs
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The project's documentation is internally contradictory. README.md says
Fase 1 is "a iniciar" but CHECKUP.md says Fase 1 and 2 are concluded.
ROADMAP.md says Fase 1 is "A INICIAR" with all checkboxes unchecked, but
the code for Fase 1 and 2 is already implemented and tested (52 tests
passing). README.md line 76 says "(quando requirements.txt existir)" but
requirements.txt exists and has 43 lines. These contradictions confuse
new contributors and agents: they cannot tell what is done and what is
not. Aligning the docs with the actual state (CHECKUP.md as source of
truth) makes the project status unambiguous.

## Current state

**CHECKUP.md is the source of truth.** It was last updated 2026-07-15 and
accurately reflects the codebase. Key facts from CHECKUP.md:

- Line 4: "Fase atual: Fase 1 e 2 concluidas, Fase 2.5 (pesquisa de
  estrategias) concluida"
- Line 18: "Fase 1: Pipeline de Dados Historicos (CONCLUIDA)"
- Line 31: "Fase 2: Matriz de Correlacao e Grafo (CONCLUIDA)"
- Lines 59-77: Fase 2.5 (pesquisa de estrategias) is CONCLUIDA with 9
  manuais and 4.208 lines of documentation.
- Lines 81-91: Fase 3 is the next step (backtest), with 10 sub-tasks
  listed.
- Lines 93-98: Fase 4 (paper trading) is planned.
- Lines 100-104: Fase 5 (real trading) is planned.
- Line 45-47: 52 tests passing, covering ParquetStore, Universe, Returns,
  Correlation, Graph, GraphVisualizer.

**README.md is stale.** Three specific problems:

1. Line 76 says "(quando requirements.txt existir)" but it exists:
   ```
   # Instalar dependencias (quando requirements.txt existir)
   pip install -r requirements.txt
   ```

2. Lines 62-65 say Fase 1 is "a iniciar" and Fase 2 is "planejada", but
   CHECKUP.md says both are CONCLUIDA:
   ```
   - **Fase 0**: Pesquisa e documentacao (concluida)
   - **Fase 1**: Pipeline de dados historicos (a iniciar)
   - **Fase 2**: Matriz de correlacao e grafo (planejada)
   - **Fase 3**: Backtest de estrategia (planejada)
   - **Fase 4**: Bot em paper trading (planejada)
   - **Fase 5**: Bot em real (planejada)
   ```

3. Line 79 says "(quando script existir)" but the download script exists
   and works:
   ```
   # Baixar dados historicos (quando script existir)
   python scripts/download_historical.py --symbols BTCUSDT,ETHUSDT --start 2023-01-01
   ```

**ROADMAP.md is stale.** Three specific problems:

1. Line 13 says "Fase 1: Pipeline de Dados Historicos (A INICIAR)" but
   CHECKUP.md says CONCLUIDA:
   ```
   ## Fase 1: Pipeline de Dados Historicos (A INICIAR)
   ```

2. Lines 17-33: All Fase 1 checkboxes are unchecked `[ ]`, but the code
   is implemented. CHECKUP.md lines 18-29 show all items as `[x]`.

3. Lines 37-62: Fase 2 has no status label and all checkboxes are
   unchecked `[ ]`, but CHECKUP.md says CONCLUIDA. The ROADMAP header
   just says:
   ```
   ## Fase 2: Matriz de Correlacao e Grafo
   ```

4. Lines 64-86: Fase 3 checkboxes are all unchecked `[ ]`, but
   CHECKUP.md lines 81-91 show that strategy modules are partially
   implemented (src/strategy/base.py, mean_reversion.py, momentum.py,
   stat_arb.py, regime_filter.py, meta.py all exist in the codebase).
   The backtest engine (src/backtest/engine.py) and walk_forward.py
   also exist. Scripts/run_backtest.py is functional.

5. There is no mention of Fase 2.5 (pesquisa de estrategias) in
   ROADMAP.md at all, even though CHECKUP.md documents it as
   CONCLUIDA with 4.208 lines of strategy documentation.

**Repo conventions (AGENTS.md):**
- No em-dash in any file (line 9). Use ":" or "." or "," instead.
- Documentation is in Portuguese (pt-BR) based on existing docs.

## Commands you will need

| Purpose          | Command                                              | Expected on success |
|-----------------|------------------------------------------------------|---------------------|
| Verify no em-dash | `grep -rn $'\xe2\x80\x94' README.md ROADMAP.md`    | no matches          |
| Verify file changed | `git diff --stat README.md ROADMAP.md`           | both files listed   |

## Scope

**In scope** (the only files you should modify):
- `README.md`
- `ROADMAP.md`

**Out of scope** (do NOT touch):
- `CHECKUP.md` (it is the source of truth, already accurate)
- `PRODUCT.md` (owned by plan 019, product direction reconciliation)
- `DESIGN.md` (owned by plan 019)
- `AGENTS.md`
- All source code and test files

## Git workflow

- Branch: `advisor/018-fix-stale-docs`
- Commit per step or per logical unit; message style: conventional commits
  (e.g. `docs: align README and ROADMAP with CHECKUP status`)
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix README.md line 76 (remove stale parenthetical)

README.md line 76 currently reads:

```
# Instalar dependencias (quando requirements.txt existir)
pip install -r requirements.txt
```

Change it to:

```
# Instalar dependencias
pip install -r requirements.txt
```

The parenthetical "(quando requirements.txt existir)" is false:
requirements.txt exists with 43 lines and is the active dependency file.

**Verify**: `grep -n "quando requirements.txt existir" README.md` returns no matches.

### Step 2: Fix README.md line 79 (remove stale parenthetical)

README.md line 79 currently reads:

```
# Baixar dados historicos (quando script existir)
python scripts/download_historical.py --symbols BTCUSDT,ETHUSDT --start 2023-01-01
```

Change it to:

```
# Baixar dados historicos
python scripts/download_historical.py --symbols BTCUSDT,ETHUSDT --start 2023-01-01
```

The parenthetical "(quando script existir)" is false: the download script
exists (275 lines) and is functional per CHECKUP.md line 24.

**Verify**: `grep -n "quando script existir" README.md` returns no matches.

### Step 3: Fix README.md lines 62-65 (status section)

README.md lines 58-67 currently read:

```
## Status atual

Veja `CHECKUP.md` para o estado detalhado. Resumo:

- **Fase 0**: Pesquisa e documentacao (concluida)
- **Fase 1**: Pipeline de dados historicos (a iniciar)
- **Fase 2**: Matriz de correlacao e grafo (planejada)
- **Fase 3**: Backtest de estrategia (planejada)
- **Fase 4**: Bot em paper trading (planejada)
- **Fase 5**: Bot em real (planejada)
```

Change it to match CHECKUP.md (the source of truth):

```
## Status atual

Veja `CHECKUP.md` para o estado detalhado. Resumo:

- **Fase 0**: Pesquisa e documentacao (concluida)
- **Fase 1**: Pipeline de dados historicos (concluida)
- **Fase 2**: Matriz de correlacao e grafo (concluida)
- **Fase 2.5**: Pesquisa de estrategias (concluida)
- **Fase 3**: Backtest de estrategia (em andamento)
- **Fase 4**: Bot em paper trading (planejada)
- **Fase 5**: Bot em real (planejada)
```

Key changes:
- Fase 1: "a iniciar" -> "concluida"
- Fase 2: "planejada" -> "concluida"
- Added Fase 2.5: "Pesquisa de estrategias (concluida)" (matches CHECKUP.md
  line 59)
- Fase 3: "planejada" -> "em andamento" (CHECKUP.md lines 81-91 show
  strategy and backtest modules are implemented; scripts/run_backtest.py
  is functional)

**Verify**: `grep -n "a iniciar" README.md` returns no matches. `grep -n "Fase 2.5" README.md` returns at least one match.

### Step 4: Fix ROADMAP.md Fase 1 header and checkboxes

ROADMAP.md line 13 currently reads:

```
## Fase 1: Pipeline de Dados Historicos (A INICIAR)
```

Change it to:

```
## Fase 1: Pipeline de Dados Historicos (CONCLUIDA)
```

Then update all Fase 1 checkboxes from `[ ]` to `[x]`. The checkboxes are
on lines 17-33. Based on CHECKUP.md lines 18-29, all items are done:

```
- [x] `requirements.txt` com dependencias base (ccxt, pandas, pyarrow, numpy)
- [x] `scripts/download_historical.py`: baixar klines da Binance Vision
  - Input: lista de symbols, timeframe, data inicio/fim
  - Output: arquivos Parquet em `data/parquet/<symbol>/<timeframe>/`
  - Suporte a spot e futures (USD-M)
  - Incremental: nao re-baixar o que ja existe
- [x] `scripts/download_binance_vision.py`: baixar CSVs direto do data.binance.vision
  - Para tick-by-tick ou klines de 1s (nao disponiveis via API REST)
  - URL pattern: `https://data.binance.vision/data/spot/monthly/klines/<SYMBOL>/<INTERVAL>/<SYMBOL>-<INTERVAL>-<YEAR>-<MONTH>.zip`
- [x] `src/data/parquet_store.py`: modulo para leitura/escrita de Parquet
  - Schema: timestamp, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_base, taker_buy_quote
  - Particionamento por symbol + timeframe
- [x] `src/data/universe.py`: definir universo de ativos tradaveis
  - Top 30-50 pares USDT por volume
  - Filtro de liquidez (volume medio diario > $10M)
  - Filtro de historico (listados antes de 2022)
- [x] Validacao: baixar 5 symbols, verificar integridade, conferir com API
```

Note: `scripts/download_binance_vision.py` may not exist as a separate
file (the download logic is in `scripts/download_historical.py` with a
`--source vision` flag). If it does not exist as a separate script, keep
the checkbox checked but add a note: "(integrado em
`download_historical.py` com flag `--source vision`)". Check the
filesystem first:

```bash
ls scripts/download_binance_vision.py
```

If the file does not exist, append the note to that checkbox line.

**Verify**: `grep -n "A INICIAR" ROADMAP.md` returns no matches in Fase 1. `grep -c "\[ \]" ROADMAP.md` (counted in Fase 1 section only) returns 0.

### Step 5: Fix ROADMAP.md Fase 2 header and checkboxes

ROADMAP.md line 37 currently reads:

```
## Fase 2: Matriz de Correlacao e Grafo
```

Change it to:

```
## Fase 2: Matriz de Correlacao e Grafo (CONCLUIDA)
```

Then update all Fase 2 checkboxes from `[ ]` to `[x]`. The checkboxes are
on lines 41-60. Based on CHECKUP.md lines 31-42, all items are done:

```
- [x] `src/analysis/returns.py`: calcular log-returns diarios e intradiarios
  - Alinhamento de timestamps entre ativos
  - Tratamento de gaps e outliers
- [x] `src/analysis/correlation.py`: matriz de correlacao
  - Pearson, Spearman, Kendall
  - Janela deslizante (rolling correlation)
  - Threshold para criar arestas no grafo (|corr| > 0.5)
- [x] `src/analysis/graph.py`: construcao do grafo
  - NetworkX: nodes = ativos, edges = correlacao
  - Deteccao de comunidades (Louvain, Greedy Modularity)
  - Metricas: degree centrality, betweenness, clustering coefficient
  - Evolucao temporal: um grafo por mes/semana
- [x] `src/viz/graph_visualizer.py`: visualizacao interativa
  - Pyvis: HTML interativo com fisica
  - Cor das arestas por sinal da correlacao (verde = positiva, vermelho = negativa)
  - Tamanho dos nodes por volume ou degree
  - Filtro de threshold ajustavel
- [x] `scripts/build_correlation_graph.py`: pipeline completo
  - Ler Parquet -> calcular returns -> matriz -> grafo -> HTML
- [x] Notebook exploratorio: `notebooks/correlation_exploration.ipynb`
```

Note: The notebook may not exist. If it does not, keep the checkbox checked
only if CHECKUP.md confirms it. CHECKUP.md does not mention a notebook, so
if the file does not exist, leave that checkbox as `[ ]` and add a note:
"(nao criado, analise feita via scripts)". Check the filesystem first:

```bash
ls notebooks/correlation_exploration.ipynb
```

**Verify**: `grep -n "Fase 2: Matriz" ROADMAP.md` shows "(CONCLUIDA)" in the header.

### Step 6: Add Fase 2.5 to ROADMAP.md and update Fase 3 checkboxes

After the Fase 2 section (after line 62, the "Criterio de saida" line),
insert a new Fase 2.5 section before Fase 3. This matches CHECKUP.md
lines 59-77:

```
## Fase 2.5: Pesquisa de Estrategias (CONCLUIDA)

- [x] Pesquisa profunda sobre: day trade, price action, estatistica aplicada, entropia, order flow, microestrutura, volume profile, momentum, VWAP, funding rate, liquidity sweep, ICT/SMC, Hurst exponent, cointegracao
- [x] 9 manuais de estrategias criados em `docs/strategies/`
- [x] Documento master `docs/STRATEGIES.md` com comparativo, mapa de regime x estrategia, arquitetura de combinacao
- [x] Total: 4.208 linhas de documentacao de estrategias
```

Then update Fase 3. The Fase 3 header (line 64) currently reads:

```
## Fase 3: Backtest de Estrategia
```

Change it to:

```
## Fase 3: Backtest de Estrategia (EM ANDAMENTO)
```

Then update the Fase 3 checkboxes based on what is actually implemented.
Check the filesystem for each file:

```bash
ls src/strategy/base.py src/strategy/mean_reversion.py src/backtest/engine.py src/backtest/walk_forward.py scripts/run_backtest.py
```

Based on the codebase (scripts/run_backtest.py imports from
`src.strategy.momentum`, `src.strategy.mean_reversion`,
`src.strategy.stat_arb`, `src.strategy.regime_filter`, `src.strategy.meta`,
and `src.backtest.engine`), the following are implemented:

```
- [x] Definir estrategia(s):
  - Mean reversion intra-cluster (ativos que se descolam do cluster voltam)
  - Momentum inter-cluster (clusters que se fortalecem continuam)
  - Arbitragem estatistica de pares (cointegracao)
- [x] `src/strategy/base.py`: interface de estrategia
  - `generate_signals(data) -> signals`
  - `get_positions(signals) -> target_weights`
- [x] `src/strategy/mean_reversion.py`: implementacao
- [x] `src/backtest/engine.py`: backtest com VectorBT
  - Metricas: Sharpe, Sortino, max drawdown, win rate, profit factor
  - Custos: 0.1% taker, 0.075% maker (Binance)
  - Slippage model
- [ ] `src/backtest/walk_forward.py`: walk-forward analysis
  - Treinar em janela, testar fora da amostra
  - Evitar look-ahead bias
- [x] `scripts/run_backtest.py`: executar backtest completo
- [ ] Relatorio: `docs/research/backtest-results.md`
```

Note: `src/backtest/walk_forward.py` may exist but not be fully functional.
Check the filesystem and the code. If it exists but is a stub or not
integrated, leave it as `[ ]`. If it does not exist, leave `[ ]`. The
report file `docs/research/backtest-results.md` likely does not exist yet;
leave it as `[ ]`.

Also note: `src/strategy/momentum.py`, `src/strategy/stat_arb.py`,
`src/strategy/regime_filter.py`, and `src/strategy/meta.py` are not
listed in the original ROADMAP checkboxes but are implemented. Add them
as additional checked items under the strategy section:

```
- [x] `src/strategy/momentum.py`: implementacao (STRAT-06)
- [x] `src/strategy/stat_arb.py`: implementacao (STRAT-03)
- [x] `src/strategy/regime_filter.py`: meta-filtro (STRAT-04)
- [x] `src/strategy/meta.py`: combinacao de estrategias
```

**Verify**: `grep -n "Fase 2.5" ROADMAP.md` returns at least one match. `grep -n "EM ANDAMENTO" ROADMAP.md` returns at least one match in Fase 3.

### Step 7: Verify no em-dash in modified files

Run a byte-level search for the em-dash character (UTF-8: `\xe2\x80\x94`)
in both modified files:

```bash
grep -rn $'\xe2\x80\x94' README.md ROADMAP.md
```

This should return no matches. If any em-dash is found, replace it with
":" or "." or "," per AGENTS.md line 9.

**Verify**: `grep -rn $'\xe2\x80\x94' README.md ROADMAP.md` returns no matches.

## Test plan

No tests to write. This plan modifies documentation only. Verification is
visual and grep-based:

- No stale parentheticals remain in README.md.
- ROADMAP.md Fase 1 and 2 are marked CONCLUIDA with all checkboxes checked.
- ROADMAP.md includes Fase 2.5.
- ROADMAP.md Fase 3 is marked EM ANDAMENTO with checkboxes reflecting
  actual implementation.
- No em-dash characters in either file.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -n "quando requirements.txt existir" README.md` returns no matches
- [ ] `grep -n "quando script existir" README.md` returns no matches
- [ ] `grep -n "a iniciar" README.md` returns no matches
- [ ] `grep -n "Fase 2.5" README.md` returns at least one match
- [ ] `grep -n "A INICIAR" ROADMAP.md` returns no matches
- [ ] `grep -n "Fase 2.5" ROADMAP.md` returns at least one match
- [ ] `grep -n "EM ANDAMENTO" ROADMAP.md` returns at least one match
- [ ] `grep -rn $'\xe2\x80\x94' README.md ROADMAP.md` returns no matches
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The content at the line numbers in "Current state" doesn't match the
  excerpts (the docs have been updated since this plan was written).
- A file referenced in the checkboxes (e.g. `src/strategy/base.py`) does
  not exist when you expected it to, or exists when you expected it not
  to. Report the discrepancy so the checkbox state can be corrected.
- You discover that CHECKUP.md itself is stale or inaccurate (it is the
  source of truth for this plan). If CHECKUP.md does not match the
  codebase, stop and report.
- The fix appears to require touching an out-of-scope file (e.g.
  PRODUCT.md, DESIGN.md, AGENTS.md).

## Maintenance notes

For the human/agent who owns this code after the change lands:

- CHECKUP.md is the source of truth for project status. When updating
  status, update CHECKUP.md first, then propagate to README.md and
  ROADMAP.md.
- When a new phase is completed, update three places: CHECKUP.md (detailed),
  ROADMAP.md (checkboxes + header), and README.md (one-line summary in
  Status section).
- Fase 2.5 was not in the original ROADMAP. It was added as an interim
  phase for strategy research. Future interim phases should follow the
  same pattern (add to ROADMAP with a 2.x number).
- A reviewer should verify that the ROADMAP checkboxes accurately reflect
  the filesystem state (files exist/don't exist as claimed).
- Plan 019 (product direction reconciliation) may further modify README.md
  and ROADMAP.md. Execute 018 before 019 to establish a consistent
  baseline.
