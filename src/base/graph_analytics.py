import operator
from abc import ABC, abstractmethod
from typing import Any, Literal

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


class BaseGraph(ABC):

    @classmethod
    @abstractmethod
    def type_cast(cls, value: Any) -> Any:
        """Attempt to cast a value to float if possible, else return as string."""

        raise NotImplementedError

    @classmethod
    @abstractmethod
    def nodes_by_attribute(cls, G, attribute: str, **kwargs) -> list:
        """Return node IDs whose node attribute matches a predicate."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def edges_by_attribute(cls, G, attribute: str, **kwargs) -> list:
        """Return edge IDs whose edge attribute matches a predicate."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def matching_attribute(cls, G, attribute: str, type: Literal["node", "edge", "all"], **kwargs) -> list:
        """Return the best matching attribute name in the graph for a given input."""
        raise NotImplementedError


class NetworkXGraph(BaseGraph):
    def __init__(self, graph_data):
        pass

    @classmethod
    def type_cast(cls, value: Any):
        """Attempt to cast a value to float if possible, else return as string."""

        try:
            value = float(value)
        except (ValueError, TypeError):
            pass
        return value

    @classmethod
    def nodes_by_attribute(
        cls, G: nx.Graph, attribute: str, value: Any | None = None, operator: str = "==", **kwargs
    ) -> list:
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
        value = cls.type_cast(value)
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

    @classmethod
    def edges_by_attribute(
        cls, G: nx.Graph, attribute: str, value: Any | None = None, operator: str = "==", **kwargs
    ) -> list:
        if operator not in operator_map:
            raise ValueError(f"Unsupported operator '{operator}'. Supported: {sorted(operator_map.keys())}")
        value = cls.type_cast(value)
        logger.info(f"Type-cast value: {value} (type: {type(value)})")
        logger.info(f"Finding edges with attribute '{attribute}' {operator} '{value}'")
        logger.info(f"Using operator function: {operator_map[operator]}")
        if G.is_multigraph():
            if value is None:
                return [
                    (u, v, k) for u, v, k, attrs in G.edges(keys=True, data=True) if attrs.get(attribute) is not None
                ]
            operator_func = operator_map[operator]
            matches = []
            for u, v, k, attrs in G.edges(keys=True, data=True):
                edge_val = attrs.get(attribute)
                if edge_val is None:
                    continue
                if operator_func(edge_val, value):
                    matches.append((u, v, k))
            return matches
        else:
            if value is None:
                return [(u, v) for u, v, attrs in G.edges(data=True) if attrs.get(attribute) is not None]
            operator_func = operator_map[operator]
            matches = []
            for u, v, attrs in G.edges(data=True):
                edge_val = attrs.get(attribute)
                if edge_val is None:
                    continue
                if operator_func(edge_val, value):
                    matches.append((u, v))
            return matches

    @classmethod
    def matching_attributes(
        cls, G: nx.Graph, attribute: str, type: Literal["node", "edge", "all"], **kwargs
    ) -> list[str]:
        """Return the all matching attribute names in the graph for a given input."""

        match type:
            case "node":
                all_attrs = {attr for _, attrs in G.nodes(data=True) for attr in attrs}
            case "edge":
                all_attrs = {attr for _, _, attrs in G.edges(data=True) for attr in attrs}
            case "all":
                # Get all attribute keys from nodes and edges
                node_attrs = {attr for _, attrs in G.nodes(data=True) for attr in attrs}
                edge_attrs = {attr for _, _, attrs in G.edges(data=True) for attr in attrs}
                all_attrs = node_attrs.union(edge_attrs)

        matches = [attr for attr in all_attrs if attribute.lower() in attr.lower()]
        return matches
