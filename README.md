# NetworkX MCP Server

This repository provides an MCP (Model Context Protocol) server that exposes a small set of **graph analytics tools** built on top of **NetworkX**. The server is implemented using **FastMCP** and hosted via **FastAPI**.

The tools are designed to be easy for an LLM to call correctly: each tool takes a graph in **NetworkX node-link JSON** format and returns a small JSON object.

## Project Structure

```
networkx-mcp/
├── main.py                  # Server entry point (FastAPI + FastMCP)
├── src/
│   ├── cache.py            # Graph caching infrastructure
│   ├── tools.py            # MCP tool definitions
│   ├── resources.py        # MCP resource definitions
│   └── base/
│       ├── base.py         # Graph construction utilities
│       └── graph_analytics.py  # Node/edge filtering logic
├── data/                   # Example graph JSON files
└── pyproject.toml          # Project dependencies
```

**Key principles:**

- `main.py` only initializes and starts the server
- Tools are defined in `src/tools.py` and registered via `register_tools()`
- Resources are defined in `src/resources.py` and registered via `register_resources()`
- Graph caching logic is isolated in `src/cache.py`

## Graph input format (important)

All tools that accept `graph_data` expect **NetworkX node-link JSON** (a Python `dict`), as produced by `networkx.node_link_data(G)`.

Minimum required structure:

- `nodes`: list of node objects, each containing an `id`
- `links` **or** `edges`: list of edge objects containing `source` and `target`

Optional flags:

- `directed` (bool): defaults to `true` if missing
- `multigraph` (bool): defaults to `true` if missing

Example: see `data/example_graph.json` and `data/sample_graph_attr.json`.

## Efficient graph loading (recommended)

To minimize context and traffic, use the **graph caching workflow** instead of passing full graph JSON on every tool call:

1. **Load once**: Call `load_graph_from_file` with a file path
2. **Reference many times**: Use the returned `graph://` URI in subsequent tool calls

**Example workflow**:

```python
# Step 1: Load the graph (transmits file path only, ~50 bytes)
result = load_graph_from_file(
    path="/path/to/my_graph.json",
    alias="mygraph"
)
# Returns: {"status": "loaded", "uri": "graph://mygraph", "node_count": 100, ...}

# Step 2: Use the URI in all subsequent calls (transmits ~20 bytes)
path = shortest_path(
    graph_uri="graph://mygraph",  # ← Reference cached graph
    source="A",
    target="B"
)

# Step 3: More calls using same URI
nodes = find_nodes_by_attribute(
    graph_uri="graph://mygraph",
    attribute="type",
    operator="==",
    value="important"
)
```

**Traffic comparison**:

- ❌ **Without caching**: Every call transmits full graph JSON (could be megabytes)
- ✅ **With caching**: Load once (~file size), then every call transmits just ~20 bytes for URI

**Note**: All tools support **both** `graph_data` (direct JSON) and `graph_uri` (cached reference). Choose the best approach for your use case.

## Tools

### `load_graph_from_file`

Load a graph from a JSON file and cache it server-side for efficient reuse.

- Inputs:
  - `path` (str): absolute or relative file path to a NetworkX node-link JSON file
  - `alias` (str, optional): cache key (default: `"default"`)
- Output:
  - Success: `{"status": "loaded", "alias": "...", "uri": "graph://...", "node_count": N, "edge_count": M, "directed": bool, "multigraph": bool}`
  - Failure: `{"error": "..."}` (e.g., file not found, invalid JSON, invalid graph schema)
- Side effects: **Stores graph in server memory**. Use the returned `uri` in subsequent tool calls to avoid re-transmitting graph data.

### `health_check`

Liveness probe.

- Inputs: none
- Output: `{"status": "ok"}`
- Side effects: none

### `shortest_path`

Compute an **unweighted** shortest path between two nodes.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `source` (str): node id (must exist)
  - `target` (str): node id (must exist)
- Output:
  - Success: `{"path": ["nodeA", "nodeB", ...]}`
  - Failure: `{"error": "..."}` (e.g., no path, node not found, invalid schema)
- Side effects: none

### `find_nodes_by_attribute`

Filter nodes by a node attribute using a comparison operator.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `attribute` (str): node attribute key
  - `value` (any | null): value to compare against; if `null`, the tool only checks attribute presence
  - `operator` (str): one of `==`, `!=`, `<`, `<=`, `>`, `>=`
- Behavior:
  - If `value` is `null`: returns nodes where `attrs[attribute]` exists and is not null.
  - Else: returns nodes where `attrs[attribute] operator value` is true.
- Output:
  - Success: `{"matching_nodes": ["A", "B", ...]}`
  - Failure: `{"error": "..."}` (e.g., unsupported operator, incomparable types)

### `find_edges_by_attribute`

Filter edges by an edge attribute using a comparison operator.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `attribute` (str): edge attribute key
  - `value` (any | null)
  - `operator` (str): one of `==`, `!=`, `<`, `<=`, `>`, `>=`
- Output:
  - Success: `{"matching_edges": [...]}`
    - For MultiGraphs: list of tuples `(u, v, key)`
    - For non-MultiGraphs: list of tuples `(u, v)`
  - Failure: `{"error": "..."}`

### `find_best_matching_node_attribute`

Discover **node attribute names** that partially match a search string.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `attribute` (str): search string
- Behavior: case-insensitive substring match against node attribute keys.
- Output: `{"matching_attributes": ["holdup_max", "holdup_min", ...]}`

### `find_best_matching_edge_attribute`

Discover **edge attribute names** that partially match a search string.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `attribute` (str): search string
- Behavior: case-insensitive substring match against edge attribute keys.
- Output: `{"matching_attributes": ["capacity", "transport_time", ...]}`

### `find_best_matching_node_attribute_vals`

Search **node attribute values** by substring match and return matching nodes grouped by the matched value.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `attribute` (str): exact node attribute key
  - `comparison` (str): substring to search for (case-insensitive)
- Output:
  - `{"matching_nodes": {"<value_as_string>": ["node1", "node2"], ...}}`

### `find_best_matching_edge_attribute_vals`

Search **edge attribute values** by substring match and return matching edges grouped by the matched value.

- Inputs:
  - `graph_data` (dict, optional): node-link graph **OR**
  - `graph_uri` (str, optional): cached graph reference (e.g., `"graph://default"`)
  - `attribute` (str): exact edge attribute key
  - `comparison` (str): substring to search for (case-insensitive)
- Output:
  - `{"matching_edges": {"<value_as_string>": [(u, v) or (u, v, key), ...], ...}}`

## Run the server

This repo uses a `justfile`.

- Start FastAPI (serves MCP under `/api/mcp`):
  - `just fastapi_run`

- Start via FastMCP CLI (HTTP transport):
  - `just mcp_run`

Default URL used by `client.py`:

- `http://localhost:8000/api/mcp`

## Notes for LLM tool callers

- Always pass a **single** params object when calling tools (e.g., `{"graph_uri": "graph://default", "source": "A", "target": "B"}`).
- Node IDs are typically strings (see the example JSON files).
- **For efficiency**: Use `load_graph_from_file` once to cache the graph, then reference it via `graph_uri` in all subsequent calls. This reduces traffic from megabytes to bytes.
- **Flexibility**: All tools accept **either** `graph_data` (direct JSON) **or** `graph_uri` (cached reference), but not both simultaneously.
- For numeric comparisons (`<`, `>=`, ...), ensure the attribute value in the graph is numeric and the provided `value` is numeric too.
