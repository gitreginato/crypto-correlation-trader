# Plan 019: Reconcile product direction (PRODUCT.md vs README vs ROADMAP)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report, do not improvise. When done, update the status row for this plan
> in `plans/README.md`, unless a reviewer dispatched you and told you they
> maintain the index.
>
> **STOP condition (read first)**: This plan requires a user decision at
> Step 2. Execute Step 1 (document current state), then STOP and present
> the options to the user. Do NOT proceed to Step 3 until the user has
> chosen an option. This is a design/spike plan, not a build-everything
> plan.
>
> **Drift check (run first)**: `git diff --stat pre-commit..HEAD -- PRODUCT.md README.md ROADMAP.md DESIGN.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none (but plan 018 should run first to establish a
  consistent baseline in README.md and ROADMAP.md)
- **Category**: direction
- **Planned at**: commit `pre-commit`, 2026-07-15

## Why this matters

The project has three contradictory product visions across its
documentation. PRODUCT.md describes a "Dashboard de analise de
microestrutura de mercado em tempo real" for day traders. DESIGN.md
describes an "Order Flow Terminal" dashboard design system. README.md
describes a "Bot de trading em criptomoedas baseado em grafos de
correlacao". ROADMAP.md focuses on the trading bot (Fases 0-5) but the
codebase has substantial dashboard infrastructure (scripts/analyze_live.py
at 1,945 lines, public/dashboard.html, 5 dashboard-related scripts). This
ambiguity means every contributor and agent has a different mental model
of what they are building. Reconciling the direction ensures all future
work aligns on a single, documented product vision.

## Current state

### Three contradictory product visions

**Vision 1: Trading Bot (README.md + ROADMAP.md + AGENTS.md)**

README.md line 3:
```
Bot de trading em criptomoedas baseado em grafos de correlacao entre ativos.
```

README.md lines 7-13 (objectives):
```
1. Coleta dados historicos de criptomoedas (Binance Vision + API publica)
2. Calcula matriz de correlacao entre ativos usando log-returns
3. Constroi grafo de correlacao (NetworkX + Pyvis) para visualizar e identificar clusters
4. Gera sinais de trading baseados em quebras e reconexoes de correlacao
5. Executa operacoes via API da Binance (paper trading primeiro, real depois)
```

AGENTS.md line 5:
```
Bot de trading em criptomoedas baseado em grafos de correlacao. Dados da Binance (Vision + API + WebSocket). Python 3.11+.
```

ROADMAP.md focuses entirely on the bot: Fase 0 (research), Fase 1 (data
pipeline), Fase 2 (correlation graph), Fase 3 (backtest), Fase 4 (paper
trading), Fase 5 (real trading), Fase 6 (improvements). No mention of a
dashboard product.

**Vision 2: Microstructure Dashboard (PRODUCT.md)**

PRODUCT.md line 13:
```
Dashboard de analise de microestrutura de mercado em tempo real que coleta dados de WebSocket (order book, trades) e REST (funding rate, open interest, long/short ratio, liquidations) da Binance. O produto existe para revelar "o jogo atras das velas": quem esta posicionando ordens, quem esta agredindo o book, onde estao os clusters de liquidez, e quando liquidacoes em cascata ocorrem. Sucesso = trader toma decisao mais informada em segundos.
```

PRODUCT.md line 9 (users):
```
Day traders e analistas de criptomoedas que precisam de visualizacao em tempo real de order flow, microestrutura de mercado e indicadores tecnicos.
```

PRODUCT.md makes no mention of correlation graphs, automated trading, or
backtesting.

**Vision 3: Order Flow Terminal (DESIGN.md)**

DESIGN.md frontmatter (lines 1-3):
```yaml
name: Order Flow Terminal
description: Dashboard profissional de microestrutura e order flow para traders de cripto.
```

DESIGN.md line 105:
```
A interface do Order Flow Terminal e inspirada em cockpits de trading profissional: Bloomberg Terminal, TradingView e dashboards institucionais.
```

DESIGN.md describes a full design system (colors, typography, components,
elevation) for the dashboard. It aligns with PRODUCT.md's vision but not
with README.md's bot vision.

### Codebase evidence: what actually exists

**Bot infrastructure (Vision 1):**
- `src/data/parquet_store.py`, `src/data/universe.py` (data pipeline)
- `src/analysis/returns.py`, `src/analysis/correlation.py`,
  `src/analysis/graph.py` (correlation analysis)
- `src/strategy/base.py`, `mean_reversion.py`, `momentum.py`,
  `stat_arb.py`, `regime_filter.py`, `meta.py` (trading strategies)
- `src/backtest/engine.py`, `walk_forward.py` (backtesting)
- `scripts/download_historical.py`, `scripts/build_correlation_graph.py`,
  `scripts/run_backtest.py` (bot pipeline scripts)
- 52 tests covering data, analysis, and graph modules

**Dashboard infrastructure (Vision 2/3):**
- `scripts/analyze_live.py` (1,945 lines): Real-time order flow dashboard
  generator. Collects WebSocket data, computes microstructure metrics
  (CVD, VWAP, VPIN, Kyle's Lambda, Amihud), technical indicators (RSI,
  MACD, Bollinger, SuperTrend), statistical tests (ADF, Hurst, GARCH),
  and generates an HTML dashboard.
- `scripts/statistical_analyzer.py` (788 lines): Advanced statistical
  analysis module for market microstructure.
- `scripts/generate_report.py` (433 lines): Markdown report generator
  from live analysis.
- `scripts/generate_scientific_report.py` (392 lines): Scientific report
  generator.
- `scripts/generate_correlation_dashboard.py`: Correlation dashboard
  generator.
- `scripts/generate_microstructure_dashboard.py`: Microstructure
  dashboard generator.
- `scripts/refresh_dashboard.py`: Dashboard refresh script.
- `scripts/analyze_correlations.py`, `scripts/analyze_microstructure.py`:
  Analysis scripts.
- `public/dashboard.html`: Generated dashboard output.
- `src/data/live_collector.py`: Real-time WebSocket data collector
  (order book, trades, funding, liquidations, open interest).

**Shared infrastructure (both visions):**
- `src/data/parquet_store.py` (used by bot backtests and dashboard data
  storage)
- `src/analysis/correlation.py` (used by bot graphs and dashboard
  cross-sectional analysis)
- Data download pipeline (used by both historical backtests and live
  dashboard)

### Summary of the contradiction

| Aspect        | README.md / ROADMAP.md | PRODUCT.md          | DESIGN.md             |
|---------------|------------------------|---------------------|-----------------------|
| Product       | Trading bot            | Microstructure dashboard | Order flow terminal |
| Users         | Bot operator           | Day traders         | Day traders           |
| Core feature  | Correlation graphs     | Order flow + microstructure | Visual design system |
| Trading       | Automated (paper/real) | Not mentioned       | Not mentioned         |
| Backtest      | Central (Fase 3)       | Not mentioned       | Not mentioned         |
| Dashboard     | Not mentioned          | Central             | Central               |

## Commands you will need

| Purpose          | Command                                              | Expected on success |
|-----------------|------------------------------------------------------|---------------------|
| Verify no em-dash | `grep -rn $'\xe2\x80\x94' PRODUCT.md README.md ROADMAP.md DESIGN.md` | no matches |

## Scope

**In scope** (the only files you should modify):
- `PRODUCT.md`
- `README.md`
- `ROADMAP.md`
- `DESIGN.md` (may need updating depending on the decision)

**Out of scope** (do NOT touch):
- All source code in `src/` and `scripts/`
- All test files
- `CHECKUP.md` (source of truth for implementation status)
- `AGENTS.md` (project rules, not product direction)
- `ARCHITECTURE.md` (technical design, may need a follow-up plan)

## Git workflow

- Branch: `advisor/019-reconcile-product-direction`
- Commit per step; message style: conventional commits
  (e.g. `docs: reconcile product direction across PRODUCT, README, ROADMAP`)
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Document the current state (this step is done, it is the "Current state" section above)

Read the four key files to confirm the excerpts in "Current state" are
still accurate:

```bash
head -15 PRODUCT.md
head -15 README.md
head -5 ROADMAP.md
head -5 DESIGN.md
```

Confirm:
- PRODUCT.md line 13 mentions "Dashboard de analise de microestrutura"
- README.md line 3 mentions "Bot de trading"
- ROADMAP.md focuses on bot phases (Fases 0-5)
- DESIGN.md frontmatter says "Order Flow Terminal"

Also confirm the codebase evidence by listing the key files:

```bash
wc -l scripts/analyze_live.py scripts/statistical_analyzer.py scripts/generate_report.py
ls src/strategy/ src/backtest/ public/dashboard.html
```

**Verify**: All files exist and line counts match the excerpts above. If
any file is missing or significantly different, STOP and report.

### Step 2: Present options to the user (STOP HERE)

Present the following three options to the user. Do NOT proceed to Step 3
until the user has chosen one.

**Option A: Bot is the product, dashboard is a tool**

The trading bot (correlation-based signals, backtesting, paper/real
trading) is the primary product. The dashboard (analyze_live.py,
microstructure analysis) is a research and monitoring tool that supports
the bot but is not the product itself.

Implications:
- README.md and ROADMAP.md stay bot-focused.
- PRODUCT.md is rewritten to describe the bot, not the dashboard.
- DESIGN.md is demoted to a tool design reference, not the product design
  system.
- Dashboard scripts remain in `scripts/` as utilities.
- Future development prioritizes Fase 3 (backtest), Fase 4 (paper
  trading), Fase 5 (real trading).

**Option B: Dashboard is the product, bot is backend**

The real-time microstructure dashboard (Order Flow Terminal) is the
primary product. The trading bot (correlation analysis, strategies,
backtesting) is the backend/data layer that feeds the dashboard.

Implications:
- PRODUCT.md stays as-is (or is refined).
- README.md is rewritten to describe the dashboard product.
- ROADMAP.md is restructured to include dashboard-specific phases (e.g.
  "Fase D1: Dashboard MVP", "Fase D2: Real-time WebSocket integration").
- DESIGN.md remains the product design system.
- Future development prioritizes dashboard features (real-time updates,
  more microstructure metrics, alerting).

**Option C: Two products, clarify relationship**

Both the bot and the dashboard are products. They share infrastructure
(data pipeline, correlation analysis) but serve different users and have
different roadmaps.

Implications:
- README.md describes both products and their relationship.
- PRODUCT.md is split or expanded to cover both.
- ROADMAP.md has parallel tracks (bot phases + dashboard phases).
- DESIGN.md covers the dashboard product; a separate design doc may be
  needed for the bot's UI (if any).
- Future development is split between the two tracks.

**STOP CONDITION**: After presenting these options, STOP. Do not proceed
to Step 3 until the user has chosen Option A, B, or C. Report the user's
choice back.

### Step 3: Update docs based on the chosen option

This step depends on the user's choice from Step 2. Follow the branch
that matches the chosen option.

**If Option A (bot is the product):**

1. Rewrite PRODUCT.md to describe the trading bot product:
   - Users: quant traders / developers running an automated crypto
     trading bot
   - Product purpose: generate correlation-based trading signals,
     backtest them, and execute trades (paper then real)
   - Brand personality: technical, data-driven, cautious (emphasize
     risk management)
   - Design principles: focus on signal quality, backtest rigor, risk
     control
   - Move the dashboard description to a "Tools" section at the bottom,
     noting it as a research/monitoring utility

2. Update README.md line 3 if needed (it already describes the bot, so
   minimal changes). Add a note about the dashboard tool.

3. Update ROADMAP.md: no structural changes needed (it already follows
   the bot vision). Add a note in Fase 6 (futura) about the dashboard
   tool.

4. Update DESIGN.md: add a note at the top clarifying it describes the
   dashboard tool's visual design, not the primary product's design.

**If Option B (dashboard is the product):**

1. PRODUCT.md stays largely as-is. Refine if needed.

2. Rewrite README.md:
   - Line 3: change to describe the dashboard product
   - Objectives: real-time data collection, microstructure analysis,
     visual dashboard, alerting
   - Add a section noting the bot/strategy infrastructure as the
     backend

3. Restructure ROADMAP.md:
   - Keep Fase 0 (research) and Fase 1 (data pipeline) as shared
     infrastructure
   - Add dashboard-specific phases:
     - Fase D1: Dashboard MVP (analyze_live.py is the MVP, mark as
       CONCLUIDA)
     - Fase D2: Real-time WebSocket integration (live_collector.py
       exists, mark as CONCLUIDA or EM ANDAMENTO)
     - Fase D3: Additional microstructure metrics
     - Fase D4: Alerting and notifications
     - Fase D5: Multi-exchange support
   - Keep bot phases as "backend" phases

4. DESIGN.md stays as-is (it already describes the dashboard product).

**If Option C (two products):**

1. Expand PRODUCT.md to cover both products, or split into
   PRODUCT-bot.md and PRODUCT-dashboard.md. If splitting, update
   references in other docs.

2. Rewrite README.md to describe both products:
   - Product 1: Correlation trading bot
   - Product 2: Order flow terminal dashboard
   - Shared infrastructure section

3. Restructure ROADMAP.md with parallel tracks:
   - Bot track: Fase 0-5 (existing)
   - Dashboard track: Fase D1-D5 (new)
   - Shared track: data pipeline, correlation analysis

4. DESIGN.md covers the dashboard product. Add a note about the bot
   product's design (if it has a UI, otherwise note it is headless).

**Verify**: After making changes, `grep -rn $'\xe2\x80\x94' PRODUCT.md README.md ROADMAP.md DESIGN.md` returns no matches (no em-dash).

### Step 4: Cross-check consistency

After updating all docs, verify they are consistent:

1. README.md and PRODUCT.md describe the same product(s).
2. ROADMAP.md phases align with the product vision in PRODUCT.md.
3. DESIGN.md's scope matches the product vision (if dashboard is a tool,
   DESIGN.md says so; if dashboard is the product, DESIGN.md is the
   product design system).
4. No contradictions between any two docs.

Read each file end-to-end and check for:
- Contradictory product descriptions
- References to the "other" product that are now stale
- Missing references to the chosen product direction

**Verify**: Visual review. All four docs tell a consistent story about what the product is.

## Test plan

No tests to write. This plan modifies documentation only. Verification is
visual and grep-based:

- All four docs (PRODUCT.md, README.md, ROADMAP.md, DESIGN.md) describe
  a consistent product direction.
- No em-dash characters in any file.
- No stale references to the rejected product vision.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] Step 1 completed: current state documented and verified
- [ ] Step 2 completed: user has chosen Option A, B, or C (document the
      choice in the commit message)
- [ ] Step 3 completed: all four docs updated per the chosen option
- [ ] `grep -rn $'\xe2\x80\x94' PRODUCT.md README.md ROADMAP.md DESIGN.md` returns no matches
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- **Step 2 STOP**: You must present the three options to the user and
  wait for their decision before proceeding. Do NOT choose an option
  yourself. Do NOT proceed to Step 3 without explicit user input.
- The content at the locations in "Current state" doesn't match the
  excerpts (the docs have been updated since this plan was written).
- The user chooses an option that requires changes beyond the in-scope
  files (e.g. they want ARCHITECTURE.md updated too). Report and ask
  for confirmation before expanding scope.
- You discover that the codebase has significantly diverged from what
  is described in "Current state" (e.g. analyze_live.py has been
  refactored into src/ modules by plan 011).

## Maintenance notes

For the human/agent who owns this code after the change lands:

- The product direction decision made in Step 2 is a strategic choice.
  It should be documented in AGENTS.md under "Decisoes tecnicas
  registradas" (following the pattern of existing decisions on lines
  186-210). This is out of scope for this plan but should be done as a
  follow-up.
- If Option B or C is chosen, ARCHITECTURE.md may need updating to
  reflect the dashboard architecture. This is out of scope; create a
  follow-up plan.
- If Option A is chosen, the dashboard scripts (analyze_live.py, etc.)
  remain in `scripts/` as tools. Plan 011 (extract analyze_live.py into
  src/ modules) may still be valuable for code organization, but the
  extracted modules would be tool modules, not product modules.
- A reviewer should verify that the four docs tell a single, coherent
  story. Read them in order: PRODUCT.md (what), README.md (overview),
  ROADMAP.md (when), DESIGN.md (how it looks).
- This plan has a MED risk rating because it involves a product strategy
  decision that affects all future work. The decision should be made by
  a human, not an agent.
