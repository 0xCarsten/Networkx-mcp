import json
import pathlib

import networkx as nx
import pytest

from src.base.base import Graph
from src.classes import GraphDataModel


@pytest.fixture
def sample_graph():
    with open(pathlib.Path(__file__).parents[1] / "data/sample_graph_attr.json") as f:
        graph_data = json.load(f)
    return graph_data


def test_create_graph(sample_graph):
    """Load a sample graph and test creation of NetworkX graph."""
    graph_data = GraphDataModel.model_validate(sample_graph)
    G = Graph(graph_data).graph
    assert isinstance(G, nx.Graph)
    # assert G.number_of_nodes() == 4
