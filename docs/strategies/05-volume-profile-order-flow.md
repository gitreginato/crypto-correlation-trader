# Estrategia 05: Volume Profile e Order Flow

**ID:** STRAT-05
**Categoria:** Microestrutura / Institutional
**Timeframe ideal:** 5m, 15m, 1h (com dados L2/trade)
**Horizonte:** Curto prazo (minutos a horas)
**Complexidade:** Alta

## 1. Conceito

Volume Profile mostra **onde** o volume foi negociado (por nivel de preco), nao apenas **quando** (por tempo). Order Flow analisa o fluxo de ordens em tempo real: quem esta comprando, quem esta vendendo, e onde a liquidez esta acumulada.

### Intuicao

Indicadores tradicionais (RSI, MACD, medias moveis) sao derivados do preco e sempre lagging. Volume Profile e Order Flow mostram o que esta acontecendo **agora**: onde os grandes players estao posicionados, onde os stops estao, e se ha absorcao (grandes ordens sendo executadas sem mover o preco).

### Diferenca Volume Profile vs Volume tradicional

```
Volume tradicional: bar de volume por candle (tempo)
Volume Profile:     volume por nivel de preco (preco)

Volume tradicional responde: "quanto foi negociado as 14h?"
Volume Profile responde:    "em que nivel de preco foi mais negociado?"
```

## 2. Fundamentacao Teorica

### 2.1 Volume Profile: Conceitos Chave

| Conceito | Definicao | Uso |
|----------|-----------|-----|
| POC (Point of Control) | Nivel de preco com maior volume | Ancora de equilibrio |
| Value Area (VA) | Faixa onde 70% do volume ocorreu | Zona de valor justo |
| VAH (Value Area High) | Topo do value area | Resistencia institucional |
| VAL (Value Area Low) | Base do value area | Suporte institucional |
| HVN (High Volume Node) | Nivel com volume anormalmente alto | Suporte/resistencia forte |
| LVN (Low Volume Node) | Nivel com volume anormalmente baixo | Zona de passagem rapida |

### 2.2 Order Flow: Conceitos Chave

| Conceito | Definicao | Uso |
|----------|-----------|-----|
| CVD (Cumulative Volume Delta) | Soma de volume comprador menos vendedor | Direcao do fluxo |
| Delta | Volume buy - volume sell por candle | Pressao direcional |
| Imbalance | Razao bid/ask no order book | Pressao pendente |
| Absorption | Alto volume com pouco movimento de preco | Grande ordem sendo absorvida |
| Exhaustion | Volume alto seguido de parada de movimento | Fim do impulso |
| Footprint | Volume buy/sell por nivel de preco dentro do candle | Analise intra-candle |

### 2.3 Order Book Imbalance (OBI)

```
OBI = (bid_volume - ask_volume) / (bid_volume + ask_volume)

OBI > 0: mais bids que asks (pressao compradora)
OBI < 0: mais asks que bids (pressao vendedora)
OBI ~ 0: equilibrado

Horizonte de previsao: 1-60 segundos (muito curto)
```

**Insight chave da pesquisa:** OBI e forte em 1-15s e fraco em 5min+. Momentum de preco e o oposto. Sao complementares, nao competidores.

### 2.4 Lee-Ready Tick Rule (classificacao de trades)

Quando nao temos dados de bid/ask para cada trade, usamos o tick rule:

```python
def classify_trades(prices: np.ndarray) -> np.ndarray:
    """Classify trades as buyer-initiated or seller-initiated."""
    direction = np.sign(np.diff(prices))
    # Fill first trade as neutral
    direction = np.insert(direction, 0, 0)
    # Replace zeros with previous direction
    for i in range(1, len(direction)):
        if direction[i] == 0:
            direction[i] = direction[i - 1]
    return direction  # +1 = buy, -1 = sell
```

### 2.5 Kyle's Lambda (Price Impact)

```
lambda = delta_price / signed_volume

Mede quanto o preco se move por unidade de volume direcionado.
Lambda alto: mercado iliquido (grandes ordens movem muito o preco)
Lambda baixo: mercado liquido (grandes ordens tem pouco impacto)
```

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `profile_period` | "daily" | "session", "daily", "weekly" | Periodo do Volume Profile |
| `value_area_pct` | 70 | 68 a 80 | % do volume para Value Area |
| `hvn_threshold` | 2.0 | 1.5 a 3.0 | Multiplicador do volume medio para HVN |
| `lvn_threshold` | 0.5 | 0.3 a 0.7 | Fracao do volume medio para LVN |
| `obi_levels` | 10 | 5 a 50 | Niveis do order book para OBI |
| `obi_window` | 60 | 10 a 300 | Janela rolling do OBI (segundos) |
| `delta_window` | 5 | 1 a 30 | Janela do delta (candles) |
| `absorption_volume_mult` | 3.0 | 2.0 a 5.0 | Volume x media para absorcao |
| `absorption_price_move` | 0.001 | 0.0005 a 0.005 | Max move de preco para absorcao (0.1%) |
| `min_dollar_volume` | 1e7 | 1e6 a 1e8 | Min volume em USD para operar |

## 4. Sinais de Entrada

### 4.1 POC Rejection (Long)

```
CONDICOES:
1. Preco desce ao POC do dia anterior
2. Delta na zona do POC e positivo (mais compras que vendas)
3. CVD esta virando de negativo para positivo
4. OBI > 0.3 (pressao compradora no book)
5. Volume na zona do POC > 2x volume medio

ENTRY: Long no POC
STOP: 1 ATR abaixo do VAL
TARGET: VAH (topo do value area)
```

### 4.2 LVN Breakout (continuacao)

```
CONDICOES:
1. Preco rompe um LVN (Low Volume Node)
2. Volume no breakout > 1.5x media
3. Delta fortemente positivo (CVD subindo)
4. OBI > 0.4 (forte pressao compradora)

ENTRY: Long no rompimento do LVN
STOP: abaixo do LVN
TARGET: proximo HVN (High Volume Node)

RAZAO: LVNs sao zonas de baixa liquidez onde o preco se move rapido.
Apos romper, o preco acelera ate encontrar o proximo HVN.
```

### 4.3 Absorption Reversal

```
CONDICOES:
1. Preco em nivel de suporte (HVN ou POC)
2. Volume extremamente alto (> 3x media)
3. Movimento de preco muito pequeno (< 0.1%)
4. Delta negativo (vendedores aggressivos)
5. Mas preco nao cai

ENTRY: Long (absorcao vendedora = grandes compradores absorvendo)
STOP: abaixo do nivel de absorcao
TARGET: VAH ou proximo HVN

RAZAO: grandes ordens de venda estao sendo absorvidas por
compradores institucionais sem mover o preco. Quando os
vendedores se exaurem, o preco sobe.
```

### 4.4 Exhaustion Reversal

```
CONDICOES:
1. Preco em movimento direcional forte (>= 3 candles na direcao)
2. Volume climax (pico de volume > 2x media)
3. Delta na direcao do movimento mas diminuindo
4. CVD faz divergencia com preco (preco sobe, CVD para de subir)
5. Wick longa contra a direcao do movimento

ENTRY: Contrario ao movimento (reversao)
STOP: acima/abaixo do climax
TARGET: POC ou VWAP
```

## 5. Sinais de Saida

### 5.1 Target no HVN/POC

```
SE preco atinge HVN ou POC oposto:
    FECHAR 50% da posicao
    Trailing stop no resto
```

### 5.2 Stop por divergencia de delta

```
Long aberto:
    SE delta vira negativo por 3 candles consecutivos:
    FECHAR (fluxo virou contra)
```

### 5.3 Stop por OBI reversal

```
Long aberto:
    SE OBI cai de > 0.3 para < -0.3:
    FECHAR (pressao do book inverteu)
```

## 6. Gestao de Risco

### 6.1 Position Sizing por liquidez

```python
# Ajustar tamanho pela liquidez (Kyle's lambda)
lambda_normalized = kyle_lambda / median(kyle_lambda_history)
size_multiplier = 1.0 / max(lambda_normalized, 0.5)
position_size = base_size * size_multiplier

# Mercado iliquido (lambda alto) = tamanho menor
# Mercado liquido (lambda baixo) = tamanho normal
```

### 6.2 Filtro de liquidez minima

```
SE dollar_volume_24h < min_dollar_volume:
    NAO OPERAR (liquidez insuficiente para order flow ser confiavel)
```

### 6.3 Max posicoes por direcao

```
max_long = 3
max_short = 3
SE longs_abertos >= max_long:
    NAO abrir novos longs
```

## 7. Implementacao Tecnica

### 7.1 Volume Profile

```python
def compute_volume_profile(df: pd.DataFrame, price_bins: int = 100) -> dict:
    """Compute volume profile from OHLCV data."""
    price_range = df["high"].max() - df["low"].min()
    bin_size = price_range / price_bins

    bins = np.arange(df["low"].min(), df["high"].max() + bin_size, bin_size)
    volume_profile = np.zeros(len(bins) - 1)

    for _, candle in df.iterrows():
        # Distribute candle volume across price range
        candle_range = candle["high"] - candle["low"]
        if candle_range == 0:
            continue
        # Simple: assign volume to bins within candle range
        for i in range(len(bins) - 1):
            if bins[i] >= candle["low"] and bins[i + 1] <= candle["high"]:
                volume_profile[i] += candle["volume"]

    poc_idx = np.argmax(volume_profile)
    poc = bins[poc_idx]

    # Value Area (70%)
    total_volume = volume_profile.sum()
    target_volume = total_volume * 0.70

    # Expand from POC until 70% is covered
    va_indices = [poc_idx]
    va_volume = volume_profile[poc_idx]
    while va_volume < target_volume and len(va_indices) < len(volume_profile):
        # Expand up or down, whichever has more volume
        up_idx = max(va_indices) + 1
        down_idx = min(va_indices) - 1
        up_vol = volume_profile[up_idx] if up_idx < len(volume_profile) else 0
        down_vol = volume_profile[down_idx] if down_idx >= 0 else 0
        if up_vol >= down_vol and up_idx < len(volume_profile):
            va_indices.append(up_idx)
            va_volume += up_vol
        elif down_idx >= 0:
            va_indices.append(down_idx)
            va_volume += down_vol
        else:
            break

    vah = bins[max(va_indices) + 1]
    val = bins[min(va_indices)]

    return {
        "bins": bins,
        "volumes": volume_profile,
        "poc": poc,
        "vah": vah,
        "val": val,
        "hvns": find_hvns(volume_profile, bins, threshold_mult=2.0),
        "lvns": find_lvns(volume_profile, bins, threshold_mult=0.5),
    }
```

### 7.2 Order Book Imbalance (via WebSocket)

```python
async def compute_obi(websocket, levels: int = 10) -> float:
    """Compute Order Book Imbalance from Binance WebSocket."""
    depth = await websocket.recv()
    data = json.loads(depth)

    bid_volume = sum(float(b[1]) for b in data["bids"][:levels])
    ask_volume = sum(float(a[1]) for a in data["asks"][:levels])

    if bid_volume + ask_volume == 0:
        return 0.0
    return (bid_volume - ask_volume) / (bid_volume + ask_volume)
```

### 7.3 Cumulative Volume Delta

```python
def compute_cvd(df: pd.DataFrame) -> pd.Series:
    """Compute Cumulative Volume Delta using tick rule proxy."""
    # Classify each candle as buy or sell dominant
    direction = np.sign(df["close"] - df["open"])
    # Fill zeros with previous
    direction = direction.replace(0, np.nan).ffill().fillna(0)

    delta = direction * df["volume"]
    cvd = delta.cumsum()
    return cvd
```

### 7.4 Absorption Detection

```python
def detect_absorption(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Detect absorption: high volume, low price movement."""
    avg_volume = df["volume"].rolling(window).mean()
    price_move = (df["high"] - df["low"]) / df["close"]

    high_volume = df["volume"] > avg_volume * 3.0
    low_move = price_move < 0.001  # < 0.1% move

    return high_volume & low_move
```

### 7.5 Fontes de dados

```
OHLCV (ja temos):
  - Binance Vision: dados historicos de klines
  - Binance REST API: klines em tempo real

Order Book (L2):
  - Binance WebSocket: wss://stream.binance.com:9443/ws/<symbol>@depth20@100ms
  - Dados historicos de depth: NAO disponivel gratuitamente

Trade data (tick):
  - Binance WebSocket: wss://stream.binance.com:9443/ws/<symbol>@trade
  - Binance Vision: aggTrades mensais/diarios (historico)

LIMITACAO: Volume Profile aproximado com OHLCV (distribuicao uniforme).
           Para Volume Profile preciso, precisa de tick data.
```

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 55%+ | 50% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 10% | < 15% |
| Profit factor | 2.0+ | 1.5 |
| Avg holding period | 15min a 4h | 5min a 8h |
| Trades por mes | 20-50 | 10+ |
| Slippage | < 0.05% | < 0.1% |

## 9. Backtest: O que validar

### 9.1 Validar POC como suporte/resistencia

```
Para cada dia com POC definido:
  - Preco retornou ao POC no dia seguinte? (frequencia)
  - Preco respeitou o POC (parou e reverteu)? (win rate)
  - Preco rompeu o POC e continuou? (loss rate)

Target: POC respeitado em >= 60% das vezes
```

### 9.2 Validar absorcao como sinal de reversao

```
Para cada evento de absorcao detectado:
  - Preco reverteu em quantas candles? (tempo ate reversao)
  - Magnitude da reversao? (R:R)
  - Falso positivo: absorcao seguida de continuacao? (taxa)

Target: reversao em >= 65% dos casos dentro de 1h
```

### 9.3 Impacto da latencia

```
Order flow tem horizonte de 1-60s.
Em backtest com dados de 1min, ja perdemos parte do edge.
Validar: backtest com 1min vs 5min vs 15min
Se Sharpe cai > 50% de 1min para 5min: estrategia so e viavel em live
```

## 10. Vantagens e Desvantagens

### Vantagens
- Informacao nao-lagging (order book e em tempo real)
- Identifica niveis institucionais (HVN, POC)
- Detecta absorcao e exhaustion (padroes de smart money)
- Complementar com momentum (OBI em 1-15s, momentum em 5min+)
- Funciona bem em crypto (order books mais finos que equities)

### Desvantagens
- Requer dados L2/trade em tempo real (WebSocket)
- Horizonte muito curto (segundos a minutos)
- Volume Profile aproximado com OHLCV (precisa de tick para preciso)
- Custo de infraestrutura (WebSocket, processamento de tick data)
- Dificil de backtestar sem dados historicos de order book

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Price Action (STRAT-02) | Alta | Volume Profile confirma niveis de S/R |
| + Liquidity Sweep (STRAT-08) | Alta | OBI mostra quando stops estao sendo varridos |
| + VWAP Reversion (STRAT-07) | Alta | POC e VWAP sao niveis relacionados |
| + Momentum (STRAT-06) | Media | OBI confirma momentum de curto prazo |

## 12. Referencias

- nssanta/Elite-Metrics-Trade-Bybit: 30+ metrics from order book (CVD, VWAP, imbalance)
- Snack-JPG/quantflow: VWAP, OBI, Kyle's lambda methodology
- Mattbusel/FinRL_DeepSeek_Crypto_Trading: order_flow_analytics.py (10 features)
- YungBenn/orderflow-analytics-engine: delta, aggression, absorption detection
- mefai-dev/mefai-autotrade: Volume Profile strategy (POC, VA, VWAP)
- AlgoKing: "Order book imbalance as alpha signal" (IC ~0.11-0.13 at 1-5s)
- malaythakur/AlphaEngine: OBI microstructure scalper strategy
