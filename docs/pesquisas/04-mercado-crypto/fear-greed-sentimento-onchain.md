# Topico: Fear & Greed Index, Sentimento de Mercado e Metricas On-Chain

**Data:** 2026-07-15
**Categoria:** Mercado Cripto

## TL;DR

O Fear & Greed Index (alternative.me) comprime o sentimento do mercado cripto em um
numero de 0 a 100, onde 0 e Extreme Fear e 100 e Extreme Greed. O indice blend cinco
fontes: volatilidade, momentum, social media, dominance e surveys. Em 2026, o indice
flutuou entre 9 (Extreme Fear, em periodo de stress) e 75+ (Greed em rallies). A API
e gratuita, sem autenticacao, com historico desde fevereiro de 2018. Para alem do F&G,
metricas on-chain como NVT, MVRV e SOPR oferecem signal fundamental que TA classico
nao captura: MVRV acima de 3.5 historicamente marca topos de ciclo, abaixo de 1.0
marca fundos. SOPR acima de 1.0 significa holders realizando lucro, abaixo de 1.0
realizando perda. NVT Signal acima de 150 precedeu correcoes de 30-50%. As ferramentas
principais em 2026 sao Glassnode (institucional, 300+ metricas, $29-$799/mes), Nansen
(smart money tracking, $150-$1000/mes), CryptoQuant (exchange flows, gratuito a
pago) e Arkham (entity intelligence). Spot ETFs custodiando ~1.2M BTC (Chainalysis
2026) amorteceram as amplitudes de pico de SOPR e MVRV. Para o bot, F&G e contrarian
signal (extreme fear = oportunidade de compra, extreme greed = alerta de topo),
enquanto on-chain metrics sao filtro de ciclo macro para definir se o regime e
acumulacao, distribuicao ou trending.

## Explicacao para criancas

Imagine que o mercado de cripto e uma pessoa que tem mudancas de humor o tempo todo.
As vezes ela esta com muito medo (Fear) e vende tudo barato. As vezes ela esta com
muita ganancia (Greed) e compra tudo caro.

O Fear & Greed Index e como um termometro desse humor. Quando marca perto de zero,
a pessoa esta com tanto medo que talvez seja hora de comprar (porque tudo esta barato).
Quando marca perto de 100, ela esta tao gananciosa que talvez seja hora de vender
(porque tudo esta caro e ninguem mais vai comprar para empurrar mais alto).

As metricas on-chain sao diferentes: elas olham o que as pessoas realmente fazem com
as moedas delas, nao so o que sentem. Por exemplo, se muita gente esta vendendo
Bitcoin com lucro, e sinal que pessoas estao realizando ganhos (pode ser bom ou pode
ser que o ciclo esta terminando). Se muita gente esta vendendo com prejuizo, e sinal
de desespero (costuma acontecer perto do fundo).

## Como funciona tecnicamente

### Fear & Greed Index (alternative.me)

O indice e calculado diariamente blendendo cinco fontes com pesos iguais:

1. Volatilidade (25%): compara a volatilidade atual do BTC com a media de 30 e 90
   dias. Uma subida incomum de volatilidade e interpretada como mercado medroso.

2. Momentum/Volume (25%): compara o momentum atual (preco atual vs media 30/90 dias)
   com volume. Compra agressiva em mercado subindo e sinal de greed.

3. Social Media (15%): analisa sentiment no Twitter/Reddit sobre cripto. Mais posts
   e sentiment positivo = greed. Usa NLP em mentions de BTC.

4. Dominance (10%): BTC.D subindo pode indicar flight-to-safety dentro do cripto,
   interpretado como fear em altcoins. BTC.D caindo = greed em altcoins.

5. Surveys (15%): pesquisa publica com investidores sobre seu sentimento atual.

O indice atualmente foca em BTC apenas (alternative.me oferece indices separados
para large altcoins em desenvolvimento). Cada data point e avaliado igual ao dia
anterior para visualizar progresso significativo na mudanca de sentiment.

Interpretacao:
- 0-24: Extreme Fear (historicamente proximo a fundos)
- 25-49: Fear
- 50-74: Greed
- 75-100: Extreme Greed (historicamente proximo a topos)

Como contrarian signal: extreme fear tem clusterizado perto de fundos locais e
extreme greed perto de topos locais. Nao e trigger mecanico: pode ficar em extreme
fear por semanas enquanto o mercado continua caindo.

### Sentiment Analysis em cripto

Alem do F&G, existem plataformas dedicadas a sentiment de social media:

- LunarCrush: API v4 com galaxy score e alt rank por token. Integra social activity,
  sentiment, e influencer metrics. Pago (LUNARCRUSH_API_KEY requerido).
- Santiment: platform com on-chain + social metrics combinados. Sentiment de Twitter,
  Reddit, Telegram, e development activity.
- CryptoPanic: news aggregator com API, permite filtrar por sentiment (positive,
  negative, neutral) e importancia.

Sentiment de social media e ruidoso e sujeito a manipulacao (bots, paid promotions,
influencer shilling). Mais util como confirmacao de signal on-chain do que como
signal primario.

### Metricas on-chain fundamentais

#### NVT (Network Value to Transactions)

```
NVT = Market Cap / On-Chain Transaction Volume (daily, adjusted)
NVT Signal = 90-day MA of NVT
```

NVT normaliza valoracao por atividade de rede. Interpretacao:
- NVT Signal > 150: rede sobrevalorizada vs atividade observada. Historicamente
  precedeu correcoes de 30-50% (Coin Metrics).
- NVT Signal < 45: frequentemente acompanhou fundos de ciclo.
- Cuidado: definicao de "volume" varia por vendor (adjusted, address-change filtering,
  internal exchange filtering). Trackear um metodo consistente, nao comparar curves
  de vendors diferentes.

High NVT pode significar sobrevalorizacao real OU volume subcontado quando muito
trading acontece off-chain em exchanges centralizadas.

#### MVRV (Market Value to Realized Value)

```
MVRV = Market Cap / Realized Cap
Realized Cap = Sum de todas as coins valorizadas ao preco que cada uma foi movida
               pela ultima vez on-chain (cost basis agregado)
```

MVRV compara o preco de mercado com o cost basis agregado de todos os holders:
- MVRV > 1.0: holder medio esta em lucro
- MVRV < 1.0: holder medio esta underwater (em perda)
- MVRV > 3.5: estagio tardio de bull cycle, probabilidade elevada de distribuicao
  pesada (Glassnode)
- MVRV Z-Score > 7: precedeu os topos de 2013, 2017 e 2021
- MVRV Z-Score < 0: marcou os fundos de 2015, 2019 e 2022

O MVRV Z-Score normaliza o ratio contra seu desvio padrao historico, tornando
comparacoes entre ciclos mais significativas.

Spot ETFs custodiando ~1.2M BTC (Chainalysis 2026) amorteceram as amplitudes de pico
de MVRV porque ETFs movem BTC para custody que nao transaciona on-chain, distorcendo
o realized cap. Thresholds historicos podem ter shiftado.

#### SOPR (Spent Output Profit Ratio)

```
SOPR = Preco de venda das coins que moveram on-chain / Preco de aquisicao dessas
       coins
aSOPR = SOPR ajustado (exclui outputs dos proprios senders, que sao internal moves)
```

SOPR mede se as coins que se moveram on-chain em um dado dia foram vendidas com lucro
ou perda:
- SOPR > 1.0: coins movidas foram vendidas com lucro
- SOPR < 1.0: coins movidas foram vendidas com perda
- SOPR = 1.0: breakeven point, o nivel mais importante

Signal de SOPR em bull market: quando SOPR dipa para 1.0 e bounce, holders se recusam
a vender no breakeven (esperam precos maiores). Este "SOPR reset" e sinal de compra
em bull estabelecido.

Signal em bear market: quando SOPR sobe para 1.0 e rejeita, holders aproveitam
breakeven para sair, pressao de venda continua.

aSOPR e melhor lido como tendencia rolling de 7 dias, nao como ponto diario.

#### Exchange Flows

- Exchange Inflow: BTC movido para wallets de exchange (intencao de venda potencial)
- Exchange Outflow: BTC movido para fora de exchange (acumulacao, cold storage)
- Net Flow = Inflow - Outflow: negativo sugere acumulacao, positivo sugere distribuicao
- Stablecoin Reserves: supply de USDT/USDC em exchanges, proxy de poder de compra
  disponivel

#### Whale Movements

- Movimentacoes grandes (>1000 BTC ou >10000 ETH) trackeadas por Nansen e Arkham
- Whale accumulation: grandes enderecos comprando em downtrends = bullish
- Whale distribution: grandes enderecos vendendo em uptrends = alerta de topo

### Integracao: F&G + On-Chain + OI

Combinacao de signals que o bot pode usar:
- F&G em Extreme Fear + MVRV < 1.0 + SOPR < 1.0 + Exchange Outflow positivo: setup
  classico de fundo de ciclo, acumulacao.
- F&G em Extreme Greed + MVRV > 3.5 + SOPR > 1.05 + Exchange Inflow positivo: setup
  classico de topo, distribuicao.
- F&G subindo de Fear para Greed + OI subindo + Funding positivo: bull trend
  alavancado, saudavel ate funding ficar extremo.

## Estado do mercado em 2026

### Fear & Greed em 2026

O indice mostrou amplitude extrema em 2026. Em periodo de stress (evento de outubro
de 2025), o F&G caiu para ~9 (Extreme Fear). Em rallies subsequentes, subiu para 75+
(Greed). O comportamento confirma que F&G e volatil e reativo a eventos macro, nao
um indicator smooth.

Multi-source F&G: em 2026, surgiram aggregators que blendam F&G de alternative.me,
CoinMarketCap e outras fontes em um score unico (cryptodataapi.com). A ideia e que
average de fontes independentes suaviza quirkis de metodologia individual.

### Custodia de ETFs e impacto on-chain

Chainalysis 2026 estima que spot ETFs custodiam ~1.2M BTC. Isso tem dois efeitos:

1. Realized Cap distortion: BTC em ETF custody nao transaciona on-chain, entao o
   "last moved price" fica estagnado. Isso amortiza as amplitudes de MVRV e SOPR.
   Thresholds historicos (MVRV > 3.5 = topo) podem estar shiftados para cima.

2. Exchange flows: BTC que iria para exchanges agora vai para ETF authorized
   participants. Net flow de exchange perde signal que tinha antes de 2024.

Mais de 70% dos analistas institucionais combinam pelo menos duas das tres familias
(NVT, MVRV, SOPR) em seu processo de 2026 (Glassnode weekly report).

### Ferramentas on-chain em 2026

O landscape de ferramentas consolidou em 2026 com posicoes claras:

| Ferramenta | Forca principal | Preco 2026 |
|------------|-----------------|------------|
| Glassnode   | Macro on-chain, 300+ metricas, 24 chains | Free / $29 / $799 mes |
| Nansen      | Smart money, wallet labeling, 100M+ addresses | $150 / $1000 mes |
| CryptoQuant | Exchange flows, miner data, actionable dashboards | Free a pago |
| Arkham      | Entity intelligence, wallet tracking | Free a custom |
| Token Terminal | Protocol fundamentals, revenue metrics | Free a pago |
| DefiLlama   | TVL, DEX volumes, gratuito | Gratis |

Glassnode Studio pricing 2026:
- Free: 20 metricas basicas, delay de 24h
- Advanced: $29/mes (100+ metricas, delay de 10 min)
- Professional: $799/mes (todas metricas, live, API)

Nansen AI 2026:
- VIP: $150/mes (chains limitadas, features basicas)
- Alpha: $1000/mes (todas chains, Smart Money)
- Institutional: custom (API, suporte dedicado)

Segundo relatorio Q4 2025 da Nansen, wallets labeled "Smart Money" outperformaram o
mercado altcoin em 147% sobre 12 meses, com periodo medio de hold de 6.2 semanas.

## Ferramentas e APIs disponiveis

### Fear & Greed API (alternative.me)

- Endpoint: `GET https://api.alternative.me/fng/`
- Sem autenticacao, gratuito
- Params: `limit` (int, default 1, 0 para todo historico desde fev 2018)
- Retorna: `value` (0-100), `value_classification` (Extreme Fear/Greed/etc),
  `timestamp` (Unix), `time_until_update`
- Atualizacao diaria
- Wrapper Python: `rhettre/fear-and-greed-crypto` no GitHub com metodos
  `get_current_value()`, `get_last_n_days(days)`, `get_historical_data(start, end)`

### Glassnode API

- REST API com 300+ metricas
- Endpoint base: `api.glassnode.com/v1/metrics/`
- Exemplos: `/market/mvrv` (MVRV ratio), `/transactions/sopr` (SOPR),
  `/transactions/nvt` (NVT), `/exchanges/flow-total` (exchange flows)
- Auth: API key na URL (`?api_key=KEY`)
- Free tier: 20 metricas, delay 24h
- Professional: $799/mes para live + API

### CryptoQuant API

- Foco em exchange flows, miner data, stablecoin reserves
- Dashboards actionable para traders
- Free tier com metricas basicas
- Professional com API completa

### Nansen API

- Smart Money flows, wallet labeling
- API REST com endpoints para token analytics, wallet flows
- Preco: $150/mes (VIP) a $1000/mes (Alpha)

### Arkham

- Entity intelligence e wallet tracking
- Free sign-up para core Intel platform
- API pricing para uso comercial e custom

### LunarCrush API v4

- Galaxy Score, Alt Rank, social metrics por token
- Requer LUNARCRUSH_API_KEY (pago)
- Integra social activity, sentiment, influencer metrics

## Por que importa para o crypto-correl-bot

O bot ja tem live_collector.py coletando fear-greed. A integracao com on-chain e
sentimento tem 5 aplicacoes concretas:

1. Filtro contrarian de F&G: usar F&G < 25 como filtro para reduzir shorts (mercado
   ja com medo, squeeze de short mais provavel) e F&G > 75 como filtro para reduzir
   longs (mercado ganancioso, correcao mais provavel). Nao usar como signal direcional
   unico, mas como modulador de tamanho de posicao.

2. MVRV como filtro de ciclo: antes de rodar cross-sectional analysis, checar MVRV.
   Se MVRV > 3.5, o mercado esta em estagio tardio de bull: correlacoes podem quebrar
   abruptamente em correcao. Se MVRV < 1.0, mercado em fundo: correlacoes tendem a
   aumentar (tudo cai junto). Segmentar backtests por regime de MVRV.

3. SOPR reset como signal de entrada: em bull market (MVRV > 1.5 e subindo), SOPR
   dipando para 1.0 e bouncing e um signal de compra de alta probabilidade. O bot
   pode usar isso como filtro para estrategias mean-reversion long-bias.

4. Exchange flows como leading indicator: net outflow persistente (acumulacao)
   combinado com stablecoin reserves crescendo e setup bullish (poder de compra
   subindo enquanto supply em exchange cai). O bot pode monitorar isso via CryptoQuant
   ou Glassnode API.

5. Smart money tracking: Nansen Smart Money outperformou altcoin market em 147% em
   12 meses (Q4 2025). O bot pode trackear wallets labeled Smart Money para identificar
   accumulation/distribution antes que afete preco. Isso e mais alpha que TA classico
   em cripto nativo.

6. Caveat ETF: threshold historicos de MVRV e SOPR podem ter shiftado por causa da
   custodia de ETFs (~1.2M BTC). Nao usar thresholds de 2017/2021 mecanicamente em
   2026. Recalibrar com dados de 2024-2026.

## Referencias

1. Alternative.me, "Crypto Fear & Greed Index"
   https://alternative.me/crypto/fear-and-greed-index/
2. Apify, "Crypto Fear and Greed Index Scraper" (atualizado maio 2026)
   https://apify.com/parseforge/alternative-me-fear-greed-scraper/api
3. GitHub rhettre/fear-and-greed-crypto (Python wrapper)
   https://github.com/rhettre/fear-and-greed-crypto
4. GitHub forgequant/sentinel (crypto sentiment stack)
   https://github.com/forgequant/sentinel
5. CryptoDataAPI, "Crypto Fear & Greed Index, Live Multi-Source"
   https://cryptodataapi.com/fear-greed
6. Glassnode Docs, "MVRV Ratio"
   https://docs.glassnode.com/further-information/metric-guides/mvrv/mvrv-ratio
7. Neutralis Insights, "NVT, MVRV, SOPR: Comparison for Investors"
   https://neutralis.finance/insights/nvt-mvrv-sopr-on-chain-comparison
8. Thrive, "On-Chain Analysis & Data: Blockchain Metrics Guide 2026"
   https://thrive.fi/on-chain-analysis
9. Coin Bureau (maio 2026), "Best Crypto Analysis Tools in 2026"
   https://coinbureau.com/review/crypto-research-tools
10. DEXTools, "Best On-Chain Analytics Tools 2026"
    https://www.dextools.io/tutorials/top-5-on-chain-analytics-tools-2026
11. LedgerMind, "Best On-Chain Analytics Tools 2026: 12 Platforms Tested"
    https://theledgermind.com/best-on-chain-analytics-tools/
12. TradfiDeFi, "On-Chain Cycle Indicators: MVRV, SOPR, Puell Multiple, NVT"
    https://tradfidefi.tech/tactics-onchain-indicators/
