fastapi_run:
    uvicorn main:app --reload

mcp_run:
    fastmcp run main.py:mcp --transport http --port 8000