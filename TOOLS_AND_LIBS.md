# Bibliotecas, Repositorios e Ferramentas

Catalogo de tudo que pode ajudar o desenvolvimento do projeto.

## Bibliotecas Python (core)

### Dados e I/O

| Biblioteca | Versao | Funcao | Repo |
|-----------|--------|--------|------|
| ccxt | 4.5+ | Abstracao de 100+ exchanges (REST + WS) | [ccxt/ccxt](https://github.com/ccxt/ccxt) |
| python-binance | 1.0.37+ | Cliente especifico da Binance (REST + WS) | [sammchardy/python-binance](https://github.com/sammchardy/python-binance) |
| pandas | 2.2+ | Manipulacao de dados tabulares | pypi |
| pyarrow | 17+ | I/O Parquet, backend do pandas | pypi |
| numpy | 2.0+ | Computacao numerica | pypi |
| aiohttp | 3.9+ | HTTP assincrono (download paralelo) | pypi |
| websockets | 12+ | WebSocket client para Binance | pypi |
| requests | 2.32+ | HTTP sincrono (scripts simples) | pypi |

### Analise e Grafos

| Biblioteca | Versao | Funcao | Repo |
|-----------|--------|--------|------|
| networkx | 3.3+ | Construcao e analise de grafos | [networkx/networkx](https://github.com/networkx/networkx) |
| pyvis | 0.3+ | Visualizacao interativa de grafos (HTML) | [WestHealth/pyvis](https://github.com/WestHealth/pyvis) |
| scipy | 1.13+ | Estatistica (correlacao, cointegracao) | pypi |
| statsmodels | 0.14+ | Cointegracao (ADF, Johansen), ARIMA | pypi |
| scikit-learn | 1.5+ | PCA, clustering, normalizacao | pypi |

### Backtest

| Biblioteca | Versao | Funcao | Repo |
|-----------|--------|--------|------|
| vectorbt | 0.26+ | Backtest vetorizado (Numba) | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) |
| backtrader | 1.9.78+ | Backtest event-driven (validacao) | [mementum/backtrader](https://github.com/mementum/backtrader) |

### Bot e Execucao

| Biblioteca | Versao | Funcao | Repo |
|-----------|--------|--------|------|
| asyncio | (stdlib) | Loop assincrono do bot | stdlib |
| redis | 5.0+ | Cache e estado em tempo real | pypi |
| pydantic | 2.7+ | Validacao de config e schemas | pypi |
| pyyaml | 6.0+ | Arquivos de configuracao | pypi |
| python-dotenv | 1.0+ | Carregar .env | pypi |

### Visualizacao e Dashboard

| Biblioteca | Versao | Funcao | Repo |
|-----------|--------|--------|------|
| plotly | 5.22+ | Graficos interativos (candlestick, heatmap) | pypi |
| matplotlib | 3.9+ | Graficos estaticos | pypi |
| seaborn | 0.13+ | Heatmaps de correlacao | pypi |
| streamlit | 1.36+ | Dashboard rapido (opcional) | pypi |
| fastapi | 0.111+ | API web para dashboard | pypi |

### Notificacoes

| Biblioteca | Versao | Funcao | Repo |
|-----------|--------|--------|------|
| python-telegram-bot | 21+ | Bot de Telegram para alertas | pypi |

### Qualidade e Testes

| Biblioteca | Versao | Funcao |
|-----------|--------|--------|
| pytest | 8.2+ | Framework de testes |
| pytest-asyncio | 0.23+ | Testes async |
| ruff | 0.5+ | Linter e formatter |
| mypy | 1.10+ | Type checking |

---

## Frameworks de Trading Bot (referencia)

### Freqtrade
- **Repo:** [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) (50k+ stars)
- **Licenca:** GPL-3.0
- **Linguagem:** Python 3.11+
- **Features:** Backtesting, Hyperopt, FreqAI (ML), WebUI, Telegram, dry-run
- **Exchanges:** Binance, Bybit, OKX, Kraken, Gate.io, Hyperliquid
- **Veredito:** Framework completo. Opcao se nao quisermos construir do zero. Porem e opinionado e dificil integrar grafos de correlacao como estrategia custom. Melhor como referencia de arquitetura.

### Hummingbot
- **Repo:** [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) (19k+ stars)
- **Licenca:** Apache-2.0
- **Linguagem:** Python + Cython
- **Features:** Market making, arbitragem, DEX support (Gateway)
- **Veredito:** Foco em market making e arbitragem, nao em estrategia de correlacao. Util se quisermos adicionar DEX no futuro (Fase 6).

### Jesse
- **Repo:** [jesse-ai/jesse](https://github.com/jesse-ai/jesse) (8k+ stars)
- **Licenca:** MIT
- **Linguagem:** Python + JavaScript (UI)
- **Features:** Backtest preciso, otimizacao, paper trading, live
- **Veredito:** Framework limpo e bem desenhado. MIT license e mais permissivo que Freqtrade (GPL). Considerar se precisarmos de framework.

### Nautilus Trader
- **Repo:** nautechsystems/nautilus_trader
- **Licenca:** LGPL-3.0
- **Linguagem:** Python + Rust
- **Features:** Alta performance, institutional-grade
- **Veredito:** Overkill para nosso caso. Pensar nisso se precisarmos de latencia < 1ms.

---

## Repositorios de Referencia (estudo)

### Analise de Correlacao em Cripto

| Repo | Stars | Descricao | Utilidade |
|------|-------|-----------|-----------|
| [elbasri/crypto-data-analysis](https://github.com/elbasri/crypto-data-analysis) | - | Dashboard Dash + Plotly + NetworkX para correlacao de top 10 USDT pairs | Alta: referencia de arquitetura de correlacao + visualizacao |
| [Aroesler1/crypto_stat_arb](https://github.com/Aroesler1/crypto_stat_arb) | - | Stat-arb com grafos de correlacao signed, PCA market mode removal, SPONGE/BNC clustering | Alta: referencia para estrategia de mean reversion |
| [LeonardoDiGaetano/crypto-sql-portfolio](https://github.com/LeonardoDiGaetano/crypto-sql-portfolio) | 1 | Pipeline SQL + Python para correlacao temporal de cripto | Media: referencia de pipeline ETL |
| [oxlupo/Crypto-Correlation-Matrix](https://github.com/oxlupo/Crypto-Correlation-Matrix) | 2 | Matriz de correlacao via CoinGecko | Baixa: simples demais |
| [VanHes1ng/Correlation-Trend](https://github.com/VanHes1ng/Correlation-Trend) | 2 | Streamlit app para correlacao vs BTC | Baixa: simples demais |

### Download de Dados Binance

| Repo | Stars | Descricao | Utilidade |
|------|-------|-----------|-----------|
| [binance/binance-public-data](https://github.com/binance/binance-public-data) | oficial | Scripts oficiais para download da Binance Vision | Alta: usar `python/download-kline.py` como base |

### Backtest e Estrategias

| Repo | Stars | Descricao | Utilidade |
|------|-------|-----------|-----------|
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 4k+ | Framework de backtest vetorizado | Alta: usar diretamente |
| examples/PairsTrading.ipynb (vectorbt) | - | Exemplo de pairs trading com vectorbt vs backtrader | Alta: referencia de implementacao |

---

## MCPs disponiveis (Devin)

MCPs que podem ajudar durante o desenvolvimento:

### memory (Knowledge Graph MCP)
- **Funcao:** Armazena entidades e relacoes em um knowledge graph persistente
- **Ferramentas:** `create_entities`, `create_relations`, `add_observations`, `search_nodes`, `read_graph`
- **Uso neste projeto:** Mapear relacoes entre ativos, estrategias, e decisoes tecnicas. Por exemplo: "BTCUSDT -> correlacionado_com -> ETHUSDT (0.85)", "mean_reversion -> depende_de -> graph_clustering"
- **Veredito:** Util para manter contexto entre sessoes sobre decisoes do projeto

### github (GitHub MCP)
- **Funcao:** Interage com repos do GitHub (search, create, fork, issues, PRs)
- **Ferramentas:** `search_repositories`, `get_file_contents`, `create_issue`, `create_pull_request`
- **Uso neste projeto:** Buscar repos de referencia, criar issues para tracking, criar PRs
- **Veredito:** Usar para gerenciar o repo do projeto se for hospedado no GitHub

### playwright (Browser MCP)
- **Funcao:** Automacao de browser (navegacao, screenshots, interacao)
- **Ferramentas:** `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_evaluate`
- **Uso neste projeto:** Validar visualmente os grafos HTML gerados pelo Pyvis, testar dashboard
- **Veredito:** Usar para testes visuais do dashboard e grafos

### shadcn / magic
- **Funcao:** Componentes de UI (shadcn/ui) e geracao de UI (magic)
- **Veredito:** Relevante se construirmos dashboard web com React. Por ora, FastAPI + HTMX e suficiente.

---

## Skills disponiveis (Devin)

Skills que podem ajudar durante o desenvolvimento:

| Skill | Quando usar |
|-------|-------------|
| `session-memory` | Persistir decisoes entre sessoes (qual estrategia escolhemos, quais parametros) |
| `task-observer` | Capturar padroes e melhorias de workflow durante o desenvolvimento |
| `systematic-debugging` | Quando encontrar bugs no bot ou no pipeline de dados |
| `verification-before-completion` | Antes de claimar que o bot funciona, validar com testes |
| `dispatching-parallel-agents` | Para baixar dados de 30 symbols em paralelo |
| `subagent-driven-development` | Para implementar modulos independentes em paralelo |
| `graphify` | Se quisermos mapear a estrutura do codigo do projeto como grafo |
| `impeccable` | Se construirmos dashboard web e quisermos polish de UI |
| `writing-skills` | Se quisermos criar skills especificas para este projeto |

---

## Ferramentas de linha de comando

| Ferramenta | Funcao | Instalacao |
|-----------|--------|------------|
| curl/wget | Download de arquivos da Binance Vision | pre-instalado |
| jq | Parse JSON de respostas da API | `apt install jq` |
| duckdb | Query Parquet com SQL (exploracao rapida) | `pip install duckdb` |
| clickhouse | Banco colunar para grandes volumes (futuro) | Docker |
| grafana | Dashboard de monitoramento (futuro) | Docker |
| tmux | Manter bot rodando em sessao persistente | pre-instalado |
| systemd | Service para bot 24/7 | pre-instalado |

---

## Comandos uteis (referencia)

```bash
# Baixar 1 mes de BTCUSDT 1h da Binance Vision
wget "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"
unzip BTCUSDT-1h-2024-01.zip

# Verificar todos os symbols disponiveis na Binance
curl -s "https://api.binance.com/api/v3/exchangeInfo" | jq '.symbols[].symbol' | head -20

# Verificar rate limit restante
curl -s -I "https://api.binance.com/api/v3/ping" | grep "X-MBX-USED-WEIGHT"

# Listar top 10 pares USDT por volume 24h
curl -s "https://api.binance.com/api/v3/ticker/24hr" | jq '[.[] | select(.symbol | endswith("USDT"))] | sort_by(-.quoteVolume) | .[:10] | .[] | {symbol, volume: .quoteVolume}'

# Query Parquet com DuckDB
duckdb -c "SELECT * FROM 'data/parquet/binance/spot/BTCUSDT/1m/year=2024/month=01.parquet' LIMIT 10"
```
