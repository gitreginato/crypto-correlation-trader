# Estrategia 09: Liquidity Sweep (ICT / Smart Money Concepts)

**ID:** STRAT-09
**Categoria:** Institutional / Smart Money
**Timeframe ideal:** 15m, 1h, 4h
**Horizonte:** Curto prazo (horas)
**Complexidade:** Alta

## 1. Conceito

Liquidity Sweep e a estrategia baseada em ICT (Inner Circle Trader) / Smart Money Concepts (SMC). A ideia central e que o mercado busca ativamente clusters de stop-loss de traders de varejo para "varrer" essa liquidez antes de reverter na direcao oposta. A estrategia entra apos o sweep, na direcao da reversao.

### Intuicao

Toda vez que um trader de varejo abre uma posicao, ele coloca um stop-loss. Esses stops se acumulam em niveis previsiveis: maxima/minima do dia anterior, numeros redondos, igual highs/lows. O "dinheiro inteligente" (instituicoes, algoritmos) empurra o preco ate esses niveis para disparar os stops, que geram volume para que eles possam entrar com tamanho grande na direcao oposta.

### Padrao AMD (Accumulation, Manipulation, Distribution)

```
1. ACCUMULATION: preco consolida em um range (acumula stops nos extremos)
2. MANIPULATION: preco rompe o range (varre os stops) mas nao sustenta
3. DISTRIBUTION: preco reverte e vai na direcao oposta (movimento real)

A estrategia entra na fase 3 (Distribution), apos confirmar que a fase 2
(Manipulation/Sweep) aconteceu.
```

### Por que funciona em crypto

1. Order books de crypto sao mais finos que equities (sweeps sao visiveis)
2. Funding rates extremos criam liquidez previsivel (liquidacoes)
3. Equal highs/lows em BTC sao varridos violentamente
4. Numeros redondos (50k, 60k, 100k) sao os maiores pools de stops
5. 24/7 mas kill zones de Londres/NY ainda aplicam

## 2. Fundamentacao Teorica

### 2.1 Buy-Side e Sell-Side Liquidity

```
Buy-Side Liquidity (BSL):
  - Stop-losses de traders que estao SHORT
  - Localizados ACIMA do preco atual
  - Maxima do dia anterior, equal highs, numeros redondos
  - Sweep do BSL = preco sobe ate os stops e reverte para baixo

Sell-Side Liquidity (SSL):
  - Stop-losses de traders que estao LONG
  - Localizados ABAIXO do preco atual
  - Minima do dia anterior, equal lows, numeros redondos
  - Sweep do SSL = preco cai ate os stops e reverte para cima
```

### 2.2 Niveis de Liquidez

| Nivel | Tipo | Forca |
|-------|------|-------|
| Previous Day High (PDH) | BSL | Muito forte |
| Previous Day Low (PDL) | SSL | Muito forte |
| Previous Week High (PWH) | BSL | Extremo |
| Previous Week Low (PWL) | SSL | Extremo |
| Equal Highs (EQH) | BSL | Forte (stops acumulados) |
| Equal Lows (EQL) | SSL | Forte |
| Round Numbers (50k, 100k) | Ambos | Muito forte em crypto |
| Asian Session High/Low | Ambos | Medio |
| London Session High/Low | Ambos | Forte |
| Order Block | Ambos | Forte (ultima ordem institucional) |

### 2.3 Fair Value Gap (FVG)

Um gap de valor justo ocorre quando ha um movimento direcional forte que deixa um "buraco" no preco:

```
Bullish FVG:
  Candle[i-1].high < Candle[i+1].low
  (gap entre a maxima da candle anterior e a minima da proxima)

Bearish FVG:
  Candle[i-1].low > Candle[i+1].high
  (gap entre a minima anterior e a maxima da proxima)

O preco costuma retornar para "preencher" o FVG antes de continuar.
FVGs sao zonas de entrada de alta probabilidade.
```

### 2.4 Order Block (OB)

```
Bullish Order Block:
  Ultima candle bearish antes de um movimento de alta forte
  (a instituicao vendeu aqui antes de comprar forte)

Bearish Order Block:
  Ultima candle bullish antes de um movimento de baixa forte
  (a instituicao comprou aqui antes de vender forte)

O preco costuma retornar ao OB antes de continuar na direcao do impulso.
```

### 2.5 Market Structure Shift (MSS / CHoCH)

```
Bullish MSS (apos sweep de SSL):
  1. Preco faz lower-low (sweep do SSL)
  2. Preco reverte e rompe o ultimo lower-high (quebra de estrutura)
  3. Confirmacao de que o sweep foi manipulacao, nao continuacao

Bearish MSS (apos sweep de BSL):
  1. Preco faz higher-high (sweep do BSL)
  2. Preco reverte e rompe o ultimo higher-low
  3. Confirmacao de reversao
```

### 2.6 Kill Zones (crypto)

```
Asian Session:    00:00-06:00 UTC (acumulacao, range formado)
London Open:      07:00-10:00 UTC (manipulation + distribution)
NY Open:          12:00-15:00 UTC (manipulation + distribution)
London/NY Overlap:13:00-16:00 UTC (maior volume do dia)

Estrategia: formar range na Asian, operar sweep na London/NY.
```

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `range_lookback` | 8 | 4 a 24 | Candles para definir range de acumulacao |
| `range_tolerance` | 0.002 | 0.001 a 0.005 | Tolerancia para equal highs/lows (0.2%) |
| `sweep_wick_ratio` | 0.6 | 0.5 a 0.8 | Min wick/body ratio para confirmar sweep |
| `displacement_atr_mult` | 1.5 | 1.0 a 3.0 | ATR multiplicador para candle de deslocamento |
| `fvg_min_size` | 0.001 | 0.0005 a 0.003 | Tamanho minimo do FVG (0.1% do preco) |
| `ob_max_candles_back` | 10 | 5 a 20 | Max candles para tras procurar Order Block |
| `mss_confirm_candles` | 3 | 2 a 5 | Candles para confirmar MSS |
| `kill_zone_only` | true | true, false | Operar apenas em kill zones |
| `london_start` | "07:00" | - | Inicio London (UTC) |
| `ny_start` | "12:00" | - | Inicio NY (UTC) |
| `asian_start` | "00:00" | - | Inicio Asian (UTC) |
| `min_rr` | 2.5 | 2.0 a 4.0 | R:R minimo |
| `atr_period` | 14 | 10 a 20 | Periodo do ATR |
| `atr_stop_mult` | 1.0 | 0.5 a 2.0 | ATR multiplicador para stop |

## 4. Sinais de Entrada

### 4.1 Asian Range Sweep (Long)

```
FASE 1 - IDENTIFICAR RANGE (Asian Session 00:00-06:00 UTC):
  - Identificar maxima e minima do range Asian
  - Range deve ter >= 4 candles (consolidacao real)
  - Anotar Asian High e Asian Low

FASE 2 - SWEEP (London ou NY):
  - Preco cai abaixo do Asian Low (sweep do SSL)
  - Wick inferior >= 60% do range da candle (rejeicao)
  - Close da candle volta acima do Asian Low
  - Volume no sweep > 1.5x volume medio

FASE 3 - DESLOCAMENTO (Displacement):
  - Candle seguinte e bullish e forte
  - Body >= 60% do range
  - Range da candle >= 1.5x ATR (deslocamento real)
  - Rompe o ultimo swing high (MSS confirmado)

FASE 4 - ENTRY (no FVG ou OB):
  - Identificar FVG bullish criado pelo deslocamento
  - OU identificar Order Block bullish
  - Entrar long quando preco retornar ao FVG/OB
  - Stop: abaixo do low do sweep
  - Target: Asian High (oposto do range)
```

### 4.2 Asian Range Sweep (Short)

```
FASE 1: Range Asian identico
FASE 2 - SWEEP:
  - Preco sobe acima do Asian High (sweep do BSL)
  - Wick superior >= 60% do range
  - Close volta abaixo do Asian High
  - Volume > 1.5x medio

FASE 3 - DESLOCAMENTO:
  - Candle seguinte bearish e forte
  - Body >= 60%, range >= 1.5x ATR
  - Rompe ultimo swing low (MSS bearish)

FASE 4 - ENTRY:
  - FVG bearish ou OB bearish
  - Entrar short no retorno ao FVG/OB
  - Stop: acima do high do sweep
  - Target: Asian Low
```

### 4.3 Previous Day High/Low Sweep

```
Long (sweep do PDL):
1. Preco cai abaixo do Previous Day Low
2. Wick longa embaixo (rejeicao do nivel)
3. Close volta acima do PDL
4. Proxima candle: deslocamento bullish (body forte, >= 1.5x ATR)
5. MSS: rompe ultimo swing high
6. Entrar no FVG/OB bullish
7. Stop: abaixo do low do sweep
8. Target: PDL oposto ou PWH

Short (sweep do PDH):
1. Preco sobe acima do Previous Day High
2. Wick longa em cima
3. Close volta abaixo do PDH
4. Deslocamento bearish
5. MSS: rompe ultimo swing low
6. Entrar no FVG/OB bearish
7. Stop: acima do high do sweep
8. Target: PDH oposto ou PWL
```

### 4.4 Equal Highs/Lows Sweep

```
Identificar Equal Highs (EQH):
  - 2+ swing highs no mesmo nivel (tolerancia <= 0.2%)
  - Stops acumulados acima do EQH

Short (apos sweep do EQH):
1. Preco sobe acima do EQH
2. Rejeicao (wick longa em cima)
3. Close volta abaixo do EQH
4. Deslocamento bearish
5. MSS confirmado
6. Entrar short no FVG/OB
7. Target: equal lows ou proximo SSL
```

### 4.5 Funding Rate Sweep (crypto-specific)

```
SE funding rate > +0.1% por 8h (extremamente positivo):
  Longs estao muito alavancados
  BSL acima (liquidacoes de shorts ja aconteceram)
  SSL abaixo (liquidacoes de longs sao o alvo)
  PROBABILIDADE: sweep do SSL (preco cai para liquidar longs)
  ESTRATEGIA: preparar para Long apos sweep

SE funding rate < -0.1% por 8h (extremamente negativo):
  Shorts estao muito alavancados
  BSL acima (liquidacao de shorts e o alvo)
  PROBABILIDADE: sweep do BSL (preco sobe para liquidar shorts)
  ESTRATEGIA: preparar para Short apos sweep
```

## 5. Sinais de Saida

### 5.1 Target no oposto do range

```
Long apos sweep de Asian Low:
  Target: Asian High (oposto do range)

Short apos sweep de Asian High:
  Target: Asian Low
```

### 5.2 Target em liquidez oposta

```
Long apos sweep de PDL:
  Target 1: Previous Day High (BSL oposto)
  Target 2: Asian High
  Target 3: Equal Highs (se existir)

Escalar: 50% no T1, 30% no T2, 20% trailing
```

### 5.3 Stop Loss

```
Long:
  Stop: abaixo do low da candle de sweep (wick low)
  RAZAO: se preco voltar abaixo do sweep, a hipotese falhou

Short:
  Stop: acima do high da candle de sweep (wick high)
```

### 5.4 Saida por invalidacao

```
Long:
  SE preco fecha abaixo do low do sweep:
    FECHAR imediatamente (sweep falhou, e continuacao)

Short:
  SE preco fecha acima do high do sweep:
    FECHAR
```

### 5.5 Trailing apos 1R

```
Apos preco atingir 1R (1x risco):
  Mover stop para break-even + 0.1R
  Trailing: swing low anterior (long) ou swing high (short)
```

## 6. Gestao de Risco

### 6.1 Confidence Scoring

```
| Fator                          | Score  |
|--------------------------------|--------|
| RSI divergence no sweep        | +0.25  |
| London ou NY kill zone         | +0.20  |
| Entrada no FVG                 | +0.15  |
| Entrada no Order Block         | +0.10  |
| Volume spike no sweep          | +0.15  |
| Displacement candle forte      | +0.10  |
| R:R >= 2.5                     | +0.10  |
| OB sem divergencia             | -0.20  |
| ADX < 20 (ranging) sem diverg  | -0.15  |
| Funding extremo a favor        | +0.15  |

Minimo para entrar: 0.50 (15m), 0.55 (1h)
Tamanho escala com confidence: size = base * confidence
```

### 6.2 Position Sizing

```python
confidence = compute_confidence(sweep, displacement, fvg, ob, session, rsi_div)
if confidence < min_confidence:
    skip()
position_size = base_risk * confidence
position_size = min(position_size, max_position_size)
```

### 6.3 Max trades por sessao

```
max_trades_london = 2
max_trades_ny = 2
max_total_daily = 3
SE trades_hoje >= max_total_daily:
    PARAR
```

### 6.4 Filtro de kill zone

```
SE kill_zone_only = true:
    current_hour = UTC hour
    SE current_hour not in [7,8,9,12,13,14]:
        NAO OPERAR (fora de kill zone)
    EXCECAO: se sweep ja aconteceu e estamos esperando entry,
    permitir entrada ate 2h apos o sweep
```

## 7. Implementacao Tecnica

### 7.1 Deteccao de Asian Range

```python
def detect_asian_range(df: pd.DataFrame, asian_start: int = 0, asian_end: int = 6) -> dict:
    """Detect Asian session range."""
    df["hour"] = df.index.hour
    asian = df[(df["hour"] >= asian_start) & (df["hour"] < asian_end)]

    if len(asian) < 4:
        return None

    return {
        "high": asian["high"].max(),
        "low": asian["low"].min(),
        "start": asian.index[0],
        "end": asian.index[-1],
    }
```

### 7.2 Deteccao de Equal Highs/Lows

```python
def detect_equal_levels(swings: pd.DataFrame, tolerance: float = 0.002) -> list:
    """Detect equal highs and lows (liquidity pools)."""
    levels = []

    highs = swings[swings["type"] == "high"]["value"].values
    for i in range(len(highs)):
        for j in range(i + 1, len(highs)):
            if abs(highs[i] - highs[j]) / highs[i] < tolerance:
                levels.append({"type": "BSL", "level": (highs[i] + highs[j]) / 2})

    lows = swings[swings["type"] == "low"]["value"].values
    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            if abs(lows[i] - lows[j]) / lows[i] < tolerance:
                levels.append({"type": "SSL", "level": (lows[i] + lows[j]) / 2})

    return levels
```

### 7.3 Deteccao de FVG

```python
def detect_fvg(df: pd.DataFrame, min_size: float = 0.001) -> list:
    """Detect Fair Value Gaps."""
    fvgs = []
    for i in range(1, len(df) - 1):
        # Bullish FVG: candle[i-1].high < candle[i+1].low
        gap = df["low"].iloc[i + 1] - df["high"].iloc[i - 1]
        if gap > 0 and gap / df["close"].iloc[i] > min_size:
            fvgs.append({
                "type": "bullish",
                "top": df["low"].iloc[i + 1],
                "bottom": df["high"].iloc[i - 1],
                "index": i,
            })

        # Bearish FVG: candle[i-1].low > candle[i+1].high
        gap = df["low"].iloc[i - 1] - df["high"].iloc[i + 1]
        if gap > 0 and gap / df["close"].iloc[i] > min_size:
            fvgs.append({
                "type": "bearish",
                "top": df["low"].iloc[i - 1],
                "bottom": df["high"].iloc[i + 1],
                "index": i,
            })

    return fvgs
```

### 7.4 Deteccao de Order Block

```python
def detect_order_blocks(df: pd.DataFrame, displacement_atr: float = 1.5) -> list:
    """Detect Order Blocks (last opposite candle before strong move)."""
    atr = compute_atr(df)
    obs = []

    for i in range(2, len(df)):
        # Check for displacement (strong move)
        candle_range = df["high"].iloc[i] - df["low"].iloc[i]
        if candle_range < displacement_atr * atr.iloc[i]:
            continue

        is_bullish = df["close"].iloc[i] > df["open"].iloc[i]

        if is_bullish:
            # Look for last bearish candle before this (Bullish OB)
            for j in range(i - 1, max(i - 10, 0), -1):
                if df["close"].iloc[j] < df["open"].iloc[j]:  # bearish
                    obs.append({
                        "type": "bullish",
                        "high": df["high"].iloc[j],
                        "low": df["low"].iloc[j],
                        "index": j,
                    })
                    break
        else:
            # Look for last bullish candle before (Bearish OB)
            for j in range(i - 1, max(i - 10, 0), -1):
                if df["close"].iloc[j] > df["open"].iloc[j]:  # bullish
                    obs.append({
                        "type": "bearish",
                        "high": df["high"].iloc[j],
                        "low": df["low"].iloc[j],
                        "index": j,
                    })
                    break

    return obs
```

### 7.5 Pipeline completo

```python
def liquidity_sweep_pipeline(df: pd.DataFrame, params: dict) -> list:
    """Full liquidity sweep signal generation."""
    signals = []

    # 1. Detect Asian range
    asian_range = detect_asian_range(df)
    if not asian_range:
        return signals

    # 2. Look for sweep after Asian session
    post_asian = df[df.index > asian_range["end"]]

    for i in range(len(post_asian)):
        candle = post_asian.iloc[i]

        # Sweep of Asian Low (SSL)
        if candle["low"] < asian_range["low"] and candle["close"] > asian_range["low"]:
            wick_ratio = (asian_range["low"] - candle["low"]) / (candle["high"] - candle["low"])
            if wick_ratio >= params["sweep_wick_ratio"]:
                # Check displacement in next candle
                if i + 1 < len(post_asian):
                    next_candle = post_asian.iloc[i + 1]
                    atr = compute_atr(df).iloc[i]
                    displacement = (next_candle["high"] - next_candle["low"]) / atr

                    if displacement >= params["displacement_atr_mult"] and next_candle["close"] > next_candle["open"]:
                        # Find FVG or OB for entry
                        fvgs = detect_fvg(post_asian.iloc[:i + 2])
                        bullish_fvgs = [f for f in fvgs if f["type"] == "bullish"]

                        if bullish_fvgs:
                            entry_fvg = bullish_fvgs[-1]
                            signals.append({
                                "direction": "LONG",
                                "entry": entry_fvg["top"],
                                "stop": candle["low"],
                                "target": asian_range["high"],
                                "rr": (asian_range["high"] - entry_fvg["top"]) / (entry_fvg["top"] - candle["low"]),
                            })

    return signals
```

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 60%+ | 50% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 10% | < 15% |
| Profit factor | 2.0+ | 1.5 |
| Avg R:R | 2.5+ | 2.0 |
| Trades por mes | 8-15 | 4+ |
| Avg holding period | 1-8h | 30min a 24h |

## 9. Backtest: O que validar

### 9.1 Por kill zone

```
London (07:00-10:00 UTC):  win rate esperado > 60%
NY (12:00-15:00 UTC):      win rate esperado > 60%
Asian (00:00-06:00 UTC):   win rate esperado < 45% (evitar)
Off-hours:                 win rate esperado < 40% (evitar)
```

### 9.2 Por tipo de liquidez

```
Asian range sweep:     win rate esperado > 60%
PDH/PDL sweep:         win rate esperado > 55%
Equal highs/lows:      win rate esperado > 65% (mais previsivel)
Round numbers:         win rate esperado > 60%
```

### 9.3 Validar AMD pattern

```
Para cada trade:
  - Accumulation durou quantas candles? (4-24 esperado)
  - Manipulation (sweep) durou quantas candles? (1-3 esperado)
  - Distribution durou quantas candles? (2-12 esperado)

SE accumulation < 4: range nao e significativo
SE manipulation > 5: provavelmente nao e sweep, e continuacao
```

## 10. Vantagens e Desvantagens

### Vantagens
- Entradas em niveis logicos (liquidez real, nao aleatorio)
- R:R alto (target no oposto do range, stop apertado no sweep)
- Baseado em comportamento institucional (smart money)
- Funciona bem em crypto (order books finos, sweeps visiveis)
- Kill zones filtram horarios de baixa probabilidade

### Desvantagens
- Subjetividade na identificacao de niveis (requer regras estritas)
- Pode ter poucos trades (2-3 por semana em condicoes ideais)
- Sweeps falsos (continuacao em vez de reversao) sao comuns
- Requer multi-timeframe analysis (HTF bias + LTF entry)
- Padroes ICT tem validacao academica limitada

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Volume Profile (STRAT-05) | Alta | OBI confirma absorcao no sweep |
| + Price Action (STRAT-02) | Alta | Candle de confirmacao no FVG/OB |
| + Funding Rate (STRAT-08) | Alta | Funding extremo prediz direcao do sweep |
| + Entropy (STRAT-04) | Media | Entropy filtra mercados caoticos |

## 12. Referencias

- ICT Killzone: "ICT Concepts for Crypto (BTC/ETH): The Complete Guide"
- Michael J. Huddleston (ICT): "Liquidity Trading Strategy: Buy & Sell Side Liquidity"
- rachit367/trade_hunter: ICT AMD strategy on Delta Exchange (BTC/ETH/SOL/AVAX)
- Jotanune/CryptoGuardian: SMC Liquidity Sweeps + Pairs Trading dual engine
- python-telegramBot/crypto-liquidity-ai-trading-bot: order book sweep detection
- Kalena: "Crypto Day Trading Strategies: Order Flow Separates Profitable Traders"
