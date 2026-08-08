# Topico: VaR, CVaR, Drawdowns e Risk Metrics

**Data:** 2026-07-15
**Categoria:** Estatistica / Quant

## TL;DR

VaR (Value at Risk) estima a perda maxima em um nivel de confianca, mas e criticamente falho por ignorar o que acontece alem do threshold. CVaR (Conditional Value at Risk), tambem chamado Expected Shortfall, mede a perda media condicional alem do VaR e e mais prudente. Max drawdown mede a maior queda do pico ao vale, essencial para avaliar tolerancia psicologica e risco de ruin. Ratios como Sharpe, Sortino e Calmar comparam return ajustado ao risco. Em cripto, onde drawdowns de 50-80% sao comuns, essas metricas definem se uma estrategia e sobrevivivel. Bibliotecas como quantstats, empyrical e pyfolio sao o padrao Python para calculo e reporting.

## Explicacao para criancas

Imagine que voce guarda seu dinheiro em um barco. VaR e como perguntar: "se vier uma tempestade tipica, quanta agua entra no barco?" Mas o problema e que tempestades atipicas sao as que afundam o barco, e VaR nao diz nada sobre elas. CVaR e mais inteligente: pergunta "se a tempestade for pior que o normal, qual a media de agua que entra?" Drawdown e quanto o barco baixa do ponto mais alto que ja esteve ate o ponto mais baixo seguinte. Se o barco baixa demais, a tripulacao entra em panico e abandona o navio, mesmo que ele volte a subir depois.

## Como funciona tecnicamente

### VaR (Value at Risk)

VaR no nivel de confianca alpha e a perda tal que a probabilidade de uma perda maior e (1 - alpha):

    P(L > VaR_alpha) = 1 - alpha

Exemplo: VaR 95% de $1000 significa que ha 5% de chance de perder mais que $1000 em um dia.

Tres metodos de calculo:

#### 1. Variance-Covariance (parametrico)

Assume que os returns seguem uma distribuicao conhecida (tipicamente Normal):

    VaR_alpha = -(mu + sigma * z_alpha)

Onde z_alpha e o quantil alpha da distribuicao normal padrao (ex: z_0.05 = -1.645 para VaR 95%).

```python
from scipy.stats import norm

def var_parametric(returns: pd.Series, confidence: float = 0.95) -> float:
    """Parametric VaR assuming normal distribution."""
    mu = returns.mean()
    sigma = returns.std()
    z = norm.ppf(1 - confidence)
    return float(mu + sigma * z)
```

**Vantagem**: rapido, closed-form.
**Desvantagem**: assume normalidade. Returns de cripto tem caudas pesadas (kurtosis > 3) e skew. VaR parametrico subestima risco em cripto.

#### 2. Historico

Usa a distribuicao empirica dos returns passados. O VaR e o quantil empirico:

    VaR_alpha = quantile(returns, 1 - alpha)

```python
def var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    """Historical VaR from empirical distribution."""
    return float(returns.quantile(1 - confidence))
```

**Vantagem**: sem assumir distribuicao. Captura caudas empiricas.
**Desvantagem**: assume que o passado representa o futuro. Se o periodo historico nao inclui crises, o VaR e otimista. Sensivel a janela.

#### 3. Monte Carlo

Simula cenarios futuros a partir de um modelo (ex: GBM, GARCH) e calcula o quantil das perdas simuladas:

```python
def var_monte_carlo(
    returns: pd.Series,
    confidence: float = 0.95,
    n_sims: int = 10000,
    horizon: int = 1
) -> float:
    """Monte Carlo VaR via bootstrap of historical returns."""
    simulated = np.random.choice(returns, size=(n_sims, horizon), replace=True)
    portfolio_returns = simulated.sum(axis=1)
    return float(np.quantile(portfolio_returns, 1 - confidence))
```

**Vantagem**: flexivel, pode modelar dependencias, paths multi-periodo.
**Desvantagem**: depende da qualidade do modelo de simulacao. Computacionalmente caro.

#### Limitacoes do VaR

1. **Nao mede a perda alem do threshold**: VaR 95% diz que ha 5% de chance de perder mais que X, mas nao diz quanto mais. Em cripto, os 5% piores podem ser catastroficos (-50% em um dia).
2. **Nao subaditivo**: VaR de um portfolio pode ser maior que a soma dos VaRs dos componentes. Isso viola a teoria de diversificacao.
3. **Pro-ciclico**: em periodos calmos, VaR e baixo, incentivando alavancagem. Em crises, VaR sobe, forçando deleveraging no pior momento.
4. **Backtesting dificil**: VaR e uma afirmacao sobre a cauda, onde ha poucas observacoes. Validar se o VaR 99% esta correto requer muitos anos de dados.

### CVaR / Expected Shortfall

CVaR e a perda esperada condicional alem do VaR:

    CVaR_alpha = E[L | L > VaR_alpha]

Para distribuicao continua:

    CVaR_alpha = -1/(1-alpha) * integral_{-inf}^{VaR_alpha} x * f(x) dx

Estimacao historica:

    CVaR_alpha = -mean(returns[returns <= VaR_alpha])

```python
def cvar_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    """Historical CVaR (Expected Shortfall)."""
    var = returns.quantile(1 - confidence)
    tail = returns[returns <= var]
    if len(tail) == 0:
        return float(var)
    return float(-tail.mean())
```

**Vantagens sobre VaR**:
1. **Subaditivo**: CVaR de portfolio <= soma de CVaRs. Respeita diversificacao.
2. **Mede a cauda inteira**: nao so o threshold, mas a media alem dele.
3. **Coerente (Artzner et al.)**: satisfaz todas as propriedades de uma medida de risco coerente (monotonicidade, subaditividade, homogeneidade positiva, transalacao).

CVaR sempre >= VaR em magnitude. A diferenca entre CVaR e VaR indica quao pesada e a cauda. Em cripto, essa diferenca e grande.

### Max Drawdown

Drawdown mede a queda percentual do ultimo pico ao vale atual:

    DD_t = (V_t - max(V_{0:t})) / max(V_{0:t})

Onde V_t e o valor do portfolio em t. Max drawdown e o pior drawdown historico:

    MaxDD = min(DD_t) para todo t

```python
def max_drawdown(returns: pd.Series) -> float:
    """Calculate maximum drawdown from returns."""
    cumulative = (1 + returns).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (cumulative - peak) / peak
    return float(drawdown.min())
```

**Interpretacao**:
- MaxDD de -50%: o portfolio caiu 50% do pico ao vale.
- Em cripto, buy-and-hold BTC tem MaxDD de ~80% (2018, 2022). Estrategias market-neutral tipicamente visam MaxDD < 15-20%.
- MaxDD define a tolerancia psicologica do investidor. Se MaxDD > tolerancia, o investidor abandona a estrategia antes da recuperacao.

### Calmar ratio

Calmar = CAGR / |MaxDD|

Mede return anualizado por unidade de max drawdown. Tipicamente calculado em janela de 36 meses.

| Calmar | Interpretacao |
|---|---|
| > 3 | Excelente |
| 1-3 | Bom |
| 0.5-1 | Aceitavel |
| < 0.5 | Ruim |

### Sharpe ratio

Sharpe = (mu - r_f) / sigma

Onde:
- mu: return medio (anualizado).
- r_f: risk-free rate.
- sigma: volatilidade (desvio padrao, anualizado).

Mede return excedente por unidade de volatilidade total (upside + downside).

| Sharpe | Interpretacao |
|---|---|
| > 2 | Excelente (raro em cripto) |
| 1-2 | Muito bom |
| 0.5-1 | Razoavel |
| < 0.5 | Questionavel |
| < 0 | Pior que risk-free |

**Armadilha em cripto**: Sharpe usa volatilidade total, que inclui upside volatility. Estrategias que tem returns muito positivos mas volateis podem ter Sharpe baixo. Sortino resolve isso.

### Sortino ratio

Sortino = (mu - r_f) / sigma_downside

Onde sigma_downside e o desvio padrao apenas dos returns negativos (abaixo de um target, tipicamente 0 ou r_f):

    sigma_downside = sqrt(mean(min(0, r_t - target)^2))

Sortino penaliza apenas downside volatility. Estrategias com returns assimetricos (muitos pequenos gains, poucos grandes losses) sao melhor avaliadas por Sortino.

| Sortino | Interpretacao |
|---|---|
| > 2 | Excelente |
| 1-2 | Muito bom |
| 0.5-1 | Razoavel |

Sortino >= Sharpe sempre (downside vol <= total vol). A razao Sortino/Sharpe indica assimetria: proxima de 1 significa returns simetricos, maior que 1 significa mais upside que downside.

### Outras metricas

**Ulcer Index**: mede a severidade e duracao dos drawdowns:

    UI = sqrt(mean(DD_t^2))

Ulcer Performance Index (UPI) = (mu - r_f) / UI. Similar ao Sharpe mas usando Ulcer Index ao inves de volatilidade.

**Tail Ratio**: razao entre o return no percentil 95 e no percentil 5:

    Tail Ratio = |percentile(returns, 95)| / |percentile(returns, 5)|

Tail Ratio > 1 significa que os melhores dias sao melhores que os piores dias sao ruins. Favoravel.

**Common Sense Ratio**: Profit Factor * Tail Ratio. Mede robustez combinada.

**Risk of Ruin**: probabilidade de perder todo o capital. Depende do tamanho da posicao, win rate, e payoff ratio.

### Stress testing

Stress testing avalia como o portfolio se comporta em cenarios extremos:

1. **Stress historico**: aplicar os returns dos piores periodos historicos (COVID crash mar 2020, FTX collapse nov 2022, Terra Luna mai 2022) ao portfolio atual.
2. **Stress parametrico**: simular choques especificos (BTC -30% em um dia, correlacao -> 1 em crash).
3. **Monte Carlo stress**: simular milhares de cenarios a partir de uma distribuicao com caudas pesadas (t-Student com dof baixo).

```python
def stress_test_historical(
    returns: pd.Series,
    portfolio_value: float,
    stress_period: pd.Series
) -> float:
    """Apply historical stress period to current portfolio."""
    cumulative = (1 + stress_period).cumprod()
    final_value = portfolio_value * cumulative.iloc[-1]
    loss = (final_value - portfolio_value) / portfolio_value
    return float(loss)
```

### Backtesting de VaR

Para validar se o VaR e confiavel, verificar se o numero de violacoes (returns piores que VaR) e compativel com o nivel de confianca:

- VaR 95%: esperar ~5% de violacoes.
- VaR 99%: esperar ~1% de violacoes.

**Kupiec POF test**: testa se a taxa de violacao observada e consistente com a esperada.

**Christoffersen test**: testa se as violacoes sao independentes (nao clusterizadas). Cluster de violacoes indica que o modelo nao captura volatility clustering.

### Bibliotecas Python

#### quantstats

O padrao moderno para reporting de risk metrics. Integra com pandas e gera tear sheets em HTML.

```python
import quantstats as qs

# Metricas individuais
qs.stats.value_at_risk(returns, confidence=0.95)
qs.stats.conditional_value_at_risk(returns, confidence=0.95)
qs.stats.max_drawdown(returns)
qs.stats.sharpe(returns)
qs.stats.sortino(returns)
qs.stats.calmar(returns)
qs.stats.tail_ratio(returns)
qs.stats.ulcer_index(returns)

# Monte Carlo
qs.stats.montecarlo(returns, num_sims=1000)

# Tear sheet completo em HTML
qs.reports.html(returns, output="report.html")
```

quantstats implementa VaR pelo metodo variance-covariance (parametrico) com distribuicao normal:

    VaR = norm.ppf(1 - confidence, mu, sigma)

CVaR calcula a media dos returns piores que VaR.

#### empyrical

Biblioteca classica da Quantopian, usada por pyfolio. Funcoes para todas as metricas principais:

```python
from empyrical import (
    max_drawdown, calmar_ratio, sharpe_ratio,
    sortino_ratio, annual_volatility, alpha_beta,
    roll_max_drawdown, value_at_risk
)

max_dd = max_drawdown(returns)
calmar = calmar_ratio(returns, period='daily')
sharpe = sharpe_ratio(returns, risk_free=0, period='daily')
sortino = sortino_ratio(returns, required_return=0, period='daily')
alpha, beta = alpha_beta(returns, benchmark_returns)
```

empyrical tambem suporta rolling versions: `roll_max_drawdown(returns, window=252)`.

#### pyfolio

Gera tear sheets completos com plots. As funcoes de risk metrics em pyfolio.timeseries estao deprecated e delegam para empyrical.

```python
import pyfolio as pf

pf.create_full_tear_sheet(returns)
pf.create_returns_tear_sheet(returns)
pf.create_drawdown_underwater_plot(returns)
```

## Estado do mercado em 2026

1. **quantstats como padrao**: quantstats (ranaroussi) consolidou-se como a biblioteca mais usada para risk metrics e reporting em Python. A versao atual (v0.0.81 no PyPI) inclui mais de 60 metricas: value_at_risk, conditional_value_at_risk, expected_shortfall, max_drawdown, calmar, sortino, adjusted_sortino, sharpe, tail_ratio, ulcer_index, ulcer_performance_index, kelly_criterion, risk_of_ruin, e funcoes de Monte Carlo (montecarlo, montecarlo_cagr, montecarlo_drawdown, montecarlo_sharpe).

2. **CVaR sobre VaR como padrao regulatorio**: Basel III e frameworks regulatorios modernos migraram de VaR para Expected Shortfall (CVaR) como medida de risco padrao. CVaR e coerente (subaditivo) e captura a cauda inteira, nao so o threshold. Em cripto, onde caudas sao extremas, essa migracao e ainda mais importante.

3. **VaR dinamico com GARCH**: o repositorio garch-risk-analytics (Aneesh2409, 2025) integra GARCH com VaR/CVaR, calculando VaR dinamico que responde a mudancas de volatilidade. Backtesting com Kupiec (coverage), Christoffersen (independence), e joint conditional coverage. Walk-forward validation seleciona a especificacao em folds de treino apenas, evitando overfit.

4. **Monte Carlo em quantstats**: quantstats inclui funcoes de Monte Carlo para estimar distribuicoes de CAGR, max drawdown, e Sharpe sob variacoes de ordem de returns. Isso e util para avaliar robustez da estrategia: se o Sharpe medio das simulacoes e muito menor que o Sharpe historico, a estrategia e fragil a ordenacao dos returns.

5. **empyrical e o backend**: empyrical continua como o backend computacional para pyfolio e varias outras bibliotecas. As funcoes em pyfolio.timeseries estao explicitamente deprecated e delegam para empyrical. Para uso programatico (sem plots), empyrical e mais leve e direto.

## Ferramentas e APIs disponiveis

| Ferramenta | Uso | Notas |
|---|---|---|
| `quantstats` | Risk metrics + tear sheets | Padrao moderno, HTML reports |
| `empyrical` | Risk metrics programaticas | Backend do pyfolio, rolling versions |
| `pyfolio` | Tear sheets completos com plots | Visual, delega para empyrical |
| `scipy.stats` | norm.ppf para VaR parametrico | Quantis de distribuicoes |
| `arch` | VaR/CVaR dinamico com GARCH | Volatilidade condicional |
| `vectorbt` | Risk metrics em backtest | Integrado com backtesting |

**Recomendacao para o bot**: usar quantstats para reporting (tear sheets HTML) e empyrical para calculo programatico dentro do bot. Para VaR/CVaR dinamico, integrar com arch (GARCH).

## Por que importa para o crypto-correl-bot

**O que ja temos no projeto**:
- Calculo de VaR/CVaR (mencionado no escopo do bot).
- Calculo de drawdowns (mencionado no escopo do bot).

**O que falta ou poderia ser melhorado**:
1. **CVaR sobre VaR**: garantir que o bot reporta e usa CVaR como metrica primaria de risco, nao VaR. VaR subestima risco em cripto por ignorar a cauda alem do threshold.
2. **VaR/CVaR dinamico com GARCH**: integrar a volatilidade condicional do GARCH no calculo de VaR. VaR com volatilidade constante subestima risco em periodos turbulentos. Usar `sigma_t` prevista pelo GARCH como input.
3. **Stress test de cenarios cripto**: implementar stress tests especificos: Terra Luna (mai 2022, BTC -30% em dias), FTX collapse (nov 2022), COVID crash (mar 2020). Aplicar esses cenarios ao portfolio atual e reportar perda.
4. **Max drawdown como kill switch**: se o drawdown atual exceder um threshold (ex: -15%), o bot deve parar de abrir novas posicoes. Isso e essencial em cripto onde drawdowns podem acelerar rapidamente.
5. **Sortino sobre Sharpe**: usar Sortino como metrica primaria de performance, nao Sharpe. Sortino penaliza apenas downside, o que e mais relevante para estrategias que visam returns assimetricos.
6. **Monte Carlo de robustez**: rodar Monte Carlo embaralhando a ordem dos returns para estimar a distribuicao de max drawdown e Sharpe. Se o MaxDD historico esta no percentil 5 das simulacoes, a estrategia teve sorte na ordenacao.
7. **Backtesting de VaR**: implementar Kupiec e Christoffersen tests para validar se o VaR do bot e confiavel. Se o VaR 95% e violado em 10% dos dias, o modelo subestima risco.
8. **Tear sheet automatico**: gerar tear sheet HTML com quantstats apos cada ciclo de backtest ou mensalmente em paper/live trading. Isso da visibilidade imediata de todas as metricas.
9. **Ulcer Index para duracao de drawdown**: max drawdown mede a magnitude, mas nao a duracao. Ulcer Index captura ambos. Uma estrategia com MaxDD de -20% que dura 3 meses e muito pior que uma com MaxDD de -25% que dura 1 semana.

## Referencias

1. quantstats - GitHub (ranaroussi): risk metrics, tear sheets, Monte Carlo. https://github.com/ranaroussi/quantstats/
2. quantstats stats.py: value_at_risk, conditional_value_at_risk (variance-covariance method). https://github.com/ranaroussi/quantstats/blob/34049267/quantstats/stats.py
3. quantstats - PyPI v0.0.81: lista completa de metricas. https://pypi.org/project/quantstats/
4. Risk Metrics - DeepWiki quantstats: VaR e CVaR methodology. https://deepwiki.com/ranaroussi/quantstats/3.2-risk-metrics
5. empyrical - GitHub (quantopian): risk metrics, rolling versions. https://github.com/quantopian/empyrical
6. empyrical - API Reference: calmar_ratio, sharpe_ratio, sortino_ratio. https://quantopian.github.io/empyrical/appendix.html
7. empyrical - ml4trading documentation. https://empyrical.ml4trading.io/index.html
8. pyfolio - GitHub (quantopian): tear sheets com plots. https://www.github.com/quantopian/pyfolio
9. Aneesh2409 - garch-risk-analytics: VaR/ES backtesting com Kupiec e Christoffersen. https://github.com/Aneesh2409/garch-risk-analytics
