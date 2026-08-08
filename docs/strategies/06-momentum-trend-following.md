# Estrategia 06: Momentum e Trend Following

**ID:** STRAT-06
**Categoria:** Trend Following / Momentum
**Timeframe ideal:** 1h, 4h, 1d
**Horizonte:** Medio prazo (dias a semanas)
**Complexidade:** Media

## 1. Conceito

Momentum e a estrategia mais simples e robusta do trading quantitativo: comprar ativos que estao subindo e vender ativos que estao caindo. A ideia e que tendencias persistem devido a fatores comportamentais (herding, anchor bias) e institucionais (alocacao gradual, funding flows).

### Intuicao

"Buy high, sell higher." Em vez de tentar pegar o fundo (mean reversion), momentum entra apos a tendencia ja estar estabelecida e sai quando ela mostra sinais de exaustao. Parece contra-intuitivo mas tem evidencia empirica forte: em quase todos os mercados testados (acoes, commodities, forex, crypto), momentum gera excesso de retorno em janelas de 3-12 meses.

### Por que funciona em crypto

1. **Herding**: traders de varejo seguem o que esta subindo (FOMO)
2. **Funding flows**: ETFs e fundos alocam gradualmente, criando momentum persistente
3. **Liquidacoes**: shorts sendo liquidados amplificam movimentos de alta
4. **Narrativas setoriais**: AI season, DeFi summer, meme season duram semanas
5. **Listing effects**: listagem em novas exchanges cria momentum de curto prazo

## 2. Fundamentacao Teorica

### 2.1 Cross-Sectional Momentum

Ranquear ativos por retorno passado e comprar os melhores, vender os piores:

```
momentum_score = return(t-N, t)
N = periodo de formacao (ex: 90 dias)

Comprar top 20% (maior momentum)
Vender bottom 20% (menor momentum / mais negativo)
Rebalancear a cada M periodos (ex: 30 dias)
```

### 2.2 Time-Series Momentum (TSMOM)

Seguir a tendencia de cada ativo individualmente:

```
SE return(t-N, t) > 0:
    LONG (tendencia de alta)
SE return(t-N, t) < 0:
    SHORT (tendencia de baixa)
```

TSMOM e mais robusto que cross-sectional em mercados com poucos ativos (como crypto).

### 2.3 Indicadores de Momentum

| Indicador | Formula | Sinal |
|-----------|---------|-------|
| ROC (Rate of Change) | (close - close_N) / close_N | > 0 = alta |
| RSI | 100 - 100/(1 + avg_gain/avg_loss) | > 50 = alta, > 70 = overbought |
| MACD | EMA12 - EMA26 | Cruzamento com signal line |
| ADX | DI+ - DI- normalizado | > 25 = tendencia forte |
| Supertrend | ATR-based trend line | Preco acima = alta |
| EMA crossover | EMA_fast vs EMA_slow | Fast acima de slow = alta |

### 2.4 RSI Trend Strategy (estudo validado)

Estudo peer-reviewed (Sensors Journal, DOI: 10.3390/s23031664):
- RSI 50-100 trend strategy em 10 criptos (2018-2022)
- Retorno: 773.65% vs 275.22% buy-and-hold
- Drawdown 2022-2023: 41.40% vs 65.75% buy-and-hold
- **Win rate reportado: 77%**

### 2.5 Bollinger + RSI + MACD + Stochastic

Estudo com 77% de win rate reportado:
```
BUY:
  1. Close acima da Bollinger Band superior (1 std)
  2. RSI(9) > 50
  3. Stochastic %D > 45
  4. MACD line acima da signal line

EXIT:
  MACD cruza abaixo da signal line
```

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `formation_period` | 90 | 20 a 180 | Periodo de calculo do momentum (dias) |
| `holding_period` | 30 | 7 a 90 | Periodo de rebalanceamento (dias) |
| `tsmom_threshold` | 0.0 | -0.05 a 0.05 | Retorno minimo para considerar tendencia |
| `rsi_period` | 14 | 7 a 21 | Periodo do RSI |
| `rsi_trend_level` | 50 | 45 a 55 | Nivel do RSI que define trend (acima = alta) |
| `rsi_overbought` | 70 | 65 a 80 | Nivel overbought |
| `rsi_oversold` | 30 | 20 a 35 | Nivel oversold |
| `macd_fast` | 12 | 8 a 12 | EMA rapida do MACD |
| `macd_slow` | 26 | 20 a 26 | EMA lenta do MACD |
| `macd_signal` | 9 | 5 a 9 | EMA do signal line |
| `ema_fast` | 20 | 10 a 50 | EMA rapida para crossover |
| `ema_slow` | 50 | 50 a 200 | EMA lenta para crossover |
| `adx_period` | 14 | 10 a 20 | Periodo do ADX |
| `adx_threshold` | 25 | 20 a 30 | ADX minimo para confirmar tendencia |
| `atr_period` | 14 | 10 a 20 | Periodo do ATR |
| `atr_trailing_mult` | 3.0 | 2.0 a 5.0 | Multiplicador de ATR para trailing stop |

## 4. Sinais de Entrada

### 4.1 TSMOM Long (tendencia de alta)

```
CONDICOES (2 de 3 devem ser verdadeiras):
1. Return(90 dias) > 0 (momentum positivo)
2. RSI(14) > 50 (forca relativa positiva)
3. EMA20 > EMA50 (crossover de medias)

FILTRO ADX:
4. ADX(14) > 25 (tendencia forte, nao lateral)

ENTRY: Long no proximo open
STOP: 3 x ATR abaixo do entry (trailing)
```

### 4.2 TSMOM Short (tendencia de baixa)

```
CONDICOES (2 de 3):
1. Return(90 dias) < 0
2. RSI(14) < 50
3. EMA20 < EMA50

FILTRO:
4. ADX(14) > 25

ENTRY: Short no proximo open
STOP: 3 x ATR acima do entry (trailing)
```

### 4.3 RSI Trend Strategy (estudo validado)

```
LONG:
  SE RSI(14) cruza acima de 50:
      LONG
  EXIT:
  SE RSI(14) cruza abaixo de 50:
      FECHAR

SHORT:
  SE RSI(14) cruza abaixo de 50:
      SHORT
  EXIT:
  SE RSI(14) cruza acima de 50:
      FECHAR

FILTRO DE REGIME:
  SE Hurst > 0.55 (trending): operar
  SE Hurst < 0.45 (mean-reverting): NAO operar
```

### 4.4 Multi-Indicator Confirmation

```
LONG (todas devem ser verdadeiras):
1. Close acima da Bollinger Band superior (1 std)
2. RSI(9) > 50
3. MACD line > signal line
4. ADX > 25
5. Volume > 1.2x volume medio (20 periodos)

ENTRY: Long
STOP: Banda media das Bollinger Bands
TARGET: 2x risco ou trailing ATR
```

### 4.5 Cross-Sectional Momentum (portfolio)

```
A cada 30 dias:
1. Calcular momentum_score = return(90 dias) para cada ativo
2. Ranquear todos os ativos
3. Comprar top 20% (long)
4. Vender bottom 20% (short)
5. Equal-weight dentro de cada grupo
6. Rebalancear a cada 30 dias
```

## 5. Sinais de Saida

### 5.1 Trailing Stop (ATR)

```python
# Para Long:
trailing_stop = max(highest_close_since_entry - 3 * ATR, previous_trailing_stop)
SE close < trailing_stop:
    FECHAR

# Para Short:
trailing_stop = min(lowest_close_since_entry + 3 * ATR, previous_trailing_stop)
SE close > trailing_stop:
    FECHAR
```

### 5.2 Saida por crossover de medias

```
Long aberto:
  SE EMA20 cruza abaixo de EMA50:
      FECHAR (tendencia perdeu forca)

Short aberto:
  SE EMA20 cruza acima de EMA50:
      FECHAR
```

### 5.3 Saida por RSI reversal

```
Long aberto:
  SE RSI cruza abaixo de 50:
      FECHAR

Short aberto:
  SE RSI cruza acima de 50:
      FECHAR
```

### 5.4 Saida por exaustao

```
Long aberto:
  SE RSI > 85 (extreme overbought):
      FECHAR 50% (realizar parcial)
  SE RSI > 90:
      FECHAR 100% (exaustao extrema)
```

## 6. Gestao de Risco

### 6.1 Volatility Scaling

```python
# Tamanho da posicao inversamente proporcional a volatilidade
target_volatility = 0.15  # 15% annualizado
asset_volatility = returns.std() * np.sqrt(365)  # annualized
position_size = target_volatility / asset_volatility

# Limitar a max_position_size
position_size = min(position_size, max_position_size)
```

### 6.2 Stop por drawdown do ativo

```
SE drawdown_do_trade > 2 * ATR * entry_price:
    FECHAR (trade nao esta funcionando)
```

### 6.3 Maximo de posicoes simultaneas

```
max_long = 5
max_short = 5
max_total = 8 (considerando correlacao entre longs)
```

### 6.4 Filtro de correlacao entre posicoes

```
SE dois ativos long tem correlacao > 0.8:
    contar como 1 posicao (risco duplicado)
    reduzir tamanho de cada pela metade
```

## 7. Implementacao Tecnica

### 7.1 Indicadores (pandas/numpy)

```python
def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI using Wilder's smoothing."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Compute MACD line, signal line, and histogram."""
    ema_fast = close.ewm(span=fast).mean()
    ema_slow = close.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ADX (Average Directional Index)."""
    high, low, close = df["high"], df["low"], df["close"]

    plus_dm = (high.diff() - low.diff().abs()).clip(lower=0)
    minus_dm = (low.diff().abs() - high.diff()).clip(lower=0)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/period).mean()
    return adx


def compute_bollinger_bands(close: pd.Series, period: int = 20, std: float = 1.0):
    """Compute Bollinger Bands."""
    sma = close.rolling(period).mean()
    rolling_std = close.rolling(period).std()
    upper = sma + std * rolling_std
    lower = sma - std * rolling_std
    return upper, sma, lower
```

### 7.2 TSMOM Signal Generator

```python
def tsmom_signals(returns: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Generate Time-Series Momentum signals."""
    formation = params["formation_period"]
    threshold = params["tsmom_threshold"]

    # Momentum: cumulative return over formation period
    momentum = returns.rolling(formation).sum()

    # Hurst filter
    hurst = returns.rolling(100).apply(compute_hurst, raw=True)

    signals = pd.DataFrame(0, index=returns.index, columns=returns.columns)
    signals[momentum > threshold] = 1   # Long
    signals[momentum < -threshold] = -1  # Short

    # Apply Hurst filter: only trade when trending
    signals[hurst < 0.55] = 0  # Not trending enough

    return signals
```

### 7.3 Cross-Sectional Momentum

```python
def cross_sectional_momentum(returns: pd.DataFrame, params: dict) -> dict:
    """Cross-sectional momentum: long winners, short losers."""
    formation = params["formation_period"]
    holding = params["holding_period"]
    top_pct = 0.20  # Top 20%
    bottom_pct = 0.20  # Bottom 20%

    portfolio = {}
    rebalance_dates = returns.index[::holding]

    for date in rebalance_dates:
        # Calculate momentum score
        start_idx = max(0, returns.index.get_loc(date) - formation)
        period_returns = returns.iloc[start_idx:returns.index.get_loc(date)]
        momentum = period_returns.sum()

        # Rank
        ranked = momentum.rank(ascending=False)
        n_assets = len(ranked)
        top_n = int(n_assets * top_pct)
        bottom_n = int(n_assets * bottom_pct)

        longs = ranked[ranked <= top_n].index.tolist()
        shorts = ranked[ranked > n_assets - bottom_n].index.tolist()

        portfolio[date] = {"long": longs, "short": shorts}

    return portfolio
```

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 45%+ | 40% (compensado por R:R alto) |
| Sharpe ratio | 1.2+ | 0.8 |
| Max drawdown | < 25% | < 35% |
| Profit factor | 1.5+ | 1.2 |
| Avg holding period | 30-90 dias | 7-180 dias |
| Trades por ano | 10-30 | 5+ |
| CAGR | 30%+ | 15%+ |

**Nota:** Momentum tem win rate baixo mas R:R alto. Trades perdedores sao cortados rapido (trailing stop), trades vencedores correm por semanas.

## 9. Backtest: O que validar

### 9.1 Por regime de mercado

```
Bull market (2020-2021):  CAGR esperado > 80%
Bear market (2022):       Drawdown esperado < 40% (vs 65% buy-hold)
Lateral (2023):           Sharpe esperado > 0.5 (dificil para momentum)
```

### 9.2 Formacao vs Holding

```
Testar grid:
  formation: [20, 60, 90, 180] dias
  holding: [7, 30, 60, 90] dias

Encontrar melhor combinacao.
Validar: melhor combinacao nao muda muito entre IS e OOS.
SE muda muito: overfitting.
```

### 9.3 Impacto de custos

```
Momentum tem poucos trades (rebalanceamento mensal/trimestral).
Custo de transacao baixo impacta pouco.
Mas funding rate em shorts perpetuos pode ser significativo.
Validar: estrategia long-only vs long-short (short tem custo de funding).
```

## 10. Vantagens e Desvantagens

### Vantagens
- Estrategia mais documentada e validada academicamente
- Simples de implementar
- Funciona em multiplos mercados e periodos
- R:R alto (trailing stop deixa lucro correr)
- Baixa frequencia de trades (menos custo)
- Complementar a mean reversion (oposto filosofico)

### Desvantagens
- Drawdowns grandes em mudancas de regime (bull para bear)
- Win rate baixo (40-50%, psicologicamente dificil)
- Latencia grande entre sinal e confirmacao
- Sofre em mercados laterais (whipsaw)
- Crashes podem acontecer antes do stop ser atingido (gaps)

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Entropy (STRAT-04) | Alta | Entropy ativa momentum so em regime TRENDING |
| + Mean Reversion (STRAT-01) | Alta | Diversificacao filosofica (oposto) |
| + Funding Rate (STRAT-07) | Media | Funding positivo confirma momentum de alta |
| + Volume Profile (STRAT-05) | Media | Volume confirma breakouts de momentum |

## 12. Referencias

- Sensors Journal (PMC, DOI: 10.3390/s23031664): RSI 50-100 strategy, 773% return
- Spoted Crypto: "RSI + MACD + Bollinger = 77% backtested win rate"
- DutchAlgoTrading: "Bollinger RSI MACD Stochastic Strategy"
- CoinQuant: "Multi-Indicator Strategy: Combining RSI + MACD for Higher Win Rates"
- Moskowitz, Ooi, Pedersen (2012): "Time Series Momentum" (Journal of Financial Economics)
- Jegadeesh, Titman (1993): "Returns to Buying Winners and Selling Losers" (original momentum paper)
