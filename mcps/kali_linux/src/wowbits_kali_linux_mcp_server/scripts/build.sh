#!/usr/bin/env bash
# Build the single Kali MCP Docker image
set -euo pipefail
cd "$(dirname "$0")/.."
echo "==> Building wowbits-kali-mcp Docker image..."
docker build -t wowbits-kali-mcp:latest .
echo "==> Build complete: wowbits-kali-mcp:latest"
