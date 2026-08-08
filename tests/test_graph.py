"""Tests for Graph: NetworkX graph construction and community detection."""
import numpy as np
import pandas as pd
import pytest
import networkx as nx

from src.analysis.graph import CorrelationGraph


@pytest.fixture
def corr_matrix() -> pd.DataFrame:
    """Generate a known correlation matrix for testing."""
    return pd.DataFrame({
        "BTCUSDT": [1.0, 0.85, 0.60, 0.05],
        "ETHUSDT": [0.85, 1.0, 0.55, 0.10],
        "SOLUSDT": [0.60, 0.55, 1.0, 0.15],
        "DOGEUSDT": [0.05, 0.10, 0.15, 1.0],
    }, index=["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"])


class TestCorrelationGraph:
    def test_build_graph(self, corr_matrix: pd.DataFrame):
        """Building a graph should create a NetworkX Graph with correct nodes."""
        cg = CorrelationGraph(threshold=0.5)
        graph = cg.build(corr_matrix)
        assert isinstance(graph, nx.Graph)
        assert set(graph.nodes()) == {"BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"}

    def test_threshold_filters_edges(self, corr_matrix: pd.DataFrame):
        """Edges below threshold should not be included."""
        cg = CorrelationGraph(threshold=0.5)
        graph = cg.build(corr_matrix)
        # DOGE has low correlation with all, should have no edges
        assert graph.degree("DOGEUSDT") == 0
        # BTC-ETH should have an edge (0.85 > 0.5)
        assert graph.has_edge("BTCUSDT", "ETHUSDT")

    def test_edge_weights_are_correlations(self, corr_matrix: pd.DataFrame):
        """Edge weight should be the correlation value."""
        cg = CorrelationGraph(threshold=0.5)
        graph = cg.build(corr_matrix)
        weight = graph["BTCUSDT"]["ETHUSDT"]["weight"]
        assert np.isclose(weight, 0.85)

    def test_edge_sign_attribute(self, corr_matrix: pd.DataFrame):
        """Edges should have a 'sign' attribute (positive/negative)."""
        cg = CorrelationGraph(threshold=0.5)
        graph = cg.build(corr_matrix)
        sign = graph["BTCUSDT"]["ETHUSDT"]["sign"]
        assert sign == "positive"

    def test_detect_communities(self, corr_matrix: pd.DataFrame):
        """Community detection should group correlated assets together."""
        cg = CorrelationGraph(threshold=0.3)
        graph = cg.build(corr_matrix)
        communities = cg.detect_communities(graph)
        assert isinstance(communities, dict)
        # BTC and ETH should be in the same community
        assert communities["BTCUSDT"] == communities["ETHUSDT"]
        # DOGE should be in a different community (uncorrelated)
        assert communities["DOGEUSDT"] != communities["BTCUSDT"]

    def test_graph_metrics(self, corr_matrix: pd.DataFrame):
        """Graph metrics should be computed correctly."""
        cg = CorrelationGraph(threshold=0.5)
        graph = cg.build(corr_matrix)
        metrics = cg.compute_metrics(graph)
        assert "density" in metrics
        assert "num_nodes" in metrics
        assert "num_edges" in metrics
        assert "num_communities" in metrics
        assert metrics["num_nodes"] == 4
        assert 0 <= metrics["density"] <= 1

    def test_node_centrality(self, corr_matrix: pd.DataFrame):
        """Should compute centrality measures for each node."""
        cg = CorrelationGraph(threshold=0.3)
        graph = cg.build(corr_matrix)
        centrality = cg.compute_centrality(graph)
        assert isinstance(centrality, dict)
        for node in graph.nodes():
            assert node in centrality
            assert "degree" in centrality[node]
            assert "betweenness" in centrality[node]

    def test_build_from_returns(self):
        """Should be able to build graph directly from returns DataFrame."""
        rng = np.random.default_rng(seed=42)
        n = 200
        ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
        btc = rng.normal(0, 0.02, n)
        eth = btc * 0.8 + rng.normal(0, 0.01, n)
        returns = pd.DataFrame({"BTCUSDT": btc, "ETHUSDT": eth}, index=ts)
        cg = CorrelationGraph(threshold=0.5)
        graph = cg.build_from_returns(returns)
        assert graph.has_edge("BTCUSDT", "ETHUSDT")

    def test_empty_graph_when_no_correlations(self):
        """Graph with no strong correlations should have no edges."""
        rng = np.random.default_rng(seed=42)
        n = 100
        ts = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
        returns = pd.DataFrame({
            "A": rng.normal(0, 0.02, n),
            "B": rng.normal(0, 0.02, n),
        }, index=ts)
        cg = CorrelationGraph(threshold=0.9)  # Very high threshold
        graph = cg.build_from_returns(returns)
        assert graph.number_of_edges() == 0
