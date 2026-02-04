import operator
from typing import Any

import networkx as nx
from loguru import logger

operator_map = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def type_cast(value: Any):
    """Attempt to cast a value to float if possible, else return as string."""

    try:
        value = float(value)
    except (ValueError, TypeError):
        pass
    return value


def nodes_by_attribute(G: nx.Graph, attribute: str, value: Any | None = None, operator: str = "=="):
    """Return node IDs whose node attribute matches a predicate.

    Parameters
    ----------
    G : networkx.Graph
        Input graph.
    attribute : str
        Node attribute key to test.
    value : Any | None
        If None, the predicate is "attribute exists and is not None".
        Otherwise, compare the node's attribute value to this value.
    operator : str
        One of: '==', '!=', '<', '<=', '>', '>='.

    Returns
    -------
    list
        List of node IDs (as stored in the graph).
    """
    if operator not in operator_map:
        raise ValueError(f"Unsupported operator '{operator}'. Supported: {sorted(operator_map.keys())}")
    value = type_cast(value)
    logger.info(f"Type-cast value: {value} (type: {type(value)})")
    logger.info(f"Finding nodes with attribute '{attribute}' {operator} '{value}'")
    logger.info(f"Using operator function: {operator_map[operator]}")
    if value is None:
        matching_nodes = [node for node, attrs in G.nodes(data=True) if attrs.get(attribute) is not None]
    else:
        operator_func = operator_map[operator]
        matching_nodes = []
        for node, attrs in G.nodes(data=True):
            node_val = attrs.get(attribute, None)
            if node_val is None:
                continue
            if operator_func(node_val, value):
                matching_nodes.append(node)
    return matching_nodes


def edges_by_attribute(G: nx.Graph, attribute: str, value: Any | None = None, operator: str = "=="):
    """Return edges whose edge attribute matches a predicate.

    Parameters
    ----------
    G : networkx.Graph
        Input graph.
    attribute : str
        Edge attribute key to test.
    value : Any | None
        If None, the predicate is "attribute exists and is not None".
        Otherwise, compare the edge's attribute value to this value.
    operator : str
        One of: '==', '!=', '<', '<=', '>', '>='.

    Returns
    -------
    list
        - For MultiGraphs: list of (u, v, key)
        - For non-MultiGraphs: list of (u, v)
    """
    if operator not in operator_map:
        raise ValueError(f"Unsupported operator '{operator}'. Supported: {sorted(operator_map.keys())}")

    operator_func = operator_map[operator]

    if G.is_multigraph():
        if value is None:
            return [(u, v, k) for u, v, k, attrs in G.edges(keys=True, data=True) if attrs.get(attribute) is not None]
        matches = []
        for u, v, k, attrs in G.edges(keys=True, data=True):
            edge_val = attrs.get(attribute)
            if edge_val is None:
                continue
            if operator_func(edge_val, value):
                matches.append((u, v, k))
        return matches

    # Non-multigraph
    if value is None:
        return [(u, v) for u, v, attrs in G.edges(data=True) if attrs.get(attribute) is not None]
    matches = []
    for u, v, attrs in G.edges(data=True):
        edge_val = attrs.get(attribute)
        if edge_val is None:
            continue
        if operator_func(edge_val, value):
            matches.append((u, v))
    return matches
