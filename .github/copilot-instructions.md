# Copilot Instructions: crypto-correlation-trader

## Visao geral
Bot de trading em criptomoedas baseado em grafos de correlacao entre ativos. Coleta
dados da Binance, calcula matriz de correlacao com log-returns, constroi grafo para
identificar clusters, gera sinais baseados em quebras e reconexoes de correlacao.

## Stack
- Python 3.11+ com type hints
- pandas + numpy para analise
- NetworkX + Pyvis para grafos
- VectorBT para backtest vetorizado
- CCXT / python-binance para execucao
- Parquet para armazenamento historico
- pytest (308 testes)

## Convencoes
- Correlacao com janela deslizante, nunca sobre todo o periodo
- Separar in-sample e out-of-sample no backtest
- Reportar metricas OOS, nao IS
- Se Sharpe IS > 3.0, suspeitar de overfit
- Kill switch obrigatorio em trading real
- Paper trading minimo 30 dias antes de real
- SQL parameterized, nunca concatenar
- Dados sinteticos com seed fixo em testes

## NAO faca
- Nao hardcodear API keys (sempre .env com python-dotenv)
- Nao usar dados futuros no backtest (look-ahead bias)
- Nao assumir fill de ordem (confirmar via WebSocket)
- Nao logar API keys ou saldo completo
- Nao simular dados de preco reais
- Nao commitar .env
