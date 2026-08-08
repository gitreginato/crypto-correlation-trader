# Topico: Price Action (Breakout e Pullback)

**Data:** 2026-07-15
**Categoria:** Estrategia de Trading

## TL;DR

Price action e a leitura direta do movimento do preco, sem indicadores lagging. A estrategia identifica niveis chave de suporte/resistencia, padroes de candlestick e estrutura de mercado para entrar em breakouts (rompimentos) ou pullbacks (retrocessos a niveis chave). Nao ha script em `src/strategy/` ainda, so o manual em `docs/strategies/02-price-action-breakout-pullback.md` (STRAT-02). Tem duas variantes principais: breakout (entrar quando rompe um nivel com volume) e pullback (entrar quando retorna a um nivel apos impulso). Pesquisas de 2025 e 2026 mostram que breakout em Bollinger Bands em ETH retornou +94.84% em 6 meses com Sharpe 1.95, mas win rate de so 33% (compensado por R:R de 4.9:1). O Bollinger squeeze (contracao de volatilidade antes da expansao) e o setup mais documentado. A Gate Research confirma que mean reversion simples em squeeze e vulneravel a ruido e fee drag, e que filtros de volatilidade, cooldown e bandwidth screening melhoram significativamente a estabilidade.

## Explicacao para criancas

Imagine uma bola presa numa caixa. Ela quica nas paredes da caixa. As paredes sao o suporte (chao) e resistencia (teto). Um dia a bola ganha forca e rompe o teto da caixa: e o breakout, ela vai subir para um novo nivel. Ou ela sobe ate a metade da caixa e volta um pouco antes de continuar: e o pullback, voce entra nesse recuo. Em trading, lemos onde o preco parou antes (suporte/resistencia), como ele se moveu (candlesticks) e se faz higher-highs ou lower-lows (estrutura de mercado) para decidir entrar.

## Como funciona tecnicamente

### Suporte e resistencia

Niveis onde o preco encontrou pressao de compra (suporte) ou venda (resistencia) no passado. Sao zonas, nao linhas exatas. Metodos de deteccao:
- Swing highs/lows: picos e vales identificados por fractal analysis (n >= 2 candles de cada lado).
- Volume Profile: niveis com maior volume negociado (POC, Value Area).
- Order Blocks: ultimos candles de movimento contrario antes de um impulso forte.
- Previous day high/low: niveis do dia anterior (liquidez institucional).

### Estrutura de mercado

```
Uptrend:    Higher Highs (HH) + Higher Lows (HL)
Downtrend:  Lower Highs (LH) + Lower Lows (LL)
Range:      Equals Highs (EH) + Equals Lows (EL)
```

Mudanca de estrutura (BOS, Break of Structure, ou CHoCH, Change of Character) indica possivel reversao. BOS e continuacao na direcao da tendencia, CHoCH e contra a tendencia.

### Padroes de candlestick de reversao

| Padrao | Sinal | Condicoes |
|--------|-------|-----------|
| Pin Bar (Hammer/Shooting Star) | Reversao | Wick >= 2x body, rejeicao de nivel |
| Engulfing | Reversao | Candle 2 engloba candle 1, no nivel chave |
| Inside Bar | Continuacao | Candle 2 dentro do range da candle 1, pos-impulso |
| Doji | Indecisao | Open ~= close, apos movimento longo |
| Fakey | Reversao | Inside bar seguido de falso breakout |

### Multi-Timeframe Analysis

```
HTF (4H):    Direcao primaria (trend bias)
MTF (1H):    Estrutura intermediaria (niveis chave)
LTF (15m):   Entrada precisa (trigger candle)
```

Regra: so operar a favor da direcao do HTF, a menos que seja trade de reversao em nivel HTF.

### Variante 1: Breakout Setup (Long)

```
CONDICOES:
1. Preco consolida abaixo de resistencia (swing high ou Bollinger upper)
2. Bollinger squeeze: bandwidth no minimo de 120 periodos (volatilidade baixa)
3. Candle de rompimento fecha acima da resistencia com volume > 1.5x medio
4. Body do candle >= 60% do range (rompimento forte, nao so wick)
ENTRY: Long no fechamento do candle de rompimento
STOP: abaixo do low do candle de rompimento (ou abaixo da resistencia virada suporte)
TARGET: proximo nivel de resistencia ou 2:1 a 3:1 R:R
```

### Variante 2: Pullback Setup (Long)

```
CONDICOES:
1. Tendencia de alta confirmada no HTF (HH + HL)
2. Preco faz impulso forte (rompe resistencia com volume)
3. Preco retorna a resistencia virada suporte (pullback)
4. Candle de reversao bullish no nivel (pin bar, engulfing)
5. Volume diminui no pullback (sem pressao vendedora)
ENTRY: Long no fechamento do candle de confirmacao
STOP: abaixo do low do pullback
TARGET: proxima resistencia ou 2:1 R:R
```

### Bollinger Squeeze (o setup mais documentado)

O Bollinger squeeze identifica periodos de volatilidade anormalmente baixa que antecedem movimentos explosivos. E uma estrategia de antecipacao de breakout.

```
Squeeze ativo: Bollinger Band Width (BBW) no minimo de 120 periodos
Alternativa: Bollinger Bands contraidos dentro do Keltner Channel

Entrada:
- Long: preco fecha acima da upper band apos squeeze + MACD histograma bullish
- Short: preco fecha abaixo da lower band apos squeeze + MACD histograma bearish
Saida: trailing stop 2x ATR, ou re-entrada nas bandas por 3 candles, ou 3:1 R:R
```

Exemplo real (Sentinel, BTC diario janeiro 2026): BBW comprimido a 0.028 por 14 dias. Em 15 de janeiro, candle bullish forte fechou acima da upper band a $98,200. MACD cruzou bullish no mesmo dia. Preco foi a $108,500 nos 12 dias seguintes, capturando 10.5% de movimento.

### Stop, take profit e gestao de risco

Stop: abaixo/acima do candle de entrada (breakout) ou do pullback. ATR mult (1.5x default) para placement.
Target: proximo nivel de S/R ou R:R minimo (2:1 default). Trailing stop 2x ATR para ride o breakout.
Saida por invalidacao: se o breakout vira fakeout (preco volta dentro do range em 3 candles), sai.
Saida por tempo: se nao atingir target em N candles, sai (evita ficar preso em range que nao desenvolve).

### Timeframe e expected performance

Timeframe ideal: 15m, 1h, 4h. Horizonte de horas a dias.
Targets documentados: Sharpe 1.5+, max drawdown < 20%, win rate 30 a 45% em breakout (compensado por R:R alto), 50 a 60% em pullback.
Performance real reportada: Coinquant, breakout em Bollinger Bands (20,2) em ETH/USDT 4H, novembro 2025 a maio 2026: retorno +94.84%, Sharpe 1.95, max DD 21.61%, win rate 33.3% (7 wins / 14 losses), profit factor 2.45, avg win $2,289 vs avg loss $467 (payoff 4.9:1), 21 trades, 57.8% tempo em mercado, CAGR 94.8%. O ponto chave: win rate baixo mas R:R altissimo compensa. O maior flaw do backtest: sem stop loss, trades perdedores correram media de 84h (3x mais que vencedores). Stop de 3 a 5% melhoraria o perfil de risco.

### Tabela de parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `htf_timeframe` | 4h | 1h, 4h, 1d | Timeframe superior para bias |
| `mtf_timeframe` | 1h | 30m, 1h, 2h | Timeframe intermediario |
| `ltf_timeframe` | 15m | 5m, 15m, 30m | Timeframe de entrada |
| `swing_lookback` | 5 | 3 a 10 | candles de cada lado para swing detection |
| `breakout_volume_mult` | 1.5 | 1.2 a 2.5 | Multiplicador de volume medio |
| `pullback_fib_levels` | 0.382, 0.5, 0.618 | - | Niveis de Fibonacci para pullback |
| `min_candle_body_ratio` | 0.6 | 0.5 a 0.8 | Body/wick minimo para candle de confirmacao |
| `atr_period` | 14 | 10 a 20 | Periodo do ATR para stop |
| `atr_mult_stop` | 1.5 | 1.0 a 3.0 | Multiplicador de ATR para stop |
| `rr_min` | 2.0 | 1.5 a 3.0 | Risk:Reward minimo |
| `bbw_lookback` | 120 | 60 a 200 | Periodo para min de bandwidth (squeeze) |

### Exemplo numerico (breakout)

Cenario: ETH/USDT 4H. Resistencia em $3,800 (swing high anterior). Bollinger Band Width no minimo de 120 periodos (squeeze ativo). Candle de rompimento: abre $3,750, fecha $3,850, high $3,870, low $3,740. Volume 1.8x media. Body = $100, range = $130, body ratio = 0.77 (acima de 0.6, ok). Entrada long a $3,850. ATR(14) = $90. Stop = $3,850 - 1.5 * $90 = $3,715 (abaixo do low do candle). Target = $3,850 + 2 * $135 = $4,120. R:R = 2:1. Se ETH vai a $4,120, fecha com lucro. Se cai a $3,715, stop.

### Exemplo numerico (pullback)

Cenario: BTC em tendencia de alta (HTF 4H: HH + HL). Impulso rompeu $100,000 com volume. Preco retorna a $100,000 (resistencia virada suporte). Forma pin bar bullish (wick inferior rejeita $99,500, fecha em $100,200). Volume no pullback 40% abaixo da media (sem pressao vendedora). Entrada long a $100,200. Stop abaixo do low do pin bar em $99,400. Target na proxima resistencia $104,000. R:R = (3,800) / (800) = 4.75:1.

## Estado do mercado em 2026

Price action breakout e pullback seguem como estrategias populares e praticaveis em cripto em 2026. A evidencia mais solida vem do Bollinger squeeze, que e uma forma sistematizada de breakout. A Gate Research publicou em 2026 um backtest sistematico de mean reversion sob squeeze em BTC/USDT 5 minutos, concluindo que logica de reversao simples e altamente vulneravel a ruido de mercado, fee drag e falsos breakouts. A aplicacao de filtros de volatilidade, cooldown e bandwidth screening melhora significativamente win rate, estabilidade e estrutura risco-retorno geral. Ou seja: o squeeze funciona, mas precisa de filtros, nao e so entrar quando a banda contrai.

Quem pesquisa e bot: o Coinquant rodou dois backtests em ETH/USDT 4H de novembro 2025 a maio 2026. O primeiro (breakout em Bollinger Bands 20,2, entrada acima da upper OU abaixo da lower, saida abaixo da lower): +94.84% retorno, Sharpe 1.95, win rate 33.3%, profit factor 2.45, payoff 4.9:1. O segundo (squeeze reversal: BB declinando, preco abaixo da lower, fecha acima do midline SMA20, saida acima da upper): o maior flaw identificado foi ausencia de stop loss, que deixou perdedores correrem 3x mais que vencedores. A recomendacao e adicionar stop de 3 a 5% para melhorar o perfil de risco.

Quem ensina: blogs como Sentinel e PyQuantLab (Medium) ensinam Bollinger squeeze com regras claras. O PyQuantLab reporta 200% de lucro em 2025 tradando ETH com Bollinger squeeze, com bbands_devfactor = 1.0 e trailing stops. O Sentinel mostra exemplo real de BTC em janeiro 2026 (BBW 0.028, breakout a $98,200, target $108,500).

Performance real reportada e caveats: o retorno de +94.84% em 6 meses e impressionante mas veio de 21 trades so, o que e amostra pequena. Win rate de 33% significa que a maioria dos trades perde, e a estrategia so funciona porque o R:R e altissimo (4.9:1). Se o R:R cai (mercado muda, breakouts fake aumentam), a estrategia quebra. A ausencia de stop loss no backtest do Coinquant e um flaw estrutural que inflaciona o drawdown. Para o crypto-correl-bot, sempre incluir stop e nao confiar em amostras pequenas.

### Quem ensina e quem vende curso

A area de price action e mista. Blogs quant (Coinquant, Sentinel, PyQuantLab, Gate Research) explicam com backtest e codigo, tom honesto. Existe tambem muita venda de curso de price action com promessas de win rate alto, mas a evidencia mecanica mostra que breakout tem win rate baixo (30 a 45%) compensado por R:R alto. Quem promete win rate 70%+ em breakout provavelmente tem selection bias. O tom correto: breakout e uma estrategia de R:R alto com win rate baixo, e o segredo e cortar perdedores rapido e deixar vencedores correrem.

## Ferramentas e APIs disponiveis

### Bibliotecas Python

- `pandas` + `numpy`: deteccao de swing highs/lows (fractal), Bollinger Bands, bandwidth, candlestick patterns (pin bar, engulfing, inside bar).
- `ta` ou `pandas-ta`: Bollinger Bands, ATR, MACD prontos.
- `vectorbt`: backtest vetorizado de breakout e pullback com sweep de parametros.
- `scipy`: para deteccao de picos/vales (find_peaks) na analise de swing.

### Dados

- Binance Vision e REST API: klines multi-timeframe (15m, 1h, 4h) com OHLCV.
- Volume Profile: calcular a partir de klines ou usar dados de aggTrades para maior resolucao.

### Plataformas que suportam

- TradingView: Bollinger Bands, squeeze (TTM Squeeze), padroes de candlestick nativos. Bom para prototipagem.
- Sentinel Bot: builder de estrategia baseado em blocos com Bollinger + MACD.
- Backtrader: para validacao final com slippage e commission realistas.

### Combinacao com outras estrategias do projeto

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + VWAP (STRAT-07) | Alta | Candle de confirmacao no VWAP |
| + Liquidity Sweep (STRAT-09) | Alta | BOS/CHoCH e market structure, mesmo conceito |
| + Volume Profile (STRAT-05) | Alta | POC como nivel de S/R |
| + Momentum (STRAT-06) | Media | Breakout de Donchian e price action |

A combinacao mais natural e com STRAT-07 (VWAP): candle de confirmacao no VWAP e price action puro. E com STRAT-09 (liquidity sweep): BOS/CHoCH e estrutura de mercado sao conceitos de price action.

## Por que importa para o crypto-correl-bot

Ja temos script: nao. Nao ha `src/strategy/price_action.py`. So o manual em `docs/strategies/02-price-action-breakout-pullback.md` (STRAT-02), que documenta suporte/resistencia, estrutura de mercado, candlesticks, multi-timeframe e as duas variantes (breakout e pullback). A implementacao e o proximo passo.

STRAT-02. O que falta:

1. **Implementar `src/strategy/price_action.py`**: criar a classe `PriceActionStrategy(BaseStrategy)` com deteccao de swing highs/lows, BOS/CHoCH, candlestick patterns (pin bar, engulfing, inside bar) e as duas variantes (breakout e pullback).
2. **Bollinger squeeze como sub-estrategia**: implementar deteccao de squeeze (BBW no minimo de 120 periodos) e entrada no breakout. A evidencia mostra que e o setup mais documentado e testado.
3. **Sempre incluir stop loss**: o backtest do Coinquant sem stop e um flaw estrutural. Stop de 3 a 5% ou 1.5x ATR e obrigatorio.
4. **Filtros de volatilidade e cooldown**: a Gate Research mostra que filtros de bandwidth, volatilidade e cooldown melhoram significativamente a estabilidade. Implementar filtro de volatilidade (nao operar em vol extrema) e cooldown (esperar N candles apos trade perdedor).
5. **Multi-timeframe no backtest**: o manual prevê HTF/MTF/LTF mas o backtest precisa alinhar os timeframes corretamente (sem look-ahead entre eles).
6. **Validar R:R vs win rate**: esperar win rate baixo (30 a 45%) compensado por R:R alto (2:1 a 5:1). Nao otimizar para win rate alto, otimizar para profit factor e Sharpe.
7. **Amostra suficiente**: exigir pelo menos 50 a 100 trades no backtest antes de confiar. 21 trades (como o Coinquant) e pouco.

### Metricas de avaliacao (target)

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate (breakout) | 35 a 45% | 30% |
| Win rate (pullback) | 50 a 60% | 45% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 20% | < 30% |
| Avg R:R | 2.5:1+ | 1.5:1 |
| Profit factor | 1.5+ | 1.2 |
| Trades por mes | 5 a 15 | 3+ |

### Vantagens e desvantagens

Vantagens: nao depende de indicadores lagging (le o preco direto), R:R alto em breakout (2:1 a 5:1), conceitos de estrutura de mercado (HH/HL) sao robustos e renomeados em SMC, multi-timeframe alinha bias e entrada, Bollinger squeeze e bem documentado.

Desvantagens: win rate baixo em breakout (30 a 45%), falsos breakouts comuns em cripto (especialmente em news), deteccao de S/R e subjetiva sem regras estritas, candlestick patterns tem evidencia mista (muitos padroes nao tem edge estatistico), precisa de stop disciplinado (sem stop, drawdown explode), amostra pequena engana (21 trades nao confirma nada).

### Checklist de proximos passos para STRAT-02

1. Criar `src/strategy/price_action.py` com breakout e pullback.
2. Implementar deteccao de swing, BOS/CHoCH e candlestick patterns.
3. Adicionar Bollinger squeeze como sub-estrategia.
4. Sempre incluir stop (1.5x ATR ou 3 a 5%).
5. Adicionar filtros de volatilidade e cooldown.
6. Backtest multi-timeframe sem look-ahead.
7. Exigir >= 50 trades antes de confiar.

## Referencias

- Gate Research: "Bollinger Bands in Crypto Markets, Effectiveness Analysis and Mean Reversion Strategy Backtest", squeeze mean reversion em BTC/USDT 5min, filtros de bandwidth e cooldown melhoram estabilidade. gate.com/research.
- Coinquant: "Breakout Trading Strategy: Does It Work on Crypto? (Backtested)", ETH/USDT 4H, +94.84%, Sharpe 1.95, 33.3% WR, PF 2.45, payoff 4.9:1, 21 trades. coinquant.ai.
- Coinquant: "Bollinger Bands Backtest on Ethereum: What 6 Months of Data Shows", squeeze reversal, flaw de ausencia de stop loss. coinquant.ai.
- Sentinel: "Bollinger Bands Trading Strategy: Crypto Guide 2026", squeeze + breakout + MACD, exemplo BTC janeiro 2026. sentinel.redclawey.com.
- PyQuantLab (Medium): "200% Profit in 2025 Trading ETH using the Bollinger Band Squeeze Strategy". pyquantlab.medium.com.
- Manual interno: docs/strategies/02-price-action-breakout-pullback.md (STRAT-02)
