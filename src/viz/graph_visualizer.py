"""GraphVisualizer: Pyvis interactive HTML graph generation.

Generates standalone HTML files with interactive force-directed graphs
for visualizing asset correlation networks.
"""
from pathlib import Path
from typing import Literal

import networkx as nx
from pyvis.network import Network

NodeSizeBy = Literal["volume", "degree", "fixed"]


class GraphVisualizer:
    """Visualize correlation graphs as interactive HTML using Pyvis."""

    def __init__(
        self,
        output_dir: str = "data/graphs",
        node_size_by: NodeSizeBy = "volume",
        edge_threshold: float = 0.0,
        height: str = "800px",
        width: str = "100%",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.node_size_by = node_size_by
        self.edge_threshold = edge_threshold
        self.height = height
        self.width = width

    def _compute_node_size(self, graph: nx.Graph, node: str) -> int:
        """Compute node size based on the configured metric."""
        if self.node_size_by == "volume":
            volume = graph.nodes[node].get("volume", 1e9)
            # Scale: $50B -> ~50px, $1B -> ~10px
            return max(10, min(60, int(volume / 1e9)))
        elif self.node_size_by == "degree":
            return max(10, graph.degree(node) * 10)
        else:
            return 20

    def _edge_color(self, sign: str) -> str:
        """Return color for edge based on correlation sign."""
        return "#2ecc71" if sign == "positive" else "#e74c3c"

    def _edge_width(self, weight: float) -> int:
        """Compute edge width proportional to absolute correlation."""
        return max(1, int(abs(weight) * 10))

    def visualize(self, graph: nx.Graph, title: str = "Correlation Graph") -> str:
        """Generate an interactive HTML visualization of the graph.

        Args:
            graph: NetworkX Graph with correlation edges.
            title: Title for the HTML page.

        Returns:
            Path to the generated HTML file.
        """
        net = Network(
            height=self.height,
            width=self.width,
            heading=title,
            directed=False,
            notebook=False,
            cdn_resources="in_line",
        )

        # Add nodes
        for node in graph.nodes():
            size = self._compute_node_size(graph, node)
            net.add_node(node, label=node, size=size, title=f"Asset: {node}")

        # Add edges (filtered by threshold)
        for u, v, data in graph.edges(data=True):
            weight = data.get("weight", 0)
            if abs(weight) < self.edge_threshold:
                continue
            sign = data.get("sign", "positive")
            color = self._edge_color(sign)
            width = self._edge_width(weight)
            edge_title = f"Correlation: {weight:.3f}"
            net.add_edge(u, v, color=color, width=width, title=edge_title, value=abs(weight))

        # Configure physics for better layout
        net.toggle_physics(True)
        net.set_options("""
        {
            "physics": {
                "barnesHut": {
                    "gravitationalConstant": -8000,
                    "centralGravity": 0.1,
                    "springLength": 150,
                    "springConstant": 0.05,
                    "damping": 0.4
                }
            }
        }
        """)

        # Sanitize filename from title
        safe_title = title.replace(" ", "_").replace("/", "-").lower()
        output_path = self.output_dir / f"{safe_title}.html"
        net.save_graph(str(output_path))

        return str(output_path)
