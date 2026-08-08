# Code Gaps Audit: crypto-correl-bot

Data: 2026-07-16
Metodo: comparacao de imports reais (grep) com grafo de visualizacao

## Analise revisada apos inspecao do codigo

### GAP-1: live_collector.py nao usa ParquetStore
- **Status:** NAO E GAP. Decisao arquitetural correta.
- **Motivo:** live_collector escreve dados de microestrutura L2 (order_book, trades, funding, liquidations, open_interest, long_short, fear_greed) em `data/live/` com schema proprio. ParquetStore e especializado em OHLCV com schema fixo (open_time, open, high, low, close, etc) em `data/parquet/`. Schemas e propositos diferentes. Forcar ParquetStore seria arquiteturalmente errado.

### GAP-2: live_collector.py nao usa Universe (CORRIGIDO)
- **Arquivo:** src/data/live_collector.py
- **Problema:** Symbols hardcoded no CollectorConfig: `["BTCUSDT", "ETHUSDT", "SOLUSDT"]`
- **Correcao aplicada:** Import de `Universe` e uso de `Universe().get_default_universe()[:5]` como default
- **Validado:** `CollectorConfig().symbols` retorna `['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']`

### GAP-3: analyze_live.py nao usa ParquetStore
- **Status:** NAO E GAP. Decisao arquitetural correta.
- **Motivo:** analyze_live.py le dados de `data/live/` (microestrutura L2 do live_collector), nao de `data/parquet/` (OHLCV). ParquetStore nao se aplica. O padrao glob+read_parquet e correto para este caso.

### GAP-4: statistical_analyzer.py nao usa ParquetStore (CORRIGIDO)
- **Arquivo:** scripts/statistical_analyzer.py
- **Problema:** Usava `glob.glob(f"{ohlcv_path}/{symbol}*.parquet")` que nao encontra dados na estrutura particionada do ParquetStore (`data/parquet/binance/spot/SYMBOL/TIMEFRAME/year=YYYY/month=MM/`). O script estava QUEBRADO para a estrutura atual de dados.
- **Correcao aplicada:** Import de `ParquetStore`, uso de `store.get_available_timeframes(symbol)` + `store.read(symbol, timeframe)`, renomeacao `open_time -> timestamp` para compatibilidade downstream.
- **Validado:** `analyze_historical_data('MATICUSDT', 'data/parquet')` retorna dados com keys `['symbol', 'timestamp', 'data_points', 'returns_stats', 'stationarity']`

### GAP-5: arch nao estava no requirements.txt (CORRIGIDO)
- **Problema:** statistical_analyzer.py importa `from arch import arch_model` mas `arch` nao estava no requirements.txt nem instalado
- **Correcao aplicada:** Adicionado `arch>=6.0` ao requirements.txt e instalado (arch-8.0.0)

### GAP-6: generate_correlation_dashboard.py nao importa analyze_correlations.py
- **Status:** NAO E GAP. Design decision (loose coupling via JSON).
- **Motivo:** Dashboards leem JSON de saida via `json.load()`. Isso e intencional, permite rodar analise e dashboard separadamente.

### GAP-7: generate_microstructure_dashboard.py nao importa analyze_microstructure.py
- **Status:** NAO E GAP. Mesmo padrao que GAP-6. Design decision.

## Resumo final

| ID | Severidade | Status | Acao |
|----|-----------|--------|------|
| GAP-1 | N/A | NAO E GAP | Decisao arquitetural correta |
| GAP-2 | Baixo | CORRIGIDO | live_collector usa Universe |
| GAP-3 | N/A | NAO E GAP | Decisao arquitetural correta |
| GAP-4 | Alto (bug) | CORRIGIDO | statistical_analyzer usa ParquetStore |
| GAP-5 | Medio | CORRIGIDO | arch adicionado ao requirements.txt |
| GAP-6 | N/A | NAO E GAP | Design decision |
| GAP-7 | N/A | NAO E GAP | Design decision |

## Licao aprendida

A analise inicial de imports via grep identificou 4 "gaps" potenciais. Apos inspecao do codigo real, 2 deles (GAP-1, GAP-3) sao decisoes arquiteturais corretas: ParquetStore e para OHLCV historico, nao para microestrutura L2 em tempo real. A analise mecanica de imports nao captura a intencao arquitetural.
