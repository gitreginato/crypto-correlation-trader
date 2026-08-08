# Topico: Frameworks de Backtest (VectorBT, Backtrader, Jesse, Nautilus Trader)

**Data:** 2026-07-15
**Categoria:** Ferramentas / Infra

## TL;DR

Para backtesting de estrategias de trading em cripto, existem dois paradigmas fundamentais: vetorizado (rapido, menos realista) e event-driven (mais lento, mais realista). VectorBT (BSD-3, Numba/NumPy) domina o paradigma vetorizado com 20x mais velocidade que Backtrader, processando milhares de combinacoes de parametros em segundos, ideal para pesquisa e hyperparameter sweeps. Backtrader (GPLv3, puro Python) e o workhorse event-driven, estavel desde 2015, com broker integration real (IBKR, OANDA), mas atividade do mantenedor caiu apos 2020. Jesse (MIT, Python) oferece API moderna com GUI e optimizer, focado em cripto, com backtesting sem look-ahead bias. Nautilus Trader (LGPL-3, Rust + Python) e o mais avancado: core em Rust com nanosecond resolution, research-to-live parity, multi-venue, projetado para institutional. zipline-reloaded (Apache-2.0) tem problemas serios de instalacao em Python 3.12+ (C extensions quebradas, bcolz incompativel). Para o crypto-correl-bot, a abordagem otima e VectorBT para pesquisa rapida e sweeps + Backtrader para validacao final realista, exatamente como decidido em 2026-07-15.

## Explicacao para criancas

Imagine que voce quer testar se uma estrategia de comprar e vender balas (criptomoedas) teria dado lucro no passado. Existem dois jeitos:

**Vetorizado (VectorBT)** e como calcular tudo de uma vez com uma super calculadora. Voce da todas as regras ("compre quando o preco subir 5%, venda quando cair 3%") e a calculadora processa tudo junto, em paralelo, em segundos. E tao rapido que voce pode testar milhares de variacoes da estrategia em poucos minutos. O problema e que a calculadora assume que suas ordens sempre sao executadas exatamente como voce quer (sem falhas, sem atrasos), o que na vida real nem sempre acontece.

**Event-driven (Backtrader, Jesse, Nautilus)** e como simular o mercado dia a dia, minuto a minuto, como se voce estivesse la. O simulador vai barra por barra: "ok, segunda-feira 9h, preco abriu em 100, voce tem uma ordem de compra em 98... nao executou. 9h05, preco caiu para 97, sua ordem executou em 98 (slippage), agora voce tem a bala." E mais realista porque simula slippage, partial fills, latencia, taxas, mas e bem mais lento porque faz tudo passo a passo.

**Nautilus** e como um simulador de voo profissional: tao realista que voce pode usar o mesmo codigo no simulador e no mercado real, sem mudar nada. E feito em Rust (linguagem super rapida) por isso e mais veloz que os outros event-driven.

**zipline-reloaded** era como um aviao antigo que todo mundo achava legal, mas agora as pecas nao encaixam mais (nao instala direito em Python novo).

## Como funciona tecnicamente

### Paradigma Vetorizado (VectorBT)

No paradigma vetorizado, toda a logica da estrategia e expressa como operacoes matriciais sobre arrays NumPy. Em vez de iterar barra por barra, processa-se todo o historico de uma vez:

```python
import vectorbt as vbt
import pandas as pd

# Sinais de entrada e saida como arrays booleanos
entries = prices["close"] > prices["close"].rolling(20).mean()
exits = prices["close"] < prices["close"].rolling(10).mean()

# Backtest em uma linha
pf = vbt.Portfolio.from_signals(prices, entries, exits, fees=0.001)
print(pf.total_return())
```

Internamente, VectorBT usa Numba (JIT compiler para Python que gera codigo maquina equivalente a C) para acelerar operacoes criticas. As operacoes de portfolio simulation (calcular PnL, equity curve, drawdown) sao compiladas em Numba e executadas em arrays sem overhead de Python.

**Velocidade:** Um sweep de 1000 combinacoes de parametros que leva 12 minutos no Backtrader leva 45 segundos no VectorBT (20x mais rapido, benchmark real do AlgoKing 2025). O benchmark do LedgerMind reporta 2400 backtests/hora para VectorBT vs 850/hora para Backtrader.

**Limitacoes do vetorizado:**
- Logica de ordens complexas (partial fills, ordens condicionais, OCO) e awkward ou impossivel
- Multi-timeframe nao e nativo (requer workaround com resampling)
- Simulacao de slippage e basica (modelos simples, nao realistas para HFT)
- Nao ha broker integration nativa (nao vai para live trading)
- Portfolio simulation e basica vs Backtrader

**VectorBT PRO:** Versao paga (~$1000+/ano) adiciona: limit orders com tempo-in-force, leverage/margin modeling, pipeline de research em escala, e infraestrutura para producao. A versao open source (BSD-3) e suficiente para pesquisa.

### Paradigma Event-Driven (Backtrader, Jesse, Nautilus)

No paradigma event-driven, o engine simula o mercado processando evento por evento:

1. Engine carrega dados e cria uma timeline de barras
2. Para cada barra, dispara evento `next()` para a estrategia
3. Estrategia decide e envia ordens ao broker simulado
4. Broker simula execucao (fill, partial fill, slippage, commission)
5. Portfolio e atualizado
6. Proxima barra

```python
# Backtrader example
class MyStrategy(bt.Strategy):
    def next(self):
        if self.data.close[0] > self.data.close[-20]:
            self.buy(size=1)
        elif self.data.close[0] < self.data.close[-10]:
            self.sell(size=1)
```

**Vantagens:** realismo (slippage modelavel, partial fills, multi-asset, multi-timeframe nativo), broker integration para live trading, logica de ordens complexa (OCO, bracket, trailing stop).

**Desvantagens:** lento (loop Python por barra), sweep de parametros requer loops manuais, overhead de objetos Python.

### Backtrader

Backtrader (GPLv3) e puro Python, estavel desde 2015. Arquitetura modular: Cerebro (engine), Strategy (logica), Broker (simulador ou live), Data Feeds, Indicators, Analyzers, Observers, Sizers.

**Pontos fortes:** API rica e flexivel (100+ indicadores built-in), documentacao extensa, comunidade grande com muitos exemplos, integracao com brokers (IBKR, OANDA,Interactive Brokers), multi-timeframe nativo, suporte a ordens complexas (bracket, OCO, trailing).

**Pontos fracos:** atividade do mantenedor caiu apos 2020 (PRs ocasionais mas sem releases frequentes), nao vetorizado (lento para sweeps), degradacao de performance com tick data, documentacao comprehensiva mas mal organizada, look-ahead bias requer prevencao manual.

**Resultados reais (LedgerMind 2026):** estrategia de momentum em BTC/USD (2020-2025): +23.7% retorno anual reportado vs +23.9% calculado manualmente. Variancia de 0.2%, alta precisao. Mas nao flaggeou look-ahead bias quando introduzido intencionalmente.

### Jesse

Jesse (MIT, jesse-ai) e focado em cripto. API mais moderna que Backtrader, com GUI web built-in (dashboard, charts interativos), optimizer integrado, e backtesting sem look-ahead bias (design explicito).

**Pontos fortes:** API limpa e Pythonica, sem look-ahead bias (por design), optimizer built-in, live dashboard, Docker-friendly, suporte a spot/futures/DEX, 300+ indicadores, multi-symbol/multi-timeframe, partial fills, risk management tools. Em 2026 adicionou MCP server para integracao com AI agents (Claude, Cursor).

**Pontos fracos:** comunidade menor que Freqtrade/Backtrader (8k stars), menos exchanges suportadas que Freqtrade, alguns componentes premium sao pagos (jesse.trade subscription para features avancadas).

**Performance:** LedgerMind reporta 1850 backtests/hora (vs 850 Backtrader, 2400 VectorBT). Posicao intermediaria em velocidade, mas com mais realismo que VectorBT.

### Nautilus Trader

Nautilus Trader (LGPL-3) e o framework mais avancado: core em Rust com bindings Python (PyO3). Arquitetura event-driven com nanosecond resolution, deterministica (mesmo resultado em backtest e live), multi-venue, multi-asset.

**Arquitetura:**
- Core em Rust: message bus, cache, order matching engine, clock
- Python: control plane, estrategia composition, adaptadores
- Dados: Nautilus Parquet format para replay, analise e backtest
- Modos: `backtest` (historico), `sandbox` (real-time com execucao virtual), `live` (conta real/paper)
- Research-to-live parity: mesma estrategia, mesmo codigo, mesmas semantcas

**Pontos fortes:** velocidade Rust (benchmarks de order matching, message bus throughput), nanosecond timestamps, simulacao realista (fee, latency, fill models, order book), multi-venue (market making cross-exchange), AI training (RL/ES), determinismo (backtest reproduzivel), deployment via Docker.

**Pontos fracos:** curva de aprendizado alta (Rust + Python hybrid), comunidade menor (5.5k downloads do crate nautilus-backtest), MSRV 1.96 (Rust recente), menos tutoriais que Backtrader, licenca LGPL-3 (mais restritiva que MIT).

**Versao atual:** v0.60.0 (junho 2026). Crate `nautilus-backtest` com 5473 downloads.

### zipline-reloaded

zipline-reloaded (Apache-2.0, Stefan Jansen) e o continuamento do Zipline original (Quantopian, descontinuado em 2020). Era o padrao para research quant academico.

**Problemas em 2026:**
- Python 3.12+: instalacao falha por C extensions quebradas (`_PyCFrame has no member named 'use_tracing'`, erro de compilacao Cython)
- Requer `bcolz-zipline` compilado do git (nao pip installavel diretamente)
- Requer ta-lib C library instalada manualmente
- conda-forge build disponivel apenas para Python 3.8-3.10 (nao 3.12+)
- Suporte oficial: Python >=3.10, mas issues abertos em 3.12+

Para o crypto-correl-bot com Python 3.14, zipline-reloaded e praticamente ininstalavel sem Docker/conda com Python 3.10 especificamente. Nao vale o esforco de manutencao.

### Comparativo

| Aspecto | VectorBT | Backtrader | Jesse | Nautilus | zipline-reloaded |
|---|---|---|---|---|---|
| Paradigma | Vetorizado (Numba) | Event-driven | Event-driven | Event-driven (Rust) | Event-driven |
| Linguagem | Python (Numba JIT) | Python puro | Python + JS | Rust + Python | Python (C ext) |
| Velocidade (backtests/h) | 2400 | 850 | 1850 | N/A (Rust perf) | 620 |
| Sweep de parametros | Excelente (nativo) | Manual (loops) | Built-in optimizer | Alto (Rust) | Limitado |
| Realismo (slippage/fills) | Basico | Avancado (custom) | Avancado | Muito avancado (nanosec) | Avancado |
| Broker integration | Nao | Sim (IBKR, OANDA) | Sim (cripto) | Sim (multi-venue) | Limitado |
| Live trading | Nao | Sim | Sim (paper + live) | Sim (production-grade) | Nao |
| Multi-timeframe | Awkward | Nativo | Nativo | Nativo | Nativo |
| Look-ahead bias | Baixo risco (vetor) | Risco (manual) | Prevenido (design) | Prevenido (design) | Risco (manual) |
| Licenca | BSD-3 | GPLv3 | MIT | LGPL-3 | Apache-2.0 |
| Comunidade (stars) | ~4k | ~16k | ~8k | ~2.5k | ~1.5k |
| Instalacao | Facil (pip) | Facil (pip) | Facil (pip) | Media (Rust + pip) | Dificil (C ext quebradas) |
| Custo | $0 (PRO: $1000+/ano) | $0 | $0 (premium: $$) | $0 | $0 |

## Estado do mercado em 2026

O paisagem de backtesting em Python crystallizou em 2026 com paparéis bem definidos:

**Pesquisa rapida e sweeps:** VectorBT dominante. Para explorar ideias rapidamente e testar milhares de combinacoes de parametros, nao ha concorrente na velocidade. O modelo freemium (open source para pesquisa, PRO para producao) e aceito pela comunidade.

**Validacao realista e live trading:** Backtrader permanence o ponto de entrada mais acessivel, mas sua estagnacao de manutencao (sem releases frequentes desde 2020) preocupa. Jesse cresceu como alternativa moderna para cripto especificamente, com API mais limpa e GUI built-in. Nautilus Trader e o choice institutional para quem precisa de performance e research-to-live parity, mas exige conhecimento de Rust ou aceite da curva de aprendizado.

**zipline-reloaded em crise:** Os problemas de instalacao em Python 3.12+ (C extensions incompativeis) tornaram-na praticamente inutilizavel para novos projetos. A dependencia de conda-forge com Python antigo (3.8-3.10) e uma limitacao fatal para projetos em Python 3.14.

**Freqtrade como framework completo:** Embora seja um bot framework (nao so backtester), Freqtrade tem um backtesting engine respeitavel (1200 backtests/hora segundo LedgerMind) integrado com Hyperopt e FreqAI. Para quem quer tudo em um (backtest + live + ML), e uma opcao valida, mas mais opinionated que usar bibliotecas separadas.

A recomendacao consolidada de multiples fontes (youngju.dev 2026, LedgerMind 2026, python.financial 2026, AlgoKing 2025): usar VectorBT para pesquisa (70% do tempo) e Backtrader/Jesse para validacao final (30% do tempo), ou Nautilus para quem precisa de institutional-grade.

## Ferramentas e APIs disponiveis

| Ferramenta | Versao | Licenca | Repo | Custo | Maturidade |
|---|---|---|---|---|---|
| VectorBT | 0.26+ | BSD-3 | github.com/polakowo/vectorbt | $0 | Alta |
| VectorBT PRO | N/A | Commercial | pro.vectorbt.dev | ~$1000+/ano | Alta (paid) |
| Backtrader | 1.9.78 | GPLv3 | github.com/mementum/backtrader | $0 | Alta (estagnado desde 2020) |
| Jesse | 2.3.4 | MIT | github.com/jesse-ai/jesse | $0 (premium: $$) | Alta (8k stars) |
| Nautilus Trader | 0.60.0 | LGPL-3 | github.com/nautechsystems/nautilus_trader | $0 | Media-alta (Rust+Py) |
| zipline-reloaded | 3.1.1 | Apache-2.0 | github.com/stefan-jansen/zipline-reloaded | $0 | Baixa (instalacao quebrada 3.12+) |
| backtesting.py | 0.3+ | AGPL-3 | github.com/kernc/backtesting.py | $0 | Media |
| bt | 1.1+ | MIT | github.com/pmorissette/bt | $0 | Media |
| PyAlgoTrade | 0.20 | Apache-2.0 | github.com/gbecerra/pyalgotrade | $0 | Baixa (pouco ativo) |

## Por que importa para o crypto-correl-bot

### O que usamos hoje

O projeto usa VectorBT como engine de backtest principal, decidido em 2026-07-15: "VectorBT como engine de backtest principal. Motivo: vetorizado (Numba), 20x mais rapido para sweeps de parametros." Backtrader foi listado como alternativa para validacao final (mais lento mas mais realista). Zipline foi rejeitado por ser complexo de instalar.

### Trade-offs e consideracoes

**O fluxo VectorBT + Backtrader e o otimo para este projeto.** A estrategia do crypto-correl-bot (mean reversion baseada em correlacao de grafos) tem dois fases: (1) pesquisa: testar diferentes janelas de correlacao, thresholds de edges, parametros de mean reversion, combinacoes de symbols. Isso exige sweeps de centenas de combinacoes. VectorBT faz isso em segundos. (2) validacao: confirmar que a melhor estrategia do sweep realmente funciona com slippage, fees e logica de ordens realista. Backtrader faz isso com mais fidelidade.

**VectorBT para pesquisa:**
- Sweep de threshold de correlacao (0.3 a 0.8, step 0.05): 11 valores
- Sweep de janela de correlacao (20, 60, 120, 252 barras): 4 valores
- Sweep de z-score entry/exit (-2/-1, -1.5/0, -1/1): 3 valores
- Total: 11 * 4 * 3 = 132 combinacoes
- VectorBT: ~6 segundos. Backtrader: ~27 minutos (132 * 12s cada).

**Backtrader para validacao final:**
- Rodar a estrategia otima com slippage modelado (0.05%)
- Multi-timeframe (5m para entry, 1h para trend filter)
- Partial fills e ordens limit
- Confirmar que Sharpe nao degrada com realismo

**Jesse como alternativa a Backtrader:** Jesse oferece API mais limpa, GUI built-in, e previne look-ahead bias por design (Backtrader exige cuidado manual). Se o projeto for migrar para live trading em cripto, Jesse tem integracao mais nativa (spot/futures/DEX) e dashboard de monitoramento. O custo de migrar de Backtrader para Jesse e medio (refatorar estrategia), mas o beneficio e uma base mais moderna e mantida.

**Nautilus e overkill para agora.** O projeto nao precisa de nanosecond resolution, multi-venue, ou Rust performance para 30 symbols em 5m. Se o projeto evoluir para HFT ou market making cross-exchange, Nautilus seria a escolha correta, mas isso e uma escalada arquitetural significativa.

**zipline-reloaded esta fora de questao.** Com Python 3.14, a instalacao e praticamente impossivel (C extensions quebradas em 3.12+). Mesmo se contornasse com Docker + Python 3.10, o custo de manutencao nao vale o beneficio (Alphalens e pipeline academico podem ser substituidos por pandas + statsmodels diretamente).

### O que poderiamos migrar

1. **Curto prazo (manter):** VectorBT para pesquisa + Backtrader para validacao. Este fluxo esta alinhado com a decisao registrada e com a pratica recomendada pela comunidade.

2. **Medio prazo (avaliar Jesse):** Se comecarmos live trading, avaliar migracao de Backtrader para Jesse como engine de validacao e live. Beneficio: API mais limpa, look-ahead bias prevenido por design, GUI de monitoramento, suporte nativo a cripto exchanges. Custo: refatorar estrategia de Backtrader para Jesse API.

3. **Longo prazo (se escalar para institutional):** Se o projeto evoluir para multi-venue, HFT, ou AI training (RL/ES), Nautilus Trader e a unica opcao com research-to-live parity em Rust. Custo alto de aprendizado mas beneficio maximo em performance e realismo.

## Referencias

1. Youngju Dev: Trading Bots and Quant Tools 2026 Deep Dive: https://www.youngju.dev/blog/culture/2026-05-16-trading-bots-quant-tools-2026-lean-quantconnect-backtrader-zipline-freqtrade-hummingbot-nautilus-vectorbt-deep-dive.en
2. LedgerMind: Backtesting Framework Comparison 2026, 12 Platforms: https://theledgermind.com/backtesting-framework-comparison-2026/
3. Python Financial: The Python Backtesting Landscape 2026: https://python.financial/
4. AlgoKing: vectorbt vs backtrader comparison 2025: https://algos.pro/posts/2025-05-28-vectorbt-vs-backtrader-python-backtesting/
5. AI Fin Hub: VectorBT vs Backtrader 2026: https://aifinhub.io/articles/vectorbt-vs-backtrader-2026/
6. Nautilus Trader Website: https://nautilustrader.io/
7. Nautilus Trader Docs (Overview): https://nautilustrader.io/docs/nightly/concepts/overview/
8. nautilus-backtest crate (crates.io): https://crates.io/crates/nautilus-backtest
9. Nautilus Backtest Rust Docs: https://docs.rs/nautilus-backtest/latest/nautilus_backtest/
10. Jesse AI Repository: https://github.com/jesse-ai/jesse
11. Jesse PyPI: https://pypi.org/project/jesse/
12. Jesse Website: https://jesse.trade/
13. zipline-reloaded PyPI: https://pypi.org/project/zipline-reloaded/
14. zipline-reloaded Installation Docs: https://zipline.ml4trading.io/install.html
15. zipline-reloaded Issue #241 (Python 3.12 support): https://github.com/stefan-jansen/zipline-reloaded/issues/241
16. zipline-reloaded Issue #276 (numpy compatibility): https://github.com/stefan-jansen/zipline-reloaded/issues/276
