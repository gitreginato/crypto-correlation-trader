# Topico: Mean Reversion por Correlacao entre Ativos

**Data:** 2026-07-15
**Categoria:** Estrategia de Trading

## TL;DR

Mean reversion por correlacao e a aposta de que um ativo que se descola do seu cluster de correlacionados volta a media do grupo. Calcula-se o z-score do descolamento (retorno do ativo menos retorno medio do cluster) e entra quando passa de 2 desvios. Ja implementado em `src/strategy/mean_reversion.py` como STRAT-01, com filtro de regime via Hurst exponent. Pesquisas de 2025 mostram que a versao baseada em cointegracao entre pares bate buy-and-hold apos custos, com ganho de 22 a 41 bps por trade em horizontes de 15 a 240 minutos. A versao por cluster e menos testada academicamente, mas a logica e a mesma: spreads esticados convergem. Funciona em mercados laterais, falha em trending forte, por isso o filtro de regime e obrigatorio.

A distincao chave, segundo o blog anomiq.io, e entre single-asset reversion (um ativo voltando a propria media, rejeitado pela evidencia por ficar exposto a direcao do mercado) e market-neutral reversion (spread entre ativos correlacionados, que bate buy-and-hold apos custos). A estrategia por cluster e market-neutral por construcao: cada sinal aposta na convergencia do ativo com o grupo, nao na direcao do mercado.

O ponto pratico mais importante das pesquisas de 2025: a logica de entrada e facil, o exit e onde o edge vive ou morre. Exit tight em z-score corta cerca de 64% dos vencedores antes da reversion completar. Trabalhar o exit com stop em bps e trailing resolve boa parte do problema.

## Explicacao para criancas

Imagina que voce tem um grupo de amigos que sempre andam juntos na escola. Eles entram juntos, saem juntos, comem juntos. Um dia, um deles sai sozinho para o outro lado do patio. Provavelmente ele vai voltar para o grupo logo, porque eles sempre ficam juntos. Em trading, o grupo e o cluster de moedas que se movem juntas (BTC, ETH, SOL, BNB). Quando uma delas faz algo muito diferente das outras, apostamos que ela vai voltar perto delas. Compramos se ela caiu demais (vai subir de volta) ou vendemos se subiu demais (vai cair de volta).

## Como funciona tecnicamente

### Formacao do cluster

O primeiro passo e construir a matriz de correlacao dos returns sobre uma janela deslizante (default 90 dias) e formar clusters. O projeto usa `CorrelationMatrix(method="pearson")` seguido de `CorrelationGraph(threshold=0.5)` com deteccao de comunidades (Louvain). Cada cluster resultante e um grupo de ativos que tendem a se mover juntos.

Cuidado critico: correlacao direta dos returns em cripto e dominada por BTC. O AGENTS.md do projeto alerta que e preciso remover o market mode via PCA antes de clusterizar. Hoje o codigo em `_get_clusters` ainda calcula correlacao direta. A residualizacao via PCA (projetar fora o primeiro componente principal) antes de construir o grafo e a recomendacao das pesquisas de 2025, seguida pelo repositorio Aroesler1/crypto_stat_arb. Sem isso, todos os ativos correlacionam com BTC e os clusters ficam degenerados.

### Regras de entrada

Para cada ativo `i` dentro de um cluster `C` de ativos correlacionados:

```
cluster_return(t) = mean(returns[j, t] for j in C, j != i)
deviation(t) = returns[i, t] - cluster_return(t)
z_score(t) = (deviation(t) - rolling_mean(deviation, window)) / rolling_std(deviation, window)
```

Entrada LONG quando `z_score < -entry_zscore` (o ativo subperformou o cluster, deve subir).
Entrada SHORT quando `z_score > +entry_zscore` (o ativo sobreperformou, deve cair).
Default: `entry_zscore = 2.0`, `zscore_window = 20`, `correlation_window = 90 dias`, `correlation_threshold = 0.5`.

A confianca do sinal e `min(1.0, |z_score| / entry_zscore)` multiplicada pelo fator de regime (1.0 em mean-reverting, 0.5 em ambiguo, 0.0 em trending). Isso garante tamanho maior quando o descolamento e mais extremo e o regime favoravel.

### Filtro de regime (obrigatorio)

Mean reversion so funciona em mercados com memoria curta negativa (anti-persistentes). Usa-se o expoente de Hurst:

- `Hurst > 0.55`: mercado em trending, NAO operar (mean reversion falha).
- `Hurst < 0.45`: mercado mean-reverting, ideal, operar tamanho cheio.
- `0.45 a 0.55`: operar com tamanho reduzido (50%).

### Stop, take profit e gestao de risco

Take profit: `|z_score| < exit_zscore` (0.5), o spread convergiu.
Stop loss: `|z_score| > stop_zscore` (4.0), o spread continua divergindo, hipotese invalida.
Saida por tempo: maximo 72h em posicao.
Saida por quebra de correlacao: se a correlacao do ativo com o cluster cai abaixo de `correlation_threshold * 0.5`, fechar.

Position sizing base: 1% do portfolio por trade. Se 2 ativos do mesmo cluster geram sinal simultaneo, reduzir cada um pela metade (risco nao independente). Maximo 5 posicoes simultaneas. Drawdown kill switch: 15% pausa 24h, 25% para para revisao.

### Timeframe e expected performance

Timeframe ideal: 1h, 4h, 1d. Horizonte de algumas horas a poucos dias.
Targets documentados: win rate 60%+, Sharpe 1.5+, max drawdown < 10%, profit factor 2.0+, 10 a 30 trades por mes.
R:R tipicamente baixo (1:1 a 1.5:1), compensado por win rate alto.
Pesquisa real reportada: 22 a 41 bps por trade em pares cointegrados com horizonte de 15 a 240 minutos (anomiq.io, dataset 2025 de 50 simbolos). A versao por cluster nao tem benchmark publico direto, mas a logica e equivalente a media de varios pares dentro do cluster.

### Diferenca vs Statistical Arbitrage (STRAT-03)

Mean reversion por correlacao usa a media do cluster como ancora e nao exige cointegracao formal. Stat arb (STRAT-03) usa cointegracao Engle-Granger entre exatamente 2 ativos e hedge ratio via OLS. A versao por cluster e mais flexivel (qualquer tamanho de cluster) mas menos rigorosa estatisticamente. A recomendacao pratica e usar correlacao para formar clusters e cointegracao para confirmar pares dentro de cada cluster antes de operar.

### Tabela de parametros (config `MeanReversionConfig`)

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `correlation_threshold` | 0.5 | 0.3 a 0.8 | Correlacao minima para formar cluster |
| `correlation_window` | 90 | 30 a 180 | Janela para correlacao (dias) |
| `zscore_window` | 20 | 10 a 60 | Janela do z-score do descolamento |
| `entry_zscore` | 2.0 | 1.5 a 3.0 | Z-score para abrir posicao |
| `exit_zscore` | 0.5 | 0.0 a 1.0 | Z-score para fechar (convergencia) |
| `stop_zscore` | 4.0 | 3.0 a 5.0 | Z-score para stop loss |
| `min_cluster_size` | 3 | 2 a 5 | Minimo de ativos no cluster |
| `max_position_per_asset` | 0.10 | 0.05 a 0.20 | Max % do portfolio por ativo |
| `hurst_threshold` | 0.55 | 0.50 a 0.60 | Skip se trending acima disso |

### Exemplo numerico

Cenario: cluster com BTC, ETH, SOL, BNB, ADA. BTC sobe 5% numa janela curta enquanto a media de {ETH, SOL, BNB, ADA} sobe 0.8%. O descolamento e +4.2%. Se a media rolling do descolamento e 0% e o desvio e 1.8%, o z-score e 4.2 / 1.8 = 2.33. Como 2.33 > 2.0, abre SHORT em BTC apostando que converge. Se na proxima janela BTC cair e a media do cluster subir, o z-score recua abaixo de 0.5 e a posicao fecha no take profit. Se o z-score subir acima de 4.0, o stop dispara.

### Pseudocodigo do ciclo de sinais

```python
def generate_signals(returns, params):
    # 1. Matriz de correlacao sobre janela deslizante
    corr = CorrelationMatrix(method="pearson").compute(returns.tail(params["correlation_window"]))
    # 2. Grafo + comunidades formam clusters
    graph = CorrelationGraph(threshold=params["correlation_threshold"]).build(corr)
    communities = detect_communities(graph)
    # 3. Para cada cluster e cada ativo, z-score do descolamento
    signals = []
    for cluster, members in group_by_community(communities):
        if len(members) < params["min_cluster_size"]: continue
        for asset in members:
            others = [m for m in members if m != asset]
            cluster_ret = returns[others].mean(axis=1)
            deviation = returns[asset] - cluster_ret
            z = rolling_zscore(deviation, params["zscore_window"])
            # 4. Filtro de regime Hurst
            if compute_hurst(returns[asset]) > params["hurst_threshold"]: continue
            # 5. Sinal
            if z.iloc[-1] < -params["entry_zscore"]:
                signals.append(Signal(asset, "LONG", confidence=abs(z.iloc[-1])))
            elif z.iloc[-1] > params["entry_zscore"]:
                signals.append(Signal(asset, "SHORT", confidence=abs(z.iloc[-1])))
    return signals
```

## Estado do mercado em 2026

A estrategia segue ativa e estudada em 2026. A questao central, segundo o blog anomiq.io, e que single-asset reversion (um ativo voltando a propria media) e rejeitada pela evidencia: fica exposta a direcao do mercado. Ja a versao market-neutral (spread entre ativos correlacionados ou cointegrados) bate buy-and-hold apos microstructure costs, o que single-asset nao consegue.

Quem pesquisa e bot: o repositorio Aroesler1/crypto_stat_arb estuda stat-arb com grafos de correlacao signed (k-NN), remocao do market mode via PCA, clusterizacao por SPONGE/BNC/spectral e backtest walk-forward com controles de turnover e custo. O paranjay-s/strat_adv combina PCA, clustering KMeans/DBSCAN, deteccao de comunidades via Louvain, analise de copula Student-t e ate RL com PPO para ranking de pares, com prototipo de execucao na Bybit. Esses sao os exemplos mais proximos do que o crypto-correl-bot ja faz.

Quem ensina: blogs quant (LHFX, anomiq.io) explicam o workflow Engle-Granger, z-score do spread e a distincao critica de que correlacao nao basta, e preciso cointegracao. A comunidade academica publicou em 2024 um estudo no London Journal of Research In Management & Business aplicando clustering (k-means, hierarchical, affinity propagation) nas top 50 criptos de 2021 a 2024, encontrando 21 pares com cointegracao forte, com affinity propagation superior na definicao de clusters.

Performance real reportada: o backtest anomiq em 50 simbolos de 2025, 137 pares acima de correlacao 0.65, hedge ratio recalculado diario em janela de 30 dias com teste Engle-Granger, mostrou +22 a +41 bps por trade em horizontes de 15 a 240 minutos com entrada em z-score 1.5, 2.0 e 2.5. A leitura ingenua parecia estrategia, mas a calibracao do exit e de stops importa muito: exit tight cortava ~64% dos vencedores antes da reversion completar. O ajuste para stop de 35 bps com trailing exit (ativar em 20 bps de lucro, dar de volta 15 bps do pico) melhorou o resultado. Esse e o ponto pratico: a logica de entrada e facil, o exit e onde o edge vive ou morre.

Riscos em 2026: correlacao em cripto e instavel e muda com regime. Eventos setoriais (AI season, meme season, DeFi narrative) quebram clusters. BTC domina e deve ter o market mode removido via PCA antes de clusterizar, exatamente como faz o Aroesler1/crypto_stat_arb. Sem isso, todos os ativos correlacionam com BTC e os clusters perdem significado.

Outro risco concreto e o funding nas pernas short em perp. Cada short perp paga ou recebe funding a cada intervalo. Em periodos de funding extremo positivo, shortear o ativo que sobreperformou custa funding, o que corrói o edge da convergencia. O modelo de custo do backtest precisa incluir funding das duas pernas, nao so fee de trading. O manual interno STRAT-01 ja menciona esse custo, mas nao esta confirmado que o backtest atual o inclui.

Cuidado com look-ahead: o hedge ratio e a correlacao devem ser recalculados em janela trailing e aplicados ao dia seguinte, nunca fit em todo o periodo e aplicar no mesmo periodo. O anomiq faz recalculo diario com janela de 30 dias e aplica OOS no dia seguinte, o que e o padrao correto.

### Quem ensina e quem vende curso

A area e mais academica e quant do que de vendedores de curso. Blogs como anomiq.io e LHFX explicam o workflow com codigo e sem promessa de retorno garantido. Repositorios GitHub (Aroesler1, paranjay-s) sao pesquisa aberta com walk-forward. O tom e empirico: reporta o que funcionou, o que falhou e por que. Isso e diferente de ICT/SMC (STRAT-09), onde predomina venda de curso com pouca validacao. Para mean reversion por correlacao, a evidencia e moderada e honesta: o edge existe em regime lateral, some em trending, e o exit e onde a maioria erra.

## Ferramentas e APIs disponiveis

### Bibliotecas Python

- `statsmodels`: testes Engle-Granger e Johansen de cointegracao, ADF, OLS para hedge ratio. Biblioteca padrao para a parte estatistica.
- `networkx`: deteccao de comunidades (Louvain, label propagation) para formar clusters a partir da matriz de correlacao. Ja usado no projeto.
- `scikit-learn`: KMeans, DBSCAN, AffinityPropagation para clustering alternativo. PCA para remover market mode.
- `pandas` + `numpy`: calculo de correlacao rolling, z-score, returns.
- `vectorbt`: backtest vetorizado para sweeps de parametros (ja escolhido no projeto).

### Dados

- Binance Vision (klines historicos, gratis) e Binance REST API para dados recentes.
- Funding rate history via `GET /fapi/v1/fundingRate` (max 1000 por request, paginar com startTime). Importante para modelar custo das pernas short perp.
- Desde maio de 2025 a Binance passou a usar intervalos variaveis de funding (1h, 4h, 8h) por contrato, o que afeta o calculo de custo. O endpoint `GET /fapi/v1/fundingInfo` retorna o intervalo atual por contrato.

### Plataformas que suportam

- Bybit e Binance: execucao de spot e perp para as duas pernas. O paranjay-s/strat_adv tem prototipo de execucao na Bybit com live liquidity checks, kill switch e position sizing por Kelly.
- Hyperliquid, dYdX: perps on-chain com funding mais volatil, bom para funding extremo gerar descolamentos que a estrategia pode explorar.

### Combinacao com outras estrategias do projeto

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Entropy Regime (STRAT-04) | Alta | Entropy filtra regimes caoticos onde correlacao quebra |
| + Hurst Exponent | Alta | Hurst filtra trending vs mean-reverting (ja no codigo) |
| + Funding Rate (STRAT-08) | Media | Funding extremo pode causar descolamento do cluster |
| + Momentum (STRAT-06) | Baixa | Filosofias opostas (reversion vs trend), usar em regimes diferentes |
| + Stat Arb Coint (STRAT-03) | Alta | Confirmar cointegracao por par dentro do cluster antes de operar |

A combinacao mais natural e com STRAT-04 (Entropy) e com o filtro de Hurst (ja presente). A ideia e so operar mean reversion em regime de baixa entropia e Hurst < 0.45, e deixar momentum (STRAT-06) atuar em regime de trending.

### Vantagens e desvantagens

Vantagens: market-neutral (aposta em convergencia, nao em direcao), base estatistica solida (correlacao e z-score sao robustos), funciona bem em mercados laterais (comuns em cripto), multiplos sinais simultaneos dentro de um cluster (diversificacao).

Desvantagens: falha em trending forte (por isso o filtro Hurst e obrigatorio), correlacao pode quebrar por eventos idiossincrasicos (hack, listing, delisting), custo de funding em shorts perpetuos corrói o edge se nao modelado, muitos sinais falsos em alta volatilidade, R:R baixo exige win rate alto para compensar.

### Metricas de avaliacao (target)

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Win rate | 60%+ | 55% |
| Sharpe ratio | 1.5+ | 1.0 |
| Max drawdown | < 10% | < 15% |
| Profit factor | 2.0+ | 1.5 |
| Avg holding period | 2 a 48h | 1 a 72h |
| Trades por mes | 10 a 30 | 5+ |

## Por que importa para o crypto-correl-bot

Ja temos script: sim, `src/strategy/mean_reversion.py`, classe `MeanReversionStrategy`, STRAT-01. O modulo usa `CorrelationMatrix` e `CorrelationGraph` da camada de analise para detectar clusters, calcula z-score do descolamento com `_rolling_zscore`, aplica `RegimeFilter` (Hurst) e gera `Signal` objects com metadata de zscore, cluster, hurst e regime. O `check_exit` fecha quando `|z_score| < exit_zscore` ou `> stop_zscore`.

STRAT-01. O que falta:

1. **Validar cointegracao dentro do cluster**: hoje o codigo usa correlacao para formar clusters mas nao testa cointegracao Engle-Granger por par antes de operar. A evidencia de 2025 diz que correlacao sozinha nao basta. Recomendado: adicionar gate de cointegracao (ADF nos residuos do OLS) para cada par candidato dentro do cluster.
2. **Remover market mode via PCA**: o AGENTS.md do projeto ja alerta que BTC domina e que e preciso remover o market mode antes de clusterizar. Hoje o `_get_clusters` calcula correlacao direta dos returns. Implementar residualizacao via PCA (projetar fora o primeiro componente) antes de construir o grafo.
3. **Ajustar exit para nao cortar vencedores cedo**: a pesquisa anomiq mostra que exit tight em z-score corta ~64% dos vencedores. Testar trailing exit baseado em bps de P&L ao inves de z-score puro.
4. **Walk-forward com controle de turnover e custo**: o Aroesler1/crypto_stat_arb faz walk-forward OOS com controles explicitos. Garantir que o backtest reporta metricas OOS e inclui custo de funding nas duas pernas (short perp paga/recebe funding).
5. **Backtest em eventos de stress**: crash de 2022 (Luna, FTX), rally de 2021, lateral de 2023, quebra de correlacao setorial. Ja previsto no manual STRAT-01 mas nao confirmado como executado.
6. **Position sizing por Kelly ou vol-target**: o paranjay-s/strat_adv usa Kelly-Criterion. Hoje o codigo usa sizing por confianca simples. Avaliar se Kelly fracionado melhora o Sharpe OOS sem aumentar drawdown.
7. **Detecao de quebra de cluster em tempo real**: o `check_exit` atual fecha por z-score, mas nao detecta se a correlacao do ativo com o cluster caiu abaixo do limiar. Adicionar saida por quebra de correlacao (correlacao rolling cai abaixo de `threshold * 0.5`).

### Checklist de proximos passos para STRAT-01

1. Implementar residualizacao PCA no `_get_clusters` antes de calcular correlacao.
2. Adicionar gate de cointegracao Engle-Granger por par dentro do cluster.
3. Incluir custo de funding das pernas no backtest (consumir `GET /fapi/v1/fundingRate`).
4. Testar exit por trailing bps ao inves de z-score puro.
5. Rodar walk-forward OOS (janela IS 6 meses, OOS 2 meses, step 2 meses).
6. Validar metricas OOS contra os targets da tabela acima.
7. Stress test em eventos de 2022 e 2023.

## Referencias

- Aroesler1/crypto_stat_arb: stat-arb crypto com signed graphs, PCA para remover market mode, SPONGE/BNC clustering e walk-forward backtest. github.com/Aroesler1/crypto_stat_arb
- anomiq.io: "Crypto Pairs Trading Backtest: 137 Cointegrated Pairs" e "Mean Reversion Crypto Backtest: 1 Year of Tick Data". Reporta +22 a +41 bps por trade em pares cointegrados, ajuste de exit para nao cortar vencedores. anomiq.io/blog/pairs-trading-crypto-mean-reversion
- paranjay-s/strat_adv: arquitetura decoupled com PCA, clustering, copula Student-t e RL (PPO), prototipo Bybit. github.com/paranjay-s/strat_adv
- London Journal of Research In Management & Business: "Enhancing Pairs Trading Strategies in the Cryptocurrency Industry using Machine Learning Clustering Algorithms" (2024), 21 pares cointegrados nas top 50 criptos, affinity propagation superior. journalspress.uk/index.php/LJRMB/article/view/1179
- LHFX: "Mean Reversion Trading: Pairs Trading in Forex & Crypto", distincao correlacao vs cointegracao, workflow Engle-Granger e z-score. lhfx.com/insights/pairs-trading-forex-crypto
- Manual interno: docs/strategies/01-mean-reversion-correlation.md (STRAT-01)
- Implementacao: src/strategy/mean_reversion.py
