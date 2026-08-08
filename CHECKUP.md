# Checkup: Estado do Projeto

**Ultima atualizacao:** 2026-07-15
**Fase atual:** Fase 1 e 2 concluidas, Fase 2.5 (pesquisa de estrategias) concluida

## O que esta pronto

### Fase 0: Pesquisa e Documentacao (CONCLUIDA)
- [x] Pesquisa de mercado sobre APIs da B3 (indices, futuros, dolar)
- [x] Comparativo B3 vs cripto: decisao por cripto
- [x] `DATA_SOURCES.md`: catalogo de fontes de dados de cripto
- [x] `TOOLS_AND_LIBS.md`: catalogo de bibliotecas, repos e frameworks
- [x] `ARCHITECTURE.md`: design tecnico do sistema
- [x] `ROADMAP.md`: 6 fases com criterios de saida
- [x] `AGENTS.md`: regras para agentes de IA
- [x] Estrutura de pastas criada

### Fase 1: Pipeline de Dados Historicos (CONCLUIDA)
- [x] `requirements.txt` com dependencias base
- [x] Ambiente virtual Python 3.14 com todas as dependencias instaladas
- [x] `.gitignore` configurado
- [x] `src/data/parquet_store.py`: leitura/escrita Parquet com particionamento
- [x] `src/data/universe.py`: definicao de ativos tradaveis (25 symbols default)
- [x] `scripts/download_historical.py`: download da Binance Vision e REST API
- [x] Dados baixados: 10 symbols, 2 timeframes (1d + 1h), 6 meses (Jan-Jun 2024)
  - 1d: 1.820 candles (10 symbols x 182 dias)
  - 1h: 43.680 candles (10 symbols x ~4.368 horas)
  - Total: 45.500 candles em 120 arquivos Parquet (5.1 MB)
- [x] Validacao: dados conferidos com API live da Binance

### Fase 2: Matriz de Correlacao e Grafo (CONCLUIDA)
- [x] `src/analysis/returns.py`: calculo de log-returns e simple-returns
- [x] `src/analysis/returns.py`: alinhamento de multi-asset (fill gaps, drop sparse)
- [x] `src/analysis/correlation.py`: matriz de correlacao (Pearson, Spearman, Kendall)
- [x] `src/analysis/correlation.py`: rolling correlation com janela deslizante
- [x] `src/analysis/correlation.py`: matriz de distancia e extracao de edges
- [x] `src/analysis/graph.py`: construcao do grafo (NetworkX)
- [x] `src/analysis/graph.py`: deteccao de comunidades (greedy modularity)
- [x] `src/analysis/graph.py`: metricas (density, centrality, betweenness)
- [x] `src/viz/graph_visualizer.py`: visualizacao interativa (Pyvis)
- [x] `scripts/build_correlation_graph.py`: pipeline completo
- [x] Grafo HTML gerado e validado com dados reais

### Testes (TDD)
- [x] 52 testes unitarios (pytest)
- [x] Todos os 52 testes passando
- [x] Cobertura: ParquetStore, Universe, Returns, Correlation, Graph, GraphVisualizer
- [x] Teste de integracao end-to-end com dados reais

### Resultados com dados reais (10 symbols, 1d, Jan-Jun 2024)
- Correlacao media: 0.654 (alta, como esperado em cripto)
- Correlacao max: 0.870 (ADA-DOT)
- Correlacao min: 0.395 (BNB-XRP)
- 2 comunidades detectadas:
  - Community 0: BTC, SOL, BNB, ETH, ADA (large caps)
  - Community 1: AVAX, DOGE, DOT, XRP, LINK (mid/meme caps)
- Grafo: 10 nodes, 40 edges, densidade 0.89

### Fase 2.5: Pesquisa de Estrategias (CONCLUIDA)
- [x] Pesquisa profunda sobre: day trade, price action, estatistica aplicada, entropia, order flow, microestrutura, volume profile, momentum, VWAP, funding rate, liquidity sweep, ICT/SMC, Hurst exponent, cointegracao
- [x] 9 manuais de estrategias criados em `docs/strategies/`:
  - 01: Mean Reversion por Correlacao (293 linhas)
  - 02: Price Action Breakout/Pullback (372 linhas)
  - 03: Statistical Arbitrage Cointegracao (444 linhas)
  - 04: Entropy-Based Regime Detection (451 linhas)
  - 05: Volume Profile / Order Flow (435 linhas)
  - 06: Momentum / Trend Following (469 linhas)
  - 07: VWAP Reversion (443 linhas)
  - 08: Funding Rate Arbitrage (402 linhas)
  - 09: Liquidity Sweep / ICT (598 linhas)
- [x] Documento master `docs/STRATEGIES.md` (301 linhas) com:
  - Comparativo de performance esperada
  - Mapa de regime x estrategia
  - Arquitetura de combinacao (meta-filtro + direcionais + delta-neutral)
  - Plano para chegar a 80% de assertividade
  - Protocolo de backtest (walk-forward, custos, slippage)
- [x] Total: 4.208 linhas de documentacao de estrategias

## O que falta (proximos passos)

### Fase 3: Backtest de Estrategia
1. Implementar `src/strategy/base.py` (interface comum)
2. Implementar STRAT-04 (Entropy/Hurst) como meta-filtro
3. Implementar STRAT-01 (Mean Reversion por Correlacao)
4. Implementar STRAT-06 (Momentum / Trend Following)
5. Implementar STRAT-03 (Statistical Arbitrage)
6. Implementar `src/backtest/engine.py` (VectorBT ou Backtrader)
7. Implementar `src/backtest/walk_forward.py`
8. Backtest individual de cada estrategia
9. Backtest combinado com meta-filtro
10. Validar Sharpe OOS >= 1.5 e Profit Factor >= 3.0

### Fase 4: Bot em Paper Trading
1. Implementar `src/bot/engine.py` (loop principal)
2. Implementar `src/bot/risk_manager.py`
3. Implementar `src/bot/paper_broker.py`
4. Conectar WebSocket da Binance
5. Rodar 30 dias em paper

### Fase 5: Bot em Real
1. Configurar API keys
2. Implementar `src/bot/live_broker.py`
3. Comecar com $50-100
4. Monitoramento 24/7

## Metricas de progresso

| Metrica | Atual | Meta Fase 1 | Meta Fase 3 |
|---------|-------|-------------|-------------|
| Pares em Parquet | 10 | 30+ | 30+ |
| Dados cobertos (anos) | 0.5 | 3+ | 3+ |
| Scripts funcionais | 2 | 2 | 4 |
| Testes | 52 | 5+ | 80+ |
| Linhas de codigo | ~800 | ~500 | ~2000 |
| Grafo HTML gerado | Sim | N/A | N/A |
| Backtest rodado | Nao | N/A | Sim |

## Licoes aprendidas

### Bug do Pyvis: variavel `title` sobrescrita
- **Problema:** no `GraphVisualizer.visualize()`, a variavel `title` (parametro do metodo) era sobrescrita dentro do loop de edges por `title = f"Correlation: {weight:.3f}"`. Isso fazia o nome do arquivo HTML ser gerado com o valor da correlacao em vez do titulo real.
- **Fix:** renomear a variavel do loop para `edge_title`.
- **Licao:** nunca reusar nomes de parametros como variaveis locais em loops.

### Dados de 1h vs 1d
- Correlacao em 1h e muito mais alta (densidade 1.0, 1 comunidade so) que em 1d (densidade 0.89, 2 comunidades)
- Em 1h, o ruido de curto prazo faz tudo correlacionar (BTC puxa tudo)
- Em 1d, ha mais separacao entre clusters (large caps vs mid caps)
- **Implicacao:** usar 1d ou 4h para grafos de correlacao, 1h apenas para execucao do bot

### Binance Vision: dados mensais vs diarios
- Arquivos mensais nem sempre estao disponiveis para meses recentes
- Fallback para arquivos diarios funciona mas e mais lento (mais requests)
- Para meses completos do passado, mensal e mais eficiente (1 request vs 28-31)
