# Topico: Momentum e Trend Following

**Data:** 2026-07-15
**Categoria:** Estrategia de Trading

## TL;DR

Momentum e a aposta de que ativos que subiram no passado recente continuam a subir, e os que cairam continuam a cair. Trend following e a versao sistematica: seguir a tendencia com medias moveis, Donchian channels ou breakout de range. Existem duas familias principais: time-series momentum (cada ativo comparado ao seu proprio passado, "subiu, compro") e cross-sectional momentum (ranking de ativos por forca relativa, comprar os mais fortes, vender os mais fracos). Ja implementado em `src/strategy/momentum.py` como STRAT-06, com RSI, EMA crossover e ADX como confirmacao e filtro de regime. Pesquisas de 2025 e 2026 mostram que time-series momentum e superior em cripto, com retorno anual de ~32% e Sharpe acima de 1.5 em ensemble de Donchian. O caveat principal: momentum em cripto sofre crashes severos e a variancia pode ser infinita (power law), o que torna vol-management obrigatorio.

## Explicacao para criancas

Imagine um trem andando nos trilhos. Se ele esta acelerando para frente, provavelmente vai continuar para frente por um tempo. Voce nao tenta adivinhar quando ele vai parar, voce entra no trem enquanto ele acelera e sai quando ele comeca a frear. Momentum em trading e isso: procurar os ativos que estao subindo mais rapido e entrar junto, mantendo a posicao enquanto a tendencia durar. A saida e quando a tendencia mostra sinais de fraqueza (media rapida cruza a lenta, ou o preco rompe o canal para baixo).

## Como funciona tecnicamente

### Time-series vs Cross-sectional momentum

Time-series momentum (TSMOM): avalia cada ativo contra o seu proprio retorno passado. Se o retorno sobre a janela de formacao e positivo, entra long. Se negativo, entra short. Cada ativo e independente. Esta e a familia que o `src/strategy/momentum.py` implementa (retorno sobre `formation_period` > 0 confirma bullish momentum).

Cross-sectional momentum (XSMOM): ranqueia todos os ativos por forca relativa e abre long nos mais fortes e short nos mais fracos. Nao importa se o mercado inteiro esta subindo ou caindo, importa o ranking relativo. Em cripto, a alta correlacao entre as moedas prejudica o XSMOM porque os ativos se movem juntos e o spread relativo e pequeno.

A evidencia de 2026 (doi:10.15388/batp.2026.1) com 8 criptos de 2020 a 2025, usando EMA multi-horizonte com normalizacao por volatilidade, mostra que TSMOM entrega retorno anual de 31.96% e supera XSMOM em base risco-ajustada. XSMOM tem max drawdown de 55% e menor rentabilidade, em parte pela alta correlacao entre criptos. Conclusao pratica: para o crypto-correl-bot, priorizar TSMOM.

### Indicadores usados na implementacao (STRAT-06)

O `src/strategy/momentum.py` combina tres confirmacoes mais um gate:

1. **Momentum bruto**: retorno sobre `formation_period` (default 90). Positivo confirma bullish, negativo confirma bearish.
2. **RSI**: acima de 50 confirma forca de alta. Em momentum, RSI alto confirma forca (nao e motivo para pular, ao contrario de mean reversion). So pula extremos (>95 ou <5).
3. **EMA crossover**: `ema_fast` (20) acima de `ema_slow` (50) confirma direcao da tendencia.
4. **ADX** (gate, nao confirmacao): ADX >= 25 confirma que a tendencia e forte. Sem ADX, momentum em mercado fraco gera whipsaw.

Entrada exige `min_confirmation >= 2` de 3 indicadores e ADX acima do limiar. Isso reduz sinais falsos em consolidacao.

### MACD e Donchian (variantes classicas)

MACD: `ema_fast(12) - ema_slow(26)`, com signal line `ema(9)`. Cruzamento do MACD acima da signal line e bullish. O `src/strategy/momentum.py` tem `compute_macd` implementado mas nao usado no sinal principal (so RSI, EMA e momentum bruto). Pode ser adicionado como confirmacao adicional.

Donchian channel: maximo e minimo de N periodos. Entrada long quando o preco rompe a maxima de N periodos (Donchian upper). Saida quando rompe a minima de N periodos (Donchian lower). Este e o metodo do paper Concretum Research, que usa ensemble de varios Donchian com lookbacks diferentes agregados num sinal so.

### Regras de entrada (LONG)

```
CONDICOES:
1. retorno sobre formation_period > 0 (momentum positivo)
2. RSI > 50 (forca de alta)
3. ema_fast > ema_slow (tendencia de alta)
4. ADX >= 25 (tendencia forte)
5. min 2 de 3 confirmacoes (1, 2, 3) + ADX ok

ENTRY: Long
STOP: entry_price - 3 * ATR (trailing, sobe com o preco)
TARGET: entry_price + 2 * stop_distance
```

### Regras de entrada (SHORT)

Simetrico: retorno negativo, RSI < 50, ema_fast < ema_slow, ADX >= 25, stop acima + 3 ATR, target abaixo.

### Stop, take profit e gestao de risco

Stop inicial: `entry_price - atr_trailing_mult * ATR` (default 3x ATR). O `update_trailing_stop` move o stop a favor da tendencia: para long, o stop so sobe (nunca desce). Para short, o stop so desce. Isso captura a tendencia e protege lucro.

Take profit: `entry + 2 * stop_distance`, ou saida por trailing stop quando a tendencia reverter.

Filtro de regime: so opera em `Regime.TRENDING` (Hurst > 0.55). Se o regime for mean-reverting, o momentum nao opera (e a vez de STRAT-01). Se ambiguo, opera com tamanho reduzido.

### Timeframe e expected performance

Timeframe ideal: 1d para formacao, 4h para entrada. Horizonte de dias a semanas (deixar a tendencia correr).
Targets documentados: Sharpe 1.5+, max drawdown < 20%, win rate 35 a 45% (trend following tem win rate baixo, compensado por R:R alto, tipicamente 2:1 a 4:1).
Performance real reportada em 2026: Concretum Research, ensemble de Donchian em portfolio rotacional das top 20 criptos mais liquidas desde 2015, Sharpe acima de 1.5 e alpha anualizado de 10.8% vs BTC, liquido de taxas. TSMOM com EMA multi-horizonte (doi:10.15388/batp.2026.1): 31.96% retorno anual, superior a XSMOM.

### Tabela de parametros (config `MomentumConfig`)

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `formation_period` | 90 | 30 a 180 | Janela de momentum (retorno passado) |
| `rsi_period` | 14 | 10 a 20 | Periodo do RSI |
| `rsi_trend_level` | 50 | 45 a 55 | Nivel de RSI para confirmar tendencia |
| `rsi_overbought` | 95 | 90 a 99 | Skip apenas extremos |
| `rsi_oversold` | 5 | 1 a 10 | Skip apenas extremos |
| `ema_fast` | 20 | 10 a 30 | EMA rapida |
| `ema_slow` | 50 | 40 a 100 | EMA lenta |
| `adx_period` | 14 | 10 a 20 | Periodo do ADX |
| `adx_threshold` | 25 | 20 a 30 | ADX minimo para confirmar tendencia forte |
| `atr_period` | 14 | 10 a 20 | Periodo do ATR |
| `atr_trailing_mult` | 3.0 | 2.0 a 4.0 | Multiplicador de ATR para stop |
| `min_confirmation` | 2 | 1 a 3 | Min de 3 indicadores confirmando |

### Exemplo numerico

Cenario: BTC a $90,000. formation_period = 90 dias. BTC estava a $75,000 ha 90 dias, retorno = +20% (momentum positivo, confirmacao 1 ok). RSI = 62 (acima de 50, confirmacao 2 ok). EMA20 = $88,000, EMA50 = $85,000, EMA20 > EMA50 (confirmacao 3 ok). ADX = 31 (acima de 25, gate ok). ATR(14) = $2,500. Entrada long a $90,000 com 3 confirmacoes (confianca = 3/3 = 1.0). Stop inicial = $90,000 - 3 * $2,500 = $82,500. Target = $90,000 + 2 * $7,500 = $105,000. R:R = 2:1. Se BTC sobe para $100,000, o trailing stop sobe para $100,000 - $2,800 (ATR novo) = $97,200, protegendo $7,200 de lucro. Se BTC cai para $97,200, sai com lucro, nao espera voltar a $82,500.

### Vantagens e desvantagens

Vantagens: captura tendencias longas (o maior edge em cripto, mercados que trends forte), R:R alto (2:1 a 4:1), poucos trades (baixo custo), validado academicamente com datasets survivorship-free, funciona em multi-asset (rotacao para os mais fortes).

Desvantagens: win rate baixo (35 a 45%), sofre whipsaw em consolidacao (por isso filtro de regime e obrigatorio), crashes severos em reversao brusca de tendencia, variancia pode ser infinita (power law), atraso em entrada e saida (indicadores sao lagging), em cripto small-caps o momentum nao e robusto.

### Metricas de avaliacao (target)

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Sharpe ratio | 1.5+ | 1.0 |
| Sortino ratio | 2.0+ | 1.5 |
| Max drawdown | < 20% | < 30% |
| Win rate | 35 a 45% | 30% |
| Avg R:R | 2.5:1+ | 1.5:1 |
| Profit factor | 1.5+ | 1.2 |
| Trades por mes | 3 a 10 | 2+ |
| Calmar ratio | 0.8+ | 0.5 |

## Estado do mercado em 2026

Momentum e trend following seguem como as estrategias mais documentadas e validadas em cripto em 2026. O paper Concretum Research (versao abril 2025) e a referencia mais robusta: aplica metodologia classica de trend following (ensemble de Donchian channels com lookbacks diferentes) a BTC e depois a um dataset survivorship bias-free de todas as criptos desde 2015. O modelo, em portfolio rotacional das top 20 mais liquidas com position sizing por volatilidade, atingiu Sharpe acima de 1.5 e alpha de 10.8% anualizado vs BTC, liquido de taxas. O paper tambem propoe uma tecnica de portfolio para mitigar custos de transacao, o que e critico em cripto.

Quem pesquisa e bot: o repositorio PThrower/UnconBacktest_TS-Momentum-in-Cryptocurrencies faz backtest de TSMOM em BTC, ETH, ADA, BNB desde 2016, com sinal de momentum via z-score de returns de 10 dias contra baseline de 365 dias, pesos clipados por tanh e analise de Sharpe. Os resultados mostram Sharpe positivo em todas as 4 moedas e returns do strategy nao correlacionados com returns passivos, o que indica que captura timing direcional, nao so exposicao.

O estudo comparativo de 2026 (doi:10.15388/batp.2026.1) e o mais direto para a decisao TSMOM vs XSMOM: 8 criptos, 2020 a 2025, EMA multi-horizonte com normalizacao de volatilidade. TSMOM: 31.96% retorno anual, melhor risco-ajustado. XSMOM: max drawdown de 55%, menor rentabilidade, por causa da alta correlacao entre criptos que comprime o spread relativo.

Quem ensina: a area e predominantemente academica e quant. O blog QuantifiedStrategies avalia se momentum em cripto supera entry aleatorio e conclui que sim, mas com caveats: o edge existe em condicoes especificas, depende muito do design de parametros e precisa sobreviver validacao out-of-sample. O blog PyQuantLab no Medium mostra um framework avancado com filtro de regime (BTC acima da MA50), selecao por momentum risco-ajustado, weighting por volatilidade inversa e stop-loss semanal.

Performance real e caveats criticos: o paper Springer "Cryptocurrency momentum has (not) its moments" (doi:10.1007/s11408-025-00474-9) alerta que momentum em cripto sofre crashes severos. Em dezembro de 2020, momentum crashou -255%. Mesmo uma unica cripto pode tornar o portfolio de momentum insignificante. A solucao, alinhada com a literatura de equities, e vol-management: escalar o tamanho por volatilidade inversa mitiga os crashes. Outro paper (doi:10.1002/ijfe.70036) mostra que as variancias realizadas de momentum em cripto seguem power laws com alfa < 2, o que implica que a variancia populacional teorica e infinita. Conclusao pratica: Sharpe baseado em variancia pode nao ser informativo, e vol-management e obrigatorio, nao opcional.

A recomendacao concreta de 2026: momentum em cripto e um fenomeno associado a large-caps. Small-caps sem liquidez nao apresentam momentum robusto. Para o crypto-correl-bot, limitar o universo a ativos liquidos (top 20 a 30) e aplicar vol-target.

### Risk-managed momentum

O paper "Cryptocurrency market risk-managed momentum strategies" (doi:10.1016/j.frl.2025.107879) estende a analise de Han, Kang e Ryu (SSRN 4675565) e aplica gestao de risco ao momentum em cripto. A ideia central, herdada da literatura de equities (Barroso e Santa-Clara 2014, Daniel e Moskowitz 2016), e que o momentum tem retornos positivos mas com caudas pesadas, e que escalonar o tamanho por volatilidade realizada reduz os crashes sem destruir o retorno medio. Esse paper reforca a conclusao do Springer: vol-management nao e opcional em cripto, e obrigatorio. Para o `src/strategy/momentum.py`, isso significa adicionar `size = target_vol / realized_vol` no position sizing, ao inves de usar so a confianca por confirmacoes.

### Rotacao entre TSMOM e mean reversion por regime

A descoberta mais pratica para o bot e que TSMOM e mean reversion (STRAT-01) sao complementares por construcao. TSMOM opera em regime trending (Hurst > 0.55), mean reversion opera em regime mean-reverting (Hurst < 0.45). Ambos compartilham o mesmo `RegimeFilter` no projeto. O bot pode rodar as duas estrategias simultaneamente e o filtro de regime decide qual atua em cada ativo. Isso evita o erro de forcar uma unica filosofia em todos os regimes.

### Quem ensina e quem vende curso

A area de momentum e trend following e mais academica do que de curso. Os papers citados (Concretum, Springer, SSRN) sao pesquisa rigorosa com datasets survivorship-free. Blogs quant (QuantifiedStrategies, PyQuantLab) explicam com codigo e reportam resultados honestos. Nao ha o fenomeno de venda de curso prometendo retornos que se ve em ICT/SMC. O tom e: o edge existe, mas e instavel, sofre crashes, e precisa de vol-management e validacao OOS.

### Donchian channel: o metodo classico de trend following

O Concretum Research usa ensemble de Donchian channels, que merece explicacao detalhada porque e a base do paper com Sharpe > 1.5. O Donchian channel de N periodos e simples: upper = max(high, N), lower = min(low, N). Entrada long quando o preco rompe o upper, saida quando rompe o lower. O segredo do Concretum e agregar varios Donchian com lookbacks diferentes (ex: 20, 50, 100, 200 dias) num sinal so. Cada lookback captura uma escala de tendencia diferente. O ensemble suaviza o whipsaw que um Donchian so sofre em consolidacao. Para o `src/strategy/momentum.py`, que hoje usa EMA crossover, o Donchian ensemble e uma variante a testar e comparar em OOS.

### Por que vol-management e obrigatorio em cripto

O paper Springer (doi:10.1007/s11408-025-00474-9) e o paper de risk-managed momentum (doi:10.1016/j.frl.2025.107879) convergem na mesma conclusao: momentum em cripto tem caudas pesadas e crashes severos (-255% em dezembro de 2020), e escalonar o tamanho por volatilidade inversa reduz os crashes sem destruir o retorno medio. A implementacao pratica e `size = target_vol / realized_vol`, onde `target_vol` e a volatilidade anual alvo do portfolio (ex: 20%) e `realized_vol` e a volatilidade realizada do ativo (ATR anualizada ou desvio dos returns). Em alta vol, o tamanho reduz automaticamente. Em baixa vol, o tamanho aumenta. Isso e diferente do sizing por confianca (confirmacoes / 3) que o `src/strategy/momentum.py` usa hoje, que nao escalona por vol.

## Ferramentas e APIs disponiveis

### Bibliotecas Python

- `pandas-ta` ou `ta`: calculo de RSI, MACD, ADX, ATR, EMA, Donchian channels. Pronto para uso.
- `vectorbt`: backtest vetorizado para sweeps de parametros de medias moveis e Donchian (ja escolhido no projeto).
- `numpy` + `pandas`: implementacao manual dos indicadores (o `src/strategy/momentum.py` ja implementa RSI, MACD, ADX e ATR do zero).
- `backtrader`: alternativa mais realista para validacao final, com slippage e commission modelados.

### Dados

- Binance Vision (klines historicos diarios e intradiarios, gratis).
- CoinGecko API para market cap e volume (filtrar universo por liquidez).
- Funding rate via `GET /fapi/v1/fundingRate` para modelar custo de shorts em momentum bearish.

### Plataformas que suportam

- Binance, Bybit, OKX: spot e perp para execucao long e short.
- Hyperliquid: perps on-chain, boa para alavancagem em trend following.
- TradingView: backtest rapido de Donchian e EMA crossover para prototipagem visual.

### Combinacao com outras estrategias do projeto

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Mean Reversion (STRAT-01) | Alta em regime | Momentum opera em trending, mean reversion em lateral, alternando por filtro de regime |
| + Entropy (STRAT-04) | Alta | Entropy detecta transicao de regime, liga/desliga momentum |
| + Funding (STRAT-08) | Media | Funding extremo sinaliza fim de tendencia |
| + Price Action (STRAT-02) | Media | Breakout de Donchian e price action, mesmo conceito |

A combinacao mais poderosa e momentum + filtro de regime (Hurst/Entropy). O bot so roda momentum em trending e so roda mean reversion em lateral, alternando automaticamente. Isso evita o erro classico de rodar momentum em consolidacao (whipsaw) e mean reversion em trending (divergencia continua).

## Por que importa para o crypto-correl-bot

Ja temos script: sim, `src/strategy/momentum.py`, classe `MomentumStrategy`, STRAT-06. O modulo implementa TSMOM (retorno sobre formation_period), com 3 confirmacoes (momentum, RSI, EMA crossover) e gate de ADX >= 25. Tem `compute_rsi`, `compute_macd`, `compute_adx`, `compute_atr` implementados do zero. Trailing stop por ATR via `update_trailing_stop`. Filtro de regime via `RegimeFilter` (so opera em TRENDING).

O que falta:

1. **Vol-management (position sizing por volatilidade inversa)**: o paper Springer mostra que crashes de momentum em cripto sao severos (-255% em dezembro de 2020) e que vol-management mitiga. Hoje o sizing e por confianca (confirmacoes / 3) * size_mult de regime. Adicionar scaling por `1 / volatility` (ATP ou desvio dos returns) para reduzir tamanho em alta vol.
2. **Ensemble de Donchian**: o Concretum Research usa ensemble de varios Donchian com lookbacks diferentes agregados num sinal. Hoje o codigo usa EMA crossover. Testar adicionar Donchian como alternativa e comparar Sharpe OOS.
3. **Usar MACD como confirmacao**: `compute_macd` ja existe mas nao entra no sinal. Avaliar se adicionar cruzamento MACD/signal como 4a confirmacao melhora a qualidade.
4. **Limite de universo por liquidez (large-caps)**: a evidencia diz que momentum e fenomeno de large-caps. Garantir que o universo do bot filtra por volume e market cap (top 20 a 30), nao inclui small-caps iliquidas.
5. **Stop por tempo**: trend following pode ficar preso em tendencia que nao vai a lugar nenhum. Adicionar saida por tempo maximo de posicao (ex: 30 dias) se o trailing stop nao disparar.
6. **Custo de transacao no backtest**: trend following tem poucos trades mas cada um move tamanho grande. Garantir que o backtest modela slippage e commission realistas, nao so fee fixo.
7. **Reportar metricas robustas a variancia infinita**: o paper doi:10.1002/ijfe.70036 diz que Sharpe pode nao ser informativo em cripto por variancia power-law. Complementar Sharpe com Sortino, Calmar e max drawdown absoluto.

### Checklist de proximos passos para STRAT-06

1. Implementar vol-target (size = target_vol / asset_vol) no position sizing.
2. Adicionar Donchian ensemble como variante e comparar com EMA crossover em OOS.
3. Incluir MACD/signal crossover como confirmacao opcional.
4. Filtrar universo por liquidez (top 20 a 30 por volume).
5. Adicionar saida por tempo maximo (30 dias).
6. Modelar slippage realista no backtest (Nao so fee).
7. Reportar Sortino, Calmar e max drawdown junto com Sharpe.

### Sinergia com portfolio delta-neutral

Alem do filtro de regime que alterna com mean reversion, o momentum se beneficia de uma base delta-neutral (ver pesquisa delta-neutral-estrategias). O portfolio pode alocar 50% para funding arb (STRAT-08, yield estavel 10 a 20% a.a., baixa vol) e 50% para momentum (retorno potencial 30% a.a., alta vol). A base delta-neutral reduz a volatilidade total do portfolio e protege o capital em periodos de crash de momentum (como dezembro de 2020, -255%). Sem essa base, um portfolio so momentum absorve o impacto completo dos crashes. Com a base, o drawdown do portfolio e significativamente menor. Essa combinacao e o que instituicoes fazem e o que o bot pode replicar com as estrategias ja planejadas.

## Referencias

- Concretum Research: "Catching Crypto Trends" (2025), ensemble de Donchian, Sharpe > 1.5, alpha 10.8% vs BTC, liquido de taxas, dataset survivorship-free desde 2015. concretumgroup.com (PDF).
- doi:10.15388/batp.2026.1: "Momentum Trading in Cryptocurrencies: A Comparative Study of Time-Series and Cross-Sectional Strategies", 8 criptos, 2020 a 2025, TSMOM 31.96% anual, XSMOM max DD 55%.
- doi:10.1007/s11408-025-00474-9: "Cryptocurrency momentum has (not) its moments", Springer, momentum sofre crashes severos (-255% em dez/2020), vol-management util, fenomeno de large-caps.
- doi:10.1002/ijfe.70036: "Cryptocurrency Momentum: Is It an Illusion?", variancia realizada segue power law alfa < 2, variancia populacional infinita, Sharpe pode nao ser informativo.
- QuantifiedStrategies: "Can Backtested Momentum Strategies Outperform Random Entry in Crypto?", edge existe mas com caveats e precisa OOS. quantifiedstrategies.com.
- PyQuantLab (Medium): regime-filtered momentum, BTC MA50 como filtro, inverse vol weighting, stop-loss semanal.
- PThrower/UnconBacktest_TS-Momentum-in-Cryptocurrencies: backtest TSMOM em BTC/ETH/ADA/BNB, z-score de 10 dias, tanh clipping, Sharpe positivo. github.com/PThrower.
- Manual interno: docs/strategies/06-momentum-trend-following.md (STRAT-06)
- Implementacao: src/strategy/momentum.py
