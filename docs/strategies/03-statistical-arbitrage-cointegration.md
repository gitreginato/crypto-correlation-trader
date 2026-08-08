# Estrategia 03: Statistical Arbitrage (Cointegracao)

**ID:** STRAT-03
**Categoria:** Statistical / Relative Value
**Timeframe ideal:** 5m, 15m, 1h
**Horizonte:** Curto prazo (minutos a horas)
**Complexidade:** Alta

## 1. Conceito

Statistical Arbitrage (StatArb) identifica pares de ativos **cointegrados**, ou seja, que mantem uma relacao de equilibrio de longo prazo mesmo que individualmente sejam nao-estacionarios. Quando o spread entre os dois ativos se descola significativamente desse equilibrio, abre-se posicao apostando na convergencia.

### Diferenca crucial vs Mean Reversion por Correlacao (STRAT-01)

| Aspecto | Correlacao (STRAT-01) | Cointegracao (STRAT-03) |
|---------|----------------------|------------------------|
| O que mede | Movimento conjunto (direcao) | Equilibrio de longo prazo (nivel) |
| Numero de ativos | 1 vs cluster (3+) | 1 vs 1 (par) |
| Metrica | Z-score do descolamento | Z-score do spread com hedge ratio |
| Teste estatistico | Correlacao de Pearson | ADF (Augmented Dickey-Fuller) |
| Hedge ratio | Nao usa | OLS ou Kalman Filter |
| Tempo em posicao | Horas a dias | Minutos a horas |

### Intuicao

BTC e ETH podem ter correlacao 0.85, mas isso so diz que sobem/descem juntos. Cointegracao diz mais: existe uma combinacao linear `spread = BTC - beta * ETH` que e estacionaria (reverte a uma media fixa). Isso permite um trade mais preciso porque voce sabe o hedge ratio exato.

## 2. Fundamentacao Teorica

### 2.1 Cointegracao (Engle-Granger)

Dois ativos `Y` e `X` sao cointegrados se:
1. Ambos sao I(1) (integrated of order 1, ou seja, random walk)
2. Existe um `beta` tal que `spread = Y - beta * X` e I(0) (estacionario)

**Teste ADF (Augmented Dickey-Fuller):**
```
H0: spread tem unit root (nao estacionario, nao cointegrados)
H1: spread e estacionario (cointegrados)

SE p-value < 0.05: REJEITAR H0, par e cointegrado
```

### 2.2 Hedge Ratio (OLS)

```python
# Regressao: Y = alpha + beta * X + epsilon
# beta = hedge ratio
# epsilon = spread (residuo)

from sklearn.linear_model import LinearRegression

model = LinearRegression()
model.fit(X.values.reshape(-1, 1), Y.values)
beta = model.coef_[0]
alpha = model.intercept_
spread = Y - beta * X - alpha
```

### 2.3 Kalman Filter para Hedge Ratio dinamico

O hedge ratio nao e constante. Mudancas de regime, narrativas setoriais e eventos fazem o relacionamento evoluir. Kalman Filter atualiza o beta a cada tick:

```python
from pykalman import KalmanFilter

kf = KalmanFilter(
    transition_matrices=[1],
    observation_matrices=X.values.reshape(-1, 1, 1),
    observation_offsets=Y.values.reshape(-1, 1),
    initial_state_mean=1.0,
    initial_state_covariance=1.0,
    observation_covariance=1.0,
    transition_covariance=0.01,
)
betas, _ = kf.filter(Y.values)
```

### 2.4 Half-Life of Mean Reversion

Quanto tempo o spread leva para reverter a metade do descolamento:

```python
from sklearn.linear_model import LinearRegression

spread_lag = spread.shift(1).dropna()
spread_diff = spread.diff().dropna()
spread_lag, spread_diff = spread_lag.align(spread_diff)

model = LinearRegression()
model.fit(spread_lag.values.reshape(-1, 1), spread_diff.values)
half_life = -np.log(2) / model.coef_[0]
```

**Interpretacao:**
- Half-life < 5 periodos: reversao rapida, ideal para scalping
- Half-life 5-30: reversao media, bom para day trade
- Half-life > 30: reversao lenta, custos podem comer o lucro
- Half-life < 0 ou > 200: par provavelmente nao e cointegrado

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `adf_pvalue_threshold` | 0.05 | 0.01 a 0.10 | p-value maximo para aceitar cointegracao |
| `lookback_window` | 100 | 50 a 500 | Janela para calcular cointegracao e hedge ratio |
| `zscore_window` | 20 | 10 a 60 | Janela para z-score do spread |
| `entry_zscore` | 2.0 | 1.5 a 3.0 | Z-score para abrir |
| `exit_zscore` | 0.0 | -0.5 a 0.5 | Z-score para fechar (convergencia) |
| `stop_zscore` | 4.0 | 3.5 a 5.0 | Z-score para stop |
| `min_half_life` | 1 | 0.5 a 5 | Half-life minimo (periodos) |
| `max_half_life` | 50 | 30 a 100 | Half-life maximo |
| `hedge_ratio_method` | "ols" | "ols", "kalman" | Metodo de calculo do hedge ratio |
| `rebalance_frequency` | 24 | 4 a 96 | Re-calcular cointegracao a cada N periodos |

## 4. Selecao de Pares

### 4.1 Pipeline de selecao

```
1. Universo: 10-30 ativos USDT de alta liquidez
2. Para cada par (A, B) no universo:
   a. Baixar dados dos ultimos N periodos
   b. Calcular correlacao: se < 0.5, descartar (nao vale o custo)
   c. Rodar OLS: spread = A - beta * B
   d. Rodar ADF no spread: se p-value > 0.05, descartar
   e. Calcular half-life: se < 1 ou > 50, descartar
   f. Calcular Hurst exponent do spread: se > 0.5, descartar (trending)
3. Ranquear pares sobreviventes por:
   - Sharpe ratio esperado (baseado em half-life e volatilidade)
   - Estabilidade da cointegracao (p-value mais baixo = melhor)
4. Selecionar top N pares para operar
```

### 4.2 Filtros adicionais

```python
def is_pair_tradeable(asset_a: str, asset_b: str, spread: pd.Series) -> bool:
    # 1. ADF test
    adf_result = adfuller(spread.dropna())
    if adf_result[1] > 0.05:  # p-value
        return False

    # 2. Half-life
    hl = calculate_half_life(spread)
    if hl < 1 or hl > 50:
        return False

    # 3. Hurst exponent (spread deve ser mean-reverting)
    hurst = calculate_hurst(spread)
    if hurst > 0.5:
        return False

    # 4. Volume minimo (liquidez)
    if volume_a < min_volume or volume_b < min_volume:
        return False

    # 5. Correlacao minima
    if correlation(a_returns, b_returns) < 0.5:
        return False

    return True
```

## 5. Sinais de Entrada

### 5.1 Long Spread (A subperformou, B sobreperformou)

```
SE z_score(spread) < -entry_zscore:
    LONG asset A, SHORT asset B (com hedge ratio beta)
    APOSTA: spread vai aumentar (A vai subir relativo a B)
```

### 5.2 Short Spread (A sobreperformou, B subperformou)

```
SE z_score(spread) > +entry_zscore:
    SHORT asset A, LONG asset B (com hedge ratio beta)
    APOSTA: spread vai diminuir (A vai cair relativo a B)
```

### 5.3 Filtro de Hurst Exponent

```
SE Hurst(spread) < 0.45:
    OPERAR (spread e mean-reverting, ideal)
SE 0.45 <= Hurst(spread) <= 0.55:
    NAO OPERAR (spread em random walk, sem edge)
SE Hurst(spread) > 0.55:
    NAO OPERAR (spread em trending, reversion vai falhar)
```

## 6. Sinais de Saida

### 6.1 Take Profit (convergencia ao equilibrio)

```
SE |z_score(spread)| < exit_zscore:
    FECHAR ambas as pernas
```

### 6.2 Stop Loss (divergencia continua)

```
SE |z_score(spread)| > stop_zscore:
    FECHAR ambas as pernas
    HIPOTESE INVALIDA: cointegracao quebrou
```

### 6.3 Saida por tempo (max holding period)

```
SE tempo_em_posicao > 3 * half_life:
    FECHAR posicao
    RAZAO: se nao convergiu em 3 half-lives, algo mudou
```

### 6.4 Saida por quebra de cointegracao

```
SE ADF p-value do spread rolling > 0.10:
    FECHAR posicao
    RAZAO: par nao e mais cointegrado
```

## 7. Gestao de Risco

### 7.1 Position Sizing (delta-neutral)

```python
# Valor total da posicao = 2 * risk_amount (uma perna long, uma short)
# Cada perna recebe risk_amount

risk_amount = portfolio_value * risk_per_trade  # 1% default
dollar_volatility_a = atr_a * price_a
dollar_volatility_b = atr_b * price_b

# Ajustar por hedge ratio para delta-neutral
size_a = risk_amount / dollar_volatility_a
size_b = (risk_amount * beta) / dollar_volatility_b
```

### 7.2 Gestao de risco entre pares

```
max_pairs_concurrent = 5
max_correlation_between_pairs = 0.7
SE dois pares tem correlacao > 0.7:
    contar como 1 posicao (risco nao independente)
```

### 7.3 Kill switch por drawdown

```
SE drawdown > 10%:
    PAUSAR por 24h
    Re-testar cointegracao de todos os pares
SE drawdown > 20%:
    PARAR
    Revisao manual
```

### 7.4 Custo de funding (perpetuos)

```
SE ambas as pernas sao em perpetuos:
    funding_cost = funding_rate_long + funding_rate_short
    SE funding_cost > expected_profit:
        NAO ENTRAR (custo come o lucro)
```

## 8. Implementacao Tecnica

### 8.1 Modulos necessarios

```python
from statsmodels.tsa.stattools import adfuller, coint
from sklearn.linear_model import LinearRegression
# Opcional: from pykalman import KalmanFilter
# Opcional: from hurst import compute_hurst
```

### 8.2 Pseudocodigo completo

```python
def stat_arb_pipeline(returns: pd.DataFrame, prices: pd.DataFrame, params: dict):
    # 1. Selecao de pares
    pairs = select_cointegrated_pairs(prices, params)

    # 2. Para cada par, monitorar spread
    signals = []
    for (asset_a, asset_b, beta) in pairs:
        spread = prices[asset_a] - beta * prices[asset_b]
        zscore = rolling_zscore(spread, params["zscore_window"])

        # Filtro de regime
        hurst = compute_hurst(spread.tail(100))
        if hurst > 0.55:
            continue

        # Sinal
        current_z = zscore.iloc[-1]
        if current_z < -params["entry_zscore"]:
            signals.append(Signal(
                asset=asset_a, direction="LONG",
                hedge_asset=asset_b, hedge_direction="SHORT",
                hedge_ratio=beta,
                confidence=abs(current_z),
            ))
        elif current_z > params["entry_zscore"]:
            signals.append(Signal(
                asset=asset_a, direction="SHORT",
                hedge_asset=asset_b, hedge_direction="LONG",
                hedge_ratio=beta,
                confidence=abs(current_z),
            ))

    return signals


def select_cointegrated_pairs(prices: pd.DataFrame, params: dict) -> list:
    """Selecionar pares cointegrados do universo."""
    assets = prices.columns
    pairs = []

    for i in range(len(assets)):
        for j in range(i + 1, len(assets)):
            a, b = assets[i], assets[j]

            # Correlacao pre-filtro
            corr = prices[a].pct_change().corr(prices[b].pct_change())
            if corr < 0.5:
                continue

            # OLS hedge ratio
            window = prices.tail(params["lookback_window"])
            model = LinearRegression()
            model.fit(window[b].values.reshape(-1, 1), window[a].values)
            beta = model.coef_[0]
            spread = window[a] - beta * window[b]

            # ADF test
            adf_result = adfuller(spread.dropna())
            if adf_result[1] > params["adf_pvalue_threshold"]:
                continue

            # Half-life
            hl = calculate_half_life(spread)
            if hl < params["min_half_life"] or hl > params["max_half_life"]:
                continue

            # Hurst
            hurst = compute_hurst(spread)
            if hurst > 0.5:
                continue

            pairs.append((a, b, beta, adf_result[1], hl, hurst))

    # Ranquear por p-value (menor = mais cointegrado)
    pairs.sort(key=lambda x: x[3])
    return [(a, b, beta) for a, b, beta, _, _, _ in pairs[:params["max_pairs"]]]
```

## 9. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 65%+ | 55% |
| Sharpe ratio | 2.0+ | 1.5 |
| Max drawdown | < 8% | < 12% |
| Profit factor | 2.5+ | 1.8 |
| Avg holding period | < 3 * half-life | < 5 * half-life |
| Trades por mes | 15-40 | 8+ |
| Custo de funding | < 20% do lucro | < 30% |

## 10. Backtest: O que validar

### 10.1 Estabilidade temporal da cointegracao

```
Para cada par:
  - Dividir dados em 6 janelas de 2 meses
  - Rodar ADF em cada janela
  - Validar: par deve ser cointegrado em >= 4 de 6 janelas (67%)
  - Se cointegracao aparece e desaparece, par nao e confiavel
```

### 10.2 Sensibilidade a parametros

```
Rodar backtest com:
  - entry_zscore: 1.5, 2.0, 2.5, 3.0
  - zscore_window: 10, 20, 40, 60
  - lookback: 50, 100, 200, 500
Validar: Sharpe nao deve variar mais que 30% entre parametros proximos
SE variar muito: overfitting
```

### 10.3 Impacto de custos

```
Rodar backtest com:
  - 0% fees (teorico)
  - 0.1% fees (Binance spot)
  - 0.04% fees (Binance futures maker)
  - 0.075% fees (Binance futures taker)
Validar: estrategia ainda lucrativa com 0.1% fees
```

## 11. Vantagens e Desvantagens

### Vantagens
- Market-neutral (delta-zero, nao aposta em direcao)
- Base estatistica rigorosa (ADF, OLS, Hurst)
- Entradas e saidas bem definidas (z-score)
- Multiplos pares simultaneos (diversificacao)
- Sharpe ratio tipicamente alto (1.5-3.0)

### Desvantagens
- Cointegracao pode quebrar (regime change)
- Custo de funding em perpetuos (2 pernas)
- Requer dados de alta qualidade (sem gaps)
- Complexidade de implementacao (Kalman, ADF, half-life)
- Pares podem deixar de ser cointegrados sem aviso

## 12. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Mean Reversion Correlation (STRAT-01) | Alta | Mesma filosofia, escalas diferentes |
| + Entropy (STRAT-04) | Alta | Entropy detecta quebra de cointegracao |
| + Funding Rate (STRAT-07) | Media | Funding extremo pode causar descolamento |
| + Liquidity Sweep (STRAT-08) | Baixa | Diferentes horizontes temporais |

## 13. Referencias

- ssanin82/strat-test-cointegration: Engle-Granger pair selection, OLS hedge ratio, z-score
- abailey81/Crypto-Statistical-Arbitrage: Sharpe 1.61 (altcoin) / 5.81 (BTC futures)
- ApexQuant-Dev/binance-correlation-stat-arb: Z-Score arbitrage on Binance Futures
- MarkRobertson67/Quant_Capstone: Cointegration-based pairs trading on Kraken
- Amdev-5/crypto-pairs-trading-ai: Multi-agent + 4 concurrent strategies
- Jotanune/CryptoGuardian: SMC + Pairs Trading dual engine, ADF + Hurst + half-life filtering
- MDPI Mathematics: "Anti-Persistent Values of the Hurst Exponent Anticipate Mean Reversion in Pairs Trading"
