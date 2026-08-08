# AGENTS.md: Regras para Agentes de IA neste Projeto

## Contexto do projeto

Bot de trading em criptomoedas baseado em grafos de correlacao. Dados da Binance (Vision + API + WebSocket). Python 3.11+. Ver `README.md`, `ROADMAP.md`, `ARCHITECTURE.md` para detalhes.

## Regras absolutas

### 0. NUNCA usar travessao (em-dash)
Usar ":" ou "." ou "," no lugar. Aplica a todos os arquivos.

### 1. Seguranca de API keys
- NUNCA hardcodear API keys, secrets, ou tokens no codigo
- SEMPRE usar `.env` (gitignored) com `python-dotenv`
- NUNCA fazer log de API keys ou saldo completo
- Validar presenca de env vars no startup (fail fast)

### 2. Dados financeiros
- NUNCA simular ou fabricar dados de preco. Se nao tem o dado, dizer explicitamente
- SEMPRE validar integridade dos dados baixados (checksum, contagem de linhas, gaps)
- Se dados de teste forem necessarios, gerar com seed fixo e marcar como sinteticos

### 3. Trading real
- NUNCA implementar execucao real sem kill switch
- NUNCA assumir fill de ordem: sempre confirmar via WebSocket
- SEMPRE comecar com paper trading (minimo 30 dias) antes de real
- Capital inicial maximo para teste real: $100 (configuravel, mas comecar baixo)

### 4. Backtest
- NUNCA usar dados futuros no backtest (look-ahead bias)
- SEMPRE separar in-sample e out-of-sample
- Reportar metricas OOS, nao IS
- Se Sharpe IS > 3.0, suspeitar de overfit e investigar

### 5. Correlacao
- Correlacao nao implica causalidade
- Correlacao em cripto e instavel (muda com regime de mercado)
- SEMPRE usar janela deslizante, nunca correlacao estatica sobre todo o periodo
- BTC domina: considerar remover "market mode" via PCA antes de clusterizar

## Padroes de codigo

### Estilo
- Python 3.11+ (type hints obrigatorios)
- Indentacao: 4 espacos
- Linha maxima: 120 caracteres
- Naming: snake_case para funcoes/variaveis, PascalCase para classes
- Arquivos: snake_case.py
- Funcoes: maximo 30 linhas (ideal < 15)

### Imports
```python
# Stdlib primeiro
import asyncio
from pathlib import Path

# Terceiros
import numpy as np
import pandas as pd
import ccxt

# Projeto (explicit relative ou absolute)
from src.data.parquet_store import ParquetStore
from src.analysis.correlation import CorrelationMatrix
```

### Type hints
```python
def calculate_returns(
    prices: pd.DataFrame,
    method: str = "log"
) -> pd.DataFrame:
    ...
```

### Tratamento de erros
- NAO usar try/except pass (empty catch)
- Erros de API: retry com exponential backoff (max 3)
- Erros de dados: raise com contexto (qual symbol, qual periodo)
- Erros do bot: log + notificacao Telegram + kill switch se critico

### Logging
- Structured logging (JSON) com `structlog` ou `logging` + formatter JSON
- Correlation ID por ciclo do bot
- Nivel: DEBUG (desenvolvimento), INFO (producao), WARNING (alertas), ERROR (erros)
- NUNCA logar API keys, saldo completo, ou dados pessoais

### Testes
- Todo modulo novo deve ter testes (pytest)
- Cobrir: happy path, edge cases, error cases
- Dados de teste: fixtures com dados sinteticos (seed fixo)
- Rodar `pytest` antes de commitar

## Comandos do projeto

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download de dados
python scripts/download_historical.py --symbols BTCUSDT,ETHUSDT --start 2023-01-01 --end 2024-01-01 --timeframe 5m

# Gerar grafo de correlacao
python scripts/build_correlation_graph.py --period 2024-01 --threshold 0.5

# Backtest
python scripts/run_backtest.py --strategy mean_reversion --start 2023-01-01 --end 2024-06-01

# Rodar bot em paper
python scripts/run_paper_bot.py --config config/paper.yaml

# Rodar bot em real (CUIDADO)
python scripts/run_live_bot.py --config config/live.yaml

# Testes
pytest tests/ -v
pytest tests/test_correlation.py -v

# Lint
ruff check src/ scripts/
mypy src/
```

## Estrutura de arquivos

```
src/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── parquet_store.py     # I/O Parquet
│   └── universe.py          # Definicao de ativos
├── analysis/
│   ├── __init__.py
│   ├── returns.py           # Calculo de returns
│   ├── correlation.py       # Matriz de correlacao
│   └── graph.py             # Construcao do grafo
├── viz/
│   ├── __init__.py
│   └── graph_visualizer.py  # Pyvis
├── strategy/
│   ├── __init__.py
│   ├── base.py              # Interface
│   └── mean_reversion.py    # Implementacao
├── backtest/
│   ├── __init__.py
│   ├── engine.py            # VectorBT
│   └── walk_forward.py      # Walk-forward
└── bot/
    ├── __init__.py
    ├── engine.py            # Loop principal
    ├── risk_manager.py      # Gestao de risco
    ├── paper_broker.py      # Simulador
    ├── live_broker.py       # Execucao real
    └── notifications.py     # Telegram
```

## Base de conhecimento (docs/pesquisas/)

Em 2026-07-15 foi criada uma base de conhecimento em `docs/pesquisas/` com 38 arquivos
markdown (10.093 linhas) + 1 dashboard HTML interativo, cobrindo 6 grupos de pesquisa:

| Grupo | Pasta | Arquivos | Topicos |
|-------|-------|----------|---------|
| Visao geral | `00-visao-geral/` | 3 md + 1 html | Organograma do sistema, panorama do mercado 2026, explicacao para criancas, dashboard interativo (vis-network) |
| Microestrutura | `01-microestrutura/` | 5 md | Order book/depth/microprice, order flow/CVD/delta, volume profile/VPVR, Kyle/Amihud/VPIN, taker flow/wick analysis |
| Estatistica/Quant | `02-estatistica-quant/` | 6 md | Returns/correlacao rolling, cointegracao/stat arb, Hurst/half-life, GARCH, regime detection HMM/entropy, VaR/CVaR/drawdowns |
| Estrategias | `03-estrategias-trading/` | 7 md | Mean reversion correlacao, momentum/trend, VWAP reversion, funding rate arb, liquidity sweep ICT, price action, delta-neutral |
| Mercado crypto | `04-mercado-crypto/` | 6 md | Perp futures/funding/OI/liquidations, BTC dominancia/rotacao, fear greed/on-chain, kill zones/sessoes, lead-lag/Granger, on-chain/DeFi |
| Ferramentas/Infra | `05-ferramentas-infra/` | 5 md | Binance Vision/CCXT/python-binance, NetworkX/Pyvis/graph-tool, Parquet/Arrow/TSDB, backtest frameworks, bot frameworks |
| Mercado competitivo | `06-mercado-competitivo/` | 5 md | Bots retail (3Commas/Cryptohopper/Pionex), plataformas quant (Coinglass/Laevitas/Velo), APIs dados 2026, IA trading/LLM, DeFi/on-chain analytics |

Cada arquivo segue estrutura padrao: TL;DR, Explicacao para criancas, Como funciona
tecnicamente, Estado do mercado em 2026, Ferramentas e APIs disponiveis, Por que importa
para o crypto-correl-bot, Referencias.

**Dashboard interativo:** `docs/pesquisas/00-visao-geral/mapa-sistema-mercado.html`
(abrir no browser). Mostra nodes do sistema + nodes do mercado com filtros por categoria.

**Como consultar:** ver `docs/pesquisas/README.md` para ordem de leitura recomendada.

## Decisoes tecnicas registradas

### 2026-07-15: Cripto ao inves de B3
- **Decisao:** Usar dados de cripto (Binance) ao inves de B3 (Bovespa)
- **Motivo:** Dados da B3 sao caros (R$ 320-3200/mes) e burocraticos. Cripto e gratis e sem burocracia.
- **Alternativas rejeitadas:** Cedro (R$ 440-689/mes PF), B3 direto (R$ 3200+/mes PJ), HG Brasil (nao cobre futuros)
- **Ver detalhes:** `docs/research/api-comparison-b3.md`

### 2026-07-15: Parquet para armazenamento
- **Decisao:** Usar Apache Parquet para dados historicos
- **Motivo:** Colunar, comprimido, sem servidor, nativo no pandas/arrow
- **Alternativas rejeitadas:** SQLite (menos eficiente para series temporais), Postgres (overkill para dados locais), CSV (sem compressao, sem schema)

### 2026-07-15: VectorBT para backtest
- **Decisao:** VectorBT como engine de backtest principal
- **Motivo:** Vetorizado (Numba), 20x mais rapido para sweeps de parametros
- **Alternativas rejeitadas:** Backtrader (mais lento, mas mais realista, usar para validacao final), Zipline (complexo de instalar)

### 2026-07-15: NetworkX + Pyvis para grafos
- **Decisao:** NetworkX para analise + Pyvis para visualizacao
- **Motivo:** Puro Python, facil instalacao, integracao nativa, suficiente para 30-50 nodes
- **Alternativas rejeitadas:** graph-tool (rapido mas dificil instalar), D3.js direto (precisa frontend)

### 2026-07-15: Redesign do dashboard com design system DashboardKit
- **Decisao:** Reescrever o HTML/CSS gerado por `scripts/analyze_live.py` usando layout com sidebar, topbar, cards, badges e tabelas inspirados no template DashboardKit, mantendo dark theme de terminal de trading.
- **Motivo:** Melhorar hierarquia visual, densidade informacional e legibilidade dos dados. Manter identidade profissional e semantica (verde/vermelho/bull/bear) do produto.
- **Arquivos alterados:** `scripts/analyze_live.py`, `DESIGN.md` (novo), `AGENTS.md`.
- **Nota:** Removido media query `prefers-color-scheme: light` para garantir dark theme padrao do terminal. WebSocket de order book continua funcional com batch 50ms.

### 2026-07-16: Auditoria de imports vs grafo de visualizacao
- **Decisao:** Corrigir o grafo `mapa-sistema-mercado.html` para refletir SO imports reais do codigo, e corrigir 2 code gaps reais.
- **Motivo:** O grafo tinha ~50 edges quase todas erradas (direcoes invertidas, conexoes falsas, 5 nodes faltando). A auditoria via grep revelou 34 imports reais.
- **Correcoes no grafo:** 73 nodes, 110 edges (76 solid = import real, 34 dashed = data flow/futuro), 0 orphans. Adicionados 5 nodes faltando (meta, build-corr-graph, download-historical, run-collector, gen-sci-report). Legenda com 3 tipos de edge.
- **Correcoes no codigo:**
  - GAP-2: `live_collector.py` agora importa `Universe` e usa `get_default_universe()[:5]` em vez de symbols hardcoded
  - GAP-4: `statistical_analyzer.py` agora usa `ParquetStore` em vez de glob (o glob estava QUEBRADO para a estrutura particionada atual)
  - GAP-5: `arch>=6.0` adicionado ao requirements.txt (ja era importado mas nao estava listado)
- **Nao-correcoes (decisoes arquiteturais corretas):**
  - GAP-1: live_collector nao usa ParquetStore (schemas diferentes: microestrutura L2 vs OHLCV)
  - GAP-3: analyze_live nao usa ParquetStore (le de data/live/, nao data/parquet/)
- **Ver detalhes:** `docs/pesquisas/00-visao-geral/CODE-GAPS.md`
- **Validacao:** 15/15 modulos src/ + 9/9 scripts importam OK. `analyze_historical_data('MATICUSDT', 'data/parquet')` retorna dados reais.

### 2026-07-16: Fase 4 implementada com TDD (src/bot/)
- **Decisao:** Implementar os 5 modulos da Fase 4 (paper trading) usando TDD: testes primeiro, depois implementacao.
- **Modulos criados:**
  - `src/bot/engine.py`: BotEngine, loop principal com state machine (INIT/RUNNING/PAUSED/STOPPED), kill switch, stop loss automatico
  - `src/bot/risk_manager.py`: RiskManager com max position size, stop loss, drawdown diario, kill switch, max positions
  - `src/bot/paper_broker.py`: PaperBroker com slippage (5 bps), fees (taker 0.1%, maker 0.075%), tracking de posicoes/cash/PnL
  - `src/bot/notifications.py`: NotificationManager stub (log only, sem HTTP). Niveis DEBUG/INFO/WARNING/ERROR/CRITICAL
  - `src/bot/live_broker.py`: LiveBroker stub para Fase 5. dry_run=True por default. NUNCA envia ordens reais sem enabled=True
- **Testes criados (TDD):** 106 testes novos (27 risk_manager + 24 paper_broker + 21 bot_engine + 16 notifications + 18 live_broker)
- **Testes para modulos existentes:** 88 testes novos (19 walk_forward + 35 meta + 34 live_collector)
- **Total:** 308 testes, todos passando
- **Motivo:** Fase 4 era o proximo bloco logico do ROADMAP. TDD garante que cada modulo tem cobertura antes de integrar.
- **Seguranca:** live_broker comeca desativado (enabled=False, dry_run=True). NUNCA loga api_key/secret. notifications NUNCA loga tokens.
- **Validacao:** `pytest tests/ -v` = 308 passed. Grafo atualizado com 5 novos nodes de bot/.
