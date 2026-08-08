# Topico: Delta-Neutral (Estrategias Gerais)

**Data:** 2026-07-15
**Categoria:** Estrategia de Trading

## TL;DR

Delta-neutral e a familia de estrategias que zera a exposicao direcional ao preco (delta = 0) e lucra de outras fontes: funding rates, basis spread, time decay (theta) ou volatilidade (vega). O funding rate arbitrage (STRAT-08) e o subtipo mais pratico em cripto. Esta pesquisa cobre a familia geral: spot-futures arb, perp-perp arb, basis trading com futuros datados, gamma scalping com opcoes, e como combinar delta-neutral com estrategias direcionais para reduzir a volatilidade do portfolio. Nao ha script dedicado em `src/strategy/` alem do que STRAT-08 tera. O valor principal para o crypto-correl-bot e usar delta-neutral como base estavel do portfolio (yield 5 a 30% a.a. com baixa vol) ao lado das estrategias direcionais (momentum, mean reversion, price action) que tem retorno potencial maior mas volatilidade maior. Instituicoes usam delta-neutral porque Bitcoin historicamente tem drawdowns peak-to-trough acima de 70%, e um fundo market-neutral busca returns consistentes de baixa volatilidade que nao dependem de ciclo de alta.

## Explicacao para criancas

Imagine que voce tem duas bandeiras, uma vermelha e uma azul, e esta num barco no meio do mar. O mar sobe e desce (o preco do BTC sobe e cai). Se voce segura uma bandeira vermelha que te faz ganhar quando o mar sobe e uma azul que te faz ganhar quando o mar desce, no fim o mar nao importa: voce ganha das duas bandeiras de outras formas (um amigo te paga um trocado todo dia por segurar as bandeiras). Em cripto, segurar spot (ganha se sobe) e short perp (ganha se desce) cancela o movimento do mar, e o "trocado diario" e o funding rate. Delta-neutral e isso: zerar o impacto do movimento do preco e lucrar de outras fontes.

## Como funciona tecnicamente

### O que e delta

Delta mede quanto o valor de uma posicao muda para cada $1 de movimento no ativo subjacente. Delta +1: ganha $1 a cada $1 de alta. Delta -1: ganha $1 a cada $1 de baixa. Delta 0: o valor da posicao nao muda com o preco. Um portfolio delta-neutral tem soma de deltas = 0.

### Fontes de retorno em delta-neutral

Quando o P&L direcional e zero, o lucro vem de:
1. **Funding rates** (perpetual futures): longs pagam shorts (ou vice-versa) a cada intervalo.
2. **Basis spread** (futuros datados): futuro acima do spot converge a zero no vencimento.
3. **Theta** (opcoes): decaimento de tempo, vender opcoes coleta premium.
4. **Vega** (opcoes): volatilidade, straddles longos lucram de movimentos grandes.
5. **Volatility mismatch** (gamma scalping): hedge continuo de opcoes para capturar gamma.

### Estrategia A: Spot-Futures Arbitrage (Cash and Carry)

O subtipo mais pratico e o que STRAT-08 documenta em detalhe.

```
Setup:
1. Comprar 1 BTC no spot a $95,000
2. Vender 1 BTC no perp a $95,000 (mesmo nocional)
3. Delta = 0 (spot ganha, short perp perde, liquido zero)
4. A cada 8h, se funding positivo, recebe pagamento

Yield = funding rate annualizado (5 a 30% a.a. tipico)
Riscos: rate flip, basis risk, execution cost, liquidation na perna perp
```

### Estrategia B: Basis Trading (Futuros Datados)

Variante com futuros datados em vez de perp. Yield vem do basis (premium do futuro sobre spot) que converge a zero no vencimento.

```
Setup:
1. Comprar 1 BTC no spot a $60,000
2. Vender 1 BTC no futuro trimestral a $63,000 (premium de 5%)
3. Delta = 0
4. No vencimento, futuro settle em spot, captura os $3,000 de spread

Yield = 5% em 3 meses = ~20% a.a. (independente do que BTC fizer)
Vantagem: yield travado no momento da entrada, nao depende de funding flutuante
Desvantagem: data fixa de fim, menos flexivel que perp
```

### Estrategia C: Perp-Perp Arbitrage

Short perp na exchange com funding mais alto, long perp na exchange com funding mais baixo. Captura o diferencial entre exchanges.

```
Setup:
1. Short 1 BTC perp na Exchange A (funding 0.03% por 8h)
2. Long 1 BTC perp na Exchange B (funding 0.005% por 8h)
3. Delta = 0 (as duas pernas se cancelam)
4. Recebe 0.03% - 0.005% = 0.025% por 8h de diferencial

Vantagem: nao precisa de spot, usa so perps
Desvantagem: basis risk cruzado entre exchanges, risco de transferencia, duas margin accounts
```

### Estrategia D: Gamma Scalping (Opcoes)

Estrategia com opcoes, mais complexa e tipicamente institucional. Long de um straddle (call + put no mesmo strike) deixa o portfolio delta-neutral inicialmente. Quando o preco se move, o delta escorrega (gamma), e o trader re-hedgeia vendendo/comprando spot para voltar a delta 0. Cada re-hedge captura gamma (compra barato, vende caro na volatilidade realizada).

```
Setup:
1. Comprar 1 ATM call + 1 ATM put (straddle long, delta inicial ~0)
2. Preco se move, delta escorrega (gamma)
3. Re-hedge: comprar/vender spot para voltar a delta 0
4. Repetir a cada movimento significativo

Lucro: gamma (volatilidade realizada > volatilidade implicita)
Prejuizo: theta (decaimento de tempo) se a vol realizada nao cobrir o theta
```

O NYXANCE glossary descreve straddles e strangles como long gamma (lucram de movimentos grandes em qualquer direcao) e iron condors como short gamma (lucram de baixa volatilidade). Gamma scalping e o hedge continuo do long gamma. Em cripto, opcoes existem na Deribit e em algumas DEXes (Lyra, Hegic), mas sao menos liquidas que perps.

### Combinacao com estrategias direcionais

O valor principal para o portfolio e combinar delta-neutral (base estavel) com direcionais (momentum, mean reversion, price action). Bitcoin historicamente tem drawdowns peak-to-trough acima de 70% em bear markets. Um portfolio so direcional absorve o impacto completo. Um portfolio com 50% delta-neutral (yield 10 a 20% a.a., baixa vol) e 50% direcional (retorno potencial 30 a 100% a.a., alta vol) tem volatilidade total menor sem sacrificar muito o retorno.

```
Portfolio exemplo:
- 50% em funding arb (STRAT-08): 15% a.a., vol 5%, Sharpe ~3
- 25% em momentum (STRAT-06): 30% a.a., vol 40%, Sharpe ~0.75
- 25% em mean reversion (STRAT-01): 20% a.a., vol 15%, Sharpe ~1.3

Retorno esperado: 0.5*15 + 0.25*30 + 0.25*20 = 7.5 + 7.5 + 5 = 20% a.a.
Volatilidade esperada (aproximada, assumindo baixa correlacao): ~12-15%
Sharpe do portfolio: ~1.3 a 1.7
```

Compare com portfolio 100% direcional: retorno 30%, vol 40%, Sharpe 0.75. O portfolio com base delta-neutral tem retorno menor mas Sharpe muito maior (menor vol, drawdown menor). Para instituicoes que nao aceitam drawdown de 70%, delta-neutral e a porta de entrada.

### Gestao de risco em delta-neutral

1. **Rebalanceamento de delta**: o tamanho das pernas muda com o preco, e preciso re-hedgear para manter delta 0. Definir threshold (ex: delta > 5% do nocional dispara rebalance).
2. **Margem separada na perna derivativa**: perp e futuro exigem margin. Manter buffer (2x a 3x) para evitar liquidation.
3. **Monitor de rate flip / basis**: funding ou basis vira contra, precisa sair ou inverter.
4. **Execution cost modelado**: 2 trades de abertura + 2 de fechamento + rebalance. Em yield baixo, fees comem o edge.
5. **Diversificacao entre ativos**: nao depender de um so funding/basis. BTC, ETH, SOL tem perfis diferentes.

### Timeframe e expected performance

Timeframe: dias a semanas (carry), ou continuo (gamma scalping).
Yield esperado: 5 a 30% a.a. em funding/basis. Gamma scalping depende de vol realizada vs implicita (variavel).
Sharpe: alto (2 a 4+) porque risco direcional e zero.
Drawdown: baixo se bem gerenciado, mas rate flip e basis shock podem corroer.

### Tabela de sub-estrategias

| Sub-estrategia | Fonte de retorno | Complexidade | Yield tipico | STRAT relacionado |
|----------------|------------------|--------------|--------------|-------------------|
| Spot + short perp | Funding rate | Media | 5 a 30% a.a. | STRAT-08 |
| Spot + short futuro datado | Basis spread | Media | 10 a 25% a.a. | novo |
| Perp A vs Perp B | Diferencial funding | Alta | 5 a 15% a.a. | novo |
| Gamma scalping | Vol realizada vs implicita | Muito alta | variavel | novo (opcoes) |
| Short iron condor | Theta (baixa vol) | Alta | variavel | novo (opcoes) |

### Exemplo numerico (basis trading)

Cenario: BTC spot $60,000. Futuro trimestral (3 meses) $63,000 (premium de 5%). Comprar 1 BTC spot, vender 1 BTC futuro. Delta 0. No vencimento em 3 meses, futuro settle em spot (seja qual for o preco). Se BTC esta em $70,000: spot ganha $10,000, futuro perde $7,000 (vendeu a $63,000, settle a $70,000), liquido +$3,000. Se BTC esta em $50,000: spot perde $10,000, futuro ganha $13,000 (vendeu a $63,000, settle a $50,000), liquido +$3,000. Os $3,000 sao travados na entrada, independente do preco. Yield = $3,000 / $60,000 = 5% em 3 meses = ~20% a.a.

## Estado do mercado em 2026

Delta-neutral em cripto em 2026 e predominantemente institucional e crescente. O SparkCore descreve a adocao crescente por gestores quant de cripto globalmente: para instituicoes que reconhecem o potencial de longo prazo de digitais mas nao aceitam exposicao direcional descoberta, market-neutral e a porta de entrada. A motivacao e direta: Bitcoin tem drawdowns peak-to-trough acima de 70% em bear markets, e um fundo market-neutral busca returns consistentes de baixa volatilidade que nao dependem de ciclo de alta.

Quem pesquisa e ensina: BackQuant chama basis trade de "a estrategia delta-neutral mais simples em cripto, e a que a maioria dos desks institucionais roda silenciosamente em background". O Coin Frontier descreve as fontes de retorno (funding, basis, theta, vega) e as estrategias A a D com clareza. O NYXANCE glossary cobre straddles, strangles, iron condors e gamma scalping, notando que opcoes em cripto sao mais complexas e tipicamente institucionais, embora protocolos de opcoes (Deribit, Lyra, Hegic) tornem acessivel a retail. O Altrady explica que delta-neutral isola fontes de renda enquanto remove o "chute" direcional aleatorio.

Quem vende curso: a area de delta-neutral e mais institucional e menos de curso que ICT/SMC. Exchanges (Kraken, Binance) e blogs quant (BackQuant, Coin Frontier, NYXANCE, Altrady) explicam com tom honesto. Nao ha promessa de retorno garantido. O tom e: o yield e real e estavel, mas tem modos de falha (rate flip, basis shock, liquidation), e o tradeoff e teto de retorno menor vs drawdown muito menor.

Performance real reportada: funding rate arb (STRAT-08) tem ranges de 5 a 30% a.a. dependendo do ativo e regime. Basis trading com futuros datados trava o yield na entrada (10 a 25% a.a. tipico em premium normal). Gamma scalping e variavel, depende de vol realizada vs implicita. Em bull markets, funding positivo alto favorece spot + short perp. Em bear markets, funding negativo exige inverter (short spot + long perp) ou ficar de fora.

### Por que delta-neutral importa em 2026

O ponto chave de 2026 e que o mercado cripto amadureceu o suficiente para que desks institucionais rodem delta-neutral em escala, e que retail com APIs (Binance, Bybit, OKX, Hyperliquid) consegue acessar os mesmos instruments. A barreira nao e mais acesso, e execucao: rebalanceamento automatico, monitor de rate flip, gestao de margem. Quem automatiza (Button.xyz defende um agente para o trabalho mecanico) escala o edge. Quem faz manual perde para custos e timing.

## Ferramentas e APIs disponiveis

### APIs

- Binance: `GET /fapi/v1/fundingRate` (funding history), `GET /fapi/v1/fundingInfo` (intervalo variavel), futures datados via `GET /fapi/v1/exchangeInfo`. Spot via `api/v3`.
- Bybit, OKX: endpoints equivalentes para funding, futures datados e execucao.
- Deribit: opcoes de BTC e ETH, com API para pricing de gregas.
- Hyperliquid, dYdX: perps on-chain com funding volatil.

### Bibliotecas Python

- `ccxt`: abstracao unificada para spot + futures + opcoes em multiplas exchanges. Essencial para perp-perp arb e basis trading cruzado.
- `python-binance`: SDK oficial para Binance spot e futures.
- `pandas`: para calcular APY rolling, basis, persistence de funding.
- `py_vollib` ou `mibian`: pricing de opcoes e gregas para gamma scalping (se implementar a variante com opcoes).

### Plataformas que suportam

- Binance, Bybit, OKX: spot + perp + futuros datados na mesma exchange, facilita hedge e reduz risco de transferencia.
- Deribit: opcoes de BTC/ETH para gamma scalping e iron condors.
- Hyperliquid: perps on-chain para perp-perp arb com funding volatil.

### Combinacao com outras estrategias do projeto

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Funding Arb (STRAT-08) | Alta | Funding arb e o subtipo principal de delta-neutral |
| + Momentum (STRAT-06) | Alta | Base estavel + direcional, reduz vol do portfolio |
| + Mean Reversion (STRAT-01) | Alta | Mesma logica, base estavel + direcional |
| + Price Action (STRAT-02) | Media | Base estavel + direcional de breakout |

A combinacao mais poderosa para o portfolio e a alocacao entre base delta-neutral (50%) e estrategias direcionais (50%). Isso reduz a volatilidade total sem sacrificar muito o retorno, e e o que instituicoes fazem.

## Por que importa para o crypto-correl-bot

Ja temos script: parcial. O funding rate arbitrage (STRAT-08) tera `src/strategy/funding_arb.py` (ver pesquisa dedicada). Esta pesquisa cobre a familia geral, incluindo variantes nao implementadas (basis trading com futuros datados, perp-perp arb, gamma scalping).

O que falta (alem de STRAT-08):

1. **Basis trading com futuros datados**: implementar `src/strategy/basis_trade.py` que compra spot e vende futuro trimestral, capturando o premium no vencimento. Yield travado na entrada, menos volatil que funding arb. Dados: futures datados via `GET /fapi/v1/exchangeInfo`.
2. **Perp-perp arbitrage**: implementar `src/strategy/perp_perp_arb.py` que monitora diferencial de funding entre exchanges e entra quando o spread justifica. Mais complexo (duas margin accounts, basis cruzado) mas nao precisa de spot.
3. **Portfolio allocator delta-neutral + direcional**: implementar a alocacao entre base delta-neutral (50%) e direcionais (50%) no `src/bot/risk_manager.py`. O gestor de risco decide quanto capital vai para cada estrategia baseado em vol target e correlacao entre elas.
4. **Gamma scalping (futuro)**: opcoes em cripto (Deribit) sao menos liquidas mas podem ser exploradas. Prioridade baixa no curto prazo, mas documentar como roadmap.
5. **Monitor de rate flip e basis shock**: no `risk_manager`, alerta quando funding vira negativo por N ciclos ou basis diverge de X%, e pausa ou inverte as pernas delta-neutral.

### Metricas de avaliacao (target para a base delta-neutral)

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| APY | 10%+ | 5% |
| Sharpe ratio | 2.0+ | 1.5 |
| Max drawdown | < 5% | < 10% |
| Tempo em mercado | 70%+ | 50% |
| Correlacao com BTC | < 0.2 | < 0.4 |

A correlacao com BTC deve ser baixa (idealmente proxima de 0) porque o ponto e justamente nao ter exposicao direcional.

### Vantagens e desvantagens

Vantagens: funciona em qualquer regime (P&L direcional zero), yield estavel e previsivel, baixa volatilidade, base institucional, complementa direcionais reduzindo vol do portfolio, nao precisa prever direcao do preco, correlacao proxima de zero com BTC.

Desvantagens: rate flip e basis shock podem corroer, execution cost em yield baixo, risco de liquidation na perna derivativa, rendimento teto menor que direcionais em bull market, complexidade operacional (rebalance, multiplas margin accounts), gamma scalping com opcoes e muito complexo e liquidez de opcoes em cripto e menor.

### Checklist de proximos passos

1. Implementar STRAT-08 (funding arb) primeiro, ver pesquisa dedicada.
2. Implementar basis trading com futuros datados (`basis_trade.py`).
3. Avaliar perp-perp arb (viabilidade vs complexidade).
4. Implementar portfolio allocator no `risk_manager` (delta-neutral + direcional).
5. Adicionar monitor de rate flip e basis shock.
6. Roadmap: gamma scalping com Deribit (prioridade baixa).
7. Validar que a correlacao da base delta-neutral com BTC e < 0.2 no backtest.

## Referencias

- SparkCore: "Delta Neutral & Beta Neutral Crypto Strategies", adocao institucional, drawdown BTC > 70%, market-neutral como porta de entrada. sparkcore.fund.
- BackQuant: "The Basis Trade Explained: Cash and Carry in Crypto for BTC and ETH", estrategia delta-neutral mais simples, desks rodam em background. backquant.com/learn/basis-trade.
- Coin Frontier: "Delta Neutral Trading Explained: The Ultimate Guide", fontes de retorno (funding, basis, theta, vega), estrategias A a D. coinfrontier.guide.
- NYXANCE: "Delta-Neutral Strategies for Crypto", glossario, straddles/strangles/iron condors, gamma scalping institucional. nyxance.com.
- Altrady: "Delta Neutral Trading Strategies in Crypto", isolar fontes de renda removendo chute direcional. altrady.com.
- Button.xyz: "Funding Rate Arbitrage: Capture Perp Funding at Scale", automatizacao como unico modo de escalar. button.xyz.
- Derivatives Journal: "Funding Rate Arbitrage", yield high single to low double digits, modos de falha. derivativesjournal.com.
- Manual interno: docs/strategies/08-funding-rate-arbitrage.md (STRAT-08)
