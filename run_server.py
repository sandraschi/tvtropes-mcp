"""PyInstaller entry point — dual transport (HTTP / stdio)."""
import logging
import os
import sys

sys.path.insert(0, ".")

logging.getLogger().setLevel(logging.INFO)

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
host = os.environ.get("MCP_HOST", "127.0.0.1")

if port:
    import uvicorn

    from tvtropes_mcp.app import app

    uvicorn.run(app, host=host, port=int(port), log_config=None)
else:
    import asyncio

    from tvtropes_mcp.server import mcp

    asyncio.run(mcp.run_stdio_async())
