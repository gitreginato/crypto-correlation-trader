# Topico: VWAP Reversion

**Data:** 2026-07-15
**Categoria:** Estrategia de Trading

## TL;DR

VWAP (Volume Weighted Average Price) e o preco medio ponderado por volume. Instituicoes usam VWAP como benchmark de execucao: se compraram abaixo do VWAP, tiveram boa execucao. A estrategia de VWAP reversion explora o fato de que o preco tende a reverter ao VWAP durante o dia. Quando o preco se distancia mais de 2 desvios do VWAP, entra apostando na volta ao preco justo. Nao ha script em `src/strategy/` ainda, so o manual em `docs/strategies/07-vwap-reversion.md` (STRAT-07). E uma das estrategias mais simples, com win rate alto (60 a 70% tipico) e R:R baixo (1:1 a 1.5:1). Pesquisas de 2025 mostram que a calibracao da referencia importa: session VWAP resetado a meia-noite e miscalibrado (desvio sai perto de 2.0 em vez de 1.0). EWMA VWAP que nunca reseta e melhor calibrado. Um backtest reportou Sharpe de 11.32 em BTC, mas com so 15 trades, o que torna o numero estatisticamente fragil.

## Explicacao para criancas

Imagine que voce vai a uma feira onde varias pessoas compram e vendem macas. O preco medio das macas vendidas no dia e o VWAP: se muita gente comprou macas caras, o VWAP sobe; se compraram baratas, desce. Durante o dia, o preco de cada maca varia, mas tende a girar em torno desse preco medio. Se de repente uma maca fica muito mais cara que a media do dia, provavelmente o preco vai voltar para perto da media logo. Voce vende essa maca cara e recompra quando ela voltar ao preco medio.

## Como funciona tecnicamente

### Calculo do VWAP

```
VWAP = sum(typical_price * volume) / sum(volume)
typical_price = (high + low + close) / 3
```

Para session VWAP: resetado a cada inicio de dia (default meia-noite UTC), acumula volume desde a abertura. Para rolling VWAP: janela fixa (ex: 20 periodos). Para anchored VWAP: ancorado em um evento especifico (inicio da semana, ultimo swing high/low, evento de noticia como FOMC).

### Bandas de VWAP

```
Upper Band = VWAP + n * StdDev
Lower Band = VWAP - n * StdDev
StdDev = sqrt(sum(volume * (price - VWAP)^2) / sum(volume))
n = 1, 2 ou 3 desvios (similar a Bollinger Bands mas volume-weighted)
```

### Regras de entrada (LONG)

```
CONDICOES:
1. (VWAP - close) / VWAP > min_distance  (preco abaixo do VWAP)
2. (VWAP - close) / VWAP < max_distance  (nao tao longe que e anormal)
3. zscore = (close - VWAP) / vol_std < -entry_std  (2+ desvios abaixo)
4. Delta positivo (mais compras que vendas no candle)
5. Volume do candle > 1.5x volume medio
FILTRO DE TENDENCIA (opcional):
6. SE trend_filter: close do dia anterior acima do VWAP anterior
ENTRY: Long
STOP: abaixo do low do candle de entrada
TARGET: VWAP (preco justo)
```

### Regras de entrada (SHORT)

Simetrico: preco acima do VWAP, zscore > +entry_std, delta negativo, volume alto.

### VWAP Bounce (com confirmacao)

Variante mais conservadora: espera o preco aproximar do VWAP, forma candle de reversao (pin bar, engulfing) no VWAP, delta vira a favor, entra no fechamento do candle de confirmacao. Win rate maior, menos trades.

### VWAP Breakout e Retest

Preco rompe o VWAP, retorna ao VWAP (pullback), candle de reversao no VWAP confirma suporte/resistencia, entra na direcao do breakout com target na banda oposta.

### Stop, take profit e gestao de risco

Take profit no VWAP (preco voltou ao justo). Variante em bandas: fechar 50% no VWAP, 100% na banda oposta.
Stop loss: zscore passa de stop_std (3.5), o VWAP perdeu relevancia. Ou stop abaixo/acima do candle de entrada.
Saida por tempo: maximo 4h em posicao (VWAP reversion e intraday).
Saida por fim de sessao: fechar tudo antes de 23:00 UTC (VWAP vai resetar, contexto muda).
Maximo 5 trades por sessao. Reduzir tamanho 50% se volatilidade intraday > 2x a media.

### Timeframe e expected performance

Timeframe ideal: 5m, 15m, 1h. Horizonte de minutos a poucas horas.
Targets documentados: win rate 65%+, Sharpe 1.5+, max drawdown < 8%, profit factor 2.0+, R:R 1.5+, 30 a 80 trades por mes.
Performance real reportada: blog anomiq.io testou EWMA VWAP z-score em 8 simbolos (BTC, ETH, SOL, XRP, BNB, DOGE, ADA, LINK) no ano calendario 2025 completo, com dados de 1 minuto do pipeline live. A primeira versao (entrada em z > 3.0, fast tape, hold ate 30 min, exit por z ou stop) gerou 423 eventos. O exit tight cortava ~64% dos vencedores antes da reversion completar. O exit reworkado (stop 35 bps, trailing ativa em 20 bps de lucro, dar de volta 15 bps do pico) melhorou o resultado. O QuantPie reportou Sharpe 11.32, retorno anual 87.3%, max DD 2.1%, mas so 15 trades e 66.7% win rate: a amostra e fina demais para confiar (erro padrao grande, win rate real pode ser 50%).

### Calibracao da referencia (ponto critico de 2025)

O blog anomiq.io descobriu que o session VWAP resetado a 00:00 UTC estava miscalibrado: o desvio padrao do z-score saida perto de 2.0 em vez de 1.0. Um z-score deve ter desvio 1.0 por definicao. Se sai 2.0, os limiares de entrada (2.0 desvios) sao enganosos. A solucao foi reconstruir a referencia como EWMA VWAP por volume-clock que nunca reseta, e corrigir a calibracao. Sem essa correcao, nenhum backtest significa nada. Para o crypto-correl-bot, validar a calibracao do z-score do VWAP antes de confiar em qualquer resultado.

### Tabela de parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `vwap_type` | "session" | session, rolling, anchored | Tipo de VWAP |
| `rolling_window` | 20 | 10 a 50 | Janela para rolling VWAP |
| `band_std` | 2.0 | 1.5 a 3.0 | Desvios para bandas |
| `entry_std` | 2.0 | 1.5 a 3.0 | Desvio para entrada |
| `exit_std` | 0.5 | 0.0 a 1.0 | Desvio para saida (convergencia) |
| `stop_std` | 3.5 | 3.0 a 4.5 | Desvio para stop loss |
| `session_reset` | "00:00" | - | Hora de reset do session VWAP (UTC) |
| `min_distance_from_vwap` | 0.005 | 0.003 a 0.01 | Distancia minima do VWAP (0.5%) |
| `max_distance_from_vwap` | 0.05 | 0.03 a 0.08 | Distancia maxima (acima = anormal) |
| `trend_filter` | true | true, false | Filtrar sinais contra tendencia do dia |

### Exemplo numerico

Cenario: BTC a $98,000. Session VWAP = $99,500. StdDev volume-weighted = $600. Distancia = (99,500 - 98,000) / 99,500 = 1.5% (acima de min 0.5%, abaixo de max 5%, ok). Zscore = (98,000 - 99,500) / 600 = -2.5 (abaixo de -2.0, sinal long). Delta positivo no candle, volume 1.8x media. Entrada long a $98,000. Stop abaixo do low do candle (ex: $97,600). Target = VWAP = $99,500. R:R = (1,500 de lucro) / (400 de risco) = 3.75:1. Se BTC volta a $99,500, fecha com lucro. Se cai a $97,600, stop.

### VWAP como suporte/resistencia institucional

Acima do VWAP: compradores dominaram o dia (bullish bias). Abaixo: vendedores dominaram (bearish bias). Testes do VWAP: primeiro teste alta probabilidade de reacao (80%+), segundo teste media (60%+), terceiro teste baixa (VWAP vai ceder). Anchor VWAP em eventos importantes (inicio da semana, FOMC, liquidacao em massa) e nivel de suporte/resistencia mais forte que o VWAP diario.

### Vantagens e desvantagens

Vantagens: simples de implementar (VWAP e direto de calcular), win rate alto (60 a 70% tipico), benchmark institucional (VWAP e usado por grandes players, o que torna a linha auto-reforcad), funciona bem em intraday (horizonte curto e previsivel), baixo custo (poucos trades por dia, saida rapida), nao precisa de dados externos so OHLCV.

Desvantagens: so funciona intraday (VWAP reset diario, nao segurar overnight), sofre em dias de tendencia forte (preco nao volta ao VWAP), muitos sinais falsos em alta volatilidade, R:R tipicamente baixo (1:1 a 1.5:1, compensado por win rate alto), nao funciona bem em finais de semana (liquidez reduzida), a calibracao do z-score do session VWAP e enganosa se nao corrigida (desvio sai 2.0 em vez de 1.0).

## Estado do mercado em 2026

VWAP reversion segue como uma das estrategias intraday mais populares em cripto em 2026. A razao e estrutural: market makers e algoritmos de execucao (TWAP, VWAP, POV) empurram o preco de volta ao VWAP, e o VWAP e o benchmark institucional de qualidade de execucao. Esse feedback loop torna a linha auto-reforcad: o preco reage perto do VWAP porque todos esperam que reaja.

Quem pesquisa e bot: o blog anomiq.io e a referencia mais rigorosa, com backtest em dados de 1 minuto do pipeline live em 8 simbolos durante 2025 inteiro. A conclusao pratica e que a calibracao da referencia (EWMA VWAP vs session VWAP) e o exit (trailing em bps vs z tight) sao os dois pontos que definem se a estrategia funciona ou nao. O QuantPie reporta Sharpe 11.32 em BTC mas admite que a amostra de 15 trades e fina e que ETH, SOL e AVAX falham, o que mostra que o edge e especifico da microestrutura de BTC.

Quem ensina: blogs como coinxsight, cryptoprofitcalc e Mudrex explicam as variantes (VWAP bounce, VWAP breakout, VWAP reversion com bandas) com regras claras. O coinxsight reporta win rate de 60 a 70% em VWAP bounce em dias de tendencia, significativamente menor em dias de consolidacao (VWAP flat). O Mudrex lista VWAP em 2025 com 9 estrategias e dicas, incluindo anchor VWAP semanal e mensal para mapear valor de timeframe maior.

Performance real reportada e caveats: o Sharpe 11.32 do QuantPie e real no sentido de que o calculo e os dados sao reais, mas 15 trades nao confirmam persistencia. O erro padrao de uma win rate de 66.7% em 15 trades e grande o suficiente para abranger estrategias fortes e estrategias que tiveram sorte. A leitura honesta: o edge existe em BTC intraday, mas precisa de mais amostra e validacao em outros ativos. O anomiq, com 423 eventos em 8 simbolos, e mais confiavel estatisticamente, e la o exit e o ponto critico.

### Quem ensina e quem vende curso

A area de VWAP e mais pratica e menos academica que momentum. Blogs de trading (coinxsight, cryptoprofitcalc, Mudrex, anomiq) ensinam com regras mecanicas e backtests. Nao ha o fenomeno de venda de curso prometendo retorno garantido como em ICT/SMC. O tom e: VWAP e o benchmark institucional, a reversao e real, mas a calibracao e o exit definem o resultado. Quem trata como magia (entrar em 2 desvios e fechar no VWAP sempre) perde para custos e falsos sinais. Quem calibra a referencia e trabalha o exit tem edge honesto.

### Analise por horario do dia (do manual STRAT-07)

O manual interno prevê diferencas de win rate por sessao que vale validar no backtest:

```
00:00 a 06:00 UTC (Asia):    win rate esperado < 55% (baixo volume)
06:00 a 12:00 UTC (Europe):  win rate esperado > 60%
12:00 a 18:00 UTC (US):      win rate esperado > 65% (melhor janela)
18:00 a 00:00 UTC (close):   win rate esperado > 55%
```

A logica e que a sessao US (12:00 a 18:00 UTC) tem o maior volume e a maior participacao institucional, o que torna o VWAP mais relevante como ancora. A sessao Asia tem volume baixo e o VWAP flat, gerando mais falsos sinais. Para o crypto-correl-bot, filtrar por horario (priorizar US session) deve melhorar o Sharpe.

### Analise por distancia do VWAP

```
1 a 2 desvios:  win rate esperado > 70% (reversion frequente)
2 a 3 desvios:  win rate esperado > 60% (reversion maior, menos frequente)
3+ desvios:     win rate esperado < 50% (anormal, pode ser mudanca de direcao)
```

A leitura pratica: entrar em 1 a 2 desvios tem win rate alto mas R:R baixo (pouco espaco ate o VWAP). Entrar em 2 a 3 desvios tem win rate menor mas R:R maior. Acima de 3 desvios, provavelmente nao e reversion e sim mudanca de direcao real, evitar.

## Ferramentas e APIs disponiveis

### Bibliotecas Python

- `pandas` + `numpy`: calculo direto de VWAP session, rolling e anchored. O manual STRAT-07 ja tem as funcoes `compute_session_vwap`, `compute_rolling_vwap` e `compute_anchored_vwap` prontas.
- `vectorbt`: backtest vetorizado de sinais de VWAP reversion com sweep de entry_std e exit_std.
- `ta` ou `pandas-ta`: algumas tem VWAP embutido, mas implementacao manual e trivial e mais flexivel.

### Dados

- Binance Vision e REST API: klines intradiarios (1m, 5m, 15m) com OHLCV, necessario para VWAP (precisa de volume).
- WebSocket Binance: para VWAP em tempo real, acumular volume desde a abertura da sessao.
- Dados de delta (buy/sell volume): nem sempre disponivel em exchange centralizada. Na Binance, aggTrades tem isBuyerMaker que permite inferir delta. Em DEXes, order flow e direto.

### Plataformas que suportam

- TradingView: VWAP nativo com bandas e anchor por data. Bom para prototipagem visual.
- Binance, Bybit, OKX: execucao intradiaria, VWAP disponivel no chart nativo.
- Hyperliquid, dYdX: perps on-chain com VWAP nos charts.

### Combinacao com outras estrategias do projeto

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Volume Profile (STRAT-05) | Alta | POC e VWAP sao niveis relacionados |
| + Entropy (STRAT-04) | Alta | Entropy filtra dias caoticos |
| + Price Action (STRAT-02) | Media | Candle de confirmacao no VWAP |
| + Mean Reversion Correlacao (STRAT-01) | Media | Mesma filosofia, escalas diferentes |

A combinacao mais natural e com STRAT-05 (Volume Profile): o POC (Point of Control) e o VWAP sao ambos ancoras de valor, e confluencia entre eles e um nivel mais forte. Entropy (STRAT-04) filtra dias de alta entropia onde o VWAP perde relevancia.

## Por que importa para o crypto-correl-bot

Ja temos script: nao. Nao ha `src/strategy/vwap_reversion.py`. So o manual em `docs/strategies/07-vwap-reversion.md` (STRAT-07), que ja tem as funcoes de calculo de VWAP (session, rolling, anchored) e a logica de sinais documentada em pseudocodigo. A implementacao e o proximo passo.

STRAT-07. O que falta:

1. **Implementar `src/strategy/vwap_reversion.py`**: criar a classe `VwapReversionStrategy(BaseStrategy)` seguindo o padrao de `mean_reversion.py` e `momentum.py`. As funcoes de calculo de VWAP do manual podem ser portadas direto.
2. **Calibrar o z-score do VWAP**: o anomiq descobriu que session VWAP resetado a 00:00 UTC deixa o desvio em 2.0 em vez de 1.0. Antes de qualquer backtest, validar que o z-score tem desvio 1.0. Considerar EWMA VWAP por volume-clock que nao reseta.
3. **Exit por trailing em bps, nao so z-score**: o exit tight em z corta ~64% dos vencedores. Implementar stop em bps (35 bps) com trailing que ativa em 20 bps de lucro e da de volta 15 bps do pico, como o anomiq.
4. **Filtro de sessao por horario**: o manual prevê que 12:00 a 18:00 UTC (US) tem win rate esperado > 65%, e 00:00 a 06:00 (Asia) < 55%. Implementar filtro de horario no backtest e na execucao.
5. **Filtro de dias de tendencia**: VWAP reversion falha em dias de tendencia forte (preco nao volta ao VWAP). Filtrar dias em que o VWAP tem inclinacao forte ou o preco nao toca o VWAP ha muitas horas.
6. **Validar por ativo**: o QuantPie mostra que BTC funciona mas ETH, SOL, AVAX falham. Rodar backtest por ativo e so ativar a estrategia onde o edge e confirmado.

### Metricas de avaliacao (target)

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 65%+ | 55% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 8% | < 12% |
| Profit factor | 2.0+ | 1.5 |
| Avg holding period | 30min a 4h | 15min a 8h |
| Trades por mes | 30 a 80 | 15+ |
| Avg R:R | 1.5+ | 1.0 |

### Checklist de proximos passos para STRAT-07

1. Criar `src/strategy/vwap_reversion.py` com `VwapReversionStrategy`.
2. Portar funcoes de VWAP do manual para o modulo.
3. Validar calibracao do z-score (desvio deve ser 1.0).
4. Implementar exit por trailing bps.
5. Adicionar filtro de horario (US session prioritaria).
6. Adicionar filtro de dias de tendencia (VWAP slope).
7. Rodar backtest por ativo, ativar so onde edge confirmado.

## Referencias

- anomiq.io: "Crypto Mean Reversion Backtest: 1 Year of Tick Data", EWMA VWAP z-score, 8 simbolos, 2025, calibracao do session VWAP e exit rework. anomiq.io/blog/mean-reversion-crypto-backtest
- QuantPie: "VWAP Reversion BTC Sharpe 11.32: Is It Real?", Sharpe 11.32, 87.3% anual, max DD 2.1%, 15 trades, 66.7% WR, caveat de amostra fina. trade.medias-ai.cloud.
- coinxsight: "VWAP Trading in Crypto: Institutional Entry Technique", VWAP bounce 60 a 70% WR em dias de tendencia, VWAP breakout. coinxsight.com.
- cryptoprofitcalc: "VWAP Strategy in Crypto: Complete Guide", VWAP mean reversion, bandas std, anchor VWAP semanal/mensal.
- Mudrex: "VWAP in Crypto 2025: 9 Powerful Tips and Strategies". mudrex.com/learn/vwap-in-crypto.
- Manual interno: docs/strategies/07-vwap-reversion.md (STRAT-07)
