# Estrategia 07: VWAP Reversion

**ID:** STRAT-07
**Categoria:** Mean Reversion / Intraday
**Timeframe ideal:** 5m, 15m, 1h
**Horizonte:** Curto prazo (minutos a horas)
**Complexidade:** Baixa-Media

## 1. Conceito

VWAP (Volume Weighted Average Price) e o preco medio ponderado por volume. Instituicionais usam VWAP como benchmark de execucao: se eles compraram abaixo do VWAP, tiveram uma boa execucao. A estrategia de VWAP Reversion explora o fato de que o preco tende a reverter ao VWAP durante o dia.

### Intuicao

Quando o preco se descola mais de 2 desvios padrao do VWAP, ha uma alta probabilidade de reverter. A razao e que:
1. Instituicionais vendem quando o preco esta acima do VWAP (boa execucao)
2. Market makers fazem hedge quando o preco se descola
3. Algoritmos de execucao (TWAP, VWAP, POV) empurram o preco de volta ao VWAP
4. O VWAP e o "preco justo" do dia, e o preco oscila ao redor dele

### VWAP vs Bollinger Bands

```
Bollinger Bands:  SMA +/- 2 * std (desvio do SMA)
VWAP Bands:       VWAP +/- 2 * std_volume (desvio do VWAP)

VWAP e mais relevante que SMA porque:
  - Pondera por volume (niveis com mais volume importam mais)
  - E o benchmark institucional
  - Reseta diariamente (contexto intraday)
```

## 2. Fundamentacao Teorica

### 2.1 Calculo do VWAP

```
VWAP = sum(price * volume) / sum(volume)

Para uma janela rolling:
VWAP_rolling = sum(close[i] * volume[i] for i in window) / sum(volume[i] for i in window)

Para VWAP diario (session):
  Resetado a cada inicio de dia
  Acumula volume desde a abertura
```

### 2.2 Bandas de VWAP

```
Upper Band = VWAP + n * StdDev
Lower Band = VWAP - n * StdDev

StdDev = sqrt(sum(volume * (price - VWAP)^2) / sum(volume))

n = 1, 2, ou 3 desvios (similar a Bollinger Bands mas volume-weighted)
```

### 2.3 Anchored VWAP

VWAP ancorado em um evento especifico (nao apenas inicio do dia):

```
Anchored VWAP desde:
  - Inicio do dia (session VWAP)
  - Inicio da semana
  - Ultimo swing high/low
  - Evento de noticia (FOMC, CPI, etc.)
  - Liquidacao em massa

O VWAP ancorado em eventos importantes e um nivel de suporte/resistencia
mais forte que o VWAP diario.
```

### 2.4 VWAP como suporte/resistencia institucional

```
Acima do VWAP: compradores dominaram o dia (bullish bias)
Abaixo do VWAP: vendedores dominaram o dia (bearish bias)

Testes do VWAP:
  - Primeiro teste: alta probabilidade de reacao (80%+)
  - Segundo teste: media probabilidade (60%+)
  - Terceiro teste: baixa probabilidade (VWAP vai ceder)
```

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `vwap_type` | "session" | "session", "rolling", "anchored" | Tipo de VWAP |
| `rolling_window` | 20 | 10 a 50 | Janela para rolling VWAP |
| `band_std` | 2.0 | 1.5 a 3.0 | Desvios para bandas |
| `entry_std` | 2.0 | 1.5 a 3.0 | Desvio para entrada |
| `exit_std` | 0.5 | 0.0 a 1.0 | Desvio para saida (convergencia ao VWAP) |
| `stop_std` | 3.5 | 3.0 a 4.5 | Desvio para stop loss |
| `session_reset` | "00:00" | - | Hora de reset do session VWAP (UTC) |
| `min_distance_from_vwap` | 0.005 | 0.003 a 0.01 | Distancia minima do VWAP para entrar (0.5%) |
| `max_distance_from_vwap` | 0.05 | 0.03 a 0.08 | Distancia maxima (acima = anormal, nao entrar) |
| `trend_filter` | true | true, false | Filtrar sinais contra a tendencia do dia |

## 4. Sinais de Entrada

### 4.1 Long (preco abaixo do VWAP)

```
CONDICOES:
1. (VWAP - close) / VWAP > min_distance  (preco esta abaixo do VWAP)
2. (VWAP - close) / VWAP < max_distance  (nao tao longe que e anormal)
3. zscore = (close - VWAP) / vol_std < -entry_std  (2+ desvios abaixo)
4. Delta positivo (mais compras que vendas no candle)
5. Volume do candle > 1.5x volume medio

FILTRO DE TENDENCIA (opcional):
6. SE trend_filter: close do dia anterior acima do VWAP do dia anterior
   (bias de alta, reversion a favor da tendencia)

ENTRY: Long
STOP: abaixo do low do candle de entrada
TARGET: VWAP (preco justo)
```

### 4.2 Short (preco acima do VWAP)

```
CONDICOES:
1. (close - VWAP) / VWAP > min_distance
2. (close - VWAP) / VWAP < max_distance
3. zscore > +entry_std
4. Delta negativo
5. Volume > 1.5x medio

FILTRO:
6. SE trend_filter: close anterior abaixo do VWAP anterior

ENTRY: Short
STOP: acima do high do candle de entrada
TARGET: VWAP
```

### 4.3 VWAP Bounce (com confirmacao)

```
Long:
1. Preco aproxima do VWAP por baixo
2. Candle de reversao no VWAP (pin bar, engulfing)
3. Delta vira positivo
4. Entrar no fechamento do candle de confirmacao

Short:
1. Preco aproxima do VWAP por cima
2. Candle de reversao bearish no VWAP
3. Delta vira negativo
4. Entrar no fechamento
```

### 4.4 VWAP Breakout e Retest

```
Long:
1. Preco rompe o VWAP para cima (close acima do VWAP)
2. Preco retorna ao VWAP (pullback)
3. Candle de reversao bullish no VWAP (suporte confirmado)
4. Entrar long com target no Upper Band

Short:
1. Preco rompe o VWAP para baixo
2. Preco retorna ao VWAP
3. Candle bearish no VWAP
4. Entrar short com target na Lower Band
```

## 5. Sinais de Saida

### 5.1 Take Profit no VWAP

```
Long:
  SE close >= VWAP:
      FECHAR (preco voltou ao preco justo)

Short:
  SE close <= VWAP:
      FECHAR
```

### 5.2 Take Profit nas Bandas

```
Long (entrada na Lower Band):
  SE close >= VWAP:
      FECHAR 50%
  SE close >= Upper Band:
      FECHAR 100%

Short (entrada na Upper Band):
  SE close <= VWAP:
      FECHAR 50%
  SE close <= Lower Band:
      FECHAR 100%
```

### 5.3 Stop Loss

```
Long:
  SE zscore < -stop_std:
      FECHAR (continua caindo, VWAP perdeu relevancia)

Short:
  SE zscore > +stop_std:
      FECHAR
```

### 5.4 Saida por tempo

```
SE tempo_em_posicao > 4h:
    FECHAR (VWAP reversion e intraday, nao segurar overnight)
```

### 5.5 Saida por fim de sessao

```
SE horario > 23:00 UTC:
    FECHAR todas as posicoes
    RAZAO: VWAP vai resetar, contexto muda
```

## 6. Gestao de Risco

### 6.1 Position Sizing

```python
# Tamanho baseado na distancia ao VWAP
distance = abs(close - vwap) / vwap
# Quanto mais longe do VWAP, mais "esticado" e maior a reversao esperada
# Mas tambem mais arriscado (pode ser uma mudanca de direcao real)
size = base_risk / (distance * atr)
size = min(size, max_position_size)
```

### 6.2 Maximo de posicoes por sessao

```
max_trades_per_session = 5
SE trades_hoje >= max_trades_per_session:
    PARAR ate proximo dia
```

### 6.3 Filtro de volatilidade

```
SE volatilidade_intraday > 2x volatilidade_media:
    REDUZIR tamanho em 50%
    RAZAO: alta volatilidade = mais falsos sinais
```

## 7. Implementacao Tecnica

### 7.1 Session VWAP

```python
def compute_session_vwap(df: pd.DataFrame, reset_hour: int = 0) -> pd.DataFrame:
    """Compute session VWAP that resets daily."""
    df = df.copy()
    df["date"] = df.index.date
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["vp"] = df["typical_price"] * df["volume"]

    # Cumulative sum within each day
    df["cum_vp"] = df.groupby("date")["vp"].cumsum()
    df["cum_vol"] = df.groupby("date")["volume"].cumsum()
    df["vwap"] = df["cum_vp"] / df["cum_vol"]

    # VWAP standard deviation (volume-weighted)
    df["variance"] = df["volume"] * (df["typical_price"] - df["vwap"]) ** 2
    df["cum_variance"] = df.groupby("date")["variance"].cumsum()
    df["vwap_std"] = np.sqrt(df["cum_variance"] / df["cum_vol"])

    # Bands
    df["upper_band"] = df["vwap"] + 2 * df["vwap_std"]
    df["lower_band"] = df["vwap"] - 2 * df["vwap_std"]

    return df
```

### 7.2 Rolling VWAP

```python
def compute_rolling_vwap(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute rolling VWAP."""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    vp = typical_price * df["volume"]

    rolling_vp = vp.rolling(window).sum()
    rolling_vol = df["volume"].rolling(window).sum()
    vwap = rolling_vp / rolling_vol

    # Standard deviation
    variance = df["volume"] * (typical_price - vwap) ** 2
    rolling_var = variance.rolling(window).sum()
    vwap_std = np.sqrt(rolling_var / rolling_vol)

    return pd.DataFrame({
        "vwap": vwap,
        "upper_band": vwap + 2 * vwap_std,
        "lower_band": vwap - 2 * vwap_std,
        "zscore": (df["close"] - vwap) / vwap_std,
    }, index=df.index)
```

### 7.3 Anchored VWAP

```python
def compute_anchored_vwap(df: pd.DataFrame, anchor_date: pd.Timestamp) -> pd.Series:
    """Compute VWAP anchored at a specific date."""
    filtered = df[df.index >= anchor_date]
    typical_price = (filtered["high"] + filtered["low"] + filtered["close"]) / 3
    vp = typical_price * filtered["volume"]

    return vp.cumsum() / filtered["volume"].cumsum()
```

### 7.4 Sinal completo

```python
def vwap_reversion_signals(df: pd.DataFrame, params: dict) -> list:
    """Generate VWAP reversion signals."""
    vwap_df = compute_session_vwap(df, reset_hour=0)

    signals = []
    for i in range(len(vwap_df)):
        row = vwap_df.iloc[i]
        close = row["close"]
        vwap = row["vwap"]
        zscore = (close - vwap) / row["vwap_std"] if row["vwap_std"] > 0 else 0

        distance = abs(close - vwap) / vwap if vwap > 0 else 0

        # Filters
        if distance < params["min_distance_from_vwap"]:
            continue
        if distance > params["max_distance_from_vwap"]:
            continue

        # Entry signals
        if zscore < -params["entry_std"]:
            signals.append({
                "timestamp": vwap_df.index[i],
                "direction": "LONG",
                "price": close,
                "vwap": vwap,
                "zscore": zscore,
                "target": vwap,
            })
        elif zscore > params["entry_std"]:
            signals.append({
                "timestamp": vwap_df.index[i],
                "direction": "SHORT",
                "price": close,
                "vwap": vwap,
                "zscore": zscore,
                "target": vwap,
            })

    return signals
```

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 65%+ | 55% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 8% | < 12% |
| Profit factor | 2.0+ | 1.5 |
| Avg holding period | 30min a 4h | 15min a 8h |
| Trades por mes | 30-80 | 15+ |
| Avg R:R | 1.5+ | 1.0 |

## 9. Backtest: O que validar

### 9.1 Por horario do dia

```
00:00-06:00 UTC (Asia):    win rate esperado < 55% (baixo volume)
06:00-12:00 UTC (Europe):  win rate esperado > 60%
12:00-18:00 UTC (US):      win rate esperado > 65% (melhor janela)
18:00-00:00 UTC (close):   win rate esperado > 55%
```

### 9.2 Por distancia do VWAP

```
1-2 desvios:  win rate esperado > 70% (reversion frequente)
2-3 desvios:  win rate esperado > 60% (reversion maior, menos frequente)
3+ desvios:   win rate esperado < 50% (anormal, pode ser mudanca de direcao)
```

### 9.3 Validar reset do VWAP

```
Testar diferentes horas de reset:
  - 00:00 UTC (meia-noite)
  - 08:00 UTC (abertura Londres)
  - 13:30 UTC (abertura NY)

Validar qual horario de reset produz melhor Sharpe.
```

## 10. Vantagens e Desvantagens

### Vantagens
- Simples de implementar (VWAP e direto de calcular)
- Win rate alto (60-70% tipico)
- Benchmark institucional (VWAP e usado por grandes players)
- Funciona bem em intraday (horizonte curto e previsivel)
- Baixo custo (poucos trades por dia, saida rapida)

### Desvantagens
- So funciona intraday (VWAP reset diario)
- Sofre em dias de tendencia forte (preco nao volta ao VWAP)
- Pode ter muitos sinais falsos em alta volatilidade
- R:R tipicamente baixo (1:1 a 1.5:1, compensado por win rate alto)
- Nao funciona bem em finais de semana (liquidez reduzida)

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Volume Profile (STRAT-05) | Alta | POC e VWAP sao niveis relacionados |
| + Entropy (STRAT-04) | Alta | Entropy filtra dias caoticos |
| + Price Action (STRAT-02) | Media | Candle de confirmacao no VWAP |
| + Mean Reversion Correlation (STRAT-01) | Media | Mesma filosofia, escalas diferentes |

## 12. Referencias

- Snack-JPG/quantflow: VWAP methodology and rolling implementation
- Mattbusel/FinRL_DeepSeek_Crypto_Trading: VWAP deviation as feature
- mefai-dev/mefai-autotrade: VWAP-based entry/exit strategy
- TradeAlgo: "Mean Reversion at Key Levels" (VWAP as key level)
- DEXTools: "Day Trade Crypto Guide" (VWAP as execution benchmark)
