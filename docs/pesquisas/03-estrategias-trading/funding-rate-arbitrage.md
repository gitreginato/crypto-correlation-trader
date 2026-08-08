# Topico: Funding Rate Arbitrage (Delta-Neutral)

**Data:** 2026-07-15
**Categoria:** Estrategia de Trading

## TL;DR

Funding rate arbitrage e uma estrategia delta-neutral que coleta pagamentos de funding de perpetual futures sem exposicao direcional ao preco. Mantem-se long em spot e short em perpetual (ou vice-versa), de forma que o movimento de preco se cancela e o lucro vem do funding rate. Nao ha script em `src/strategy/` ainda, so o manual em `docs/strategies/08-funding-rate-arbitrage.md` (STRAT-08). Funciona em qualquer regime de mercado (nao importa se BTC sobe ou cai, o P&L direcional e zero), o que a torna unica entre as estrategias do projeto. Yield tipico de 5 a 30% a.a. dependendo do ativo e do regime (bull markets com funding positivo alto pagam mais). A Binance oferece historico de funding via `GET /fapi/v1/fundingRate` (max 1000 por request). Desde maio de 2025 a Binance passou a usar intervalos variaveis (1h, 4h, 8h) por contrato, o que complica o calculo de custo. Os 3 riscos principais: rate flip (funding vira negativo), basis risk (spot e perp divergem) e execution cost (fees podem exceder o funding coletado em taxas baixas).

## Explicacao para criancas

Imagine que voce tem uma maca e alguem te oferece dinheiro todo dia so para voce concordar em emprestar essa maca por algumas horas, mas sempre devolver a mesma maca. Voce nao se importa se a maca ficou mais cara ou mais barata no mercado, porque voce sempre tem a maca de volta e ganha o dinheiro do emprestimo. Em cripto, a maca e o Bitcoin (comprado no spot), e o dinheiro diario e o funding rate pago pela perna short no perpetual. O preco do BTC pode subir ou cair que voce nao ganha nem perde com isso, so ganha o funding.

## Como funciona tecnicamente

### O mecanismo do funding rate

Perpetual futures nao tem vencimento. Para manter o preco do perp proximo ao spot, exchanges usam funding rates: a cada intervalo (8h na Binance historico, agora variavel), longs pagam shorts (funding positivo) ou shorts pagam longs (funding negativo).

```
Funding Rate = Premium Index + Interest Rate
Premium Index = (Perp Price - Spot Price) / Spot Price
Interest Rate = 0.01% por 8h (default Binance)
Clamp: funding limitado a [-0.75%, +0.75%] por 8h na Binance
```

### Quando o funding e positivo

```
Perp > Spot (contango): longs estao alavancados e otimistas
Funding > 0: longs pagam shorts
Estrategia: LONG spot + SHORT perp = recebe funding
```

### Quando o funding e negativo

```
Perp < Spot (backwardation): shorts estao alavancados e pessimistas
Funding < 0: shorts pagam longs
Estrategia: SHORT spot + LONG perp = recebe funding
```

### Setup delta-neutral (long spot + short perp)

1. Comprar 1 BTC no spot a $95,000.
2. Vender 1 BTC no perpetual a $95,000 (mesmo valor nocional).
3. Delta total = 0. BTC sobe 10%? Spot ganha 10%, short perp perde 10%, liquido zero.
4. A cada intervalo de funding, se funding positivo, longs pagam shorts. Voce e short, recebe.
5. Annualizar o funding rate: APY = funding_rate * ciclos_por_ano (3 * 365 = 1095 se 8h).

### Exemplo numerico

```
Capital: $10,000
Funding rate: 0.01% a cada 8h (positivo)
Posicao: Long $5,000 spot + Short $5,000 perp
Pagamento por ciclo de 8h: $5,000 * 0.01% = $0.50
Ciclos por dia: 3
Renda diaria: $1.50
Renda anual: $547.50 (5.47% a.a.)

SE funding rate subir para 0.05% (bull market):
Renda anual: $2,737.50 (27.4% a.a.)
```

### Ranges tipicos de funding por ativo (2024 a 2026, condicoes normais a bullish)

Segundo CryptoMathTools, ranges tipicos observados em 2024 a 2026:

| Ativo | Binance (8h) | APY aproximado |
|-------|--------------|----------------|
| BTC | 0.005 a 0.015% | 5.5 a 16.4% |
| ETH | 0.008 a 0.025% | 8.8 a 27.4% |
| SOL | 0.010 a 0.040% | 11.0 a 43.8% |

Em eventos extremos (hack de exchange, anuncios regulatorios, semana de lancamento de ETF), funding pode subir 5 a 10x acima desses ranges por curtos intervalos. APY assume que a taxa persiste o ano inteiro, o que e irreal: o APY real depende do periodo de hold e da flutuacao da taxa.

### Riscos principais (os 3 do Kraken)

1. **Rate Flip**: funding vira de positivo para negativo. Voce para de receber e comeca a pagar. A estrategia so e viavel quando funding esta consistentemente elevado por varios dias, nao numa leitura unica alta.
2. **Basis Risk**: spot e perp podem divergir temporariamente. Se precisa fechar a posicao no momento errado, pode ter perda mesmo que o P&L direcional medio seja zero.
3. **Execution Cost**: fees de abertura e fechamento (2 trades) + slippage. Em taxas baixas, fees podem exceder o funding coletado.
4. **Liquidation Risk**: a perna short em perp pode ser liquidada se o preco subir muito (mesmo que a perna long spot compense, voce precisa de margem separada no perp).

### Gestao de risco

- Monitorar funding rate diario. So entrar quando funding positivo persistente por >= 3 dias.
- Manter margem suficiente no perp para evitar liquidacao (geralmente 2x a 3x o nocional em margem).
- Rebalancear quando o delta escorrega (o tamanho do perp muda com o preco, e preciso re-hedgear para manter delta zero).
- Stop se funding vira negativo por N ciclos seguidos (configuravel).
- Diversificar entre varios ativos (BTC, ETH, SOL) para nao depender de um so funding.

### Timeframe e expected performance

Timeframe ideal: 8h (funding period), 1d para decisao de entrada. Horizonte de dias a semanas.
Yield esperado: 5 a 30% a.a. dependendo do ativo e regime. Em bull markets com funding alto, pode passar de 40% a.a. em alts. Em bear markets com funding negativo, a estrategia inverte (short spot + long perp) ou fica de fora.
Sharpe tipico: alto (2 a 4+) porque o risco direcional e zero e o yield e estavel, mas sensivel a rate flip.
Drawdown: baixo se bem gerenciado, mas rate flip repentino pode corroer.

### Tabela de parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `min_funding_rate` | 0.0001 | 0.00005 a 0.001 | Funding minimo para entrar (positivo) |
| `min_persistence_days` | 3 | 1 a 7 | Dias consecutivos de funding acima do min |
| `max_basis_pct` | 0.02 | 0.01 a 0.05 | Basis maximo (spot vs perp) aceitavel |
| `margin_buffer` | 3.0 | 2.0 a 5.0 | Margem no perp como multiplicador do nocional |
| `rebalance_threshold` | 0.05 | 0.02 a 0.10 | Delta maximo antes de re-hedgear |
| `stop_neg_cycles` | 3 | 1 a 6 | Ciclos negativos consecutivos para sair |
| `target_assets` | BTC, ETH | - | Ativos com funding historico estavel |

### Variantes da estrategia

1. **Spot + short perp**: a versao classica descrita acima. Yield = funding rate.
2. **Perp A vs Perp B**: short perp na exchange com funding mais alto, long perp na exchange com funding mais baixo. Captura o diferencial entre exchanges. Mais complexo, mais risco de basis cruzado.
3. **Dated futures basis trade**: long spot + short futuro trimestral com premium. Yield = basis (futuro acima do spot) que converge a zero no vencimento. Tem data fixa de fim, diferente do perp que roda indefinidamente.

## Estado do mercado em 2026

Funding rate arbitrage segue como a estrategia delta-neutral mais institucional e acessivel a retail em 2026. O Derivatives Journal descreve como uma das estrategias market-neutral mais limpas em derivativos de cripto, com yield em high single digits a low double digits anualizado, com risco concentrado em poucos modos de falha (rate flip, basis, execution). O BackQuant chama de "a estrategia delta-neutral mais simples em cripto, e a que a maioria dos desks institucionais roda silenciosamente em background".

Quem pesquisa e bot: o Button.xyz descreve a automatizacao como o unico modo de escalar o edge: execucao manual parece um meio turno, com rebalanceamento, monitoramento e retirada de lucro. O blog recomenda um agente que cuida do trabalho mecanico. O KlosStepan/Futures-funding-rate-calculations no GitHub mostra como baixar o historico completo de funding da Binance com paginacao por startTime (max 1000 por request). O CryptoMathTools mostra a formula e os ranges tipicos por ativo.

Quem ensina: Kraken, BackQuant, Button.xyz, Derivatives Journal e CryptoMathTools explicam com clareza e sem promessa de retorno garantido. O tom e honesto: o yield nao e magico nem gratis, vem de longs alavancados pagando pelo privilegio de manter posicao alavancada. A estrategia para de funcionar quando funding vira negativo.

Performance real reportada: os ranges de APY (BTC 5.5 a 16.4%, ETH 8.8 a 27.4%, SOL 11 a 43.8%) sao condicoes normais a bullish de 2024 a 2026. Em bull markets fortes, funding positivo persistente e comum, e a estrategia render bem. Em bear markets, funding fica negativo e a estrategia precisa inverter ou ficar de fora. A chave, segundo Kraken, e que a estrategia e mais viavel quando funding esteve consistentemente elevado por varios dias, nao numa leitura unica alta.

### Mudanca importante na Binance em 2025

Desde maio de 2025, a Binance passou a usar intervalos de funding variaveis por contrato: 1h, 4h ou 8h dependendo do ativo, e ate 1h quando atinge o cap/floor. Isso complica o calculo de custo e de APY. O endpoint `GET /fapi/v1/fundingInfo` retorna o intervalo atual por contrato, mas so o status atual, nao historico. Segundo a issue #12583 do freqtrade, em novembro de 2025 cerca de 60% dos contratos USDT ainda usavam 8h, mas uma parte usava 4h ou 1h. Para o backtest, isso significa que assumir 8h fixo para todos os contratos produz calculos errados para uma parte do universo.

### Quem ensina e quem vende curso

A area de funding arb e mais institucional e pratica do que de curso. Exchanges (Kraken, Binance), blogs quant (BackQuant, Derivatives Journal, CryptoMathTools) e repos GitHub (KlosStepan) explicam com codigo e sem promessa de retorno garantido. Nao ha o fenomeno de venda de curso prometendo retornos como em ICT/SMC. O tom e: o yield e real e estavel, mas tem modos de falha especificos, e automatizar e a unica forma de escalar.

## Ferramentas e APIs disponiveis

### APIs de funding rate

- Binance: `GET /fapi/v1/fundingRate` (USDT-margined), `GET /dapi/v1/fundingRate` (coin-margined). Max 1000 por request, paginar com startTime. Rate limit 500/5min/IP.
- Binance: `GET /fapi/v1/fundingInfo` retorna intervalo atual (1h, 4h, 8h) e cap/floor por contrato.
- Bybit, OKX: endpoints equivalentes para funding rate history.

### Bibliotecas Python

- `ccxt`: abstracao unificada para Binance, Bybit, OKX, com metodos para funding rate history e execucao de spot + perp.
- `python-binance`: SDK oficial da Binance com suporte a futures e funding rate.
- `pandas`: para calcular APY rolling, persistence de funding, e simular o carry.

### Dados

- Binance Vision: nao tem funding historico direto, mas tem klines para validar basis.
- Binance REST API: funding rate history (paginado), premium index, mark price.

### Plataformas que suportam

- Binance, Bybit, OKX: spot e perp na mesma exchange, o que facilita o hedge e reduz risco de transferencia.
- Hyperliquid: perps on-chain com funding mais volatil, bom para capturar funding extremo, mas nao tem spot nativo (precisa hedge em outra venue).
- dYdX: perps on-chain com funding horario.

### Combinacao com outras estrategias do projeto

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Todas as direcionais | Alta | Funding arb como base estavel do portfolio, reduz vol total |
| + Mean Reversion (STRAT-01) | Media | Funding extremo pode causar descolamento do cluster |
| + Momentum (STRAT-06) | Media | Funding extremo sinaliza fim de tendencia |
| + Delta-neutral geral | Alta | Funding arb e um subtipo de delta-neutral |

A combinacao mais poderosa para o portfolio e rodar funding arb como base estavel (yield 5 a 30% a.a. com baixa vol) ao lado das estrategias direcionais (momentum, mean reversion) que tem maior retorno potencial mas maior vol. Isso reduz a volatilidade total do portfolio sem sacrificar muito o retorno.

## Por que importa para o crypto-correl-bot

Ja temos script: nao. Nao ha `src/strategy/funding_arb.py`. So o manual em `docs/strategies/08-funding-rate-arbitrage.md` (STRAT-08), que documenta a matematica, os riscos e os parametros. A implementacao e o proximo passo.

STRAT-08. O que falta:

1. **Implementar `src/strategy/funding_arb.py`**: criar a classe `FundingArbStrategy(BaseStrategy)` que monitora funding, abre posicao delta-neutral quando funding positivo persistente, e fecha quando vira negativo. Precisa de conexao spot + perp na mesma exchange.
2. **Coletar historico de funding**: implementar download paginado de `GET /fapi/v1/fundingRate` (max 1000, paginar com startTime). Armazenar em Parquet como os klines. O KlosStepan/Futures-funding-rate-calculations mostra o padrao.
3. **Modelar intervalo variavel de funding**: desde maio de 2025 a Binance usa 1h, 4h ou 8h por contrato. Consumir `GET /fapi/v1/fundingInfo` para o intervalo atual e nao assumir 8h fixo.
4. **Modelar basis risk no backtest**: o P&L direcional medio e zero, mas basis temporario pode gerar perda se precisa fechar no momento errado. Incluir basis no backtest.
5. **Modelar execution cost**: 2 trades (abertura e fechamento) + slippage. Em taxas baixas, fees podem exceder funding. So entrar se funding esperado > fees * 2.
6. **Monitor de liquidation na perna perp**: margem separada, alerta se margem cai abaixo de buffer.
7. **Rebalanceamento automatico**: o tamanho do perp muda com o preco, e preciso re-hedgear para manter delta zero. Definir threshold de delta para rebalancear.

### Vantagens e desvantagens

Vantagens: funciona em qualquer regime de mercado (o P&L direcional e zero), yield estavel e previsivel (5 a 30% a.a.), baixa volatilidade comparada a direcionais, base institucional (desks rodam em background), nao precisa prever direcao do preco, complementa estrategias direcionais reduzindo vol do portfolio.

Desvantagens: rate flip pode virar o fluxo de pagamento, basis risk em momentos de stress (spot e perp divergem), execution cost pode exceder funding em taxas baixas, risco de liquidacao na perna perp (precisa margem separada), rendimento limitado comparado a direcionais em bull market, complexidade operacional de manter duas pernas sincronizadas e rebalancear delta.

### Metricas de avaliacao (target)

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| APY | 10%+ | 5% |
| Sharpe ratio | 2.0+ | 1.5 |
| Max drawdown | < 5% | < 10% |
| Tempo em mercado | 70%+ | 50% |
| Rate flip events/ano | < 6 | < 12 |

### Checklist de proximos passos para STRAT-08

1. Criar `src/strategy/funding_arb.py` com `FundingArbStrategy`.
2. Implementar download paginado de funding history (`GET /fapi/v1/fundingRate`).
3. Consumir `GET /fapi/v1/fundingInfo` para intervalo variavel.
4. Modelar basis risk e execution cost no backtest.
5. Implementar monitor de liquidation e rebalanceamento.
6. Backtest em bull (2021) e bear (2022) para validar os dois lados.
7. Integrar como base estavel do portfolio ao lado das direcionais.

## Referencias

- Kraken: "Funding rate arbitrage in crypto: how the strategy works", delta-neutral, 3 riscos (rate flip, basis, execution). kraken.com/learn/futures-trading-funding-rate-arbitrage
- BackQuant: "The Basis Trade Explained: Cash and Carry in Crypto for BTC and ETH", yield 5 a 30% a.a., long spot short perp. backquant.com/learn/basis-trade
- CryptoMathTools: "Crypto Funding Rate Explained", ranges por ativo (BTC 5.5 a 16.4%, ETH 8.8 a 27.4%, SOL 11 a 43.8% APY). cryptomathtools.com.
- Button.xyz: "Funding Rate Arbitrage: Capture Perp Funding at Scale", automatizacao como unico modo de escalar. button.xyz/blog/funding-rate-arbitrage
- Derivatives Journal: "Funding Rate Arbitrage: How Perp Funding Creates Profit Opportunities", yield high single to low double digits. derivativesjournal.com.
- KlosStepan/Futures-funding-rate-calculations: download paginado de funding history Binance. github.com/KlosStepan.
- Binance API: `GET /fapi/v1/fundingRate` e `GET /fapi/v1/fundingInfo`. developers.binance.com.
- freqtrade issue #12583: intervalos variaveis de funding (1h, 4h, 8h) desde maio 2025. github.com/freqtrade/freqtrade.
- Manual interno: docs/strategies/08-funding-rate-arbitrage.md (STRAT-08)
