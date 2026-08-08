# Topico: On-Chain Analytics e DeFi Data para Trading em Cripto

**Data:** 2026-07-15
**Categoria:** Mercado Cripto

## TL;DR

On-chain analytics usa dados da blockchain publica (UTXOs, smart contract events,
wallet balances, gas usage) para inferir comportamento de mercado. Para cripto nativo,
vale mais que TA classico porque captura fundamentals que o grafico de preco nao mostra.
Metricas DeFi-specific (TVL, DEX volumes, lending rates, oracle usage) dao signal sobre
saude e fluxo de capital dentro de protocolos. Em junho de 2026, DeFi TVL esta em
$71.77B (queda de 37.3% YTD), com Ethereum concentrando 53.1% ($38.24B). Dune Analytics
e o padrao para queries SQL customizadas em 20+ chains, com free tier robusto. Flipside
Crypto compete com 30+ chains, unified schema e AI agents built-in. The Graph indexa
eventos via subgraphs para apps. DefiLlama e gratuito e referencia para TVL, DEX volumes,
bridge flows. Nansen lidera wallet intelligence com 100M+ addresses labeled e Smart
Money tracking que outperformou altcoin market em 147% em 12 meses. Para o bot, on-chain
data e complementar aos dados de Binance (preco, OI, funding): enquanto Binance mostra
o que acontece no trading, on-chain mostra o que acontece com o ativo real. Combinar os
dois da uma visao mais completa que qualquer um isoladamente.

## Explicacao para criancas

A blockchain de cripto e como um quadro de avisos publico onde todas as transferencias
de dinheiro sao anotadas. Todo mundo pode ver quem enviou o quê para quem, quando e
quanto. Nada e escondido.

On-chain analytics e ler esse quadro de avisos e tentar entender o que esta acontecendo.
Por exemplo: se muita gente esta tirando Bitcoin das bolsas e guardando, e sinal que
estao guardando para o longo prazo (bullish). Se muita gente esta enviando para as
bolsas, pode ser que queiram vender (bearish).

DeFi e como um banco que funciona sozinho, sem gerente. As pessoas colocam dinheiro,
emprestam, trocam, tudo automatico por codigo. O TVL (Total Value Locked) e quanto
dinheiro tem la dentro. Se o TVL sobe, mais gente confiando no protocolo. Se cai, gente
tirando dinheiro.

Como o quadro de avisos e publico, nos podemos ver coisas que TA classico (so olhar
o grafico de preco) nao mostra. Por isso on-chain vale mais para cripto nativo.

## Como funciona tecnicamente

### Dados on-chain: UTXO model (Bitcoin)

Bitcoin usa o modelo UTXO (Unspent Transaction Output). Cada transacao consome UTXOs
existentes como input e cria novos UTXOs como output. Dados derivaveis:

- Transaction volume: soma dos valores de UTXOs movidos (com ajuste para excluir
  change outputs e internal exchange shuffles)
- Active addresses: enderecos que enviaram ou receberam em um periodo
- Spent outputs: UTXOs consumidos, cada um com o preco de aquisicao (quando foi
  criado) e o preco de gasto (quando foi consumido). Base para SOPR.
- Realized cap: soma de todos os UTXOs valorizados ao preco que cada um foi criado
  (last moved). Base para MVRV.
- Holder cohorts: agrupar UTXOs por idade (long-term holders > 155 dias, short-term
  < 155 dias). LTH supply subindo = acumulacao.
- Exchange flows: UTXOs movidos para/from wallets conhecidas de exchange.

### Dados on-chain: account model (Ethereum e EVM)

Ethereum usa account model. Cada transacao tem from, to, value, gas, e opcionalmente
data para interagir com smart contracts. Dados derivaveis:

- Smart contract events: cada contrato emite eventos (Transfer, Swap, Deposit,
  Withdraw, Liquidation). Indexados por The Graph, Dune, Flipside.
- ERC-20 token transfers: evento Transfer(from, to, value) rastreia movement de
  tokens.
- Gas usage: gas consumed indica atividade economica real na chain. Gas price spikes
  indicam congestionamento e demanda.
- DEX swaps: eventos Swap em Uniswap, Curve, Balancer revelam volume, pair, direction.
- Lending activity: eventos Deposit, Borrow, Repay, Liquidate em Aave, Compound.
- Bridge flows: eventos de lock/mint em bridges indicam cross-chain capital flow.

### Metricas DeFi-specific

#### TVL (Total Value Locked)

```
TVL_protocol = soma de todos os assets depositados no contrato do protocolo
TVL_chain = soma de TVL de todos os protocolos na chain
```

TVL e o metrica mais citado de DeFi. Interpretacao:
- TVL subindo: mais capital entrando no protocolo/chain, bullish para token nativo
  (se capture fee)
- TVL caindo: capital saindo, pode ser flight-to-safety ou loss of confidence
- TVL pode subir por appreciation de token (mercado subindo) sem novos depositos.
  Sempre checar TVL em USD vs em units de token.

#### DEX volumes

Volume de swaps em DEXs (Uniswap, Curve, etc):
- Volume alto = atividade de trading alta, demanda pelo asset
- Volume pode ser mercenary (arbitrage, JIT liquidity) e nao refletir adocao real
- Comparar DEX volume vs CEX volume: razao subindo indica descentralizacao de trading

#### Lending rates

Supply rate (o que LPs ganham) e borrow rate (o que borrowers pagam) em Aave, Compound:
- Borrow rate alto = demanda por alavancagem alta, mercado bullish
- Supply rate alto = escassez de liquidez, risco de liquidacoes
- Utilization rate (borrowed / supplied) > 80% e zona de stress

#### Oracle usage

Oracles (Chainlink, Pyth, RedStone) alimentam precos para DeFi:
- Oracle update frequency indica demanda por dados frescos
- Oracle deviations em stress causam liquidacoes erradas
- Em 2026, Pyth Network entrega feeds sub-100ms, habilitando funding continuo em
  perp DEXs

### Entity adjustment

Dados on-chain brutos tem ruido: exchanges tem centenas de wallets, transferencias
internas inflacam volume. Entity adjustment agrupa wallets da mesma entidade (exchange,
fund, protocol) e net out transferencias internas. Glassnode e CryptoQuant fazem isso.
Sem entity adjustment, volume e flows sao overestimados.

### Decoding smart contract events

Eventos de smart contracts nao sao auto-explicativos. O processo de decode envolve:
1. Ler ABI do contrato (function signatures, event signatures)
2. Match transaction input data contra ABI
3. Decode parametros (amounts, addresses, etc)
4. Mapear para acao semantica (Deposit, Swap, Liquidation)

Plataformas como Dune e Flipside fazem decode automatico para protocolos conhecidos
(tabelas pre-decoded). Para protocolos novos ou obscure, o usuario precisa decode
manualmente.

## Estado do mercado em 2026

### DeFi TVL em 2026

Dados do DeFiLlama em junho de 2026:
- Total DeFi TVL: $71.77B across 453 chains
- Queda de 37.3% YTD (de $114.49B no inicio do ano)
- Queda de 23.8% nos ultimos 90 dias
- A $2B do low de 2026
- Ethereum concentra 53.1% ($38.24B), deepening chain consolidation
- Queda de 59.6% do pico de novembro de 2021 ($177.48B)

A queda de TVL em 2026 coincide com duas shifts estruturais:
1. Concentracao de capital em Ethereum (53.1%, aumentando)
2. Quiet decoupling entre stablecoin supply e DeFi protocols (stablecoins crescendo
   mas nao indo para DeFi, ficando em CEX ou yield products fora de DeFi on-chain)

DEX volume diario em junho de 2026: $7.20B (CoinLaw). Em Q1 2026, perp DEX processaram
$492.7B coletivamente.

### Ferramentas on-chain em 2026: landscape

| Ferramenta | Tipo | Forca | Preco |
|------------|------|-------|-------|
| Dune Analytics  | SQL queries | 20+ chains, community dashboards | Free / pago |
| Flipside Crypto | SQL + AI | 30+ chains, unified schema, AI agents | Free / $200+ |
| The Graph       | Indexing | Subgraphs para apps, decentralized | Pay per query |
| DefiLlama       | Dashboards | TVL, DEX, bridges, gratuito | Gratis |
| Nansen          | Wallet intel | 100M+ labels, Smart Money | $150-$1000/mes |
| Arkham          | Entity intel | Wallet tracking, entity unmasking | Free a custom |
| Glassnode       | On-chain metrics | 300+ metrics, institutional | $29-$799/mes |
| CryptoQuant     | Exchange flows | Actionable dashboards | Free a pago |
| Token Terminal  | Protocol fundamentals | Revenue, fees, usage | Free a pago |

### Dune Analytics em 2026

Dune e o padrao para SQL queries em dados on-chain. Features:
- 20+ chains suportadas com dados decoded
- Free tier: queries ilimitadas, dashboards publicos
- Community dashboards: milhares de dashboards publicos para qualquer protocolo
- SQL queries contra tabelas pre-decoded de eventos de smart contracts
- Visualizacao: line charts, bar charts, counters
- Forking: qualquer dashboard publico pode ser forkado e modificado

### Flipside Crypto em 2026

Flipside compete com Dune com diferencas:
- 30+ chains com unified schema (mesmo nome de tabela across chains)
- AI agents built-in: rodam queries em schedule, detectam anomalias, ping Slack
- Snowflake integration: data warehouse dedicado
- Free tier generoso (queries e dashboards ilimitados)
- Builder+ ($200/mes) para private queries
- Voyager tier ($1200/mes) para enterprise

Vantagem vs Dune: decoded data out-of-the-box em unified schema across 30+ chains,
AI agents. Desvantagem: comunidade menor que Dune.

### The Graph em 2026

The Graph e infraestrutura descentralizada de indexacao:
- Subgraphs: definem como indexar eventos de um contrato especifico
- Queries via GraphQL
- Usado por dApps para data realtime (precisa de subgraph deployado)
- Descentralizado: indexers stake tokens para servir queries
- Pay per query (GRT token)

Caso de uso: se o bot precisa de data realtime de um protocolo especifico e ja tem
subgraph deployado, The Graph e a opcao. Para analise ad-hoc, Dune ou Flipside sao
melhores.

### DefiLlama em 2026

DefiLlama e gratuito e referencia para:
- TVL por protocolo, chain, sector
- DEX volumes e market share
- Bridge volumes e net flows
- Stablecoin supply e flows
- Yields (pool-level)
- Fees e revenue de protocolos

API: api.llama.fi (restful, gratuito, sem auth). Endpoints como:
- `/protocols`: lista de protocolos com TVL
- `/protocol/{name}`: detalhe de um protocolo
- `/charts`: TVL historico por chain

### Nansen Smart Money em 2026

Nansen labelou 100M+ addresses identificando exchanges, funds, MEV bots, smart money.
Smart Money dashboard trackeia o que top traders estao acumulando. Dado Q4 2025:
wallets labeled Smart Money outperformaram broader altcoin market em 147% sobre 12
meses, com holding period medio de 6.2 semanas. Token God Mode da analytics
comprehensive por token. NFT Paradise trackeia NFT wallet trends.

### AI agents e on-chain data

Tendencia 2026: AI agents que rodam queries em schedule e entregam findings. Flipside
tem built-in. Sentinel (forgequant/sentinel no GitHub) agrega F&G, news, prediction
markets, e social intelligence em signal stream que LLMs podem reason over.

AI-agent wallets accountaram por 8-12% do volume DeFi em Q1 2026 (spotedcrypto). Isso
cria uma nova categoria de on-chain actor que nao e humano nem MEV bot tradicional.

## Ferramentas e APIs disponiveis

### Dune Analytics API

- SQL queries contra dados decoded de 20+ chains
- Endpoint: `https://api.dune.com/api/v1/query/{query_id}/execute`
- Auth: API key (Dune API key, free tier com rate limit)
- Resultados em CSV, JSON
- Free tier: queries publicas ilimitadas, private com plano pago

### Flipside Crypto API

- SDKs em R, Python, JavaScript
- Queries SQL contra tabelas pre-aggregated (ez_pools_metrics_daily, ez_dex_metrics_
  daily, ez_bridge_metrics_daily, ez_stablecoin_flows_daily)
- Snowflake data warehouse access (enterprise)
- Free tier: queries e dashboards ilimitados
- URL: flipsidecrypto.xyz

### DefiLlama API

- Restful, gratuito, sem autenticacao
- Base: `https://api.llama.fi/`
- Exemplos: `/protocols`, `/protocol/{name}`, `/charts`, `/stablecoins`, `/overview/
  dexs`
- Dados: TVL, DEX volumes, bridge flows, stablecoin supply, yields

### The Graph

- GraphQL queries contra subgraphs
- Gateway: `https://api.thegraph.com/subgraphs/id/{subgraph_id}`
- Pay per query em GRT token
- Para data realtime de protocolos com subgraph deployado

### Nansen API

- REST API para Smart Money flows, wallet analytics, token God Mode
- Auth: API key
- Pricing: $150/mes (VIP) a $1000/mes (Alpha)
- URL: nansen.ai

### Glassnode API (complementar)

- 300+ metricas on-chain
- Base: `api.glassnode.com/v1/metrics/`
- Auth: API key
- Free: 20 metricas, 24h delay. Professional: $799/mes, live, API

## Por que importa para o crypto-correl-bot

O bot opera em Binance com dados de preco, OI, funding, liquidations, F&G. On-chain
data e o complemento que falta: mostra o que acontece com o ativo real, nao so com
o trading. Aplicacoes concretas:

1. TVL como filtro de adocao: para altcoins de DeFi (UNI, AAVE, COMP, etc), TVL
   subindo indica adocao real e e bullish para o token. TVL caindo indica loss of
   confidence. O bot pode integrar TVL da DefiLlama API como feature para filtrar
   quais altcoins tem fundamental suportando o preco vs pura especulacao.

2. Exchange flows via CryptoQuant/Glassnode: net outflow persistente de BTC de
   exchanges e bullish (acumulacao). Net inflow e bearish (intencao de venda).
   Combinar com OI e funding: outflow + OI subindo + funding positivo = acumulacao
   alavancada, rally saudavel. Inflow + OI caindo + funding negativo = distribuicao,
   alerta.

3. DEX volumes como corroboracao: se volume em DEX para um token sobe enquanto
   preco sobe, e demanda real. Se preco sobe mas DEX volume cai, e rally em CEX com
   pouca liquidez real, mais manipulavel. O bot pode usar DEX volume como filtro de
   qualidade de move.

4. Lending rates como signal de alavancagem: borrow rate subindo em Aave/Compound
   para um asset indica demanda por short via borrowing+selling. Utilization > 80%
   e zona de stress que pode levar a liquidacoes em cascada. O bot pode monitorar
   isso via Dune queries ou subgraphs.

5. Smart Money tracking via Nansen: se Smart Money esta acumulando um token que o
   bot esta considerando para long, e corroboracao. Se Smart Money esta distribuindo
   enquanto o bot quer comprar, e alerta. 147% de outperformance em 12 meses e
   signal forte.

6. Bridge flows como signal de rotacao cross-chain: se capital esta flowing de
   Ethereum para Solana via bridge, e bullish para SOL ecosystem. O bot pode
   trackear net bridge flows por chain como signal macro de rotacao.

7. Oracle usage como signal de atividade DeFi: se um protocolo usa mais oracle
   updates, ha mais atividade de lending/trading acontecendo. Util para gauge health
   de DeFi em tempo real.

8. Implementacao pratica: para o bot, DefiLlama API (gratuito, sem auth) e o point
   de entrada mais facil. Integrar TVL e DEX volumes como features daily. Dune para
   queries customizadas especificas. Nansen Smart Money em tier pago se o edge
   justificar o custo.

9. Caveat data freshness: on-chain data tem delay natural (block time + indexacao
   + decode). Para BTC, block time e ~10 min. Para Ethereum, ~12s. Dune e Flipside
   tem delay adicional de indexacao. On-chain nao serve para signal intraday de
   segundos/minutos, mas sim para daily regime e trend.

10. Para cripto nativo, on-chain vale mais que TA classico porque captura
    fundamentals que o grafico nao mostra. O bot deve ter on-chain data como
    camada de confirmacao e filtro macro, nao como signal de timing preciso. O
    timing vem de Binance realtime (preco, OI, funding); o conviction vem de
    on-chain (TVL, flows, smart money).

## Referencias

1. CoinLaw, "DeFi Market Statistics 2026: TVL, Chains & DEXs" (junho 2026)
   https://coinlaw.io/decentralized-finance-market-statistics/
2. Flipside Crypto, "Protocol & DeFi Analytics"
   https://flipsidecrypto.xyz/solutions/protocol-defi/
3. XYZEO, "Flipside Crypto Review 2026"
   https://xyzeo.com/product/flipside-crypto
4. Startupik, "Best On-Chain Analysis Tools for Crypto"
   https://startupik.com/best-on-chain-analysis-tools-for-crypto/
5. ChainScore Labs, "How to Build a Cross-Chain Analytics Dashboard with Dune &
   Flipside"
   https://chainscorelabs.com/guides/interoperability-and-cross-chain-technologies/interoperability-standards/setting-up-a-cross-chain-analytics-dashboard-with-dune-and-flipside
6. Coin Bureau (maio 2026), "Best Crypto Analysis Tools in 2026"
   https://coinbureau.com/review/crypto-research-tools
7. DEXTools, "Best On-Chain Analytics Tools 2026"
   https://www.dextools.io/tutorials/top-5-on-chain-analytics-tools-2026
8. LedgerMind, "Best On-Chain Analytics Tools 2026: 12 Platforms Tested"
   https://theledgermind.com/best-on-chain-analytics-tools/
9. CoinGabbar, "Best Blockchain Analytics Tools 2026"
   https://www.coingabbar.com/en/crypto-blogs-details/best-blockchain-analytics-tools-2026
10. SpotedCrypto, "Altcoin Sector Rotation 2026" (DePIN revenue, AI agent volume)
    https://www.spotedcrypto.com/altcoin-sector-rotation-2026-depin-ai-rwa-gaming/
11. Gate Blog, "2026 Analysis of Three Major Crypto Sectors"
    https://www.gate.com/blog/2026-crypto-three-major-sectors-rwa-perp-dex-ai-infrastructure-capital-narrative-competition
12. DefiLlama, "DeFi TVL and Protocol Metrics"
    https://defillama.com
