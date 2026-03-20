"""
tools/__init__.py — Auto-discovery for tool modules.

Any .py file dropped into this directory is loaded automatically.
Each module must expose a  register(mcp)  function that decorates
its tool functions with @mcp.tool().
"""

import importlib
import logging
import os

logger = logging.getLogger(__name__)


def register_all(mcp) -> None:
    """
    Scan this directory and call register(mcp) on every tool module found.
    Import errors are logged but do not stop other tools from loading.
    """
    tools_dir = os.path.dirname(__file__)
    for filename in sorted(os.listdir(tools_dir)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue
        module_name = f"tools.{filename[:-3]}"
        try:
            mod = importlib.import_module(module_name)
            if hasattr(mod, "register"):
                mod.register(mcp)
                logger.debug("Loaded tool module: %s", module_name)
            else:
                logger.warning("Skipping %s — no register() function found.", module_name)
        except Exception as exc:
            logger.error("Failed to load %s: %s", module_name, exc)
