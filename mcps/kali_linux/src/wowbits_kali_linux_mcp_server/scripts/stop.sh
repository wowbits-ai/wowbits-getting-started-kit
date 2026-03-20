#!/usr/bin/env bash
# Stop and remove the Kali MCP container
set -euo pipefail
cd "$(dirname "$0")/.."
echo "==> Stopping Kali MCP container..."
docker rm -f wowbits-kali-mcp || true
echo "==> Done."
