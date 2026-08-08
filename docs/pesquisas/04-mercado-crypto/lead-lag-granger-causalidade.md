# Topico: Lead-Lag Effect, Granger Causalidade e Cross-Correlation em Cripto

**Data:** 2026-07-15
**Categoria:** Mercado Cripto

## TL;DR

Lead-lag effect e o fenomeno onde um ativo move primeiro e outro segue com atraso.
Em cripto, Bitcoin tipicamente lidera e altcoins seguem, especialmente small-caps com
menor liquidez. Granger causality test verifica se valores passados de uma serie
ajudam a prever outra alem do que ela sozinha ja previu. Cross-correlation function
(CCF) mede correlacao em diferentes lags, identificando onde o pico ocorre. Estudos
academicos de 2025-2026 confirmam: (1) BTC Granger-causa altcoins unidirecionalmente
em alta frequencia, com small-caps exibindo resposta mais lenta; (2) futuros lideram
spot em price discovery (~80% dos movimentos permanentes segundo FCVAR time-varying);
(3) Binance spot e perp na menos-regulada exchange sao a fonte primaria de price
discovery para BTC, com Coinbase ganhando influencia relativa no fixing 4pm NY; (4)
estrategias de lag trading usando BTC como leading indicator outperformam buy-and-hold
consistente across regimes quando combinadas com ML. O spot-perp delta (CryptoQuant)
indica se rally e spot-driven (saudavel) ou leverage-driven (fragil): delta negativo
persistente significa spot liderando. Para o bot, lead-lag e o core do cross-sectional
analysis: prever moves de altcoins via BTC e exploitable, mas instavel por regime e
timeframe, exigindo janela deslizante e segmentacao por liquidez.

## Explicacao para criancas

Imagine um grupo de carros numa estrada. O primeiro carro e o Bitcoin, que vai na
frente. Os outros carros sao as altcoins, que tentam seguir. O Bitcoin da a direcao:
quando ele vira, os outros carros viram depois, mas com um atraso.

O "lead-lag" e medir esse atraso. Se o Bitcoin sobe e uma altcoin sobe 5 minutos
depois, dizemos que o Bitcoin "lidera" e a altcoin "segue" com lag de 5 minutos.

"Granger causality" e um teste matematico que verifica se olhar o que o Bitcoin fez
ajuda a adivinhar o que a altcoin vai fazer. Se ajudar, dizemos que o Bitcoin
"Granger-causa" a altcoin. Nao e causalidade no sentido filosofico: e predictabilidade
estatistica.

O spot-perp delta e outra ideia: comparar o preco real do Bitcoin (spot) com o preco
do contrato de apostas (perp). Se o spot esta acima do perp, significa que gente real
esta comprando Bitcoin de verdade, nao so apostando. Isso e mais saudavel.

## Como funciona tecnicamente

### Lead-lag effect

Lead-lag e a estrutura temporal onde mudancas de preco de um ativo (leader) precedem
mudancas de outro (follower). Em cripto, a hierarquia empirica e:

1. BTC futuros (especialmente Binance perp) lidera
2. BTC spot segue com lag de segundos a minutos
3. ETH segue BTC com lag de minutos
4. Large-cap altcoins (SOL, XRP, etc) seguem com lag de minutos a dezenas de minutos
5. Small-cap altcoins seguem com lag de dezenas de minutos a horas

A magnitude do lag correlaciona inversamente com liquidez. Estudo de 2026 (Springer)
introduz um indicator de immediate price responsiveness e encontra que lower liquidity
tende a associar-se com slower reactions. Small-cap cryptocurrencies exibem
significant delayed responses a BTC price movements.

### Granger causality test

Formulado por Clive Granger (1969). O teste verifica se valores passados de serie X
ajudam a prever serie Y alem do que a propria historia de Y ja previu.

Modelo restrito (null hypothesis: X nao Granger-causa Y):
```
Y_t = a0 + sum(a_i * Y_{t-i}) + e_t
```

Modelo irrestrito (X Granger-causa Y):
```
Y_t = a0 + sum(a_i * Y_{t-i}) + sum(b_j * X_{t-j}) + e_t
```

Testa-se se os coeficientes b_j sao conjuntamente significativos (F-test ou chi-
square). Se sim, rejeita H0 e X Granger-causa Y.

Importante: Granger causality NAO e causalidade filosofica. E predictabilidade
estatistica temporal. Se X Granger-causa Y, significa que X tem informacao util para
prever Y que nao esta na propria historia de Y. Pode haver uma variavel Z nao-observada
causando ambos.

Em cripto, estudos encontram:
- BTC Granger-causa altcoins unidirecionalmente na maioria dos casos
- Causalidade e mais evidente na left tail da distribuicao (crashes), onde BTC atua
  como transmitter de informacao
- Em bullish markets, BTC as vezes atua como receiver de informacao (altcoins
  antecipam)
- Bi-directional causality existe entre BTC e todas as altcoins nos tails da
  distribuicao (eventos extremos)

### Cross-correlation function (CCF)

CCF mede correlacao entre duas series em diferentes lags:

```
CCF(k) = corr(X_t, Y_{t+k})
```

O pico da CCF indica o lag onde a correlacao e maxima. Se CCF pica em k > 0, X lidera
Y em k periodos. Se pica em k < 0, Y lidera X. Se pica em k = 0, sao simultaneos.

Em cripto, CCF entre BTC e altcoins tipicamente pica em k > 0 (BTC lidera), com
magnitude do pico decrescendo para small-caps (lag maior, correlacao menor no pico).

### Vector Autoregression (VAR)

VAR modela multiplas series temporais como sistema onde cada variavel e regredida
sobre seus proprios lags e lags das outras:

```
Y_t = A0 + A1 * Y_{t-1} + A2 * Y_{t-2} + ... + Ap * Y_{t-p} + e_t
```

Onde Y_t e um vetor de N series. VAR permite capturar a estrutura completa de
interdependencias e testar Granger causality multipla.

### Co-integration e lead-lag

Quando duas series sao co-integradas (tem equilibrio de longo prazo), usa-se VECM
(Vector Error Correction Model) ou FCVAR (Fractionally Cointegrated VAR):

```
dY_t = alpha * (beta' * Y_{t-1} - mu) + lagged differences + e_t
```

O termo de correcao de erro (beta' * Y_{t-1} - mu) captura o desvio do equilibrio.
O alpha indica quem ajusta: se alpha_BTC ~ 0 e alpha_alt != 0, BTC e weakly exogenous
e lidera, altcoin ajusta para restaurar equilibrio.

Estudo FCVAR time-varying (2025) em BTC encontra:
- Bitcoin futures dominam price discovery, drive 80% dos movimentos permanentes
- Adjust entre spot e futures e lento e persistente, mostrando long-memory effects
- Mercados tipicamente mantem parity, mas contango frequente em alta volatilidade
- Esto sugere only partial market efficiency

### Price discovery: spot vs futures

A pergunta "quem descobre o preco primeiro?" tem resposta empirica nuanced:

1. Futures geralmente lideram spot (futures market leads), mas com flutuacoes diarias
2. A contribuicao do futures para price discovery aumenta around macroeconomic
   surprises e Tether minting tweets
3. Binance spot e perp (menos regulados) sao a primary source de price discovery
4. Coinbase (mais regulado) ganha influencia relativa no New York 4pm fixing
5. CME futures tem OI proporcional maior que sobrevive selloffs, mantendo price
   discovery share

O spot-perp delta (CryptoQuant) operationaliza isso:
- Delta = Spot Price - Perp Price (ou Spot Index - Perp Mark)
- Delta negativo persistente: spot acima do perp, rally spot-driven (saudavel, menos
  alavancado)
- Delta positivo: perp acima do spot, rally leverage-driven (fragil, risco de
  correcao)
- Flip de negativo para positivo sinaliza influx de longs alavancados, frequentemente
  precursor de topo local

### Hasbrouck Information Share e Gonzalo-Granger

Para decompor quem contribui mais para price discovery entre venues co-integradas:

- Hasbrouck Information Share (IS): decompoem a variancia da componente permanente
  do preco em contribuicoes de cada market. Maior IS = maior contribuicao para
  price discovery.
- Gonzalo-Granger Permanent-Transitory (PT): identifica qual market carrega a
  componente permanente (informacao) vs transitoria (ruido).

Estudo de 2025 aplicando IS e PT em ETH entre Binance e Uniswap v2 encontra que
centralized markets tipicamente lideram price discovery. Em futures, high-volatility
periods produzem mixed outcomes.

## Estado do mercado em 2026

### Hierarquia de price discovery em 2026

Pesquisa consolidada de 2024-2026:

1. Binance perp (menos regulado, menor custo, maior volume) e primary source de price
   discovery para BTC
2. Binance spot segue, com lag de segundos
3. CME futures tem contribuicao significativa para price discovery em periods de
   stress e around macro events, mantendo OI proporcional maior
4. Coinbase ganha influencia relativa no 4pm NY fixing (importante para ETF NAVs)
5. Hyperliquid emergiu como venue de price discovery significativa em 2025, mas
   contraiu em stress (OI caiu 57% no crash de outubro)

### Estrategias de lag trading em 2026

Estudo de 2026 (Springer, Asia-Pacific Financial Markets) desenvolve e valida uma
lag trading strategy:
- Usa BTC preceding returns como leading indicator
- Foca em small-cap cryptocurrencies com prominent delay structure
- Machine learning-based trading decisions
- Consistentemente outperforma buy-and-hold across diverse market conditions
- Oferece valor para high-frequency e arbitrage traders

Estudo anterior (2017-2022, Revista 59:1) encontra:
- Melhor estrategia de BTC trading usa informacao de todas as cryptocurrencies
- Cumulative return de 331% vs 121% buy-and-hold
- Annualized Sharpe de 94.59% vs 64.74% buy-and-hold
- Resultados estatisticamente significativos
- Threshold de enter/exit de 0.25%, apos 0.5% round-trip transaction costs

### Caveats e limitacoes

1. Instabilidade por regime: lead-lag structure muda entre bull e bear. Em bull
   markets, BTC as vezes recebe informacao de altcoins (em vez de transmitir). Em
   bear/crash, BTC volta a liderar fortemente. O bot deve re-estimar lead-lag em
   janela deslizante e idealmente segmentar por regime.

2. Instabilidade por timeframe: lead-lag em 1m pode ser segundos, em 1h pode ser
   dezenas de minutos. O lag nao e invariante ao timeframe. Backtestar no timeframe
   de trading, nao em daily se opera intraday.

3. Causalidade em distribuicao: Granger causality in mean (padrao) so captura
   predictabilidade na media. Causalidade in distribution (quantiles) mostra que
   relacoes podem existir so nos tails (extremos). Estudos encontram causalidade
   bidirectional entre BTC e altcoins em high quantiles [0.6-0.95], com BTC e ETH
   tendo stronger causality para smaller coins.

4. Transaction costs: lag trading so e profitavel se o lag for grande o suficiente
   para cobrir fees + slippage. Em 2026, com fees de Binance futures em 0.02% maker
   / 0.05% taker, um lag que produz move de <0.1% pode nao ser exploitable apos
   costs.

5. Eficiencia crescente: conforme mais traders exploitam lead-lag, ele diminui. O
   edge pode ter decaido entre a publicacao dos estudos e 2026. Backtestar com
   dados recentes antes de deploy.

## Ferramentas e APIs disponiveis

### Binance API para lead-lag

- `GET /api/v3/klines` (spot) e `GET /fapi/v1/klines` (futures): candlesticks com
  timestamps alinhados. Comparar timestamps identicos entre spot e futures para
  calcular spot-perp delta e lead-lag.
- WebSocket streams: `wss://stream.binance.com:9443/ws/btcusdt@trade` para trade-by-
  trade data, permitindo analise de lead-lag em escala de segundos.
- `GET /api/v3/ticker/price` e `/fapi/v1/ticker/price`: preco atual spot e futures
  para delta em tempo real.

### Python: statsmodels

- `from statsmodels.tsa.stattools import grangercausalitytests`: testa Granger
  causality bidirectional com maxlag configuravel. Retorna F-test, chi-square,
  p-values por lag.
- `from statsmodels.tsa.vector_ar.var_model import VAR`: estima VAR e permite
  Granger causality test, impulse response, forecast error variance decomposition.
- `from statsmodels.tsa.stattools import ccf`: cross-correlation function.
- `from statsmodels.tsa.stattools import coint`: teste de co-integracao (Engle-
  Granger).

### Python: outros

- `arch` package: para GARCH e causalidade em quantiles
- `pycausal` ou `causal-ccm`: Convergent Cross Mapping (CCM) para causalidade nao-
  linear
- `pingouin` ou `scipy`: para testes estatisticos auxiliares

### CryptoQuant (spot-perp delta)

- CryptoQuant publica o spot-perpetual price delta como metrica
- Indica se rally e spot-driven (delta negativo, saudavel) ou leverage-driven
  (delta positivo, fragil)
- Disponivel via dashboard, API em tier pago

### Academic data sources

- Kaiko: tick-by-tick data de multiplas exchanges, usado em estudos academicos
- CryptoCompare: dados agregados com granularidade alta
- Binance Vision: dados historicos gratuitos em CSV (klines, trades, aggTrades)

## Por que importa para o crypto-correl-bot

Lead-lag e Granger causality sao o core do cross-sectional analysis do bot. O bot
ja faz lead-lag e Granger, e esta pesquisa confirma e refina a abordagem:

1. Hierarquia de leading: BTC e o leader empirico. O bot deve testar BTC como
   leading indicator para cada altcoin no universo, medir o lag otimo por CCF, e
   usar BTC returns passados como feature preditora. Aproveitar que small-caps tem
   lag maior (mais tempo para reagir, mas tambem menos liquidez para executar).

2. Spot-futures lead-lag: Binance perp lidera spot. O bot pode usar futuros de BTC
   como leading indicator para spot de altcoins. Medir o lag entre /fapi klines e
   /api klines de BTC, e entre BTC futures e altcoin spot.

3. Spot-perp delta como feature: integrar o spot-perp delta (CryptoQuant ou
   calcular internamente) como feature de regime. Delta negativo = spot-driven
   (mais seguro para trend follow). Delta positivo = leverage-driven (cuidado com
   reversao). Flip de negativo para positivo = alerta de topo local.

4. Segmentacao por regime: re-estimar Granger causality em janela deslizante (ex:
   30 dias). O bot ja faz janela deslizante por design (AGENTS.md regra 5). Alem
   disso, segmentar por regime de BTC.D e fear-greed: em BTC.D alto + fear, BTC
   lidera mais fortemente. Em BTC.D caindo + greed, altcoins podem antecipar BTC.

5. Causalidade nos tails: usar Granger in quantiles (pacote `arch`) para detectar
   causalidade so nos tails. Relacoes que existem so em crashes podem ser criticas
   para risk management, mesmo se nao sao exploitable para return.

6. Validacao de transaction costs: antes de deployar estrategia de lag trading,
   backtestar com fees reais (0.02% maker, 0.05% taker em Binance futures) e
   slippage estimado. So deployar se o lag produz move esperado > 2x costs.

7. Co-integration para pairs trading: se BTC e uma altcoin sao co-integradas, o bot
   pode fazer pairs trading (long um, short outro) explorando deviations do
   equilibrio. VECM modela a dinamica de correcao. Mais robusto que correlacao sola
   porque captura equilibrio de longo prazo.

8. Cuidado com overfitting: Granger causality com muitos lags e muitas series e
   sujeito a false positives (multiplos testes). O bot deve corrigir para multiplos
   testes (Bonferroni ou FDR) e validar out-of-sample. Se Sharpe IS > 3.0, suspeitar
   de overfit (regra do AGENTS.md).

## Referencias

1. Springer, "Price Transmission from Bitcoin to Altcoins: High-Frequency Evidence
   and Implications for Trading Strategy" (2026)
   https://doi.org/10.1007/s10690-026-09589-z
2. Revista 59:1, "Bitcoin and Main Altcoins: Causality and Trading Strategies"
   (2017-2022 data)
   https://doi.org/10.14195/2183-203x_59_1
3. IRFA, "Measuring Quantile Dependence and Testing Directional Predictability
   Between Bitcoin, Altcoins and Traditional Financial Assets"
   https://doi.org/10.1016/j.irfa.2020.101571
4. Finance Letters, "Causal Relationship Among Cryptocurrencies: A Conditional
   Quantile Approach"
   https://ideas.repec.org/a/eee/finlet/v42y2021ics1544612320316937.html
5. SSRN, "Where is the Price of Bitcoin Determined? Price Discovery in a Fragmented
   Market" (2024-2025)
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5070964
6. arXiv, "Price Discovery in Cryptocurrency Markets" (2025)
   https://doi.org/10.48550/arxiv.2506.08718
7. ResearchGate, "Price Discovery in Bitcoin Spot or Futures? The Jury Is Out"
   (janeiro 2025, Journal of Futures Markets 45(4))
   https://www.researchgate.net/publication/387887123_Price_Discovery_in_Bitcoin_Spot_or_Futures_The_Jury_Is_Out
8. SCIENCE@home, "When the Tail Wags the Dog: A Time-Varying FCVAR Analysis of
   Bitcoin Market"
   https://sah.borca.ai/papers/283950319
9. CryptoPotato (via CryptoQuant), "This Overlooked Binance Metric Might Predict
   Bitcoin's Next Major Move" (spot-perp delta)
   https://cryptopotato.com/this-overlooked-binance-metric-might-predict-bitcoins-next-major-move/
10. statsmodels documentation, Granger Causality tests
    https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.grangercausalitytests.html
