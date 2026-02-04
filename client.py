import asyncio
import json

from fastmcp import Client

client = Client("http://localhost:8000/api/mcp")


async def call_tool(name: str):
    async with client:
        result = await client.call_tool("health_check")
        print(result)


async def shortest_path(graph_data: dict, source: str, target: str):
    async with client:
        # fastmcp Client.call_tool does not accept arbitrary kwargs for tool params;
        # pass a single params dict as the second positional argument instead.
        params = {"graph_data": graph_data, "source": source, "target": target}
        result = await client.call_tool("shortest_path", params)
        print(result)


with open("data/example_graph.json") as f:
    graph_data = json.load(f)

asyncio.run(shortest_path(graph_data, "0", "19"))


async def find_nodes_by_attribute(graph_data: dict, attribute: str, value=None, operator: str = "=="):
    async with client:
        params = {
            "graph_data": graph_data,
            "attribute": attribute,
            "value": value,
            "operator": operator,
        }
        result = await client.call_tool("find_nodes_by_attribute", params)
        print(result)


async def find_edges_by_attribute(graph_data: dict, attribute: str, value=None):
    async with client:
        params = {"graph_data": graph_data, "attribute": attribute, "value": value}
        result = await client.call_tool("find_edges_by_attribute", params)
        print(result)


async def matching_node_attribute(graph_data: dict, attribute: str, comparison: str):
    async with client:
        params = {
            "graph_data": graph_data,
            "attribute": attribute,
            "comparison": comparison,
        }
        result = await client.call_tool("find_best_matching_node_attribute", params)
        print(result)


async def matching_edge_attribute(graph_data: dict, attribute: str, comparison: str):
    async with client:
        params = {
            "graph_data": graph_data,
            "attribute": attribute,
            "comparison": comparison,
        }
        result = await client.call_tool("find_best_matching_edge_attribute", params)
        print(result)


async def best_matching_edge_attribute(graph_data: dict, attribute: str):
    async with client:
        params = {"graph_data": graph_data, "attribute": attribute}
        result = await client.call_tool("find_best_matching_edge_attribute", params)
        print(result)


async def best_matching_node_attribute(graph_data: dict, attribute: str):
    async with client:
        params = {"request": {"path": "data/sample_graph_attr.json", "alias": "test"}}
        result = await client.call_tool("load_graph_from_file", params)
        params = {"request": {"uri": "graph://test", "attribute": attribute}}
        result = await client.call_tool("find_best_matching_node_attribute", params)
        print(result)


with open("data/sample_graph_attr.json") as f:
    graph_data = json.load(f)
# with open("data/sap_supergraph.json") as f:
#     graph_data = json.load(f)

# asyncio.run(find_nodes_by_attribute(graph_data, operator= "<", attribute="holdup_max", value=100.0))
# asyncio.run(matching_node_attribute(graph_data, "object_type", "a"))
# asyncio.run(matching_edge_attribute(graph_data, "capacity", "1"))
asyncio.run(best_matching_node_attribute(graph_data, "ho"))

# asyncio.run(find_nodes_by_attribute(graph_data, "CM1"))

# asyncio.run(find_edges_by_attribute(graph_data, "demand",[]))
