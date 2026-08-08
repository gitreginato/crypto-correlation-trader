# STRATEGIES.md: Manual Master de Estrategias

**Projeto:** crypto-correl-bot
**Data:** 2026-07-15
**Objetivo:** Chegar a >= 80% de assertividade combinando estrategias

## Visao Geral

9 estrategias foram pesquisadas e documentadas. Cada uma tem um manual detalhado em `docs/strategies/`. Este documento e o indice comparativo que ajuda a decidir quais implementar e combinar no backtest.

## Indice de Estrategias

| ID | Estrategia | Manual | Categoria | Timeframe | Complexidade |
|----|------------|--------|-----------|-----------|--------------|
| 01 | Mean Reversion por Correlacao | [01](strategies/01-mean-reversion-correlation.md) | Statistical | 1h, 4h, 1d | Media |
| 02 | Price Action (Breakout/Pullback) | [02](strategies/02-price-action-breakout-pullback.md) | Technical | 15m, 1h, 4h | Media-Alta |
| 03 | Statistical Arbitrage (Cointegracao) | [03](strategies/03-statistical-arbitrage-cointegration.md) | Statistical | 5m, 15m, 1h | Alta |
| 04 | Entropy-Based (Regime Detection) | [04](strategies/04-entropy-regime-detection.md) | Meta-Filter | 1h, 4h, 1d | Alta |
| 05 | Volume Profile / Order Flow | [05](strategies/05-volume-profile-order-flow.md) | Microstructure | 5m, 15m, 1h | Alta |
| 06 | Momentum / Trend Following | [06](strategies/06-momentum-trend-following.md) | Trend | 1h, 4h, 1d | Media |
| 07 | VWAP Reversion | [07](strategies/07-vwap-reversion.md) | Mean Reversion | 5m, 15m, 1h | Baixa-Media |
| 08 | Funding Rate Arbitrage | [08](strategies/08-funding-rate-arbitrage.md) | Delta-Neutral | 8h, 1d | Media |
| 09 | Liquidity Sweep (ICT) | [09](strategies/09-liquidity-sweep-ict.md) | Institutional | 15m, 1h, 4h | Alta |

## Comparativo de Performance Esperada

| ID | Win Rate | Sharpe | Max DD | R:R | Trades/mes | Horizonte |
|----|----------|--------|--------|-----|------------|-----------|
| 01 | 60%+ | 1.5+ | < 10% | 1.5:1 | 10-30 | Horas a dias |
| 02 | 50%+ | 1.5+ | < 12% | 2.0:1 | 8-20 | Horas a dias |
| 03 | 65%+ | 2.0+ | < 8% | 1.5:1 | 15-40 | Min a horas |
| 04 | N/A | +30%* | -30%* | N/A | N/A | Filtro |
| 05 | 55%+ | 1.5+ | < 10% | 1.5:1 | 20-50 | Min a horas |
| 06 | 45%+ | 1.2+ | < 25% | 3.0:1 | 5-10 | Dias a semanas |
| 07 | 65%+ | 1.5+ | < 8% | 1.2:1 | 30-80 | Min a horas |
| 08 | N/A** | 2.0+ | < 3% | N/A | 1-5 | Dias a semanas |
| 09 | 60%+ | 1.5+ | < 10% | 2.5:1 | 8-15 | Horas |

\* STRAT-04 e um meta-filtro: melhora o Sharpe das outras estrategias em ~30% e reduz drawdown em ~30%.
\** STRAT-08 e delta-neutral: win rate nao se aplica, mede por yield anualizado (5-30%).

## Mapa de Regime x Estrategia

Qual estrategia funciona em qual regime de mercado (usando Entropy + Hurst para classificar):

| Regime | Entropy | Hurst | Estrategias Ativas | Estrategias Inativas |
|--------|---------|-------|--------------------|-----------------------|
| MEAN_REVERT | Baixa | < 0.45 | 01, 03, 07 | 06 |
| TRENDING | Baixa | > 0.55 | 06, 02 | 01, 03, 07 |
| RANDOM | Media | ~0.5 | 02 (cautela) | 01, 03, 06, 07 |
| TRANSITION | Media | qualquer | Todas com 50% size | N/A |
| CHAOTIC | Alta | qualquer | Nenhuma (PARAR) | Todas |
| BULL EXTREME | Baixa | > 0.6 | 06, 08, 09 | 01, 03 |
| BEAR EXTREME | Baixa | > 0.6 | 06 (short), 08, 09 | 01, 03 |

## Arquitetura de Combinacao

### Nivel 1: Meta-Filtro (sempre ativo)

```
STRAT-04 (Entropy + Hurst)
  |
  +-> Classifica regime a cada candle
  +-> Ativa/desativa estrategias por regime
  +-> Ajusta tamanho por confianca do regime
```

### Nivel 2: Estrategias Direcionais (ativas por regime)

```
MEAN_REVERT regime:
  +-> STRAT-01 (Mean Reversion por Correlacao)
  +-> STRAT-03 (StatArb por Cointegracao)
  +-> STRAT-07 (VWAP Reversion)

TRENDING regime:
  +-> STRAT-06 (Momentum / Trend Following)
  +-> STRAT-02 (Price Action Breakout)

Qualquer regime (com cautela):
  +-> STRAT-09 (Liquidity Sweep, se kill zone)
  +-> STRAT-05 (Volume Profile, se dados L2 disponiveis)
```

### Nivel 3: Estrategia Delta-Neutral (sempre ativa)

```
STRAT-08 (Funding Rate Arbitrage)
  |
  +-> Independente de regime
  +-> Funciona em paralelo com estrategias direcionais
  +-> Reduz volatilidade do portfolio
  +-> Yield base estavel (5-30% a.a.)
```

### Fluxo de decisao do bot

```
1. A cada candle novo:
   a. Calcular Entropy + Hurst (STRAT-04)
   b. Classificar regime atual
   c. Se CHAOTIC: fechar tudo, esperar
   d. Se TRANSITION: reduzir tamanho em 50%

2. Se regime permite estrategias direcionais:
   a. Rodar estrategias ativas para o regime
   b. Coletar sinais de cada estrategia
   c. Se multiplos sinais no mesmo ativo: somar confianca
   d. Se sinais conflitantes (long vs short): nao operar

3. Em paralelo, sempre:
   a. Monitorar funding rates (STRAT-08)
   b. Se funding extremo: abrir/close arbitragem
   c. Monitorar sweeps (STRAT-09) em kill zones

4. Gestao de risco global:
   a. Max drawdown do portfolio: 15%
   b. Max posicoes simultaneas: 10
   c. Max correlacao entre posicoes: 0.7
   d. Kill switch: drawdown > 20% para tudo
```

## Prioridade de Implementacao para Backtest

### Fase 3a: Implementar as 4 estrategias core (ordem de prioridade)

| Prioridade | Estrategia | Razao | Esforco |
|------------|------------|-------|---------|
| 1 | STRAT-04 (Entropy) | Meta-filtro que melhora todas as outras | Medio |
| 2 | STRAT-01 (Mean Reversion Corr) | Ja temos infra de correlacao | Baixo |
| 3 | STRAT-06 (Momentum) | Mais simples e validada academicamente | Baixo |
| 4 | STRAT-03 (StatArb) | Alta performance esperada (Sharpe 2+) | Medio |

### Fase 3b: Implementar estrategias complementares

| Prioridade | Estrategia | Razao | Esforco |
|------------|------------|-------|---------|
| 5 | STRAT-07 (VWAP Reversion) | Simples, alto win rate | Baixo |
| 6 | STRAT-08 (Funding Arb) | Delta-neutral, reduz volatilidade | Medio |
| 7 | STRAT-02 (Price Action) | Complementa Volume Profile | Medio |
| 8 | STRAT-09 (Liquidity Sweep) | Alta R:R mas subjetiva | Alto |
| 9 | STRAT-05 (Volume Profile) | Requer dados L2 em tempo real | Alto |

### Estrategia de chegada aos 80%

```
Cenario realista de combinacao:

1. STRAT-04 filtra ~30% dos trades ruins (regime caotico)
   -> Win rate base sobe de 55% para ~65%

2. STRAT-01 + STRAT-03 combinadas (mean reversion multi-escala)
   -> Sinais conflitantes sao filtrados
   -> Win rate combinado: ~70%

3. STRAT-06 ativa so em trending (filtrada por STRAT-04)
   -> Win rate em trending: ~55% mas R:R 3:1
   -> Contribui para Sharpe sem prejudicar win rate

4. STRAT-08 (funding arb) roda em paralelo
   -> Nao afeta win rate direcional
   -> Adiciona yield estavel, reduz drawdown

5. STRAT-09 (liquidity sweep) em kill zones
   -> Win rate: ~60% mas R:R 2.5:1
   -> Poucos trades mas alta qualidade

RESULTADO ESPERADO:
  Win rate direcional: 65-75%
  Win rate ponderado por R:R: 70-80%
  Sharpe combinado: 1.5-2.5
  Max drawdown: 8-12%

Para chegar a 80% de assertividade:
  - Filtrar agressivamente com STRAT-04 (so operar em regime claro)
  - Exigir confirmacao multi-estrategia (2+ estrategias concordam)
  - Kill zones estritas (STRAT-09 so em London/NY)
  - Stop apertado e take profit disciplinado
  - Nao operar em eventos de noticia (CPI, FOMC, NFP)
```

## Requisitos de Dados por Estrategia

| Estrategia | OHLCV | Volume | Order Book L2 | Trade Tick | Funding Rate |
|------------|-------|--------|---------------|------------|--------------|
| 01 Mean Rev Corr | OK | Nao | Nao | Nao | Nao |
| 02 Price Action | OK | Sim | Nao | Nao | Nao |
| 03 StatArb | OK | Nao | Nao | Nao | Opcional |
| 04 Entropy | OK | Nao | Nao | Nao | Nao |
| 05 Volume Profile | OK | Sim | Sim (ideal) | Sim (ideal) | Nao |
| 06 Momentum | OK | Sim | Nao | Nao | Nao |
| 07 VWAP Reversion | OK | Sim | Nao | Nao | Nao |
| 08 Funding Arb | OK | Nao | Nao | Nao | Sim |
| 09 Liquidity Sweep | OK | Sim | Opcional | Nao | Opcional |

**Status dos dados no projeto:**
- OHLCV: disponivel (Binance Vision, ja baixado para 10 symbols)
- Volume: disponivel (incluido nos klines)
- Order Book L2: NAO disponivel (requer WebSocket ao vivo)
- Trade Tick: disponivel via Binance Vision (aggTrades)
- Funding Rate: disponivel via Binance API (futures)

## Fatores Adicionais de Decisao

### Fatores que podem melhorar a assertividade

1. **Filtro de eventos macro**: nao operar 30min antes/depois de CPI, FOMC, NFP
2. **Sentiment analysis**: Fear & Greed Index extremo como filtro
3. **Correlation regime**: se correlacao media do cluster > 0.9, todos se movem juntos (reduz oportunidades de mean reversion)
4. **Volatility regime**: ATR ratio (ATR atual / ATR medio 30d) para ajustar tamanho
5. **Time of day**: win rate varia significativamente por horario (kill zones)
6. **Day of week**: fins de semana tem liquidez menor em crypto
7. **Bitcoin dominance**: se BTC.D subindo, altcoins sofrem (filtro para altcoin strategies)

### Fatores que podem prejudicar

1. **Overfitting**: muitos parametros, otimizar demais no IS
2. **Transaction costs**: 0.1% por trade em spot, 0.04% maker em futures
3. **Slippage**: ordens a mercado podem ter slippage de 0.05-0.2%
4. **Funding costs**: manter shorts em perp custa funding a cada 8h
5. **Latency**: tempo entre sinal e execucao (especialmente STRAT-05)
6. **Liquidity**: ordens grandes movem o mercado em crypto

## Validacao: Como medir 80% de assertividade

### Definicao de "assertividade"

```
Assertividade = Win Rate ponderado por R:R

Exemplo:
  10 trades: 6 vencedores (60%), 4 perdedores (40%)
  Vencedores: R:R medio 2.5 (ganha 2.5x o risco)
  Perdedores: perde 1x o risco

  P&L = 6 * 2.5R - 4 * 1R = 15R - 4R = +11R
  Profit factor = 15/4 = 3.75

  Assertividade efetiva = 11R / 15R = 73% (do P&L bruto virou lucro)

  Para 80%: profit factor >= 4.0
  = vencedores precisam de R:R medio 3.0 com 60% win rate
  = OU win rate 70% com R:R 2.0
```

### Metricas para validar 80%

| Metrica | Target 80% | Como medir |
|---------|------------|------------|
| Profit factor | >= 4.0 | gross_profit / gross_loss |
| Expectancy | >= 0.8R | (win_rate * avg_win) - (loss_rate * avg_loss) |
| Win rate x R:R | >= 1.6 | win_rate * avg_rr |
| Sharpe ratio | >= 2.0 | mean(excess_returns) / std(excess_returns) * sqrt(365) |
| Max drawdown | < 10% | max peak-to-trough decline |
| Calmar ratio | >= 3.0 | CAGR / max_drawdown |

### Backtest protocol

```
1. Dados: 2021-2024 (3 anos, cobre bull, bear, lateral)
2. Split: 70% IS (2021-2023), 30% OOS (2024)
3. Walk-forward: 6m IS, 2m OOS, step 2m
4. Custos: 0.1% per trade (spot), 0.04% maker (futures)
5. Slippage: 0.05% per trade
6. Funding: incluir para posicoes em perp
7. Position sizing: 1% risk per trade, max 10% portfolio risk
8. Rebalanceamento: diario

CRITERIO DE SUCESSO:
  OOS Sharpe >= 1.5 (vs IS Sharpe >= 2.0)
  OOS Max DD <= 12%
  OOS Profit Factor >= 3.0
  IS-OOS degradation <= 30%
```

## Resumo: Plano de Acao

```
FASE 3 (Backtest):
  1. Implementar STRAT-04 (Entropy/Hurst) como meta-filtro
  2. Implementar STRAT-01 (Mean Reversion Correlation)
  3. Implementar STRAT-06 (Momentum)
  4. Backtest individual de cada uma
  5. Implementar STRAT-03 (StatArb)
  6. Backtest combinado: STRAT-04 + STRAT-01 + STRAT-06 + STRAT-03
  7. Implementar STRAT-07 (VWAP) e STRAT-08 (Funding)
  8. Backtest completo com 6 estrategias
  9. Walk-forward validation
  10. Se Sharpe OOS >= 1.5: avancar para Fase 4 (Paper Trading)

FASE 4 (Paper Trading):
  - Adicionar STRAT-09 (Liquidity Sweep) com dados ao vivo
  - Adicionar STRAT-05 (Volume Profile) se dados L2 disponiveis
  - Rodar 30 dias em paper
  - Validar que live performance bate backtest

FASE 5 (Live):
  - Comecar com $50-100
  - So STRAT-01, STRAT-03, STRAT-06, STRAT-08 (mais validadas)
  - Adicionar outras conforme ganha confianca
```
