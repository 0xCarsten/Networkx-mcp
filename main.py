"""NetworkX MCP Server entry point.

This module initializes and starts the FastMCP server with FastAPI hosting.
All tools and resources are registered from their respective modules.
"""

from fastapi import FastAPI
from fastmcp import FastMCP

from src.resources import register_resources
from src.tools import register_tools

mcp = FastMCP("NetworkX MCP Server")

register_tools(mcp)
register_resources(mcp)

# Create FastAPI app with MCP integration
mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(title="NetworkX MCP Server", lifespan=mcp_app.lifespan)

app.name = "networkx_mcp"

app.mount("/api", mcp_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
