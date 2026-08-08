# Topico: Order Book (L1/L2), Depth, Spread, Microprice e Imbalance

**Data:** 2026-07-15
**Categoria:** Microestrutura

## TL;DR

O order book e a estrutura de ordens pendentes (bids e asks) que define preco, liquidez e pressao direcional em tempo real. L1 mostra o melhor bid/ask (top of book), L2 mostra multiplas profundidades. Metricas derivadas como spread bid-ask, microprice, midpoint e order book imbalance (OBI) revelam para onde o preco tende a ir nos proximos milissegundos. Em cripto, onde a maioria das venues opera fora de jurisdicao regulada, o book tambem e vetor de spoofing, o que torna a distincao entre interesse real e fake walls uma skill critica.

## Explicacao para criancas

Imagine a feira de frutas. Tem uma banca com duas filas: de um lado, pessoas querendo comprar mangas (bids, oferecendo preco); do outro, vendedores com caixas de manga (asks, pedindo preco). O vendedor mais barato pede R$ 3,00. O comprador mais generoso oferece R$ 2,90. A diferenca de R$ 0,10 e o spread. Quando alguem nao quer esperar e grita "compro por R$ 3,00 agora", essa pessoa e o agressor (taker): ela cruza o spread e define o preco da ultima manga vendida. Se de repente aparecem 50 compradores na fila e so 2 vendedores, a banana vai subir: isso e imbalance.

## Como funciona tecnicamente

### Niveis de dados de mercado

- **L1 (Level 1 / BBO):** melhor bid (preco + quantidade) e melhor ask (preco + quantidade). Top of book. Atualizado em tempo real.
- **L2 (Level 2):** top N niveis do book (tipicamente 5, 10, 20). Cada nivel traz preco e quantidade. Permite calcular depth, imbalance multi-nivel e microprice.
- **L3 (Level 3):** ordens individuais com ID. Raro em cripto (Binance nao publica L3 publicamente), comum em equities US.

### Definicoes base

```
best_bid (Pb) = maior preco de compra pendente
best_ask (Pa) = menor preco de venda pendente
spread       = Pa - Pb
midpoint     = (Pa + Pb) / 2
spread_bps   = (spread / midpoint) * 10000
```

### Microprice

O microprice e uma estimativa de "preco justo" ponderada pelas quantidades no BBO. Pesa mais o lado com mais liquidez. E martingale por construcao e prediz o proximo tick melhor que o midpoint puro.

```
microprice = (Pb * Va + Pa * Vb) / (Vb + Va)

Pb = best_bid price
Pa = best_ask price
Vb = best_bid size (quantidade)
Va = best_ask size (quantidade)
```

Intuicao: se ha muito mais bid size que ask size (Vb >> Va), o microprice puxa para o ask, antecipando que o proximo movimento sera para cima (o lado buy esta mais grosso, sellers scarce). Implementacao Python equivalente ao exemplo da Databento:

```python
def calc_microprice(bid_px, bid_qty, ask_px, ask_qty):
    if (bid_qty + ask_qty) == 0:
        return (bid_px + ask_px) / 2
    return (bid_px * ask_qty + ask_px * bid_qty) / (bid_qty + ask_qty)
```

### Order Book Imbalance (OBI)

Mede a diferenca relativa de liquidez entre bids e asks. Range: -1 (so asks) a +1 (so bids).

```
OBI_N = (sum(bid_qty_1..N) - sum(ask_qty_1..N)) / (sum(bid_qty_1..N) + sum(ask_qty_1..N))

OBI > 0: mais bids que asks (pressao compradora pendente)
OBI < 0: mais asks que bids (pressao vendedora pendente)
OBI ~ 0: equilibrado
```

OBI multi-nivel (N=5, 10, 20) e mais robusto que OBI de L1 sozinho. O horizonte de previsao do OBI e curto: 1 a 60 segundos. Acima disso o sinal decai para ruido.

### Weighted mid price e microprice estendido

O microprice de top-of-book e o caso mais simples. Extensoes ponderam por profundidade multi-nivel:

```
weighted_mid_N = mid + (OBI_N * spread / 2)

# Ou microprice estendido a N niveis (cryptostats):
S = Pa * Vb_total / (Va_total + Vb_total) + Pb * Va_total / (Va_total + Vb_total)

Vb_total = sum(bid_qty ate nivel N)
Va_total = sum(ask_qty ate nivel N)
```

A relacao entre microprice e midpoint e indicador de probabilidade do proximo tick. Microprice > midpoint sugere proximo tick para cima; microprice < midpoint sugere tick para baixo. Funciona melhor em venues com taker fees altos vs maker fees, pois cria incentivo para join do BBO em vez de cruzar o spread.

### Imbalance como feature de ML

Em research quant, OBI de multi-nivel vira um vetor de features:

```
features = [imbalance_l1, imbalance_l5, imbalance_l10, imbalance_l20,
            bid_depth_5, ask_depth_5, spread, spread_bps, microprice_dev]
microprice_dev = (microprice - midpoint) / midpoint
```

Essas features alimentam modelos de previsao de direcao de proximo tick e de short-term return. O desafio: OBI de L1 e ruidoso e manipulavel por spoofing de top-of-book, por isso o consenso e agregar ate pelo menos o nivel 5 ou 10.

### Depth e cumulative depth

```
bid_depth_N = sum(bid_qty_1..N)   # liquidez compradora ate nivel N
ask_depth_N = sum(ask_qty_1..N)   # liquidez vendedora ate nivel N
```

O "depth chart" plota cumulative depth: curva verde sobe descendo os bids, curva vermelha sobe subindo os asks. Padroes: curva ingreme = wall (liquidez concentrada); curva plana = zona rala (preco viaja rapido); desbalanceamento > 1.5x ou < 0.7x indica tilt direcional de curto prazo.

### Como a Binance publica o depth

A Binance Spot oferece dois streams principais de order book via WebSocket (`wss://stream.binance.com:9443`):

- **Partial Book Depth Stream:** `<symbol>@depth<levels>` ou `<symbol>@depth<levels>@100ms`. Levels validos: 5, 10, 20. Snapshot dos top N niveis. Para JSON, update speed 1000ms ou 100ms. Para SBE (Simple Binary Encoding), o stream `<symbol>@depth20` update speed foi alterado para 50ms em 2025-11-26.
- **Diff Depth Stream:** `<symbol>@depth` ou `<symbol>@depth@100ms`. Updates incrementais para manter um book local. Exige snapshot REST inicial (`/api/v3/depth?symbol=...&limit=5000`) e logica de sincronizacao com `lastUpdateId` / `U` / `u`.

O SBE (Simple Binary Encoding), disponivel desde 18 de marco de 2025, oferece payload menor e melhor latencia que o JSON equivalente para os mesmos streams. Em 2025-11-26 a Binance reduziu o update speed de depth/depth20 SBE de 50ms para 25ms.

### Gerenciamento de book local (diff depth)

Para manter um book local correto a partir do diff depth stream, o procedimento oficial da Binance e:

1. Abrir WebSocket para `<symbol>@depth` (ou `@depth@100ms`).
2. Buffer os eventos recebidos. Anotar o `U` (first update ID) do primeiro evento.
3. Obter snapshot REST: `GET /api/v3/depth?symbol=...&limit=5000`.
4. Se `lastUpdateId` do snapshot for estritamente menor que o `U` do passo 2, voltar ao passo 3 (snapshot obsoleto).
5. Descartar eventos bufferados onde `u` (final update ID) <= `lastUpdateId` do snapshot. O primeiro evento bufferado valido deve ter `U` <= `lastUpdateId + 1` E `u` >= `lastUpdateId + 1`.
6. Aplicar cada evento: atualizar niveis com bids/asks do evento. Remover niveis com quantidade zero.
7. Repetir passo 6 para cada novo evento, garantindo que `U` do evento atual == `u` do evento anterior + 1 (sequencia continua).

Essa logica garante consistencia entre o snapshot REST e os diffs do WebSocket. Perdas de eventos ou gaps de sequencia exigem re-snapshot. O `depth20@100ms` (partial book) evita essa complexidade porque entrega snapshot completo a cada update, mas com menos niveis e mais largura de banda.

### Comparacao: partial vs diff depth

| Aspecto | Partial (`@depth20`) | Diff (`@depth@100ms`) |
|---------|---------------------|----------------------|
| Niveis | 5, 10, 20 | Ilimitado (ate 5000 via snapshot) |
| Largura de banda | Alta (snapshots completos) | Baixa (apenas mudancas) |
| Complexidade | Baixa (usar direto) | Alta (gerenciar book local) |
| Latencia percebida | Limitada pelo update speed | Real-time por evento |
| Custo de processamento | Baixo | Medio (aplicar diffs) |

Para o crypto-correl-bot, `depth20@100ms` e o trade-off ideal: 20 niveis suficientes para OBI multi-nivel, complexidade baixa, largura de banda aceitavel.

### Estados do book: skews, spoofing vs real interest

Um book "skewed" para bids (muitos bids, poucos asks) sugere, em principio, pressao compradora. Mas em cripto, ~30 a 40% da liquidez visivel pode ser spoofing (ordens que serao canceladas antes de executar). Sinais para distinguir real interest de spoofing:

1. **Ordem proporcional ao depth vizinho:** ordem real se mistura ao contexto. Spoof tipicamente tem 3x a 10x o depth circundante, criando ancora visual obvia.
2. **Timing de cancelamento:** spoof cancela conforme o preco se aproxima, nao depois de testar. A taxa de cancel-antes-fill em suspeitos de spoof e dramaticamente maior que em ordens genuine.
3. **Repeticao:** um unico large order aparecendo e sumindo e ruido. Mesmo tamanho, mesmo cluster de preco, mesmo comportamento de cancel 3-4x na sessao e signal.
4. **Localizacao em niveis psicologicos:** spoofed orders cluster em round numbers e logo dentro de suporte/resistencia visivel. Precisam ser vistos para funcionar.
5. **Preenchimento incremental:** walls reais preenchem incrementalmente conforme o preco se aproxima e ficam no lugar mesmo quando o preco graca o nivel. Fake walls somem no primeiro volume serio.

### Quatro padroes de spoofing catalogados em 2026

Frameworks de 2026 (ChainGain, CryptoTradeSignals, Kalena) formalizam quatro assinaturas distintas de manipulacao de book:

1. **Layered wall:** large sell order (US$ 5M a US$ 50M) aparece em resistencia chave. Algoritmos e traders ativos veem a "wall" e front-run vendendo. Preco cai. Spoofer cancela a wall antes de qualquer porcao executar. Os buy orders reais do spoofer preenchem no preco mais baixo. Assinatura: long upper wick rejeitando exatamente no nivel da wall, seguida de reversao rapida. Wall visivel 1 a 15 min, depois some.

2. **Flash-cancel:** versao mais sofisticada. Ordem spoof aparece por milissegundos, visivel so para algoritmos de alta frequencia. Move o preco disparando respostas algoritmicas, depois cancela antes que participantes lentos reajam. Comum em horas de baixa liquidez (02:00 a 06:00 UTC) quando o depth do book e ralo.

3. **Multi-level layering:** varias spoof orders empilhadas em precos incrementais diferentes, criando aparencia de depth organico. Mais dificil de detectar: 20 a 100+ ordens menores em vez de uma grande, espalhadas em 0.5% a 2% do range de preco. Cancelamento sequencial ou cascata, nao tudo de uma vez.

4. **Iceberg spoofing:** spoof ordens aparecem e somem ciclicamente no mesmo nivel de preco, testando se outros traders reagem. Cada aparecimento dura segundos. O padrao de repeticao (mesmo tamanho, mesmo preco, mesmo comportamento de cancel) e o tell que mais traders perdem.

O Candle following e o testemunho: uma long upper wick rejeitando exatamente no nivel da wall, seguida de reversao rapida, e a assinatura classica de spoof de venda. A deteccao sem ver o book diretamente e possivel: a estrutura da candle conta a historia.

## Estado do mercado em 2026

A latencia de feeds de book continua caindo. A Binance reduziu o update speed de streams SBE depth/depth20 para 25ms em novembro de 2025, dobrando o volume de dados por segundo. Isso aproxima o retail e institucional de granularidade que antes era exclusiva de venues tradicionais via co-location. O SBE (Simple Binary Encoding), disponivel desde marco de 2025, entrega payload binario menor e melhor latencia que o JSON para os mesmos streams, tornando-se padrao para data feeds de baixa latencia.

Spoofing continua endemico em cripto. Segundo dados da Chainalysis citados em reportagens de 2026, manipulacao por spoofing custou ~US$ 2.3 bilhoes a traders de cripto em 2026. Apesar disso, enforcement ainda e inconsistente: spoofing e ilegal em futuros regulados US (Dodd-Frank 2010, SEC/CFTC), mas a maioria das venues de cripto spot opera fora de jurisdicao. Guias praticos de 2026 (ChainGain, Kalena, CryptoTradeSignals) formalizam frameworks de deteccao com 4 a 7 padroes de spoofing distintos, incluindo layered wall, flash-cancel, e multi-level layering.

Um caso documentado pela LedgerMind: em maio de 2024, uma unica whale de Bitcoin colocou US$ 47 milhoes em buy orders em tres exchanges, cancelou 98.6% em 90 segundos, o preco subiu 4.2%, retail comprou o topo, e a whale vendeu US$ 23 milhoes no pico. Esse padrao, repetido diariamente em cripto, e a motivacao para frameworks de deteccao automatizada.

O mercado institucional consolidou: a Kaiko adquiriu a Amberdata em 2026, criando a unica empresa regulada e independente de dados/analytics/indices para ativos digitais. Isso sinaliza que dados L2/L3 profissionalizados viraram commodity para desks institucionais. CoinAPI, Tardis.dev e Databento competem no espaco de dados L2/L3 normalizados, com focus em replay historico e normalizacao cross-exchange.

### Spread tiers em 2026

O guia ChainGain de 2026 formaliza um framework de 4 tiers de spread para avaliar liquidez do book:

- **Tier 1 (tight, < 0.05%):** alta liquidez, BTC/ETH em venues top. Sinais de order flow confiaveis, agressao reflete conviccao real.
- **Tier 2 (normal, 0.05% a 0.15%):** liquidez adequada, major alts. Sinais utilizaveis com contexto.
- **Tier 3 (wide, 0.15% a 0.3%):** liquidez limitada, mid-cap alts. Agressao cara, sinais menos confiaveis.
- **Tier 4 (illiquid, > 0.3%):** baixa liquidez, small caps. Sinais de order flow ruidosos, spoofing mais prevalente, slippage alto.

Esse tiering serve como filtro de confianca: sinais de CVD e OBI em Tier 4 deveriam ser descontados ou ignorados.

## Ferramentas e APIs disponiveis

- **Binance Spot WebSocket**, tipo: L2 depth streaming, custo: gratis, URL: `wss://stream.binance.com:9443`, doc: https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md. Streams `depth5/10/20` e `depth@100ms`. SBE desde 2025. Partial book (snapshots top N) ou diff depth (incremental, ate 5000 niveis).
- **Binance REST depth**, tipo: snapshot L2, custo: gratis, URL: `https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5000`, ate 5000 niveis. Usado para inicializar book local no diff depth stream.
- **Coinglass API V4**, tipo: snapshots L2/L3 + order flow, custo: freemium / pago, URL: https://www.coinglass.com/CryptoApi. Inclui order book snapshots multi-nivel, large order monitoring, CVD aggregated. Spot L2/L3 depth snapshots e historico.
- **Kaiko**, tipo: L1/L2 tick + aggregations, custo: pago (L1 aggregations from US$ 1.000/mes, L2 tick from US$ 2.500/mes), URL: https://www.kaiko.com/products/l1-l2-data. Cobertura 100+ exchanges, entrega via REST, WebSocket, Snowflake, BigQuery. Historico desde 2010.
- **Amberdata**, tipo: market data L1/L2 + DeFi + on-chain, custo: pago (institucional), URL: https://www.amberdata.io. Adquirida pela Kaiko em 2026. 1000+ exchanges, 500k+ pares, CloudSync para data warehouses.
- **Databento**, tipo: L2 MBP-10 (Pandas-ready), custo: pago (pay-as-you-go), URL: https://databento.com/docs/examples/order-book/microprice. Exemplos prontos de microprice e book imbalance em Python. Schema MBP-10 com top 10 niveis.
- **CoinAPI**, tipo: L2/L3 + derivativos, custo: pago, URL: https://www.coinapi.io. Normalizacao unificada across exchanges. Raw tick data, full L2/L3 order books, trades, quotes, derivativos.
- **Tardis.dev**, tipo: archive de ticks raw, custo: pago, URL: https://tardis.dev. Replay historical order book state, L2/L3 deltas. Dados raw exchange-native, sem normalizacao.
- **nanoARB (open source)**, tipo: extracao de features de LOB em Rust, custo: gratis, repo: https://mintlify.wiki/dhir1007/nanoARB. Calcula microprice, weighted_mid, imbalance_l1/total, bid/ask depth e cumulative, spread. Performance nativa para HFT.
- **cryptostats.dev**, tipo: streaming de microprice e imbalance, custo: nao confirmado, URL: https://docs.cryptostats.dev/streaming/orderbook-dynamics. Canal normalizado de mismatch bid/ask, microprice estendido a niveis 1-25.

## Por que importa para o crypto-correl-bot

O coletor (`src/data/live_collector.py`) ja assina `depth20@100ms` e armazena top 20 niveis em Parquet. Porem, `scripts/analyze_live.py` (`calc_order_book_metrics`, linhas 204-229) so usa os primeiros 5 niveis para spread, mid, spread_bps, bid_depth, ask_depth e imbalance. Lacunas concretas:

1. **Microprice nao e calculado.** O bot tem bid_px[0], bid_qty[0], ask_px[0], ask_qty[0] disponiveis. Adicionar `microprice = (bid_px*ask_qty + ask_px*bid_qty)/(bid_qty+ask_qty)` e trivial e melhoraria a estimativa de "fair value" usada em sinais e no VWAP. A funcao ja esta pronta para colar no `calc_order_book_metrics`.
2. **OBI multi-nivel subutilizado.** O coletor grava 20 niveis mas a analise aggrega so 5. OBI de N=10 e N=20 tende a ser mais estavel e menos manipulavel por spoofing de top-of-book. Implementar `calc_obi_multilevel(ob, n_levels=[1,5,10,20])` retornando um dict de imbalances por profundidade.
3. **Deteccao de spoofing ausente.** Nao ha tracking de aparecimento/cancelamento de walls grandes nem do "cancel-before-fill rate". Um modulo simples que registra ordens > 3x do depth vizinho e flaga cancelamentos em < 2s adicionaria um sinal anti-manipulacao valioso. Pseudocodigo:
   ```
   for each depth snapshot diff:
       detect new levels with qty > 3 * median(surrounding depth)
       track timestamp of appearance
       on disappearance: if (now - appeared) < 2s AND not filled: flag as spoof_candidate
       maintain rolling spoof_score = count(spoof_candidates last N min) / count(all large orders)
   ```
4. **Depth dynamics nao persistidas.** Gravar a serie temporal de microprice e OBI em Parquet permitiria backtestar horizonte de previsao por timeframe. Hoje so o snapshot instantaneo e mostrado no dashboard.
5. **Spread regime.** spread_bps ja e calculado. Monitorar regimes de spread (tight vs wide) como filtro de confianca para sinais de order flow aumentaria robustez: sinais de CVD em spread wide sao menos confiaveis porque custos de cross sao altos e agressao reflete menos conviccao.
6. **Weighted mid price.** O bot usa midpoint puro. Trocar para `weighted_mid = mid + OBI_5 * spread/2` reduz o lag do midpoint como referencia de fair value.
7. **Microprice deviation como feature.** `microprice_dev = (microprice - midpoint) / midpoint` normalizado e um preditor de direcao de proximo tick. Deveria entrar como feature em qualquer modelo ML do bot.

Recomendacao: criar `src/analysis/orderbook.py` com funcoes puras `calc_microprice`, `calc_obi_multilevel(n)`, `calc_weighted_mid(n)`, `detect_spoof_walls(window)` e integrar no `analyze_live.py`. O modulo deve ser testavel com dados sinteticos (seed fixo, conforme AGENTS.md) e cobrir edge cases: book vazio, nivel com qty zero, spread invertido (erro de feed).

## Referencias

- https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md (Binance WebSocket: depth streams, partial book, diff depth, gerenciamento de book local)
- https://github.com/binance/binance-spot-api-docs/blob/master/sbe-market-data-streams.md (Binance SBE: depth20 update speed 25ms/50ms)
- https://github.com/binance/binance-spot-api-docs/blob/master/CHANGELOG.md (mudancas de update speed em 2025-11-26)
- https://databento.com/docs/examples/order-book/microprice (formula de microprice e book imbalance em Python)
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694 (Sascha Stoikov, "The Micro-Price: A High Frequency Estimator of Future Prices")
- https://chaingain.io/crypto-order-book-market-depth-guide-2026/ (guia pratico 2026: spread tiers, walls, spoofing)
- https://blog.kalena.ai/crypto-spoofing-detection-the-analytical-framework-that-actually-works-in-real-time-dom-trading (framework de deteccao de spoofing em tempo real)
- https://www.kaiko.com/products/l1-l2-data (Kaiko L1/L2 data tiers e precos)
