# WowBits Kali Linux MCP Server

A fully containerised [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives WowBits agents access to Kali Linux security tools — nmap, gobuster, nikto, sqlmap, netexec, searchsploit, curl, wget, and a raw terminal.

---

## How it works

```
┌─────────────────────────────────┐
│           WowBits Agent         │
│  (or any MCP-compatible client) │
└──────────────┬──────────────────┘
               │  HTTP  (MCP protocol)
               │  http://localhost:8765/mcp
               ▼
┌─────────────────────────────────┐   Docker
│      mcp-server container       │   ──────
│   FastMCP (Python)              │   port 8765 exposed
│   Translates MCP tool calls     │
│   → REST requests               │
└──────────────┬──────────────────┘
               │  HTTP  (internal Docker network)
               │  http://kali-api:5000
               ▼
┌─────────────────────────────────┐   Docker
│       kali-api container        │   ──────
│   Flask REST API                │   port 5000 internal only
│   Runs inside Kali Linux OS     │
│   Executes real security tools  │
└─────────────────────────────────┘
```

**Two containers, one `docker-compose up`.**

| Container | Image | Role | Port |
|-----------|-------|------|------|
| `wowbits-kali-api` | `kalilinux/kali-rolling` | Executes security tools, exposes REST `/execute` | internal only |
| `wowbits-kali-mcp` | `python:3.12-slim` | Translates MCP calls to REST, speaks the MCP protocol | **8765** (public) |

Only port `8765` is ever exposed outside Docker. Port `5000` (the Kali tool executor) stays on the internal Docker network — it is never reachable from outside.

---

## Quick start (local / dev)

### Prerequisites
- Docker + Docker Compose
- No Python install required on the host — everything runs in containers

### 1. Clone and start

```bash
git clone <repo>
cd wowbits_kali_linux_mcp_server

docker-compose up -d --build
```

That's it. Two containers start:
- `wowbits-kali-api` — Kali Linux tool executor (internal)
- `wowbits-kali-mcp` — MCP HTTP server at **http://localhost:8765/mcp**

Check health:
```bash
docker-compose ps
curl http://localhost:8765/mcp   # should return MCP server info
```

### 2. Connect wowbits

In your wowbits kit, the config is already set (`mcps/kali_linux/wowbits_mcp.yaml`):

```yaml
kind: mcp_config
config:
  name: kali_linux
  url: http://localhost:8765/mcp
  config:
    transport_mode: http
    timeout: 300
```

wowbits reads this URL and connects — no paths, no subprocess spawning.

### 3. Stop

```bash
docker-compose down
```

Or via the convenience launcher:
```bash
python3 mcps/kali_linux/run.py stop
```

---

## Deploying to a server (production)

1. Copy the `wowbits_kali_linux_mcp_server/` folder to your server
2. Run `docker-compose up -d --build`
3. Update the wowbits config URL to point to your server:

```yaml
# mcps/kali_linux/wowbits_mcp.yaml
url: https://your-server.com:8765/mcp
```

That's the **only change** between local and hosted. The rest of the config is identical.

### Recommended: put Nginx in front

```nginx
location /mcp/kali {
    proxy_pass http://localhost:8765/mcp;
}
```

Then the URL becomes `https://your-server.com/mcp/kali` — no port needed.

### Security checklist before going public

- [ ] Set `ENFORCE_ALLOWLIST=true` in `docker-compose.yml` (restricts which commands can run)
- [ ] Add authentication (API key header, mTLS, or put behind VPN)
- [ ] Only expose port 8765 — never 5000
- [ ] Run on a dedicated server, not your dev machine

---

## Available MCP tools

| Tool | Function | Description |
|------|----------|-------------|
| Terminal | `run_terminal_command` | Run any shell command inside Kali |
| Nmap | `nmap_scan` | Network discovery and port scanning |
| Netexec | `nxc_smb`, `nxc_run` | SMB/AD enumeration |
| Gobuster | `gobuster_dir`, `gobuster_dns`, `gobuster_vhost` | Directory, DNS, vhost fuzzing |
| Nikto | `nikto_scan` | Web server vulnerability scanner |
| SQLMap | `sqlmap_test` | SQL injection detection |
| curl | `curl_request` | HTTP requests from within Kali |
| wget | `wget_download` | File downloads |
| Searchsploit | `searchsploit_query` | Search the local ExploitDB database |

---

## Project structure

```
wowbits_kali_linux_mcp_server/
├── Dockerfile          # Kali Linux image (kali-api container)
├── Dockerfile.mcp      # Python slim image (mcp-server container)
├── docker-compose.yml  # Starts both containers together
├── requirements.txt    # Host-side deps (only needed for non-Docker dev)
│
├── kali_api_server/    # Runs INSIDE the Kali container
│   ├── server.py       # Flask REST API  →  GET /health, POST /execute
│   └── executor.py     # subprocess wrapper, allowlist enforcement
│
├── mcp_server/         # Runs INSIDE the mcp-server container
│   ├── server.py       # FastMCP entry point, HTTP transport on :8765
│   ├── kali_client.py  # HTTP client → calls kali-api:5000/execute
│   └── tools/          # One file per MCP tool
│       ├── nmap.py
│       ├── gobuster.py
│       ├── nikto.py
│       ├── sqlmap.py
│       ├── nxc.py
│       ├── searchsploit.py
│       ├── curl.py
│       ├── wget.py
│       └── terminal.py
│
└── scripts/
    ├── build.sh
    ├── start.sh
    └── stop.sh
```

---

## Comparison with playwright MCP

| | Playwright MCP | Kali Linux MCP |
|--|--|--|
| Start command | `npx @playwright/mcp@latest` | `docker-compose up -d` |
| Transport | HTTP | HTTP |
| wowbits config | `url: http://localhost:8931` | `url: http://localhost:8765/mcp` |
| Host deps | Node.js / npm | Docker |
| Hosted | N/A (browser, local only) | Any Docker host, change URL only |

---

## Environment variables

### kali-api container

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Flask listen port |
| `HOST` | `0.0.0.0` | Flask bind address |
| `ENFORCE_ALLOWLIST` | `false` | Restrict to pre-approved commands |
| `LOG_LEVEL` | `INFO` | Python logging level |

### mcp-server container

| Variable | Default | Description |
|----------|---------|-------------|
| `KALI_API_URL` | `http://kali-api:5000` | URL of the kali-api container |
| `MCP_HOST` | `0.0.0.0` | MCP server bind address |
| `MCP_PORT` | `8765` | MCP server listen port |
| `LOG_LEVEL` | `INFO` | Python logging level |
