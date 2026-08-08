# Topico: Plataformas quant e profissionais de dados de cripto (Coinglass, Laevitas, Velo, Amberdata, Kaiko, Glassnode, Nansen, Skew)

**Data:** 2026-07-15
**Categoria:** Mercado Competitivo

## TL;DR

O segmento de plataformas quant/profissionais de dados de cripto e onde o
dinheiro institucional compra infraestrutura. Em 2026, esse mercado passou por
consolidacao: Kaiko adquiriu Amberdata em junho de 2026, criando a maior
plataforma regulada e independente de dados de ativos digitais. Coinglass
domina o agregamento de dados de derivados (liquidacoes, OI, funding rate) com
pricing acessivel ($29 a $699/mes), enquanto Laevitas se posiciona em opcoes
com um modelo inovador de micropagamentos USDC via HTTP 402. Glassnode e
Nansen lideram on-chain analytics com filosofias opostas: Glassnode para
macro/inteligencia de mercado, Nansen para rastreamento de wallets e smart
money. O gap mais interessante para o crypto-correl-bot: nenhuma plataforma
combina dados de derivados (funding, OI, liquidacoes) com analise de correlacao
multi-asset em um unico produto acessivel ao retail/semi-pro. Coinglass tem os
dados, mas nao faz correlacao. Laevitas tem opcoes, mas nao cobre spot
correlation. A opportunity esta em orquestrar essas fontes.

## Explicacao para criancas

Existem ferramentas que nao fazem trades, mas mostram informacao tao importante
que traders profissionais pagam centenas ou milhares de dolares por mes para
acessa-la. E como ter um radar que mostra onde os peixes estao antes de todo
mundo. Coinglass mostra onde estao acontecendo liquidacoes (pessoas sendo
forçadas a vender). Laevitas mostra o mercado de opcoes (apostas sobre o preco
futuro). Glassnode mostra se os investidores de longo prazo estao comprando ou
vendendo. Nansen mostra quais carteiras "espertas" estao comprando. Kaiko e
Amberdata (agora uma empresa so) vendem dados de altissima qualidade para
bancos e fundos. Cada uma ve uma parte diferente do mercado. Nenhuma ve tudo
junto.

## Como funciona (o segmento de mercado)

O segmento de plataformas quant/profissionais atende tres publicos distintos:

1. **Retail/semi-pro traders** que querem dados de derivados e on-chain que
   exchanges nao fornecem de forma agregada. Exemplos: Coinglass, Laevitas
   (tier free e Pro).

2. **Desenvolvedores e quants** que precisam de APIs de dados para alimentar
   modelos e bots. Exemplos: Coinglass API, Amberdata, Kaiko, Glassnode API.

3. **Instituicoes (fundos, bancos, market makers)** que precisam de dados de
   qualidade regulada, com SLA, latencia baixa, e cobertura ampla. Exemplos:
   Kaiko, Amberdata (agora combinados), Velo.

A cadeia de valor tem tres camadas:

- **Coleta:** ingestao de dados de exchanges (CEX e DEX), blockchains, e
  venues OTC. Cada exchange tem formatos diferentes, rate limits diferentes,
  e qualidade de dados variavel.

- **Normalizacao e enriquecimento:** transformar dados brutos em series
  temporais consistentes, com tratamento de survivorship bias, adjustment de
  funding intervals, e agregacao cross-exchange. Este e o valor real.

- **Distribuicao:** APIs REST, WebSocket, Snowflake sharing, flat files (CSV/
  Parquet), e dashboards visuais. O pricing varia de free a $10K+/mes.

O diferencial competitivo neste segmento nao e ter dados (todos tem acesso as
mesmas exchanges), mas sim: cobertura de exchanges, profundidade historica,
qualidade de normalizacao, latencia, e features analiticas proprietarias
(labels de wallets, vol surface calibration, liquidation heatmaps).

## Estado do mercado em 2026

### Players principais

**Coinglass:** o aggregator dominante de dados de derivados de cripto. Em 2026
lancou a API V4, expandindo de derivados para spot, options, ETF, e on-chain
data. Cobertura: 30+ exchanges para futures (Binance, OKX, Bybit, Bitget,
Deribit, Hyperliquid, dYdX, Drift, e outras), 4+ para options (Deribit, Binance,
OKX, Bybit). Endpoint de funding rate historico com OHLC, OI-weighted e
volume-weighted funding, liquidation heatmaps com 3 modelos, liquidation maps,
max pain para opcoes, long/short ratios, e order flow analytics L2/L3. Pricing
da API: Hobbyist $29/mes, Trader $79/mes, Analyst $299/mes, Professional $699/
mes, Enterprise custom. Rate limits de 30 a 1200 req/min. URL:
https://www.coinglass.com

**Laevitas:** plataforma especializada em dados de derivativos, com foco em
opcoes. Oferece option chains completos, trade flows (blocks e strategies),
Greeks, implied volatility, vol surface calibration, term structure, e funding
rates. Cobertura: Binance, Deribit, OKX, Bybit, Hyperliquid. Inovacao em 2026:
API V2 com pay-per-request via micropagamentos USDC usando HTTP 402 (protocolo
onde o servidor responde 402 Payment Required e o cliente paga por request). Sem
API key necessaria para este modo. Pricing: Free ($0), Pro ($50/mes por seat,
3 dashboards, 1 ano de historico), Custom Enterprise ($500/mes por seat, API
historica, dashboards ilimitados). URL: https://laevitas.ch

**Kaiko + Amberdata:** em junho de 2026, Kaiko adquiriu Amberdata, criando a
maior plataforma regulada e independente de dados e analise de ativos digitais.
A entidade combinada cobre: market data L1/L2, derivativos analytics (options
tooling, GVOL), on-chain data, DeFi, RWA, reference rates, indices, e AI-driven
market intelligence. Amberdata traz on-chain + DeFi + derivativos; Kaiko traz
institutional market data, indices, e compliance. Pricing: parcialmente publico.
Amberdata On-Demand tem tiers publicos (Trial, On-Demand, Enterprise), mas a
maioria do packaging institucional requer quote de vendas. Estimates: ~$600/mes
por exchange para On-Demand; Kaiko L1 Aggregations ~$1.000/mes, L2 Tick-Level
~$2.500/mes. URL: https://amberdata.io e https://kaiko.com

**Glassnode:** lider em on-chain analytics com abordagem macro. Indicadores
proprietarios: Long-Term Holder (LTH) supply, exchange reserves, realized cap,
SOPR, entity-adjusted metrics. Cobertura: Bitcoin, Ethereum, e principais L1s.
Diferencial: metodologia rigorosa com PIT (point-in-time) data, data
finalization guidance, e documentacao detalhada. Distribuicao: API REST, CLI,
Snowflake sharing, Excel add-in, alerts, Workbench. Pricing: transparente em
alto nivel, mas capabilities de maior valor splitadas across tiers. Free tier
com metricas limitadas; Advanced e Enterprise com pricing por vendas. URL:
https://studio.glassnode.com

**Nansen:** lider em wallet intelligence e smart money tracking. Banco de dados
com 250M+ wallets etiquetadas. Categoriza wallets em: smart money, funds,
institutions, CEX, DeFi protocols, e participantes ativos de ecossistema.
Diferencial vs Glassnode: foco em entity-level intelligence (quem esta
comprando) vs market-level intelligence (o que o mercado esta fazendo). API
com address labels, premium labels (smart money, alpha trader) em endpoint
separado. Cobertura: 25+ chains incluindo Ethereum, Solana, Arbitrum, Base,
Hyperliquid, Monad, Sonic, Tron. Pricing: ~$150/mes+ para o tier de entrada.
URL: https://www.nansen.ai

**Velo:** plataforma de dados institucionais de cripto. Foco em dados de
mercado de alta qualidade para trading desks e fundos. Cobertura e pricing:
nao confirmado publicamente em detalhe. Posicionamento: competidor de Kaiko e
Amberdata no segmento institutional.

**Skew:** plataforma de analytics de derivativos de cripto, com foco em
options e perpetuals. Historicamente focada em implied volatility, Greeks, e
order flow de derivativos. Em 2026, parte do ecossistema institutional. URL e
pricing: nao confirmado publicamente em detalhe.

### Consolidacao e M&A

O evento mais significativo de 2026 foi a aquisicao da Amberdata pela Kaiko
(junho de 2026). Esta consolidacao:

- Criou a unica plataforma regulada e independente de dados e analytics, indices
  e infraestrutura de dados para ativos digitais.
- Combinou o on-chain + DeFi + derivativos da Amberdata com o institutional
  market data + indices + compliance da Kaiko.
- Sinaliza que o mercado de dados institucionais esta maduro o suficiente para
  consolidacao, com economias de escala em coverage e reducao de duplicacao.
- Cria incerteza de packaging e roadmap para clientes existentes de ambas.

### Tendencias

1. **Pay-per-request e micropagamentos:** Laevitas introduziu HTTP 402 com
   pagamentos USDC por request, eliminando a necessidade de API key e
   assinatura. Modelo inovador que pode se espalhar.

2. **AI-native data access:** Laevitas oferece "AI-native MCP" (Model Context
   Protocol), permitindo que agentes de IA acessem dados diretamente. Amberdata
   lancou "Amberdata Intelligence", hub institucional AI-driven.

3. **Expansao de coverage para DEX e DEX perp:** Coinglass agora inclui
   Hyperliquid, dYdX, Drift, Apex, e outros DEX perps nos seus feeds
   agregados, refletindo a migracao de volume para DEXs.

4. **On-chain + market data convergence:** a aquisicao Kaiko-Amberdata e o
   sintoma de que clientes querem on-chain e market data de uma fonte, nao duas.

## Ferramentas e APIs disponiveis

| Nome | Fundacao | Pricing | Publico-alvo | Diferencial | URL |
| --- | --- | --- | --- | --- | --- |
| Coinglass | ~2020 | $29 a $699/mes (API) | Retail a pro traders | Aggregator de derivados, liquidation heatmaps, 30+ exchanges | https://www.coinglass.com |
| Laevitas | ~2021 | $0 a $500/mes/seat | Pro traders e quants de opcoes | Vol surface calibration, pay-per-request USDC, AI-native MCP | https://laevitas.ch |
| Kaiko | ~2017 | ~$1.000 a $2.500+/mes | Instituicoes, compliance | Market data regulada, indices, L2 tick-level | https://kaiko.com |
| Amberdata (Kaiko) | ~2017 | ~$600+/mes por exchange | Instituicoes, quants | On-chain + market + DeFi + derivativos, Snowflake sharing | https://amberdata.io |
| Glassnode | ~2017 | Free a Enterprise (sales) | Investidores e researchers | Macro on-chain metrics, LTH supply, entity-adjusted, metodologia rigorosa | https://studio.glassnode.com |
| Nansen | ~2019 | ~$150/mes+ | Traders, fundos, BD teams | 250M+ wallets etiquetadas, smart money tracking, 25+ chains | https://www.nansen.ai |
| Velo | nao confirmado | nao confirmado | Trading desks institucionais | Dados institucionais de cripto | nao confirmado |
| Skew | ~2018 | nao confirmado | Quants de derivativos | Options IV, Greeks, order flow de perps | nao confirmado |

## Por que importa para o crypto-correl-bot

### Oportunidade

O crypto-correl-bot vive na intersecao que nenhuma plataforma cobre
completamente: correlacao entre ativos de cripto usando dados de derivados.
Coinglass tem os dados de derivados (funding, OI, liquidacoes) mas nao faz
correlacao multi-asset. Glassnode tem on-chain mas nao tem derivados. Laevitas
tem opcoes mas nao cobre spot correlation. Nansen tem wallet intelligence mas
nao tem market data de derivados. O bot pode ser o orchestrator que combina
essas fontes em um produto unico.

### Gaps identificados

1. **Nenhum produto combina derivados + correlacao:** Coinglass fornece os
   blocos de dados (funding rate, OI, liquidacoes) mas nao oferece analise de
   correlacao entre ativos baseada nesses dados. Um trader que quer saber "BTC
   e ETH estao correlacionados via funding rate divergence?" precisa construir
   isso manualmente.

2. **Pricing gap entre retail e institucional:** Coinglass ($29 a $699/mes) e
   acessivel, mas Kaiko/Amberdata ($1.000 a $10.000+/mes) e proibitivo para
   retail/semi-pro. Existe um gap de mercado para dados de qualidade
   intermediaria a pricing intermediario.

3. **Vol surface para retail inexistente:** Laevitas e Skew tem vol surfaces
   profissionais, mas o retail trader nao tem acesso a implied volatility de
   cripto de forma simples e integrada com seu workflow de trading.

4. **On-chain + derivados desconectados:** a aquisicao Kaiko-Amberdata mostra
   que o mercado quer convergencia, mas o produto combinado ainda e
   institucional. Para retail/semi-pro, on-chain (Glassnode/Nansen) e derivados
   (Coinglass) continuam em plataformas separadas.

### Onde podemos competir ou aprender

- **Aprender com Coinglass API V4:** a estrutura de endpoints (funding rate
  OHLC history, OI-weighted funding, liquidation aggregated history) e
  exatamente o que o crypto-correl-bot precisa consumir. Estudar o schema e
  rate limits para planejar ingestao.
- **Aprender com Laevitas pay-per-request:** o modelo HTTP 402 com USDC e
  inovador e pode inspirar um modelo de monetizacao do bot (pay per correlation
  query, pay per signal).
- **Aprender com Glassnode metodologia:** a abordagem PIT (point-in-time) e
  data finalization guidance e essencial para evitar look-ahead bias no
  backtest do bot.
- **Competir no nicho de correlacao de derivados:** posicionar o bot como a
  ferramenta que faz o que Coinglass nao faz: analisar correlacao entre
  ativos usando dados de derivados (funding, OI, liquidacoes) como sinais.
- **Integrar, nao duplicar:** nao tentar construir o que Coinglass ja faz
  (agregar dados de 30+ exchanges). Consumir a API do Coinglass e adicionar a
  camada de correlacao que falta.

## Referencias

1. Coinglass. Crypto Data API Pricing.
   https://www.coinglass.com/pricing
2. Coinglass. Endpoint Overview (API V4).
   https://docs.coinglass.com/reference/endpoint-overview
3. Coinglass. API Introduction.
   https://docs.coinglass.com/reference/getting-started-with-your-api
4. Laevitas. Homepage e Pricing.
   https://laevitas.ch/
5. Laevitas. API V2.
   https://apiv2.laevitas.ch/
6. Amberdata. Homepage (Kaiko acquisition announcement).
   https://amberdata.io/
7. RFP Wiki. Amberdata Crypto Cost Drivers (2026).
   https://www.rfp.wiki/crypto/digital-assets-nfts/crypto-data-analytics-market-risk/amberdata
8. Startupik. Glassnode vs Nansen: On-Chain Analytics.
   https://startupik.com/glassnode-vs-nansen-which-on-chain-analytics-tool-is-better/
9. RFP Wiki. Glassnode vs Nansen (2026).
   https://www.rfp.wiki/crypto/digital-assets-nfts/crypto-data-analytics-market-risk/glassnode/nansen
10. DennTech Blog. On-Chain Analytics Tools Guide 2026.
    https://denntech.io/blog/on-chain-analytics-tools-traders-guide
11. Startupik. Nansen vs Dune vs Glassnode Deep Comparison.
    https://startupik.com/nansen-vs-dune-vs-glassnode-deep-comparison/
12. Spark. Crypto Market Data APIs: Providers, Pricing, and Coverage.
    https://www.spark.money/tools/crypto-data-api-comparison
