"""Tests for MCP tools functionality.

This module tests the underlying functionality of the MCP tools including
graph creation, caching, shortest path, attribute filtering, and more.
"""

import json
import pathlib

import networkx as nx
import pytest

from src.base.base import Graph
from src.base.graph_analytics import NetworkXGraph
from src.cache import _loaded_graphs, _resolve_graph, cache_graph, get_cached_graph
from src.classes import GraphDataModel


@pytest.fixture
def sample_graph_data():
    """Load sample graph data from JSON file."""
    with open(pathlib.Path(__file__).parents[1] / "data/sample_graph_attr.json") as f:
        return json.load(f)


@pytest.fixture
def example_graph_data():
    """Load example graph data from JSON file."""
    with open(pathlib.Path(__file__).parents[1] / "data/example_graph.json") as f:
        return json.load(f)


@pytest.fixture
def sample_graph(sample_graph_data):
    """Create a NetworkX graph from sample data."""
    graph_model = GraphDataModel.model_validate(sample_graph_data)
    return Graph(graph_model).graph


@pytest.fixture
def example_graph(example_graph_data):
    """Create a NetworkX graph from example data."""
    graph_model = GraphDataModel.model_validate(example_graph_data)
    return Graph(graph_model).graph


@pytest.fixture(autouse=True)
def clear_graph_cache():
    """Clear the graph cache before and after each test."""
    _loaded_graphs.clear()
    yield
    _loaded_graphs.clear()


class TestGraphCreation:
    """Test graph creation from data."""

    @pytest.mark.parametrize(
        "fixture_name,check_edges",
        [
            ("sample_graph_data", False),
            ("example_graph_data", True),
        ],
    )
    def test_create_graph_from_data(self, fixture_name, check_edges, request):
        """Test creating a graph from various data sources."""
        graph_data = request.getfixturevalue(fixture_name)
        graph_model = GraphDataModel.model_validate(graph_data)
        G = Graph(graph_model).graph

        assert isinstance(G, nx.Graph)
        assert G.number_of_nodes() > 0
        if check_edges:
            assert G.number_of_edges() > 0


class TestGraphCache:
    """Test graph caching functionality."""

    def test_cache_and_retrieve_graph(self, sample_graph_data):
        """Test caching and retrieving a graph."""
        cache_graph("test_alias", sample_graph_data)

        retrieved = get_cached_graph("test_alias")
        assert retrieved is not None
        assert retrieved == sample_graph_data

    def test_retrieve_nonexistent_graph(self):
        """Test retrieving a graph that doesn't exist."""
        result = get_cached_graph("nonexistent")
        assert result is None

    def test_resolve_graph_from_data(self, sample_graph_data):
        """Test resolving a graph from direct data."""
        G = _resolve_graph(graph_data=sample_graph_data, graph_uri=None)

        assert isinstance(G, nx.Graph)
        assert G.number_of_nodes() > 0

    def test_resolve_graph_from_uri(self, sample_graph_data):
        """Test resolving a graph from a cached URI."""
        # First cache the graph
        cache_graph("test", sample_graph_data)

        # Then resolve it by URI
        G = _resolve_graph(graph_data=None, graph_uri="graph://test")

        assert isinstance(G, nx.Graph)
        assert G.number_of_nodes() > 0

    def test_resolve_graph_with_invalid_uri(self):
        """Test resolving a graph with an invalid URI format."""
        with pytest.raises(ValueError, match="Invalid graph URI"):
            _resolve_graph(graph_data=None, graph_uri="invalid://test")

    def test_resolve_graph_with_nonexistent_alias(self):
        """Test resolving a graph with a non-existent alias."""
        with pytest.raises(ValueError, match="not found"):
            _resolve_graph(graph_data=None, graph_uri="graph://nonexistent")


class TestShortestPath:
    """Test shortest path functionality."""

    def test_shortest_path_exists(self, example_graph):
        """Test finding shortest path when one exists."""
        try:
            path = nx.shortest_path(example_graph, source="0", target="19")
            assert path[0] == "0"
            assert path[-1] == "19"
            assert len(path) >= 2
        except nx.NetworkXNoPath:
            pytest.skip("No path exists between nodes 0 and 19")

    def test_shortest_path_same_node(self, example_graph):
        """Test shortest path from a node to itself."""
        path = nx.shortest_path(example_graph, source="0", target="0")
        assert path == ["0"]

    def test_shortest_path_no_path(self, sample_graph):
        """Test shortest path when no path exists."""
        # Create two disconnected nodes if graph structure allows
        nodes = list(sample_graph.nodes())
        if len(nodes) >= 2:
            # Try to find a pair with no path
            for i, source in enumerate(nodes):
                for target in nodes[i + 1 :]:
                    if not nx.has_path(sample_graph, source, target):
                        with pytest.raises(nx.NetworkXNoPath):
                            nx.shortest_path(sample_graph, source, target)
                        return
        pytest.skip("No disconnected nodes found for testing")

    def test_shortest_path_invalid_node(self, example_graph):
        """Test shortest path with an invalid node."""
        with pytest.raises((nx.NodeNotFound, KeyError)):
            nx.shortest_path(example_graph, source="0", target="nonexistent_node")


class TestNodesByAttribute:
    """Test finding nodes by attribute."""

    @pytest.mark.parametrize(
        "attribute,value,operator,validator",
        [
            ("object_type", "node", "==", lambda v, val: v == val),
            ("object_type", "edge", "!=", lambda v, val: v != val),
            ("holdup_max", 100.0, "<", lambda v, val: v < val),
            ("holdup_max", 0.0, ">", lambda v, val: v > val),
            ("holdup_max", 50.0, "<=", lambda v, val: v <= val),
            ("holdup_max", 10.0, ">=", lambda v, val: v >= val),
        ],
    )
    def test_find_nodes_with_operators(self, sample_graph, attribute, value, operator, validator):
        """Test finding nodes with various comparison operators."""
        result = NetworkXGraph.nodes_by_attribute(sample_graph, attribute, value, operator)

        assert isinstance(result, list)
        # Verify all returned nodes satisfy the condition
        for node in result:
            node_value = sample_graph.nodes[node].get(attribute)
            if node_value is not None:
                assert validator(node_value, value)

    def test_find_nodes_attribute_not_exists(self, sample_graph):
        """Test finding nodes by non-existent attribute."""
        result = NetworkXGraph.nodes_by_attribute(sample_graph, "nonexistent_attr", "value", "==")
        assert isinstance(result, list)


class TestEdgesByAttribute:
    """Test finding edges by attribute."""

    @pytest.mark.parametrize(
        "attribute,value,operator,validator",
        [
            ("capacity", 10, "==", lambda v, val: v == val),
            ("capacity", 0, ">", lambda v, val: v > val),
            ("capacity", 100, "<", lambda v, val: v < val),
        ],
    )
    def test_find_edges_with_operators(self, sample_graph, attribute, value, operator, validator):
        """Test finding edges with various comparison operators."""
        result = NetworkXGraph.edges_by_attribute(sample_graph, attribute, value, operator)

        assert isinstance(result, list)
        for edge in result:
            if len(edge) == 3:  # MultiGraph: (u, v, key)
                u, v, key = edge
                edge_value = sample_graph.edges[u, v, key].get(attribute)
            else:  # Regular graph: (u, v)
                u, v = edge
                edge_value = sample_graph.edges[u, v].get(attribute)
            if edge_value is not None:
                assert validator(edge_value, value)

    def test_find_edges_attribute_not_exists(self, sample_graph):
        """Test finding edges by non-existent attribute."""
        result = NetworkXGraph.edges_by_attribute(sample_graph, "nonexistent_attr", "value", "==")
        assert isinstance(result, list)


class TestAttributeDiscovery:
    """Test attribute discovery functionality."""

    @pytest.mark.parametrize(
        "search_term,element_type,expected_attr",
        [
            ("ho", "node", "holdup_max"),
            ("cap", "edge", "capacity"),
        ],
    )
    def test_find_attributes(self, sample_graph, search_term, element_type, expected_attr):
        """Test finding attributes that match a pattern."""

        if element_type == "node":
            matching_attributes = NetworkXGraph.matching_attributes(sample_graph, search_term, type="node")
        else:
            matching_attributes = NetworkXGraph.matching_attributes(sample_graph, search_term, type="edge")

        assert expected_attr in matching_attributes

    def test_case_insensitive_attribute_search(self, sample_graph):
        """Test that attribute search is case-insensitive."""
        search_upper = "CM1"
        search_lower = "cm1"

        matches_upper = NetworkXGraph.matching_attributes(sample_graph, search_upper, type="node")
        matches_lower = NetworkXGraph.matching_attributes(sample_graph, search_lower, type="node")

        assert matches_upper == matches_lower


class TestIntegrationScenarios:
    """Integration tests combining multiple operations."""

    def test_cache_and_query_workflow(self, sample_graph_data):
        """Test complete workflow: cache graph, then query it."""
        # Cache the graph
        cache_graph("integration_test", sample_graph_data)

        # Resolve and query
        G = _resolve_graph(graph_data=None, graph_uri="graph://integration_test")

        # Find nodes by attribute
        nodes_result = NetworkXGraph.nodes_by_attribute(G, "object_type", "node", "==")
        assert isinstance(nodes_result, list)

        # Find edges by attribute
        edges_result = NetworkXGraph.edges_by_attribute(G, "capacity", 0, ">")
        assert isinstance(edges_result, list)

    def test_multiple_queries_on_same_graph(self, example_graph):
        """Test running multiple queries on the same graph."""
        # Query 1: Find shortest path
        try:
            path = nx.shortest_path(example_graph, source="0", target="5")
            assert len(path) >= 2
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            pass

        # Query 2: Get all nodes (just verify it works)
        nodes = list(example_graph.nodes())
        assert len(nodes) > 0

        # Query 3: Get all edges
        edges = list(example_graph.edges())
        assert isinstance(edges, list)

    def test_graph_data_validation(self, sample_graph_data):
        """Test that graph data is properly validated."""
        # Valid data should work
        graph_model = GraphDataModel.model_validate(sample_graph_data)
        assert graph_model is not None

        # Can create a graph from validated data
        G = Graph(graph_model).graph
        assert isinstance(G, nx.Graph)

    def test_multiple_graph_caching(self, sample_graph_data, example_graph_data):
        """Test caching and working with multiple graphs."""
        # Cache first graph
        cache_graph("graph1", sample_graph_data)
        g1 = _resolve_graph(graph_data=None, graph_uri="graph://graph1")

        # Cache second graph
        cache_graph("graph2", example_graph_data)
        g2 = _resolve_graph(graph_data=None, graph_uri="graph://graph2")

        # Both graphs should be accessible
        assert g1.number_of_nodes() > 0
        assert g2.number_of_nodes() > 0

        # They should be different graph instances
        assert id(g1) != id(g2)
