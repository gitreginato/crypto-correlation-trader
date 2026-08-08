# Topico: Microstructure Toxicity: Kyle's Lambda, Amihud, VPIN, Roll e Corwin-Schultz

**Data:** 2026-07-15
**Categoria:** Microestrutura

## TL;DR

Metricas de microestrutura estimam liquidez, impacto de preco e toxicidade do order flow a partir de dados de baixa frequencia (OHLCV) ou alta frequencia (trades, book). Kyle's Lambda mede impacto de preco por unidade de volume (inverso de profundidade de mercado). Amihud illiquidity mede resposta de preco ao volume em dolar. VPIN (Volume-Synchronized Probability of Informed Trading) detecta fluxo toxico de traders informados via imbalance em volume-time. Roll's spread estima spread efetivo via autocovariancia de retornos. Corwin-Schultz estima spread via range high-low intraday. Juntas, essas metricas classificam regimes de liquidez e antecipam movimentos de preco em quant trading.

## Explicacao para criancas

Imagine uma piscina. Se ela e grande e funda, voce joga uma pedra e a agua mal se mexe: e liquida, impacto baixo (Kyle's Lambda baixo, Amihud baixo). Se e uma piscina pequena e rasa, a mesma pedra faz ondas enormes: pouco liquida, impacto alto. VPIN e como perceber que alguem com informacao privilegiada esta jogando pedras de um lado so, tentando nao chamar atencao: o nivel da agua comeca a inclinar antes da onda chegar. Roll e Corwin-Schultz sao formas de medir o tamanho da borda da piscina (o spread) so observando as ondulinhas da agua, sem ver a borda diretamente.

## Como funciona tecnicamente

### Kyle's Lambda (price impact)

Kyle (1985) modelou trading estrategico por um informed trader contra market makers competitivos. O parametro lambda mede impacto de preco por unidade de order flow. Lambda alto = menos liquido, maior informacao assimetrica.

Forma reduzida (regressao):

```
delta_m_t = alpha + Lambda * Q_t + epsilon_t

m_t   = log price (ou mid price)
Q_t   = signed order flow (net buy volume - net sell volume)
Lambda = price impact per unit volume (inverse market depth)
```

Estimacao via OLS com erros HAC (Newey-West) para inferencia robusta. Implementacao em Python:

```python
def calc_kyle_lambda(returns: pd.Series, volumes: pd.Series) -> float:
    aligned = pd.DataFrame({'ret': returns.abs(), 'vol': volumes}).dropna()
    if len(aligned) < 20 or aligned['vol'].std() == 0:
        return 0.0
    lambda_est = np.linalg.lstsq(aligned[['vol']], aligned['ret'], rcond=None)[0][0]
    return float(lambda_est)
```

Janela tipica: 30 min rolling em alta frequencia, ou diaria em baixa frequencia.

### Amihud Illiquidity

Amihud (2002) mede illiquidez como resposta de preco ao volume em dolar. intuitivo: se pouco volume move muito o preco, o mercado e iliquido.

```
ILLIQ_t = |return_t| / dollar_volume_t

Amihud_window = mean(ILLIQ) over window (tipico 20 periodos)

Amihud alto = iliquido (preco sensivel a volume)
Amihud baixo = liquido
```

### VPIN (Volume-Synchronized Probability of Informed Trading)

Easley, Lopez de Prado e O'Hara (2012). Detecta toxicidade do order flow agrupando trades em volume-time (buckets de volume igual), nao em wall-clock. Normaliza para periodos de atividade variavel.

Passo a passo:

1. **Agrupar trades em buckets de volume igual.** Se BTC tradeou US$ 10M na ultima hora e o bucket size e US$ 500K, gera 20 buckets. Volume-synchronization e critico: normaliza o padrao U-shaped intraday de volume.
2. **Classificar cada trade como buy ou sell** via tick rule ou bulk volume classification (na Binance, usar flag `isBuyerMaker` diretamente).
3. **Calcular imbalance por bucket.** Se bucket de US$ 500K tem US$ 400K buy e US$ 100K sell: imbalance = |0.8 - 0.2| = 0.6. Ruido aleatorio produz ~0.5 (noise floor).
4. **Media do imbalance** sobre ultimos 10 a 20 buckets. Esse e o VPIN raw (0 a 1).
5. **Normalizar.** Raw 0.5 = ruido. Rescalar: `normalized = max(0, (raw - 0.5) * 2)`.

```
VPIN normalizado > 0.35 (raw ~0.675): informed trading elevado
VPIN normalizado > 0.50 (raw ~0.75): move major provavel em minutos a horas
```

### Implementacao de VPIN em Python

```python
def calc_vpin(trades: pd.DataFrame, bucket_size: float, n_buckets: int = 50) -> float:
    """VPIN normalizado a partir de trades classificados."""
    cum_vol = 0.0
    buy_in_bucket = 0.0
    sell_in_bucket = 0.0
    imbalances = []
    for _, t in trades.iterrows():
        qty = t["quantity"]
        cum_vol += qty
        if t["is_buyer_maker"]:
            sell_in_bucket += qty
        else:
            buy_in_bucket += qty
        if cum_vol >= bucket_size:
            total = buy_in_bucket + sell_in_bucket
            imb = abs(buy_in_bucket - sell_in_bucket) / total if total > 0 else 0
            imbalances.append(imb)
            cum_vol = 0.0
            buy_in_bucket = 0.0
            sell_in_bucket = 0.0
    if len(imbalances) < n_buckets:
        return 0.0
    raw_vpin = np.mean(imbalances[-n_buckets:])
    return max(0.0, (raw_vpin - 0.5) * 2.0)  # normalizar: 0.5 -> 0.0, 1.0 -> 1.0
```

O bucket_size tipico e ~1/50 do volume medio diario. n_buckets entre 10 e 50. VPIN normalizado > 0.35 e alerta; > 0.50 e sinal forte de move iminente.

Insight critico: VPIN diz QUE informed traders estao ativos, mas nao a DIRECAO. Combinar com CVD para direcao: VPIN elevado + CVD buy forte = acumulacao informada.

### Roll's Spread Estimator

Roll (1984) estima spread efetivo a partir da autocovariancia de retornos. Sem precisar de book. Premissa: spreads geram bounce negativo serial de 1 lag.

```
S_Roll = 2 * sqrt(-cov(r_t, r_{t-1}))   se cov < 0
S_Roll = 0                               se cov >= 0 (estimador falha)

spread_efetivo_estimado = S_Roll
```

Implementacao:

```python
def calc_roll_spread(returns: pd.Series, window: int = 20) -> float:
    if len(returns) < window:
        return 0.0
    cov = returns.rolling(window).apply(
        lambda x: np.cov(x[:-1], x[1:])[0, 1], raw=True
    ).iloc[-1]
    return float(2 * np.sqrt(-cov)) if cov < 0 else 0.0
```

### Corwin-Schultz Spread Estimator

Corwin e Schultz (2012) estimam spread via range high-low intraday. Premissa: o range diario reflete volatilidade + bid-ask bounce. Maior spread inflaciona o range.

```
Para cada dia, com high H e low L:
beta = sum(ln(H/L)^2) ao longo de N dias
gamma = ln(H_max / L_min)^2 ao longo de N dias (max high, min low)
alpha = (sqrt(2*beta) - sqrt(beta)) / (3 - 2*sqrt(2)) - gamma

S_CS = 2 * (exp(alpha) - 1) / (1 + exp(alpha))

S_CS = spread estimado como fracao do preco
```

Vantagem sobre Roll: usa high/low que sao mais faceis de obter que tick data, e nao quebra quando cov >= 0. Limitacao: assume que o componente de spread e constante ao longo do dia, o que nao vale em cripto (spread varia com regime). Mesmo assim, o estimador captura bem a tendencia de spread.

### Abdi-Ranaldo estimator

Abdi e Ranaldo (2017) refinam Corwin-Schultz usando close-to-high e close-to-low. O estudo de 2020 (Dimpfl, Mestel et al.) mostrou que Abdi-Ranaldo e Corwin-Schultz superam outros estimadores em descrever variacoes temporais de liquidez em cripto, independentemente da frequencia de observacao, venue e benchmark de alta frequencia.

### Modelo estrutural de Kyle (1985)

Kyle derivou o equilibrio de trading estrategico por um informed trader contra market makers competitivos. Resultados centrais:

- O preco segue um martingale em relacao a informacao publica.
- Lambda e a constante de price impact: preco se ajusta proporcionalmente ao order flow signed.
- Em equilibrio, o informed trader executa gradualmente para minimizar impacto, nao de uma vez.
- A profundidade de mercado (1/lambda) mede quanta ordem signed o mercado absorve por unidade de movimento de preco.

A forma reduzida (regressao delta_m = alpha + Lambda * Q + epsilon) e a que se usa na pratica. A forma estrutural exige estimacao por maximum likelihood ou GMM, mais complexa e rara em trading aplicado.

### Quando cada metrica falha

- **Kyle lambda:** falha quando volume tem pouca variancia (std ~ 0) ou poucos pontos. Sensivel a outliers de volume.
- **Amihud:** falha quando dollar_volume e zero ou proximo (divide por zero). Sensivel a days com retorno extremo em volume baixo.
- **VPIN:** ruido alto se bucket size muito pequeno (poucos trades por bucket). Viessa se tick rule errado (~15% de erro).
- **Roll:** falha (retorna 0) quando autocovariancia e positiva, comum em tendencias fortes. Viessa para baixo em periodos de momentum.
- **Corwin-Schultz:** viessa para baixo quando volatilidade overnight e alta. Assumir spread constante intraday e irreal em cripto 24/7.

### PIN (Probability of Informed Trading) classico

O precursor do VPIN. Modelo estrutural de Easley e O'Hara:

```
PIN = (alpha * mu) / (alpha * mu + 2 * epsilon)

alpha = prob de evento informacional
mu    = taxa de chegada de trades informados
epsilon = taxa de trades nao informados (ruido) de cada lado
```

PIN exige estimacao por maximum likelihood, mais complexo. VPIN e a aproximacao pratico, livre de parametros, em volume-time.

### Comparativo de estimadores

| Metrica | O que mede | Dados necessarios | Quando usar |
|---------|-----------|-------------------|-------------|
| Kyle's Lambda | price impact / unidade volume | returns + signed volume | detectar liquidez, info assimetrica |
| Amihud | |return| / dollar volume | OHLCV + volume | illiquidez rapida, cross-asset |
| VPIN | toxicidade (informed trading) | trades classificados buy/sell | early warning de moves |
| Roll | spread efetivo | returns series | spread sem book, baixa freq |
| Corwin-Schultz | spread efetivo | OHLC (high/low) | spread sem tick data |

Estudo academico (Dimpfl, Mestel et al., J. Banking & Finance 2020): Corwin-Schultz e Abdi-Ranaldo superam em variacao temporal; Kyle-Obizhaeva e Amihud superam em estimar niveis absolutos de liquidez e distinguir venues. Nao ha medida universalmente melhor.

## Estado do mercado em 2026

Microestrutura de cripto ganhou papers academicos robustos em 2025-2026. Um estudo de Easley et al. (Cornell, SSRN 4814346) aplicou metricas de microestrutura a 5 criptos maiores e mostrou: valores surpreendentemente altos de Roll Measure e VPIN em cripto vs equities, indicando maior toxicidade por info assimetrica. As metricas tem poder preditivo para dinamica de preco, estavel mesmo durante o "crypto winter".

Um paper de 2026 (Frontiers in Blockchain, "Microstructure alpha: hierarchical learning and cross-asset transfer") integrou spread bid-ask, Kyle's lambda, Amihud, VPIN e order flow imbalance em um modelo preditivo unificado com aprendizado hierarquico. O framework construiu features motivadas em microestrutura classica e mostrou transfer cross-asset.

Validacao pratico-publicada (MEXC News, 2026): VPIN funciona em futuros perpétuos de BTC. Sinal "Follow Smart Money" (long quando VPIN sobe + flow buy-heavy) rendeu +59.4 bps/trade bruto, +31.4 bps liquido (t=8.68, p<0.0001). Walk-forward 26 meses: Sharpe OOS medio 0.88, 4 de 6 folds lucrativos, 102 trades, max drawdown 12.2%. Descoberta critica: o alpha esta decaindo. 2024: +82 bps/trade, 2025: +38 bps, 2026 YTD: +12 bps. E so funciona em BTC, nao em alts. Isso sugere que o sinal esta sendo arbitrado conforme mais players o adotam.

Paper academico (Abad, Benito, Lopez, Sanchez 2025) validou VPIN em cripto para predicao de volatilidade (VPIN prediz |retorno| futuro), nao alpha direcional. O estudo de price jumps em Bitcoin (Scribd 997497570) correlacionou VPIN com saltos de preco.

Um repositorio GitHub (drelick/kyle-1985-digital-variant) demonstrou estimacao de Kyle lambda em BTC-USD Coinbase com signed order flow e HAC inference, com robustez across time aggregations e regimes de volatilidade.

Consolidou-se em 2026 que metricas de microestrutura de equities funcionam em cripto, mas com niveis mais altos de toxicidade e com decay de alpha mais rapido que em mercados tradicionais.

## Ferramentas e APIs disponiveis

- **Binance klines REST**, tipo: OHLCV + taker buy volume, custo: gratis, URL: `https://api.binance.com/api/v3/klines`. Suficiente para Amihud, Roll, Corwin-Schultz, VPIN via taker_buy_base.
- **Binance aggTrade WebSocket**, tipo: tick classificado, custo: gratis, URL: `wss://stream.binance.com:9443/ws/btcusdt@aggTrade`. Para VPIN em volume-time e Kyle lambda com signed order flow.
- **Coinglass API V4**, tipo: taker buy/sell + order book imbalance, custo: freemium/pago, URL: https://www.coinglass.com/CryptoApi. Inputs para VPIN e toxicity.
- **Kaiko**, tipo: L1/L2 tick-level com direcao, custo: pago (from US$ 1.500/mes), URL: https://www.kaiko.com/products/l1-l2-data. Ideal para Kyle lambda e VPIN institucional.
- **Amberdata**, tipo: market data + analytics, custo: pago institucional, URL: https://www.amberdata.io. Parte da Kaiko desde 2026.
- **FinRL order_flow_analytics.py (open source)**, tipo: lib de features de microestrutura, custo: gratis, repo: https://github.com/Mattbusel/FinRL_DeepSeek_Crypto_Trading/blob/main/order_flow_analytics.py. Implementa kyle_lambda, roll_spread, amihud_illiquidity, order_toxicity (PIN proxy), cum_delta.
- **drelick/kyle-1985-digital-variant (open source)**, tipo: estimacao Kyle lambda em cripto, custo: gratis, repo: https://github.com/drelick/kyle-1985-digital-variant-. HAC Newey-West, signed order flow.

## Por que importa para o crypto-correl-bot

O bot ja implementa 2 das 5 metricas. Em `scripts/analyze_live.py`:

- `calc_kyle_lambda` (linhas 144-152): regressao OLS de |return| vs volume. Funcional porem simplificada: usa volume absoluto, nao signed order flow. Implementacao academica correta usa Q_t (net buy - sell).
- `calc_amihud` (linhas 154-159): |return| / volume, rolling 20. Funcional porem usa volume em base asset, nao dollar volume. Amihud classico usa dollar volume.

Lacunas concretas:

1. **VPIN nao implementado.** E a metrica de maior valor preditivo (early warning de moves). O bot ja tem trades classificados via `is_buyer_maker`. Implementar: agrupar trades em buckets de volume igual, calcular imbalance por bucket, media rolling 10-20 buckets, normalizar. Pseudocodigo:
   ```
   def calc_vpin(trades, bucket_size, n_buckets=50):
       buckets = group_into_volume_buckets(trades, bucket_size)
       imbalances = []
       for b in buckets:
           buy_vol = sum(qty where not is_buyer_maker)
           sell_vol = sum(qty where is_buyer_maker)
           imbalances.append(abs(buy_vol - sell_vol) / (buy_vol + sell_vol))
       raw_vpin = mean(imbalances[-n_buckets:])
       return max(0, (raw_vpin - 0.5) * 2)  # normalizar
   ```
   Adicionar como feature no dashboard com alerta quando VPIN > 0.35.
2. **Roll's spread ausente.** O bot tem returns. Adicionar `calc_roll_spread` e trivial (autocovariancia de 1 lag). Complementa spread_bps do book quando book indisponivel ou em backtest historico sem L2.
3. **Corwin-Schultz ausente.** O bot tem OHLC. Adicionar `calc_corwin_schultz` para estimar spread sem tick data, util em backtest historico. Vantagem: nao quebra quando autocovariancia e positiva (limitacao do Roll).
4. **Kyle lambda simplificado.** Versao atual usa |return| vs volume absoluto. Versao correta usa signed order flow (delta ou CVD local) como Q_t. O bot tem CVD (`calc_cvd`), pode derivar Q_t por janela. Melhoraria a estimativa de impacto de preco real. A regressao `delta_m = alpha + Lambda * Q_t + epsilon` com Newey-West HAC errors e o padrao academico.
5. **Amihud sem dollar volume.** Trocar volume base por quote volume (p * q ou campo `quote_volume` do kline) alinharia com a definicao classica. Dollar volume normaliza across ativos (BTC volume 1 unidade ~ US$ 100k, altcoin volume 1 unidade ~ US$ 0.01).
6. **Sem features de toxicity no ML.** VPIN, Roll, Corwin-Schultz deveriam entrar como features em qualquer pipeline preditivo. Decay de alpha documentado (2024->2026: +82 -> +38 -> +12 bps/trade) sugere usar em ensemble, nao isolado. So funciona em BTC, nao em alts: usar como feature de BTC para prever correlacoes do grafo.
7. **Sem regime de liquidez.** Combinar Amihud + Roll + spread_bps para classificar regime de liquidez (liquid/normal/illiquid) como filtro de confianca para outros sinais. Sinais de CVD em regime iliquido sao menos confiaveis.
8. **Cross-asset toxicity.** O estudo Easley et al. mostrou efeitos cross-market de Roll e VPIN entre BTC e ETH. O bot tem multiplos simbolos: calcular VPIN por symbol e cruzar como feature preditiva de contágio de toxicidade.

Recomendacao: criar `src/analysis/liquidity.py` com `calc_vpin(trades, bucket_size, n_buckets)`, `calc_roll_spread(returns, window)`, `calc_corwin_schultz(ohlcv, n)`, `calc_kyle_lambda_signed(returns, signed_flow)`, `calc_amihud_dollar(returns, dollar_volume)`, `classify_liquidity_regime(amihud, roll, spread_bps)`. Integrar VPIN como alerta no dashboard live. Funcoes testaveis com dados sinteticos (seed fixo), cobrindo edge cases: sem trades, volume zero, returns constantes, autocovariancia positiva.

## Referencias

- https://doi.org/10.1016/j.jbankfin.2020.106041 (Dimpfl, Mestel et al., "How to measure the liquidity of cryptocurrency markets?", J. Banking & Finance 2020)
- https://stoye.economics.cornell.edu/docs/Easley_ssrn-4814346.pdf (Easley et al., microstructure metrics preditivos em 5 criptos, Roll e VPIN elevados)
- https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2026.1811716/full (Microstructure alpha: hierarchical learning, Kyle/Amihud/VPIN/OFI, 2026)
- https://www.mexc.co/news/1002105 (MEXC 2026: VPIN alpha em BTC perp, walk-forward, decay 2024->2026)
- https://github.com/drelick/kyle-1985-digital-variant- (estimacao Kyle lambda em BTC-USD Coinbase, HAC inference)
- https://github.com/Mattbusel/FinRL_DeepSeek_Crypto_Trading/blob/main/order_flow_analytics.py (features: kyle_lambda, roll_spread, amihud, toxicity, cum_delta)
- https://cripton.ai/en/guides/vpin-orderbook-imbalance-crypto (VPIN em cripto: volume-time, tick rule, toxic flow)
- https://www.buildix.trade/blog/vpin-crypto-indicator-volume-synchronized-probability-explained (matematica do VPIN: buckets, imbalance, normalizacao)
