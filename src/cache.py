"""Graph cache management for the MCP server.

This module provides a global in-memory cache for loaded graphs,
along with a helper function to resolve graphs from either direct
data or cached URIs.
"""

import networkx as nx

from src.base.base import Graph
from src.classes import GraphDataModel

# Global cache for loaded graphs
_loaded_graphs: dict[str, dict] = {}


def _resolve_graph(graph_data: dict | None, graph_uri: str | None) -> nx.Graph:
    """Resolve a graph from either direct data or a cached URI.

    Parameters
    ----------
    graph_data : dict | None
        Direct node-link graph data.
    graph_uri : str | None
        URI of a cached graph (e.g., 'graph://default').

    Returns
    -------
    networkx.Graph
        The resolved graph instance.

    Raises
    ------
    ValueError
        If neither or both parameters are provided, or if the URI is not found.
    """
    if graph_uri:
        if not graph_uri.startswith("graph://"):
            raise ValueError(f"Invalid graph URI '{graph_uri}'. Expected 'graph://<alias>'.")
        alias = graph_uri.replace("graph://", "")
        if alias not in _loaded_graphs:
            raise ValueError(f"Graph '{alias}' not found. Load it first with load_graph_from_file.")
        return Graph(GraphDataModel.model_validate(_loaded_graphs[alias])).graph

    # At this point, graph_data must be a dict (we validated above)
    if not isinstance(graph_data, dict):
        raise ValueError("No graph data provided. Please provide either graph_data or graph_uri.")
    return Graph(GraphDataModel.model_validate(graph_data)).graph


def get_cached_graph(alias: str) -> dict | None:
    """Get a cached graph by alias.

    Parameters
    ----------
    alias : str
        The graph cache key.

    Returns
    -------
    dict | None
        The cached node-link graph data, or None if not found.
    """
    return _loaded_graphs.get(alias)


def cache_graph(alias: str, graph_data: dict) -> None:
    """Cache a graph under the given alias.

    Parameters
    ----------
    alias : str
        The cache key.
    graph_data : dict
        Node-link graph data to cache.
    """
    _loaded_graphs[alias] = graph_data


def is_cached(alias: str) -> bool:
    """Check if a graph is cached.

    Parameters
    ----------
    alias : str
        The cache key to check.

    Returns
    -------
    bool
        True if the graph is cached, False otherwise.
    """
    return alias in _loaded_graphs
