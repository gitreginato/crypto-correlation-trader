# Topico: Returns, Correlacao e Rolling Correlation

**Data:** 2026-07-15
**Categoria:** Estatistica / Quant

## TL;DR

Returns sao a base de toda analise quant: log returns sao aditivos no tempo e preferidos para modelagem estatistica, enquanto simple returns sao aditivos no portfolio. Correlacao mede co-movimento linear (Pearson) ou monotono (Spearman, Kendall), mas e instavel em cripto. Rolling correlation com janela deslizante captura essa instabilidade. O maior problema em cripto e o "market mode": BTC domina e infla todas as correlacoes. A solucao e remover o primeiro componente principal via PCA antes de clusterizar.

## Explicacao para criancas

Imagine que voce quer saber se duas pessoas andam juntas no parque. Voce pode olhar se elas sempre viram a mesma esquina ao mesmo tempo. Se sim, estao correlacionadas. Mas no mundo das cripto, quase todas as moedas andam atraz do BTC, como um bairro inteiro segue o lider do grupo. Para saber quem realmente anda junto por escolha propria, e nao por seguir o mesmo lider, voce precisa primeiro remover a influencia do lider e depois comparar quem continua lado a lado.

## Como funciona tecnicamente

### Log returns vs simple returns

Simple return (retorno aritmetico):

    R_t = (P_t - P_{t-1}) / P_{t-1} = P_t / P_{t-1} - 1

Log return (retorno logaritmico):

    r_t = ln(P_t / P_{t-1}) = ln(1 + R_t)

Propriedades chave:

1. **Aditividade temporal**: log returns somam ao longo do tempo. O return de N periodos e simplesmente a soma dos returns diarios: `r_{0:t} = sum(r_i)`. Simple returns exigem multiplicacao composta: `(1 + R_{0:t}) = prod(1 + R_i)`.

2. **Simetria**: um log return de +10% seguido de -10% volta ao preco original. Com simple returns, +10% e depois -10% nao volta ao mesmo valor (100 -> 110 -> 99). Isso e a assimetria dos simple returns.

3. **Aproximacao**: para |R_t| pequeno (< 5%), `r_t ~= R_t` pela expansao de Taylor de ln(1+x). Para cripto, onde returns diarios podem passar de 10%, a divergencia e material.

4. **Aditividade no portfolio**: simple returns sao aditivos em posicoes. Se voce tem 50% em ativo A e 50% em ativo B, o return do portfolio e `0.5 * R_A + 0.5 * R_B`. Log returns nao tem essa propriedade diretamente.

**Quando usar cada um**:
- Log returns: modelagem estatistica, volatilidade, series temporais, GARCH, cointegracao.
- Simple returns: metricas de performance, portfolio optimization, PnL real.

Codigo Python:

```python
import numpy as np
import pandas as pd

# Simple returns
simple_returns = prices.pct_change()

# Log returns (metodo 1)
log_returns = np.log(prices / prices.shift(1))

# Log returns (metodo 2, equivalente)
log_returns = np.log1p(prices.pct_change())

# Cumulative: log returns somam
cum_log = np.exp(log_returns.cumsum()) - 1

# Cumulative: simple returns multiplicam
cum_simple = (1 + simple_returns).cumprod() - 1
```

### Correlacao: Pearson, Spearman, Kendall

**Pearson (r)**: mede associacao linear entre duas variaveis.

    r = cov(X, Y) / (sigma_X * sigma_Y)

Assumacoes: linearidade, normalidade bivariada, ausencia de outliers. Sensivel a outliers, o que e problematico em cripto (caudas pesadas). Se a relacao e nao-linear mas monotona, Pearson subestima.

**Spearman (rho)**: Pearson aplicado aos ranks. Mede associacao monotonica (nao necessariamente linear).

    rho = pearson(rank(X), rank(Y))

Robusto a outliers. Captura relacoes exponenciais, quadraticas, etc., desde que monotonicas. Nao assume normalidade. Ideal para cripto onde a linearidade e duvidosa.

**Kendall (tau)**: baseado em pares concordantes e discordantes.

    tau = (n_concordant - n_discordant) / (n * (n-1) / 2)

Mais conservador que Spearman. Melhor para amostras pequenas e dados ordinais. Interpretacao direta: probabilidade de concordancia menos probabilidade de discordancia. Valores tipicamente menores em magnitude que Spearman para os mesmos dados.

**Comparacao pratica**:

| Metrica | Mede | Robustez a outliers | Assumacao |
|---|---|---|---|
| Pearson | Linear | Baixa | Normalidade |
| Spearman | Monotona | Alta | Nenhuma |
| Kendall | Concordancia | Alta | Nenhuma |

Para cripto: reportar os tres. Se Pearson >> Spearman, verificar outliers. Se Spearman >> Kendall, relacao pode ser nao-monotona.

```python
from scipy.stats import pearsonr, spearmanr, kendalltau

r_p, p_p = pearsonr(x, y)
r_s, p_s = spearmanr(x, y)
r_k, p_k = kendalltau(x, y)
```

### Rolling correlation

Correlacao estatica sobre todo o periodo e uma ilusao em cripto. A correlacao entre BTC e ETH em 2020 era ~0.3, em 2022 chegou a ~0.9, e oscila com o regime de mercado.

Rolling correlation calcula a correlacao em uma janela deslizante de tamanho W:

    rho_t = corr(X_{t-W+1:t}, Y_{t-W+1:t})

Escolha da janela W:
- W muito pequena (< 20): ruido, oscila violentamente.
- W muito grande (> 180): suaviza demais, nao detecta mudancas de regime.
- Para dados diarios em cripto: 30 a 90 dias e o intervalo tipico.
- Para dados intradiarios (1h): 7 a 30 dias equivalentes.

```python
import pandas as pd

def rolling_correlation(
    returns_a: pd.Series,
    returns_b: pd.Series,
    window: int = 60
) -> pd.Series:
    """Rolling Pearson correlation between two return series."""
    return returns_a.rolling(window).corr(returns_b)

# Spearman rolling (mais lento, mas robusto)
def rolling_spearman(a: pd.Series, b: pd.Series, window: int = 60) -> pd.Series:
    result = []
    for i in range(len(a) - window + 1):
        r, _ = spearmanr(a.iloc[i:i+window], b.iloc[i:i+window])
        result.append(r)
    return pd.Series(result, index=a.index[window-1:])
```

### Matriz de distancia de correlacao

Para clusterizar ativos por correlacao, nao usamos corr diretamente (a distancia entre corr=0.99 e corr=0.95 deveria ser maior do que aparenta). A distancia padrao e:

    d_{i,j} = sqrt(2 * (1 - corr_{i,j}))

Esta transformacao garante que:
- d = 0 quando corr = 1 (identicos)
- d = sqrt(2) quando corr = 0 (independentes)
- d = 2 quando corr = -1 (perfeitamente anti-correlacionados)
- A matriz de distancia satisfaz a desigualdade triangular (condicao para clustering valido).

```python
import numpy as np

def corr_distance_matrix(corr_matrix: np.ndarray) -> np.ndarray:
    """Convert correlation matrix to distance matrix."""
    return np.sqrt(2.0 * (1.0 - corr_matrix))
```

### Armadilha 1: correlacao nao implica causalidade

Correlacao alta entre BTC e ETH nao significa que BTC "causa" ETH. Pode haver uma variavel latente (sentimento de mercado, fluxo de capital, macro). Para inferir causalidade, seria necessario Granger causality, convergent cross mapping, ou design experimental. Em trading, o que importa e se a relacao e estavel e exploravel, nao a direcao causal.

### Armadilha 2: correlacao e instavel em cripto

A correlacao em cripto muda com o regime. Em bull markets, tudo sobe junto (corr -> 1). Em bear markets, correlacoes tambem aumentam (contagio). Em mercados laterais, correlacoes caem. Isso significa que uma correlacao estimada hoje pode nao valer amanha.

### Armadilha 3: market mode (BTC domina)

O primeiro componente principal de uma matriz de correlacao de cripto tipicamente explica 40-60% da variancia, contra 20-30% em equities. Isso e o "market mode": um fator comum que move todos os ativos. Se voce clusteriza a matriz de correlacao bruta, todos os ativos aparecem em um unico cluster, porque o market mode domina.

### Solucao: PCA para remover market mode

O procedimento e:

1. Calcular a matriz de correlacao dos returns.
2. Aplicar PCA e identificar o primeiro componente (PC1, o market mode).
3. Regredir os returns de cada ativo contra PC1.
4. Usar os residuais (returns sem o market mode) para calcular a nova matriz de correlacao.
5. Clusterizar essa matriz residual.

```python
from sklearn.decomposition import PCA

def remove_market_mode(returns: pd.DataFrame, n_components: int = 1) -> pd.DataFrame:
    """Remove market mode via PCA residualization."""
    pca = PCA(n_components=n_components)
    market_factor = pca.fit_transform(returns.fillna(0))
    # Regredir cada ativo contra o fator de mercado
    residuals = returns.copy()
    for col in returns.columns:
        beta = np.cov(returns[col].fillna(0), market_factor[:, 0])[0, 1] / np.var(market_factor[:, 0])
        residuals[col] = returns[col] - beta * market_factor[:, 0]
    return residuals
```

Apos remover o market mode, a matriz de correlacao residual revela correlacoes "genuinas" entre ativos: setores (DeFi, L1, meme), pares cointegrados, e estruturas que o clustering bruto nao enxerga.

### Armadilha 4: janela de correlacao e look-ahead bias

Se voce calcula a correlacao sobre uma janela que inclui dados futuros, voce tem look-ahead bias. A janela rolling deve sempre usar apenas dados passados: `corr(X_{t-W:t-1}, Y_{t-W:t-1})` para prever o estado em `t`, nunca `corr(X_{t-W/2:t+W/2}, ...)` (janela centrada).

## Estado do mercado em 2026

A pesquisa em correlacao de cripto evoluiu em varias direcoes em 2025-2026:

1. **PCA e market mode sao praticas estabelecidas**: o repositorio crypto_stat_arb (Aroesler1, 2025) implementa o pipeline completo de residualizacao por PCA, clustering em grafo signed (SPONGE, BNC, spectral), e backtest walk-forward com controle de turnover e custos. O Talos Risk Models report (2023) comparou PCA vs factor models para cripto e concluiu que PCA e promissor por sua adaptabilidade a estrutura nao-fixa de fatores.

2. **Detrended cross-correlation analysis (DCCA)**: um paper de 2025 na Entropy (MDPI) aplicou DCCA com fluctuation-order parameter em 140 criptos de 2021 a 2024 em dados de 1 minuto. Revelou modos coletivos robustos, incluindo um fator de mercado dominante e componentes setoriais, cuja forca depende da escala temporal analisada. Apos filtrar o market mode, o bulk de eigenvalues alinha com o limite de correlacoes aleatorias, permitindo identificar outliers estruturalmente significativos.

3. **Rolling-window kernel regularized partial correlation (RW-KRPC)**: um estudo de 2025 no Finance Research Letters introduziu este metodo para capturar ligacoes nao-lineares, time-varying e condicionais entre cripto e equities. Encontrou que correlacoes entre S&P 500 e BTC/ETH ficaram negativas durante crises (COVID, FTX) sugerindo comportamento safe-haven temporario, e se fortaleceram durante a aprovacao dos ETFs spot de BTC em 2024.

4. **Functional PCA (FPCA) intradiario**: um paper de 2025 no arXiv aplicou FPCA em returns intradiarios de BTC, mostrando que interval forecasts melhoram quando a heteroscedasticidade condicional das funcoes de return e considerada. O metodo FPCA rolling superou ARMA e ML em acuracia direcional (sign forecast).

5. **Correlacao parcial**: a correlacao regular entre dois ativos inclui o efeito indireto via outros ativos. Correlacao parcial remove esse efeito. Em cripto, onde o market mode e onipresente, correlacao parcial e mais informativa que correlacao bruta para identificar pares genuinamente conectados.

## Ferramentas e APIs disponiveis

| Ferramenta | Uso | Notas |
|---|---|---|
| `scipy.stats` | pearsonr, spearmanr, kendalltau | Padrao para correlacao estatica |
| `pandas.DataFrame.rolling.corr` | Rolling correlation | Rapido, vetorizado em C |
| `statsmodels` | corr_nearest, correlacao parcial | corr_nearest corrige matrizes nao PSD |
| `scikit-learn` PCA | Remover market mode | sklearn.decomposition.PCA |
| `nolds` | Hurst, DFA | Para analise de memoria longa |
| `numpy` | Operacoes matriciais | corrcoef, distancia |
| `networkx` | Grafos de correlacao | Clusterizacao |
| `ruptures` | Detectar breaks na correlacao | Change point detection |
| `ccxt` / `python-binance` | Dados de preco | Para calcular returns |

Bibliotecas especializadas para correlacao em altissima dimensao:
- `oas` (Ledoit-Wolf shrinkage): para matrizes de correlacao com N > T (mais ativos que observacoes).
- `graphical_lasso` (sklearn): para estimar a matriz de precisao (inverse covariance), que revela correlacao parcial.

## Por que importa para o crypto-correl-bot

**O que ja temos no projeto**:
- Calculo de returns em `src/analysis/returns.py`.
- Matriz de correlacao em `src/analysis/correlation.py`.
- Construcao do grafo em `src/analysis/graph.py`.
- Calculo de Pearson, Spearman e Kendall (ja implementado nas tres metricas).
- Janela deslizante para correlacao rolling.

**O que falta ou poderia ser melhorado**:
1. **Remocao de market mode via PCA**: este e o upgrade de maior impacto. Sem isso, o grafo de correlacao e dominado por um unico cluster gigante. Implementar `remove_market_mode()` como preprocessing antes da clusterizacao.
2. **Matriz de distancia d = sqrt(2(1-corr))**: verificar se o bot ja usa esta transformacao ou se clusteriza a correlacao diretamente. A transformacao e obrigatoria para clustering valido.
3. **Correlacao parcial**: implementar via matriz de precisao (graphical lasso) como alternativa complementar.
4. **Deteccao de breaks na correlacao**: usar `ruptures` para detectar quando a estrutura de correlacao muda estruturalmente, e re-clusterizar.
5. **Rolling Spearman e Kendall**: o bot provavelmente so faz rolling Pearson. Adicionar rolling Spearman para robustez.
6. **Shrinkage da matriz de correlacao**: quando o numero de ativos se aproxima do numero de observacoes, a matriz amostral e ruidosa. Ledoit-Wolf shrinkage estabiliza.

## Referencias

1. Aroesler1 - Crypto Stat Arb: market-neutral stat-arb com PCA residualization e clustering signed. https://github.com/Aroesler1/crypto_stat_arb
2. Detrended Cross-Correlations and Their Random Matrix Limit: An Example from the Cryptocurrency Market (Entropy, 2025). https://doi.org/10.3390/e27121236
3. Talos - Risk Models for Crypto Assets: Fundamental vs PCA (2023). https://go.talos.com/rs/545-ATY-448/images/Talos_Risk%20Models%20for%20Crypto%20Assets%20-%20Fundamental%20vs%20PCA_Jul%202023.pdf
4. Cryptocurrency U.S. equity co-movements: Rolling-Window Kernel Regularized Partial Correlation (Finance Research Letters, 2025). https://ideas.repec.org/a/eee/finlet/v86y2025ipgs1544612325020999.html
5. Intraday Functional PCA Forecasting of Cryptocurrency Returns (arXiv, 2025). https://arxiv.org/pdf/2505.20508
6. Correlation Coefficients in Python: Pearson, Spearman, Kendall (2026). https://insightful-data-lab.com/2026/01/14/correlation-coefficients-in-python-pearson-spearman-kendall/
7. statsmodels - Statistics stats (corr_nearest para matrizes nao PSD). https://www.statsmodels.org/dev/stats.html
8. Log returns vs simple returns: when each convention is appropriate (pfolio academy). https://www.pfolio.io/academy/log-vs-simple-returns
