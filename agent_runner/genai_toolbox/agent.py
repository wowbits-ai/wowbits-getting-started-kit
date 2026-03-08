import json
import logging
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams, SseConnectionParams
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Path to mcp_configs.json
MCP_CONFIGS_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "mcps", "mcp_configs.json"
)

MCP_NAME = "genai_toolbox"


def load_mcp_toolset():
    """Load MCP toolset from mcp_configs.json by name."""
    with open(MCP_CONFIGS_JSON, "r") as f:
        data = json.load(f)

    for mcp in data.get("mcps", []):
        if mcp.get("name") == MCP_NAME:
            url = mcp.get("url")
            config = mcp.get("config", {})
            transport_mode = config.get("transport_mode", "http")

            if not url:
                raise RuntimeError(f"MCP '{MCP_NAME}' has no 'url' in mcp_configs.json")

            if transport_mode == "http":
                logger.info(f"Connecting to MCP '{MCP_NAME}' via HTTP at {url}")
                return MCPToolset(connection_params=StreamableHTTPConnectionParams(url=url))
            elif transport_mode == "sse":
                logger.info(f"Connecting to MCP '{MCP_NAME}' via SSE at {url}")
                return MCPToolset(connection_params=SseConnectionParams(url=url))
            else:
                raise RuntimeError(f"Unknown transport_mode '{transport_mode}' for MCP '{MCP_NAME}'")

    raise RuntimeError(f"MCP '{MCP_NAME}' not found in {MCP_CONFIGS_JSON}")


INSTRUCTIONS = """You are a database assistant that helps users explore and query the WowBits SQLite database.
You have access to the GenAI Toolbox for Databases MCP server which provides SQL tools.

## Available Capabilities

1. **List Tables**: Discover all tables in the database
2. **Describe Table**: Get the schema of any table
3. **Query Data**: Run SQL SELECT queries to retrieve data
4. **Search Agents**: Find agents by name
5. **List MCP Servers**: Show all registered MCP configurations
6. **List Skills**: Show all registered skills

## Guidelines

- Always start by listing available tables if the user's request is vague
- Before querying a table, describe its schema first to understand the columns
- Use SELECT queries only - never modify data
- Present results in a clean, formatted manner
- If a query returns too many rows, use LIMIT to restrict results
- Explain what you found in plain language after retrieving data
- Be proactive: suggest related queries the user might find useful
"""

# Use HTTP mode — connects to the running MCP server via mcp_configs.json
root_agent = LlmAgent(
    name="genai_toolbox",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    description="A database assistant agent that uses the GenAI Toolbox for Databases MCP to query and explore the WowBits SQLite database via natural language.",
    instruction=INSTRUCTIONS,
    tools=[load_mcp_toolset()],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=16000,
    ),
)

logger.info(f"GenAI Toolbox agent created (HTTP mode — reading config from mcp_configs.json)")
