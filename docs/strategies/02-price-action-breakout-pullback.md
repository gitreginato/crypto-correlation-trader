# Estrategia 02: Price Action (Breakout e Pullback)

**ID:** STRAT-02
**Categoria:** Technical Analysis / Discretionary-Systematic
**Timeframe ideal:** 15m, 1h, 4h
**Horizonte:** Curto prazo (horas a dias)
**Complexidade:** Media-Alta

## 1. Conceito

Price Action e a leitura direta do movimento do preco, sem indicadores lagging. A estrategia identifica niveis chave de suporte/resistencia, padroes de candlestick, e estrutura de mercado para entrar em breakouts (rompimentos) ou pullbacks (retrocessos a niveis chave).

### Intuicao

O preco ja contem toda a informacao disponivel. Em vez de usar RSI ou MACD (que sao derivados lagging do preco), lemos diretamente: onde o preco parou antes (suporte/resistencia), como ele se moveu (candlesticks), e se esta fazendo higher-highs ou lower-lows (estrutura de mercado).

### Duas variantes

1. **Breakout**: entrar quando o preco rompe um nivel chave com volume
2. **Pullback**: entrar quando o preco retorna a um nivel chave apos um impulso

## 2. Fundamentacao Teorica

### 2.1 Suporte e Resistencia

Niveis onde o preco encontrou pressao de compra (suporte) ou venda (resistencia) no passado. Sao zonas, nao linhas exatas. Metodos de deteccao:

- **Swing highs/lows**: picos e vales identificados por fractal analysis (n >= 2 candles de cada lado)
- **Volume Profile**: niveis com maior volume negociado (POC, Value Area)
- **Order Blocks**: ultimos candles de movimento contrario antes de um impulso forte
- **Previous day high/low**: niveis do dia anterior (liquidez institucional)

### 2.2 Estrutura de Mercado

```
Uptrend:    Higher Highs (HH) + Higher Lows (HL)
Downtrend:  Lower Highs (LH) + Lower Lows (LL)
Range:      Equals Highs (EH) + Equals Lows (EL)
```

Mudanca de estrutura (BOS, Break of Structure ou CHoCH, Change of Character) indica possivel reversao.

### 2.3 Candlesticks de Reversao

| Padrao | Sinal | Condicoes |
|--------|-------|-----------|
| Pin Bar (Hammer/Shooting Star) | Reversao | Wick >= 2x body, rejeicao de nivel |
| Engulfing | Reversao | Candle 2 engloba candle 1, no nivel chave |
| Inside Bar | Continuacao | Candle 2 dentro do range da candle 1, pos-impulso |
| Doji | Indecisao | Open ~= close, apos movimento longo |
| Fakey | Reversao | Inside bar seguido de falso breakout |

### 2.4 Multi-Timeframe Analysis

```
HTF (4H):    Direcao primaria (trend bias)
MTF (1H):    Estrutura intermediaria (niveis chave)
LTF (15m):   Entrada precisa (trigger candle)
```

Regra: so operar a favor da direcao do HTF, a menos que seja trade de reversao em nivel HTF.

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `htf_timeframe` | 4h | 1h, 4h, 1d | Timeframe superior para bias |
| `mtf_timeframe` | 1h | 30m, 1h, 2h | Timeframe intermediario |
| `ltf_timeframe` | 15m | 5m, 15m, 30m | Timeframe de entrada |
| `swing_lookback` | 5 | 3 a 10 | candles de cada lado para swing detection |
| `breakout_volume_mult` | 1.5 | 1.2 a 2.5 | Multiplicador de volume medio para validar breakout |
| `pullback_fib_levels` | [0.382, 0.5, 0.618] | - | Niveis de Fibonacci para pullback |
| `min_candle_body_ratio` | 0.6 | 0.5 a 0.8 | Body/wick minimo para candle de confirmacao |
| `atr_period` | 14 | 10 a 20 | Periodo do ATR para stop placement |
| `atr_mult_stop` | 1.5 | 1.0 a 3.0 | Multiplicador de ATR para stop loss |
| `rr_min` | 2.0 | 1.5 a 3.0 | Risk:Reward minimo para entrar |

## 4. Sinais de Entrada

### 4.1 Breakout Setup (Long)

```
CONDICOES (todas devem ser verdadeiras):
1. HTF em uptrend (HH + HL)
2. Preco consolida abaixo de resistencia no MTF (>= 5 candles)
3. Candle de breakout no LTF:
   a. Fecha acima da resistencia
   b. Volume >= 1.5x volume medio (20 periodos)
   c. Body >= 60% do range (candle forte, nao wick)
4. R:R >= 2.0 calculado com ATR stop
```

### 4.2 Breakout Setup (Short)

```
CONDICOES:
1. HTF em downtrend (LH + LL)
2. Preco consolida acima de suporte no MTF (>= 5 candles)
3. Candle de breakout no LTF:
   a. Fecha abaixo do suporte
   b. Volume >= 1.5x volume medio
   c. Body >= 60% do range
4. R:R >= 2.0
```

### 4.3 Pullback Setup (Long)

```
CONDICOES:
1. HTF em uptrend
2. Impulso recente rompeu resistencia (breakout confirmado)
3. Preco retorna a zona de breakout (resistencia virou suporte)
4. Candle de reversao no LTF na zona:
   a. Pin bar bullish (wick long embaixo)
   b. OU engulfing bullish
   c. OU inside bar + breakout na direcao do trend
5. Stop abaixo do swing low do pullback
6. R:R >= 2.0
```

### 4.4 Pullback Setup (Short)

```
CONDICOES:
1. HTF em downtrend
2. Impulso recente rompeu suporte
3. Preco retorna a zona de breakdown (suporte virou resistencia)
4. Candle de reversao bearish no LTF
5. Stop acima do swing high do pullback
6. R:R >= 2.0
```

## 5. Sinais de Saida

### 5.1 Take Profit

```
Opcao A: Target fixo no proximo nivel de suporte/resistencia (HTF)
Opcao B: Trailing stop com ATR (trail = 2x ATR desde o swing)
Opcao C: Escalar saida (50% no 1R, 30% no 2R, 20% trailing)
```

### 5.2 Stop Loss

```
Breakout Long:  stop = breakout_level - (atr_mult_stop * ATR)
Breakout Short: stop = breakout_level + (atr_mult_stop * ATR)
Pullback Long:  stop = swing_low - (atr_mult_stop * ATR)
Pullback Short: stop = swing_high + (atr_mult_stop * ATR)
```

### 5.3 Saida por invalidacao

```
Breakout Long:
    SE candle fecha abaixo do nivel rompido (false breakout):
    FECHAR imediatamente
Pullback Long:
    SE preco fecha abaixo do swing low do pullback:
    FECHAR imediatamente
```

## 6. Gestao de Risco

### 6.1 Position Sizing baseado em ATR

```python
risk_amount = portfolio_value * risk_per_trade  # 1% default
stop_distance = atr_mult_stop * current_atr
position_size = risk_amount / stop_distance
```

### 6.2 Filtro de sessao (crypto 24/7 mas com horarios de maior volume)

```
Kill zones (maior probabilidade):
- London open:    02:00-05:00 UTC
- New York open:  12:00-15:00 UTC
- London/NY overlap: 13:00-16:00 UTC

Evitar:
- Asian session:  00:00-02:00 UTC (baixo volume, breakouts falsos)
- Weekend:        Sabado e domingo (liquidez reduzida)
```

### 6.3 Max trades por dia

```
max_daily_trades = 3
SE trades_hoje >= max_daily_trades:
    PARAR de procurar novas entradas
```

## 7. Implementacao Tecnica

### 7.1 Deteccao de Swing Highs/Lows

```python
def detect_swings(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """Detect swing highs and lows using fractal analysis."""
    highs = df["high"]
    lows = df["low"]

    swing_high = pd.Series(False, index=df.index)
    swing_low = pd.Series(False, index=df.index)

    for i in range(lookback, len(df) - lookback):
        # Swing high: highest of 2*lookback+1 window
        if highs.iloc[i] == highs.iloc[i-lookback:i+lookback+1].max():
            swing_high.iloc[i] = True
        # Swing low: lowest of window
        if lows.iloc[i] == lows.iloc[i-lookback:i+lookback+1].min():
            swing_low.iloc[i] = True

    df["swing_high"] = swing_high
    df["swing_low"] = swing_low
    return df
```

### 7.2 Deteccao de Candlestick Patterns

```python
def detect_pin_bar(df: pd.DataFrame) -> pd.Series:
    """Detect pin bars (hammer/shooting star)."""
    body = abs(df["close"] - df["open"])
    range_total = df["high"] - df["low"]
    upper_wick = df["high"] - df[["close", "open"]].max(axis=1)
    lower_wick = df[["close", "open"]].min(axis=1) - df["low"]

    is_hammer = (lower_wick >= 2 * body) & (upper_wick <= body * 0.5)
    is_shooting = (upper_wick >= 2 * body) & (lower_wick <= body * 0.5)

    return pd.Series(
        np.where(is_hammer, 1, np.where(is_shooting, -1, 0)),
        index=df.index,
        name="pin_bar",
    )

def detect_engulfing(df: pd.DataFrame) -> pd.Series:
    """Detect bullish/bearish engulfing patterns."""
    prev_body = abs(df["close"].shift(1) - df["open"].shift(1))
    curr_body = abs(df["close"] - df["open"])

    bullish_engulf = (
        (df["close"].shift(1) < df["open"].shift(1))  # prev red
        & (df["close"] > df["open"])                  # curr green
        & (df["close"] >= df["open"].shift(1))        # engulfs prev open
        & (df["open"] <= df["close"].shift(1))        # engulfs prev close
    )

    bearish_engulf = (
        (df["close"].shift(1) > df["open"].shift(1))  # prev green
        & (df["close"] < df["open"])                  # curr red
        & (df["close"] <= df["open"].shift(1))
        & (df["open"] >= df["close"].shift(1))
    )

    return pd.Series(
        np.where(bullish_engulf, 1, np.where(bearish_engulf, -1, 0)),
        index=df.index,
        name="engulfing",
    )
```

### 7.3 Deteccao de estrutura de mercado (BOS/CHoCH)

```python
def detect_market_structure(df: pd.DataFrame, swings: pd.DataFrame) -> dict:
    """Detect Break of Structure (BOS) and Change of Character (CHoCH)."""
    swing_highs = df[df["swing_high"]]["high"].values
    swing_lows = df[df["swing_low"]]["low"].values

    current_high = swing_highs[-1] if len(swing_highs) > 0 else None
    current_low = swing_lows[-1] if len(swing_lows) > 0 else None
    prev_high = swing_highs[-2] if len(swing_highs) > 1 else None
    prev_low = swing_lows[-2] if len(swing_lows) > 1 else None

    structure = {
        "trend": "unknown",
        "bos": False,
        "choch": False,
        "direction": None,
    }

    if prev_high and prev_low and current_high and current_low:
        if current_high > prev_high and current_low > prev_low:
            structure["trend"] = "uptrend"
        elif current_high < prev_high and current_low < prev_low:
            structure["trend"] = "downtrend"
        else:
            structure["trend"] = "range"

        # BOS: price breaks previous swing in trend direction
        if structure["trend"] == "uptrend" and df["close"].iloc[-1] > prev_high:
            structure["bos"] = True
            structure["direction"] = "bullish"
        elif structure["trend"] == "downtrend" and df["close"].iloc[-1] < prev_low:
            structure["bos"] = True
            structure["direction"] = "bearish"

    return structure
```

### 7.4 Bibliotecas uteis

- `pymarket-structure` (fortunato): 67 colunas de market structure prontas
- `price-action-lib` (tonylyliu): 95+ colunas de price action analysis
- Implementacao propria para controle total

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 50%+ | 45% (compensado por R:R alto) |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 12% | < 20% |
| Profit factor | 1.8+ | 1.3 |
| Avg R:R | 2.0+ | 1.5 |
| Trades por mes | 8-20 | 4+ |

## 9. Backtest: O que validar

### 9.1 Por regime de mercado

```
Bull market:  breakouts longs devem ter win rate > 55%
Bear market:  breakouts shorts devem ter win rate > 55%
Range market: pullbacks devem ter win rate > 60%
```

### 9.2 Por sessao

```
London kill zone:  win rate esperado > 55%
NY kill zone:      win rate esperado > 55%
Asian session:     win rate esperado < 45% (evitar)
```

### 9.3 Falsos breakouts

Medir a taxa de false breakouts (preco rompe e volta no mesmo candle). Se > 40%, aumentar `breakout_volume_mult` ou adicionar filtro de close confirmation.

## 10. Vantagens e Desvantagens

### Vantagens
- Nao depende de indicadores lagging
- Funciona em qualquer mercado liquido
- Entradas em niveis logicos (nao aleatorias)
- Stop placement baseado em estrutura (nao arbitrario)

### Desvantagens
- Subjetividade na identificacao de niveis (requer regras estritas)
- Falsos breakouts sao comuns em crypto
- Performance depende muito do timeframe
- Dificil de automatizar 100% (padroes de candle tem nuances)

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Volume Profile (STRAT-05) | Alta | Volume Profile confirma niveis de suporte/resistencia |
| + Liquidity Sweep (STRAT-08) | Alta | Sweep identifica onde stops estao antes do breakout |
| + Momentum (STRAT-06) | Media | Momentum confirma forca do breakout |
| + Entropy (STRAT-04) | Media | Entropy filtra regimes caoticos |

## 12. Referencias

- Colibri Trader: "Day Trading Crypto: Master a Proven Price Action Strategy"
- DEXTools: "How to Day Trade Crypto: Complete Strategy and Risk Management Guide"
- fortunato/pymarket-structure: Python library for market structure analysis
- tonylyliu/price-action-lib: 95+ columns of price action analysis
- ICT killzone: kill zone timing for crypto
