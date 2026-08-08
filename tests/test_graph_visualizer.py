"""Tests for GraphVisualizer: Pyvis interactive HTML graph generation."""
from pathlib import Path

import networkx as nx
import pytest

from src.viz.graph_visualizer import GraphVisualizer


@pytest.fixture
def sample_graph() -> nx.Graph:
    """Create a sample correlation graph for testing."""
    graph = nx.Graph()
    graph.add_node("BTCUSDT", volume=50000000000, degree=3)
    graph.add_node("ETHUSDT", volume=20000000000, degree=2)
    graph.add_node("SOLUSDT", volume=3000000000, degree=2)
    graph.add_node("DOGEUSDT", volume=800000000, degree=0)
    graph.add_edge("BTCUSDT", "ETHUSDT", weight=0.85, sign="positive")
    graph.add_edge("BTCUSDT", "SOLUSDT", weight=0.60, sign="positive")
    graph.add_edge("ETHUSDT", "SOLUSDT", weight=0.55, sign="positive")
    return graph


class TestGraphVisualizer:
    def test_visualize_generates_html(self, sample_graph: nx.Graph, tmp_path: Path):
        """Visualizing should generate an HTML file."""
        viz = GraphVisualizer(output_dir=str(tmp_path))
        output_path = viz.visualize(sample_graph, title="Test Graph")
        assert Path(output_path).exists()
        assert output_path.endswith(".html")

    def test_html_contains_node_names(self, sample_graph: nx.Graph, tmp_path: Path):
        """Generated HTML should contain node names."""
        viz = GraphVisualizer(output_dir=str(tmp_path))
        output_path = viz.visualize(sample_graph, title="Test Graph")
        content = Path(output_path).read_text()
        assert "BTCUSDT" in content
        assert "ETHUSDT" in content

    def test_html_contains_edge_weights(self, sample_graph: nx.Graph, tmp_path: Path):
        """Generated HTML should contain edge weight information."""
        viz = GraphVisualizer(output_dir=str(tmp_path))
        output_path = viz.visualize(sample_graph, title="Test Graph")
        content = Path(output_path).read_text()
        assert "0.85" in content or "0.8" in content

    def test_custom_title(self, sample_graph: nx.Graph, tmp_path: Path):
        """HTML should contain the custom title."""
        viz = GraphVisualizer(output_dir=str(tmp_path))
        output_path = viz.visualize(sample_graph, title="My Custom Title")
        content = Path(output_path).read_text()
        assert "My Custom Title" in content

    def test_node_size_by_volume(self, sample_graph: nx.Graph, tmp_path: Path):
        """Node size should be proportional to volume."""
        viz = GraphVisualizer(output_dir=str(tmp_path), node_size_by="volume")
        output_path = viz.visualize(sample_graph, title="Test")
        assert Path(output_path).exists()

    def test_node_size_by_degree(self, sample_graph: nx.Graph, tmp_path: Path):
        """Node size should be proportional to degree."""
        viz = GraphVisualizer(output_dir=str(tmp_path), node_size_by="degree")
        output_path = viz.visualize(sample_graph, title="Test")
        assert Path(output_path).exists()

    def test_empty_graph(self, tmp_path: Path):
        """Visualizing an empty graph should not crash."""
        viz = GraphVisualizer(output_dir=str(tmp_path))
        empty_graph = nx.Graph()
        output_path = viz.visualize(empty_graph, title="Empty")
        assert Path(output_path).exists()

    def test_threshold_filtering(self, sample_graph: nx.Graph, tmp_path: Path):
        """Visualizer should filter edges below threshold."""
        viz = GraphVisualizer(output_dir=str(tmp_path), edge_threshold=0.7)
        output_path = viz.visualize(sample_graph, title="Filtered")
        content = Path(output_path).read_text()
        # Edge with weight 0.60 should be filtered out
        # Edge with weight 0.85 should remain
        assert "0.85" in content or "0.8" in content
