"""Tests for MCP resources."""

import json
import pathlib

import pytest

from src.cache import _loaded_graphs, cache_graph
from src.resources import get_graph_resource


@pytest.fixture
def sample_graph_data():
    """Load sample graph data from file."""
    with open(pathlib.Path(__file__).parents[1] / "data/sample_graph_attr.json") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the graph cache before and after each test."""
    _loaded_graphs.clear()
    yield
    _loaded_graphs.clear()


def test_get_graph_resource_found(sample_graph_data):
    """Test retrieving a cached graph resource."""
    # Cache a graph
    cache_graph("test_graph", sample_graph_data)

    # Call the resource function directly
    result = get_graph_resource(alias="test_graph")

    # Verify the result
    assert result is not None
    result_data = json.loads(result)
    assert "nodes" in result_data
    assert "links" in result_data
    assert result_data == sample_graph_data


def test_get_graph_resource_not_found():
    """Test retrieving a non-existent graph resource."""
    # Call with non-existent alias
    result = get_graph_resource(alias="nonexistent")

    # Verify error response
    result_data = json.loads(result)
    assert "error" in result_data
    assert "nonexistent" in result_data["error"]
    assert "not found" in result_data["error"].lower()


def test_get_graph_resource_multiple_graphs(sample_graph_data):
    """Test retrieving different cached graphs."""
    # Cache multiple graphs
    graph_1 = sample_graph_data
    graph_2 = {"nodes": [{"id": "x"}], "links": []}

    cache_graph("graph1", graph_1)
    cache_graph("graph2", graph_2)

    # Retrieve both graphs
    result1 = json.loads(get_graph_resource(alias="graph1"))
    result2 = json.loads(get_graph_resource(alias="graph2"))

    # Verify each graph is distinct
    assert result1 == graph_1
    assert result2 == graph_2
    assert result1 != result2


def test_cache_persistence():
    """Test that cached graphs persist across multiple calls."""
    test_data = {"nodes": [{"id": "a"}, {"id": "b"}], "links": [{"source": "a", "target": "b"}]}

    cache_graph("persistent", test_data)

    # Call multiple times
    result1 = json.loads(get_graph_resource(alias="persistent"))
    result2 = json.loads(get_graph_resource(alias="persistent"))

    assert result1 == test_data
    assert result2 == test_data
    assert result1 == result2
