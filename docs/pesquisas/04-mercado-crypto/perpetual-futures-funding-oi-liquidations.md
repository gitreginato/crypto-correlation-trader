# Topico: Perpetual Futures, Funding Rate, Open Interest e Liquidations

**Data:** 2026-07-15
**Categoria:** Mercado Cripto

## TL;DR

Perpetual futures (perps) sao contratos derivados sem data de vencimento, mantidos
ancorados ao preco spot por um mecanismo de funding rate. Longs pagam shorts quando
funding e positivo (mercado bullish), shorts pagam longs quando negativo (bearish).
Open Interest (OI) mede o total de contratos em aberto: quando OI sobe junto com
preco, novos longs entram; quando OI cai com preco, posicoes sao fechadas a forca.
Liquidations sao o motor das cascadas de preco em cripto: quando a margem cai abaixo
do maintenance margin, a exchange fecha a posicao a forca, gerando venda automatica
que derruba o preco e dispara mais liquidacoes. Em 10 de outubro de 2025, ocorreu a
maior liquidacao da historia: $19 bilhoes em 24 horas, OI caiu 43% de $217B para
$123B. Binance domina derivativos com 34.9% de market share em Q1 2026. Hyperliquid
lidera os perp DEX com ~72% de share, mas perp DEX:CEX caiu para 10% em abril 2026
apos pico de 13% em novembro 2025. A tendencia de 2026 e funding continuo (per-block)
em vez do intervalo classico de 8 horas.

## Explicacao para criancas

Imagina que voce quer apostar que o Bitcoin vai subir, mas nao quer comprar Bitcoin de
verdade. Voce faz um contrato com alguem que acha que vai cair. Voces apostam entre si.

O problema e: como garantir que o contrato fica perto do preco real do Bitcoin? Se o
contrato ficar muito mais caro que o Bitcoin real, todo mundo vai querer apostar que
sobe, e ninguem aposta que desce. Para resolver isso, existe uma taxa chamada funding.
Quando muita gente aposta que sobe, quem aposta que sobe paga uma taxa para quem aposta
que desce. Isso desencoraja todo mundo de ficar do mesmo lado.

Open Interest e simplesmente contar quantos contratos estao abertos no momento. Se
muita gente esta apostando, o numero sobe. Se gente esta saindo, cai.

Liquidacao e quando voce apostou com dinheiro emprestado e o preco foi contra voce.
A bolsa fecha sua aposta a forca antes que voce perca mais do que tem. O problema e
que isso cria uma bola de neve: a venda forca derruba o preco, o que faz mais gente
ser liquidada, o que derruba mais o preco.

## Como funciona tecnicamente

### Perpetual futures vs futures classicos

Futures classicos tem data de vencimento (settlement). Um future trimestral de BTC
expira em uma data definida e settle no preco spot naquele momento. Perpetual futures
nao tem vencimento: o trader pode manter a posicao aberta indefinidamente, desde que
tenha margem suficiente e pague o funding rate periodicamente.

O funding rate e o mecanismo de ancoragem. Ele nao e uma taxa cobrada pela exchange:
e uma transferencia peer-to-peer entre longs e shorts. A exchange apenas calcula e
debita/credita nas contas.

### Formula do funding rate

O funding rate tem dois componentes na maioria das exchanges:

1. Interest rate (taxa de juros): representa o custo de carrego. Tipicamente 0.01%
   por periodo de 8 horas (0.00125% por hora em settlement horario), o que anualiza
   ~11% APR. Este componente e fixo e predeterminado.

2. Premium index: mede a diferenca entre o preco do perp e o preco spot (oracle).
   Se o perp esta acima do spot, premium e positivo. Se abaixo, negativo.

Formula generica (estilo Hyperliquid/Binance):

```
F = P + clamp(r - P, -0.0005, +0.0005)

Onde:
  F = funding rate
  P = premium index (media do periodo)
  r = interest rate base
  clamp limita o componente de juros entre -0.05% e +0.05% por periodo
```

O premium index e calculado a partir de impact prices (precos ponderados por volume
para fillar um notional definido em cada lado do orderbook), nao do mid price. Isso
torna o funding resistente a manipulacao por ordens finas longe do mercado.

### Intervalos de funding

- Binance, OKX, Bybit: intervalo classico de 8 horas (00:00, 08:00, 16:00 UTC)
- Hyperliquid: calcula sobre 8h mas settle a cada hora (1/8 da taxa por hora)
- dYdX v4: settle a cada hora com TWAP do premium index
- Tendencia 2026: funding continuo (per-block), habilitado por oracles sub-100ms
  como Pyth Network. Reduz gaming nos instantes antes do settlement e suaviza o
  alinhamento de preco.

### Open Interest (OI)

OI e o total de contratos em aberto (nao fechados) em um dado momento. Cada contrato
em aberto tem um long e um short. OI sobe quando novos contratos sao abertos, cai
quando posicoes sao fechadas (manualmente ou por liquidacao).

Interpretacao combinada de OI + preco + funding:
- OI subindo + preco subindo + funding positivo: novos longs entrando, mercado
  bullish e alavancado. Risco de long squeeze se preco cair.
- OI subindo + preco caindo + funding negativo: novos shorts entrando, mercado
  bearish. Risco de short squeeze se preco subir.
- OI caindo + preco caindo: longs sendo fechados a forca (liquidacoes), deleveraging.
- OI caindo + preco subindo: shorts sendo fechados (cover), rally com menos alavancagem.

### Liquidations e cascada

Cada exchange tem um maintenance margin requirement (MMR). Binance usa 0.5% para
BTC perps na tier mais baixa. Quando o equity da conta cai abaixo do MMR, a exchange
fecha a posicao a forca via engine de liquidacao.

A cascada funciona assim:
1. Um shock de preco derruba o mercado alguns por cento.
2. Traders alavancados atingem o MMR e sao liquidados.
3. A liquidacao gera ordens de mercado de venda (para longs) que derrubam mais o preco.
4. Mais traders atingem MMR, mais liquidacoes, mais venda.
5. Market makers recuam, spreads abrem, ordens param de absorver a venda.
6. O resultado e uma wick (pavio) grande seguido de recuperacao parcial.

Diferentes exchanges liquidam de forma diferente. Binance usa parcial close em alguns
casos. Hyperliquid tem auto-deleveraging (ADL) que pode quebrar estrategias delta-neutral
fechando shorts de hedge a forca, expondo o trader ao spot.

### Squeeze de long e short

- Long squeeze: preco cai, longs alavancados sao liquidados, venda forca amplifica
  a queda. Ocorre quando OI e funding estao altos (longs crowded).
- Short squeeze: preco sobe, shorts alavancados sao liquidados, compra forca amplifica
  a alta. Ocorre quando funding esta muito negativo (shorts crowded).

O squeeze de 67 dias de funding negativo em BTC (ate maio de 2026) e um exemplo: funding
 ficou negativo por ~201 settlements (3 por dia x 67 dias) enquanto BTC subia de $74K
 para $83K. Shorts pagaram continuousmente ate que a margem foi erodida e o squeeze
 os forcou a fechar (~$590M em 24h em 18 de maio).

## Estado do mercado em 2026

### Market share de derivativos

Dados do CoinGlass Q1 2026 e TokenInsight 2025 Annual Report:

| Exchange | Share derivativos Q1 2026 | Volume acumulado Q1 2026 |
|----------|--------------------------|--------------------------|
| Binance  | 34.9%                    | $4.90T                   |
| OKX      | ~15%                     | $2.19T                   |
| Bybit    | ~10%                     | $1.49T                   |
| Gate     | ~8%                      | nao confirmado           |
| Bitget   | ~7%                      | nao confirmado           |

Binance tem ~2.2x o volume do OKX (segundo lugar) e ~2.2x o OI medio do Bybit.
Derivativos totalizaram $85.7T em volume em 2025, media de $264.5B/dia.

No lado DEX, Hyperliquid dominou com ~72% de market share em 2025, mas viu uma quebra
estrutural em setembro/outubro quando challengers escalaram. O ratio perp DEX:CEX
subiu de 3% para 13% em novembro de 2025, depois caiu para 10% em abril de 2026. Em
abril de 2026, Hyperliquid processou $190.28B em volume, ~3.9% do total entre perp
exchanges, ranqueando #9 (atras de BingX com $196.81B).

### O evento de 10-11 de outubro de 2025

A maior liquidacao da historia do cripto:
- $19 bilhoes liquidados em 24 horas (1.6 milhoes de traders afetados)
- BTC caiu para $104,782 (ate entao em ~$122K); ETH para $3,436
- Altcoins levaram 86% das liquidacoes ($16B de $19B total)
- OI total caiu 43%: de $217B para $123B
- Hyperliquid teve a maior contracao: OI caiu 57% (de $14B para $6B)
- Bitwise calculou ~$65B de OI desapareceram em todas as venues
- Funding virou negativo broadamente: SOL funding hitou -0.23% em intervalos
- Glassnode flagou aggregate funding no nivel mais baixo desde o bear de 2022
- USDe depegged para $0.65 na Binance, trigger secundario de liquidacoes

O trigger foi o anuncio de Trump de 100% tariff sobre importacoes chinesas. Como
equities estavam fechados (sexta-feira), traders nao podiam mover colateral de acoes
para cripto. Engines de liquidacao dispararam simultaneamente em multiplas exchanges,
compondo a queda. O evento foi 9x maior que o crash de fevereiro de 2025 e 19x maior
que o FTX collapse de novembro 2022.

### Funding rate em regime normal

Em condicoes normais de mercado, o funding de BTC perps gravita em torno de +0.01%
por periodo de 8h. Dados do CoinGlass mostram clustering forte neste valor central.
Desvios materiais so aparecem em volatilidade aguda. Isso e por design: o componente
de interest rate predeterminado em 0.01% atua como atrator.

### Tendencia de funding continuo

Em 2026, a migracao para funding continuo ou per-block acelera. Hyperliquid settle
por hora, dYdX v4 por hora, Drift usa TWAP com block times rapidos da Solana. A
vantagem e que elimina a janela exploritavel de 8h onde traders tentam fechar posicoes
 segundos antes do settlement para evitar o pagamento. Com Pyth Network entregando
feeds sub-100ms, o funding pode accrue em tempo real sem depender de snapshots.

## Ferramentas e APIs disponiveis

### Binance Futures API (principal para o bot)

Endpoints publicos sem autenticacao para market data:

- `GET /fapi/v1/fundingRate`: historico de funding rate. Params: symbol, startTime,
  endTime, limit (max 1000). Retorna array com symbol, fundingRate (decimal string),
  fundingTime (ms), markPrice.
- `GET /fapi/v1/openInterest`: OI atual de um symbol. Retorna openInterest (em
  contratos), symbol, time.
- `GET /futures/data/openInterestHist`: historico de OI. Params: symbol, period
  (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d), limit.
- `GET /fapi/v1/premiumIndex`: mark price, index price, funding rate atual, next
  funding time.
- `GET /fapi/v1/forceOrders`: historico de liquidacoes (requer autenticacao para
  ordens proprias; existe endpoint publico em /fapi/v1/allForceOrders em alguns casos).
- `GET /fapi/v1/fundingInfo`: configuracao de funding (intervalo, cap/floor) por
  symbol.

Funding acontece a cada 8h em 00:00, 08:00, 16:00 UTC. Binance nao cobra fee sobre
o funding: e transferencia pura entre longs e shorts.

### CoinGlass (agregador)

CoinGlass agrega OI, funding, liquidacoes e market share de multiplas exchanges.
Tem API publica limitada e dashboards. Fonte dos dados de market share e liquidacao
usados neste documento. URL: coinglass.com

### Hyperliquid API

Hyperliquid expoe uma API HTTP/WS para funding, OI e oracle prices. O funding e
calculado sobre 8h mas settle por hora (1/8 do rate). Formula documentada:
`F = P + clamp(r - P, -0.0005, +0.0005)` onde P e o premium index medio e r e
0.01%/8h. Oracle e mediana ponderada de CEX spot prices computada por validators.
Docs: hyperliquid.gitbook.io

### Outras exchanges

- OKX: endpoints publicos similares a Binance (/api/v5/public/funding-rate,
  /api/v5/public/open-interest). Funding em 8h.
- Bybit: /v5/market/funding/history e /v5/market/open-interest. Funding em 8h.
- dYdX v4: API REST em dydx.exchange, funding horario com TWAP do premium.

### Ferramentas de visualizacao

- CoinGlass: dashboards de OI, funding heatmap, liquidation maps, market share
- Coinglass Deep: nivel de liquidacao estimado por price level
- Hyperliquid Stats: volume, OI, funding por asset em tempo real

## Por que importa para o crypto-correl-bot

O bot opera em Binance e ja tem live_collector.py para funding, OI, long-short ratio,
liquidations e fear-greed. Estes dados sao os inputs mais importantes para inferir
regime de mercado e alavancagem. Aplicacoes concretas:

1. Deteccao de squeeze: combinar OI crescendo + funding extremo (positivo ou negativo)
   + long-short ratio assimetrico para antecipar squeeze. O bot pode reduzir tamanho
   ou evitar entrar contra um setup de squeeze.

2. Filtro de regime: funding persistentemente negativo + OI alta = shorts crowded,
   risco de short squeeze. Funding muito positivo + OI alta = longs crowded, risco
   de long squeeze. O bot pode ajustar bias de estrategia por regime.

3. Liquidation cascade como evento de risco: o evento de out/2025 mostrou que $19B
   pode ser liquidado em 24h. O bot deve ter kill switch que dispara quando OI cai
   >10% em 1h ou quando funding vira abruptamente negativo em multiplas exchanges.

4. Cross-sectional: comparar funding entre ativos para identificar quais estao mais
   crowded. Um ativo com funding 3x a media do setor e candidato a mean reversion.

5. Spot-perp delta: o spot-perpetual price delta (CryptoQuant) indica se o rally e
   spot-driven (saudavel) ou leverage-driven (fragil). Delta negativo persistente
   significa spot liderando, perps trailing. Flip para positivo sinaliza influx de
   leverage, frequentemente precursor de topo local.

6. Dados do live_collector ja cobrem o necessario. O faltante e a integracao com
   Granger causality e lead-lag para validar se funding de BTC prediz moves de
   altcoins (provavelmente sim, com lag de minutos a horas).

## Referencias

1. BitMEX, "State of Crypto Perpetual Swaps 2025" (via bitcoinethereumnews.com)
   https://bitcoinethereumnews.com/crypto/bitmex-report-highlights-structural-shifts-in-crypto-perpetual-swaps-market-in-2025/
2. CoinDesk Research, "Market Spotlight: The $19 Billion Liquidation That Shook Crypto"
   https://www.coindesk.com/research/market-spotlight-the-19-billion-liquidation-that-shook-crypto
3. CoinShares, "Billions in Crypto Liquidations: Inside October's $19B Crash"
   https://coinshares.com/insights/knowledge/billions-in-liquidations-what-happened/
4. CoinGecko, "State of Crypto Perpetuals Report 2026"
   https://www.coingecko.com/research/publications/state-of-crypto-perpetuals-report-2026
5. CoinGlass, "2026 Q1 Cryptocurrency Market Share Research Report"
   https://www.coinglass.com/learn/2026-q1-mktshare-report-en
6. TokenInsight, "Crypto Exchange 2025 Annual Report"
   https://tokeninsight.com/en/research/reports/crypto-exchange-2025-annual-report
7. FinanceFeeds, "Binance, OKX, Bybit Control Over 60% of $85.7T Derivatives Volume"
   https://financefeeds.com/binance-okx-bybit-control-over-60-of-85-7t-derivatives-volume/
8. Binance Developers, "Open Interest, USD-S Margined Futures API"
   https://developers.binance.com/legacy-docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest
9. Hyperliquid Docs, "Funding"
   https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding
10. Bitcoin.com, "How Funding Rates Work on Perp DEXs, Complete Guide (2026)"
    https://www.bitcoin.com/get-started/trading-and-investing/trading-mechanics/how-funding-rates-work-on-perp-dex/
11. CoinPapa, "Same Trade, Different Liquidations: How Exchange Mechanics Decided
    Bitcoin's 67-Day Funding Squeeze"
    https://bitrss.com/same-trade-different-liquidations-how-exchange-mechanics-decided-bitcoin-s-67-day-funding-squeeze-212452
12. CryptoQuant (via CryptoPotato), "Binance Spot-Perpetual Delta Analysis"
    https://cryptopotato.com/this-overlooked-binance-metric-might-predict-bitcoins-next-major-move/
