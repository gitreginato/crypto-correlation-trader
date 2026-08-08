# Topico: Volume Profile (VPVR), POC, VAH/VAL e HVN/LVN

**Data:** 2026-07-15
**Categoria:** Microestrutura

## TL;DR

Volume Profile e um histograma horizontal que mostra quanto volume foi negociado em cada nivel de preco, em vez de por tempo. VPVR (Volume Profile Visible Range) recalcula automaticamente conforme o range visivel no chart. POC (Point of Control) e o nivel de maior volume, a ancora de "fair value". VA (Value Area) e a faixa com ~70% do volume, delimitada por VAH (High) e VAL (Low). HVNs (High Volume Nodes) sao zonas de suporte/resistencia forte; LVNs (Low Volume Nodes) sao zonas de passagem rapida. A ferramenta mapeia onde o mercado concordou sobre preco, revelando suporte e resistencia baseados em volume real negociado, nao em linhas arbitrárias.

## Explicacao para criancas

Imagine um mapa de calor de um shopping. O Volume Profile e como olhar de cima e ver por onde as pessoas mais andaram. Os corredores com muita gente, bem marcados, sao os High Volume Nodes: lojas fortes, onde todos param. Os corredores vazios, quase sem marca, sao os Low Volume Nodes: atalhos que as pessoas atravessam rapido sem parar. O Point of Control e a praca de alimentacao, o lugar onde mais gente se concentrou, o centro de tudo. Quando voce volta ao shopping, tende a passar pela praca de alimentacao de novo: o preco tambem tende a voltar ao POC, porque e onde o mercado sentiu que valia a pena.

## Como funciona tecnicamente

### Volume tradicional vs Volume Profile

```
Volume tradicional: bar de volume por candle (eixo X = tempo)
Volume Profile:     volume por nivel de preco (eixo Y = preco)

Volume tradicional responde: "quanto foi negociado as 14h?"
Volume Profile responde:    "em que nivel de preco foi mais negociado?"
```

### Tipos de Volume Profile

- **VPVR (Visible Range):** recalcula sobre o que esta visivel no chart. Zoom in/out atualiza POC, VAH, VAL. Mais usado.
- **VPFR (Fixed Range):** range manual fixo (data A a data B). Snapshot estatico.
- **Session Volume Profile:** por sessao (diario, semanal). Mostra evolucao do POC ao longo do dia.
- **Volume Node Profile:** apenas nodos de alto/baixo volume, sem histograma completo.

### Componentes

| Conceito | Definicao | Uso |
|----------|-----------|-----|
| POC (Point of Control) | Nivel de preco com maior volume | Ancora de equilibrio / fair value |
| VA (Value Area) | Faixa com ~70% do volume negociado | Zona de valor justo |
| VAH (Value Area High) | Topo do value area | Resistencia institucional |
| VAL (Value Area Low) | Base do value area | Suporte institucional |
| HVN (High Volume Node) | Nivel com volume anormalmente alto | Suporte/resistencia forte |
| LVN (Low Volume Node) | Nivel com volume anormalmente baixo | Zona de passagem rapida |

### Calculo do Value Area (metodo TPO clássico)

O Value Area com 70% do volume e construido expandindo a partir do POC:

```python
def calc_value_area(volume_profile, poc_idx, target_pct=0.70):
    total_vol = volume_profile.sum()
    target_vol = total_vol * target_pct
    cum_vol = volume_profile[poc_idx]
    low_idx = high_idx = poc_idx
    bins = len(volume_profile)
    while cum_vol < target_vol and (low_idx > 0 or high_idx < bins - 1):
        # expande para o lado com mais volume adjacente
        if low_idx > 0 and (high_idx >= bins - 1
                or volume_profile[low_idx - 1] >= volume_profile[high_idx + 1]):
            low_idx -= 1
            cum_vol += volume_profile[low_idx]
        elif high_idx < bins - 1:
            high_idx += 1
            cum_vol += volume_profile[high_idx]
        else:
            break
    return low_idx, high_idx, cum_vol
```

Esse e exatamente o algoritmo ja implementado em `scripts/analyze_live.py` (`calc_volume_profile`, linhas 161-202), que retorna `poc_price`, `vah_price`, `val_price`, bins e volumes.

### Distribuicao do histograma

Para cada bin de preco i dentro do range [price_min, price_max]:

```
volume_profile[i] = sum(quantity dos trades executados no bin i)
```

Bins tipicos: 50 a 200. Mais bins = mais resolucao, mais ruido. Menos bins = smoother, menos precisao. Em cripto, 50 bins por sessao diaria e um compromisso razoavel. Regra adaptativa: bins ~ range_total / (2 * ATR_periodo), que ajusta resolucao a volatilidade.

### Volume profile por sessao

O VPVR visivel recalcula sobre o range visivel do chart. Para analise intraday estruturada, usa-se volume profile por sessao:

```python
def calc_session_profile(trades: pd.DataFrame, session_start: str = "00:00") -> dict:
    """Computa volume profile por sessao UTC."""
    trades = trades.copy()
    trades["session"] = trades.index.floor("D")  # agrupar por dia UTC
    profiles = {}
    for session, group in trades.groupby("session"):
        profiles[session] = calc_volume_profile(group, bins=50)
    return profiles
```

Cada sessao tem seu proprio POC, VAH, VAL. Comparar POCs de sessoes consecutivas revela a estrutura de tendencia (migracao do POC). O POC da sessao atual e o imã mais forte para o preco intradia; POCs de sessoes anteriores viram suporte/resistencia quando retestados.

### Volume profile vs Volume tradicional em pratico

| Pergunta | Volume tradicional responde | Volume Profile responde |
|----------|---------------------------|------------------------|
| Quando negociou mais? | Sim (por tempo) | Nao |
| Onde negociou mais? | Nao | Sim (por preco) |
| Qual o fair value? | Nao | POC |
| Onde esta suporte/resistencia? | Nao diretamente | HVN/VAH/VAL |
| Onde o preco acelera? | Nao | LVN (zona de passagem) |

O volume tradicional e temporal; o volume profile e espacial. Para trading de microestrutura, o espacial e mais acionavel porque niveis de preco repetem e sao testados, enquanto momentos no tempo nao se repetem.

### Interpretacao dos nodes

**HVN (High Volume Node):** zonas onde muito volume foi negociado. Representam consenso: compradores e vendedores concordaram ali. Funcionam como suporte/resistencia porque ha positions abertas defendendo o nivel. HVNs costumam alinhar com order blocks institucionais no framework Smart Money Concepts.

**LVN (Low Volume Node):** zonas de volume ralo. O mercado passou rapido, sem consenso. O preco tende a atravessar LVNs rapidamente (sem liquidez para segurar). Quando o preco reentra num LVN, costuma atravessar de novo. LVNs costumam coincidir com Fair Value Gaps.

**Padrao de migracao do POC:** durante tendencia, o POC migra na direcao da tendencia. Se o POC diario atual esta acima do POC de ontem, a estrutura e bullish. POCs antigos funcionam como suporte/resistencia quando o preco retorna.

### Classificacao quantitativa de nodes

Para transformar nodes em features numericas, define-se thresholds estatisticos:

```python
def classify_nodes(volume_profile: np.ndarray, k: float = 1.5) -> dict:
    mean_vol = volume_profile.mean()
    std_vol = volume_profile.std()
    hvn_mask = volume_profile > mean_vol + k * std_vol
    lvn_mask = volume_profile < mean_vol - k * std_vol
    return {
        "hvn_levels": np.where(hvn_mask)[0],
        "lvn_levels": np.where(lvn_mask)[0],
        "hvn_volumes": volume_profile[hvn_mask],
        "lvn_volumes": volume_profile[lvn_mask],
    }
```

k tipico entre 1.0 (mais nodes) e 1.5 (apenas extremes). Nodes devem ser identificados dentro do range relevante, nao sobre todo o historico, para evitar que HVNs de meses atras dominem o profile atual.

### Dinamica de retorno ao POC

O POC age como ima. Quando o preco se afasta do POC, ha tendencia de retorno. Quando o preco esta no ou perto do POC, consolida. Pensar no POC como ponto de equilibrio do mercado para aquele range. A forca do imã decai com o tempo: um POC de 1 hora atrai menos que um POC de 1 dia.

### Value Area como zona de negociacao

A dinamica do Value Area define comportamentos classicos:

- **Preco dentro do VA:** mercado aceita o preco como fair. Consolidacao, range-bound. Estrategias de mean reversion funcionam.
- **Preco acima do VAH:** mercado em premium. Sinal de que o preco pode estar esticado. Sellers tendem a aparecer.
- **Preco abaixo do VAL:** mercado em discount. Buyers tendem a aparecer.
- **Preco rejeita voltar ao VA apos breakout:** trend confirmation. O VA antigo vira suporte/resistencia na direcao oposta.

### Volume Shelf (prateleira de volume)

Em cripto, niveis de alto volume visiveis no VPVR que nao foram testados ainda pelo preco atual funcionam como "volume shelves": suporte/resistencia oculto baseado em negociacao passada. Mais confiavel que linhas de tendencia arbitrárias porque reflete liquidez real. Shelves sao HVNs que o preco ainda nao visitou desde que se formaram: o mercado os respeita quando retorna porque ha positions pendentes defendendo o nivel.

### Migracao do POC como indicador de trend

Comparar POCs consecutivos (diarios ou por sessao) gera um indicador de estrutura:

```
trend_structure = sign(POC_hoje - POC_ontem)

trend_structure > 0 por N sessoes seguidas: estrutura bullish (POC subindo)
trend_structure < 0 por N sessoes seguidas: estrutura bearish (POC caindo)
trend_structure alternando: range/consolidacao
```

POC que para de migrar e fica no mesmo nivel por varias sessoes indica acumulacao/distribuicao: o mercado esta consolidando posicoes antes do proximo movimento direcional.

## Estado do mercado em 2026

VPVR continua como ferramenta central de analise institucional em cripto. Plataformas como Bitfinex, TradingView, KuCoin e Datawallet publicaram guias atualizados em 2026 integrando VPVR com Smart Money Concepts (SMC). A convergencia que ganhou forca: HVNs do VPVR alinham com order blocks institucionais; LVNs alinham com Fair Value Gaps. Isso tornou o VPVR uma ponte entre volume profile classico e SMC, dois frameworks que antes operavam separados.

Caso concreto publicado pela Bitfinex (BTC/USD 1h, 23 de abril de 2026): HVN formado logo abaixo do preco atual (~US$ 75 a 76K), POC em US$ 75.753 atuando como suporte forte. O blog Bitfinex destaca que o VPVR no TradingView built-in permite alternar entre Volume Profile Fixed Range e Visible Range sem ferramenta externa.

A Gate publicou guia em janeiro de 2026 formalizando a estrategia VPoC (Volume + Price + Time) que combina POC com moving averages e Fibonacci. O consenso: POC funciona melhor combinado, nunca isolado. KuCoin publicou estudo sobre "volume shelves" no contexto do mercado australiano de cripto em fevereiro de 2026, destacando que ~22% dos adultos australianos holdiam ativos digitais, elevando a demanda por ferramentas de alta fidelidade como VPVR.

O ponto fundamental de 2026: o VPVR deixou de ser so visual. Quant desks agora extraem POC/VAH/VAL como features numericas em pipelines de ML, junto com order flow imbalance e CVD, para modelos preditivos de suporte/resistencia baseados em volume negociado. A normalizacao POC -> VAH -> VAL como coordenadas (em z-score ou como distancia relativa ao preco atual) permite comparar estrutura de volume across ativos e across janelas temporais.

### Convergencia VPVR + Smart Money Concepts

A integracao que se consolidou em 2026:

- **HVN ~ Order Block:** zonas de alto volume no VPVR correspondem a order blocks institucionais (zonas de impulso que o mercado respeita no reteste). Cruzar as duas confirmacoes aumenta confianca no nivel.
- **LVN ~ Fair Value Gap:** zonas de volume ralo correspondem a FVGs (gaps de valor justo, areas que o mercado preenche rapido). LVNs sao alvos de movimento, nao suporte/resistencia.
- **POC ~ Equilibrio:** o POC funciona como o ponto de equilibrio que o SMC chama de "fair value". Preco acima do POC = premium, abaixo = discount.
- **VAH/VAL ~ Premium/Discount zones:** mapeia diretamente para o framework Premium/Discount do SMC.

Essa convergencia tornou o VPVR uma ferramenta de validacao: se um nivel de SMC nao tem volume correspondente no VPVR, a tese e mais fraca.

### VPVR como feature numerica em pipelines quant

A transformacao do VPVR em features para ML em 2026 seguiu este padrao:

```
vpvr_features = {
    "dist_to_poc_atr": (close - poc_price) / atr,        # distancia ao POC em ATR
    "dist_to_vah_atr": (close - vah_price) / atr,
    "dist_to_val_atr": (close - val_price) / atr,
    "price_regime": "premium" if close > vah else "discount" if close < val else "fair",
    "poc_migration_sign": sign(poc_today - poc_yesterday),
    "n_hvn_near": count(hvn_levels within 1 ATR of close),
    "n_lvn_near": count(lvn_levels within 1 ATR of close),
    "va_width_pct": (vah - val) / close,                  # largura do value area
}
```

Essas features sao invariantes a escala (normalizadas por ATR ou por preco), permitindo comparar estrutura de volume across ativos com precos muito diferentes (BTC US$ 100k vs altcoin US$ 0.10).

## Ferramentas e APIs disponiveis

- **TradingView (built-in)**, tipo: indicador VPVR/VPFR, custo: freemium, URL: https://www.tradingview.com. Volume Profile Visible Range e Fixed Range nativos no menu de indicadores.
- **Binance klines REST**, tipo: dados para construir VPVR, custo: gratis, URL: `https://api.binance.com/api/v3/klines`. Volume por candle para agregar por nivel de preco.
- **Binance aggTrade WebSocket**, tipo: tick data para VPVR de alta resolucao, custo: gratis, URL: `wss://stream.binance.com:9443/ws/btcusdt@aggTrade`. Permite volume por preco com granularidade de tick.
- **Coinglass API V4**, tipo: volume footprint + CVD aggregated, custo: freemium/pago, URL: https://www.coinglass.com/CryptoApi. Volume footprint charts cross-exchange.
- **Kaiko**, tipo: L1/L2 com volume por trade, custo: pago (from US$ 1.000/mes), URL: https://www.kaiko.com/products/l1-l2-data. Tick-level para volume profile institucional.
- **Amberdata**, tipo: market data + analytics, custo: pago institucional, URL: https://www.amberdata.io. Agora parte da Kaiko (aquisicao 2026). CloudSync para data warehouses.
- **Bitfinex charts**, tipo: VPVR nativo via TradingView, custo: gratis para usuarios, URL: https://blog.bitfinex.com/education/chart-decoder-series-volume-profile-where-the-market-actually-trades/. Indicador built-in, sem ferramenta externa.
- **Tardis.dev**, tipo: replay historico de ticks para VPVR, custo: pago, URL: https://tardis.dev. Replay de order flow historico para reconstruir volume profile em qualquer periodo passado.
- **Quantum Algo**, tipo: guia de estrategia VPVR + SMC, custo: gratis (blog), URL: https://www.quantum-algo.com/blog/volume-profile-trading-strategy-guide. Integracao VPVR com session profiles e order blocks.

## Por que importa para o crypto-correl-bot

O bot ja implementa o core do VPVR. Em `scripts/analyze_live.py`:

- `calc_volume_profile` (linhas 161-202): computa histograma com 50 bins, encontra POC, expande Value Area 70%, retorna `poc_price`, `vah_price`, `val_price`, `bins`, `volumes`, `total_volume`, `volume_in_va`. Algoritmo correto e funcional.
- Dashboard live ja plota VPVR (referenciado em `analyze_live.py` linhas 953, 1523-1527 com dados de `volume_profile`).

Lacunas concretas:

1. **Sem deteccao de HVN/LVN.** O bot retorna o histograma mas nao classifica nodos como HVN ou LVN. Implementar: HVN se volume[i] > media + k*desvio_padrao; LVN se volume[i] < media - k*desvio_padrao (k tipico 1.0 a 1.5). Retornar lista de niveis HVN/LVN para o dashboard. Funcao `classify_nodes(volume_profile, k)` pronta para implementar.
2. **VPVR so por janela de trades recente, nao por sessao.** O bot calcula sobre os trades carregados no buffer. Adicionar volume profile por sessao UTC (reset diario) e por range visivel (multi-dia) daria suporte/resistencia mais robusto. Implementar `calc_vpc_session(trades, session_start_utc="00:00")`.
3. **Sem tracking de migracao do POC.** Comparar POC atual com POC anterior (dia/session anterior) e registrar direcao da migracao como feature de trend (POC subindo = bullish structure). Implementar `track_poc_migration(sessions)` retornando serie temporal de POCs e o sinal de estrutura.
4. **Sem combinacao com order blocks / SMC.** Cruzar HVNs com zonas de order block (swings de preco) aumentaria confianca nos niveis de suporte/resistencia. A convergencia HVN + order block e um nivel de maior probabilidade que HVN isolado.
5. **Volume shelves nao identificados.** Marcar HVNs nao testados pelo preco atual como "shelves" (suporte/resistencia potencial) enriqueceria o sinal. Um shelf e um HVN que o preco ainda nao visitou desde que se formou: o mercado tende a respeitar no reteste.
6. **Resolucao fixa de 50 bins.** Tornar configuravel por timeframe (mais bins em 1h, menos em 1d) melhoraria adaptabilidade. Regra pratica: bins ~ range / (2 * ATR).
7. **Sem Value Area como zona de negociacao.** O bot computa VAH/VAL mas nao usa para classificar preco atual como premium/discount. Implementar: `if close > VAH: regime = "premium"; elif close < VAL: regime = "discount"; else: regime = "fair"`. Esse regime e contexto para sinais de mean reversion.
8. **Volume Profile como feature de ML.** Converter POC, VAH, VAL em features numericas: distancia do close ao POC (em ATR), distancia ao VAH, distancia ao VAL. Essas features alimentam modelos preditivos de reversao.

Recomendacao: estender `calc_volume_profile` em `src/analysis/` (ou criar `src/analysis/volumeprofile.py`) com `classify_nodes(profile, k)`, `calc_vpc_session(trades, session_start)`, `track_poc_migration(sessions)`, `detect_volume_shelves(hvns, current_price)`, `classify_price_regime(close, vah, val)`, `calc_vpvr_features(ohlcv, bins)`. Integrar HVN/LVN no dashboard como linhas horizontais destacadas. Funcoes testaveis com dados sinteticos (seed fixo), cobrindo edge cases: preco constante (1 bin), volume zero, range minimo.

## Referencias

- https://www.datawallet.com/crypto/vpvr-indicator-explained (VPVR: POC, HVN, value area, uso em cripto)
- https://www.gate.com/crypto-wiki/article/what-is-point-of-control-how-to-use-poc-in-crypto-trading-20260116 (Gate 2026: POC, VPoC, HVN/LVN, estrategia com MA e Fibonacci)
- https://blog.bitfinex.com/education/chart-decoder-series-volume-profile-where-the-market-actually-trades/ (Bitfinex 2026: POC US$ 75.753, VAH/VAL, VPVR vs VPFR)
- https://www.quantum-algo.com/blog/volume-profile-trading-strategy-guide (POC, value area, HVN/LVN, alinhamento com SMC e order blocks)
- https://www.kucoin.com/en-au/blog/vpvr-strategy-for-australian-intraday-trading (KuCoin 2026: volume shelves, VPVR em intraday)
- https://www.coinglass.com/CryptoApi (Coinglass API V4: volume footprint, CVD aggregated)
