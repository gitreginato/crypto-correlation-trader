# Estrategia 01: Mean Reversion por Correlacao

**ID:** STRAT-01
**Categoria:** Statistical / Relative Value
**Timeframe ideal:** 1h, 4h, 1d
**Horizonte:** Curto a medio prazo (horas a dias)
**Complexidade:** Media

## 1. Conceito

A estrategia explora o fato de que ativos cripto altamente correlacionados tendem a se mover juntos. Quando um ativo se descola significativamente do seu cluster (grupo de ativos correlacionados), ha uma alta probabilidade de reverter a media do grupo.

### Intuicao

Se BTC e ETH tem correlacao de 0.85, eles normalmente se movem juntos. Se em uma janela curta BTC sobe 5% e ETH cai 2%, o spread entre eles se descolou. A aposta e que esse spread vai convergir de volta ao normal.

### Diferenca vs Statistical Arbitrage

Mean Reversion por Correlacao usa a **media do cluster** como ancora. Statistical Arbitrage (STRAT-03) usa **cointegracao** entre exatamente 2 ativos. A diferenca pratica:

- Correlacao: "BTC esta caro vs a media de {ETH, SOL, BNB, ADA}"
- Cointegracao: "O spread BTC-ETH saiu de 2 desvios do seu equilibrio de longo prazo"

## 2. Fundamentacao Teorica

### 2.1 Correlacao de Pearson

```
corr(A, B) = sum((rA - mean_rA) * (rB - mean_rB)) / (std_rA * std_rB * (n-1))
```

Mede a relacao linear entre dois ativos. Varia de -1 (anti-correlacionados) a +1 (perfeitamente correlacionados).

### 2.2 Z-Score do Descolamento

Para cada ativo `i` no cluster `C`:

```
cluster_return(t) = mean(returns[j, t] for j in C, j != i)
deviation(t) = returns[i, t] - cluster_return(t)
z_score(t) = (deviation(t) - rolling_mean(deviation, window)) / rolling_std(deviation, window)
```

### 2.3 Pressupostos

1. A correlacao de longo prazo e estacionaria (nao muda drasticamente)
2. Descolamentos extremos sao causados por ruido, nao por mudanca fundamental
3. O ativo descolado vai reverter, nao o cluster inteiro

### 2.4 Quando os pressupostos falham

- Eventos especificos de um ativo (hack, listing, delisting, upgrade)
- Mudanca de regime de mercado (bull para bear)
- Correlacao quebrada por narrativa setorial (DeFi summer, AI season, meme season)
- Liquidacoes em cascata que afetam um ativo mais que outros

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `correlation_threshold` | 0.5 | 0.3 a 0.8 | Correlacao minima para formar cluster |
| `correlation_window` | 90 | 30 a 180 | Janela para calcular correlacao (dias) |
| `zscore_window` | 20 | 10 a 60 | Janela para calcular z-score do descolamento |
| `entry_zscore` | 2.0 | 1.5 a 3.0 | Z-score para abrir posicao |
| `exit_zscore` | 0.5 | 0.0 a 1.0 | Z-score para fechar posicao |
| `stop_zscore` | 4.0 | 3.0 a 5.0 | Z-score para stop loss |
| `min_cluster_size` | 3 | 2 a 5 | Minimo de ativos no cluster |
| `max_position_per_asset` | 0.10 | 0.05 a 0.20 | Max % do portfolio por ativo |

## 4. Sinais de Entrada

### 4.1 Long (ativo subperformou o cluster)

```
SE z_score(i) < -entry_zscore:
    ABRIR LONG no ativo i
    APOSTA: ativo i vai subir para convergir com o cluster
```

### 4.2 Short (ativo sobreperformou o cluster)

```
SE z_score(i) > +entry_zscore:
    ABRIR SHORT no ativo i
    APOSTA: ativo i vai cair para convergir com o cluster
```

### 4.3 Filtro de regime (obrigatorio)

```
SE Hurst_exponent(returns[i]) > 0.55:
    NAO operar (mercado em trending, mean reversion falha)
SE Hurst_exponent(returns[i]) < 0.45:
    OPERAR (mercado em mean-reverting, ideal para a estrategia)
SE 0.45 <= Hurst_exponent <= 0.55:
    OPERAR com tamanho reduzido (50% do normal)
```

## 5. Sinais de Saida

### 5.1 Take Profit (convergencia)

```
SE |z_score(i)| < exit_zscore:
    FECHAR posicao (spread convergiu)
```

### 5.2 Stop Loss (divergencia continua)

```
SE |z_score(i)| > stop_zscore:
    FECHAR posicao (spread continua divergindo, hipotese invalida)
```

### 5.3 Saida por tempo

```
SE tempo_em_posicao > max_holding_period:
    FECHAR posicao (independente do z-score)
```

### 5.4 Saida por quebra de correlacao

```
SE correlacao(i, cluster) cai abaixo de correlation_threshold * 0.5:
    FECHAR posicao (a relacao quebrou)
```

## 6. Gestao de Risco

### 6.1 Position Sizing

```
position_size = base_risk * confidence_multiplier

base_risk = 1% do portfolio por trade
confidence_multiplier = min(1.0, |z_score| / entry_zscore)
```

### 6.2 Correlacao entre posicoes

Se 2 ativos do mesmo cluster geram sinal simultaneamente, reduzir tamanho de cada um pela metade (eles sao correlacionados, o risco nao e independente).

### 6.3 Drawdown kill switch

```
SE drawdown > 15%:
    PAUSAR estrategia por 24h
    Re-calcular correlacoes do zero
SE drawdown > 25%:
    PARAR estrategia
    Revisao manual obrigatoria
```

### 6.4 Maximo de posicoes simultaneas

```
max_concurrent = 5
SE posicoes_abertas >= max_concurrent:
    NAO abrir novas posicoes
```

## 7. Implementacao Tecnica

### 7.1 Modulos necessarios

```python
# Ja implementados
from src.analysis.correlation import CorrelationMatrix
from src.analysis.graph import CorrelationGraph
from src.analysis.returns import calculate_returns, align_returns

# A implementar
from src.strategy.mean_reversion import MeanReversionStrategy
from src.strategy.regime_filter import HurstExponentFilter
```

### 7.2 Pseudocodigo

```python
def generate_signals(returns: pd.DataFrame, params: dict) -> list[Signal]:
    # 1. Calcular matriz de correlacao
    cm = CorrelationMatrix(method="pearson")
    corr = cm.compute(returns.tail(params["correlation_window"]))

    # 2. Detectar clusters (comunidades)
    cg = CorrelationGraph(threshold=params["correlation_threshold"])
    graph = cg.build(corr)
    communities = cg.detect_communities(graph)

    # 3. Para cada cluster, calcular z-score de descolamento
    signals = []
    for comm_id, members in group_by_community(communities):
        if len(members) < params["min_cluster_size"]:
            continue

        for asset in members:
            # Cluster return exclui o proprio ativo
            cluster_others = [m for m in members if m != asset]
            cluster_return = returns[cluster_others].mean(axis=1)
            deviation = returns[asset] - cluster_return
            zscore = rolling_zscore(deviation, params["zscore_window"])

            # Filtro de regime
            hurst = compute_hurst(returns[asset].tail(100))
            if hurst > 0.55:
                continue  # trending, skip

            # Sinal
            current_z = zscore.iloc[-1]
            if current_z < -params["entry_zscore"]:
                signals.append(Signal(asset, "LONG", confidence=abs(current_z)))
            elif current_z > params["entry_zscore"]:
                signals.append(Signal(asset, "SHORT", confidence=abs(current_z)))

    return signals
```

### 7.3 Rolling Z-Score

```python
def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / std
```

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 60%+ | 55% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 10% | < 15% |
| Profit factor | 2.0+ | 1.5 |
| Avg holding period | 2-48h | 1-72h |
| Trades por mes | 10-30 | 5+ |

## 9. Backtest: O que validar

### 9.1 In-Sample vs Out-of-Sample

```
IS: 70% dos dados (ex: 2021-2023)
OOS: 30% dos dados (ex: 2024)
Validar que Sharpe_OOS > 0.7 * Sharpe_IS
```

### 9.2 Walk-Forward

```
Janela IS: 6 meses
Janela OOS: 2 meses
Step: 2 meses
Rodar em todo o periodo disponivel
```

### 9.3 Stress tests

- Crash de 2022 (Luna, FTX)
- Rally de 2021 (BTC $20k -> $69k)
- Lateral de 2023 (BTC $16k -> $30k)
- Correlacao quebrada por evento setorial

## 10. Vantagens e Desvantagens

### Vantagens
- Market-neutral (nao aposta em direcao, aposta em convergencia)
- Base estatistica solida (correlacao e z-score sao robustos)
- Funciona bem em mercados laterais (comuns em cripto)
- Multiplos sinais simultaneos (diversificacao)

### Desvantagens
- Falha em mercados em trending forte
- Correlacao pode quebrar por eventos idiossincaticos
- Custo de funding em shorts perpetuos
- Pode ter muitos sinais falsos em alta volatilidade

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Entropy (STRAT-04) | Alta | Entropy filtra regimes caoticos onde correlacao quebra |
| + Hurst Exponent | Alta | Hurst filtra trending vs mean-reverting |
| + Funding Rate (STRAT-07) | Media | Funding extremo pode causar descolamento |
| + Momentum (STRAT-06) | Baixa | Filosofias opostas (reversion vs trend) |

## 12. Referencias

- Elbasri/crypto-data-analysis: correlation dashboard com NetworkX
- Aroesler1/crypto_stat_arb: stat-arb com signed graphs + PCA
- MDPI Mathematics 12(18):2911: "Anti-Persistent Values of the Hurst Exponent Anticipate Mean Reversion in Pairs Trading"
- BIS Working Paper 955: "70-80% of retail day traders lose money" (contexto de risco)
