import networkx as nx

from src.classes import GraphDataModel


class Graph(nx.Graph):
    def __init__(self, graph_data: GraphDataModel):

        self.graph_data: GraphDataModel = graph_data
        self.graph: nx.Graph = self.create_graph()

    def create_graph(self) -> nx.Graph:
        """Create a NetworkX graph from a node-link pydantic model."""
        directed = self.graph_data.directed
        multigraph = self.graph_data.multigraph
        data = {
            "multigraph": multigraph,
            "directed": directed,
            "graph": {},
            "nodes": self.graph_data.nodes,
            "links": self.graph_data.links,
        }
        G: nx.Graph = nx.node_link_graph(data, edges="links", directed=directed, multigraph=multigraph)
        return G
