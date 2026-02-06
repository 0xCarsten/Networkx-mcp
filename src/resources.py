"""MCP resource definitions for the NetworkX server."""

import json

from fastmcp import FastMCP

from src.cache import get_cached_graph


def get_graph_resource(alias: str) -> str:
    """Return the cached graph data as JSON.

    This resource allows clients to query loaded graphs without re-transmitting
    the full graph data. Use load_graph_from_file to populate the cache first.

    Parameters
    ----------
    alias : str
        The graph alias (e.g., 'default').

    Returns
    -------
    str
        JSON representation of the cached node-link graph data.
    """
    graph_data = get_cached_graph(alias)
    if graph_data is None:
        return json.dumps({"error": f"Graph '{alias}' not found. Use load_graph_from_file to load it first."})
    return json.dumps(graph_data)


def register_resources(mcp: FastMCP) -> None:
    """Register all MCP resources with the server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance.
    """

    @mcp.resource("graph://{alias}")
    def _get_graph_resource(alias: str) -> str:
        """MCP resource wrapper for get_graph_resource."""
        return get_graph_resource(alias)
