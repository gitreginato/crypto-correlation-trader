# Topico: Landscape de APIs de dados para cripto trading em 2026

**Data:** 2026-07-15
**Categoria:** Mercado Competitivo

## TL;DR

O landscape de APIs de dados para cripto trading em 2026 se divide em cinco
camadas: (1) APIs de exchanges centralizadas (Binance, Bybit, OKX, Coinbase),
(2) APIs de exchanges descentralizadas (dYdX, Hyperliquid), (3) oraculos on-chain
(Pyth, Chainlink), (4) aggregators de market data (CoinGecko, CoinMarketCap,
CryptoCompare, Messari), e (5) plataformas de on-chain data (The Graph, Dune,
Flipside). Cada camada tem tradeoffs de custo, rate limit, granularidade e
cobertura. O dado mais dificil de obter de forma gratuita e liquidacao
historica e funding rate historico profundo: exchanges oferecem apenas alguns
meses, e aggregadores cobram por isso. Pyth mudou seu modelo em julho de 2026:
o que era free agora exige assinatura a partir de $500/mes. CoinGecko oferece o
melhor free tier (10K calls/mes, 100 RPM). O gap para o crypto-correl-bot:
funding rate historico profundo (2+ anos) e liquidacao historica agregada so
estao disponiveis em Coinglass ($29+/mes) ou via coleta manual paciente nas
APIs de cada exchange ao longo do tempo.

## Explicacao para criancas

Para saber o preco de uma criptomoeda, voce pode perguntar direto a loja
(exchange) ou perguntar a um guia que junta precos de varias lojas
(aggregator). As lojas grandes (Binance, Bybit, OKX) dao informacao de graca,
mas com limites: voce so pode perguntar tantas vezes por minuto. Se quiser
dados mais antigos, como o preco de 2 anos atras, algumas lojas so guardam
alguns meses. Os agregadores (CoinGecko, CoinMarketCap) cobram uma pequena
mensalidade mas juntam dados de muitas lojas. Para dados de "quem foi
liquidado" e "qual era a taxa de financiamento", e mais dificil: as lojas nao
guardam por muito tempo, e os agregadores que tem esses dados cobram mais. Em
2026, o Pyth, que era de graca, comecou a cobrar $500 por mes.

## Como funciona (o segmento de mercado)

O ecossistema de APIs de dados para cripto trading tem cinco camadas
distintas, cada uma com proposicao de valor diferente:

### Camada 1: APIs de exchanges centralizadas (CEX)

Cada exchange oferece sua propria API REST + WebSocket para market data e
trading. Os dados sao gratuitos (para market data), mas com rate limits
significativamente diferentes:

- **Binance:** sistema de weight. 1.200 weight/min (rolling). GET /ticker/price
  custa 1 weight (1.200 calls/min), mas GET /depth com limit=5000 custa 250
  weight (4 calls/min). IP-based, nao key-based. Violacoes repetidas geram ban
  de IP de 2 min a 3 dias. Headers X-MBX-USED-WEIGHT permitem monitorar consumo.

- **Bybit:** modelo mais simples. 120 req por 5 segundos (sliding window),
  ~24 req/s sustentado. Headers X-Bapi-Limit-Status mostram requests restantes.
  Endpoint de funding rate historico: GET /v5/market/funding/history, retorna
  ate 200 registros por pagina, com paginacao via startTime/endTime.

- **OKX:** split por categoria. Market data: 20 req/2s. Trade: 60 req/2s.
  Endpoint GET /api/v5/public/funding-rate-history com paginacao via
  before/after em fundingTime. Max 100 registros por request. Historico
  tipicamente limitado a alguns meses no endpoint nativo; para dados mais
  profundos (2021+), recomendam provedores terceiros como CoinAPI.

- **Coinbase Advanced Trade:** 10 req/s para endpoints publicos, 10 req/s
  para privados. Limites relativamente conservadores vs concorrentes.

- **KuCoin:** 100 req/10s para publico, 45 req/3s para privado, 100 topics por
  conexao WebSocket. Um dos mais generosos para public data.

### Camada 2: APIs de exchanges descentralizadas (DEX)

DEXs que oferecem APIs publicas para market data:

- **Hyperliquid:** API sem autenticacao para leitura (Info API). POST
  https://api.hyperliquid.xyz/info com JSON body especificando request type.
  Sem KYC, sem API key. Endpoints: allMids (mid prices de todos assets),
  l2Book (ate 20 niveis de order book), candleSnapshot (ate 5.000 OHLCV
  candles, 1m a 1M), clearinghouseState (posicoes do usuario), fundingHistory
  (funding rate historico), predictedFundings. WebSocket para streaming de
  price feeds, order book e fills. Rate limit: baseado em weight units (l2Book
  custa 2 weight). ~$7B volume diario, 200+ mercados perp. Dados de trades
  disponiveis desde abril 2023.

- **dYdX:** API REST para market data, orders, e account. Dados on-chain
  acessiveis via indexers. Cobertura de funding rate e posicoes disponivel.

### Camada 3: Oraculos on-chain

- **Pyth Network:** em julho de 2026, Pyth Core recebeu upgrade transformacional.
  O que era free agora exige assinatura. Starter plan: $500/mes (crypto data,
  1s update frequency). Pro plans: Crypto $2.500/mes, FX $5.000/mes, US
  Equities $5.000/mes, All Asset Classes $10.000/mes. Free tier: view-only
  access via Pyth Terminal, sem API permissions, 10s update frequency. O
  publisher network inclui Fidelity, Revolut, Tradeweb, Jane Street, Jump, DRW,
  Cboe, e 125+ instituicoes. Hermes (web service) entrega price updates via
  REST, SSE streaming, e SDK. Autenticacao via Bearer token obrigatoria desde
  31 de julho de 2026. History API: OHLC candlesticks em formato TradingView
  UDF, com autenticacao desde 24 de julho de 2026.

- **Chainlink:** oraculo push (dados atualizados on-chain por node operators).
  Price feeds disponiveis on-chain em multiples chains. Para leitura off-chain,
  requer RPC calls a smart contracts. Sem API REST direta equivalente ao
  Hermes do Pyth. Pricing: dados on-chain gratuitos (gas costs apenas), mas
  data feeds premium via Chainlink Data Streams (off-chain, low-latency) tem
  pricing comercial.

### Camada 4: Aggregators de market data

- **CoinGecko:** free tier generoso. Demo: $0/mes, 10K credits/mes, 100 RPM,
  50+ endpoints, 60s freshness, 1 ano de historico. Basic: $35/mes (anual
  $29/mes), 100K credits, 300 RPM. Analyst: $129/mes (anual $103/mes), 500K
  credits, 500 RPM, real-time, WebSocket. Lite: $499/mes (anual $399/mes), 2M+
  credits. Modelo de credit flat: 1 credit por call independente do numero de
  data points. 17.000+ CEX coins, 40-50M+ on-chain DEX tokens, 260+ blockchains.
  URL: https://www.coingecko.com/en/api

- **CoinMarketCap:** free tier: 15.000 credits/mes, 50 RPM, 25 endpoints, sem
  historico. Modelo de credit compounding: 1 credit per 100 data points
  retornados, o que pode ser 24x mais caro que CoinGecko para queries
  equivalentes. Hobbyist: $29/mes, 150K credits, 300 RPM. Startup: $79/mes,
  450K credits, 600 RPM. Standard: $299/mes, 2M credits, 750 RPM. Professional:
  $699/mes, 5M credits, 1.200 RPM. Em 2025/2026 dobrou credits e aumentou rate
  limits 10x a 20x. URL: https://coinmarketcap.com/api

- **CryptoCompare (agora CoinDesk Data):** free tier: 100.000 calls/mes, sem
  cartao de credito. Cobertura: 7.000+ assets, 300+ exchanges. Inclui social
  stats (Reddit subscribers, Twitter followers), mining data, e exchange info.
  Pro: ~$79 a $200/mes. Em maio de 2026, CoinDesk retirou o free tier da API.
  Contudo, CryptoCompare mantem seu free tier proprio em
  min-api.cryptocompare.com. URL: https://www.cryptocompare.com

- **Messari:** free tier: 200 RPM uncapped calls. Pro: $30/mes. Enterprise:
  ~$500+/mes, 600 RPM. Cobertura: 40.000+ assets, 210+ exchanges. Diferencial:
  research, governance, fundraising data, e AI Copilot. URL:
  https://messari.io

### Camada 5: On-chain data platforms

- **The Graph:** indexing descentralizado via subgraphs. Desenvolvedores
  escrevem mappings em TypeScript e schemas em YAML. GraphQL API. 60+ redes
  suportadas no Subgraph Studio. Limitacao historica: block-by-block
  processing lento, mas Firehose e Substreams melhoraram throughput. Bom para
  dados especificos de protocolos (DEX swaps, lending events, NFT transfers).
  URL: https://thegraph.com

- **Dune Analytics:** SQL-based on-chain analytics. Free: $0, 2.500 credits/mes.
  Analyst: $75/mes (anual $65/mes), 4.000 credits. Plus: $399/mes (anual
  $349/mes), 25.000 credits. Credit-based: queries complexas custam mais
  credits. 100+ chains com dados completos. Curated tables: dex.trades,
  nft.trades, etc. Datashare para Snowflake/BigQuery/Databricks. URL:
  https://dune.com

- **Flipside:** SQL on-chain com schema crosschain normalizado. Pre-aggregated
  tables (ez_protocol_tvl, ez_dex_swaps, ez_lending_) e granular event data.
  20+ chains. AI agents que monitoram metricas e alertam no Slack. URL:
  https://flipsidecrypto.xyz

## Estado do mercado em 2026

### Onde conseguir dados especificos

**Funding rate historico:**
- Direto da exchange: Bybit (GET /v5/market/funding/history, 200 por pagina),
  OKX (GET /api/v5/public/funding-rate-history, 100 por request, alguns meses),
  Binance (GET /fapi/v1/fundingRate, historico razoavel).
- Aggregador: Coinglass API (funding rate OHLC history, OI-weighted, volume-
  weighted) a partir de $29/mes.
- Profundidade: exchanges nativas tipicamente oferecem alguns meses a 1-2 anos.
  Para 2+ anos, Coinglass ou coleta manual paciente.

**Open interest historico:**
- Direto da exchange: disponivel em Binance, Bybit, OKX via endpoints de
  market data. Granularidade tipica: 5m a 1h candles.
- Aggregador: Coinglass (OI historical, OHLC candlesticks, OI-to-market-cap,
  OI-to-volume, exchange OI dominance).

**Liquidacoes historico:**
- Direto da exchange: Binance e Bybit oferecem endpoints de liquidacao, mas
  com profundidade limitada e sem agregacao cross-exchange.
- Aggregador: Coinglass (pair liquidation history, coin liquidation history,
  aggregated history, liquidation heatmaps com 3 modelos, liquidation maps,
  max pain). Este e o dado mais dificil de obter de graça com qualidade.
- Alternativa: coletar em tempo real via WebSocket de cada exchange e
  armazenar localmente ao longo do tempo.

### Tendencias

1. **Pyth monetizacao:** a transicao de free para $500/mes minimo sinaliza que
   oraculos free estao acabando. O mercado de dados on-chain esta madurando.

2. **CoinDesk/CryptoCompare confusao:** CoinDesk retirou free tier em maio de
   2026, mas CryptoCompare mantem o seu. A relacao entre as marcas (CoinDesk
   Data absorveu CryptoCompare/CCData) criou incerteza para desenvolvedores.

3. **DEX APIs sem friccao:** Hyperliquid oferece API sem KYC, sem API key, sem
   autenticacao para leitura. Isso e um diferencial competitivo vs CEXs que
   requerem registro para rate limits maiores.

4. **Credit-based pricing dominante:** CoinGecko, CoinMarketCap, Dune, e
   Coinglass todos usam sistemas de credits. Entender o modelo de cada um e
   essencial para estimar custo real.

5. **Rate limit wars:** CoinMarketCap aumentou rate limits 10x a 20x em 2025/
   2026, respondendo a pressao de CoinGecko. Competicao beneficia
   desenvolvedores.

## Ferramentas e APIs disponiveis

| Nome | Tipo | Free tier | Pago desde | Rate limit (free) | Diferencial | URL |
| --- | --- | --- | --- | --- | --- | --- |
| Binance API | CEX | Sim (market data) | N/A | 1.200 weight/min | Maior liquidez, weight system flexivel | https://binance-docs.github.io |
| Bybit API | CEX | Sim (market data) | N/A | 120 req/5s | Modelo simples, funding history paginado | https://bybit-exchange.github.io/docs/v5 |
| OKX API | CEX | Sim (market data) | N/A | 20 req/2s (market) | Split por categoria, trade vs market | https://www.okx.com/docs-v5 |
| Coinbase API | CEX | Sim (market data) | N/A | 10 req/s | Regulado EUA, conservative limits | https://docs.cloud.coinbase.com |
| Hyperliquid API | DEX | Sim (sem auth) | N/A | Weight-based | Sem KYC, sem API key, on-chain order book | https://hyperliquid.gitbook.io |
| dYdX API | DEX | Sim | N/A | Variavel | DEX perp on-chain, indexer data | https://docs.dydx.exchange |
| Pyth | Oracle | View-only (Terminal) | $500/mes | N/A | 125+ publishers institucionais, 1s updates | https://docs.pyth.network |
| Chainlink | Oracle | On-chain (gas only) | Data Streams: comercial | N/A | Push oracle, multi-chain, mais adotado | https://chain.link |
| CoinGecko | Aggregator | 10K credits/mes | $29/mes | 100 RPM | Melhor free tier, flat credit model | https://www.coingecko.com/en/api |
| CoinMarketCap | Aggregator | 15K credits/mes | $29/mes | 50 RPM | Brand recognition, compounding credits | https://coinmarketcap.com/api |
| CryptoCompare | Aggregator | 100K calls/mes | ~$79/mes | ~2.000/min | Social stats, mining data, generoso free | https://www.cryptocompare.com |
| Messari | Aggregator | 200 RPM uncapped | $30/mes | 200 RPM | Research, governance, AI Copilot | https://messari.io |
| Coinglass | Derivados agg | Endpoint free limitado | $29/mes | Variavel | Liquidacoes, OI, funding rate agregado | https://www.coinglass.com |
| The Graph | On-chain | Sim (subgraph queries) | N/A | Variavel | GraphQL, subgraphs, 60+ chains | https://thegraph.com |
| Dune | On-chain SQL | 2.500 credits/mes | $75/mes | Variavel | SQL sobre 100+ chains, curated tables | https://dune.com |
| Flipside | On-chain SQL | Sim (com signup) | N/A | Variavel | Crosschain schema, AI alerts | https://flipsidecrypto.xyz |

## Por que importa para o crypto-correl-bot

### Oportunidade

O crypto-correl-bot precisa de tres tipos de dados que tem disponibilidade e
custo diferentes: (1) price OHLCV (facil e gratuito via Binance/CoinGecko),
(2) funding rate historico (medio, gratuito via exchanges mas com profundidade
limitada, ou $29+/mes via Coinglass para profundidade maior), e (3) liquidacao
historica agregada (dificil, melhor via Coinglass API ou coleta WebSocket
propria ao longo do tempo). A estrategia ideal e hibrida: coletar dados free
das exchanges em tempo real via WebSocket (acumulando historico proprio) e
complementar com Coinglass API para dados historicos pre-existentes.

### Gaps identificados

1. **Funding rate historico profundo (2+ anos) sem custo alto:** exchanges
   nativas limitam a meses. Coinglass cobra $29+/mes. A unica alternativa
   gratuita e coleta paciente via API ao longo de meses.

2. **Liquidacao historica agregada cross-exchange:** nenhum free tier oferece
   isso com qualidade. Coinglass e a unica fonte agregada confiavel. Sem
   Coinglass, seria necessario coletar de cada exchange individualmente e
   normalizar.

3. **Pyth era free, agora nao e mais:** bots que dependiam de Pyth para price
   feeds off-chain gratuitos precisam migrar ou pagar $500/mes. Isso afeta
   especialmente projetos que usavam Pyth como referencia de preco.

4. **Fragmentacao de rate limits:** cada exchange tem um modelo diferente
   (weight, sliding window, per-category). Um bot multi-exchange precisa
   implementar logicas de rate limiting diferentes para cada uma, aumentando
   complexidade.

### Onde podemos competir ou aprender

- **Estrategia de dados hibrida:** usar Binance API (free, boa profundidade
  para price OHLCV) como fonte primaria, CoinGecko free tier para dados de
  market cap e metadata, e Coinglass ($29/mes Hobbyist) para funding rate,
  OI, e liquidacoes historicas. Custo total: ~$29/mes para dados de derivados
  profissionais.
- **Coleta WebSocket propria:** implementar coleta de liquidacoes em tempo real
  via WebSocket de Binance, Bybit, OKX, e Hyperliquid, armazenando em Parquet
  localmente. Em 6-12 meses, ter historico proprio sem depender de terceiros.
- **Aprender com Hyperliquid API design:** sem autenticacao, sem KYC, sem API
  key para leitura. Modelar a API do bot (se houver) com essa filosofia de
  baixa friccao.
- **Rate limit abstraction:** implementar uma camada de abstracao no bot que
  normalize os diferentes modelos de rate limit das exchanges, evitando bans
  e 429s.

## Referencias

1. Binance. REST API Documentation (rate limits, IP bans).
   https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md
2. Bybit. API Rate Limit Rules.
   https://bybit-exchange.github.io/docs/v5/rate-limit
3. Bybit. Get Funding Rate History.
   https://bybit-exchange.github.io/docs/v5/market/history-fund-rate
4. GitHub. OKX Funding Rate API (endpoints, rate limits, historical depth).
   https://github.com/lxdys649/okx-funding-rate-api
5. VoiceOfChain Academy. Exchange API Rate Limits: Binance vs Bybit vs OKX.
   https://voiceofchain.com/academy/crypto-exchange-api-rate-limits-comparison
6. Hyperliquid Docs. Perpetuals API endpoints.
   https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
7. HyprSwarm. Hyperliquid API Complete Developer Guide (2026).
   https://hyprswarm.com/blog/hyperliquid-api-guide/
8. Pyth Network. The Pyth Core Upgrade (jul 2026, pricing).
   https://www.pyth.network/blog/the-pyth-core-upgrade
9. Pyth Developer Hub. Fetch Price Updates (Hermes, auth).
   https://docs.pyth.network/price-feeds/core/fetch-price-updates
10. Pyth Developer Hub. History API.
    https://docs.pyth.network/price-feeds/pro/api/history
11. CoinGecko. API Pricing Plans.
    https://www.coingecko.com/en/api/pricing
12. CoinGecko. CoinGecko API vs CoinMarketCap API.
    https://www.coingecko.com/learn/coingecko-api-vs-coinmarketcap-api
13. CoinMarketCap. API Gets Biggest Upgrade (credits, rate limits).
    https://coinmarketcap.com/academy/article/coinmarketcap-api-gets-biggest-upgrade-yet
14. Spark. Crypto Market Data APIs: Providers, Pricing, and Coverage.
    https://www.spark.money/tools/crypto-data-api-comparison
15. FreeAPI.watch. CryptoCompare Free Tier.
    https://freeapi.watch/cryptocompare/
16. CoinStats. Cheaper CoinDesk API Alternatives (CoinDesk free tier retired).
    https://coinstats.app/blog/top-coindesk-api-alternatives-for-crypto-data/
