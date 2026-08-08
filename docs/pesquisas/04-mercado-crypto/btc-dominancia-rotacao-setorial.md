# Topico: Bitcoin Dominance, Rotacao de Capital e Setores Cripto

**Data:** 2026-07-15
**Categoria:** Mercado Cripto

## TL;DR

Bitcoin Dominance (BTC.D) e a porcentagem do market cap total de cripto que pertence
ao Bitcoin. Em julho de 2026, BTC.D esta em ~58%, dentro de um zone de supply entre
58% e 64%. O ciclo classico de rotacao e: BTC sobe primeiro e puxa BTC.D junto, depois
BTC.D cai quando capital migra para ETH e altcoins (altseason). A altseason confirmada
requer 75%+ das top 50 altcoins superando BTC em janela de 90 dias, e o Altcoin Season
Index esta em ~39 em junho de 2026, longe do threshold. A era dos ETFs mudou a dinamica:
BTC.D nao cai abaixo de 50% desde setembro de 2023, a maior sustain acima desse nivel
desde 2017. Em 2026, o mercado e sector-driven em vez de broad-altseason. Os setores
que cruzaram o threshold de Breakout em 2026 sao RWA (Real-World Assets), DePIN
(Decentralized Physical Infrastructure) e AI crypto, todos com receita on-chain
verificavel. Memes e L1 genericos nao passaram no filtro. Para o bot, BTC.D funciona
como filtro macro: quando acima de 60%, priorizar estrategias em BTC; quando cai abaixo
de 55% com confirmacao, aumentar exposicao em altcoins de setores com receita real.

## Explicacao para criancas

Imagina que o dinheiro do cripto e agua. O Bitcoin e um balde grande no topo de uma
cascata. Quando entra dinheiro novo no cripto, vai primeiro no balde do Bitcoin. O
balde enche, fica pesado, e a agua comeca a transbordar para os baldes menores embaixo:
Ethereum primeiro, depois as altcoins menores.

Bitcoin Dominance e simplesmente medir quanto da agua total esta no balde do Bitcoin
versus todos os outros baldes juntos. Se a dominancia sobe, o Bitcoin esta ficando com
mais agua. Se cai, a agua esta se espalhando para os outros baldes.

A rotacao acontece porque quando o Bitcoin para de subir tao rapido, os investidores
olham para os outros baldes e pensam: "aqui tem mais espaco para crescer". Ai eles
tiram agua do Bitcoin e colocam nas altcoins. Isso e a altseason.

Mas em 2026 isso nao acontece com todos os baldes ao mesmo tempo. So alguns baldes
que tem algo real dentro (como RWA que tem titulos do governo, ou AI que tem agentes
gerando receita) recebem agua. Os baldes vazios (memes, moedas sem uso) ficam de fora.

## Como funciona tecnicamente

### Definicao de Bitcoin Dominance

```
BTC.D = Market Cap BTC / Market Cap Total Cripto * 100

Onde Market Cap Total inclui BTC + todas as altcoins + stablecoins
```

Existem variantes:
- TOTAL: market cap de todas as criptos incluindo stablecoins
- TOTAL2: market cap excluindo BTC (so altcoins + stablecoins)
- TOTAL3: market cap excluindo BTC e ETH (so altcoins menores + stablecoins)

A escolha importa: uma queda de BTC.D pode nao significar que altcoins estao ganhando,
mas sim que stablecoin supply cresceu (diluicao). Antes de declarar altseason, verificar
se a queda e por forca real de altcoins ou por diluicao de stablecoins.

### O ciclo classico de rotacao

O padrao historico de fluxo de capital:

1. Fase BTC: capital novo entra via Bitcoin (institucional, ETFs, retail conservador).
   BTC sobe mais rapido que altcoins. BTC.D sobe.
2. Fase ETH: BTC estabiliza, capital migra para Ethereum. ETH/BTC sobe. BTC.D cai
   moderadamente.
3. Fase altcoins large-cap: capital migra de ETH para top altcoins (SOL, XRP, etc).
   BTC.D cai mais.
4. Fase altcoins small-cap: capital migra para micro-caps e memes. BTC.D cai
   acentuadamente. Este e o pico da altseason.

Cada fase historica teve caracteristicas proprias:
- 2017: ICO boom, BTC.D crashou de 85% para 37%
- 2021: DeFi summer + NFT boom, BTC.D hitou 38%
- 2024-2026: ETFs estruturais, BTC.D ficou acima de 50% por mais tempo que qualquer
  ciclo desde 2017

### Altcoin Season Index

Definicao operacional do BlockchainCenter: altseason confirmada quando 75%+ das top
50 altcoins (excluindo stablecoins e wrapped BTC) superam BTC em janela de 90 dias.
O Altcoin Season Index varia de 0 a 100. Em junho de 2026, estava em ~39 (Bitcoin
Season territory). Threshold de 75 para altseason confirmada.

### Setores cripto em 2026

A classificacao de setores evoluiu. Os principais em 2026:

| Setor | Descricao | Status 2026 |
|-------|-----------|-------------|
| L1    | Blockchains base (ETH, SOL, AVAX, etc) | Maduro, competicao intensa |
| L2    | Rollups sobre Ethereum (Arbitrum, OP, Base) | Escalando, fees baixos |
| DeFi  | Protocolos financeiros on-chain (Uniswap, Aave) | Maduro, TVL estavel |
| Memes | Tokens sem fundamental (DOGE, PEPE, etc) | Speculativo, sem receita |
| AI    | Tokens de infra de IA (TAO, Bittensor, agent layer) | S-tier, receita emergente |
| RWA   | Tokenizacao de ativos reais (Ondo, Chainlink) | S-tier, top performer 2025 |
| DePIN | Infra fisica descentralizada (Helium, Akash) | Breakout em 2026 |

O framework de rotacao setorial de 2026 usa 4 filtros:
1. Receita on-chain trailing 90d: so setores com slope positivo qualificam
2. TVL lead-time: TVL subindo em RWA precedeu appreciation de token em 4-6 semanas
3. Eventos regulatorios: approvals de OCC, dismissals de SEC reduzem risk premium
4. Concentracao de VC: 40% do VC crypto em 2026 tracking AI-convergence

### Filtro macro por BTC.D para estrategias em altcoins

Logica de decisao por regime:

- BTC.D > 60%: Bitcoin Season. Priorizar estrategias em BTC, reduzir exposicao em
  altcoins. Correlacao entre altcoins e alta (todas seguem BTC).
- BTC.D 55-60%: Transicao. Setores especificos podem outperformar, mas broad altseason
  nao confirmado. Foco em setores com receita real (RWA, AI, DePIN).
- BTC.D < 55% com Altcoin Season Index > 60: Pre-altseason. Aumentar exposicao em
  altcoins, especialmente small-caps com lag.
- BTC.D < 50% com Altcoin Season Index > 75: Altseason confirmado. Maxima exposicao
  em altcoins, mas com cuidado pois e onde o ciclo tipicamente termina.

## Estado do mercado em 2026

### BTC.D em julho de 2026

BTC.D esta em ~58%, em fase de consolidacao apos recuar de 65% em junho de 2025. O
nivel de 64.12% era suporte chave que foi quebrado, abrindo caminho para testar a
zone de supply 58-64%. ETH/BTC esta em zona de acumulacao historica apos correcao de
80%, com resistencia em 0.065-0.080. Um rompimento acima desse range seria bullish
para Ethereum e confirmaria rotacao.

Dados historicos de BTC.D:

| Ano    | BTC.D | Evento chave |
|--------|-------|--------------|
| 2013   | 90%   | BTC era o mercado cripto |
| 2017   | 42%   | ICO boom, BTC.D crash de 85% para 37% |
| 2018   | 55%   | Bear market consolidation |
| 2021   | 41%   | DeFi summer + NFT, BTC.D hit 38% |
| 2022   | 40%   | Post-Terra bear bottom |
| 2023   | 51%   | Recovery com ETF optimism |
| 2024   | 57%   | Spot ETFs launch, $35.2B inflows ano 1 |
| 2025   | 59%   | Institutional accumulation peak, BTC.D hit 65% em junho |
| Jul 2026 | ~58% | Consolidation apos pullback de 60%+ |

BTC.D nao caiu abaixo de 50% desde setembro de 2023. A era dos ETFs criou um piso
de demanda estrutural que nao existia em ciclos anteriores.

### Por que 2026 nao segue o playbook de 2021

Tres diferencas estruturais:

1. ETFs: fluxo institucional constante e direto em BTC via ETFs (IBIT, FBTC, etc).
   Isso cria um piso de demanda que mantem BTC.D elevado. Em 2021, nao havia ETFs
   nos EUA.

2. Stablecoin supply em historic highs: liquidez disponivel e enorme, mas concentrada.
   Milhares de novos assets competem pelo mesmo capital, tornando liquidez um recurso
   escasso para projetos pequenos.

3. Mercado sector-driven: o Altcoin Season Index em 39 significa que capital nao se
   espalha broad-based. Setores com receita on-chain real (RWA, AI, DePIN) absorvem
   capital enquanto memes e L1 genericos ficam de fora. Um print de 58% em 2026 tem
   significado estrutural completamente diferente de 58% em 2022.

### Setores breakout em 2026

RWA foi o top performer de 2025 com retorno medio de +185.76% (CoinGecko). Keeta
Network surgiu +1,794.9%, Zebec Network +217.3%. O mercado on-chain de RWA cresceu
de $5.5B no inicio de 2025 para $29.2B em abril de 2026 em blockchains publicas, $36B
incluindo permissioned chains (SVB 2026 Crypto Outlook).

DePIN gerou ~$150M em receita on-chain em janeiro de 2026 so, o numero que empurrou
o setor past o Breakout threshold.

AI crypto tem ~919 projetos com market cap combinado de ~$22.6B. A diferencia dos
ciclos anteriores de AI tokens, os protocolas lideres estao gerando fees on-chain
de economias de AI agents deployados, nao de roadmap promises. AI-agent wallets
accountaram por 8-12% do volume DeFi em Q1 2026.

Perp DEX processaram $492.7B em Q1 2026, com Hyperliquid dominando. O setor e
classificado como A-tier (maduro com product-market fit) versus S-tier de RWA e AI.

### O sinal de ETH/BTC

O par ETH/BTC e o indicador mais limpo de rotacao BTC -> ETH. Em 2026, ETH/BTC esta
em zona de acumulacao apos correcao de 80% do topo. Higher lows sugerem forca relativa
renovada. Para confirmar rotacao broader, ETH/BTC precisa romper acima de 0.065-0.080
(order block bearish). Ate entao, a rotacao e setorial, nao broad-market.

## Ferramentas e APIs disponiveis

### CoinGecko API

- Endpoint: `/coins/markets` com `vs_currency=usd` e `order=market_cap_desc`
- Retorna market cap de cada asset, permitindo calcular BTC.D manualmente
- Endpoint: `/global` retorna market cap total, BTC dominance, ETH dominance
- Free tier: 50 calls/min, sem autenticacao necessaria para endpoints publicos
- URL: api.coingecko.com

### CoinMarketCap API

- Endpoint: `/v1/global-metrics/quotes/latest` retorna BTC dominance diretamente
- Free tier: 333 calls/dia com key gratuita
- URL: pro-api.coinmarketcap.com

### TradingView

- Symbol `BTC.D` (Bitcoin Dominance Index) disponivel para charting
- Symbols `TOTAL`, `TOTAL2`, `TOTAL3` para market caps agregados
- `ETHBTC` para o par de rotacao

### Altcoin Season Index

- BlockchainCenter: blockchaincenter.net/altcoin-season-index
- Calcula automaticamente o % de top 50 altcoins superando BTC em 90 dias
- Atualizacao diaria, gratuito

### DeFiLlama

- Para TVL por setor e chain
- URL: defillama.com, API em api.llama.fi
- Permite trackear TVL de RWA, DePIN, AI setores para o filtro de lead-time

### Messari

- Para sector metrics e叙事 tracking
- Tem dashboards de AI crypto, RWA, DePIN com metricas de receita on-chain
- Free tier limitado, pago para API

## Por que importa para o crypto-correl-bot

O bot faz cross-sectional analysis com lead-lag e Granger entre ativos. A relevancia
de BTC.D e dupla:

1. Filtro macro de regime: o bot deve ajustar seu universo de ativos e parametros
   por regime de BTC.D. Com BTC.D > 60%, a correlacao entre altcoins e BTC e muito
   alta (todas seguem BTC), o que diminui a utilidade de cross-sectional analysis
   (pouca variancia idiossincritica). Com BTC.D caindo, altcoins comecam a decorrelar
   e o cross-sectional passa a ter mais signal.

2. Filtro setorial: em vez de tratar todas as altcoins como um bloco, o bot pode
   agrupar por setor (RWA, AI, DePIN, L1, DeFi, memes) e testar lead-lag intra-setor
   e inter-setor. Setores com receita on-chain real (RWA, AI, DePIN) tendem a ter
   dinamica propria menos correlacionada com BTC puro.

3. Timing de rotacao: o ciclo BTC -> ETH -> altcoins e empiricamente observavel.
   O bot pode usar BTC.D caindo + ETH/BTC subindo como trigger para shiftar peso de
   BTC para ETH no portfolio, e ETH/BTC rompendo resistencia como trigger para
   shiftar para altcoins.

4. Falso signal de altseason: o bot deve verificar se queda de BTC.D e por altcoins
   ganhando ou por stablecoin diluicao. Comparar TOTAL vs TOTAL2 vs TOTAL3. Se TOTAL2
   sobre mas TOTAL3 nao, a rotacao parou em ETH. Se TOTAL3 sobre, chegou em altcoins.

5. Integracao com fear-greed e OI: BTC.D subindo com fear-greed em extreme fear e OI
   caindo e um setup de deleveraging (capital migra para o ativo mais seguro). BTC.D
   caindo com fear-greed em extreme greed e altseason approaching, mas com risco de
   topo proximo.

6. Backtest consideration: correlacao entre altcoins muda drasticamente por regime
   de BTC.D. O bot deve sempre usar janela deslizante para correlacao (ja faz por
   design do projeto) e idealmente segmentar por regime de BTC.D para evitar misturar
   regimes com dinamica fundamentalmente diferente.

## Referencias

1. KuCoin, "Bitcoin Dominance vs Altseason: What Happens Once BTC Stabilizes at
   Around $60K?" (julho 2026)
   https://www.kucoin.com/blog/bitcoin-dominance-vs-altseason-what-happens-once-btc-stabilizes-at-around-60k
2. CoinCodex, "Bitcoin Dominance Is Climbing Again: What That Actually Means for
   Altcoin Holders"
   https://coincodex.com/article/87551/bitcoin-dominance-is-climbing-again-what-that-actually-means-for-altcoin-holders/
3. AMBCrypto, "Here's Why Crypto's Next Altseason May Not Follow the 2021 Rulebook"
   https://ambcrypto.com/heres-why-cryptos-next-altseason-may-not-follow-the-2021-playbook/
4. TapBit, "When Is Altcoin Season? 5 Indicators Traders Watch in 2026"
   https://www.tapbit.com/en/learn/article/when-is-altcoin-season-indicators-2026-20260603
5. SpotedCrypto, "Altcoin Sector Rotation 2026: DePIN, AI, RWA & Gaming Signals"
   https://www.spotedcrypto.com/altcoin-sector-rotation-2026-depin-ai-rwa-gaming/
6. SpotedCrypto, "Altcoin Sector Rotation 2026, Breakout Narrative Framework"
   https://www.spotedcrypto.com/altcoin-sector-rotation-2026-breakout-narratives/
7. DailyCoinBrief, "RWA, DePIN, AI Lead 2026 Crypto Sector Rotation"
   https://dailycoinbrief.com/why-rwa-depin-and-ai-are-2026s-real-breakouts/
8. Gate Blog, "2026 Analysis of Three Major Crypto Sectors: RWA, Perp DEX, AI
   Infrastructure"
   https://www.gate.com/blog/2026-crypto-three-major-sectors-rwa-perp-dex-ai-infrastructure-capital-narrative-competition
9. KuCoin, "BTC Dominance Drops Below 64.12% as Altseason Setup Gains Momentum"
   https://www.kucoin.com/news/flash/btc-dominance-drops-below-64-12-as-altseason-setup-gains-momentum
