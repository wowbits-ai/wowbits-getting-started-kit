#!/usr/bin/env python3
"""
server.py — WowBits Kali Linux MCP Server entry point.

Runs directly inside the Kali Docker container.
It hosts a FastMCP HTTP server on port 8765, executing tools locally via subprocess.
"""

import logging
import os
import sys

from fastmcp import FastMCP

# Ensure the project root is on sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools import register_all

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

mcp = FastMCP("WowBitsKaliMCP")
register_all(mcp)

if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8765"))
    logger.info("WowBits Kali Linux MCP Server starting")
    logger.info("MCP endpoint:    http://%s:%d/mcp", host, port)
    mcp.run(transport="streamable-http", host=host, port=port)
