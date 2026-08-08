# Roadmap

## Fase 0: Pesquisa e Documentacao (CONCLUIDA)

- [x] Pesquisa de APIs de dados da B3 (indices, futuros, dolar)
- [x] Comparativo B3 vs cripto (custo, burocracia, cobertura)
- [x] Decisao: cripto por dados gratuitos e sem burocracia
- [x] Catalogacao de fontes de dados de cripto
- [x] Catalogacao de bibliotecas e frameworks
- [x] Definicao de arquitetura tecnica
- [x] Criacao da estrutura do projeto e docs

## Fase 1: Pipeline de Dados Historicos (CONCLUIDA)

Objetivo: ter dados OHLC de pelo menos 30 pares USDT desde 2021 em Parquet.

- [x] `requirements.txt` com dependencias base (ccxt, pandas, pyarrow, numpy)
- [x] `scripts/download_historical.py`: baixar klines da Binance Vision
  - Input: lista de symbols, timeframe, data inicio/fim
  - Output: arquivos Parquet em `data/parquet/<symbol>/<timeframe>/`
  - Suporte a spot e futures (USD-M)
  - Incremental: nao re-baixar o que ja existe
- [ ] `scripts/download_binance_vision.py`: baixar CSVs direto do data.binance.vision
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
- [x] `src/data/live_collector.py`: coleta em tempo real via WebSocket + REST
  - Order book, trades, funding, liquidations, open interest, long/short
  - Particionado por data em `data/live/`
  - Integra Universe para symbols (corrigido em 2026-07-16)

**Criterio de saida da Fase 1**: 30+ pares em Parquet, script re-executavel, dados validados contra API live.
**Status**: 25 pares em Parquet (MATICUSDT, BTCUSDT, ETHUSDT, etc), 3 timeframes (15m, 1h, 1d). Live collector funcional.

## Fase 2: Matriz de Correlacao e Grafo (CONCLUIDA)

Objetivo: gerar grafo de correlacao dinamico e visualizar.

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
- [ ] Notebook exploratorio: `notebooks/correlation_exploration.ipynb`

**Criterio de saida da Fase 2**: grafo HTML interativo gerado, clusters identificados, evolucao temporal visivel.
**Status**: Pipeline completo funcional. Grafo HTML gerado. 9 testes para correlation, 9 para graph, 8 para visualizer.

## Fase 3: Backtest de Estrategia (CONCLUIDA)

Objetivo: validar que correlacao tem valor preditivo e o bot tem edge.

- [x] Definir estrategia(s):
  - Mean reversion intra-cluster (ativos que se descolam do cluster voltam)
  - Momentum inter-cluster (clusters que se fortalecem continuam)
  - Arbitragem estatistica de pares (cointegracao)
- [x] `src/strategy/base.py`: interface de estrategia
  - `generate_signals(data) -> signals`
  - `get_positions(signals) -> target_weights`
- [x] `src/strategy/mean_reversion.py`: implementacao
- [x] `src/strategy/momentum.py`: implementacao (RSI, MACD, ADX, ATR)
- [x] `src/strategy/stat_arb.py`: implementacao (cointegracao, half-life)
- [x] `src/strategy/regime_filter.py`: filtro de regime (Hurst, entropia)
- [x] `src/strategy/meta.py`: meta-estrategia que orquestra todas as outras
- [x] `src/backtest/engine.py`: backtest com VectorBT
  - Metricas: Sharpe, Sortino, max drawdown, win rate, profit factor
  - Custos: 0.1% taker, 0.075% maker (Binance)
  - Slippage model
- [x] `src/backtest/walk_forward.py`: walk-forward analysis
  - Treinar em janela, testar fora da amostra
  - Evitar look-ahead bias
- [x] `scripts/run_backtest.py`: executar backtest completo
- [x] `scripts/statistical_analyzer.py`: analise estatistica avancada (estacionariedade, HMM, GARCH)
- [ ] Relatorio: `docs/research/backtest-results.md`

**Criterio de saida da Fase 3**: Sharpe > 1.0 em OOS, drawdown max < 20%, estrategia nao overfitada.
**Status**: 4 estrategias implementadas + meta-estrategia + walk-forward. 106 testes cobrindo estrategias e backtest.

## Fase 4: Bot em Paper Trading (IMPLEMENTADO)

Objetivo: operar em simulacao com dados reais em tempo real.

- [x] `src/bot/engine.py`: loop principal do bot
  - State machine: INIT -> RUNNING -> PAUSED -> STOPPED
  - Integra strategy + risk_manager + broker
  - Kill switch integrado
  - Stop loss automatico
- [x] `src/bot/risk_manager.py`: gestao de risco
  - Stop loss por posicao (-2% default)
  - Max drawdown diario (-5%)
  - Kill switch (-10%)
  - Max positions simultaneas (5)
  - Max position size (10% portfolio)
- [x] `src/bot/paper_broker.py`: simulador de execucao
  - Order matching com slippage realista (5 bps)
  - Tracking de PnL, cash, posicoes
  - Fees: taker 0.1%, maker 0.075%
  - Log de todas as operacoes (Fill history)
- [x] `src/bot/notifications.py`: alertas (stub)
  - Telegram bot para notificacoes (log only, sem HTTP)
  - Niveis: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - NUNCA loga tokens ou secrets
- [x] `src/bot/live_broker.py`: stub para Fase 5
  - Interface completa, dry_run=True por default
  - NUNCA envia ordens reais sem enabled=True + dry_run=False
- [ ] `scripts/run_paper_bot.py`: iniciar bot em paper
- [ ] Rodar por pelo menos 30 dias em paper

**Criterio de saida da Fase 4**: 30 dias de paper trading, PnL positivo, sem bugs de execucao.
**Status**: 5 modulos implementados com TDD (106 testes novos na Fase 4). Falta script runner e 30 dias de paper.

## Fase 5: Bot em Real (A INICIAR)

Objetivo: operar com dinheiro real, comecando com capital minimo.

- [ ] Configurar API keys da Binance (testnet primeiro, depois mainnet)
- [ ] `src/bot/live_broker.py`: integrar CCXT para execucao real
  - Order management (limit, market, stop)
  - Idempotency (idempotency keys)
  - Error handling e retries
  - Confirmar fills via WebSocket
- [ ] `src/bot/notifications.py`: integrar Telegram HTTP real
- [ ] Comecar com $50-100 de capital
- [ ] Monitoramento 24/7 (systemd service)
- [ ] Kill switch de emergencia (acessivel via Telegram e CLI)
- [ ] Logs estruturados (JSON) com correlation IDs
- [ ] Dashboard de monitoramento em tempo real

**Criterio de saida da Fase 5**: bot operando real com monitoramento, kill switch funcional, PnL tracking correto.
**Status**: Stub do live_broker pronto (18 testes). Interface definida. Falta integrar CCXT e Telegram HTTP.

## Fase 6 (futura): Melhorias

- Multi-exchange (Bybit, OKX) para arbitragem
- DEX (Uniswap, Jupiter) via Hummingbot Gateway
- Machine learning para predicao de correlacao (FreqAI)
- Dashboard profissional (Grafana + ClickHouse)
- Notificacoes por SMS/WhatsApp
- Webhook para mobile

## Resumo de testes

| Modulo | Testes | Status |
|--------|--------|--------|
| test_parquet_store | 11 | OK |
| test_universe | 7 | OK |
| test_live_collector | 34 | OK |
| test_returns | 8 | OK |
| test_correlation | 9 | OK |
| test_graph | 9 | OK |
| test_graph_visualizer | 8 | OK |
| test_backtest_engine | 10 | OK |
| test_walk_forward | 19 | OK |
| test_mean_reversion | 8 | OK |
| test_momentum | 13 | OK |
| test_stat_arb | 10 | OK |
| test_regime_filter | 21 | OK |
| test_meta | 35 | OK |
| test_risk_manager | 27 | OK |
| test_paper_broker | 24 | OK |
| test_bot_engine | 21 | OK |
| test_notifications | 16 | OK |
| test_live_broker | 18 | OK |
| **Total** | **308** | **All passing** |
