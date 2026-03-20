#!/usr/bin/env bash
# Start the Kali MCP container as a background service
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Starting Kali MCP container..."
docker rm -f wowbits-kali-mcp || true
docker run -d \
  --name wowbits-kali-mcp \
  --restart unless-stopped \
  -p 8765:8765 \
  -v "$(pwd)/data:/app/data" \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  wowbits-kali-mcp:latest

echo ""
echo "✅  Kali MCP server is running at http://localhost:8765/mcp"
echo ""
