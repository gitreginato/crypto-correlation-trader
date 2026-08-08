"""Graph: NetworkX graph construction and community detection.

Builds correlation graphs where nodes are assets and edges
represent strong correlations. Detects communities and computes metrics.
"""
import networkx as nx
import pandas as pd
from networkx.algorithms.community import greedy_modularity_communities

from src.analysis.correlation import CorrelationMatrix, CorrMethod


class CorrelationGraph:
    """Build and analyze correlation graphs from asset return data."""

    def __init__(self, threshold: float = 0.5, corr_method: CorrMethod = "pearson"):
        self.threshold = threshold
        self.corr_method = corr_method

    def build(self, corr_matrix: pd.DataFrame) -> nx.Graph:
        """Build a graph from a correlation matrix.

        Args:
            corr_matrix: Square correlation matrix (assets x assets).

        Returns:
            NetworkX Graph with nodes=assets, edges=strong correlations.
        """
        graph: nx.Graph = nx.Graph()

        for symbol in corr_matrix.columns:
            graph.add_node(symbol)

        symbols = corr_matrix.columns
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                value = float(corr_matrix.iloc[i, j])  # type: ignore[arg-type]
                if abs(value) >= self.threshold:
                    sign = "positive" if value > 0 else "negative"
                    graph.add_edge(
                        symbols[i],
                        symbols[j],
                        weight=value,
                        sign=sign,
                    )

        return graph

    def build_from_returns(self, returns: pd.DataFrame) -> nx.Graph:
        """Build a graph directly from a returns DataFrame.

        Args:
            returns: DataFrame where each column is an asset's return series.

        Returns:
            NetworkX Graph with correlation-based edges.
        """
        cm = CorrelationMatrix(method=self.corr_method)
        corr = cm.compute(returns)
        return self.build(corr)

    def detect_communities(self, graph: nx.Graph) -> dict[str, int]:
        """Detect communities using greedy modularity maximization.

        Args:
            graph: NetworkX Graph.

        Returns:
            Dict mapping node name to community ID.
        """
        if graph.number_of_edges() == 0:
            return {node: i for i, node in enumerate(graph.nodes())}

        communities = greedy_modularity_communities(graph)
        node_to_community: dict[str, int] = {}
        for comm_id, community in enumerate(communities):
            for node in community:
                node_to_community[node] = comm_id
        return node_to_community

    def compute_metrics(self, graph: nx.Graph) -> dict:
        """Compute overall graph metrics.

        Args:
            graph: NetworkX Graph.

        Returns:
            Dict with density, num_nodes, num_edges, num_communities, etc.
        """
        communities = self.detect_communities(graph)
        num_communities = len(set(communities.values()))

        return {
            "num_nodes": graph.number_of_nodes(),
            "num_edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "num_communities": num_communities,
            "is_connected": nx.is_connected(graph) if graph.number_of_nodes() > 0 else False,
        }

    def compute_centrality(self, graph: nx.Graph) -> dict[str, dict]:
        """Compute centrality measures for each node.

        Args:
            graph: NetworkX Graph.

        Returns:
            Dict mapping node name to its centrality metrics.
        """
        degree = nx.degree_centrality(graph)
        betweenness = nx.betweenness_centrality(graph)

        result: dict[str, dict] = {}
        for node in graph.nodes():
            result[node] = {
                "degree": float(degree.get(node, 0)),
                "betweenness": float(betweenness.get(node, 0)),
                "degree_raw": int(graph.degree(node)),
            }
        return result
