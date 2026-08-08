# Topico: Taker Flow, Wick Analysis e Candle Anatomy

**Data:** 2026-07-15
**Categoria:** Microestrutura

## TL;DR

Taker buy/sell ratio mede qual lado esta agredindo o book em cada intervalo: compradores forcando execucao no ask ou vendedores forcando no bid. Wick analysis le a anatomia das velas (body vs wick ratios) para detectar rejeicao: long upper wicks indicam distribuicao e rejeicao de alta; long lower wicks indicam absorcao e rejeicao de baixa. Candle anatomy quantifica a "saude" de cada movimento: corpo longo = momentum comprometido, pavio longo = pressao que falhou. Round-number clustering revela que precos sao atraidos para niveis psicologicos. Gap analysis intraday detecta deslocamentos repentinos. Juntos, esses sinais expoe a pressao compradora/vendedora escondida dentro das velas.

## Explicacao para criancas

Imagine um leilao de quadros. O taker buy/sell ratio e contar, a cada minuto, quantas pessoas gritaram "compro agora!" versus "vendo agora!". Se mais gente grita "compro", o ratio sobe de 0.5. As mechas (wicks) das velas sao como rastros de pneu num congestionamento: uma mecha longa para cima significa que alguem acelerou forte rumo ao teto, bateu a cabeça e foi jogado para tras. Rejeicao. Uma mecha longa para baixo e um trampolim que nao segurou: o preco caiu, mas alguem empurrou de volta rapido. O corpo da vela e o trecho que o preco conseguiu segurar sem ser empurrado de volta. Numeros redondos (100, 200, 1000) funcionam como imas psicologicos.

## Como funciona tecnicamente

### Taker Buy/Sell Ratio

```
taker_buy_volume   = volume de trades onde o taker e o comprador (executado no ask)
taker_sell_volume  = volume de trades onde o taker e o vendedor (executado no bid)
                     = total_volume - taker_buy_volume  (na Binance)

ratio_norm = taker_buy_volume / (taker_buy_volume + taker_sell_volume)

ratio_norm > 0.5: buyers dominantes (agressao compradora)
ratio_norm < 0.5: sellers dominantes (agressao vendedora)
ratio_norm = 0.5: equilibrio perfeito, consolidacao/indecisao
```

Extremos: > 0.6 ou < 0.4 = agressao muito one-sided. A normalizacao torna o ratio comparavel across regimes de volume (candle de US$ 10M com 55% buy diz o mesmo sobre agressao que candle de US$ 100M com 55% buy).

Implementacao a partir de klines da Binance (campo `taker_buy_base_asset_volume`, index 9 no array de klines):

```python
def calc_taker_ratio(df: pd.DataFrame) -> pd.Series:
    taker_buy = df["taker_buy_base"]
    taker_sell = df["volume"] - df["taker_buy_base"]
    total = taker_buy + taker_sell
    return (taker_buy / total.replace(0, np.nan)).fillna(0.5)
```

### Candle anatomy: body e wicks

Para cada candle com open (O), high (H), low (L), close (C):

```
body      = |C - O|
upper_wick = H - max(O, C)
lower_wick = min(O, C) - L
range      = H - L

body_ratio      = body / range          # fracao do range que e corpo
upper_wick_ratio = upper_wick / range
lower_wick_ratio = lower_wick / range
```

Interpretacao:

- **body_ratio alto (> 0.7):** momentum forte, lado vencedor dominou do open ao close.
- **upper_wick_ratio alto (> 0.4):** rejeicao de alta. Preco empurrou para cima e foi jogado de volta. Sinal bearish.
- **lower_wick_ratio alto (> 0.4):** rejeicao de baixa (absorcao). Preco caiu e foi empurrado de volta. Sinal bullish (pin bar / hammer).
- **body_ratio baixo + wicks grandes:** indecisao, batalha equilibrada (doji spinning top).

### Rejection wicks como signal

Long lower wick (hammer / pin bar bullish):
- Preco caiu forte (sellers empurraram).
- Buyers absorveram agressivamente e empurraram de volta perto do open.
- Sinal: falha de leilao para baixo. Liquidity sweep seguido de absorcao.
- Contexto ideal: apos downtrend, em nivel de suporte/HVN.

Long upper wick (shooting star / pin bar bearish):
- Preco subiu forte (buyers empurraram).
- Sellers absorveram/distribuiram e empurraram de volta perto do open.
- Sinal: falha de leilao para cima. Distribuicao em forca.
- Contexto ideal: apos uptrend, em nivel de resistencia/HVN.

### Liquidity sweep + displacement (setup de reversao de maior probabilidade em cripto)

A sequencia classicamente observada:

1. Preco varre (sweep) um topo ou fundo anterior.
2. Traders agressivamente perseguem o breakout.
3. Open interest sobe.
4. Funding superaquece.
5. Preco rejeita violentamente.
6. Candle de displacement forma na direcao oposta (corpo longo, wick curto).
7. Trapped traders viram combustivel para o movimento contrario.

O candle de displacement e critico: mostra compromisso. Corpo longo com wick curto na direcao da reversao confirma que a absorcao funcionou.

### Candle anatomy quantitativo

Para transformar anatomy em features numericas, computa-se ratios por candle:

```python
def calc_candle_anatomy(ohlcv: pd.DataFrame) -> pd.DataFrame:
    body = (ohlcv["close"] - ohlcv["open"]).abs()
    rng = (ohlcv["high"] - ohlcv["low"]).replace(0, np.nan)
    upper_wick = ohlcv["high"] - ohlcv[["open", "close"]].max(axis=1)
    lower_wick = ohlcv[["open", "close"]].min(axis=1) - ohlcv["low"]
    is_bull = ohlcv["close"] > ohlcv["open"]
    return pd.DataFrame({
        "body_ratio": body / rng,
        "upper_wick_ratio": upper_wick / rng,
        "lower_wick_ratio": lower_wick / rng,
        "is_bull": is_bull,
        "is_rejection_top": (upper_wick_ratio > 0.4) & (body_ratio < 0.3),
        "is_rejection_bottom": (lower_wick_ratio > 0.4) & (body_ratio < 0.3),
        "is_momentum_candle": body_ratio > 0.7,
    })
```

Classificacao derivada:

- **Hammer / pin bar bullish:** lower_wick_ratio > 0.6, body no topo. Sinal de absorcao de baixa.
- **Shooting star / pin bar bearish:** upper_wick_ratio > 0.6, body na base. Sinal de distribuicao.
- **Doji:** body_ratio < 0.1. Indecisao.
- **Marubozu:** body_ratio > 0.9, wicks quase zero. Momentum extremo, direcao firme.
- **Spinning top:** body_ratio entre 0.1 e 0.3, wicks dos dois lados. Batalha equilibrada.

### Round-number clustering

Precos psicologicos (BTC 100k, 150k; ETH 5k; numeros redondos em geral) atraem ordens. Hipotese: stops e ordens pendentes se acumulam em round numbers, criando liquidity pools que o preco tende a visitar e testar.

Metrica de clustering: distancia do close ao round number mais proximo, normalizada:

```
round_number_dist = |close - round_nearest| / tick_size
```

Distribuicao empirica: se close frequenta round numbers mais que o esperado por acaso, ha clustering. Teste: histograma de distancias vs distribuicao uniforme esperada. Em cripto, round numbers em USDT (100, 1000, 10000) e em BTC inteiro (0.1, 1, 10) funcionam como imas. O efeito e mais forte em altcoins com preco baixo, onde round numbers sao psicologicamente mais salientes.

### Gap analysis intraday

Gap = open_t - close_{t-1}. Em cripto 24/7, gaps sao raros em timeframes continuos, mas em timeframes discretes (1h, 4h, diario) podem ocorrer por deslocamentos repentinos entre candles.

```
gap = open_t - close_{t-1}
gap_pct = gap / close_{t-1}
```

Classificacao de gaps:

- **Gap up sem fill (preco fica acima do gap):** breakout com forca, ausencia de sellers.
- **Gap up com fill rapido:** exaustao de compra, gap foi opportunistic.
- **Gap down sem fill:** breakdown, panico ou liquidacao em serie.
- **Gap down com fill rapido:** flush que absorveu (V-bottom), strong buy.
- **Gap > 3 std do gap medio historico:** evento de deslocamento, investigar causa (liquidacao, noticia).

O "gap mean" historico em cripto e tipicamente < 0.2% em timeframes >= 15m porque o mercado nao fecha. Gaps > 1% em 1h indicam evento extremo (liquidacao cascade, funding settlement anomalia).

### Combinacao taker ratio + wick

Sinal de maior confianca: taker ratio alinhado com wick anatomy.

- **Long upper wick + taker sell dominante (ratio < 0.45):** distribuicao confirmada por agressao. Sinal bearish forte.
- **Long lower wick + taker buy dominante (ratio > 0.55):** absorcao confirmada por agressao. Sinal bullish forte.
- **Long upper wick + taker buy dominante:** divergencia. Preco rejeitado mas buyers ainda agredindo. Ambiguo, possivel re-teste.
- **Corpo longo verde + taker buy dominante:** momentum saudavel, sustentado por agressao real.

## Estado do mercado em 2026

A leitura de candlestick amadureceu em 2026 para alem de patterns memorizados. O consenso entre educators (CJPeart, 3Commas, Blackperp, DCT Alpha): traders profissionais nao negociam velas isoladas, negociam liquidity, positioning, order flow, displacement e trapped participants. A vela e apenas evidencia do que aconteceu no leilao.

O taker buy/sell ratio se consolidou como pressure gauge de ordem flow sem precisar de order book completo. A Binance expoe taker buy-sell data para futuros. Plataformas como Blackperp computam o ratio em multi-timeframe simultaneo (1m, 5m, 1h): quando todos concordam na direcao, confianca do sinal sobe; quando discordam, o sistema flaga estado conflitado e reduz conviccao.

DCT Alpha formalizou o threshold: ratio > 0.5 sustained = buying-dominant environment; < 0.5 sustained = selling dominance; extremos > 0.6 ou < 0.4 = one-sided aggression. A normalizacao (dividir por total) tornou o ratio comparavel across ativos e regimes de volume, vantagem sobre delta absoluto.

Wick analysis ganhou framing de "liquidity events": toda reversao conta uma historia. Long wick para baixo = sellers empurraram, stops disparados, breakout shorts entraram, buyers absorveram agressivamente. Esse rejection wick e evidencia de leilao que falhou. O setup de maior probabilidade em cripto em 2026 e liquidity sweep seguido de displacement: sweep de high/low, OI sobe, funding superaquece, rejeicao violenta, candle de displacement na direcao oposta.

Round-number clustering e gap analysis continuam como ferramentas auxiliares para contexto, nao sinais primarios. O mercado reconhece que round numbers atraem liquidez mas que o sinal so e acionavel quando combinado com order flow (CVD, taker ratio) e estrutura (POC, HVN/LVN).

### Pin bars e liquidacoes em 2026

Um estudo da DolphinDB (Medium, 2026) analisou a formacao de pin bars em cripto correlacionada a um evento de US$ 19 bilhoes em liquidacoes. A analise usou dados de candlestick minuto-a-minuto para identificar padroes pin bar, aggTrade para calcular VPIN, e snapshots de order book para medir imbalance. Conclusao: os indicadores de microestrutura (VPIN e Order Book Imbalance) ja sinalizavam risco elevado antes do movimento extremo de preco. Isso reforca que wick analysis isolada e insuficiente: combinada com toxicity (VPIN) e imbalance, vira early warning.

### Multi-timeframe confluencia

A pratica consolidada em 2026 para taker ratio e wick analysis e multi-timeframe:

- **1m:** captura mudanca imediata de agressao. Ruidoso, para scalping.
- **5m:** filtra ruido, captura shift de pressao de curto prazo.
- **1h:** trend context, direcao estrutural.
- **Confluencia:** quando 1m, 5m e 1h concordam na direcao, confianca do sinal e maxima. Quando discordam (curto bullish, longo bearish), sistema flaga conflito e reduz conviccao. Esse padrao de multi-timeframe agreement e o filtro que separa sinais acionaveis de ruido.

## Ferramentas e APIs disponiveis

- **Binance klines REST**, tipo: OHLCV + taker buy, custo: gratis, URL: `https://api.binance.com/api/v3/klines`. Campos: open, high, low, close, volume, taker_buy_base_asset_volume (index 9). Base para taker ratio e candle anatomy.
- **Binance klines WebSocket**, tipo: OHLCV em tempo real, custo: gratis, URL: `wss://stream.binance.com:9443/ws/btcusdt@kline_1m`. Stream `<symbol>@kline_<interval>` com campo `V` (taker buy base) e `Q` (taker buy quote).
- **Binance aggTrade WebSocket**, tipo: tick flow classificado, custo: gratis, URL: `wss://stream.binance.com:9443/ws/btcusdt@aggTrade`. Para taker ratio de alta resolucao.
- **Coinglass API V4**, tipo: taker buy/sell long-short ratio, custo: freemium/pago, URL: https://www.coinglass.com/CryptoApi. Taker buy/sell volume spot, top trader position ratio, top trader account ratio. Multi-timeframe.
- **Kaiko**, tipo: L1 tick com direcao, custo: pago (from US$ 1.500/mes), URL: https://www.kaiko.com/products/l1-l2-data. Trade direction explicito para taker flow institucional. Cobertura 100+ exchanges.
- **Amberdata**, tipo: market data + analytics, custo: pago institucional, URL: https://www.amberdata.io. Parte da Kaiko desde 2026. CloudSync para data warehouses.
- **TradingView**, tipo: indicadores de candle anatomy / pin bar, custo: freemium, URL: https://www.tradingview.com. Scripts Pine para deteccao de rejection wicks e round-number levels. Indicadores de volume profile integrados.
- **Tardis.dev**, tipo: replay historico de ticks, custo: pago, URL: https://tardis.dev. Replay de taker flow historico para backtest de wick analysis em qualquer periodo.
- **Blackperp**, tipo: engine de 173 sinais com taker ratio, custo: freemium, URL: https://blackperp.com/academy/what-is-taker-buy-sell-ratio. Computa taker ratio multi-timeframe (1m, 5m, 1h) para 21 symbols.

## Por que importa para o crypto-correl-bot

O bot ja implementa parte substancial desses sinais. Em `scripts/analyze_microstructure.py`:

- `compute_taker_buy_sell_ratio` (linhas 49-100): calcula ratio por symbol, por hora e por dia a partir de `taker_buy_base`. Retorna avg_ratio, median_ratio, pct_buy_dominant, net_aggression.
- Analise de wick (referenciado no docstring linhas 8, 14): candle anatomy com body/wick ratios por tempo e direcao.
- Gap analysis (docstring linha 7): open vs previous close.
- Round number clustering (docstring linha 9): teste de atracao a niveis psicologicos.

Lacunas concretas:

1. **Taker ratio apenas em batch historico, nao live.** `analyze_microstructure.py` roda em Parquet historico. O dashboard live (`analyze_live.py`) mostra CVD mas nao taker ratio normalizado por candle em tempo real. Adicionar `calc_taker_ratio` no loop live e plotar como sub-chart ao lado do CVD. O campo `V` (taker buy base) ja vem no stream kline.
2. **Wick analysis nao quantificado como feature numerica.** Computar body_ratio, upper_wick_ratio, lower_wick_ratio por candle e persistir permitiria detectar rejection wicks algoritmicamente. Implementar flag: `is_rejection_top = upper_wick_ratio > 0.4 AND body_ratio < 0.3`; `is_rejection_bottom = lower_wick_ratio > 0.4 AND body_ratio < 0.3`. Esses flags viram features binarias para modelos preditivos.
3. **Sem cruzamento taker ratio + wick.** O sinal de maior confianca (long upper wick + taker sell dominante) nao e detectado. Combinar flag de rejection com taker ratio na mesma candle:
   ```
   strong_distribution = is_rejection_top AND taker_ratio < 0.45
   strong_absorption = is_rejection_bottom AND taker_ratio > 0.55
   ```
4. **Liquidity sweep + displacement nao detectado.** Sequencia de 7 passos (sweep, OI sobe, funding superaquece, rejeicao, displacement) nao esta automatizada. O bot tem dados de OI e funding (`live_collector.py` pollers): cruzar com wick analysis daria o setup de reversao de maior probabilidade. Pseudocodigo:
   ```
   def detect_sweep_displacement(candles, oi, funding):
       swept_level = prior_high (ou prior_low)
       if price wicked_beyond(swept_level) AND oi_rising AND funding_extreme:
           if next_candle is_displacement_opposite AND body_ratio > 0.7:
               return SIGNAL (reversao)
   ```
5. **Round-number clustering como feature, nao so teste.** Converter distancia ao round number em feature numerica (z-score vs distribuicao uniforme) para alimentar modelos preditivos. Quanto mais perto de um round number, maior a probabilidade de teste/reacao.
6. **Gap analysis sem alerta.** Flagar gaps intraday > N desvios do gap medio historico como evento de deslocamento. Gaps extremos em 1h correlacionam com liquidacao cascades que o bot ja detecta via stream `!forceOrder`.
7. **Candle anatomy por regime.** Distribuicao de body/wick ratios muda com regime de volatilidade. Computar estatisticas de anatomy por regime (alto vs baixo ATR) e usar como contexto para interpretar rejection wicks: wick em regime de baixa vol e mais significativo que wick em regime de alta vol.

Recomendacao: criar `src/analysis/candle_anatomy.py` com `calc_body_wick_ratios(ohlcv)`, `detect_rejection_wicks(thresholds)`, `calc_taker_ratio_live(kline)`, `detect_round_number_clustering(closes, base)`, `detect_liquidity_sweep(ohlcv, oi, funding)`, `detect_gap_events(ohlcv, n_std=3)`. Integrar rejection wicks e taker ratio live no dashboard como novas colunas/secoes. Funcoes testaveis com dados sinteticos (seed fixo), cobrindo edge cases: candle com high == low (range zero), candle com volume zero, gap com close anterior zero.

## Referencias

- https://cryptoadventure.com/taker-buy-sell-ratio-explained-what-it-measures-and-why-traders-watch-it/ (taker buy/sell ratio: definicao, agressor vs maker, uso em breakouts)
- https://blackperp.com/academy/what-is-taker-buy-sell-ratio (ratio multi-timeframe, thresholds 0.5, 173-signal engine)
- https://cjpeart.com/beyond-the-engulfing-candle-how-professional-traders-actually-read-reversals-in-the-crypto-markets/ (reversao como liquidity event, sweep + displacement, rejection wicks)
- https://academy.dctalpha.com/chart-tools/taker-ratio (normalizacao 0.5, extremos 0.6/0.4, comparacao cross-regime)
- https://3commas.io/blog/read-candlestick-chart (anatomia de candle, body/wick, momentum vs indecisao)
- https://www.coinglass.com/CryptoApi (Coinglass: taker buy/sell long-short ratio, spot buy/sell volume)
- https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md (kline stream com campos V e Q de taker buy)
