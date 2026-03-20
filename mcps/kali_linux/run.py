"""
Convenience launcher for the WowBits Kali Linux MCP stack.

The Kali tool executor and FastMCP server run natively together in a single Docker container.
This script just calls the appropriate bash scripts to build and start the container.

After running this, the MCP endpoint is live at: http://localhost:8765/mcp
wowbits connects to that URL automatically — no path dependency.

Usage:
  python3 mcps/kali_linux/run.py            # start the stack
  python3 mcps/kali_linux/run.py stop       # stop the stack
"""

import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_server_dir() -> str:
  folder_name = "src/wowbits_kali_linux_mcp_server"
  candidates = [
    os.path.join(_HERE, folder_name),
    os.path.join(os.path.dirname(_HERE), folder_name),
    os.path.join(os.path.dirname(os.path.dirname(_HERE)), folder_name),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))), folder_name),
  ]
  for path in candidates:
    if os.path.isdir(path):
      return path

  searched = "\n  - ".join(candidates)
  raise FileNotFoundError(
    "Could not find 'wowbits_kali_linux_mcp_server'. Searched:\n"
    f"  - {searched}"
  )


SERVER_DIR = _find_server_dir()
action = sys.argv[1] if len(sys.argv) > 1 else "up"

if action == "stop":
  subprocess.run(["bash", "scripts/stop.sh"], cwd=SERVER_DIR, check=True)
else:
  subprocess.run(["bash", "scripts/build.sh"], cwd=SERVER_DIR, check=True)
  subprocess.run(["bash", "scripts/start.sh"], cwd=SERVER_DIR, check=True)

print("\nMCP server is starting up.")
print("Endpoint: http://localhost:8765/mcp")
print("Stop with: python3 mcps/kali_linux/run.py stop")
