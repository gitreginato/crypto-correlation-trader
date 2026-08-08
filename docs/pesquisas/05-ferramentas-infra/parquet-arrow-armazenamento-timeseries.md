# Topico: Apache Parquet, PyArrow e Armazenamento de Series Temporais Financeiras

**Data:** 2026-07-15
**Categoria:** Ferramentas / Infra

## TL;DR

Apache Parquet e o formato padrao de fato para armazenamento de dados analiticos em 2026: colunar, comprimido (10-25x sobre CSV), sem servidor, e universalmente suportado (pandas, polars, Spark, DuckDB, scikit-learn). PyArrow e o engine dominante para ler/escrever Parquet em Python, com Fastparquet em declinio (deprecado pelo Dask desde 2024, pandas 3.0 requer PyArrow). Para o volume do crypto-correl-bot (30 symbols x 3 anos x 5m = ~3.15M linhas), Parquet com Zstd ocupa ~900MB e queries via DuckDB rodam em milissegundos. Alternativas como HDF5 (cientifico, legacy), ClickHouse (OLAP distribuido, overkill para volume local), TimescaleDB (Postgres extension, bom para ponto-queries mas exige servidor), QuestDB (ingestao ultra-rapida, mas servidor), e ArcticDB (MongoDB, API Python de alto nivel) existem mas adicionam complexidade desnecessaria para um projeto local de dados write-once-read-many. A combinacao Parquet + DuckDB + PyArrow e o ponto otimo: zero infraestrutura, compressao maxima, queries SQL rapidas, e interoperabilidade total com o ecossistema Python de ML.

## Explicacao para criancas

Imagine que voce tem um caderno gigante com os precos de varias balas (criptomoedas) ao longo de varios anos. Cada linha tem: data, bala, preco de abertura, maxima, minima, fechamento, volume.

**CSV** e como escrever tudo em linhas, uma apos a outra, em texto puro. Simples, mas o arquivo fica gigante e para saber so o preco de fechamento do Bitcoin, voce precisa ler o arquivo inteiro linha por linha.

**Parquet** e como organizar o caderno em colunas separadas: uma pagina so com datas, outra so com precos de fechamento, outra so com volumes. Se voce quer so o fechamento, le so aquela pagina. Alem disso, cada pagina e comprimida (como ZIP), entao o caderno inteiro fica muito menor. E como um caderno que se comprime sozinho.

**PyArrow** e a ferramenta que abre e fecha o caderno Parquet de forma rapida, usando codigo em C++ por baixo dos panos.

**DuckDB** e como uma calculadora inteligente que sabe ler o caderno Parquet diretamente e fazer contas (media, soma, maximo) sem precisar carregar tudo na memoria. E como ter um SQLite mas para dados analiticos grandes.

As outras opcoes (ClickHouse, TimescaleDB, QuestDB) sao como bibliotecas inteiras com bibliotecarios: voce precisa instalar, configurar, manter um servidor rodando. Para um projeto pessoal que cabe em um computador, e como contratar um bibliotecario para organizar 10 livros.

## Como funciona tecnicamente

### Apache Parquet

Parquet e um formato binario colunar de codigo aberto, parte do ecossistema Apache (Hadoop, Arrow, Iceberg). Diferente de formatos linha-a-linha (CSV, JSON), Parquet armazena dados por coluna:

**Estrutura interna:**
- **Row Groups**: dados sao particionados em grupos de linhas (tipicamente 128MB cada)
- **Column Chunks**: dentro de cada row group, cada coluna e armazenada como um chunk independente
- **Pages**: dentro de cada column chunk, dados sao paginados (compression unit)
- **Footer**: metadata (schema, statistics min/max por chunk, encoding, compression)

**Encoding e compressao:**
- Dictionary encoding: valores repetidos sao substituidos por indices em um dicionario
- Run-Length Encoding (RLE): sequencias de valores repetidos sao comprimidas
- Delta encoding: para timestamps e valores sequenciais
- Compressao de pagina: Snappy (rapido, default), Zstd (melhor ratio, ~20% menor), Gzip (compatibilidade), Brotli (melhor ratio, mais lento)

**Vantagens para dados financeiros:**
- Dados OHLCV sao altamente comprimiveis: precos tem poucos valores unicos relativos, volume tem muitos zeros em periodos de baixa liquidez, timestamps sao sequenciais (delta encoding eficiente)
- Leitura seletiva de colunas: se so precisa de `close` e `volume`, le so essas colunas, poupando I/O
- Predicate pushdown: statistics min/max por chunk permitem pular row groups inteiros que nao match o filtro (ex: `WHERE date > '2024-06-01'`)
- Schema evolution: adicionar colunas nao quebra readers antigos

**Particionamento:**
A melhor pratica para dados de series temporais e particionar hierarquicamente:
```
data/
  symbol=BTCUSDT/
    timeframe=5m/
      year=2024/
        month=01/
          data.parquet
        month=02/
          data.parquet
      year=2025/
        ...
  symbol=ETHUSDT/
    ...
```

Isso permite: (1) leitura eficiente de um symbol especifico sem scan de todos, (2) append incremental de novos meses sem reescrever, (3) predicate pushdown no nivel de diretorio (Hive partitioning).

### PyArrow vs Fastparquet

| Aspecto | PyArrow | Fastparquet |
|---|---|---|
| Implementacao | C++ (Apache Arrow) | Python + Numba |
| Velocidade leitura | 2-5x mais rapido para >1GB | Mais lento para datasets grandes |
| Velocidade escrita | 20-25% mais rapido (benchmark real: 50.6s vs 63.5s para 794MB) | Mais lento |
| Multithreading | Sim (C++ backend paralelo) | Limitado (GIL) |
| Memoria | Maior footprint inicial (C++ deps) | Menor footprint |
| Compressao | Snappy, Zstd, Brotli, Gzip, LZ4 | Snappy, Zstd, Gzip |
| Suporte pandas 3.0 | Requerido (pandas 3.0 faz PyArrow obrigatorio) | Nao suportado |
| Suporte Dask | Recomendado | Deprecado desde Dask 2024.1.0 |
| Manutencao | Apache Foundation, time grande | Dask team (que abandonou o proprio Fastparquet) |
| Tamanho do pacote | ~176MB | ~1.1MB |
| Schema evolution | Sim | Limitado |
| Nested types (structs, lists) | Suporte completo | Limitado |

O veredito da comunidade em 2024-2026 e unanime: use PyArrow. Fastparquet foi deprecado pelo proprio Dask team (que o criou), pandas 3.0 requer PyArrow, e benchmarks mostram PyArrow superior em 80% dos casos para datasets >1GB.

### Estimativa de volume para o crypto-correl-bot

Para 30 symbols x 3 anos x timeframe 5m:
- Linhas por symbol por ano: 365 * 24 * 12 = 105.120
- Linhas por symbol (3 anos): ~315.360
- Total de linhas (30 symbols): ~9.460.800

| Componente | Estimativa |
|---|---|
| Linhas brutas | ~9.5M |
| Colunas (OHLCV + timestamp): 7 | 7 * 8 bytes = 56 bytes/linha |
| Tamanho bruto (sem compressao) | ~530MB |
| Compressao Snappy (10-15x) | ~35-53MB |
| Compressao Zstd (20-25x) | ~21-27MB |

Na pratica, com 12 colunas (klines tem open_time, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore) e particionamento:
- Bruto: ~900MB
- Parquet Zstd: ~50-90MB
- Parquet Snappy: ~70-120MB

O numero de ~900MB Parquet do enunciado refere-se provavelmente a dados mais largos (com mais colunas ou sem compressao maxima), ou a um universo maior de symbols. Com Zstd e particionamento eficiente, 30 symbols x 3 anos x 5m cabe em menos de 100MB.

### DuckDB como engine de query

DuckDB e um banco de dados analitico in-process (sem servidor, como SQLite mas para OLAP). Pode ler Parquet diretamente:

```sql
SELECT symbol, date_trunc('day', timestamp) as day, avg(close) as avg_close
FROM read_parquet('data/**/*.parquet')
WHERE timestamp >= '2024-01-01'
GROUP BY symbol, day
ORDER BY symbol, day
```

Vantagens: (1) zero infraestrutura, (2) le Parquet sem carregar tudo na memoria, (3) SQL completo (joins, window functions, CTEs), (4) mais rapido que pandas para agregacoes em datasets grandes, (5) integracao nativa com pandas/Arrow (resultado de query vira DataFrame).

### Alternativas

**HDF5:** Formato hierarquico cientifico (h5py, pandas HDFStore). Era popular para dados financeiros pre-2015. Problemas: formato binario opaco (nao universal como Parquet), sem compressao colunar, problemas de concorrencia (um writer trava tudo), e dependencia de bibliotecas C (libhdf5). Em 2026, e legacy.

**ClickHouse:** OLAP distribuido (C++), construido na Yandex para bilhoes de eventos/dia. Arquitetura servidor-cliente com MergeTree storage engine. Ingestao 100k+ eventos/segundo sustentado. Compressao 7.5x. Ideal para: dashboards em tempo real, multi-tenant analytics, ingestao continua >100k events/seg. Overkill para: dados locais write-once, 30 symbols, queries de um usuario. Adiciona complexidade de servidor, monitoramento, cluster.

**TimescaleDB:** Extension PostgreSQL para series temporais. Hypertables (particionamento automatico por tempo), compressao nativa (5.2x), continuos aggregates. Ideal se ja se usa Postgres e precisa de point queries rapidas (2ms). Problemas: requer servidor Postgres, setup complexo (timescaledb-tune), performance suscetivel a escolhas de chunking, pior que MongoDB/Parquet em writes e multi-record appends segundo benchmark.

**QuestDB:** TSDB construido do zero para performance. Ingestao 4M+ rows/segundo. Suporte nativo a Parquet. SQL-compatible. Ideal para tick data de alta frequencia. Para 5m OHLCV (volume baixo), e overkill. Benchmark: point query 3ms, range scan 18ms, aggregation 42ms (mais rapido que TimescaleDB e ClickHouse em tudo).

**ArcticDB (Man Group):** Camada Python sobre MongoDB (ou agora com backend local LMDB). API de alto nivel: `lib.write(symbol, df)`, `lib.read(symbol)`. Versionamento nativo (historico de snapshots). Ideal para: timeseries com versionamento, append frequente, read rapido. Benchmark vs MongoDB direto: ArcticDB tem reads mais rapidos e multi-record appends melhores. Problemas: dependencia de MongoDB (ou backend local menos testado), licenca comercial (ArcticDB comercial para enterprise, open source limitado).

**Arctic (original, deprecated):** Versao original sobre MongoDB, agora substituida por ArcticDB.

### Comparativo

| Aspecto | Parquet + DuckDB | HDF5 | ClickHouse | TimescaleDB | QuestDB | ArcticDB |
|---|---|---|---|---|---|---|
| Modelo | Arquivo + embedded | Arquivo | Servidor | Servidor (Postgres) | Servidor | Lib + backend |
| Infraestrutura | Zero | Zero | Alta (cluster) | Media (Postgres) | Media | Baixa (MongoDB) |
| Compressao | 20-25x (Zstd) | 3-5x | 7.5x | 5.2x | 2.1x | N/A (delegado) |
| Point query | ~5-10ms | ~1ms | 7ms | 2ms | 3ms | N/A |
| Aggregation | ~50ms | N/A (manual) | 85ms | 180ms | 42ms | N/A |
| Ingestao continua | N/A (batch) | Limitada | 100k+/s | N/A | 4M+/s | Boa |
| SQL | DuckDB (completo) | Nao | Sim | Sim (Postgres) | Sim | Nao (Python API) |
| Interoperabilidade | Maxima (universal) | Baixa | Media | Alta (Postgres) | Media | Media (Python) |
| Licenca | Apache-2.0 | BSD | Apache-2.0 | Apache-2.0 / TSL | Apache-2.0 | Comercial / Apache |
| Custo | $0 | $0 | $0 | $0 / $$ (managed) | $0 | $0 / $$$ (enterprise) |

## Estado do mercado em 2026

A combinacao Parquet + DuckDB + PyArrow tornou-se o padrao default para pipelines de ML e data science em 2026. O artigo de referencia (AI Code Invest) recomenda explicitamente: "Parquet + DuckDB e a top recommendation for ML training pipelines. If preprocessed data is consumed primarily by model-training scripts, Jupyter notebooks, or batch analytics, this combination is unmatched in simplicity, performance, and cost (free)."

O movimento e claro: dados analiticos locais nao precisam de servidor. Parquet e o formato de intercambio universal (lido por pandas, polars, Spark, DuckDB, scikit-learn, PyTorch, e todos os clouds S3/GCS/Azure). DuckDB e a query engine embedded que substitui a necessidade de um servidor OLAP para volumes ate ~100GB.

No dominio de TSDB (Time Series Databases), QuestDB destacou-se em 2025-2026 como o mais rapido em ingestion e queries para tick data financeira, com suporte nativo a Parquet e SQL. TimescaleDB (agora TigerData apos rebranding em junho 2025) mantem nicho em equipes ja investidas em PostgreSQL. ClickHouse domina analytics em escala petabyte (multi-node, multi-user).

ArcticDB ganhou tracao em instituicois que ja usam MongoDB, mas para projetos greenfield, Parquet + DuckDB e mais simples.

Fastparquet entrou em declinio terminal: deprecado pelo Dask (que o criou), nao suportado por pandas 3.0, e a comunidade migrou para PyArrow.

## Ferramentas e APIs disponiveis

| Ferramenta | Versao | Licenca | Repo | Custo | Maturidade |
|---|---|---|---|---|---|
| Apache Parquet (formato) | 2.10+ (spec) | Apache-2.0 | parquet.apache.org | $0 | Muito alta (padrao de facto) |
| PyArrow | 18.x | Apache-2.0 | github.com/apache/arrow | $0 | Muito alta |
| Fastparquet | 2024.x | BSD-3 | github.com/dask/fastparquet | $0 | Declinio (deprecado) |
| DuckDB | 1.x | MIT | github.com/duckdb/duckdb | $0 | Muito alta (20k+ stars) |
| HDF5 / h5py | 1.14+ | BSD | github.com/h5py/h5py | $0 | Alta (legacy) |
| ClickHouse | 24.x | Apache-2.0 | github.com/ClickHouse/ClickHouse | $0 | Muito alta (35k+ stars) |
| TimescaleDB / TigerData | 2.x | Apache-2.0 / TSL | github.com/timescale/timescaledb | $0 / $$ (managed) | Alta |
| QuestDB | 8.x | Apache-2.0 | github.com/questdb/questdb | $0 | Alta (14k+ stars) |
| ArcticDB | 4.x | Apache-2.0 (community) | github.com/man-group/ArcticDB | $0 / $$$ (enterprise) | Media-alta |

## Por que importa para o crypto-correl-bot

### O que usamos hoje

O projeto usa Apache Parquet (via PyArrow) como formato de armazenamento primario para dados historicos OHLCV. A decisao foi registrada em 2026-07-15: "Usar Apache Parquet para dados historicos. Motivo: colunar, comprimido, sem servidor, nativo no pandas/arrow." Alternativas rejeitadas na epoca: SQLite (menos eficiente para series temporais), Postgres (overkill para dados locais), CSV (sem compressao, sem schema).

### Trade-offs e consideracoes

**Parquet + DuckDB e o ponto otimo para este projeto.** Os dados sao write-once-read-many (baixar historico, ler repetidamente para backtest e analise). Nao ha ingestao continua de alta frequencia (5m candles sao batch, nao tick). Nao ha multi-usuario. Nao ha necessidade de ponto-queries em tempo real. Parquet + DuckDB entrega: (1) compressao maxima (~50-90MB para 3 anos de 30 symbols), (2) queries SQL rapidas sem servidor, (3) interoperabilidade total com pandas/scikit-learn/statsmodels, (4) zero custo de infraestrutura.

**Particionamento recomendado:** `symbol={SYMBOL}/timeframe={TF}/year={YYYY}/month={MM}/data.parquet`. Isso permite: leitura eficiente de um symbol (sem scan de todos), append incremental de novos meses, e predicate pushdown no nivel de diretorio via DuckDB.

**Compressao Zstd > Snappy para dados financeiros.** Zstd oferece ~20% melhor ratio com impacto minimo em velocidade de leitura (decompressao Zstd e quase tao rapido quanto Snappy). Para escrita, Zstd e ~10-15% mais lento, mas como nossos dados sao write-once, o trade-off vale a pena.

**Row group size importa para queries seletivas.** Row groups de 128MB (default PyArrow) sao bons para full scans. Para queries com filtro de data frequentes, row groups menores (8-32MB) permitem pular mais dados via statistics min/max. Para 30 symbols particionados por mes, cada arquivo mensal ja e naturalmente pequeno (~1-3MB), entao o row group size default e adequado.

**Nao migrar para ClickHouse/QuestDB/TimescaleDB.** Para 30 symbols x 5m candles, o volume e trivial (~10M linhas, <100MB em Parquet). Qualquer TSDB adiciona complexidade de servidor sem beneficio mensuravel. Se no futuro o projeto escalar para tick data (1000+ ticks/segundo) ou 1000+ symbols, reavaliar QuestDB para hot data + Parquet para cold data.

**DuckDB como query layer adicional.** Hoje o projeto provavelmente le Parquet via pandas/PyArrow diretamente. Adicionar DuckDB como opcao de query e de baixo custo e alto beneficio: permite SQL para joins entre symbols, window functions para rolling correlations, e aggregacoes sem carregar tudo em memoria. Integracao: `duckdb.query("SELECT * FROM read_parquet('data/**/*.parquet') WHERE symbol='BTCUSDT'").df()`.

### O que poderiamos migrar

1. **Curto prazo (manter + otimizar):** Parquet via PyArrow com Zstd. Adicionar DuckDB como query layer para analises ad-hoc. Verificar esquema de particionamento. Custo: baixo. Beneficio: queries SQL sem pandas boilerplate.

2. **Medio prazo (se escalar volume):** Se adicionar tick data ou L2 orderbook, considerar particionamento por dia em vez de mes, e avaliar QuestDB para hot data (ultimos 7 dias) com Parquet para cold data (historico). Custo: medio. Beneficio: ingestion continua + queries de baixa latencia.

3. **Nao migrar:** HDF5 (legacy, sem vantagem), Fastparquet (deprecado), ClickHouse (overkill), TimescaleDB (overkill sem beneficio sobre DuckDB+Parquet), ArcticDB (dependencia MongoDB desnecessaria).

## Referencias

1. AI Code Invest: Best Databases for Preprocessed Time-Series Data: http://www.aicodeinvest.com/best-databases-preprocessed-time-series-data-comparison-guide/
2. Medium (Everton Kozloski): Timeseries Databases Performance, 7 alternatives: https://medium.com/@ev_kozloski/timeseries-databases-performance-testing-7-alternatives-56a3415e6e9e
3. Elest.io: ClickHouse vs DuckDB 2026: https://blog.elest.io/clickhouse-vs-duckdb-which-analytical-database-for-embedded-vs-distributed-workloads-in-2026/
4. CodeBrewTools: DuckDB vs ClickHouse 2026 OLAP Guide: https://codebrewtools.com/blogs/duckdb-vs-clickhouse-olap-guide
5. Pythontutorials: Fastparquet vs PyArrow Comprehensive Comparison: https://www.pythontutorials.net/blog/a-comparison-between-fastparquet-and-pyarrow/
6. StackOverflow: Comparison between fastparquet and pyarrow (2024+): https://stackoverflow.com/questions/51361356/a-comparison-between-fastparquet-and-pyarrow
7. Dask Issue #8900: PyArrow vs Fastparquet discussion: https://github.com/dask/dask/issues/8900
8. QuestDB: TimescaleDB vs QuestDB Comparison: https://questdb.com/blog/timescaledb-vs-questdb-comparison/
9. NordVarg Blog: Time-Series Databases Comparison for Trading: https://nordvarg.com/blog/time-series-databases-comparison
10. Quantt: Time Series Databases in Finance: https://www.quantt.co.uk/resources/time-series-databases-finance
11. Medium (Oleg Komarov): How to store financial data, SQL vs NoSQL: https://medium.com/data-science/how-to-store-financial-data-a-sql-vs-no-sql-comparison-bbd0d71bfc26
12. Data Syndrome Blog: Python and Parquet performance optimization: https://blog.datasyndrome.com/python-and-parquet-performance-e71da65269ce
