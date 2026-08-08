# Topico: GARCH e Volatilidade Condicional

**Data:** 2026-07-15
**Categoria:** Estatistica / Quant

## TL;DR

GARCH (Generalized Autoregressive Conditional Heteroskedasticity) modela volatilidade que muda ao longo do tempo, capturando o fenomeno de volatility clustering: periodos de alta volatilidade tendem a ser seguidos por mais alta volatilidade. O modelo GARCH(1,1) e o workhorse da finance, mas EGARCH e GJR-GARCH capturam o leverage effect (choques negativos aumentam volatilidade mais que positivos). Em cripto, GARCH supera LSTM em previsao de volatilidade de curto prazo, com 32% menos MAE. Aplicacoes principais: position sizing dinamico, pricing de opcoes, e calculo de VaR/CVaR. A biblioteca arch e o padrao Python para estimacao e forecasting.

## Explicacao para criancas

Imagine que o clima de uma cidade tem dias calmos e dias tempestuosos. A tempestade de hoje nao vem do nada: ela costuma vir depois de varios dias de instabilidade crescente. GARCH e um modelo que aprende esse padrao: ele olha a volatilidade recente e os choques recentes para prever quao tempestuoso sera amanha. Se hoje teve um choque grande, amanha provavelmente tambem sera turbulento. Se esta calmo ha dias, provavelmente continuara calmo. Em cripto, isso e especialmente util porque os "choques" sao frequentes e violentos.

## Como funciona tecnicamente

### Volatilidade condicional vs incondicional

**Volatilidade incondicional**: a variancia de longo prazo da serie, um numero constante. Assume que a volatilidade nao muda.

**Volatilidade condicional**: a variancia no instante t, dado o historico ate t-1. Denotada sigma_t^2 = Var(epsilon_t | F_{t-1}), onde F_{t-1} e a informacao disponivel ate t-1.

Series financeiras exibem volatility clustering: variancia condicional muda ao longo do tempo, com periodos de alta e baixa volatilidade agrupados. Modelos de volatilidade constante (OLS, ARMA) ignoram isso. GARCH modela essa dinamica.

### ARCH(q)

O modelo ARCH (Autoregressive Conditional Heteroskedasticity) de Engle (1982) modela a variancia condicional como funcao dos choques passados ao quadrado:

    epsilon_t = sigma_t * z_t,  z_t ~ N(0,1)

    sigma_t^2 = omega + sum(alpha_i * epsilon_{t-i}^2)  para i = 1..q

Onde:
- epsilon_t: retorno (ou residuo) em t.
- sigma_t^2: variancia condicional em t.
- z_t: ruido branco (normal, t-Student, etc.).
- omega, alpha_i: parametros a estimar.

**Limitacao**: ARCH(q) precisa de q grande para capturar persistencia longa, o que leva a muitos parametros.

### GARCH(p,q)

Bollerslev (1986) generalizou ARCH adicionando termos AR da variancia passada:

    sigma_t^2 = omega + sum(alpha_i * epsilon_{t-i}^2) + sum(beta_j * sigma_{t-j}^2)

GARCH(1,1), o modelo mais usado:

    sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2

Condicoes:
- omega > 0, alpha >= 0, beta >= 0 (positividade da variancia).
- alpha + beta < 1 (estacionariedade).
- alpha + beta proximo de 1 indica alta persistencia (volatility clustering forte).

**Interpretacao dos parametros**:
- alpha: sensibilidade a choques recentes (news impact). Alto alpha = choques aumentam volatilidade rapidamente.
- beta: persistencia da volatilidade. Alto beta = volatilidade decai lentamente.
- alpha + beta: persistencia total. Em cripto, tipicamente 0.95-0.99 (muito persistente).
- omega: variancia de longo prazo. A variancia incondicional e omega / (1 - alpha - beta).

### Forecasting com GARCH(1,1)

Previsao de 1 passo a frente:

    sigma_{t+1}^2 = omega + alpha * epsilon_t^2 + beta * sigma_t^2

Previsao de h passos a frente (recursiva):

    sigma_{t+h}^2 = omega * sum((alpha+beta)^i) + (alpha+beta)^h * (sigma_{t+1}^2 - omega/(1-alpha-beta))

Para h -> infinito, sigma_{t+h}^2 -> omega / (1 - alpha - beta) (variancia incondicional).

### EGARCH (Exponential GARCH)

Nelson (1991) modela log(variancia), garantindo positividade sem restricoes de parametro:

    log(sigma_t^2) = omega + alpha * (|z_{t-1}| - E[|z_{t-1}|]) + gamma * z_{t-1} + beta * log(sigma_{t-1}^2)

O termo gamma captura o leverage effect (assimetria):
- gamma < 0: choques negativos aumentam volatilidade mais que positivos (typical em equities).
- gamma = 0: sem assimetria (GARCH simetrico).
- gamma > 0: choques positivos aumentam mais (raro, mas possivel em cripto em bull runs).

**Vantagem**: sem restricoes de nao-negatividade nos parametros. Log(variancia) e sempre positivo.

### GJR-GARCH (Glosten-Jagannathan-Runkle)

Modela a assimetria via indicator function:

    sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + gamma * I(epsilon_{t-1} < 0) * epsilon_{t-1}^2 + beta * sigma_{t-1}^2

Onde I(.) e a funcao indicadora (1 se verdadeiro, 0 caso contrario). gamma captura o excesso de impacto de choques negativos.

### TGARCH (Threshold GARCH)

Similar ao GJR-GARCH mas modela a volatilidade (desvio padrao) ao inves da variancia:

    sigma_t = omega + alpha * |epsilon_{t-1}| + gamma * I(epsilon_{t-1} < 0) * |epsilon_{t-1}| + beta * sigma_{t-1}

### CGARCH (Component GARCH)

Decompoe a variancia em componente permanente (longo prazo) e transitoria (curto prazo):

    sigma_t^2 = q_t + alpha * (epsilon_{t-1}^2 - q_{t-1}) + beta * (sigma_{t-1}^2 - q_{t-1})

    q_t = omega + rho * (q_{t-1} - omega) + xi * (epsilon_{t-1}^2 - sigma_{t-1}^2)

Onde q_t e a componente de longo prazo (trend da volatilidade). Util para capturar ciclos de volatilidade.

### Distribuicoes de inovacao

GARCH assume que z_t segue alguma distribuicao. A escolha importa muito em cripto:

| Distribuicao | Caudas | Quando usar |
|---|---|---|
| Normal | Leves | Inadequado para cripto |
| t-Student | Pesadas (parametro dof) | Padrao para cripto |
| Skew-t (Hansen) | Pesadas + assimetricas | Cripto com skew |
| GED | Pesadas | Alternativa ao t-Student |

Em cripto, t-Student com baixos graus de liberdade (dof 3-7) tipicamente e o melhor fit. BTC retem caudas pesadas condicionais genuinas mesmo apos modelar a volatilidade, enquanto equities tendem a ter residuais near-Gaussian apos condicionar.

### Estimacao e diagnostico

A estimacao e por Maximum Likelihood (MLE). O procedimento:

1. Especificar o modelo de media (ex: AR(1)-GARCH(1,1)).
2. Estimar os parametros por MLE.
3. Verificar os residuos padronizados: z_t = epsilon_t / sigma_t. Devem ser i.i.d. (sem autocorrelacao, sem ARCH effects remanescentes).
4. Teste de Ljung-Box nos residuos e nos residuos ao quadrado.
5. Teste ARCH-LM nos residuos padronizados (nao deve rejeitar H0 de no ARCH effects).

### Aplicacao 1: Position sizing dinamico

A volatilidade condicional sigma_t permite ajustar o tamanho da posicao inversamente:

    position_size_t = target_volatility / sigma_t

Se a volatilidade prevista aumenta, o tamanho da posicao diminui. Isso mantem o risco constante ao longo do tempo.

### Aplicacao 2: VaR/CVaR

VaR com GARCH:

    VaR_t = mu_t + sigma_t * z_alpha

Onde z_alpha e o quantil alpha da distribuicao de inovacao (ex: t-Student). Isso da um VaR dinamico que responde a mudancas de volatilidade, mais preciso que VaR com volatilidade constante.

### Aplicacao 3: Options pricing

A volatilidade condicional prevista e usada como input para pricing de opcoes (Black-Scholes com volatilidade GARCH, ou modelos GARCH-option pricing diretos).

### Código Python com arch

```python
from arch import arch_model

def fit_garch(returns: pd.Series, dist: str = 't') -> dict:
    """Fit GARCH(1,1) with t-Student innovations."""
    model = arch_model(
        returns * 100,  # escalar para convergencia
        mean='AR',
        lags=1,
        vol='GARCH',
        p=1, q=1,
        dist=dist
    )
    result = model.fit(disp='off')

    # Forecast 1 passo a frente
    forecast = result.forecast(horizon=1, reindex=False)
    cond_mean = forecast.mean.iloc[-1, 0] / 100
    cond_var = forecast.variance.iloc[-1, 0] / 10000
    cond_vol = np.sqrt(cond_var)

    return {
        "params": result.params,
        "cond_vol": cond_vol,
        "log_likelihood": result.loglikelihood,
        "aic": result.aic,
        "bic": result.bic,
    }

def fit_egarch(returns: pd.Series) -> dict:
    """Fit EGARCH(1,1) with t-Student innovations."""
    model = arch_model(
        returns * 100,
        vol='EGARCH',
        p=1, q=1,
        dist='t'
    )
    result = model.fit(disp='off')
    return {"params": result.params, "aic": result.aic}
```

### Walk-forward validation

Para evitar look-ahead bias, re-estimar o modelo periodicamente:

```python
def walk_forward_garch(
    returns: pd.Series,
    window: int = 252,
    refit_every: int = 21
) -> pd.Series:
    """Walk-forward GARCH forecasting with periodic refit."""
    forecasts = []
    for i in range(window, len(returns), refit_every):
        train = returns.iloc[i-window:i]
        model = arch_model(train * 100, vol='GARCH', p=1, q=1, dist='t')
        result = model.fit(disp='off')
        # Forecast para os proximos refit_every periodos
        f = result.forecast(horizon=refit_every, reindex=False)
        vol_forecast = np.sqrt(f.variance.values[0]) / 100
        forecasts.extend(vol_forecast)
    return pd.Series(forecasts[:len(returns)-window],
                     index=returns.index[window:])
```

### Armadilhas

1. **Escala dos dados**: GARCH converge melhor com returns escalados (x100). Se os returns sao em decimal (0.01 = 1%), os parametros podem ser muito pequenos e o otimizador falha.

2. **Distribuicao normal em cripto**: usar inovacoes normais em cripto subestima drasticamente a probabilidade de eventos extremos. Sempre usar t-Student ou skew-t.

3. **Estacionariedade**: GARCH exige que os returns sejam estacionarios. Se ha drift significativo, remover primeiro (usar mean='AR' ou de-trend).

4. **Refit frequency**: re-estimar a cada barra e computacionalmente caro. Re-estimar raramente demais (mensal) perde adaptabilidade. Para dados diarios, refit semanal ou a cada 21 barras e o equilibrio tipico.

5. **Convergencia**: GARCH pode nao convergir com maus starting values ou dados problematicos. Verificar `result.convergence_flag`.

6. **Persistencia proxima de 1**: se alpha + beta ~ 1, a volatilidade e quase non-stationary (IGARCH). Isso e comum em cripto e significa que shocks tem efeito permanente. O forecast de longo prazo nao converge para a variancia incondicional.

## Estado do mercado em 2026

1. **GARCH supera LSTM em volatilidade**: um estudo de 2026 (TildAlice) comparou GARCH(1,1) vs LSTM para previsao de volatilidade de BTC em dados diarios de 2017 a 2025. GARCH teve 32% menos MAE que LSTM. O modelo de 1986 superou a rede neural porque volatility clustering e um padrao simples e quebras de regime em BTC prejudicam a generalizacao do LSTM. GARCH e mais rapido e interpretavel. LSTM pode vencer com dados de alta frequencia, features exogenas, ou previsao multi-passo, mas para variancia diaria GARCH e superior.

2. **GARCH(3,3) pode superar GARCH(1,1) em BTC**: um paper de junho 2025 no SSRN analisou BTC de 2014 a 2024 e encontrou que GARCH(3,3) teve o melhor fit por AIC, BIC e MSE. O modelo AR(2)-GARCH(1,1) tambem performou bem, com autocorrelacao negativa significativa nos returns e forte persistencia de volatilidade. Forecasts mostram volatilidade crescente no horizonte, refletindo incerteza crescente. O BTC teve volatilidade anualizada media de 68%, aproximadamente 4x o S&P 500.

3. **GJR-GARCH com skew-t para cripto**: o repositorio garch-risk-analytics (Aneesh2409, 2025) implementa GJR-GARCH(1,1) rolling com inovacoes t-Student e skew-t de Hansen, com walk-forward validation. Para BTC, os graus de liberdade do t-Student sao baixos e estaveis, indicando caudas condicionais genuinamente pesadas. Para equities, os dof sao grandes e instaveis, indicando que as caudas sao absorvidas pela volatilidade condicional.

4. **HAR (Heterogeneous Autoregressive) models**: o framework GARCH-HAR (HolyFot, 2025) compara modelos GARCH-family com HAR-family (realized volatility). HAR decomponde a volatilidade em componentes diaria, semanal e mensal. Variantes incluem HAR-RS (semivariances) e HAR-CJ (continuous-jump decomposition). Para cripto, HAR com dados intradiarios pode superar GARCH em horizontes medios.

5. **Model checking: Kupiec e Christoffersen**: praticas modernas validam forecasts de volatilidade e VaR com testes de coverage (Kupiec POF), independence (Christoffersen), e joint conditional coverage. O repositorio garch-risk-analytics implementa todos esses testes para backtesting de VaR/ES.

## Ferramentas e APIs disponiveis

| Ferramenta | Uso | Notas |
|---|---|---|
| `arch` | GARCH, EGARCH, GJR-GARCH, TGARCH, CGARCH | Padrao Python, mais completo |
| `arch.arch_model` | Interface de alto nivel | vol='GARCH', 'EGARCH', 'GJR', etc. |
| `statsmodels` | ARCH-LM test, Ljung-Box | Diagnostico de residuos |
| `rugarch` (R) | GARCH para R | Referencia em academia |
| `vgarch` (Python) | Multivariate GARCH | DCC-GARCH, BEKK |
| `pyflux` | GARCH bayesiano | Alternativa probabilistica |

A biblioteca `arch` (Kevin Sheppard) e a referencia absoluta em Python:

```python
from arch import arch_model

# GARCH(1,1) com t-Student
am = arch_model(returns, vol='Garch', p=1, q=1, dist='t')
res = am.fit(update_freq=5)
print(res.summary())

# EGARCH com leverage
am = arch_model(returns, vol='EGarch', p=1, q=1, dist='t')
res = am.fit()

# Forecast
forecast = res.forecast(horizon=5)
```

## Por que importa para o crypto-correl-bot

**O que ja temos no projeto**:
- Calculo de GARCH (mencionado no escopo do bot).

**O que falta ou poderia ser melhorado**:
1. **Distribuicao t-Student**: garantir que o bot usa t-Student (ou skew-t) ao inves de normal. Normal em cripto subestima risco drasticamente.
2. **EGARCH ou GJR-GARCH**: se o bot so usa GARCH(1,1) simetrico, considerar EGARCH para capturar assimetria. Em cripto, a assimetria existe mas e diferente de equities: choques positivos extremos (bull runs) tambem aumentam volatilidade.
3. **Walk-forward com refit periodico**: garantir que o bot re-estima o modelo periodicamente e nao usa parametros estaticos. Refit semanal para dados diarios, diario para dados intradiarios.
4. **Position sizing baseado em volatilidade**: usar sigma_t prevista para ajustar tamanho de posicao. Manter volatilidade alvo constante (ex: 1% por trade). Se sigma_t aumenta, reduzir tamanho.
5. **VaR/CVaR dinamico**: integrar GARCH com VaR/CVaR para ter metricas de risco que respondem a mudancas de volatilidade. VaR com volatilidade constante subestima risco em periodos turbulentos.
6. **Diagnosticos obrigatorios**: apos fitar GARCH, rodar ARCH-LM nos residuos padronizados. Se ainda ha ARCH effects, o modelo e inadequado. Log isso como warning.
7. **HAR como complemento**: se o bot tem dados intradiarios (que tem), HAR com realized volatility pode complementar GARCH, especialmente para horizontes de 1-7 dias.

## Referencias

1. HolyFot - GARCH-HAR: framework de testes para modelos de volatilidade GARCH e HAR em cripto (2025). https://github.com/HolyFot/GARCH-HAR
2. Forecasting Bitcoin Price Volatility Using GARCH Models and Real-Time Data (SSRN, junho 2025). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5279513
3. Aneesh2409 - garch-risk-analytics: GJR-GARCH, VaR/ES backtesting, walk-forward (2025). https://github.com/Aneesh2409/garch-risk-analytics
4. GARCH vs LSTM for Bitcoin Volatility Forecasting (TildAlice, 2026). https://tildalice.io/garch-lstm-bitcoin-volatility/
5. arch - ARCH Modeling documentation (Kevin Sheppard). https://arch.readthedocs.io/en/stable/univariate/univariate_volatility_modeling.html
