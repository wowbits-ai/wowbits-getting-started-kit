import subprocess
import json
from pathlib import Path

# Load config
config_path = Path(__file__).resolve().parent / "config.json"
with open(config_path) as f:
    config = json.load(f)

port = config["server"]["port"]
host = config["server"]["host"]

# Verify the local clone exists
mcp_dir = Path(__file__).resolve().parent
repo_dir = mcp_dir / "memento-protocol"
entry_point = repo_dir / "src" / "index.js"

if not entry_point.exists():
    print(f"❌ Local memento-protocol clone not found at: {repo_dir}")
    print("   Run setup.py first to clone the repo:")
    print("   python setup.py")
    exit(1)

print(f"🚀 Starting Memento MCP server (local storage) via supergateway on {host}:{port}")
print(f"   Using: node src/index.js (local clone)")
print(f"   Repo:  {repo_dir}")
print(f"   Data:  {repo_dir / 'data'}")

# Use supergateway to bridge the local clone (STDIO) → SSE
subprocess.run(
    [
        "npx", "-y", "supergateway",
        "--stdio", f"node {entry_point}",
        "--port", str(port),
        "--host", host,
    ],
)
