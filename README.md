# Crypto Correlation Trader

> Bot de trading em criptomoedas baseado em grafos de correlação entre ativos. Coleta dados da Binance, calcula matriz de correlação com log-returns, constrói grafo para identificar clusters, gera sinais baseados em quebras e reconexões de correlação, e executa via API da Binance (paper trading primeiro).

## Stack

| Camada | Tecnologia | Por quê |
|--------|-----------|---------|
| Dados históricos | Binance Vision (CSV) + CCXT | Grátis, tick-by-tick desde 2017 |
| Dados tempo real | Binance WebSocket (python-binance) | Baixa latência, grátis |
| Armazenamento | Parquet (histórico) + Redis (estado) | Colunar, comprimido, rápido |
| Análise | pandas + numpy | Padrão da indústria |
| Grafos | NetworkX + Pyvis | NetworkX para análise, Pyvis para visualizar |
| Backtest | VectorBT | Vetorizado (Numba), 20x mais rápido para sweeps |
| Execução | CCXT / python-binance | Direto na exchange |
| Testes | pytest (308 testes) | TDD desde o início |

## O que aprendi

- **Decisão de domínio justificada**: escolhi cripto ao invés de B3 porque dados da B3 custam R$ 320-3200/mês e exigem vendor license. Cripto é grátis, granular e sem burocracia. Documentei a comparação em `docs/research/api-comparison-b3.md`.
- **Parquet sobre SQLite/Postgres**: para séries temporais, Parquet é colunar, comprimido e nativo no pandas. Sem servidor, sem overhead.
- **Correlação não é estática**: usei janela deslizante em vez de correlação sobre todo o período. BTC domina o mercado, então considerei remover "market mode" via PCA antes de clusterizar.
- **Backtest honesto**: separação in-sample/out-of-sample, walk-forward, e alerta se Sharpe IS > 3.0 (suspeita de overfit).
- **Segurança no trading real**: kill switch obrigatório, paper trading mínimo 30 dias antes de real, capital inicial máximo $100, nunca assumir fill de ordem (confirmar via WebSocket).
- **TDD em sistema financeiro**: 308 testes escritos antes da implementação, cobrindo happy path, edge cases e error cases com dados sintéticos (seed fixo).

## Funcionalidades

- **Coleta de dados históricos** via Binance Vision (CSV) e API pública
- **Matriz de correlação** entre ativos usando log-returns com janela deslizante
- **Grafo de correlação** interativo (NetworkX + Pyvis) para visualizar clusters
- **Sinais de trading** baseados em quebras e reconexões de correlação
- **Backtest walk-forward** com VectorBT (vetorizado, Numba)
- **Paper trading** com slippage (5 bps), fees (taker 0.1%, maker 0.075%), tracking de PnL
- **Risk manager** com max position size, stop loss, drawdown diário, kill switch
- **Live broker** com dry_run=True por padrão (nunca envia ordens sem enabled=True)

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Baixar dados históricos
python scripts/download_historical.py --symbols BTCUSDT,ETHUSDT --start 2023-01-01

# Gerar grafo de correlação
python scripts/build_correlation_graph.py --period 2024-01 --threshold 0.5

# Backtest
python scripts/run_backtest.py --strategy mean_reversion --start 2023-01-01 --end 2024-06-01

# Paper trading
python scripts/run_paper_bot.py --config config/paper.yaml

# Testes
pytest tests/ -v
```

## Arquitetura

```
src/
├── data/           # Parquet I/O, definição de universos
├── analysis/       # Returns, matriz de correlação, grafo
├── viz/            # Visualização Pyvis
├── strategy/       # Interface + mean reversion
├── backtest/       # Engine VectorBT + walk-forward
└── bot/            # Engine, risk manager, paper/live broker, notifications
```

## Testes

308 testes cobrindo:
- Risk manager (27 testes): max position, stop loss, drawdown, kill switch
- Paper broker (24 testes): slippage, fees, PnL tracking
- Bot engine (21 testes): state machine, kill switch, stop loss automático
- Walk-forward (19 testes): separação IS/OOS, métricas OOS
- Live collector (34 testes): coleta WebSocket, validação de dados
- Meta/correlação (35+34 testes): matriz, janela deslizante, PCA

```bash
pytest tests/ -v
```

## Status

- **Fase 0**: Pesquisa e documentação (concluída)
- **Fase 1**: Pipeline de dados históricos (concluída)
- **Fase 2**: Matriz de correlação e grafo (concluída)
- **Fase 3**: Backtest de estratégia (concluída)
- **Fase 4**: Paper trading com risk manager (concluída)
- **Fase 5**: Trading real (planejada, com kill switch e capital $100)

## Avisos

- Projeto educacional e de pesquisa
- Trading de cripto envolve risco significativo de perda
- Sempre testar em paper trading antes de operar real
- Não usar dinheiro que não pode perder

## Licença

[MIT](LICENSE)
