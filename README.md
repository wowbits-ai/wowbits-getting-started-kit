# WowBits Getting Started Kit

**Ship AI agents in minutes, not days.** This repo is your reference workspace: prebuilt agents, tools, and MCPs so you can run a real agent with one CLI and zero boilerplate.

---

## Why WowBits

Most agent frameworks make you wire SDKs, infra, and prompts by hand. WowBits gives you:

- **One flow:** YAML → create → run. No custom servers or glue code.
- **Config as code:** Agents live in `agent_studio/*.yaml`. Version them, review them, reuse them.
- **Tools your way:** Python functions in `functions/` or any MCP server. One connector (e.g. OpenAI), then focus on behavior.

**wowbits-cli** is the only binary you need. It manages functions, connectors, agents, and MCPs—and runs agents on [Google ADK](https://github.com/google/adk) (web UI or API) so you get a chat interface or an API out of the box.

---

## Who it’s for

- **Builders** who want a running agent in one sitting.
- **Teams** that want agent definitions in Git, not scattered in dashboards.
- **Anyone** tired of stitching LLM + tools + orchestration from scratch.

---

## Get started (under 5 minutes)

**Prereqs:** Python 3.8+, an LLM API key (e.g. OpenAI).

**1. Install the CLI**

```bash
pip install wowbits-cli
```

**2. Use this repo as your WowBits root**

```bash
export WOWBITS_ROOT_DIR="$(pwd)"   # or the path to this repo
```

Put that in `~/.zshrc` or `~/.bashrc`, or add `WOWBITS_ROOT_DIR=/path/to/wowbits-getting-started-kit` to a `.env` in this folder.

**3. Setup (once)**

```bash
wowbits setup
```

Pick **SQLite** when prompted. This creates `data/`, `agent_studio/`, `functions/`, `agent_runner/`, and the DB.

**4. Register tools and create the browser agent**

```bash
wowbits create function
wowbits create connector --provider openai    # paste your API key when asked
wowbits create agent browser_tool
```

**5. Run it**

```bash
wowbits run agent browser_tool
```

Open **http://localhost:5151** and ask the agent to do something in a browser (e.g. “Go to example.com and tell me the page title”).

---

## How WowBits works

| Idea | Meaning |
|------|--------|
| **Tool** | A single capability: a **Python function** (e.g. in `functions/`) or an **MCP server** (e.g. in `mcps/`). |
| **Skill** | An LLM + tools (and optionally sub-skills). Runs as one unit. Defined in YAML with `kind: wowbits_skill`. |
| **Agent** | The top-level runner: an LLM + one or more skills. Execution can be **LLM**, **sequential**, or **parallel**. Defined in YAML with `kind: wowbits_agent`. |

Pipeline: **YAML** in `agent_studio/` → `wowbits create agent` → stored in DB → `wowbits run agent` → ADK serves web UI or API. You never touch generated runner code unless you want to.

---

## wowbits-cli at a glance

| Action | Command |
|--------|--------|
| First-time setup | `wowbits setup [--root-dir PATH]` |
| List | `wowbits list functions` \| `connectors` \| `agents` |
| Register tools | `wowbits create function [--dir PATH]` |
| Add LLM/API | `wowbits create connector --provider openai` |
| Create/update agent | `wowbits create agent <name>` (uses `agent_studio/<name>.yaml`) |
| Register MCP | `wowbits create mcp <name>` (uses `mcps/<name>/config.yaml`) |
| Run agent | `wowbits run agent <name> [--mode web|api] [-p PORT]` |
| Run MCP server | `wowbits run mcp <name>` |
| Pull tools from GitHub | `wowbits pull functions --repo-url <url>` |

Full reference: [wowbits-cli](https://github.com/wowbits/wowbits-cli#readme).

---

## What’s in this kit

**Reference agents** (`agent_studio/`)

- **browser_tool** — Agent that drives a real browser (start session → run task → get result). Good for automation, scraping, or quick E2E flows. Uses the `browser_tool` Python function.
- **get_twitter_feeds** — Example agent shape; swap in your own tool implementation.

**Tools** (`functions/`)

- **browser_tool** — Browser automation with sessions: `start_session`, `run_task_and_wait`, `stop_session`, etc. [Details](functions/browser_tool.md).
- **serp_api** — Google search via SerpAPI. [Details](functions/serp_api.md).

Run `pip install -r functions/requirements.txt`. Put `OPENAI_API_KEY` (and `SERPAPI_API_KEY` if you use Serp) in `.env` or your environment.

**MCPs** (`mcps/`)

- **playwright** — Example MCP server. The CLI reads **config.yaml** from each MCP folder. The [playwright](mcps/playwright/) example has `wowbits.yaml`; copy it to `config.yaml` so `wowbits create mcp playwright` works.

---

## Run modes

- **Web (default):** `wowbits run agent browser_tool` → http://localhost:5151 (ADK chat UI).
- **API only:** `wowbits run agent browser_tool --mode api` (no UI, same port).
- Custom port: `wowbits run agent browser_tool -p 8080`.

---

## If something breaks

| Symptom | What to do |
|--------|------------|
| `WOWBITS_ROOT_DIR` not set | Run `wowbits setup` or set it (e.g. in `.env` or shell rc). |
| Agent create fails on “invalid kind” | Use `kind: wowbits_tool`, `kind: wowbits_skill`, `kind: wowbits_agent` in your YAML. |
| “Python function 'X' not found” | Run `wowbits create function` so `functions/` is scanned and registered. |
| Agent needs a model/API | Run `wowbits create connector --provider openai` (or the provider your agent uses). |
| MCP create fails | Add `mcps/<name>/config.yaml` with `kind: wowbits_mcp_config` and a `config` block (`name`, `url`, `config`). |

---

## Next steps

- **Tweak agents:** Edit `agent_studio/*.yaml`, then `wowbits create agent <name>` and `wowbits run agent <name>` again.
- **Tool docs:** [Browser tool](functions/browser_tool.md), [SERP API](functions/serp_api.md).
- **CLI repo:** [wowbits-cli](https://github.com/wowbits/wowbits-cli#readme).

---

*WowBits — from zero to a running agent in one flow.*
