"""MCP tool definitions for the NetworkX server.

This module contains all tool implementations that expose NetworkX
graph analytics functionality via the Model Context Protocol.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import networkx as nx
from fastmcp import FastMCP

from src.base.base import Graph
from src.base.graph_analytics import NetworkXGraph
from src.cache import _resolve_graph, cache_graph
from src.classes import (
    AttributeMatchRequest,
    AttributeValueFilter,
    ErrorModel,
    GraphCacheModel,
    GraphDataModel,
    GraphPathModel,
    ResultsAttributesModel,
    ResultsModel,
)


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance.
    """

    @mcp.tool(
        name="load_graph_from_file",
        description=(
            "Load a graph from a JSON file and cache it server-side under an alias. "
            "Subsequent tool calls can reference 'graph://<alias>' instead of transmitting the full graph. "
            "Side effects: loads file from disk, caches graph in server memory."
        ),
    )
    def load_graph_from_file(path: str, alias: str = "default") -> GraphCacheModel | ErrorModel:
        """Load a graph from a JSON file and cache it.

        This eliminates the need to transmit large graph_data on every tool call.
        After loading, use the returned URI (e.g., 'graph://default') in other tools.

        Parameters
        ----------
        path : str
            The file path of the graph JSON file.
        alias : str, optional
            The alias under which to cache the graph (default is "default").

        Returns
        -------
        GraphCacheModel
            Status information and the resource URI.
        """
        try:
            request = GraphPathModel(path=path, alias=alias)
            file_path = Path(request.path)
            if not file_path.exists():
                return ErrorModel(error=f"File not found: {request.path}")
            if not file_path.is_file():
                return ErrorModel(error=f"Path is not a file: {request.path}")

            with open(file_path, encoding="utf-8") as f:
                graph_data = GraphDataModel.model_validate(json.load(f))
            # Validate by creating a graph (will raise if invalid)
            _ = Graph(graph_data).graph

            # Cache the raw data
            cache_graph(request.alias, graph_data.model_dump())

            return GraphCacheModel(
                alias=request.alias,
                status="loaded",
                uri=f"graph://{request.alias}",
            )
        except json.JSONDecodeError as e:
            return ErrorModel(error=f"Invalid JSON: {e}")
        except Exception as e:
            return ErrorModel(error=f"Failed to load graph: {e}")

    @mcp.tool(
        name="health",
        description=(
            "Return a minimal liveness response to confirm the MCP server is reachable. "
            "Inputs: none. Output: {status: 'ok'}. Side effects: none."
        ),
    )
    def health():
        """Return a liveness probe response."""
        return {"status": "ok"}

    @mcp.tool(
        name="shortest_path",
        description=(
            "Compute an unweighted shortest path between two nodes in a graph. "
            "Inputs: (graph_data OR graph_uri), source (node id as string), target (node id as string). "
            "graph_data: direct node-link JSON dict. graph_uri: cached graph URI like 'graph://default'. "
            "Output: {path: [node_id, ...]} if a path exists; otherwise {error: <message>}. "
            "Side effects: none (graph is created in-memory)."
        ),
    )
    def shortest_path(
        source: str,
        target: str,
        graph_data: dict | None = None,
        graph_uri: str | None = None,
    ):
        """Compute an unweighted shortest path.

        Notes
        -----
        - This uses NetworkX's default shortest path for unweighted graphs.
        - For directed graphs, the path respects edge direction.
        - The input graph must be in NetworkX node-link format (as produced by `networkx.node_link_data`).
          This project accepts both 'links' and 'edges' as the edge list key.
        """
        try:
            G = _resolve_graph(graph_data, graph_uri)
            path = nx.shortest_path(G, source=source, target=target)
            return {"path": path}
        except nx.NetworkXNoPath:
            return {"error": f"No path found between {source} and {target}."}
        except (nx.NodeNotFound, KeyError, TypeError, ValueError) as e:
            return {"error": f"Invalid input: {e}"}

    @mcp.tool(
        name="find_nodes_by_attribute",
        description=(
            "Filter nodes by a node attribute using a comparison operator. "
            "Inputs: {request: {'uri': <uri>, 'attribute': <attribute>, 'value': <value>, 'operator': <operator>}}. "
            "value (float or str), operator (one of '==', '!=', '<', '<=', '>', '>='). "
            "Behavior: if value is null, returns nodes where the attribute exists and is not null. "
            "If value is provided, compares node_attr <op> value using Python semantics; the values must be comparable. "
            "Output: {matching_nodes: [node_id, ...]}. Side effects: none."
        ),
    )
    def find_nodes_by_attribute(
        uri: str,
        attribute: str,
        value: float | str,
        operator: Literal["==", "!=", "<", "<=", ">", ">="],
        graph_data: dict | None = None,
    ) -> ResultsModel | ErrorModel:
        """Return a list of node IDs whose node attribute matches the requested predicate.
        E.g "find all nodes where 'age' > 30" or "find all nodes where 'type' == 'person'".

        Parameters
        ----------
        uri: str
            The URI of the cached graph (e.g., 'graph://default').
        attribute : str
            The node attribute key to test.
        value : float | str
            The value to compare against.
        operator : Literal["==", "!=", "<", "<=", ">", ">="]
            The comparison operator.
        graph_data : dict | None, optional
            The graph data in node-link format (if not using a cached URI).

        Returns
        -------
        ResultsModel
            List of matching node IDs.

        """
        try:
            request = AttributeValueFilter(
                uri=uri,
                attribute=attribute,
                value=value,
                operator=operator,
                graph_data=graph_data,
            )
            G = _resolve_graph(request.graph_data, request.uri)
            matching_nodes = NetworkXGraph.nodes_by_attribute(G, request.attribute, request.value, request.operator)
            return ResultsModel(matches=matching_nodes)
        except (KeyError, TypeError, ValueError) as e:
            return ErrorModel(error=f"Invalid input: {e}")

    @mcp.tool(
        name="find_edges_by_attribute",
        description=(
            "Filter edges by an edge attribute using a comparison operator. "
            "Inputs: {request: {'uri': <uri>, 'attribute': <attribute>, 'value': <value>, 'operator': <operator>}}. "
            "Behavior: if value is null, returns edges where the attribute exists and is not null. "
            "If value is provided, compares edge_attr <op> value using Python semantics; the values must be comparable. "
            "Output: {matches: [...]}. For MultiGraphs, each edge is a tuple (u, v, key). For non-MultiGraphs, each edge is (u, v). "
            "Side effects: none."
        ),
    )
    def find_edges_by_attribute(
        uri: str,
        attribute: str,
        value: float | str,
        operator: Literal["==", "!=", "<", "<=", ">", ">="],
        graph_data: dict | None = None,
    ) -> ResultsModel | ErrorModel:
        """Return a list of edges IDs whose edges attribute matches the requested predicate.
        E.g "find all edges where 'weight' < 1.0" or "find all edges where 'type' == 'friends'".

        Parameters
        ----------
        uri : str
            The URI of the cached graph (e.g., 'graph://default').
        attribute : str
            The edge attribute key to test.
        value : float | str
            The value to compare against.
        operator : Literal["==", "!=", "<", "<=", ">", ">="]
            The comparison operator.
        graph_data : dict | None, optional
            The graph data in node-link format (if not using a cached URI).
        Returns
        -------
        ResultsModel
            List of matching edges.

        """
        try:
            request = AttributeValueFilter(
                uri=uri,
                attribute=attribute,
                value=value,
                operator=operator,
                graph_data=graph_data,
            )
            G = _resolve_graph(request.graph_data, request.uri)
            matching_edges = NetworkXGraph.edges_by_attribute(G, request.attribute, request.value, request.operator)
            return ResultsModel(matches=matching_edges)
        except (KeyError, TypeError, ValueError) as e:
            return ErrorModel(error=f"Invalid input: {e}")

    @mcp.tool(
        name="find_best_matching_node_attribute",
        description=(
            "Discover node attribute names present in the graph that *partially* match a search string. "
            "Behavior: collects all node attribute keys where search_string is a case-insensitive substring of the key. "
            "Output: {matching_attributes: [attribute_name, ...]} (unique list). Side effects: none."
        ),
    )
    def find_best_matching_node_attribute(
        uri: str, attribute: str, graph_data: dict | None = None
    ) -> ResultsAttributesModel | ErrorModel:
        """Return a list of node attribute keys which at least partially matches the provided attribute.
        E.g. if attribute="age", it would match "age", "age_years", "average_age", etc.

        Parameters
        ----------
        uri : str
            The URI of the cached graph (e.g., 'graph://default').
        attribute : str
            The search string to match against attribute keys.
        graph_data : dict | None, optional
            The graph data in node-link format (if not using a cached URI).

        Returns
        -------
        ResultsAttributesModel
            List of matching attribute names.
        """
        request = AttributeMatchRequest(uri=uri, attribute=attribute, graph_data=graph_data)
        try:
            G = _resolve_graph(request.graph_data, request.uri)
        except ValueError as e:
            return ErrorModel(error=str(e))

        matching_attributes = NetworkXGraph.matching_attributes(G, request.attribute, type="node")

        return ResultsAttributesModel(matching_attributes=list(set(matching_attributes)))

    @mcp.tool(
        name="find_best_matching_edge_attribute",
        description=(
            "Discover edge attribute names present in the graph that *partially* match a search string. "
            "Inputs: {request: {'uri': <uri>, 'attribute': <attribute>}}. "
            "Behavior: collects all edge attribute keys where search_string is a case-insensitive substring of the key. "
            "Output: {matching_attributes: [attribute_name, ...]} (unique list). Side effects: none."
        ),
    )
    def find_best_matching_edge_attribute(
        request: AttributeMatchRequest,
    ) -> ResultsAttributesModel | ErrorModel:
        """Return a list of edge attribute keys which at least partially matches the provided attribute.
        E.g. if attribute="weight", it would match "weight", "max_weight", "average_weight", etc.


        Parameters
        ----------
        uri : str
            The URI of the cached graph (e.g., 'graph://default').
        attribute : str
            The search string to match against attribute keys.
        graph_data : dict | None, optional
            The graph data in node-link format (if not using a cached URI).


        Returns
        -------
        ResultsAttributesModel
            List of matching attribute names.

        """
        try:
            G = _resolve_graph(request.graph_data, request.uri)
        except ValueError as e:
            return ErrorModel(error=str(e))

        matching_attributes = NetworkXGraph.matching_attributes(G, request.attribute, type="edge")

        return ResultsAttributesModel(matching_attributes=list(set(matching_attributes)))
