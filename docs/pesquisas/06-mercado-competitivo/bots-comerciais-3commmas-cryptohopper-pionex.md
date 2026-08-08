# Topico: Bots comerciais retail (3Commas, Cryptohopper, Pionex, Bitsgap, TradeSanta, Coinrule, KuCoin Trading Bot)

**Data:** 2026-07-15
**Categoria:** Mercado Competitivo

## TL;DR

O mercado de bots de trading retail evoluiu de ferramentas de automacao simples
para plataformas SaaS com milhares de assinantes. O segmento se divide em tres
modelos: (1) cloud SaaS com assinatura mensal (3Commas, Cryptohopper, Bitsgap,
TradeSanta, Coinrule), (2) exchange com bots integrados e sem assinatura
(Pionex, KuCoin Trading Bot), e (3) open-source self-hosted (Freqtrade, Jesse,
Hummingbot). Em 2026, a regulacao MiCA na Europa mudou as regras do jogo: bots
que operam com estrategias do provedor em contas de clientes podem ser
classificados como gestao de carteira de criptoativos, exigindo licenca. O
mercado retail continua a crescer, mas a concorrencia em precos e a
comoditizacao de features basics (DCA, grid, signals) squeezed as margens. O
gap mais interessante para o crypto-correl-bot esta em analise de derivativos
(funding rate, OI, liquidacoes), algo que nenhum bot retail oferece nativamente
com profundidade quant.

## Explicacao para criancas

Imagine que voce quer comprar e vender figurinhas o dia inteiro, mas nao consegue
ficar acordado 24 horas. Entao voce contrata um ajudante que faz isso por voce.
Esse ajudante segue regras simples que voce ensina: "compre quando o preco
cair 5%, venda quando subir 3%". Os bots comerciais sao esses ajudantes. Alguns
cobram um mesada fixa todo mes (3Commas, Cryptohopper). Outros sao de graca,
mas cobram uma pequena taxa cada vez que compram ou vendem (Pionex). E existem
ajudantes que voce mesmo constroi com pecas de Lego em casa, de graca, mas
precisa saber montar (Freqtrade). Em 2026, alguns paises disseram que o ajudante
precisa de uma licenca oficial se estiver usando as regras dele e nao as suas.

## Como funciona (o segmento de mercado)

O segmento de bots de trading retail atende traders individuais (retail) que
querem automatizar operacoes em exchanges centralizadas (CEX) e, em alguns
casos, descentralizadas (DEX). A arquitetura tipica envolve:

1. **Conexao via API:** o usuario conecta sua conta de exchange (Binance, Bybit,
   OKX, Coinbase, etc.) ao bot usando chaves de API com permissoes de leitura e
   trade, mas sem permissao de saque.

2. **Estrategias pre-configuradas:** o bot oferece templates de estrategias como
   DCA (Dollar Cost Averaging), Grid Trading, Grid Futures, Signal Bots (que
   seguem sinais de TradingView ou provedores terceiros), e Smart Trades (ordens
   avancadas com trailing stop, take profit multiplo).

3. **Execucao em nuvem:** na maioria dos casos SaaS, o bot roda nos servidores
   do provedor, 24/7, sem que o usuario precise manter seu computador ligado.
   Excecoes: Freqtrade e Jesse sao self-hosted.

4. **Monetizacao:** tres modelos principais.
   - Assinatura mensal/anual com tiers (3Commas, Cryptohopper, Bitsgap,
     TradeSanta, Coinrule).
   - Sem assinatura, com taxa de trade embutida (Pionex cobra 0.05% por trade).
   - Free e open-source, com custo de infraestrutura por conta do usuario
     (Freqtrade: ~$25 a $44/mes de VPS).

O mercado se segmenta por nivel de complexidade. No entry-level estao Pionex e
KuCoin Trading Bot, com setup em minutos e zero configuracao avancada. No
mid-market estao 3Commas, Cryptohopper, Bitsgap e TradeSanta, com mais opcoes de
customizacao, backtesting limitado, e marketplaces de sinais. No topo esta
Coinrule, com regras IF/THEN e ate 350+ templates, mas pricing que chega a
$995/mes no tier mais alto. No paralelo, Freqtrade oferece customizacao
ilimitada via Python, mas exige conhecimento tecnico.

## Estado do mercado em 2026

### Players principais e pricing

**3Commas:** lider historico do segmento SaaS. Em 2025/2026 reestruturou os
planos para tres tiers: Starter ($20/mes), Pro ($50/mes) e Expert ($140/mes).
Removeu planos bienais (de 2 anos) em marco de 2026. O plano gratuito permite
apenas portfolio tracking, sem trading real. Suporta 15+ exchanges. Diferencial:
DCA bots, Signal bots, Grid bots, SmartTrades, e backtesting com limite por
plano. URL: https://3commas.io

**Cryptohopper:** cloud SaaS com estrategia marketplace e AI Strategy Designer.
Pricing: free tier limitado, Explorer ($16.58/mes), Adventurer ($41.58/mes),
Hero ($83.25/mes). Em algumas fontes o range chega a $99 a $107.50/mes no topo.
Diferencial: marketplace de estrategias, copy trading, paper trading, AI
optimization. Suporta 16+ exchanges. URL: https://www.cryptohopper.com

**Pionex:** exchange com bots integrados, modelo diferente dos demais. 16 tipos
de bots gratuitos (Grid, DCA, Martingale, Rebalancing, etc.). Sem assinatura.
Taxa de trade de 0.05% por operacao, entre as mais baixas do mercado. KYC
obrigatorio. Copy trading disponivel para portfolios acima de $50K. URL:
https://www.pionex.com

**Bitsgap:** SaaS com foco em multi-exchange. Tres planos: Basic ($26/mes
anual, $21/mes), Advanced ($62/mes, $49/mes anual), Pro ($135/mes, $108/mes
anual). Limites crescentes de Grid bots (3, 10, 50) e DCA bots. Diferencial: AI
Portfolio Mode, reinvestimento de lucros, futures bots no Pro. Sem taxas de
trade extras alem da assinatura. URL: https://bitsgap.com

**TradeSanta:** SaaS com foco em simplicidade. Planos: Basic ($25/mes, $18/mes
com desconto), Advanced ($45/mes, $32/mes), Maximum ($90/mes, $45/mes). Suporta
7 exchanges. Diferencial: interface simples, copy trading, mobile app completo,
integracao TradingView. Limitacao: falta backtesting historico robusto. URL:
https://tradesanta.com

**Coinrule:** no-code rule builder com logica IF/THEN, 350+ templates de
estrategia, suporta crypto e acoes. Free tier limitado, planos pagos de
$39.99/mes ate $995/mes no topo. AI: CoinruleGPT para ajustar regras. Suporta
10 a 15 exchanges, 30+ com stocks. Diferencial: regra visual, multi-asset. Sem
mobile app dedicado. URL: https://coinrule.io

**KuCoin Trading Bot:** integrado a exchange KuCoin, sem custo de assinatura.
Bots de Grid, DCA, e Futures Grid gratuitos para usuarios da exchange. Modelo
similar ao Pionex: taxa de trade da exchange. URL: https://www.kucoin.com

### Open-source: a alternativa

**Freqtrade:** o maior bot open-source de crypto, em Python, licenca GPL-3.0.
Suporta 20+ exchanges via CCXT, spot e futures. Estrategias em Python com
backtesting completo, hyperopt (otimizacao de hyperparametros), e FreqAI para
machine learning. Custo real: $25 a $44/mes de VPS + tempo de setup (10 a 40
horas) e manutencao (2 a 5 horas/mes). A estrategia comunitaria
NostalgiaForInfinity tem ~2.9K stars no GitHub. Diferencial vs SaaS:
customizacao ilimitada, data ownership, chaves de API nunca saem do seu
servidor. Versao 2026.6 em julho de 2026. URL: https://www.freqtrade.io

**Jesse:** framework Python para backtesting e trading, foco em qualidade de
backtest. Menor comunidade que Freqtrade, mas abordagem mais rigorosa em
simulacao. URL: https://docs.jesse.trade

**Hummingbot:** open-source focado em market making e arbitragem, ideal para
estrategias de alta frequencia. URL: https://hummingbot.org

### Tendencias e noticias recentes

1. **Consolidacao de planos:** 3Commas removeu planos bienais e simplificou para
   3 tiers em 2025/2026, sinal de foco em retencao e reducao de complexidade
   administrativa.

2. **Comoditizacao de features basics:** DCA e Grid bots sao agora standard em
   praticamente todas as plataformas. O diferencial migrou para AI, copy
   trading, e integracoes com TradingView.

3. **Regulacao MiCA (Europa):** em janeiro de 2026, o tribunal administrativo
   federal da Austria confirmou que um bot de trading operado pelo provedor com
   estrategias do provedor em contas de clientes constitui "gestao de carteira
   de criptoativos" sob MiCA, exigindo licenca de CASP. O periodo transitorio
   de MiCA expira em 1 de julho de 2026: qualquer CASP sem licenca deve cessar
   operacoes para clientes da UE. Bots non-custodial (que so executam ordens do
   usuario com suas proprias chaves) podem ficar fora do escopo, mas bots que
   gerenciam estrategias para clientes estao no escopo.

4. **Copy trading sob escrutinio:** ESMA publicou guidance classificando copy
   trading de cripto como potencialmente exigindo autorizacao sob MiCA/MiFID II,
   dependendo do grau de automatizacao e quem controla a estrategia.

5. **IA generativa entrando nos bots:** 3Commas lancou AI Assistant (com credits
   mensais), Cryptohopper tem AI Strategy Designer, TradeSanta tem plugin
   ChatGPT, Coinrule tem CoinruleGPT. A IA ainda e usada para auxiliar
   configuracao, nao para decisao autonoma de trade.

## Ferramentas e APIs disponiveis

| Nome | Fundacao | Pricing | Publico-alvo | Diferencial | URL |
| --- | --- | --- | --- | --- | --- |
| 3Commas | ~2017 | $20 a $140/mes | Retail e pro-sumers | DCA/Signal/Grid bots, SmartTrades, 15+ exchanges | https://3commas.io |
| Cryptohopper | ~2017 | Free a ~$99/mes | Retail com interesse em AI | Marketplace de estrategias, AI Strategy Designer | https://www.cryptohopper.com |
| Pionex | ~2019 | Free (0.05% taxa) | Retail iniciante | 16 bots gratis integrados na exchange | https://www.pionex.com |
| Bitsgap | ~2018 | $26 a $135/mes | Retail mid-market | AI Portfolio Mode, multi-exchange, futures bots | https://bitsgap.com |
| TradeSanta | ~2018 | $25 a $90/mes | Retail que quer simplicidade | Interface simples, copy trading, mobile completo | https://tradesanta.com |
| Coinrule | ~2018 | Free a $995/mes | Retail no-code multi-asset | Rule builder IF/THEN, 350+ templates, stocks+crypto | https://coinrule.io |
| KuCoin Trading Bot | ~2017 | Free (taxas da exchange) | Usuarios da KuCoin | Integrado na exchange, sem custo extra | https://www.kucoin.com |
| Freqtrade | ~2019 (open-source) | Free + ~$25-44/mes VPS | Desenvolvedores e quants | Python, FreqAI, hyperopt, data ownership total | https://www.freqtrade.io |
| Jesse | ~2020 (open-source) | Free + VPS | Quants que valorizam backtest rigoroso | Backtesting de alta fidelidade | https://docs.jesse.trade |
| Hummingbot | ~2019 (open-source) | Free + VPS | Market makers e arbitrage | Market making e arbitragem HF | https://hummingbot.org |

## Por que importa para o crypto-correl-bot

### Oportunidade

O mercado retail de bots e maduro em automacao basica (DCA, grid) mas imaturo em
analise de derivativos. Nenhum dos bots comerciais listados oferece analise
profunda de funding rate, open interest, liquidacoes, ou correlacoes
cross-asset como recurso nativo de geracao de sinal. 3Commas tem Signal bots,
mas dependem de fontes externas (TradingView, provedores terceiros). O
crypto-correl-bot pode ocupar esse nicho: um bot que nao so executa, mas usa
dados de derivativos (funding rate anomalo, OI divergence, liquidacao cascades)
como alpha signal.

### Gaps identificados

1. **Falta de dados de derivativos nos bots retail:** o retail trader que usa
   3Commas ou Cryptohopper nao tem acesso integrado a liquidation heatmaps, OI
   historical, ou funding rate arbitrage. Esses dados estao em plataformas
   separadas (Coinglass, Laevitas) e exigem troca de contexto manual.

2. **Backtesting fraco na maioria SaaS:** exceto Freqtrade, nenhum bot retail
   oferece backtesting verdadeiramente robusto com survivorship bias control e
   slippage realista. TradeSanta e Coinrule sequer tem backtesting historico.

3. **MiCA criando espaco para bots non-custodial:** com a pressao regulatoria
   sobre bots que gerenciam estrategias de clientes, existe oportunidade para
   ferramentas que sao explicitamente non-custodial e self-hosted (como
   Freqtrade), ou que fornecem dados/sinais sem executar trades.

4. **IA ainda e superficie, nao nucleo:** os "AI features" atuais sao
   assistentes de configuracao, nao motores de decisao. Existe espaco para
   ML/RL real integrado a dados de derivativos, algo que FreqAI comeca a explorar
   mas ainda e tecnico demais para retail.

### Onde podemos competir ou aprender

- **Aprender com Freqtrade:** arquitetura, CCXT integration, FreqAI como modulo
  de ML, e a comunidade NostalgiaForInfinity como exemplo de estrategia
  open-source de alta qualidade.
- **Aprender com Coinglass:** como agregar e apresentar dados de derivativos de
  forma acessivel. O crypto-correl-bot pode internalizar essa camada de dados.
- **Competir no nicho de derivativos:** posicionar como "o bot que entende
  funding rate e liquidacoes", um segmento que 3Commas e Cryptohopper nao
  atendem bem.
- **Evitar o modelo SaaS de assinatura crowded:** o mercado de $20 a $140/mes
  esta saturado. O diferencial precisa ser dados + correlacao, nao mais um DCA
  bot.

## Referencias

1. 3Commas. Pricing Plans. https://3commas.io/pricing
2. 3Commas Help Center. Available Subscription Plans.
   https://help.3commas.io/en/articles/8420093
3. 3Commas Help Center. Subscription Plan changes for Existing Users (mar 2026).
   https://help.3commas.io/en/articles/12569512
4. TradingToolsHub. Cryptohopper vs Pionex (2026).
   https://tradingtoolshub.com/compare/cryptohopper-vs-pionex/
5. Bitsgap Blog. Bitsgap vs Pionex.
   https://bitsgap.com/blog/bitsgap-vs-pionex-trading-bot-review-which-is-right-for-you
6. XCryptoBot. Best Crypto Trading Bots 2026 (atualizado dez 2025).
   https://xcryptobot.com/bot-comparison
7. AlexBobes. Freqtrade vs 3Commas vs Cryptohopper (2026).
   https://alexbobes.com/crypto/freqtrade-vs-3commas-vs-cryptohopper/
8. OpenAltFinder. Freqtrade: Open Source 3Commas Alternative.
   https://openaltfinder.com/tools/freqtrade
9. TradeSanta. Pricing. https://tradesanta.com/pricing
10. TradeSanta Blog. Coinrule vs TradeSanta (2026).
    https://tradesanta.com/blog/coinrule-vs-tradesanta
11. Sabadello Legal. MiCAR: Crypto Trading Bot as Portfolio Management (jan
    2026). https://sabadello.legal/news/2026-03-21-micar-crypto-trading-bot-portfolio-management/
12. Skadden. Update on MiCA Implementation: Copy Trading (mai 2025).
    https://www.skadden.com/insights/publications/2025/05/update-on-mica-implementation
13. ESMA. Statement on the end of transitional periods under MiCA (abr 2026).
    https://www.esma.europa.eu/sites/default/files/2026-04/ESMA75-113276571-1679_Statement_on_the_end_of_transitional_periods_under_MiCA.pdf
