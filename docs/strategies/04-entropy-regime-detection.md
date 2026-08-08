# Estrategia 04: Entropy-Based (Regime Detection)

**ID:** STRAT-04
**Categoria:** Meta-Strategy / Regime Filter
**Timeframe ideal:** 1h, 4h, 1d
**Horizonte:** N/A (filtro, nao estrategia standalone)
**Complexidade:** Alta

## 1. Conceito

Esta estrategia usa **teoria da informacao** (entropia de Shannon, entropia amostral, entropia de transferencia) para detectar o regime atual do mercado. Ela funciona como um **meta-filtro**: nao gera sinais de compra/venda diretamente, mas determina quais outras estrategias devem operar.

### Intuicao

Mercados financeiros alternam entre tres estados:
1. **Ordenado (baixa entropia)**: padroes se repetem, previsibilidade alta, trend following funciona
2. **Aleatorio (entropia maxima)**: ruido puro, nenhuma estrategia tem edge
3. **Caotico (entropia intermediaria mas instavel)**: transicoes, crises, mudancas de regime

A entropia mede quao "surpreendente" ou "incerta" a serie de returns e. Quando a entropia cai, o mercado esta mais ordenado e previsivel. Quando sobe, esta mais aleatorio.

### Por que isso importa para o bot

Cada estrategia tem um regime onde funciona:
- Mean Reversion: funciona em regime de baixa entropia e Hurst < 0.5
- Trend Following: funciona em regime de baixa entropia e Hurst > 0.5
- StatArb: funciona em regime de baixa entropia e spread estacionario
- Price Action: funciona em qualquer regime com baixa entropia

**Em regime de entropia maxima (alta incerteza), NENHUMA estrategia tem edge.** O bot deve ficar parado.

## 2. Fundamentacao Teorica

### 2.1 Shannon Entropy

Para uma serie de returns discretizada em N bins:

```
H(X) = -sum(p(xi) * log2(p(xi)))

onde p(xi) = frequencia do bin i
```

- H = 0: serie totalmente deterministica (1 bin dominante)
- H = log2(N): distribuicao uniforme (maxima incerteza)
- H alto: mercado aleatorio, sem padrao
- H baixo: mercado ordenado, padrao existe

### 2.2 Sample Entropy (SampEn)

Mede a regularidade/complexidade de uma serie temporal:

```
SampEn(m, r, N) = -ln(A^m(r) / B^m(r))

onde:
  m = dimensao de embedding (tamanho do padrao)
  r = tolerancia (fracao do desvio padrao, tipicamente 0.2)
  N = tamanho da serie
  B^m(r) = numero de matches de comprimento m
  A^m(r) = numero de matches de comprimento m+1
```

**Vantagem sobre ApEn:** SampEn nao conta self-matches, e menos enviesado.

**Interpretacao:**
- SampEn baixo: serie regular, padroes se repetem (mercado ordenado)
- SampEn alto: serie irregular, padroes nao se repetem (mercado caotico)
- SampEn diminuindo: mercado ficando mais previsivel
- SampEn aumentando: mercado ficando mais caotico (possivel crise)

### 2.3 Transfer Entropy

Mede o fluxo de informacao de uma serie para outra (causalidade informacional):

```
TE(X -> Y) = sum p(y_{t+1}, y_t, x_t) * log2(
    p(y_{t+1} | y_t, x_t) / p(y_{t+1} | y_t)
)
```

**Aplicacao:** detectar qual ativo "lider" o movimento do cluster. Se TE(BTC -> ETH) > TE(ETH -> BTC), BTC lidera e ETH segue.

### 2.4 Approximate Entropy (ApEn)

Similar a SampEn mas inclui self-matches. Menos confiavel que SampEn para series curtas, mas computacionalmente mais simples.

### 2.5 Relacao com Eficiencia de Mercado

```
Mercado eficiente (EMH): entropia = maxima (precos sao random walk)
Mercado ineficiente:     entropia < maxima (existem padroes exploraveis)

A entropia mede o GRAU de eficiencia do mercado.
Quando a entropia cai significativamente, o mercado esta ineficiente
e estrategias quantitativas tem edge.
```

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `entropy_window` | 100 | 50 a 200 | Janela para calculo da entropia |
| `entropy_method` | "sample" | "shannon", "sample", "approximate" | Metodo de entropia |
| `sampen_m` | 2 | 2 a 5 | Dimensao de embedding (SampEn) |
| `sampen_r` | 0.2 | 0.1 a 0.3 | Tolerancia (fracao do std) |
| `shannon_bins` | 10 | 5 a 20 | Numero de bins para Shannon |
| `regime_threshold_low` | 0.3 | 0.2 a 0.4 | Entropia normalizada abaixo = ordenado |
| `regime_threshold_high` | 0.7 | 0.6 a 0.8 | Entropia normalizada acima = caotico |
| `rolling_step` | 1 | 1 a 5 | Step da janela rolling (1 = tick a tick) |
| `hurst_window` | 100 | 50 a 200 | Janela para Hurst exponent |
| `transfer_entropy_lag` | 1 | 1 a 5 | Lag para transfer entropy |

## 4. Classificacao de Regime

### 4.1 Esquema de 4 regimess

```
                        Hurst < 0.45    0.45-0.55    Hurst > 0.55
Entropia baixa (< 0.3)  MEAN_REVERT    RANDOM       TRENDING
Entropia media (0.3-0.7) TRANSITION     RANDOM       TRANSITION
Entropia alta (> 0.7)   CHAOTIC        CHAOTIC      CHAOTIC
```

### 4.2 Acao por regime

| Regime | Entropia | Hurst | Acao | Estrategias Ativas |
|--------|----------|-------|------|--------------------|
| MEAN_REVERT | baixa | < 0.45 | Operar | STRAT-01, STRAT-03 |
| TRENDING | baixa | > 0.55 | Operar | STRAT-06 (Momentum) |
| RANDOM | media | ~0.5 | Reduzido | STRAT-02 (Price Action) com cautela |
| TRANSITION | media | qualquer | Cautela | Reduzir tamanho em 50% |
| CHAOTIC | alta | qualquer | PARAR | Nenhuma |

### 4.3 Implementacao do classificador

```python
def classify_regime(returns: pd.Series, params: dict) -> str:
    """Classify market regime using entropy and Hurst exponent."""
    window = returns.tail(params["entropy_window"])

    # Normalized entropy (0 to 1)
    if params["entropy_method"] == "sample":
        entropy = sample_entropy(window.values, m=params["sampen_m"], r=params["sampen_r"])
        # Normalize: SampEn typically ranges 0-2 for financial data
        norm_entropy = min(entropy / 2.0, 1.0)
    else:
        entropy = shannon_entropy(window.values, bins=params["shannon_bins"])
        max_entropy = np.log2(params["shannon_bins"])
        norm_entropy = entropy / max_entropy

    # Hurst exponent
    hurst = compute_hurst(window.values)

    # Classify
    if norm_entropy > params["regime_threshold_high"]:
        return "CHAOTIC"
    elif norm_entropy < params["regime_threshold_low"]:
        if hurst < 0.45:
            return "MEAN_REVERT"
        elif hurst > 0.55:
            return "TRENDING"
        else:
            return "RANDOM"
    else:
        return "TRANSITION"
```

## 5. Deteccao de Mudanca de Regime

### 5.1 Z-Score da entropia

```python
def detect_regime_change(entropy_series: pd.Series, window: int = 50) -> bool:
    """Detect significant change in entropy (regime shift)."""
    current = entropy_series.iloc[-1]
    rolling_mean = entropy_series.iloc[-window-1:-1].mean()
    rolling_std = entropy_series.iloc[-window-1:-1].std()
    z_score = (current - rolling_mean) / rolling_std
    return abs(z_score) > 2.0  # 2 sigma = mudanca significativa
```

### 5.2 Variance Ratio Test

Compara a variancia de returns de k periodos com k vezes a variancia de 1 periodo:

```
VR(k) = Var(r_k) / (k * Var(r_1))

VR = 1: random walk
VR < 1: mean reversion (anti-persistent)
VR > 1: momentum (persistent)
```

### 5.3 Alertas de crise

```python
def crisis_alert(entropy_history: pd.DataFrame) -> dict:
    """Detect potential crisis based on entropy patterns."""
    alerts = []

    for asset in entropy_history.columns:
        ent = entropy_history[asset]

        # 1. Entropia subiu mais que 2 sigma
        z = (ent.iloc[-1] - ent.iloc[-50:].mean()) / ent.iloc[-50:].std()
        if z > 2:
            alerts.append({"asset": asset, "type": "entropy_spike", "z": z})

        # 2. SampEn caiu drasticamente (regularidade aumentou = padrao quebrando)
        if ent.iloc[-1] < ent.iloc[-50:].quantile(0.1):
            alerts.append({"asset": asset, "type": "entropy_collapse", "value": ent.iloc[-1]})

        # 3. Transfer entropy mudou de direcao (lideranca mudou)
        # (requer calculo de TE entre pares)

    return alerts
```

## 6. Transfer Entropy: Quem Lidera o Cluster

### 6.1 Calculo

```python
def compute_transfer_entropy(x: pd.Series, y: pd.Series, lag: int = 1) -> float:
    """Compute transfer entropy from X to Y."""
    # Discretize returns
    x_disc = discretize(x.diff().dropna(), bins=5)
    y_disc = discretize(y.diff().dropna(), bins=5)

    # TE(X -> Y) = H(Y_{t+1} | Y_t) - H(Y_{t+1} | Y_t, X_t)
    y_future = y_disc.shift(-lag).dropna()
    y_present = y_disc.shift(0).dropna()
    x_present = x_disc.shift(0).dropna()

    # Align
    idx = y_future.index.intersection(y_present.index).intersection(x_present.index)
    y_f, y_p, x_p = y_future.loc[idx], y_present.loc[idx], x_present.loc[idx]

    # Joint probabilities
    p_yp_yf = pd.crosstab(y_p, y_f, normalize=True)
    p_yp_xp_yf = pd.crosstab([y_p, x_p], y_f, normalize=True)

    # TE = sum p(yf, yp, xp) * log2( p(yf|yp,xp) / p(yf|yp) )
    te = 0
    for yp in p_yp_yf.index:
        for yf in p_yp_yf.columns:
            p_yf_yp = p_yp_yf.loc[yp, yf]
            for xp in x_p.unique():
                if (yp, xp) in p_yp_xp_yf.index and yf in p_yp_xp_yf.columns:
                    p_yf_yp_xp = p_yp_xp_yf.loc[(yp, xp), yf]
                    if p_yf_yp > 0 and p_yf_yp_xp > 0:
                        te += p_yf_yp_xp * np.log2(p_yf_yp_xp / p_yf_yp)

    return te
```

### 6.2 Aplicacao: lider do cluster

```python
def find_cluster_leader(returns: pd.DataFrame, cluster: list[str]) -> str:
    """Find which asset leads the cluster via transfer entropy."""
    te_scores = {}
    for leader in cluster:
        total_te = 0
        for follower in cluster:
            if leader != follower:
                te = compute_transfer_entropy(returns[leader], returns[follower])
                total_te += te
        te_scores[leader] = total_te

    return max(te_scores, key=te_scores.get)
```

**Uso pratico:** se BTC lidera o cluster, sinais em BTC devem ser priorizados (o resto vai seguir).

## 7. Implementacao Tecnica

### 7.1 Sample Entropy

```python
def sample_entropy(series: np.ndarray, m: int = 2, r: float = 0.2) -> float:
    """Compute sample entropy of a time series."""
    n = len(series)
    r = r * np.std(series)

    # Create embedding vectors
    def _count_matches(dim):
        vectors = np.array([series[i:i+dim] for i in range(n - dim)])
        count = 0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                if np.max(np.abs(vectors[i] - vectors[j])) <= r:
                    count += 1
        return count

    b = _count_matches(m)      # matches of length m
    a = _count_matches(m + 1)  # matches of length m+1

    if b == 0:
        return float("inf")
    return -np.log(a / b)
```

### 7.2 Shannon Entropy

```python
def shannon_entropy(series: np.ndarray, bins: int = 10) -> float:
    """Compute Shannon entropy of a time series."""
    hist, _ = np.histogram(series, bins=bins, density=True)
    p = hist * np.diff(_)[0]  # convert density to probability
    p = p[p > 0]  # remove zeros
    return -np.sum(p * np.log2(p))
```

### 7.3 Hurst Exponent (R/S Analysis)

```python
def compute_hurst(series: np.ndarray) -> float:
    """Compute Hurst exponent using R/S analysis."""
    n = len(series)
    rs_values = []
    ns = []

    for size in [10, 20, 50, 100, 200]:
        if size > n:
            continue
        num_chunks = n // size
        rs_chunk = []
        for i in range(num_chunks):
            chunk = series[i * size : (i + 1) * size]
            mean = np.mean(chunk)
            deviations = np.cumsum(chunk - mean)
            r = np.max(deviations) - np.min(deviations)
            s = np.std(chunk)
            if s > 0:
                rs_chunk.append(r / s)
        if rs_chunk:
            rs_values.append(np.mean(rs_chunk))
            ns.append(size)

    if len(ns) < 2:
        return 0.5  # default to random walk

    # Regress log(R/S) on log(n)
    log_ns = np.log(ns)
    log_rs = np.log(rs_values)
    hurst = np.polyfit(log_ns, log_rs, 1)[0]

    return hurst
```

### 7.4 Bibliotecas

```python
# Numpy/Scipy (ja instalados)
import numpy as np
from scipy.stats import entropy

# Entropy especifica
# pip install nolds  # Hurst, SampEn, DFA, correlation dimension
import nolds

# Alternativa
# pip install antropy  # Various entropy measures
import antropy as ant
```

## 8. Metricas de Avaliacao

Como meta-filtro, a metrica principal e a **melhoria no Sharpe das estrategias filtradas**:

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Sharpe improvement (vs sem filtro) | +30% | +15% |
| Reducao de max drawdown | -30% | -15% |
| Falsos positivos (filtro bloqueou trade bom) | < 20% | < 35% |
| Falsos negativos (filtro permitiu trade ruim) | < 15% | < 25% |
| Latencia do calculo | < 1s | < 5s |

## 9. Backtest: O que validar

### 9.1 Validar que o filtro melhora resultados

```
Rodar STRAT-01 (Mean Reversion) SEM filtro de entropia:
  - Sharpe: X
  - Max DD: Y%

Rodar STRAT-01 COM filtro de entropia (so opera em MEAN_REVERT):
  - Sharpe: deve ser > X * 1.15
  - Max DD: deve ser < Y * 0.85
```

### 9.2 Validar deteccao de crises

```
Testar em periodos de crise conhecidos:
  - Luna crash (May 2022): entropia deve ter subido ANTES do crash
  - FTX collapse (Nov 2022): entropia deve ter subido
  - COVID crash (Mar 2020): entropia deve ter subido

Validar: filtro CHAOTIC ativado em pelo menos 2 de 3 crises
antes do evento principal (lookback > 0)
```

### 9.3 Estabilidade temporal

```
Calcular entropia em janelas de 100 periodos, deslizando por todos os dados
Validar: entropia nao deve ter saltos > 3 sigma sem evento de mercado
SE tem saltos sem evento: calculo esta instavel, ajustar parametros
```

## 10. Vantagens e Desvantagens

### Vantagens
- Detecta regime ANTES de outras estrategias falharem
- Base teorica solida (teoria da informacao)
- Funciona como meta-filtro para todas as estrategias
- Transfer entropy identifica lider do cluster
- Deteccao de crises antecipada

### Desvantagens
- Computacionalmente intensivo (SampEn e O(n^2))
- Sensivel a parametros (m, r, bins, window)
- Pode ter lag (janela rolling olha para tras)
- Dificil de validar standalone (precisa de estrategia base)
- Transfer entropy e cara de calcular para muitos pares

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Todas as estrategias | Critica | Filtro que ativa/desativa por regime |
| + Mean Reversion (STRAT-01) | Alta | So opera em regime MEAN_REVERT |
| + StatArb (STRAT-03) | Alta | So opera em regime MEAN_REVERT |
| + Momentum (STRAT-06) | Alta | So opera em regime TRENDING |
| + Price Action (STRAT-02) | Media | Reduz tamanho em regime TRANSITION |

## 12. Referencias

- MDPI Entropy 22(9):1064: "The Flow of Information in Trading: An Entropy Approach to Market Regimes"
- MDPI Entropy 23(4):484: "A Volatility Estimator Based on the Intrinsic Entropy Model"
- Scuola Normale Superiore (Pisa): "Measuring market efficiency: Shannon entropy of high-frequency financial time series"
- Springer: "Approximate entropy and sample entropy algorithms in financial time series analyses"
- Springer Nonlinear Dynamics: "Inverse sample entropy analysis for stock markets"
- Javihaus/Chaos-in-Time-Series: Lyapunov, Hurst, SampEn, fractal dimension
- chrisOTM/Hurst-Trend-Detection: Hurst exponent regime detector
- fractalcycles.com: Hurst exponent Python implementation guide
- Pincus (2008): "Approximate Entropy as an Irregularity Measure for Financial Data"
