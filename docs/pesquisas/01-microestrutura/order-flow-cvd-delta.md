# Topico: Order Flow, CVD, Delta e Absorption

**Data:** 2026-07-15
**Categoria:** Microestrutura

## TL;DR

Order flow analisa quem e o agressor em cada trade: o taker que cruza o spread e remove liquidez (market buy ou market sell) ou o maker que estava descansando no book. Delta e a diferenca entre volume comprador agressivo e volume vendedor agressivo num intervalo. CVD (Cumulative Volume Delta) e a soma cumulativa do delta, um "scoreboard" da agressao liquida. Absorption acontece quando alto volume agressivo num lado nao move o preco, indicando que um grande player passivo esta absorvendo. Esses sinais decodificam quem esta realmente forçando o mercado a se mover.

## Explicacao para criancas

Pense num jogo de cabo de guerra. A corda e o preco. De um lado, pessoas que puxam de proposito, com forca (esses sao os aggressors, que gritam "quero comprar agora" e pulam a fila). Do outro, pessoas que estao firmes, com os pes cravados no chao, esperando (esses sao os makers, com ordens pendentes). O Delta mede quantas pessoas puxaram forte neste minuto: mais gente puxando para o lado compra deixa o Delta positivo. O CVD e o placar acumulado do jogo inteiro. Absorption e quando um lado puxa com tudo e a corda nem se mexe: significa que alguem muito forte esta segurando do outro lado, parado, absorvendo toda a forca sem ceder terreno.

## Como funciona tecnicamente

### Aggressor vs maker

Toda trade tem dois lados. O lado passivo e a ordem limit que estava no book. O lado agressivo (taker) e a ordem que cruzou o spread para executar imediatamente. Em cripto, a Binance classifica isso no campo `m` (isBuyerMaker) do stream `aggTrade`:

- `isBuyerMaker = false` (m=0): buyer e o taker, trade e um aggressive buy (executado no ask).
- `isBuyerMaker = true` (m=1): seller e o taker, trade e um aggressive sell (executado no bid).

### Delta e CVD

```
delta_bar   = sum(volume dos trades buy-aggressor) - sum(volume dos trades sell-aggressor)
CVD_t       = CVD_{t-1} + delta_bar_t

delta > 0: buyers agredindo mais (demand aggressive)
delta < 0: sellers agredindo mais (supply aggressive)
CVD subindo: pressao compradora persistente
CVD caindo: pressao vendedora persistente
CVD plano com preco subindo: alta sustentada por makers passivos, nao por takers. Potencialmente insustentavel.
```

### Footprint charts (cluster charts)

O footprint mostra volume buy/sell por nivel de preco dentro de cada candle. Transforma um candlestick numa matriz de atividade intra-candle. Para cada nivel de preco i dentro do candle:

```
footprint[i].buy_volume  = sum(quantity dos trades buy-aggressor executados no preco i)
footprint[i].sell_volume = sum(quantity dos trades sell-aggressor executados no preco i)
footprint[i].delta       = buy_volume - sell_volume
```

Imbalances no footprint: quando um nivel de preco tem volume de um lado >= 3x o lado oposto (comparado diagonalmente, buy no nivel i vs sell no nivel i+1 tick). Celulas de alto volume branco no footprint costumam agir como suporte/resistencia de curto prazo porque ambos os lados concordaram ali.

### Implementacao de CVD e footprint em Python

```python
def calc_cvd_series(trades: pd.DataFrame) -> pd.Series:
    """CVD cumulativo a partir de trades com is_buyer_maker."""
    buys = trades.loc[~trades["is_buyer_maker"], "quantity"]
    sells = trades.loc[trades["is_buyer_maker"], "quantity"]
    delta = trades.assign(
        delta=np.where(trades["is_buyer_maker"], -trades["quantity"], trades["quantity"])
    )
    return delta["delta"].cumsum()

def calc_footprint(trades: pd.DataFrame, n_bins: int = 20) -> dict:
    """Footprint: volume buy/sell por nivel de preco dentro do candle."""
    price_min, price_max = trades["price"].min(), trades["price"].max()
    edges = np.linspace(price_min, price_max, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    buy_vol = np.zeros(n_bins)
    sell_vol = np.zeros(n_bins)
    for _, t in trades.iterrows():
        idx = np.searchsorted(edges, t["price"]) - 1
        if 0 <= idx < n_bins:
            if t["is_buyer_maker"]:
                sell_vol[idx] += t["quantity"]
            else:
                buy_vol[idx] += t["quantity"]
    delta = buy_vol - sell_vol
    poc_idx = int(np.argmax(buy_vol + sell_vol))
    return {
        "centers": centers.tolist(),
        "buy_volume": buy_vol.tolist(),
        "sell_volume": sell_vol.tolist(),
        "delta": delta.tolist(),
        "poc_price": float(centers[poc_idx]),
    }
```

O footprint retorna uma matriz que pode ser visualizada como cluster chart ou processada para detectar stacked imbalances (niveis onde |buy/sell| >= 3).

### Absorption

Absorption e o sinal de ordem flow mais valioso. Padrao: preco flat ou quase parado enquanto delta acumula forte em uma direcao. O book do lado passivo (bid ou ask) recarrega nao importa quantas vezes e atacado. Isso indica um grande player escondido no ruido, absorvendo agressao sem mover o preco.

Classificacao por resultado:

- **Preco sobe + delta negativo:** buyers passivos absorveram venda agressiva. Sinal de nivel forte ou acumulacao institucional price-insensitive.
- **Preco desce + delta positivo:** sellers passivos absorveram compra agressiva. Sinal de oferta pesada descansada (large resting offers).
- **Preco plano + delta forte (qualquer lado):** absorcao pura. O lado agressivo esta sendo contido. Mismatch entre esforco (delta) e resultado (preco) e o core signal.

### Delta divergence

A divergencia entre preco e CVD e o sinal de order flow de maior probabilidade:

- **Preco HH (higher high), CVD LH (lower high):** a alta esta acontecendo com compra agressiva decrescente. Possivel distribuicao. Sellers preenchendo em buy orders sem precisar agredir.
- **Preco LL (lower low), CVD HL (higher low):** a baixa esta acontecendo com venda agressiva decrescente. Possivel acumulacao. Buyers absorvendo.
- **Preco subindo + CVD descendo:** divergencia bearish classica. Sustentacao por makers, nao por takers.

### Classificacao de trades (tick rule)

Quando nao se tem o flag `isBuyerMaker` direto (algumas venues), usa-se o tick rule de Lee-Ready:

```
se trade_price > prev_trade_price: classificar como buy
se trade_price < prev_trade_price: classificar como sell
se trade_price == prev_trade_price: usar regra de Bostick (ultimo lado)
```

Na Binance, o flag `m` elimina a necessidade do tick rule: a classificacao e direta e mais acurada. Em venues sem o flag, o tick rule tem erro de classificacao de ~15% em periodos de baixa volatilidade (muitos trades no mesmo tick). Bulk Volume Classification (BVC) e uma alternativa que usa a distribuicao de volume dentro do candle, mas tambem introduz ruido.

### Exhaustion e momentum breaks

Exhaustion e o complemento da absorption. Padrao: volume alto seguido de parada de movimento. O impulso esgota. Sinais:

- **Volume spike + candle pequena (body curto):** esforco grande, resultado pequeno. Exaustao.
- **CVD acelerando forte + preco parando de acompanhar:** os aggressors estao batendo numa parede que nao cede.
- **Delta extremo seguido de flip de delta:** o lado que dominava subitamente perde forca.

### Delta por nivel de preco (stacked imbalances)

Dentro do footprint, imbalances empilhados no mesmo nivel de preco sao o sinal mais forte. Definicao formal:

```
imbalance[i] = buy_volume[i] / sell_volume[i]   (ou o inverso)
se imbalance[i] >= 3: flagged como imbalance cell
se 3+ imbalance cells seguidas no mesmo lado, mesmo nivel: stacked imbalance
```

Stacked imbalances indicam que um lado esta atacando repetidamente o mesmo nivel de preco com forca desproporcional. Funciona como suporte/resistencia intra-candle de curto prazo. A deteccao comparada diagonalmente (buy no nivel i vs sell no nivel i+1 tick) e mais acurada que comparada horizontalmente, porque buyers atacam um tick acima e sellers um tick abaixo.

### Divergencias CVD avancadas

Alem da divergencia classica preco vs CVD, existem variacoes:

- **CVD divergence em multi-timeframe:** CVD 1m divergente de CVD 15m indica conflito de timeframe (curto prazo exaustao dentro de tendencia de prazo maior). Sinal de potencial pullback, nao de reversao completa.
- **CVD vs OI divergence:** OI subindo com CVD caindo significa new shorts sendo abertos agressivamente (sellers abrindo posicoes). OI subindo com CVD subindo significa new longs abertos (buyers abrindo posicoes). OI caindo com CVD forte e closing de posicoes (cover).
- **CVD acceleration:** a segunda derivada do CVD. Se CVD esta subindo mas a taxa de subida desacelera, o momentum comprador esta perdendo forca mesmo antes do CVD virar.

### Fonte de dados: Binance aggTrade

O stream `<symbol>@aggTrade` entrega trades agregados tick-a-tick:

```json
{
  "e": "aggTrade", "s": "BTCUSDT",
  "a": 12345, "p": "0.001", "q": "100",
  "f": 100, "l": 105, "T": 1688980000000,
  "m": true, "T": 1688980000000
}
```

Campo `m` (isBuyerMaker) define a direcao do agressor. O campo `q` e a quantidade em base asset. Para volume em quote (USDT), multiplicar `p * q`. AggTrades agregam trades com mesmo preco, lado e timestamp em um evento, reduzindo volume de mensagens vs o stream `trade` puro.

Alternativa de baixa frequencia: o endpoint `/api/v3/klines` retorna `taker_buy_base_asset_volume` (V) e `taker_buy_quote_asset_volume` (Q). Sell volume = total_volume - taker_buy_base. Isso permite calcular delta por candle sem tick data. Precisao menor (delta de candle, nao de tick), mas suficiente para divergencias em timeframes >= 5m.

Para footprint de alta resolucao, o stream aggTrade combinado com klines (para definir os limites de cada candle) permite reconstruir a matriz buy/sell por nivel de preco dentro de cada candle. A lib open source kline-orderbook-chart faz exatamente isso: conecta ao aggTrade, atribui cada trade ao barIndex correspondente via timestamp, e chama `footprintAddTrade(barIndex, price, quantity, isBuyerMaker)`.

## Estado do mercado em 2026

Order flow virou linguagem comum entre traders de cripto perpetuais em 2026. Plataformas como ChartWhisperer, CoinXSight, Blackperp e DCT Alpha publicaram frameworks completos integrando delta, CVD, footprint, OI, funding e order book. O consenso pratico: delta diz quem empurrou, absorption diz se o empurrao funcionou. Os dois conceitos sao gateways para todos os outros sinais de order flow (CVD divergence, footprint imbalance clusters, OI flushes, funding squeezes).

Um caso publicado em maio de 2026 (CoinXSight): BTC empurrou para US$ 108.200 em 15 de maio, mas o painel de order flow mostrou CVD virando negativo, com US$ 47M de venda liquida em 4 horas apesar do preco fazendo novos topos. Essa absorption, preco subindo enquanto sellers agressivos dominam, sinalizou exaustao. BTC reverteu para US$ 104.600 (queda de 3.3%) em 36 horas. O Confluence Score marcou 4/10, confirmando a divergencia bearish.

O footprint e a camada "X-ray": revela dentro do candle quem foi agressivo e onde. Imbalances diagonais (>= 3x volume de um lado vs outro) viraram o recurso mais acionavel do footprint, marcados como retangulos vermelhos/verdes ao lado das celulas de preco.

Absorption Initiation Pattern (AIP) emergiu como setup formal: footprint mostra imbalances empilhados no mesmo nivel de preco enquanto o preco recusa, seguido de CVD divergente. Combina informacao intra-candle (footprint) com momentum estrutural (CVD).

### Gates de confluencia em 2026

O framework de 2026 que ganhou tracao (ChartWhisperer) estrutura order flow em 5 gates sequenciais de confirmacao:

1. **Gate 1 (Delta):** quem empurrou agora? Delta do candle atual.
2. **Gate 2 (CVD):** quem esta empurrando consistentemente? Trend da linha CVD.
3. **Gate 3 (Footprint):** onde dentro do candle a batalha aconteceu? Imbalances e stacked levels.
4. **Gate 4 (Liquidity Sweep):** o preco varreu um nivel com delta gritando mas o preco absorveu e recusou. Isso e absorption definida por delta em uma frase.
5. **Gate 5 (CHoCH):** a candle que confirma que a absorption cumpriu seu papel. Change of Character, a reversao confirmada.

Todos os gates sao variacoes dos mesmos dois conceitos: quem empurrou (delta) e se o empurrao funcionou (absorption). Sem esses dois, todos os outros sinais de order flow ficam abafados.

### Armadilhas do order flow em 2026

O consenso tambem formalizou onde order flow engana:

- **Delta isolado sem contexto:** delta positivo num candle nao significa bullish. Pode ser absorcao de venda (preco desce com delta positivo = sellers passivos absorvendo).
- **CVD cumulativo sem reset:** CVD que roda por varios dias mistura regimes. Zerar por sessao e essencial.
- **Footprint sem volume total:** imbalance num nivel com volume total baixo e ruido. Imbalance so conta em niveis com volume significativo.
- **Tick rule em venues sem flag:** ~15% de erro de classificacao infla delta. Sempre preferir venues com flag explicito (Binance `m`).

## Ferramentas e APIs disponiveis

- **Binance aggTrade WebSocket**, tipo: tick flow, custo: gratis, URL: `wss://stream.binance.com:9443/ws/btcusdt@aggTrade`. Direcao via campo `m` (isBuyerMaker). Aggrega trades com mesmo preco/lado/timestamp, reduzindo volume de mensagens.
- **Binance klines REST**, tipo: OHLCV com taker buy, custo: gratis, URL: `https://api.binance.com/api/v3/klines`. Campos `V` (taker buy base) e `Q` (taker buy quote). Permite delta por candle sem tick data.
- **Binance klines WebSocket**, tipo: OHLCV em tempo real, custo: gratis, URL: `wss://stream.binance.com:9443/ws/btcusdt@kline_1m`. Stream `<symbol>@kline_<interval>` com campo `V` e `Q` atualizados a cada 1-2s.
- **Coinglass API V4**, tipo: CVD aggregated + footprint, custo: freemium/pago, URL: https://www.coinglass.com/CryptoApi. Volume Footprint charts e Cumulative Volume Delta agregado cross-exchange. Inclui Aggregated CVD que soma flow de multiplas venues.
- **kline-orderbook-chart (open source)**, tipo: lib JS de footprint, custo: gratis, repo: https://github.com/PhamNhinh/kline-orderbook-chart. Footprint via aggTrade stream, bid/ask volume por nivel de preco. Demo com Binance Futures + Bybit Linear, 5 symbols cada.
- **Kaiko**, tipo: L1 tick-level com direcao, custo: pago (from US$ 1.500/mes), URL: https://www.kaiko.com/products/l1-l2-data. Trade direction explicito por trade. Cobertura 100+ exchanges, entrega via REST, WebSocket, Snowflake, BigQuery.
- **Amberdata**, tipo: trade-level com side, custo: pago institucional, URL: https://www.amberdata.io. Agora parte da Kaiko (aquisicao 2026). 1000+ exchanges, CloudSync para data warehouses.
- **Tardis.dev**, tipo: replay historico de ticks, custo: pago, URL: https://tardis.dev. Replay de order flow historico para backtest. Dados raw exchange-native, L2/L3 deltas.
- **DolphinDB**, tipo: platform de analise de microestrutura, custo: pago, URL: https://medium.com/@DolphinDB_Inc. Usado em estudos de pin bar + VPIN + liquidacoes (2026).

## Por que importa para o crypto-correl-bot

O bot ja tem order flow parcial implementado. Em `scripts/analyze_live.py`:

- `calc_cvd` (linhas 137-142): calcula CVD a partir de trades com `is_buyer_maker`. Correto e funcional.
- `analyze_microstructure.py` (linhas 49-100): computa taker buy/sell ratio por candle, por hora e por dia a partir de `taker_buy_base`.

Lacunas concretas:

1. **Sem deteccao de absorption.** O bot calcula CVD mas nao cruza com movimento de preco para detectar absorption (preco plano + delta forte). Implementar: janela rolling de N candles, flag se |delta| > threshold E |price_change| < threshold. Pseudocodigo:
   ```
   def detect_absorption(candles, window=10, delta_thresh=2*std_delta):
       for each window:
           total_delta = sum(delta)
           price_range = (high.max() - low.min()) / open
           if abs(total_delta) > delta_thresh AND price_range < 0.3%:
               flag absorption (side = sign(total_delta))
   ```
   Sinal de alto valor preditivo para reversao.
2. **Sem delta divergence.** Nao ha deteccao de divergencia preco vs CVD (preco HH com CVD LH). Implementar comparando topos/fundos recentes de preco e CVD com tolerancia de N candles. Divergencia bearish: preco faz topo mais alto, CVD faz topo mais baixo. Divergencia bullish: preco faz fundo mais baixo, CVD faz fundo mais alto.
3. **Sem footprint por candle.** `calc_volume_profile` (linhas 161-202) agrupa volume por preco mas nao separa buy/sell. Estender para retornar matriz buy_volume[i], sell_volume[i], delta[i] por bin de preco dentro do candle. Isso habilita deteccao de stacked imbalances.
4. **CVD por sessao nao zerado.** O CVD do bot e cumulativo desde o inicio dos dados. Para analise intradia, zerar no inicio de cada sessao UTC (ou 00:00 local) e plotar por sessao e mais util. CVD cumulativo de varios dias mistura regimes e perde o sentido de "scoreboard da sessao".
5. **Sem registro de imbalance clusters do footprint.** Detectar niveis com >= 3x volume de um lado seria um sinal de suporte/resistencia intra-candle de curto prazo. Implementar sobre o footprint estendido do ponto 3.
6. **Sem CVD acceleration (segunda derivada).** A aceleracao do CVD (diff do diff) anteceda o flip de momentum. Mesmo antes do CVD virar, a desaceleracao alerta que o lado dominante esta perdendo forca.
7. **CVD vs OI divergence nao cruzado.** O bot tem dados de OI (REST poller em live_collector.py) e CVD. Cruzar os dois: OI subindo + CVD caindo = new shorts agressivos. OI subindo + CVD subindo = new longs. Esse sinal discrimina direcao do positioning novo.

Recomendacao: criar `src/analysis/orderflow.py` com `calc_delta_per_candle`, `detect_absorption(window)`, `detect_cvd_divergence(lookback)`, `calc_footprint(trades, bins)`, `calc_cvd_session(trades, session_start)`, `detect_stacked_imbalances(footprint, threshold=3)`. Integrar no dashboard live como nova secao entre Order Book Imbalance e CVD. Todas as funcoes devem ser testaveis com dados sinteticos (seed fixo, conforme AGENTS.md), cobrindo edge cases: sem trades, todos trades de um lado, preco constante.

## Referencias

- https://chartwhisperer.ca/order-flow (Order Flow & CVD Trading Guide for Crypto Perps, 2026: delta, CVD, absorption, footprint)
- https://dtsystems.dev/blog/order-flow-trading-explained (D&T Systems: CVD, delta, divergences, armadilhas do tick rule)
- https://coinxsight.com/blog/strategy/order-flow-delta-trading-system (caso real BTC US$ 108.200 -> US$ 104.600 em maio 2026, divergencia bearish)
- https://bullcryptosignals.com/blog/order-flow-footprint-imbalances-aip-cvd/ (footprint, imbalances diagonais, Absorption Initiation Pattern)
- https://united-daytraders.com/blog/delta-cvd-advanced-order-flow (delta por nivel de preco, footprint view, CVD line)
- https://github.com/PhamNhinh/kline-orderbook-chart/blob/main/docs/guides/footprint-chart.md (implementacao footprint via aggTrade stream, campo isBuyerMaker)
- https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md (stream aggTrade, campo m)
- https://github.com/binance/binance-public-data (klines com taker_buy_base_asset_volume)
