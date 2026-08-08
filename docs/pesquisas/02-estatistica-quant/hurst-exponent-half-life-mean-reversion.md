# Topico: Hurst Exponent, Half-Life e Mean Reversion

**Data:** 2026-07-15
**Categoria:** Estatistica / Quant

## TL;DR

O Hurst exponent (H) classifica o comportamento de uma serie temporal: H < 0.5 indica mean reversion, H = 0.5 indica random walk, H > 0.5 indica persistencia (trending). Em cripto, H varia com a escala temporal e o regime de mercado: BTC e geralmente persistente em longo prazo, mas pode ser mean-reverting intradiario. O half-life da mean reversion, estimado via processo Ornstein-Uhlenbeck, quantifica quanto tempo o spread leva para decair a metade do desvio. Juntos, H e half-life definem se usar estrategia de mean reversion ou momentum: H < 0.5 com half-life curto favorece mean reversion, H > 0.5 favorece momentum.

## Explicacao para criancas

Imagine um rio. As vezes a agua flui sempre na mesma direcao (trending), as vezes ela volta sempre para o meio do canal (mean reversion), e as vezes ela se move aleatoriamente sem padrao (random walk). O Hurst exponent e como um medidor que diz qual desses tres comportamentos o rio tem. Se o numero e menor que 0.5, a agua sempre volta para o centro: aposte que ela vai voltar. Se e maior que 0.5, a agua segue a correnteza: aposte que ela vai continuar na mesma direcao. Se e exatamente 0.5, nao da para apostar, e puramente aleatorio.

## Como funciona tecnicamente

### Hurst exponent: definicao

O Hurst exponent (H) quantifica a memoria longa de uma serie temporal. Origina-se da analise R/S (rescaled range) desenvolvida por Harold Edwin Hurst para modelar o fluxo do rio Nilo.

Classificacao:

| Valor de H | Comportamento | Estrategia |
|---|---|---|
| 0 < H < 0.5 | Anti-persistente (mean reverting) | Mean reversion |
| H = 0.5 | Random walk (Browniano) | Nenhuma (market efficient) |
| 0.5 < H < 1 | Persistente (trending) | Momentum |
| H = 1 | Correlacao perfeita | Impossivel na pratica |

Relacao com a dimensao fractal: D = 2 - H. Para H = 0.5, D = 1.5 (Browniano). Para H = 0, D = 2 (espaco totalmente preenchido, maxima anti-persistencia). Para H = 1, D = 1 (linha reta, maxima persistencia).

### Metodo 1: R/S analysis (Rescaled Range)

O metodo classico. Para uma serie de N observacoes, dividir em sub-séries de tamanho n, e para cada uma calcular:

1. Media m da sub-serie.
2. Desvio acumulado Z_t = sum(X_i - m) para i = 1..t.
3. Range R = max(Z_t) - min(Z_t).
4. Desvio padrao S da sub-serie.
5. Rescaled range R/S = R / S.

A relacao de scaling e:

    E[R/S] = c * n^H

Estimando H pela regressao log-log de R/S contra n:

    log(E[R/S]) = log(c) + H * log(n)

A inclinacao da regressao e H.

```python
import numpy as np

def hurst_rs(series: np.ndarray, max_lag: int = 100) -> float:
    """Estimate Hurst exponent via R/S analysis."""
    lags = range(2, max_lag)
    rs_values = []
    for lag in lags:
        # Dividir em sub-series de tamanho lag
        n_subseries = len(series) // lag
        rs = []
        for i in range(n_subseries):
            chunk = series[i * lag : (i + 1) * lag]
            mean = np.mean(chunk)
            deviations = np.cumsum(chunk - mean)
            r = np.max(deviations) - np.min(deviations)
            s = np.std(chunk)
            if s > 0:
                rs.append(r / s)
        rs_values.append(np.mean(rs))
    # Regressao log-log
    h = np.polyfit(np.log(lags), np.log(rs_values), 1)[0]
    return float(h)
```

### Metodo 2: DFA (Detrended Fluctuation Analysis)

DFA e mais robusto que R/S porque remove tendencias locais antes de calcular a flutuacao. E o metodo preferido para series nao-estacionarias com tendencias.

Procedimento:

1. Calcular o perfil cumulativo: Y_t = sum(X_i - mean(X)).
2. Dividir Y em janelas de tamanho n.
3. Em cada janela, ajustar uma tendencia (linear ou polinomial) e calcular os residuos.
4. Calcular a flutuacao: F(n) = sqrt(mean(residuals^2)).
5. Repetir para varios n.
6. A relacao de scaling e F(n) ~ n^alpha.

Para uma serie estacionaria: H = alpha. Para uma serie com tendencia: H = alpha (DFA ja remove a tendencia).

```python
import numpy as np

def hurst_dfa(series: np.ndarray, max_lag: int = 100) -> float:
    """Estimate Hurst exponent via DFA."""
    # Perfil cumulativo
    profile = np.cumsum(series - np.mean(series))
    lags = np.unique(np.logspace(0.5, np.log10(max_lag), 20).astype(int))
    fluctuations = []
    for lag in lags:
        # Dividir em janelas nao sobrepostas
        n_windows = len(profile) // lag
        rms = []
        for i in range(n_windows):
            window = profile[i * lag : (i + 1) * lag]
            # Ajustar tendencia linear
            x = np.arange(lag)
            coeffs = np.polyfit(x, window, 1)
            trend = np.polyval(coeffs, x)
            residuals = window - trend
            rms.append(np.sqrt(np.mean(residuals ** 2)))
        fluctuations.append(np.mean(rms))
    # Regressao log-log
    h = np.polyfit(np.log(lags), np.log(fluctuations), 1)[0]
    return float(h)
```

### Metodo 3: Generalized Hurst Exponent (GHE)

Baseado na estrutura de momentos de ordem q:

    K_q(tau) = E[|X(t+tau) - X(t)|^q] ~ tau^(q*H(q))

Para q = 2, K_2(tau) ~ tau^(2H), entao H = slope / 2. GHE permite detectar multifractalidade: se H(q) varia com q, a serie e multifractal.

### Metodo 4: Wavelet-based

Usa wavelet transforms para estimar H. Mais robusto a nao-estacionariedade e ruido. Implementado em bibliotecas como `pywt` (PyWavelets).

### Comparacao dos metodos

| Metodo | Robustez a tendencia | Complexidade | Quando usar |
|---|---|---|---|
| R/S | Baixa (nao remove tendencia) | Baixa | Series estacionarias, rapido |
| DFA | Alta (remove tendencia local) | Media | Series nao-estacionarias, preferido |
| GHE | Media | Media | Detectar multifractalidade |
| Wavelet | Alta | Alta | Series complexas, ruidosas |

### Half-life via Ornstein-Uhlenbeck

O processo Ornstein-Uhlenbeck modela mean reversion continua:

    dX_t = theta * (mu - X_t) dt + sigma dW_t

Onde theta e a velocidade de mean reversion. O half-life e:

    half_life = ln(2) / theta

Estimacao discreta via regressao AR(1):

    X_t - X_{t-1} = a + b * X_{t-1} + epsilon_t

    theta = -b
    half_life = -ln(2) / b    (requer b < 0)

Se b >= 0, a serie nao e mean-reverting. Se b ~ 0, a serie e um random walk (half_life -> infinito).

```python
import numpy as np
import statsmodels.api as sm

def half_life(series: pd.Series) -> float:
    """Estimate half-life of mean reversion via AR(1)."""
    lag = series.shift(1).dropna()
    delta = series.diff().dropna()
    lag, delta = lag.align(delta, join='inner')
    model = sm.OLS(delta, sm.add_constant(lag)).fit()
    b = model.params.iloc[1]
    if b >= 0:
        return float('inf')
    return float(-np.log(2) / b)
```

### Relacao entre Hurst e half-life

H e half-life sao conceitos complementares:
- H < 0.5 indica que a serie e mean-reverting, mas nao diz quao rapido.
- half-life quantifica a velocidade da mean reversion em unidades de tempo.
- Uma serie com H = 0.3 pode ter half-life de 5 dias ou 50 dias. H diz a direcao, half-life diz a magnitude.

**Combinados para decisao de estrategia**:

| H | Half-life | Decisao |
|---|---|---|
| < 0.3 | < 10 dias | Mean reversion agressiva |
| 0.3-0.5 | 10-50 dias | Mean reversion moderada |
| ~0.5 | infinito | Nenhuma (random walk) |
| 0.5-0.7 | N/A | Momentum suave |
| > 0.7 | N/A | Momentum agressivo |

### Hurst local (rolling Hurst)

H nao e constante: ele muda com o regime de mercado. Um ativo pode ser trending em um periodo e mean-reverting em outro. O Hurst local calcula H em uma janela deslizante:

```python
def rolling_hurst(series: pd.Series, window: int = 100) -> pd.Series:
    """Rolling Hurst exponent via DFA."""
    result = []
    for i in range(len(series) - window + 1):
        h = hurst_dfa(series.iloc[i:i+window].values)
        result.append(h)
    return pd.Series(result, index=series.index[window-1:])
```

### Armadilhas

1. **Tamanho da amostra**: estimar H com menos de 100 pontos e pouco confiavel. R/S precisa de pelo menos 50-100 observacoes. DFA e mais robusto mas tambem sofre com amostras pequenas.

2. **Multifractalidade**: se a serie e multifractal (H varia com a escala), um unico H e enganador. Cripto e frequentemente multifractal. Testar H em varias escalas temporais.

3. **Regime dependence**: H muda com o regime. Estimar H sobre todo o periodo da uma media que pode nao representar o estado atual. Sempre usar rolling H.

4. **DFA vs R/S divergencia**: se DFA e R/S dao resultados muito diferentes, a serie provavelmente tem tendencias que R/S nao remove. Confiar em DFA.

5. **Half-life e cointegracao**: half-life so e meaningful se a serie e realmente mean-reverting. Estimar half-life em uma serie com H > 0.5 e invalido (a serie nao reverte).

## Estado do mercado em 2026

A pesquisa em Hurst exponent para cripto evoluiu em varias direcoes:

1. **Multi-scale DFA em cripto**: um paper de 2025 na Physica A investigou correlacoes de longo alcance nas top 5 criptos (2017-2023) usando multi-scale DFA. Encontrou persistencia (H > 0.5) em 4 das 5, com apenas XRP exibindo random walk (H ~ 0.5). ETH foi unico em manter persistencia forte tanto em curto quanto em longo prazo. ETH e XRP mostraram efeitos persistentes em periodos de volatilidade de mercado. Os autores sugerem usar H como ferramenta para monitorar continuacao ou reversao de tendencia e detectar riscos sistemicos.

2. **Hurst + LSTM para previsao**: um paper de 2025 no Computational Economics estudou memoria em dados de cripto de minuto a minuto. Calculou H com janela deslizante e encontrou relacao inversa entre H e o erro relativo de previsao com LSTM: series que desviam do regime estocastico (H != 0.5) sao mais previsiveis. Desenvolveram um modelo LSTM-Browniano que captura a natureza estocastica para descrever a difusao de previsao.

3. **Anti-persistencia como sinal de pairs trading**: um paper de 2024 no Mathematics (MDPI) propus usar o Hurst local como sinal para abrir trades em pairs trading de cripto. Mostraram que spreads com H < 0.5 (anti-persistente) revertem a media significativamente mais rapido. O efeito e universal across pairs com diferentes niveis de co-movimento. Todas as estrategias backtested que incluem H < 0.5 como indicador resultaram em lucro. Conclusao: H e um indicador significativo para detectar oportunidades de pairs trading.

4. **Multifractalidade em cripto**: um paper de 2025 no Fractals and Fractal Geometry (MDPI) aplicou MFCCA e MFDFA em BTC, ETH, DEX e NFT. Encontrou que a fonte primaria de multifractalidade sao as correlacoes temporais, nao as caudas pesadas. Sem as correlacoes temporais, a multifractalidade desaparece. Isso tem implicacao direta: a multifractalidade e estrutural, nao um artefato de outliers.

5. **Rough volatility em cripto**: pesquisas recentes (Springer, Digital Finance) mostram que cripto tem rough volatility (H < 0.5 para a volatilidade, nao para o return) e jumps correlacionados. Isso e distinto de equities, onde rough volatility tambem existe mas com parametros diferentes. A implicacao e que modelos de volatilidade padrao (GARCH) podem ser insuficientes e modelos rough volatility (como rough Bergomi) podem ser mais apropriados.

## Ferramentas e APIs disponiveis

| Ferramenta | Uso | Notas |
|---|---|---|
| `nolds` | Hurst (R/S, DFA), lyapunov, DFA | Biblioteca Python dedicada a analise nao-linear |
| `hurst` (pip) | Hurst exponent via R/S e DFA | Simples, focado em H |
| `statsmodels` | AR(1) para half-life | OLS regression |
| `MFDFA` (pip) | Multifractal DFA | Para multifractalidade |
| `pywt` (PyWavelets) | Wavelet-based Hurst | Mais robusto a ruido |
| `arch` | Para volatilidade rough | Modelos de volatilidade |
| `antropy` | Entropia e complexidade | Inclui H como medida de complexidade |

Biblioteca recomendada: `nolds` e a mais completa e bem documentada para analise nao-linear em Python, incluindo Hurst (R/S e DFA), DFA, lyapunov exponent, e correlation dimension.

```python
import nolds

# R/S Hurst
h_rs = nolds.hurst_rs(series)

# DFA Hurst
h_dfa = nolds.dfa(series)
```

## Por que importa para o crypto-correl-bot

**O que ja temos no projeto**:
- Calculo de Hurst (mencionado no escopo do bot).
- Calculo de half-life (mencionado no escopo do bot).

**O que falta ou poderia ser melhorado**:
1. **Rolling Hurst**: se o bot calcula H estatico sobre todo o periodo, o valor e pouco util porque H muda com o regime. Implementar rolling Hurst com janela de 100-250 periodos.
2. **DFA ao inves de R/S**: se o bot usa R/S, migrar para DFA. R/S nao remove tendencias e pode superestimar H em series com drift. DFA e o padrao moderno.
3. **H como meta-filtro de estrategia**: o bot deveria usar H para decidir entre mean reversion e momentum automaticamente. Se H < 0.5 para um par, ativar mean reversion. Se H > 0.6, ativar momentum. Se H ~ 0.5, nao tradar.
4. **Half-life como horizonte de held**: usar o half-life para definir quanto tempo held uma posicao de mean reversion. Se half_life = 10 dias, held maximo de ~20 dias (2x half-life).
5. **H local para pairs trading**: o paper de 2024 no Mathematics mostra que H < 0.5 no spread e um sinal forte de mean reversion rapida. Integrar isso no pipeline de pairs trading: so abrir posicoes quando o Hurst local do spread for anti-persistente.
6. **Multifractalidade como alerta de risco**: se a serie for multifractal (H varia muito entre escalas), a previsao e mais dificil e o risco e maior. Usar MFDFA para detectar isso e reduzir tamanho de posicao.
7. **Rough volatility detection**: se H da volatilidade (nao do return) for < 0.5, a volatilidade e rough. Isso sugere que GARCH pode ser insuficiente e modelos rough volatility seriam mais apropriados.

## Referencias

1. Long-range correlations in cryptocurrency markets: A multi-scale DFA approach (Physica A, 2025). https://ideas.repec.org/a/eee/phsmap/v661y2025ics037843712500069x.html
2. Memory Persistence in Minute Frequency Cryptocurrencies: Hurst-Exponent and LSTM Brownian Diffusion Network (Computational Economics, 2025). https://ideas.repec.org/a/kap/compec/v66y2025i5d10.1007_s10614-024-10831-x.html
3. Cryptocurrencies and Long-Range Trends (MDPI, 2023). https://www.mdpi.com/2227-7072/11/1/40
4. Anti-Persistent Values of the Hurst Exponent Anticipate Mean Reversion in Pairs Trading: Cryptocurrencies Market (Mathematics, 2024). https://www.mdpi.com/2227-7390/12/18/2911
5. Multifractality and Its Sources in the Digital Currency Market (Fractals and Fractal Geometry, MDPI, 2025). https://www.mdpi.com/1999-5903/17/10/470
6. nolds - Python library for nonlinear time series analysis (Hurst, DFA). https://pypi.org/project/nolds/
