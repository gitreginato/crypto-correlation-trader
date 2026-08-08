# Topico: Regime Detection, HMM, Entropy e Ruptures

**Data:** 2026-07-15
**Categoria:** Estatistica / Quant

## TL;DR

Regime detection identifica estados de mercado distintos (bull, bear, range, caotico) e permite que estrategias se adaptem. Hidden Markov Models (HMM) sao o metodo dominante: modelam estados latentes com transicoes probabilisticas. Entropy (Shannon, approximate, sample) mede o grau de aleatoriedade e detecta regimes caoticos ou ineficientes. Structural breaks (ruptures, Chow, Bai-Perron) detectam mudancas estruturais no nivel ou variancia da serie. Para o crypto-correl-bot, esses metodos funcionam como meta-filtros: so ativar mean reversion em regime range, so ativar momentum em regime trending, e desligar tudo em regime caotico.

## Explicacao para criancas

Imagine que o mercado e como o clima: tem dias de sol (bull), dias de chuva (bear), e dias nublados sem direcao (range). Se voce veste roupa de chuva todo dia, vai passar calor nos dias de sol. Se usa protetor todo dia, vai se molhar na chuva. Regime detection e como um meteorologista que diz qual clima estamos tendo agora, para que voce se vista adequadamente. HMM e o modelo que aprende os padroes do clima. Entropy mede quao imprevisivel o clima esta. Ruptures detectam quando uma estacao mudou abruptamente.

## Como funciona tecnicamente

### Hidden Markov Models (HMM)

Um HMM modela um sistema que passa por estados ocultos (nao observaveis diretamente) que seguem uma cadeia de Markov. As observacoes (returns, volatilidade) sao geradas pelos estados.

Componentes:
- **Estados ocultos** S_t: ex: {bull, bear, range} ou {calm, volatile, chaotic}.
- **Probabilidades de transicao** A: A[i,j] = P(S_{t+1}=j | S_t=i). Matriz N x N.
- **Probabilidades de emissao** B: P(O_t | S_t=i). Define como as observacoes sao geradas em cada estado.
- **Distribuicao inicial** pi: P(S_0 = i).

Para HMM Gaussiano (o mais comum em finance), cada estado emite observacoes de uma Gaussiana com media e variancia propria:

    O_t | S_t = i ~ N(mu_i, sigma_i^2)

**Estimacao**: o algoritmo Baum-Welch (EM) estima os parametros (A, B, pi) por maximum likelihood.

**Inferencia**: o algoritmo de Viterbi encontra a sequencia de estados mais provavel dado as observacoes. O forward-backward calcula a probabilidade marginal de cada estado em cada instante.

### HMM para regime detection em finance

Estados tipicos:

| Estados | Interpretacao | O que ativar |
|---|---|---|
| 2 estados | bull / bear | Momentum long / flat |
| 3 estados | bull / bear / range | Momentum / flat / mean reversion |
| 4 estados | bull / bear / range / chaotic | Momentum / flat / mean reversion / desligar |

Features de input comuns:
- Returns diarios (ou log returns).
- Volatilidade realizada (rolling std).
- Volume.
- RSI, MACD (indicadores tecnicos).
- Macro indicators (VIX, rates).

**Armadilha do HMM de 2 estados**: 2 estados sao frequentemente insuficientes. O estado "bear" em cripto inclui tanto o crash (alta volatilidade, return negativo) quanto a recuperacao lenta (baixa volatilidade, return levemente positivo). 3 estados e o minimo recomendado.

```python
from hmmlearn.hmm import GaussianHMM
import numpy as np

def fit_hmm_regimes(returns: np.ndarray, n_states: int = 3) -> dict:
    """Fit Gaussian HMM for regime detection."""
    model = GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=100,
        random_state=42
    )
    model.fit(returns.reshape(-1, 1))

    # Viterbi: sequencia de estados mais provavel
    states = model.predict(returns.reshape(-1, 1))

    # Probabilidades marginais de cada estado
    probs = model.predict_proba(returns.reshape(-1, 1))

    return {
        "states": states,
        "probabilities": probs,
        "means": model.means_.flatten(),
        "transmat": model.transmat_,
    }
```

### Interpretacao dos estados

Apos fitar o HMM, os estados nao vem rotulados. E preciso interpreta-los olhando os parametros:

- Estado com media de return alta e variancia moderada: bull.
- Estado com media de return negativa e variancia alta: bear (crash).
- Estado com media proxima de zero e variancia baixa: range (calmo).
- Estado com variancia extrema: chaotic (volatilidade explosiva).

Ordenar os estados por variancia e uma heuristica util: o de menor variancia e tipicamente o range, o de maior e o chaotic ou bear.

### Entropy: Shannon, Approximate, Sample

#### Shannon Entropy

Mede a aleatoriedade de uma distribuicao de probabilidade:

    H(X) = -sum(p_i * log2(p_i))

Para series temporais, simbolizar os returns em bins e calcular a frequencia de cada simbolo:

1. Dividir o range de returns em B bins.
2. Calcular p_i = frequencia do bin i.
3. H = -sum(p_i * log2(p_i)).

**Interpretacao**:
- H alto: returns bem distribuidos, maxima aleatoriedade, mercado eficiente.
- H baixo: returns concentrados em poucos bins, padrao detectavel, mercado ineficiente.
- H maximo = log2(B) (distribuicao uniforme).

Quedas significativas em H sinalizam previsibilidade (padroes exploraveis). Aumentos em H sinalizam maior eficiencia (mais dificil de prever).

#### Approximate Entropy (ApEn)

Mede irregularidade na serie temporal. Nao exige simbolizacao: trabalha com a serie diretamente.

ApEn(m, r, N):
1. Construir vetores de embedding de dimensao m: u_i = [x_i, x_{i+1}, ..., x_{i+m-1}].
2. Para cada u_i, contar quantos u_j estao dentro de distancia r (tolerancia).
3. Calcular C_i^m(r) = fraction de u_j dentro de r.
4. ApEn = ln(mean(C_i^m)) - ln(mean(C_i^{m+1})).

Parametros tipicos: m = 2, r = 0.2 * std(series).

**Interpretacao**:
- ApEn baixo: serie regular, previsivel, padrao repetitivo.
- ApEn alto: serie irregular, complexa, menos previsivel.

**Bias**: ApEn tem viis de self-matching (conta o proprio vetor como match), levando a subestimacao da irregularidade. Por isso, Sample Entropy e preferida.

#### Sample Entropy (SampEn)

Similar a ApEn mas sem self-matching. Mais consistente e menos enviesada.

SampEn(m, r, N):
1. Construir vetores u_i de dimensao m e m+1.
2. Contar pares de vetores dentro de distancia r, excluindo self-matching.
3. A^m = numero de matches de dimensao m.
4. B^m = numero de matches de dimensao m+1.
5. SampEn = -ln(A^m / B^m).

Estudos de 2022 confirmaram que SampEn e mais consistente e homogenea que ApEn para analise financeira, recomendando SampEn como padrao.

```python
import nolds

# Sample entropy
sampen = nolds.sampen(series, emb_dim=2, tolerance=0.2)
```

#### Aplicacao: entropy como detector de regime caotico

Entropy baixa => padrao detectavel => mercado ineficiente => possivel opportunity.
Entropy alta => aleatorio => mercado eficiente => estrategia tem dificuldade.

Em cripto, entropy varia com o regime:
- Bull market com trending forte: entropy baixa (padrao direcional claro).
- Crash: entropy inicialmente baixa (panic selling direcional) depois alta (chaos).
- Range lateral: entropy media.

### Structural breaks

Structural breaks sao mudancas abruptas na estrutura da serie: nivel, tendencia, ou variancia mudam em um ponto no tempo.

#### Chow test

Testa se os parametros de uma regressao sao iguais antes e depois de um ponto conhecido:

    H0: parametros iguais (sem break)
    H1: parametros diferentes (break em t*)

Exige conhecer o ponto t* a priori. Util para validar breaks em datas de eventos (ex: FTX collapse em nov 2022, ETF approval em jan 2024).

#### Bai-Perron

Detecta multiple structural breaks em pontos desconhecidos. Usa minimizacao da soma de residuos quadrados (SSR) com penalizacao pelo numero de breaks.

    min sum_{j=1}^{m+1} sum_{t=T_{j-1}+1}^{T_j} (y_t - x_t' * beta_j)^2 + penalty(m)

Onde T_j sao os breakpoints. O algoritmo testa sequencialmente para encontrar o numero otimo de breaks.

#### CUSUM (Cumulative Sum)

Detecta mudancas na media ou variancia. Calcula a soma cumulativa dos desvios da media:

    CUSUM_t = sum_{i=1}^{t} (x_i - mean) / std

Se CUSUM cruza um limite, um break e detectado. Util para monitoring online.

#### Zivot-Andrews

Teste de raiz unitaria que permite um break endogeno. Diferente do ADF padrao, que assume estrutura constante.

### ruptures: change point detection em Python

```python
import ruptures as rpt

def detect_breaks(series: np.ndarray, n_bkps: int = 3) -> list:
    """Detect structural breaks via dynamic programming."""
    algo = rpt.Dynp(model="l2").fit(series)
    breakpoints = algo.predict(n_bkps=n_bkps)
    return breakpoints

# PELT: numero de breaks otimo automaticamente
def detect_breaks_pelt(series: np.ndarray, pen: float = 10) -> list:
    """PELT algorithm for optimal segmentation."""
    algo = rpt.Pelt(model="rbf").fit(series)
    return algo.predict(pen=pen)

# Visualizar
rpt.display(series, true_bkps, detected_bkps)
```

Algoritmos disponiveis no ruptures:
- **Dynp**: dynamic programming, numero de breaks fixo. Computacionalmente equivalente a Bai-Perron mas usa BIC ao inves de F-tests sequenciais.
- **Pelt**: numero de breaks otimo, penalizacao. Mais rapido que Dynp.
- **Binseg**: binary segmentation, aproximacao rapida.
- **BottomUp**: bottom-up segmentation.
- **Window**: sliding window, mais rapido mas menos preciso.

Modelos de custo: "l1" (mudanca na media), "l2" (mudanca na media, quadratico), "rbf" (mudanca na distribuicao), "normal" (mudanca na media e variancia), "ar" (mudanca em modelo AR).

### HMM + Entropy + Ruptures: pipeline combinado

O uso ideal e hierarquico:

1. **Ruptures**: detectar breaks estruturais. Cada segmento entre breaks e um regime candidato.
2. **HMM**: dentro de cada segmento, fitar HMM para identificar sub-estados (bull/bear/range).
3. **Entropy**: calcular entropy rolling. Se entropy cair, o regime esta ficando mais previsivel (opportunity). Se subir, mais caotico (caution).

### Armadilhas

1. **HMM label switching**: os estados sao arbitrarios. Se voce roda o HMM duas vezes, estado 0 pode ser bull em uma rodada e bear em outra. Sempre rotular pelos parametros (media, variancia), nao pelo indice.

2. **Numero de estados**: usar BIC ou AIC para escolher o numero de estados. Mais estados nem sempre e melhor (overfitting). 2-4 e o intervalo pratico.

3. **HMM assume Markov**: a probabilidade de transicao depende so do estado atual, nao do historico. Em cripto, regimes tem duracao tipica (bear markets duram meses), violando a assumacao Markov. HMM hierarquico resolve isso parcialmente.

4. **Entropy e sensivel a janela**: entropy calculada em janelas muito pequenas e ruidosa. Janelas muito grandes suavizam mudancas. 50-100 observacoes e o intervalo tipico.

5. **Ruptures e offline**: a maioria dos metodos em ruptures e offline (usa toda a serie). Para uso online, usar CUSUM ou MOSUM monitoring.

## Estado do mercado em 2026

1. **Ensemble HMM voting**: um paper de 2025 no Data Science in Finance and Economics combinou ensemble learning (bagging, boosting) com HMM para detectar regime shifts. Propuseram hybrid voting classifiers que integram HMM com modelos ensemble para增强 robustez. Usaram ETFs de Russell 3000 e S&P 500. Demonstraram que regime-aware strategies suportam tomada de decisao informada.

2. **Adaptive Hierarchical HMM (AH-HMM)**: um paper de 2026 no MDPI (Journal of Risk and Financial Management) introduziu AH-HMM onde transicoes de regime dependem de um meta-regime nao observado que reflete o ambiente macro-financeiro. Cada meta-regime define sua propria matriz de transicao. Usando VIX como proxy do meta-regime, o modelo identificou turning points incluindo a Global Financial Crisis, COVID shock, e o tightening cycle de 2022. O modelo adaptativo teve maior in-sample likelihood e forecasts out-of-sample competitivos, com melhor cobertura de VaR que HMMs convencionais.

3. **HMM-SVM-MKL hybrid**: um paper de abril 2025 no Springer (Methodology and Computing in Applied Probability) combinou HMM com SVM/MKL (multi-kernel learning) em abordagem generative-discriminative. O HMM produz feature embeddings generativos a partir de dados de microestrutura, que alimentam o SVM para discriminacao preditiva. Melhorou acuracia de classificacao de regimes em alta frequencia, superando logistic classifiers e feed-forward networks.

4. **Robust Rolling Regime Detection (R2-RD)**: um paper de 2024 no SSRN propus o framework R2-RD que re-treina adaptativamente com streaming data, usando temporal ensemble, label assignment, e threshold policies. Data-driven model selection escolhe o melhor modelo de uma variedade de latent variable models. Demonstracao em mercados de futuros e dados macro.

5. **Feature selection para HMM**: um paper de 2025 no ACM examinou quais features produzem regime structure significativo. Descobriram que returns diarios sozinhos produzem valid variance regimes. Adicionar volatilidade rolling preserva a estrutura. Mas adicionar absolute return colapsa os regimes para 53 stocks porque introduz informacao redundante. Trend features baseadas em returns cumulativos de 20, 60 e 100 dias preservam regime structure. Volatility features produzem variance-dominated regimes, trend features produzem direction-dominated regimes.

6. **Entropy para meme stocks e ineficiencia**: um paper no Decisions in Economics and Finance (Springer) usou Shannon entropy para detectar time-varying regimes. Valores baixos de entropy correspondem a periodos de previsibilidade (estrategias lucrativas), interpretados como ineficiencia de mercado. Aplicaram a meme stocks (GameStop) vs IT stocks em 2020-2021, mostrando que entropy captura periodos de coordinacao de retail investors.

## Ferramentas e APIs disponiveis

| Ferramenta | Uso | Notas |
|---|---|---|
| `hmmlearn` | Gaussian HMM, GMM HMM | Padrao Python para HMM |
| `ruptures` | Change point detection | Dynp, Pelt, Binseg, BottomUp, Window |
| `statsmodels` | Chow test, Zivot-Andrews | Break detection classico |
| `nolds` | Sample entropy, ApEn | Entropy e complexidade |
| `antropy` | Shannon, approximate, sample entropy | Focada em entropia |
| `pyhhmm` | Hierarchical HMM | Para AH-HMM |
| `fHMM` (R) | HMM para series financeiras | Journal of Statistical Software 2024 |
| `pomegranate` | HMM, Bayesian networks | Alternativa ao hmmlearn |

Biblioteca recomendada: `hmmlearn` para HMM, `ruptures` para breaks, `nolds` ou `antropy` para entropy. A combinacao das tres cobre o pipeline completo.

```python
# Pipeline completo
from hmmlearn.hmm import GaussianHMM
import ruptures as rpt
import nolds

def regime_pipeline(returns: np.ndarray) -> dict:
    """Combined regime detection: breaks + HMM + entropy."""
    # 1. Detectar breaks estruturais
    algo = rpt.Pelt(model="rbf").fit(returns.reshape(-1, 1))
    breaks = algo.predict(pen=10)

    # 2. Fitar HMM no periodo mais recente
    recent = returns[breaks[-2]:breaks[-1]] if len(breaks) > 1 else returns
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100)
    hmm.fit(recent.reshape(-1, 1))
    states = hmm.predict(returns.reshape(-1, 1))

    # 3. Sample entropy (rolling ou global)
    sampen = nolds.sampen(returns, emb_dim=2, tolerance=0.2)

    return {
        "breaks": breaks,
        "states": states,
        "hmm_means": hmm.means_.flatten(),
        "hmm_transmat": hmm.transmat_,
        "sample_entropy": sampen,
    }
```

## Por que importa para o crypto-correl-bot

**O que ja temos no projeto**:
- Calculo de HMM regimes (mencionado no escopo do bot).
- Calculo de structural breakpoints (mencionado no escopo do bot).

**O que falta ou poderia ser adicionado**:
1. **Entropy como meta-filtro**: o bot provavelmente nao calcula entropy. Adicionar sample entropy rolling como detector de regime caotico. Se SampEn subir acima de um threshold, desligar estrategias directional e reduzir exposicao.
2. **3+ estados no HMM**: se o bot usa 2 estados (bull/bear), upgrade para 3 (bull/bear/range) ou 4 (bull/bear/range/chaotic). 2 estados e insuficiente para distinguir range de crash.
3. **Rotulacao automatica de estados**: implementar logica que rotula estados pelos parametros (media, variancia) ao inves de indice fixo. Evita label switching.
4. **Meta-filtro integrado**: usar o regime detectado como gate para todas as estrategias. Mean reversion so ativa em regime range. Momentum so ativa em regime trending. Tudo desliga em regime chaotic.
5. **Ruptures para re-clusterizacao**: quando ruptures detecta um break, re-clusterizar o grafo de correlacao. A estrutura de correlacao muda apos breaks.
6. **Feature selection**: baseado no paper de 2025 do ACM, usar returns diarios + volatilidade rolling como features do HMM. Evitar absolute return (colapsa regimes). Adicionar trend features (cumulative returns de 20/60/100 dias).
7. **AH-HMM hierarquico**: como upgrade de research, considerar HMM hierarquico onde um meta-regime (baseado em VIX crypto ou BTC dominance) define a matriz de transicao dos sub-regimes. Isso captura mudancas estruturais que HMM plano nao captura.
8. **CUSUM online**: implementar CUSUM monitoring para detectar breaks em tempo real (streaming), ao inves de depender so de ruptures offline.

## Referencias

1. A forest of opinions: multi-model ensemble-HMM voting framework (Data Science in Finance and Economics, 2025). https://doi.org/10.3934/dsfe.2025019
2. Adaptive Hierarchical Hidden Markov Models for Structural Market Change (MDPI JRFM, 2026). https://www.mdpi.com/1911-8074/19/1/15
3. Generative-Discriminative Machine Learning Models for High-Frequency Financial Regime Classification (Springer, 2025). https://link.springer.com/article/10.1007/s11009-025-10148-8
4. Robust Rolling Regime Detection (R2-RD) (SSRN, 2024). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729435
5. Feature Selection for HMM Regime Detection (ACM, 2025). https://doi.org/10.1145/3816713.3819068
6. ruptures: change point detection in Python. https://centre-borelli.github.io/ruptures-docs/
7. smadinen7 - financial-structural-break-forecasting: Chow, CUSUM, Bai-Perron. https://github.com/smadinen7/financial-structural-break-forecasting
8. Variance of entropy for testing time-varying regimes: meme stocks (Decisions in Economics and Finance, Springer). https://doi.org/10.1007/s10203-023-00427-9
9. Approximate entropy and sample entropy algorithms in financial time series analyses (Procedia Computer Science, 2022). https://doi.org/10.1016/j.procs.2022.09.058
