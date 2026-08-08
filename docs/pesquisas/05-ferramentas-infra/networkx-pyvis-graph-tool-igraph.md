# Topico: NetworkX, Pyvis, graph-tool e igraph (Bibliotecas de Analise e Visualizacao de Grafos)

**Data:** 2026-07-15
**Categoria:** Ferramentas / Infra

## TL;DR

Para analise de grafos de correlacao em Python existem quatro bibliotecas principais com perfis drasticamente diferentes. NetworkX e puro Python, facil de instalar (pip), com 500+ funcoes e a maior comunidade, mas 40 a 250x mais lento que alternativas em C/C++. igraph (C com bindings Python) oferece performance proxima a C com API decente, sendo o equilibrio ideal para producao. graph-tool (C++ com Boost e OpenMP) e o mais rapido (2-10x mais que igraph, 100-1000x mais que NetworkX), mas e notoriamente dificil de instalar (requere compilacao C++ com Boost). Pyvis e um wrapper Python sobre vis.js que gera HTML interativo a partir de grafos NetworkX, ideal para visualizacao sem frontend. Neo4j e um graph database otimo para persistencia e queries complexas, mas overkill para analise estatistica de correlacao. Para o crypto-correl-bot com 30-50 nodes, NetworkX + Pyvis e suficiente. Se escalar para 500+ nodes, igraph passa a ser necessario.

## Explicacao para criancas

Imagine que voce quer desenhar um mapa mostrando quais balas (criptomoedas) sao parecidas entre si. Cada bala e um ponto (node) no mapa, e quando duas sao parecidas voce desenha uma linha (edge) entre elas.

**NetworkX** e como usar canetinhas e papel: super facil de usar, todo mundo sabe, mas se voce tiver que desenhar milhares de pontos e linhas, vai demorar muito.

**igraph** e como usar uma maquina de impressao rapida: mais rapido que canetinha, um pouco mais dificil de aprender, mas da conta do recado para mapas grandes.

**graph-tool** e como usar uma impressora industrial profissional: absurdamente rapida, mas voce precisa montar a maquina inteira primeiro (instalar compilador C++, bibliotecas Boost, etc.), o que pode levar horas.

**Pyvis** e como um quadro magico: voce da o mapa que ja desenhou com NetworkX e ele transforma em um desenho bonito e interativo na tela do computador, onde voce pode arrastar os pontos com o mouse.

**Neo4j** e como um armario gigante para guardar mapas: otimo se voce quiser guardar mapas para sempre e fazer perguntas complexas ("quais balas estao conectadas a Bitcoin em 3 passos?"), mas se voce so quer analisar o mapa uma vez, e exagero.

## Como funciona tecnicamente

### NetworkX

NetworkX e uma biblioteca puramente em Python. Grafos sao representados internamente como dicionarios de dicionarios (adjacency list). Cada node e edge pode ter atributos arbitrarios (dict). Nao ha compilacao, nao ha C extensions, nao ha paralelismo.

Arquitetura interna:
- `Graph`: grafo nao-dirigido, permite self-loops, sem multi-edges
- `DiGraph`: grafo dirigido
- `MultiGraph` / `MultiDiGraph`: permite multi-edges (paralelas)
- Representacao: dict-of-dicts (default), ou sparse matrix para grafos densos

Algoritmos disponiveis: 500+ funcoes cobrindo centralidade (degree, betweenness, closeness, eigenvector, pagerank), deteccao de comunidades (Louvain, Girvan-Newman, label propagation, modularity), caminhos mais curtos (Dijkstra, Bellman-Ford, A*), fluxo maximo, arvores geradoras minimas, metricas de rede (densidade, assortatividade, clustering), e mais.

Para o caso de uso do crypto-correl-bot, os algoritmos relevantes sao:
- **Construcao do grafo**: `nx.Graph()`, `add_edge(u, v, weight=corr)`, com peso = correlacao entre pares
- **Deteccao de comunidades**: `nx.community.louvain_communities()` para identificar clusters de ativos correlacionados
- **Centralidade**: `nx.betweenness_centrality()` para identificar quais ativos sao "pontes" entre clusters (alta importancia para propagacao de movimento de preco)
- **Modularity**: `nx.community.modularity()` para avaliar qualidade da clusterizacao
- **MST (Minimum Spanning Tree)**: `nx.minimum_spanning_tree()` para visualizar a estrutura de correlacao mais forte (MST e uma tecnica classica em finance, aka "Minimum Spanning Tree of correlation distances")

Exemplo de construcao do grafo de correlacao:
```python
import networkx as nx
import numpy as np

# corr_matrix: DataFrame de correlacao entre symbols
G = nx.Graph()
for symbol in corr_matrix.columns:
    G.add_node(symbol)

for i, s1 in enumerate(corr_matrix.columns):
    for s2 in corr_matrix.columns[i+1:]:
        corr = corr_matrix.loc[s1, s2]
        if abs(corr) > threshold:  # ex: 0.5
            # Distancia de correlacao: d = sqrt(2*(1-corr))
            G.add_edge(s1, s2, weight=corr, distance=np.sqrt(2*(1-corr)))

# Deteccao de comunidades
communities = nx.community.louvain_communities(G, weight="weight")
```

O preco da simplicidade e performance. Por ser puro Python, operacoes que envolvem travessia de grafo (betweenness, shortest paths) sao O(VE) com constante Python alta. Para um grafo de 1M de nodes, PageRank leva ~180s e usa 4.2 GB de RAM. Para 30 nodes, porem, tudo roda em milissegundos: betweenness centrality em 30 nodes e instantaneo, Louvain em 30 nodes tambem.

### igraph

igraph e escrito em C com bindings Python (e tambem R). A API e menos Pythonica que NetworkX (indices inteiros em vez de chaves arbitratias para vertices), mas a performance e dramaticamente superior.

No mesmo benchmark de PageRank em 1M nodes: ~6s e 1.1 GB de RAM (vs 180s e 4.2 GB do NetworkX). Instalacao e trivial via `pip install igraph` (wheels pre-compilados disponiveis para todas as plataformas principais).

Algoritmos: caminhos mais curtos, centralidade (betweenness, closeness, pagerank), deteccao de comunidades (Louvain, Walktrap, Infomap, Fast Greedy, Label Propagation), cliques, matching, fluxo, cortes, spectral. Uma revisao academica de 2024 (Indonesian Journal of Computer Science) concluiu que igraph e a biblioteca otima baseada em tempo de execucao, uso de memoria e usabilidade, com o algoritmo Louvain mostrando alta modularity em deteccao de comunidades.

Diferenca fundamental de API vs NetworkX: igraph usa indices inteiros para vertices (0, 1, 2...) enquanto NetworkX permite qualquer objeto hashable como node. Para mapear symbols (strings) para indices, e necessario manter um dict de mapeamento:
```python
import igraph as ig

# Mapear symbols para indices
symbols = list(corr_matrix.columns)
symbol_to_idx = {s: i for i, s in enumerate(symbols)}

g = ig.Graph(n=len(symbols), directed=False)
g.vs["name"] = symbols  # atributo de nome

for i, s1 in enumerate(symbols):
    for s2 in symbols[i+1:]:
        corr = corr_matrix.loc[s1, s2]
        if abs(corr) > threshold:
            g.add_edge(symbol_to_idx[s1], symbol_to_idx[s2], weight=corr)

# Louvain (mais rapido que NetworkX)
communities = g.community_multilevel(weights="weight")
```

igraph tambem tem visualizacao built-in via Cairo (menos interativa que Pyvis mas util para export estatico).

### graph-tool

graph-tool e escrito em C++ usando Boost Graph Library internamente, com template metaprogramming e OpenMP para paralelismo. A instalacao e o ponto critico: nao ha wheel pip universal. Requer conda ou compilacao manual com dependencias C++ pesadas (Boost, CGAL, expat, cairo).

Performance: no benchmark de PageRank 1M nodes, ~2s e 0.8 GB. Com OpenMP em 16 threads, betweenness centrality em grafos grandes pode ser 100x mais rapido que igraph. Para algoritmos paralelaveis (PageRank, clustering global, betweenness), graph-tool com OpenMP escala quase linearmente com o numero de cores.

O benchmark oficial (graph-tool.skewed.de) mostra:
- Single-source shortest path: graph-tool 0.0023s vs igraph 0.0092s vs NetworkX 0.25s
- PageRank: graph-tool 0.0052s (16 threads) vs igraph 0.072s vs NetworkX 1.54s
- Betweenness: graph-tool 102s (16 threads) vs igraph 198s vs NetworkX 10297s (~6.7 horas)

graph-tool tem algoritmos unicos nao disponiveis em NetworkX/igraph, especialmente stochastic block modeling (inferencia de estrutura de comunidade bayesiana).

### Pyvis

Pyvis e um wrapper Python sobre vis.js (vis-network), uma biblioteca JavaScript para visualizacao interativa de grafos. O fluxo e:

1. Construir grafo NetworkX normalmente
2. Chamar `Network.from_nx(nx_graph)` para converter
3. Chamar `Network.show("output.html")` para gerar HTML
4. Abrir o HTML no navegador

Features: fisica interativa (force-directed layout), drag-and-drop de nodes, hover tooltips, highlight de vizinhanca ao clicar, menu de configuracao dinamico, suporte a notebook Jupyter (inline). Nodes podem ter cor, tamanho, titulo (tooltip), imagem. Edges podem ter peso, cor, largura.

Exemplo de uso para o crypto-correl-bot:
```python
from pyvis.network import Network
import networkx as nx

# Grafo de correlacao ja construido
net = Network(height="750px", width="100%", bgcolor="#222222",
              font_color="white", notebook=False)
net.from_nx(G)

# Customizar: tamanho do node por degree, cor por comunidade
for node in net.nodes:
    node["size"] = G.degree(node["id"]) * 5 + 10
    node["color"] = community_colors[node["id"]]

# Fisica ativa para layout automatico
net.toggle_physics(True)
net.show("correlation_graph.html")
```

O resultado e um HTML standalone que pode ser aberto em qualquer navegador, sem servidor. O usuario pode arrastar nodes, dar zoom, clicar para ver vizinhos, e ajustar parametros de layout em tempo real via menu de configuracao.

Limitacoes: para grafos muito grandes (1000+ nodes), o vis.js no navegador fica lento (renderizacao no lado do cliente em canvas). Nao ha suporte a layouts 3D. Nao ha export para formatos vetoriais (SVG/PDF) de qualidade. Para capturar imagens de alta qualidade, e necessario usar ferramentas externas (puppeteer, screenschot) ou recorrer a matplotlib com layouts do graphviz.

Instalacao: `pip install pyvis`. Versao atual: 0.3.2. Repo: github.com/WestHealth/pyvis. Licenca: BSD (nao confirmado, verificar).

### Neo4j

Neo4j e um graph database nativo (armazenamento orientado a grafos, nao relacional). Usa Cypher como linguagem de query (declarativa, similar a SQL mas para grafos). Persiste em disco, suporta transacoes ACID, e otimizado para traversals de grafos (pattern matching, shortest path, community detection via GDS library).

Para analise de correlacao de cripto, Neo4j seria util se precisassemos: (1) persistir o historico de todos os grafos de correlacao por periodo, (2) fazer queries como "quais pares estiveram correlacionados em todos os meses de 2024", (3) integrar com dados de outras fontes em um schema de conhecimento.

Para analise estatistica pura (calcular correlacao, clusterizar, visualizar), Neo4j e overkill: adiciona complexidade de infraestrutura (servidor, JVM, Cypher) sem beneficio sobre arquivos Parquet + NetworkX.

### Comparativo de performance e features

| Aspecto | NetworkX | igraph | graph-tool | Pyvis | Neo4j |
|---|---|---|---|---|---|
| Linguagem | Python puro | C + Python | C++ + Python | Python + JS | Java |
| PageRank 1M nodes | ~180s | ~6s | ~2s | N/A | N/A (GDS) |
| Memoria 1M nodes | 4.2 GB | 1.1 GB | 0.8 GB | N/A | N/A |
| Instalacao | Trivial (pip) | Facil (pip wheel) | Dificil (conda/apt) | Trivial (pip) | Medio (Docker) |
| Visualizacao | Basica (matplotlib) | Basica (Cairo) | Boa (Cairo, nativa) | Excelente (HTML interativo) | Bloom (pago) |
| Comunidade | Maior (25k+ stars) | Media | Pequena | Pequena | Grande (DB) |
| Licenca | BSD-3 | GPL-2+ | LGPL-3 | BSD | GPL-3 (community) |
| Paralelismo | Nao | Limitado | OpenMP (SIMD) | N/A | Sim (GDS) |
| Persistencia | Nao (pickle/graphml) | Nao (graphml) | Nao (graphml) | N/A | Sim (nativo) |
| Schema | Flexivel (dict) | Inteiros | Flexivel | N/A | Rigido (labels/rel types) |
| Melhor para | Prototipos, <100 nodes | Producao, 100-100k nodes | Pesquisa, 100k+ nodes | Visualizacao | Persistencia, queries complexas |

## Estado do mercado em 2026

O ecossistema de analise de grafos em Python permanece dominado por NetworkX em termos de adocao (mais downloads, mais tutoriais, mais documentacao), mas a convergencia para performance esta ocorrendo. Uma revisao academica de 2025 (Springer, Social Network Analysis and Mining) benchmarks NetworkX, RustworkX, igraph, EasyGraph e graph-tool, concluindo que enquanto NetworkX e o mais popular, graph-tool e igraph sao consistentemente mais rapidos e eficientes. O estudo enfatiza o trade-off entre usabilidade e performance, sugerindo que a escolha otima depende dos requisitos especificos do projeto.

RustworkX (da IBM/Qiskit, escrito em Rust) emergiu como uma alternativa interessante em 2024-2025, com performance excepcional em betweenness centrality (3.14ms vs horas para NetworkX em alguns benchmarks), mas ainda tem comunidade menor e menos algoritmos implementados. Para casos de uso que precisam de velocidade extrema em algoritmos especificos sem a complexidade de instalacao do graph-tool, RustworkX e uma opcao crescente.

O benchmark oficial do graph-tool (graph-tool.skewed.de) permanece a referencia para comparacao direta. Os numeros sao consistentes: NetworkX e 40 a 250x mais lento que graph-tool, e igraph ocupa uma posicao intermediaria (2-10x mais lento que graph-tool, mas 10-30x mais rapido que NetworkX). Para algoritmos paralelaveis com OpenMP, graph-tool com 16 threads pode ser 100x mais rapido que igraph em betweenness centrality.

Para visualizacao interativa, Pyvis permanece a opcao mais simples para Python + HTML. Alternativas como pyvis-network (fork), bokeh graphs, e plotly graph objects existem mas sao mais complexas. Para visualizacao de producao com grafos grandes, D3.js direto ou Cytoscape.js (com backend Python via cyrest) oferecem mais controle. Uma outra alternativa emergente e o tinkercad de grafos do panel-chemistry/ecosystem, mas com nicho mais academico.

Neo4j continua o graph database dominante, mas para casos de uso de analise (nao persistencia), sua relevancia diminuiu. O movimento "embedded analytics" (DuckDB + Parquet + bibliotecas in-process) reduziu a necessidade de servidores de banco de dados para analise. Para queries historicas complexas em grafos de correlacao, Neo4j + Cypher seria poderoso, mas a mesma funcionalidade pode ser obtida com Parquet + pandas groupby com muito menos infraestrutura.

CDlib (Community Discovery Library) merece mencao como biblioteca especializada em deteccao de comunidades, oferecendo 39 algoritmos (Walktrap, Label Propagation, Girvan-Newman, Louvain, Infomap, etc.) com avaliacao e comparacao integradas. CDlib funciona sobre NetworkX e igraph, adicionando algoritmos que nao estao disponives nativamente em nenhuma das duas bibliotecas. Para o crypto-correl-bot, CDlib poderia ser util se precisarmos comparar multiplos algoritmos de deteccao de comunidade sistematicamente.

## Ferramentas e APIs disponiveis

| Ferramenta | Versao | Licenca | Repo | Custo | Maturidade |
|---|---|---|---|---|---|
| NetworkX | 3.x | BSD-3 | github.com/networkx/networkx | $0 | Muito alta (25k+ stars) |
| igraph (python) | 0.11+ | GPL-2+ | github.com/igraph/python-igraph | $0 | Alta |
| graph-tool | 2.45+ | LGPL-3 | graph-tool.skewed.de | $0 | Alta (mas instalacao dificil) |
| Pyvis | 0.3.2 | BSD | github.com/WestHealth/pyvis | $0 | Media |
| vis.js (vis-network) | 9.x | Apache-2.0 / MIT | github.com/visjs/vis-network | $0 | Alta |
| RustworkX | 0.15+ | Apache-2.0 | github.com/Qiskit/rustworkx | $0 | Media (crescendo) |
| Neo4j Community | 5.x | GPL-3 | github.com/neo4j/neo4j | $0 (community), $$ (enterprise) | Muito alta |
| Neo4j GDS | 2.x | Commercial | neo4j.com/product/graph-data-science | $0 (community limited), $$$ | Alta |
| CDlib | 0.3+ | MIT | github.com/GiulioRossetti/CDlib | $0 | Media |

## Por que importa para o crypto-correl-bot

### O que usamos hoje

O projeto usa NetworkX para construcao e analise do grafo de correlacao, com Pyvis para visualizacao interativa em HTML. Esta combinacao foi escolhida por: (1) facilidade de instalacao (pip, sem compilacao), (2) integracao nativa NetworkX -> Pyvis via `from_nx()`, (3) suficencia para o escopo atual de 30-50 nodes.

### Trade-offs e consideracoes

**NetworkX para 30-50 nodes e perfeitamente adequado.** Todos os algoritmos necessarios (correlacao como pesos de edges, betweenness centrality para identificar hubs, Louvain para deteccao de comunidades, modularity para avaliar clusters) rodam em milissegundos. A diference de performance para igraph/graph-tool e irrelevante nesta escala.

**Cenariode escala (500+ nodes):** Se o universo de ativos crescer para 200-500+ symbols, NetworkX comeca a ser um gargalo em: (1) betweenness centrality (O(VE) em Python puro), (2) deteccao de comunidades em grafos densos, (3) iteracao sobre todos os pares para construir a matriz de correlacao. Neste cenario, igraph seria a migracao natural (pip install, API decente, 30x mais rapido).

**graph-tool nao vale a pena para este projeto.** A dificuldade de instalacao (conda ou compilacao manual com Boost) adiciona complexidade de CI/CD sem beneficio em 30-50 nodes. Se no futuro precisarmos de stochastic block modeling (inferencia bayesiana de estrutura de comunidade), graph-tool e a unica opcao com implementacao madura, mas isso e um needs nice-to-have, nao critico.

**Pyvis vs alternativas de visualizacao:** Pyvis e ideal para o caso de uso: gerar HTML interativo para analise exploratoria. Limitacoes: grafos com 500+ nodes ficam lentos no navegador (vis.js renderiza em canvas no cliente). Se precisarmos de visualizacao de producao com grafos grandes, considerar: (1) Cytoscape.js com layout server-side, (2) filtrar o grafo antes de visualizar (so mostrar top-N edges por peso), (3) plotly/bokeh para grafos menores com mais controle estilistico.

**Neo4j e overkill.** Para analise de correlacao periodica (calcular matriz, construir grafo, clusterizar, visualizar), persistir em Parquet e carregar em NetworkX e mais simples e rapido. Neo4j so faria sentido se precisassemos de queries historicas complexas ("quais pares mantiveram correlacao > 0.7 por 6 meses consecutivos"), o que pode ser feito com Parquet + pandas groupby de forma mais leve.

### O que poderiamos migrar

1. **Curto prazo (manter):** NetworkX + Pyvis. Adequado para o escopo atual, sem custo de migracao.

2. **Medio prazo (se escalar para 100+ nodes):** Avaliar migracao do backend de analise para igraph, mantendo NetworkX apenas para construcao do grafo (API mais Pythonica) e Pyvis para visualizacao. Custo: medio (refatorar modulo de analise). Beneficio: 30x mais rapido em centralidade e comunidades.

3. **Longo prazo (se escalar para 500+ nodes ou precisar de SBM):** Avaliar graph-tool para algoritmos pesados, mas somente em ambiente conda/Docker para resolver o problema de instalacao.

## Referencias

1. graph-tool Performance Comparison: https://graph-tool.skewed.de/performance.html
2. Springer: A comparative evaluation of social network analysis tools (2025): https://link.springer.com/article/10.1007/s13278-025-01409-y
3. KinDaTechnical: NetworkX vs igraph vs Graph Tool Comparison: https://kindatechnical.com/graph-theory-applications/networkx-vs-igraph-vs-graph-tool-comparison.html
4. Indonesian Journal of Computer Science: Community detection algorithms analysis (2024): https://www.ijcs.net/ijcs/index.php/ijcs/article/download/4019/581
5. Pyvis Documentation: https://pyvis.readthedocs.io/en/latest/
6. Pyvis PyPI: https://pypi.org/project/pyvis/
7. NetworkX Repository: https://github.com/networkx/networkx
8. igraph Python Repository: https://github.com/igraph/python-igraph
9. graph-tool Website: https://graph-tool.skewed.de/
10. RustworkX Repository: https://github.com/Qiskit/rustworkx
11. CDlib Repository: https://github.com/GiulioRossetti/CDlib
12. IJSAT: A Review of Python Graph Algorithms (2025): https://www.ijsat.org/papers/2025/2/3562.pdf
