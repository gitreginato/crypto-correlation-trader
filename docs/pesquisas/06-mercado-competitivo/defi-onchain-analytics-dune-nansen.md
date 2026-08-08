# Topico: DeFi e on-chain analytics em 2026 (Dune, The Graph, Flipside, Nansen, Arkham, Glassnode, Token Terminal, DefiLlama, Coinglass DeFi)

**Data:** 2026-07-15
**Categoria:** Mercado Competitivo

## TL;DR

O ecossistema de DeFi e on-chain analytics em 2026 e composto por seis
plataformas dominantes (Dune, Nansen, Artemis, Allium, Token Terminal,
DeFiLlama) mais players especializados (Flipside, Arkham, Glassnode, The
Graph). DeFiLlama domina em cobertura (2.400+ protocolos, 180+ chains) e e
gratuito, mas raso em profundidade de dados. Dune domina em flexibilidade
(SQL sobre 100+ chains) com pricing baseado em credits ($0 a $399/mes). Nansen
lidera em wallet intelligence (250M+ wallets etiquetadas). Arkham e o melhor
em attribution (deanonymizar wallets). Token Terminal posiciona DeFi como
fundamentals (P/E ratios, revenue multiples). O TVL total de DeFi em 2026 esta
em ~$90-100 bilhoes, com Ethereum mantendo ~$55-60B. O gap mais interessante
para o crypto-correl-bot: on-chain analytics e market data de derivados
continuam desconectados em plataformas separadas. Nenhuma plataforma correlaciona
eventos on-chain (large withdrawals de exchanges, smart money accumulando)
com dados de derivados (funding rate spikes, liquidacao cascades) em tempo
real. Essa integracao e um vetor de alpha generation nao explorado.

## Explicacao para criancas

Cada criptomoeda vive numa rede chamada blockchain. Tudo que acontece nessa
rede fica registrado para sempre, como um diario publico que ninguem pode
apagar. Mas o diario tem tantas paginas que ninguem consegue ler tudo. Entao
existem ferramentas que leem o diario por voce. DeFiLlama junta todos os
numeros e mostra "quanto dinheiro esta guardado em cada app de financas
descentralizada". Dune deixa voce escrever perguntas em uma linguagem chamada
SQL e o diario responde. Nansen etiqueta as carteiras: "esta carteira e de um
fundo esperto", "esta e da Binance". Arkham tenta descobrir quem sao as pessoas
por tras das carteiras. Token Terminal trata apps de cripto como empresas,
calculando lucro e preco/acao. Cada ferramenta ve uma parte diferente do
diario. Nenhuma junta tudo.

## Como funciona (o segmento de mercado)

O segmento de DeFi e on-chain analytics transforma dados brutos de blockchain
em inteligencia acionavel. A cadeia de valor tem tres estagios:

### 1. Extracao (node layer)

Dados brutos vivem em nodes de blockchain. Ethereum archive nodes excedem 13
TB. Indexadores processam centenas de terabytes. Extrair dados diretamente de
nodes e caro e tecnicamente complexo. Por isso, plataformas de analytics
constroem pipelines de extracao e normalizacao.

### 2. Indexacao e modelagem

- **The Graph:** indexacao descentralizada via subgraphs. Desenvolvedores
  escrevem mappings em TypeScript e schemas em YAML. GraphQL API para
  querying. Pioneiro do modelo subgraph (2020-2021). Limitacoes
  historicas: block-by-block processing lento, GraphQL dificulta aggregations.
  Evolucao: Firehose e Substreams para higher-throughput e backfill mais
  rapido. 60+ redes no Subgraph Studio. Subgraphs agora suportados em
  plataformas terceiras (Alchemy, Goldsky).

- **Dune Analytics:** SQL-based on-chain analytics. Nao requer nodes proprios.
  Dune indexa dados de 100+ chains e expoe em tables queryable via SQL.
  Curated tables: dex.trades (todos DEX trades cross-chain), nft.trades,
  erc20 transfers, prices, ENS names. Datashare para Snowflake, BigQuery, e
  Databricks. Engine de queries com pricing baseado em credits (consumo
  proporcional a recursos computacionais).

- **Flipside:** SQL on-chain com schema crosschain normalizado. Pre-aggregated
  tables (ez_protocol_tvl, ez_dex_swaps, ez_lending_) e granular event data.
  20+ chains. AI agents que monitoram metricas e alertam no Slack quando algo
  se move. Diferencial vs Dune: schema normalizado cross-chain (uma query
  compara TVL em todas as chains).

- **Allium:** managed data warehouse on-chain. Cobertura similar a Dune (~100
  chains). Foco em infraestrutura enterprise.

### 3. Servir (front end)

- **DeFiLlama:** TVL aggregator. O mais amplo em cobertura: 2.400+ protocolos,
  180+ chains. Free, sem ads, sem token, sem login, open source (GitHub).
  Mantido pela comunidade, criado por desenvolvedor anonimo 0xngmi. API free
  sem key necessaria. Dados: TVL, yields, DEX volumes, stablecoin flows,
  bridge activity, protocol revenues, funding rounds, hacks, token unlocks.
  Limitacao: modelo de dados raso. Larga cobertura, shallow depth. DeFiLlama
  Pro adiciona custom dashboards, LlamaAI, Excel/Sheets integrations.

- **Nansen:** labeled dashboard com wallet intelligence. 250M+ wallets
  etiquetadas. Categoriza: smart money, funds, institutions, CEX, DeFi
  protocols. API com address labels (free e premium labels separados).
  Cobertura: 25+ chains (Ethereum, Solana, Arbitrum, Base, Hyperliquid,
  Monad, Sonic, Tron, etc.).

- **Arkham:** intelligence platform com foco em attribution. AI para conectar
  wallets a entidades reais. Tagging system: entities, labels, tags. Mais
  granular do mercado: identifica hackers, scammers, memecoin traders,
  prediction market participants, whales. Intel Marketplace com bounties
  em ARKM tokens para contribuicoes da comunidade. Diferencial vs Nansen:
  depth em attribution (quem e) vs Nansen que e melhor em behavior patterns
  (o que faz).

- **Token Terminal:** fundamentals tool para DeFi. Trata protocolos como
  empresas. Metricas: revenue, fees, P/E ratios, fully diluted valuation,
  years to payback, active users (daily/weekly/monthly). Pricing
  reestruturado em 2025: free plan agora inclui muito mais (full historical
  data, 3 custom dashboards, Sheets/Excel plugin, MCP access, CSV exports,
  500K API requests/mes). Pro: $350/mes ($297.50/mes anual), 1M API
  requests/mes. API: custom, 250K requests/dia.

- **Glassnode Studio:** macro on-chain intelligence. Indicadores
  proprietarios (LTH supply, SOPR, realized cap, exchange reserves). Para
  investidores e researchers que querem entender cycle position. Detalhes
  em documento anterior (plataformas-quant).

- **Coinglass DeFi:** extensao da plataforma Coinglass para dados on-chain,
  incluindo on-chain reserves e ETF net flows. Menos profundo que Glassnode
  mas integrado com dados de derivados.

### Estado do TVL em 2026

Total DeFi TVL: ~$90-100 bilhoes.
- Ethereum: ~$55-60B (maioria)
- Solana: ~$7-9B
- BNB Chain, Arbitrum, Base, Optimism, Polygon: variando
- DeFiLlama rastreia 2.400+ protocolos em 180+ chains

## Estado do mercado em 2026

### Players principais e pricing

| Plataforma | Cobertura | Free tier | Pago | Diferencial |
| --- | --- | --- | --- | --- |
| DeFiLlama | 2.400+ protocolos, 180+ chains | Completo (free, sem login) | Pro (custom) | Larga cobertura, open source, API free |
| Dune | 100+ chains (SQL) | 2.500 credits/mes | $75 a $399/mes | SQL flexivel, curated tables, Datashare |
| Nansen | 25+ chains (wallet labels) | Limitado | ~$150/mes+ | 250M+ wallets etiquetadas, smart money |
| Arkham | Multi-chain | Sim (com signup) | nao confirmado | Attribution via AI, Intel Marketplace ARKM |
| Token Terminal | Multi-chain (fundamentals) | Generoso (500K API req/mes) | $350/mes | DeFi como fundamentals, P/E ratios |
| Flipside | 20+ chains (SQL crosschain) | Sim (com signup) | N/A | Schema crosschain normalizado, AI alerts |
| Glassnode | BTC, ETH, principais L1s | Limitado | Enterprise (sales) | Macro on-chain, LTH metrics, metodologia |
| The Graph | 60+ chains (subgraphs) | Sim (GraphQL queries) | N/A | Indexacao descentralizada, subgraphs |
| Allium | ~100 chains (warehouse) | Trial | Enterprise | Managed warehouse, enterprise focus |
| Artemis | ~75 chains (metrics) | Sim | N/A | Chain-level economic data, metric directory |

### Tendencias

1. **Consolidacao de plataformas:** em 2026, seis plataformas dominam o
   middle layer entre nodes e workflows: Dune, Nansen, Artemis, Allium, Token
   Terminal, DeFiLlama. Cada uma com centro de gravidade diferente.

2. **Token Terminal reestruturou pricing em 2025:** free plan agora inclui
   muito mais (full historical data, 500K API requests/mes). Movimento para
   competir com DeFiLlama no free tier e capturar usuarios antes do upgrade.

3. **AI integrada em analytics:** Flipside oferece AI agents que monitoram
   metricas e alertam no Slack. Laevitas oferece AI-native MCP. Token Terminal
   tem MCP access. A integracao de IA com on-chain data e trend crescente.

4. **Subgraph migration:** ferramentas como Satsuma (adquirido pela Alchemy),
   Goldsky, Ponder, Subquery, Subsquid, StreamingFast surgiram para resolver
   limitacoes dos subgraphs do The Graph. The Graph respondeu com Firehose e
   Substreams.

5. **DeFiLlama como infraestrutura publica:** a API free do DeFiLlama alimenta
   terceiros como CoinGecko, Token Terminal, e dezenas de analytics platforms.
   O ecossistema inteiro se beneficia da cobertura aberta do DeFiLlama.

6. **Solana coverage expandida:** Dune adicionou comprehensive coverage de
   Solana DeFi e NFT ecosystems (dex_solana.trades). Flipside normaliza Solana
   no schema crosschain. A migracao de volume para Solana em 2024-2025 forçou
   plataformas a investir em coverage.

## Ferramentas e APIs disponiveis

| Nome | Fundacao | Pricing | Publico-alvo | Diferencial | URL |
| --- | --- | --- | --- | --- | --- |
| DeFiLlama | ~2020 | Free (Pro: custom) | Todos os niveis | 2.400+ protocolos, 180+ chains, open source, API free | https://defillama.com |
| Dune Analytics | ~2019 | $0 a $399/mes | Analistas, data teams | SQL sobre 100+ chains, curated tables, Datashare | https://dune.com |
| Nansen | ~2019 | ~$150/mes+ | Traders, fundos, BD | 250M+ wallets etiquetadas, smart money, 25+ chains | https://www.nansen.ai |
| Arkham | ~2021 | Free (com signup) | Investigators, compliance | AI attribution, Intel Marketplace ARKM, tagging granular | https://www.arkhamintelligence.com |
| Token Terminal | ~2020 | $0 a $350/mes | Investidores fundamentals | DeFi como empresas, P/E, revenue, FDV, payback | https://tokenterminal.com |
| Flipside | ~2017 | Free (com signup) | Protocolos, data teams | Schema crosschain, AI alerts, ez_ tables | https://flipsidecrypto.xyz |
| Glassnode | ~2017 | Free a Enterprise | Investidores, researchers | Macro on-chain, LTH supply, metodologia PIT | https://studio.glassnode.com |
| The Graph | ~2020 | Free (GraphQL) | Desenvolvedores dApps | Subgraphs descentralizados, 60+ chains, GraphQL | https://thegraph.com |
| Allium | ~2022 | Trial a Enterprise | Enterprises | Managed warehouse, ~100 chains | https://www.allium.so |
| Artemis | ~2022 | Free a pago | Analistas chain-level | ~75 chains, metric directory, economic data | https://www.artemis.xyz |

## Por que importa para o crypto-correl-bot

### Oportunidade

O crypto-correl-bot pode gerar alpha correlacionando eventos on-chain com
dados de derivados em tempo real. Nenhuma plataforma faz essa integracao
hoje. Exemplos de sinais que combinam on-chain + derivados:

1. **Exchange outflow + funding rate spike:** quando grandes quantidades de
   BTC saem de exchanges (on-chain, detectavel via Glassnode/Nansen) e o
   funding rate simultaneamente spike (detectavel via Coinglass), isso pode
   indicar squeeze. Nenhuma plataforma alerta sobre essa combinacao.

2. **Smart money accumulation + OI divergence:** quando Nansen detecta smart
   money accumulando um token e Coinglass mostra OI divergence (OI caindo
   enquanto preco sobe), isso pode indicar posicoes sendo fechadas enquanto
   spot e comprado. Sinal de mudanca de regime.

3. **Stablecoin supply expansion + funding negative:** quando supply de
   stablecoins cresce on-chain (DeFiLlama/DefiLlama) e funding rate fica
   negativo sustained, capital esta entrando sem alavancagem, potencialmente
   bullish.

4. **Whale movement + liquidation cascade risk:** quando Arkham/Nansen detecta
   whale movendo grandes posicoes para exchanges e Coinglass mostra altos OI,
   risco de liquidacao cascade aumenta.

### Gaps identificados

1. **On-chain e derivados desconectados:** Glassnode/Nansen veem on-chain.
   Coinglass/Laevitas veem derivados. Nenhuma plataforma cruza os dois em
   tempo real com alertas.

2. **SQL power sem custo acessivel:** Dune e poderoso mas credits-based
   pricing significa que queries complexas (joins cross-chain) custam
   caro. Flipside e mais acessivel mas tem menos cobertura de chains.

3. **Wallet labeling premium e caro:** Nansen smart money labels e premium
   labels (alpha trader) requerem tiers pagos. Arkham e mais acessivel mas
   com menos foco em trading signals.

4. **DeFiLlama raso mas essencial:** DeFiLlama e a unica fonte free para
   TVL, yields, e DEX volumes em escala. Mas nao tem granularidade de
   transacao individual. Complementar, nao substituir.

### Onde podemos competir ou aprender

- **Aprender com Dune curated tables:** o schema dex.trades e outras curated
  tables sao exemplos de como normalizar dados cross-chain. O bot pode
  implementar schemas similares para dados de derivados cross-exchange.
- **Aprender com Flipside ez_ tables:** o conceito de pre-aggregated tables
  (ez_protocol_tvl, ez_dex_swaps) e aplicavel a derivados: ez_funding_rate,
  ez_liquidations, ez_open_interest.
- **Consumir DeFiLlama API (free) para TVL e stablecoin flows:** integrar
  no bot como feature macro. Custo zero.
- **Consumir Nansen ou Arkham para wallet intelligence (se orcamento
  permitir):** usar smart money flows como signal complementar aos dados de
  derivados. Se orcamento nao permitir, focar apenas em derivados.
- **Criar correlacao on-chain + derivados:** este e o diferencial unico do
  bot. Nenhuma plataforma faz isso. Posicionar como "on-chain meets
  derivatives correlation engine".
- **Token Terminal para fundamentals screening:** usar dados de revenue e
  fees de protocolos para filtrar tokens fundamentalmente saudaveis antes
  de aplicar estrategia de derivados. Free tier com 500K API requests/mes
  e suficiente para screening diario.

## Referencias

1. Eco.com. Best Onchain Analytics Platforms 2026.
   https://eco.com/support/en/articles/14800357-best-onchain-analytics-platforms-2026
2. Plisio. DefiLlama: Free DeFi Analytics Dashboard and TVL Tracker.
   https://plisio.net/defi/defillama
3. Flipside. Protocol and DeFi Analytics (TVL, DEX, Lending Data).
   https://flipsidecrypto.xyz/solutions/protocol-defi/
4. Plisio. Token Terminal Review: Inside the Bloomberg of Crypto.
   https://plisio.net/defi/token-terminal
5. BlockCodex. Free vs Paid Crypto Analytics Tools: 7 Critical Differences.
   https://blockcodex.io/free-vs-paid-crypto-analytics-tools/
6. Dune Docs. How Credits Work (pricing).
   https://docs.dune.com/resources/credits-billing/how-credits-work
7. Dune Docs. Credit System (plans table).
   https://docs.dune.com/learning/how-tos/credit-system
8. Dune Docs. Curated Data Overview.
   https://docs.dune.com/data-catalog/curated/overview
9. Dune Blog. The State of EVM Indexing.
   https://dune.com/blog/the-state-of-evm-indexing
10. Startupik. Arkham Intelligence vs Nansen.
    https://startupik.com/arkham-intelligence-vs-nansen-which-wallet-tracking-tool-is-better/
11. Arkham Research. Industry-Leading Tagging System Explained.
    https://info.arkm.com/research/a-guide-to-arkham-intels-industry-leading-tagging-system
12. Arkham Research. How To Use Arkham Intel.
    https://info.arkm.com/research/how-to-use-arkham-intel-guide-explained
13. Chainscore Labs. Arkham vs Nansen: Intelligence Platforms.
    https://chainscorelabs.com/comparisons/security-audits-vs-formal-verification/runtime-monitoring-solutions/arkham-vs-nansen-intelligence-platforms
14. Nansen API Docs. Address Labels.
    https://docs.nansen.ai/api/profiler/address-labels
15. CryptoDataBytes. 2025 Annual Guide: Crypto Data Engineering.
    https://read.cryptodatabytes.com/p/2025-annual-guide-crypto-data-engineering
16. DCentralab. Web3 Data Indexing and Analytics 2025.
    https://www.dcentralab.com/blog/web3-data-indexing-and-analytics-in-2025
17. OrmiLabs. How to Access Crypto Data Using Subgraphs.
    https://blog.ormilabs.com/crypto-data-access-guide/
