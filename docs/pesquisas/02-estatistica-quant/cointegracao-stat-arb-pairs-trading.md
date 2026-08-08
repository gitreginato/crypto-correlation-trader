# Topico: Cointegracao, Stat Arb e Pairs Trading

**Data:** 2026-07-15
**Categoria:** Estatistica / Quant

## TL;DR

Cointegracao e correlacao sao conceitos fundamentalmente diferentes: correlacao mede co-movimento de returns, cointegracao mede se duas series de preco nao-estacionarias compartilham um equilibrio de longo prazo. Pairs trading explora desvios desse equilibrio: o spread entre dois ativos cointegrados e estacionario e reverte a media. Os testes principais sao ADF (univariado), Engle-Granger (2-step) e Johansen (multivariado). O half-life do spread via Ornstein-Uhlenbeck define a velocidade de mean reversion e o horizonte da estrategia. Em cripto, pares como BTC/ETH e ETH/LTC mostram cointegracao robusta, mas regime breaks e halting sao riscos criticos.

## Explicacao para criancas

Imagine dois amigos que caminham juntos por uma cidade grande. As vezes um vai um pouco na frente, outras o outro acelera, mas eles sempre voltam a ficar lado a lado porque combinaram de ir juntos. A distancia entre eles (o "spread") oscila mas nao cresce indefinidamente. Se um se afasta muito, voce pode apostar que ele vai esperar o outro. Cointegracao e isso: dois precos que se afastam mas sempre voltam ao equilibrio. Correlacao seria se os dois sempre acelerassem e desacelerassem ao mesmo tempo, o que e diferente.

## Como funciona tecnicamente

### Cointegracao vs correlacao

| Aspecto | Correlacao | Cointegracao |
|---|---|---|
| O que mede | Co-movimento de returns | Equilibrio de longo prazo de precos |
| Serie analisada | Returns (estacionarios) | Precos (nao-estacionarios) |
| Dimensao | Instantanea | Longo prazo |
| Se corr = 0 | Sem relacao linear | Pode ainda ser cointegrado |
| Exemplo | BTC e ETH sobem juntos hoje | BTC e ETH nao divergem indefinidamente |

Duas series podem ter correlacao baixa e ser cointegradas, ou correlacao alta e nao ser cointegradas. Exemplo classico: um random walk X e Y = X + ruido. Correlacao dos returns pode ser baixa, mas Y e X sao cointegradas porque Y - X e estacionario.

**Definicao formal**: duas series I(1) (integradas de ordem 1, ou seja, com raiz unitaria) sao cointegradas se existe um vetor beta tal que beta' * X_t e estacionario (I(0)). Em outras palavras, existe uma combinacao linear dos precos que e estacionaria.

### O spread de pairs trading

Para dois ativos X e Y, o spread e:

    S_t = alpha + beta * X_t - Y_t

Onde:
- beta e o hedge ratio (razao de cobertura), estimado por OLS de Y contra X.
- alpha e o intercepto.
- S_t deveria ser estacionario (I(0)) se X e Y sao cointegrados.

O z-score do spread normaliza o sinal de trading:

    z_t = (S_t - mean(S)) / std(S)

Regras tipicas de trading:
- Entrar short no spread quando z > +2 (spread muito alto, esperar regressao).
- Entrar long no spread quando z < -2 (spread muito baixo).
- Sair quando |z| < 0.5 (voltou perto da media).

### Teste 1: ADF (Augmented Dickey-Fuller)

Testa a hipotese nula de raiz unitaria (nao-estacionario) contra a alternativa de estacionariedade.

    H0: serie tem raiz unitaria (nao-estacionaria)
    H1: serie e estacionaria

Aplicado ao spread S_t: se rejeitamos H0, o spread e estacionario, e os pares sao cointegrados.

O teste ADF estima a regressao:

    Delta S_t = alpha + rho * S_{t-1} + sum(gamma_i * Delta S_{t-i}) + epsilon_t

Se rho < 0 e significativo, S_t e estacionario. A estatistica de teste e o t-statistic de rho.

```python
from statsmodels.tsa.stattools import adfuller

result = adfuller(spread, maxlag=1)
adf_stat = result[0]
p_value = result[1]
# p_value < 0.05 => rejeita H0 => spread estacionario => cointegrado
```

**Armadilha**: ADF tem baixo poder em amostras pequenas e em series com raiz unitaria proxima (rho proximo de 0). Em cripto, com volatilidade extrema, o teste pode falhar em detectar cointegracao real.

### Teste 2: Engle-Granger (2-step)

1. Estimar a regressao de cointegracao: Y_t = alpha + beta * X_t + epsilon_t (OLS).
2. Aplicar ADF nos residuos epsilon_t.

Se os residuos sao estacionarios, X e Y sao cointegrados com vetor (beta, -1).

**Limitacao**: Engle-Granger assume que ha exatamente uma relacao de cointegracao e que X e a variavel independente. Se trocar X e Y, pode obter resultado diferente. Tambem nao funciona bem com mais de duas variaveis.

```python
from statsmodels.tsa.stattools import coint

# Engle-Granger via statsmodels
coint_t, p_value, crit_values = coint(y, x)
# p_value < 0.05 => cointegrados
```

### Teste 3: Johansen

Teste multivariado baseado em Vector Error Correction Model (VECM). Permite detectar multiple cointegrating relationships e nao exige escolher uma variavel dependente.

Para um VAR(p) com k variaveis I(1):

    Delta X_t = Pi * X_{t-1} + sum(Gamma_i * Delta X_{t-i}) + epsilon_t

O rank de Pi (matriz k x k) determina o numero de relacoes de cointegracao:
- rank(Pi) = 0: nenhuma cointegracao.
- rank(Pi) = r: existem r relacoes de cointegracao.

Johansen usa dois testes: trace test e max eigenvalue test.

```python
from statsmodels.tsa.vector_ar.vecm import coint_johansen

result = coint_johansen(data, det_order=0, k_ar_diff=1)
# result.eig: autovalores
# result.lr1: estatistica trace
# result.lr2: estatistica max eigenvalue
# Comparar com critical values em result.cvt
```

**Vantagem do Johansen**: encontra todas as relacoes de cointegracao simultaneamente, sem assumir qual variavel e dependente. Para portfolios com 3+ ativos, e o teste correto.

### Teste 4: KSS (Kapetanios-Snell-Shin)

Testa cointegracao nao-linear. Util quando a mean reversion e assimetrica (spread reverte mais rapido em uma direcao que na outra). Estudos de 2025 em cripto usaram KSS como complemento ao Johansen.

### Half-life via Ornstein-Uhlenbeck

O processo Ornstein-Uhlenbeck (OU) modela a dinamica do spread:

    dS_t = theta * (mu - S_t) dt + sigma dW_t

Onde:
- theta: velocidade de mean reversion.
- mu: media de longo prazo.
- sigma: volatilidade do spread.
- W_t: movimento browniano.

O half-life e o tempo para o spread decair a metade do desvio em relacao a media:

    half_life = ln(2) / theta

Estimacao por regressao AR(1):

    Delta S_t = a + b * S_{t-1} + epsilon_t

    theta = -b
    half_life = -ln(2) / b    (quando b < 0)

Se b >= 0, o spread nao e mean-reverting (random walk ou trending), half_life e indefinido.

```python
import numpy as np
import statsmodels.api as sm

def half_life(spread: pd.Series) -> float:
    """Estimate half-life of mean reversion via AR(1) regression."""
    lag = spread.shift(1).dropna()
    delta = spread.diff().dropna()
    lag, delta = lag.align(delta, join='inner')
    model = sm.OLS(delta, sm.add_constant(lag)).fit()
    theta = -model.params.iloc[1]
    if theta <= 0:
        return float('inf')  # not mean-reverting
    return np.log(2) / theta
```

**Interpretacao para trading**:
- half_life < 5 dias: reversion rapida, mas pode ser ruido. Held curto.
- half_life 5-30 dias: zona ideal para pairs trading.
- half_life > 100 dias: reversion lenta demais, capital preso por muito longo.
- half_life = infinito: nao ha mean reversion, nao tradar.

### Riscos do stat arb em cripto

1. **Regime breaks**: a relacao de cointegracao pode quebrar. Um fork, uma regulacao, ou uma mudanca fundamental no token pode destruir a cointegracao permanentemente. A estrategia continua abrindo posicoes baseada em um equilibrio que nao existe mais.

2. **Halting e liquidacao**: exchanges cripto podem pausar withdraw/deposit, e derivativos podem ser liquidados forcadamente. Se um lado do par e halted, o spread diverge e voce nao pode fechar a posicao.

3. **Custos de transacao**: cripto tem fees de trading + slippage + funding rate (em perps). O spread precisa reverter mais do que o custo total para ser lucrativo.

4. **Counterparty risk**: se voce opera em uma exchange e ela quebra (FTX), voce perde ambos os lados do par.

5. **Non-stationarity do hedge ratio**: beta muda ao longo do tempo. Usar Kalman filter para estimar beta dinamico e melhor que OLS estatico.

### Estrutura completa de pairs trading

```python
def pairs_trading_pipeline(x: pd.Series, y: pd.Series) -> dict:
    """Complete pairs trading analysis pipeline."""
    # 1. Testar cointegracao
    coint_t, p_value, _ = coint(y, x)
    is_cointegrated = p_value < 0.05

    if not is_cointegrated:
        return {"cointegrated": False}

    # 2. Estimar hedge ratio (OLS)
    model = sm.OLS(y, sm.add_constant(x)).fit()
    alpha, beta = model.params

    # 3. Calcular spread
    spread = y - alpha - beta * x

    # 4. Half-life
    hl = half_life(spread)

    # 5. Z-score
    z_score = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()

    return {
        "cointegrated": True,
        "hedge_ratio": beta,
        "half_life": hl,
        "z_score_latest": z_score.iloc[-1],
        "spread": spread,
    }
```

## Estado do mercado em 2026

A pesquisa em cointegracao de cripto amadureceu significativamente:

1. **Resultados empiricos solidos**: um estudo de 2026 no IJSRA examinou BTC, ETH, LTC e XRP com dados diarios de 2022 a 2024 usando Engle-Granger e Johansen. Encontrou cointegracao forte entre BTC-ETH e ETH-LTC, com Sharpe ratios de 1.58 a 2.45. A estrategia BTC-ETH teve retorno anualizado de 16.34% com volatilidade de 8.45%, contra buy-and-hold de BTC com volatilidade de 54.67%. Beta de 0.09-0.18 confirma a natureza market-neutral.

2. **High-frequency cointegration**: uma tese de Erasmus Rotterdam aplicou EG2SLS + Johansen em dados de alta frequencia com 16 semanas de backtest. A versao assistida por Johansen superou EG2SLS puro: retorno semanal de 6.81% vs 5.97%, incluindo custos de transacao. Usaram Granger causality para pre-filtrar pares com maior probabilidade de cointegracao (lagging assets tendem a ser cointegrados com leaders).

3. **Dynamic cointegration com OU**: um paper no arXiv implementou estrategia dinamica com Engle-Granger, KSS e Johansen, calibrando a velocidade de mean reversion via OU para obter o half-life usado na selecao de pares e na estimacao da janela look-back. Usaram uma colecao numerosa de moedas para formular o spread do modelo, melhorando a rentabilidade risk-adjusted. O max drawdown foi razoavelmente baixo.

4. **Copula-based pairs trading**: um paper de dezembro 2025 no Financial Innovation (Springer) introduziu uma estrategia baseada em copulas para pares cointegrados de cripto. Combina testes de cointegracao linear e nao-linear, coeficiente de correlacao, e fitting de familias de copulas. O metodo superou estrategias baseadas apenas em cointegracao ou apenas em copulas em rentabilidade e returns risk-adjusted.

5. **Kalman filter para hedge ratio dinamico**: praticas modernas substituem OLS estatico por Kalman filter para estimar beta que varia no tempo. Isso captura mudancas na relacao de cointegracao sem precisar re-estimar periodicamente.

## Ferramentas e APIs disponiveis

| Ferramenta | Uso | Notas |
|---|---|---|
| `statsmodels.tsa.stattools.coint` | Engle-Granger 2-step | Univariado, rapido |
| `statsmodels.tsa.stattools.adfuller` | ADF nos residuos | Teste de raiz unitaria |
| `statsmodels.tsa.vector_ar.vecm.coint_johansen` | Johansen multivariado | Multiple cointegrating vectors |
| `statsmodels.tsa.stattools.zivot_andrews` | ADF com break estrutural | Detecta cointegracao com regime break |
| `arch.unitroot` | ADF, KPSS, Phillips-Perron | Mais flexivel que statsmodels |
| `hmmlearn` | Regime switching no spread | Detectar mudancas de regime |
| `pykalman` | Kalman filter para beta dinamico | Hedge ratio time-varying |
| `arbitragelab` | OU model, half-life, trading rules | Biblioteca especializada em stat arb |

Bibliotecas complementares:
- `statsmodels.tsa.stattools.grangercausalitytests`: para pre-filtrar pares via Granger causality.
- `copulae` (Python): para pairs trading baseado em copulas.
- `vectorbt`: para backtest de pairs trading com baixo look-ahead bias.

## Por que importa para o crypto-correl-bot

**O que ja temos no projeto**:
- Calculo de ADF (mencionado no escopo do bot).
- Calculo de half-life (mencionado no escopo do bot).
- Correlacao entre pares (Pearson, Spearman, Kendall).

**O que falta ou poderia ser adicionado**:
1. **Teste de Johansen**: o bot provavelmente so tem ADF e Engle-Granger. Johansen e essencial para cointegracao multivariada (3+ ativos). Sem ele, o bot nao consegue identificar baskets cointegradas, apenas pares.
2. **Pairs trading pipeline completo**: integrar cointegracao + half-life + z-score em um modulo de estrategia. O bot tem as pecas (ADF, half-life) mas falta o pipeline de stat arb que as conecta.
3. **Kalman filter para hedge ratio dinamico**: OLS estatico e limitado. Kalman filter adapta beta em tempo real, crucial em cripto onde a relacao muda.
4. **Kill switch por regime break**: se a cointegracao quebra (ADF deixa de rejeitar H0), a estrategia deve parar de abrir novas posicoes imediatamente. Implementar monitoramento continuo da cointegracao.
5. **Copula-based pairs**: como upgrade de research, testar copulas para capturar dependencia nao-linear que a cointegracao linear nao captura.
6. **Pre-filtro por Granger causality**: antes de testar cointegracao em todos os pares (O(N^2)), usar Granger causality para reduzir o conjunto de candidatos. Assets que nao Granger-cause uns aos outros raramente sao cointegrados.
7. **Half-life como meta-parametro**: usar o half-life para definir a janela do z-score e o horizonte de held da posicao. Spread com half-life de 10 dias nao deveria usar z-score de 60 dias.

## Referencias

1. Statistical Arbitrage Strategies Using Cointegration Analysis in Cryptocurrency Markets (IJSRA, 2026). https://doi.org/10.30574/ijsra.2026.18.2.0283
2. High-Frequency Trading of Cryptocurrencies Through Short-Term Cointegration Pairs-Trading Strategies (Erasmus Rotterdam, tese). https://thesis.eur.nl/pub/47732/Bruijn-de.pdf
3. Evaluation of Dynamic Cointegration-Based Pairs Trading Strategy in the Cryptocurrency Market (arXiv). https://arxiv.org/pdf/2109.10662
4. Copula-based trading of cointegrated cryptocurrency Pairs (Financial Innovation, Springer, 2025). https://ideas.repec.org/a/spr/fininn/v11y2025i1d10.1186_s40854-024-00702-7.html
5. ssanin82 - Cointegration-Based Pairs Trading Strategy (Binance Futures, Engle-Granger). https://github.com/ssanin82/strat-test-cointegration
6. RiskLabAI - Closed-form optimal OU trading rules (Lipton-Lopez de Prado). https://github.com/RiskLabAI/RiskLabAI.py
7. arbitragelab - Trading Under the Ornstein-Uhlenbeck Model (half-life). https://hudson-and-thames-arbitragelab.readthedocs-hosted.com/en/latest/optimal_mean_reversion/ou_model.html
8. kshitijbhandari - Statistical Arbitrage com OU + Kalman filter (S&P 500). https://github.com/kshitijbhandari/Statistical-Arbitrage-Market-Neutral-Spread-Trading-on-S-P-500-Cointegrated-Equities
