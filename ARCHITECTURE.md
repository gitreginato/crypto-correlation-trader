# Arquitetura Tecnica

## Visao geral

```
+------------------+     +------------------+     +------------------+
|  Binance Vision  |     |  Binance API     |     |  Binance WS      |
|  (CSV historico) |     |  (REST klines)   |     |  (tempo real)    |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+--------+---------+     +--------+---------+     +--------+---------+
|  download_vision  |     |  download_api    |     |  ws_streamer     |
|  (scripts/)       |     |  (scripts/)      |     |  (src/bot/)      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        |
+--------+---------+     +--------+---------+              |
|  Parquet Store    |<----+  Parquet Store   |              |
|  (data/parquet/)  |     |  (data/parquet/) |              |
+--------+---------+     +------------------+              |
         |                                                |
         v                                                v
+--------+---------+     +------------------+     +--------+---------+
|  Returns Calc     |     |  Correlation     |     |  Live Returns    |
|  (src/analysis/)  |     |  Matrix          |     |  (src/bot/)      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+--------+---------+     +--------+---------+     +--------+---------+
|  Graph Builder    |     |  Graph Builder   |     |  Signal Gen      |
|  (src/analysis/)  |     |  (src/analysis/) |     |  (src/bot/)      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+--------+---------+     +--------+---------+     +--------+---------+
|  Pyvis Visualizer |     |  VectorBT        |     |  Risk Manager    |
|  (src/viz/)       |     |  Backtest        |     |  (src/bot/)      |
+------------------+     +--------+---------+     +--------+---------+
                                  |                        |
                                  v                        v
                          +--------+---------+     +--------+---------+
                          |  Backtest Report |     |  Broker (paper/  |
                          |  (docs/)         |     |  live)           |
                          +------------------+     +------------------+
```

## Componentes

### 1. Camada de Dados (`src/data/`)

#### `parquet_store.py`
- Leitura e escrita de arquivos Parquet particionados
- Schema padrao: `timestamp, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_base, taker_buy_quote`
- Particionamento: `data/parquet/<exchange>/<market>/<symbol>/<timeframe>/year=<YYYY>/month=<MM>/`
- Usa pyarrow para I/O eficiente
- Suporte a leitura incremental (so dados novos)

#### `universe.py`
- Define lista de ativos tradaveis
- Criterios: volume medio diario > $10M, listado antes de 2022, par USDT
- Atualizacao periodica (re-ranquear a cada mes)
- Output: lista de symbols + metadados (setor, categoria)

### 2. Camada de Analise (`src/analysis/`)

#### `returns.py`
- Calcula log-returns: `ln(P_t / P_{t-1})`
- Alinha timestamps entre ativos (reindex + forward fill limitado)
- Trata gaps: se gap > 1 dia, nao faz fill
- Suporte a multi-timeframe (1m, 5m, 15m, 1h, 1d)

#### `correlation.py`
- Matriz de correlacao: Pearson (default), Spearman, Kendall
- Rolling correlation com janela configuravel (ex: 30 dias, 90 dias)
- Threshold para arestas: |corr| > 0.5 (ajustavel)
- Matriz de distancia: `d = sqrt(2 * (1 - corr))` para clustering

#### `graph.py`
- NetworkX Graph: nodes = ativos, edges = correlacao
- Atributos das edges: weight (corr), sign (positiva/negativa)
- Deteccao de comunidades: Louvain (padrao), Greedy Modularity
- Metricas por node: degree, betweenness, clustering coefficient
- Metricas do grafo: densidade, modularidade, numero de comunidades
- Evolucao temporal: lista de grafos (um por periodo)

### 3. Camada de Visualizacao (`src/viz/`)

#### `graph_visualizer.py`
- Pyvis Network para HTML interativo
- Cor das edges: verde (corr > 0), vermelho (corr < 0)
- Espessura das edges: proporcional a |corr|
- Tamanho dos nodes: proporcional ao volume ou degree
- Tooltip: mostra correlacao ao passar o mouse
- Filtro de threshold: slider para ajustar |corr| minimo
- Layout: physics engine do vis.js (force-directed)
- Output: `data/graphs/correlation_<period>.html`

### 4. Camada de Estrategia (`src/strategy/`)

#### `base.py`
- Interface abstrata: `generate_signals(data, graph) -> signals`
- Signals: DataFrame com timestamp, symbol, signal (-1, 0, 1), strength

#### `mean_reversion.py`
- Identifica ativos que se descolaram do seu cluster
- Sinal: short o ativo que subiu demais vs cluster, long o que caiu demais
- Z-score do spread vs media do cluster

#### `momentum.py` (futuro)
- Clusters que estao se fortalecendo (correlacao aumentando) = momentum
- Long no cluster com momentum positivo

### 5. Camada de Backtest (`src/backtest/`)

#### `engine.py`
- VectorBT para backtest vetorizado
- Input: signals + price data
- Custos: 0.1% taker, 0.075% maker
- Slippage: modelo simples (spread medio)
- Metricas: Sharpe, Sortino, max DD, win rate, profit factor, turnover

#### `walk_forward.py`
- Divide dados em janelas: treino (70%) + teste (30%)
- Desliza janela ao longo do tempo
- Reporta metricas agregadas OOS
- Detecta overfit: se OOS << IS, alerta

### 6. Camada de Bot (`src/bot/`)

#### `engine.py`
- Loop principal: `while True: receive_data -> update_corr -> gen_signal -> manage_risk -> execute`
- Asyncio para I/O (WebSocket + REST)
- State machine: INIT -> RUNNING -> PAUSED -> STOPPED
- Health check: heartbeat a cada 30s

#### `risk_manager.py`
- Max position size: 10% do portfolio por ativo
- Max total exposure: 100% (sem alavancagem inicial)
- Stop loss: -2% por posicao
- Max drawdown diario: -5% (para tudo)
- Kill switch: se DD > 10%, fecha tudo e para

#### `paper_broker.py`
- Simula execucao com spread real do WebSocket
- Tracking de posicoes, PnL, cash
- Log de todas as ordens (JSON)
- Latencia simulada: 100-500ms

#### `live_broker.py` (Fase 5)
- CCXT para executar ordens reais
- Idempotency: clientOrderId unico
- Retries com backoff em erros transientes
- Nunca assume fill: confirma via WebSocket

#### `notifications.py`
- Telegram bot para alertas
- Mensagens: nova ordem, fill, stop loss hit, erro critico
- Comando `/status` para ver posicoes e PnL

## Padroes de design

- **Repository pattern** para dados: `ParquetStore` abstrai I/O
- **Strategy pattern** para estrategias: interface comum, implementacoes trocaveis
- **Dependency injection**: engine recebe broker, risk_manager, strategy como parametros
- **Config-driven**: tudo via arquivo YAML ou env vars, nada hardcoded
- **Structured logging**: JSON logs com correlation ID por ciclo do bot

## Decisoes tecnicas

### Por que Parquet e nao SQLite/Postgres?
- Parquet e colunar: le so close/volume e nao todo o registro
- Comprimido: 1 ano de BTCUSDT 1m = ~50MB em Parquet vs ~200MB em CSV
- Sem servidor: arquivos diretos, portateis, versionaveis
- Pandas/Arrow leem Parquet nativamente
- Para estado do bot (posicoes, ordens), SQLite ou Redis

### Por que VectorBT e nao Backtrader?
- VectorBT: vetorizado (Numba), 20x mais rapido para sweeps
- Backtrader: event-driven, mais lento mas mais realista
- Para pesquisa (Fase 3): VectorBT (velocidade para otimizar parametros)
- Para validacao final: Backtrader (realismo de execucao)
- Para live: nem um nem outro, loop proprio em asyncio

### Por que NetworkX e nao graph-tool/igraph?
- NetworkX: puro Python, facil de instalar, ecossistema maior
- graph-tool: C++ backend, muito mais rapido, mas dificil de instalar
- Para 30-50 nodes, NetworkX e suficiente
- Se escalar para 500+ ativos, migrar para graph-tool

### Por que Pyvis e nao D3.js/Cytoscape direto?
- Pyvis: wrapper Python sobre vis.js, gera HTML standalone
- Nao precisa servidor frontend
- Interativo out of the box (zoom, drag, physics)
- Integracao nativa com NetworkX

## Consideracoes de seguranca

- API keys NUNCA no codigo, sempre em `.env` (gitignored)
- `.env` com permissoes 600
- Validacao de env vars no startup (fail fast)
- Logs nunca expoe API keys ou saldo completo
- Kill switch acessivel via Telegram (`/stop`) e CLI
- Backup de estado do bot em disco a cada ciclo
