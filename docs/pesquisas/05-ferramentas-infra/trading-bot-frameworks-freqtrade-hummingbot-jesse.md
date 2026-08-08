# Topico: Frameworks de Bot de Trading em Producao (Freqtrade, Hummingbot, Jesse, outros)

**Data:** 2026-07-15
**Categoria:** Ferramentas / Infra

## TL;DR

Para operar bots de trading em producao existem dois caminhos: usar um framework opinionated ou construir do zero. Freqtrade (GPLv3, 50k stars) domina o espaco open source com backtesting integrado, Hyperopt, FreqAI (ML adaptativo), Telegram bot, e web UI (FreqUI). Hummingbot (Apache-2.0, 19k stars) e especializado em market making e arbitragem cross-exchange (CEX + DEX), com $34B+ em volume gerado pelos usuarios. Jesse (MIT, 8k stars) oferece API limpa com GUI, MCP server para AI agents, e foco em cripto. Nautilus Trader (LGPL-3, Rust) e institutional-grade com research-to-live parity. Lean/QuantConnect (Apache-2.0, 20k stars) e multi-asset C# mas com cloud lock-in. OctoBot (GPLv3, 6k stars) e opinionated para grid/DCA/TradingView. O trade-off fundamental e: frameworks opinionated entregam velocidade de deploy e comunidade, mas impoem licenca (GPL contamina codigo), arquitetura rigida, e abstracao que pode esconder bugs criticos. Construir do zero (nossa abordagem atual) da controle total, licenca propria, e entendimento profundo de cada componente, mas exige implementar tudo: risk management, order routing, reconnect logic, notifications, monitoring. Para o crypto-correl-bot, a abordagem "do zero" e correta porque a estrategia (correlacao de grafos) e unica e nao se encaixa nos templates de nenhum framework, mas vale estudar Freqtrade e Jesse para borrow patterns de producao.

## Explicacao para criancas

Imagine que voce quer construir um robo que compra e vende balas automaticamente, sem voce ficar olhando o tempo todo.

**Usar um framework (Freqtrade, Hummingbot, Jesse)** e como comprar um carro pronto: voce so precisa aprender a dirigir (escrever a estrategia) e o carro ja tem motor, freio, airbag, GPS, e tudo o que precisa. Vantagem: rapido para comecar, ja testado por milhares de pessoas. Desvantagem: voce nao pode mudar o motor, nao pode trocar a forma do chassi, e se o carro quebrar de um jeito que o fabricante nao previu, voce depende dele para consertar. Alguns fabricantes dizem "se voce usar meu carro, todo carro que voce construir depois tem que ser igual ao meu" (isso e a licenca GPL).

**Construir do zero** e como construir o carro peca por peca: voce escolhe o motor (VectorBT), os freios (risk manager), o GPS (Binance API), o radio (Telegram notifications). Vantagem: controle total, voce entende cada peca, pode otimizar para sua estrategia especifica. Desvantagem: demora muito mais, e se esquecer de colocar o airbag (kill switch), pode bater forte.

Cada framework tem uma personalidade:

- **Freqtrade** e o SUV popular: todo mundo tem um, comunidade enorme, mas e feito para estrategias de "seguir tendencia" (RSI, MACD), nao para correlacao de grafos.
- **Hummingbot** e o caminhao de entrega: feito para market making (colocar ordens de compra e venda ao mesmo tempo e lucrar no spread), nao para estrategias direcionais.
- **Jesse** e o carro esportivo moderno: rapido, bonito, feito para cripto, mas comunidade menor.
- **Nautilus** e um tanque militar: super robusto, feito em Rust, para instituicoes, mas complexo.
- **OctoBot** e o carro familiar: grid, DCA, simples, com interface amigavel.

## Como funciona tecnicamente

### Freqtrade

Freqtrade (GPLv3, 50k+ stars) e o framework de bot de cripto mais popular. Arquitetura modular em Python puro:

**Componentes principais:**
- **Strategy**: classe Python com metodos `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()` que retornam DataFrames com sinais
- **Backtesting**: engine integrado que simula a estrategia sobre dados historicos
- **Hyperopt**: otimizacao de hyperparametros via Optuna (bayesian optimization)
- **FreqAI**: modulo de ML adaptativo que treina modelos (XGBoost, LightGBM, etc.) que se adaptam ao mercado
- **FreqUI**: interface web para monitorar e controlar o bot
- **Telegram**: integracao para notificacoes e controle remoto
- **Exchange integration**: via CCXT, suporta 20+ exchanges
- **Dry-run**: paper trading integrado

**Fluxo de estrategia:**
```python
class MyStrategy(IStrategy):
    def populate_indicators(self, dataframe, metadata):
        dataframe['rsi'] = ta.RSI(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[(dataframe['rsi'] < 30), 'buy'] = 1
        return dataframe
```

**FreqAI:** Permite treinar modelos de ML que se adaptam ao mercado. Suporta classificadores (XGBoost, LightGBM, CatBoost) e regressores. Treina periodicamente com dados recentes e prediz sinais. Isso e o diferencial vs outros frameworks: ML nativo integrado no pipeline de backtest e live.

**Licenca GPLv3:** Critico. Se voce distribuir seu bot baseado em Freqtrade, voce DEVE abrir o codigo fonte sob GPLv3. Para uso pessoal (nao distribuicao), nao ha problema. Mas se o projeto crescer para um produto comercial, GPLv3 e uma limitacao real.

### Hummingbot

Hummingbot (Apache-2.0, 19k stars) e especializado em market making e arbitragem. Diferente de Freqtrade (direcional), Hummingbot coloca ordens simultaneas de compra e venda ao redor do preco atual, lucrando do spread.

**Arquitetura V2 (2025-2026):**
- **Controllers**: framework refatorado para estrategias multi-mercado complexas
- **Connectors**: 300+ conectores para CEX (Binance, Bybit, OKX), DEX (Uniswap, PancakeSwap, Hyperliquid)
- **Gateway**: middleware para DEX (AMM, CLOB on-chain)
- **Strategy frameworks**: Pure Market Making, Liquidity Mining, Cross-Exchange Arbitrage, PMM Dynamic
- **Dashboard**: web UI para monitorar multiplas instancias
- **Backtesting**: limitado (foco em producao, nao pesquisa)

**Caso de uso tipico:** Voce tem $10k+ e quer ganhar spread colocando ordens em BTC/USDT. Hummingbot coloca buy em $99.500 e sell em $100.500, e se ambos executarem, voce lucra $1000 (spread) menos fees. Se o mercado cair, voce fica com BTC (risco direcional residual).

**Volume gerado:** $34B+ em volume aggregate reportado por instancias desde janeiro 2025. 100k+ instancias ativas.

**Licenca Apache-2.0:** Permissiva. Pode usar comercialmente, modificar, distribuir sem abrir codigo. Melhor que GPLv3 do Freqtrade para casos comerciais.

### Jesse

Jesse (MIT, 8k stars) e focado em cripto com API mais limpa que Freqtrade. Features em 2026:

- **Backtesting sem look-ahead bias**: design explicito para prevenir peeking de dados futuros
- **Optimizer**: otimizacao de parametros integrada
- **Live dashboard**: GUI web para monitorar estrategias
- **Multi-account**: suporte a multiplas contas simultaneas
- **MCP Server**: integracao com AI agents (Claude, Cursor) que podem pesquisar, backtestar e validar estrategias
- **Notifications**: Telegram, Slack, Discord
- **Spot/Futures/DEX**: suporte completo
- **Partial fills**: modelagem realista
- **Risk management**: tools built-in
- **Code editor**: editor built-in na GUI

**Licenca MIT:** A mais permissiva. Uso comercial livre, sem restricoes.

**Diferenca vs Freqtrade:** Jesse e menos opinionated (nao impoe template de estrategia), tem API mais Pythonica, e previne look-ahead bias por design. Freqtrade tem comunidade maior, FreqAI (ML nativo), e mais exchanges.

### Nautilus Trader

Ja coberto em detalhe no arquivo de backtest. Para producao, o diferencial e:
- **Research-to-live parity**: mesmo codigo em backtest e live, sem mudancas
- **Nanosecond resolution**: para estrategias de baixa latencia
- **Multi-venue**: market making cross-exchange em producao
- **Rust core**: performance e memory safety para producao critica
- **LGPL-3**: licenca mais restritiva que MIT/Apache (derivativos devem abrir codigo)

### Lean (QuantConnect)

Lean (Apache-2.0, 20k stars) e o engine da QuantConnect. Multi-asset (acoes, forex, cripto, options, futuros), escrito em C# com suporte a Python.

**Caracteristicas:**
- Event-driven, professional-caliber
- QuantConnect Cloud: plataforma SaaS para deploy e backtest na nuvem
- Lean CLI: interacao via terminal
- Data library: dados historicos de multiplas fontes (incluindo cripto)
- Broker integration: IBKR, Binance, Bitfinex, Coinbase, etc.
- Apache-2.0: permissiva

**Limitacoes para cripto puro:** E projetado para multi-asset institutional, nao otimizado para cripto-especifico. A nuvem QuantConnect tem custo ($0-$400/mo para features avancadas). O suporte a Python e secundario vs C# (94% C# vs 5.6% Python no repo).

### OctoBot

OctoBot (GPLv3, 6k stars) e opinionated para estrategias simples: Grid, DCA, TradingView signals. Tem interface web amigavel, suporta 15+ exchanges (Binance, Hyperliquid, Coinbase).

**Casos de uso:** Grid trading (colocar grades de ordens em intervalos regulares), DCA (dollar cost averaging automatico), TradingView webhooks (executar sinais do Pine Script). Nao e projetado para estrategias quant complexas como correlacao de grafos.

**Licenca GPLv3:** Mesma restricao do Freqtrade.

### Outros: jespresso, OctoBot-Script

**jespresso:** Fork/variante do Jesse para deploy rapido em VPS. Comunidade muito pequena, nao confirmado se mantido ativamente.

**OctoBot-Script:** Framework quant do OctoBot (escrever, backtestar e automatizar em Python como Pine Script). Em alpha, 41 stars, nao pronto para producao.

### Comparativo

| Aspecto | Freqtrade | Hummingbot | Jesse | Nautilus | Lean/QC | OctoBot | Do zero |
|---|---|---|---|---|---|---|---|
| Stars | 50k | 19k | 8k | 2.5k | 20k | 6k | N/A |
| Licenca | GPLv3 | Apache-2.0 | MIT | LGPL-3 | Apache-2.0 | GPLv3 | Sua |
| Estrategia | Direcional | Market making | Direcional | Multi | Multi | Grid/DCA | Qualquer |
| Backtesting | Integrado | Limitado | Integrado | Avancado | Avancado | Basico | VectorBT |
| ML integrado | FreqAI | Nao | Nao | AI training | Nao | Nao | Voce faz |
| Exchanges | 20+ | 300+ | Cripto focus | Multi-venue | Multi-asset | 15+ | CCXT (100+) |
| Telegram | Sim | Nao (dashboard) | Sim (TG/Slack/Discord) | Nao | Nao | Sim | Voce faz |
| Web UI | FreqUI | Dashboard | Built-in | Nao | QC Cloud | Sim | Voce faz |
| DEX support | Limitado | Excelente | Sim | Sim | Limitado | Hyperliquid | CCXT/Gateway |
| Deploy | Docker | Docker | Docker | Docker | QC Cloud | Docker | Voce faz |
| Curva de aprendizado | Media | Ingreme | Baixa | Alta | Alta | Baixa | Alta |
| Opinionated | Alto | Alto (MM) | Medio | Baixo | Medio | Alto (Grid) | Zero |
| Comercial use | GPLv3 limita | Sim | Sim | LGPL limita | Sim | GPLv3 limita | Sim |

## Estado do mercado em 2026

O ecossistema de bots de trading open source maturou significativamente em 2025-2026. Tres tendencias principais:

**1. ML nativo integrado:** Freqtrade com FreqAI lidera, permitindo treinar modelos adaptativos que se reajustam ao mercado. Jesse adicionou MCP server para AI agents. Nautilus suporta RL/ES training. A barreira entre "bot tradicional" e "AI trading agent" esta diminuindo.

**2. DEX como cidadão de primeira classe:** Hummingbot com Gateway para AMM/CLOB DEX, Jesse com suporte a DEX, OctoBot com Hyperliquid. O movimento e claro: com geoblocks de CEX (Binance BR), DEX sem KYC tornam-se infraestrutura critica.

**3. Frameworks vs do zero:** A questao "usar framework ou construir do zero" depende da estrategia. Para estrategias padrao (trend following, grid, DCA, market making), frameworks entregam 80% do valor em 20% do tempo. Para estrategias nao-padrao (correlacao de grafos, stat arb custom, HFT proprietario), frameworks impoem abstracoes que atrapalham mais que ajudam, e construir do zero com bibliotecas (CCXT + VectorBT + pandas) e mais eficiente.

A licenca GPLv3 (Freqtrade, OctoBot) permanece uma preocupacao real para projetos com potencial comercial. Apache-2.0 (Hummingbot, Lean) e MIT (Jesse) sao significativamente mais seguros para uso comercial.

## Ferramentas e APIs disponiveis

| Ferramenta | Versao | Licenca | Repo | Custo | Maturidade |
|---|---|---|---|---|---|
| Freqtrade | 2026.4 | GPLv3 | github.com/freqtrade/freqtrade | $0 | Muito alta (50k stars) |
| Hummingbot | 2.15.0 | Apache-2.0 | github.com/hummingbot/hummingbot | $0 | Muito alta (19k stars) |
| Jesse | 2.3.4 | MIT | github.com/jesse-ai/jesse | $0 (premium: $$) | Alta (8k stars) |
| Nautilus Trader | 0.60.0 | LGPL-3 | github.com/nautechsystems/nautilus_trader | $0 | Media-alta |
| Lean (QuantConnect) | 2.5+ | Apache-2.0 | github.com/QuantConnect/Lean | $0 ($0-$400/mo cloud) | Muito alta (20k stars) |
| OctoBot | 2.1.1 | GPLv3 | github.com/Drakkar-Software/OctoBot | $0 | Alta (6k stars) |
| OctoBot-Script | Alpha | GPLv3 | github.com/Drakkar-Software/OctoBot-Script | $0 | Baixa (alpha) |
| jespresso | Nao confirmado | Nao confirmado | Nao confirmado | Nao confirmado | Baixa (nao confirmado) |

## Por que importa para o crypto-correl-bot

### O que usamos hoje

O projeto adota a abordagem "construir do zero": CCXT/python-binance para dados, PyArrow/Parquet para armazenamento, NetworkX para analise de grafos, VectorBT para backtest, e componentes proprios para risk management, paper broker, live broker, e notifications (Telegram). Esta decisao nao foi explicita contra frameworks, mas implicita pela arquitetura modular do projeto (ver estrutura de arquivos em AGENTS.md: `src/bot/engine.py`, `src/bot/risk_manager.py`, `src/bot/paper_broker.py`, etc.).

### Trade-offs e consideracoes

**A abordagem "do zero" e correta para a estrategia de correlacao de grafos.** Nenhum framework existente tem abstracao nativa para:
- Construir grafo de correlacao entre symbols (NetworkX)
- Detectar comunidades/clusters no grafo (Louvain, modularity)
- Gerar sinais baseados em desvios de correlacao (z-score de spread entre pares)
- Dynamic universe selection (quais symbols incluir baseado em estrutura do grafo)

Freqtrade exige que a estrategia se encaixe em `populate_indicators / populate_entry_trend / populate_exit_trend`, que e orientada a indicadores tecnicos por symbol. Correlacao entre symbols nao se encaixa naturalmente. Hummingbot e para market making, totalmente diferente. Jesse e mais flexivel mas ainda espera estrategias por symbol.

**O que vale borrow de frameworks:**

1. **Freqtrade: Padroes de producao**
   - Telegram integration: Freqtrade tem bot Telegram maduro para notificacoes e controle. Borrow o padrao de comandos (/status, /profit, /stop).
   - Dry-run (paper trading): Freqtrade tem modo dry-run que simula live sem dinheiro real. Nosso `paper_broker.py` faz similar, mas vale estudar como Freqtrade lida com edge cases (reconexao, ordens pendentes em restart).
   - FreqAI: O conceito de treinar modelos que se adaptam ao mercado e aplicavel. Se a correlacao for instavel (muda com regime), treinar HMM ou modelo de regime detection que se reajusta e analogo ao FreqAI.

2. **Jesse: Prevencao de look-ahead bias**
   - Jesse previne look-ahead bias por design. Nosso backtest com VectorBT precisa de cuidado manual para nao usar dados futuros. Borrow o conceito de "bar close" semantics: so agir apos o candle fechar.

3. **Hummingbot: Padroes de DEX**
   - Se precisarmos migrar para DEX (Hyperliquid) por geoblock, o padrao de Gateway da Hummingbot (middleware para AMM/CLOB on-chain) e referencia de arquitetura.

4. **Nautilus: Research-to-live parity**
   - O conceito de usar o mesmo codigo em backtest e live e fundamental. Nosso projeto separa `backtest/engine.py` de `bot/engine.py`, mas a logica da estrategia deveria ser identica. Vale garantir que `MeanReversionStrategy` tem a mesma interface em ambos.

**Riscos da abordagem "do zero" que frameworks ja resolveram:**
- **Kill switch:** Frameworks tem kill switch testado por milhares de usuarios. Nosso bot precisa implementar e testar (AGENTS.md regra 3: "NUNCA implementar execucao real sem kill switch").
- **Reconnect logic:** WebSocket reconexao com backoff exponential. python-binance faz isso, mas se migrarmos para CCXT, precisamos implementar.
- **Order tracking:** Confirmar fill via WebSocket, nao assumir. Frameworks tem maquina de estados de ordens (submitted -> partial -> filled / cancelled / rejected).
- **Risk limits:** Max position size, max drawdown stop, daily loss limit. Frameworks tem built-in, nos precisamos implementar em `risk_manager.py`.
- **Monitoring e alerting:** Se o bot para de funcionar silenciosamente (geoblock 403), quem avisa? Freqtrade tem heartbeat via Telegram. Nos precisamos de similar.

### O que poderiamos migrar

1. **Curto prazo (manter do zero + borrow patterns):** Continuar construindo componentes proprios, mas estudar Freqtrade e Jesse para padroes de producao (Telegram, kill switch, order tracking, reconnect). Custo: zero (apenas estudo). Beneficio: evitar reinventar rodas com bugs.

2. **Medio prazo (avaliar Jesse para live trading):** Se a complexidade de manter `live_broker.py` + `risk_manager.py` + `notifications.py` + `engine.py` se tornar excessiva, avaliar migrar o runtime para Jesse (que tem tudo isso built-in e MIT licenca), mantendo a logica de correlacao de grafos como biblioteca propria importada. Custo: medio (adaptar estrategia para Jesse API + importar modulo de correlacao). Beneficio: infraestrutura de producao madura sem GPLv3.

3. **Nao migrar para:** Freqtrade (GPLv3 contamina, estrategia nao se encaixa), Hummingbot (market making, nao direcional), OctoBot (Grid/DCA, nao correlacao), Lean (C# focused, cloud lock-in), Nautilus (overkill para 30 symbols em 5m).

4. **Considerar FreqAI como inspiracao:** O conceito de ML adaptativo que se treina periodicamente com dados recentes e aplicavel ao nosso problema (correlacao instavel). Implementar versao propria: treinar HMM de regime detection a cada N dias com dados dos ultimos M dias, ajustar parametros da estrategia por regime. Nao usar FreqAI diretamente (dependencia Freqtrade), mas borrow a arquitetura.

## Referencias

1. Freqtrade Repository: https://github.com/freqtrade/freqtrade
2. Freqtrade Documentation: https://www.freqtrade.io
3. Freqtrade FreqAI: https://www.freqtrade.io/en/stable/freqai/
4. Hummingbot Repository: https://github.com/hummingbot/hummingbot
5. Hummingbot Website: https://hummingbot.org
6. VoiceOfChain: Freqtrade vs Hummingbot 2026: https://voiceofchain.com/academy/freqtrade-vs-hummingbot-2026
7. DEV Community: Freqtrade vs Hummingbot vs CCXT: https://dev.to/trendrider/freqtrade-vs-hummingbot-vs-ccxt-which-should-you-use-1ma7
8. InvestingRobots: Freqtrade vs Hummingbot: https://investingrobots.com/freqtrade-vs-hummingbot/
9. Gainium: Freqtrade vs Hummingbot vs Gainium 2026: https://gainium.io/compare/freqtrade-vs-hummingbot
10. Jesse AI Repository: https://github.com/jesse-ai/jesse
11. Jesse Website: https://jesse.trade/
12. Jesse PyPI: https://pypi.org/project/jesse/
13. QuantConnect Lean Repository: https://github.com/QuantConnect/Lean
14. QuantConnect Lean CLI: https://www.lean.io
15. OctoBot Repository: https://github.com/Drakkar-Software/OctoBot
16. OctoBot-Script Repository: https://github.com/Drakkar-Software/OctoBot-Script
17. Youngju Dev: Trading Bots and Quant Tools 2026: https://www.youngju.dev/blog/culture/2026-05-16-trading-bots-quant-tools-2026-lean-quantconnect-backtrader-zipline-freqtrade-hummingbot-nautilus-vectorbt-deep-dive.en
