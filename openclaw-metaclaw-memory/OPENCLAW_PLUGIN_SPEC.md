# MetaClaw Memory — OpenClaw Plugin Specification

> This document is written for OpenClaw. It explains what this plugin is, how it
> integrates with the OpenClaw plugin system, and how to install, configure, and
> test it from scratch.

---

## 1. What This Plugin Does

MetaClaw Memory is a **local-first, self-evolving long-term memory system** that
plugs into OpenClaw's `memory` slot. It replaces the built-in `memory-core` with
a richer memory backend that runs entirely on your machine — no cloud APIs, no
external accounts.

**Core capabilities:**

- **6 structured memory types** — episodic, semantic, preference, project_state,
  working_summary, procedural_observation (vs. memory-core's generic text chunks)
- **Hybrid retrieval** — keyword (FTS5), embedding (vector), or hybrid mode
- **Auto-recall** — injects relevant memories into every prompt via
  `before_prompt_build` hook
- **Auto-capture** — extracts memories from completed sessions via `agent_end`
  hook
- **Local consolidation** — deduplication, merging, and decay happen on-device
- **Self-evolving policy** — candidate → replay → promotion pipeline optimizes
  retrieval strategy over time

**What it registers:**

| Surface | Items |
|---------|-------|
| `kind` | `"memory"` (occupies `plugins.slots.memory`) |
| Lifecycle hooks | `before_prompt_build`, `agent_end` |
| AI tools | `metaclaw_memory_search`, `metaclaw_memory_store`, `metaclaw_memory_forget`, `metaclaw_memory_status` |
| Slash commands | `/remember`, `/recall`, `/memory-status` |
| CLI commands | `openclaw metaclaw setup\|status\|search\|wipe\|upgrade` |
| Background service | `metaclaw-memory` (manages Python sidecar process) |

---

## 2. Architecture

```
┌──────────────────────────┐       localhost:19823       ┌──────────────────────────┐
│     OpenClaw Gateway     │  ←── HTTP (fetch) ───────→  │   MetaClaw Sidecar       │
│                          │                             │   (FastAPI + uvicorn)    │
│  ┌────────────────────┐  │                             │                          │
│  │  TypeScript Plugin  │  │   POST /retrieve ────────→ │  MemoryManager           │
│  │                    │  │   POST /ingest ──────────→ │    .retrieve_for_prompt() │
│  │  • before_prompt_  │  │   POST /search ──────────→ │    .ingest_session_turns()│
│  │    build hook      │  │   POST /store ───────────→ │    .search_memories()     │
│  │  • agent_end hook  │  │   POST /forget ──────────→ │                          │
│  │  • 4 AI tools      │  │   GET  /health ──────────→ │  MemoryStore (SQLite+FTS5)│
│  │  • 3 slash cmds    │  │   GET  /stats ───────────→ │                          │
│  │  • CLI commands    │  │   POST /consolidate ─────→ │  UpgradeWorker           │
│  └────────────────────┘  │   GET  /upgrade/status ──→ │    (background asyncio)  │
│                          │   POST /upgrade/trigger ──→ │                          │
└──────────────────────────┘                             └──────────────────────────┘
```

The plugin is split into two processes:

1. **TypeScript plugin** (runs inside OpenClaw Gateway) — registers hooks, tools,
   commands via the OpenClaw Plugin API. Communicates with the sidecar over HTTP.
2. **Python sidecar** (spawned by the plugin as a managed service) — wraps the
   full MetaClaw memory subsystem (MemoryManager, MemoryStore, UpgradeWorker)
   behind a FastAPI server on `localhost:19823`.

The sidecar keeps the SQLite database connection, FTS5 index, embedder, and
caches warm for the lifetime of the Gateway process.

---

## 3. Plugin Entry Point

**File:** `dist/index.js` (compiled from `src/index.ts`)

```typescript
export default {
  id: "metaclaw-memory",
  name: "MetaClaw Memory",
  kind: "memory",
  configSchema,          // TypeBox schema, mirrors openclaw.plugin.json
  register(api) { ... }  // registers service, hooks, tools, commands
}
```

The `register()` function:

1. Parses `api.pluginConfig` into a typed config object
2. Calls `api.registerService()` to manage the Python sidecar lifecycle
3. Registers `before_prompt_build` hook for auto-recall
4. Registers `agent_end` hook for auto-capture
5. Registers 4 AI tools with TypeBox parameter schemas
6. Registers 3 slash commands via `api.registerCommand()`
7. Registers CLI command group via `api.registerCli()` under `openclaw metaclaw`

---

## 4. File Structure

```
openclaw-metaclaw-memory/
├── openclaw.plugin.json           # Plugin manifest (id, kind, configSchema, uiHints)
├── package.json                   # npm package with openclaw.extensions field
├── tsconfig.json
├── src/
│   ├── index.ts                   # Default export: { id, kind, register(api) }
│   ├── config-schema.ts           # TypeBox config schema
│   ├── types.ts                   # PluginConfig interface + parseConfig()
│   ├── client.ts                  # Typed HTTP client for sidecar API
│   ├── sidecar.ts                 # SidecarManager: spawn/health-poll/kill Python
│   ├── hooks/
│   │   ├── auto-recall.ts         # before_prompt_build → POST /retrieve → prependContext
│   │   └── auto-capture.ts        # agent_end → POST /ingest
│   ├── tools/
│   │   ├── memory-search.ts       # metaclaw_memory_search tool
│   │   ├── memory-store.ts        # metaclaw_memory_store tool
│   │   ├── memory-forget.ts       # metaclaw_memory_forget tool
│   │   └── memory-status.ts       # metaclaw_memory_status tool
│   └── commands/
│       ├── slash.ts               # /remember, /recall, /memory-status
│       └── cli.ts                 # openclaw metaclaw setup|status|search|wipe|upgrade
└── sidecar/
    ├── pyproject.toml             # pip-installable Python package
    └── metaclaw_memory_sidecar/
        ├── __init__.py
        ├── __main__.py            # python -m metaclaw_memory_sidecar (argparse + uvicorn)
        ├── config.py              # SidecarConfig dataclass + env var loading
        └── server.py              # FastAPI app factory, 10 endpoints
```

---

## 5. Installation

### Prerequisites

- Node.js >= 18
- Python >= 3.10
- OpenClaw (latest)

### Step 1 — Install the plugin

From npm (after publishing):

```bash
openclaw plugins install @metaclaw/memory
```

From a local directory (for development or testing):

```bash
cd /path/to/openclaw-metaclaw-memory
npm install && npm run build
openclaw plugins install -l .
```

Or from a tarball:

```bash
npm pack
openclaw plugins install ./metaclaw-memory-0.1.0.tgz
```

After installation, verify the plugin is discovered:

```bash
openclaw plugins list
# metaclaw-memory should appear
```

### Step 2 — Initialize the Python sidecar

```bash
openclaw metaclaw setup
```

This creates a Python virtual environment at
`~/.openclaw/plugins/@metaclaw/memory/.venv/` and installs `metaclaw-memory-sidecar`
along with its dependencies (FastAPI, uvicorn, metaclaw).

> **Note:** The `metaclaw` core Python package must be installable. If it is not
> yet on PyPI, install it locally first:
> `pip install -e /path/to/metaclaw-test`

### Step 3 — Configure

Add to `~/.openclaw/openclaw.json` (or project-level `openclaw.json`):

```json
{
  "plugins": {
    "entries": {
      "metaclaw-memory": {
        "enabled": true
      }
    },
    "slots": {
      "memory": "metaclaw-memory"
    }
  }
}
```

Setting `slots.memory` to `"metaclaw-memory"` tells OpenClaw to use this plugin
instead of the built-in `memory-core`. To keep both active, omit the `slots`
line and just enable via `entries`.

### Step 4 — Verify

```bash
openclaw metaclaw status
```

Expected output:

```
Memory System Status
  Status:   ok
  Scope:    default
  Memories: 0
```

---

## 6. Configuration Reference

All options live under `plugins.entries.metaclaw-memory.config`:

```json
{
  "autoRecall": true,
  "autoCapture": true,
  "sidecarPort": 19823,
  "scope": "default",
  "retrievalMode": "hybrid",
  "maxInjectedTokens": 800,
  "maxInjectedUnits": 6,
  "memoryDir": "~/.metaclaw/memory",
  "autoUpgradeEnabled": false,
  "pythonPath": "python3",
  "debug": false
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `autoRecall` | boolean | `true` | Inject relevant memories into every prompt via `before_prompt_build` |
| `autoCapture` | boolean | `true` | Extract and store memories from completed sessions via `agent_end` |
| `sidecarPort` | number | `19823` | Localhost port for the Python sidecar HTTP server |
| `scope` | string | `"default"` | Memory scope — use different values to isolate memories per project |
| `retrievalMode` | enum | `"hybrid"` | `"keyword"` (FTS5 only), `"embedding"` (vector only), or `"hybrid"` (both) |
| `maxInjectedTokens` | number | `800` | Token budget for memory context injected into each prompt |
| `maxInjectedUnits` | number | `6` | Maximum memory units to inject per prompt |
| `memoryDir` | string | `~/.metaclaw/memory` | Directory for the SQLite database and related files |
| `autoUpgradeEnabled` | boolean | `false` | Run the self-evolving upgrade worker as a background task |
| `pythonPath` | string | `"python3"` | Path to the Python interpreter (must be 3.10+) |
| `debug` | boolean | `false` | Enable verbose logging from the plugin |

---

## 7. How It Integrates with OpenClaw

### 7.1 Memory Injection (before_prompt_build)

When a user sends a message, the plugin's `before_prompt_build` hook fires:

1. Extracts the user's prompt text from the event
2. Sends `POST /retrieve { task_description: prompt }` to the sidecar
3. The sidecar calls `MemoryManager.retrieve_for_prompt()` which runs hybrid
   search (keyword + vector), scores and ranks results, and renders them as
   structured Markdown
4. The hook returns `{ prependContext: rendered_markdown }`
5. OpenClaw prepends this context to the user's message — the LLM sees relevant
   memories before the actual prompt

**Example injected context:**

```markdown
## Relevant Long-Term Memory

### [semantic] User preferences
The user prefers TypeScript for backend development and uses PostgreSQL.
Tags: typescript, database | Importance: 0.8

### [episodic] Previous discussion
Discussed API refactoring — decided on REST over GraphQL for simplicity.
Tags: api, architecture | Importance: 0.6
```

### 7.2 Memory Capture (agent_end)

When a session completes successfully, the `agent_end` hook fires:

1. Extracts user/assistant turn pairs from `event.messages`
2. Sends `POST /ingest { session_id, turns }` to the sidecar
3. The sidecar calls `MemoryManager.ingest_session_turns()` which:
   - Creates episodic memories for each conversation turn
   - Generates a working summary of the session
   - Runs consolidation (dedup, merge) against existing memories
4. New memories are stored in SQLite with FTS5 indexing

### 7.3 AI Tools

The 4 registered tools let the LLM explicitly interact with memory:

| Tool | Parameters | Returns |
|------|-----------|---------|
| `metaclaw_memory_search` | `query: string`, `limit?: number` | Formatted list of matching memories with scores |
| `metaclaw_memory_store` | `content: string`, `memory_type?: enum`, `tags?: string[]`, `importance?: number` | `memory_id` of stored memory |
| `metaclaw_memory_forget` | `memory_id: string` | Confirmation of archival |
| `metaclaw_memory_status` | (none) | Health status + statistics |

### 7.4 Sidecar Lifecycle

The Python sidecar is managed as an OpenClaw service via `api.registerService()`:

- **start**: Spawns `python -m metaclaw_memory_sidecar` with CLI args and env
  vars derived from plugin config. Polls `/health` every 250ms until ready (15s
  timeout).
- **stop**: Sends SIGTERM to the sidecar. Falls back to SIGKILL after 5 seconds.

The sidecar runs for the lifetime of the OpenClaw Gateway process.

---

## 8. Testing the Plugin

### 8.1 Test the sidecar standalone

Without OpenClaw, you can verify the Python sidecar works:

```bash
# Terminal 1 — start sidecar
cd /path/to/metaclaw-test
PYTHONPATH=openclaw-metaclaw-memory/sidecar:. \
  python -m metaclaw_memory_sidecar \
    --port 19823 \
    --memory-dir /tmp/metaclaw-test-memory \
    --scope test

# Terminal 2 — test endpoints
curl http://127.0.0.1:19823/health
# → {"status":"ok","memories":0,"scope":"test"}

curl -X POST http://127.0.0.1:19823/store \
  -H "Content-Type: application/json" \
  -d '{"content":"User prefers Python over Java","memory_type":"preference"}'
# → {"memory_id":"<uuid>"}

curl -X POST http://127.0.0.1:19823/search \
  -H "Content-Type: application/json" \
  -d '{"query":"programming language preference"}'
# → {"results":[{"unit":{...},"score":...}]}

curl -X POST http://127.0.0.1:19823/retrieve \
  -H "Content-Type: application/json" \
  -d '{"task_description":"Help me choose a tech stack"}'
# → {"rendered_prompt":"## Relevant Long-Term Memory\n...","unit_count":1}

curl -X POST http://127.0.0.1:19823/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"test-001",
    "turns":[
      {"prompt_text":"What database should I use?","response_text":"PostgreSQL is a solid choice."},
      {"prompt_text":"Why PostgreSQL?","response_text":"It has great JSON support and is well-maintained."}
    ]
  }'
# → {"added":3}  (2 episodic + 1 working_summary)

curl http://127.0.0.1:19823/stats
# → {"active":4,"total":4,...}

curl -X POST http://127.0.0.1:19823/consolidate \
  -H "Content-Type: application/json" \
  -d '{}'
# → {"superseded":0,"decayed":0,"reinforced":0}

curl -X POST http://127.0.0.1:19823/forget \
  -H "Content-Type: application/json" \
  -d '{"memory_id":"<uuid-from-store-above>"}'
# → {"ok":true}

curl http://127.0.0.1:19823/upgrade/status
# → {"state":"not_configured","detail":"no upgrade state file"}

curl -X POST http://127.0.0.1:19823/upgrade/trigger
# → {"triggered":true,"ran":false}

# Clean up
rm -rf /tmp/metaclaw-test-memory
```

All 10 endpoints have been verified to return HTTP 200 with correct responses.

### 8.2 Test within OpenClaw

After installing and configuring the plugin (see Section 5):

```bash
# 1. Check plugin is loaded
openclaw plugins list
# Should show: metaclaw-memory (memory) — enabled

# 2. Check sidecar is running
openclaw metaclaw status
# Should show: Status: ok, Memories: 0

# 3. Store a memory via slash command
# In an OpenClaw conversation, type:
/remember This project uses PostgreSQL 14 with Redis caching

# 4. Search for it
/recall database
# Should return the stored memory

# 5. Check status
/memory-status
# Should show: Status: ok | Memories: 1 | Scope: default

# 6. Have a conversation
# Ask OpenClaw something. After the session ends, auto-capture should
# extract and store memories from the conversation.

# 7. Start a new conversation about the same topic
# Auto-recall should inject relevant context from previous sessions.
# The LLM should reference prior knowledge without being explicitly told.

# 8. CLI search
openclaw metaclaw search "database"
# Should return results from stored memories
```

### 8.3 Test memory isolation

```bash
# Store memory in scope "project-a"
# In openclaw.json: "scope": "project-a"
/remember Project A uses MongoDB

# Switch scope to "project-b"
# In openclaw.json: "scope": "project-b"
/recall MongoDB
# Should return: No memories found (isolated by scope)
```

---

## 9. Sidecar API Reference

All endpoints are on `http://127.0.0.1:{sidecarPort}` (default 19823).

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| GET | `/health` | — | `{"status","memories","scope"}` | Health check |
| POST | `/retrieve` | `{"task_description","scope_id?"}` | `{"rendered_prompt","unit_count"}` | Retrieve and render memories for a prompt |
| POST | `/ingest` | `{"session_id","turns[]","scope_id?"}` | `{"added"}` | Ingest conversation turns into memory |
| POST | `/search` | `{"query","scope_id?","limit?"}` | `{"results":[{"unit","score","reason"}]}` | Search memories |
| POST | `/store` | `{"content","memory_type","scope_id?","tags[]","importance?"}` | `{"memory_id"}` | Store a memory |
| POST | `/forget` | `{"memory_id"}` | `{"ok":true}` | Archive a memory (soft delete) |
| GET | `/stats` | — | `{"active","total","types",...}` | Detailed statistics |
| POST | `/consolidate` | `{"scope_id?"}` | `{"superseded","decayed","reinforced"}` | Run dedup/merge/decay |
| GET | `/upgrade/status` | — | `{"state","detail",...}` | Upgrade worker state |
| POST | `/upgrade/trigger` | — | `{"triggered","ran"}` | Trigger self-upgrade cycle |

---

## 10. Differences from memory-core

| Aspect | memory-core | MetaClaw Memory |
|--------|------------|-----------------|
| Storage | Markdown files + SQLite chunks | SQLite + FTS5 (structured) |
| Memory types | Generic text chunks | 6 typed categories |
| Retrieval | FTS5 + sqlite-vec | Keyword, embedding, hybrid, or auto |
| Capture | File watching + indexing | Session-level turn extraction + summarization |
| Consolidation | None | Local dedup, merge, decay |
| Self-improvement | None | Candidate → replay → promotion policy pipeline |
| Cloud dependency | None | None |
| Runtime | In-process | Python sidecar (localhost HTTP) |
| Data location | Workspace `memory/` dir | Configurable (`~/.metaclaw/memory` default) |

---

## 11. Troubleshooting

**Sidecar won't start:**

```bash
# Check if port is in use
lsof -i :19823

# Start sidecar manually to see errors
PYTHONPATH=openclaw-metaclaw-memory/sidecar:. \
  python -m metaclaw_memory_sidecar --port 19823 --log-level debug
```

**Python dependency issues:**

```bash
# Verify Python version
python3 --version   # must be 3.10+

# Check that metaclaw is importable
python3 -c "from metaclaw.memory.manager import MemoryManager; print('OK')"

# Check that FastAPI is installed
python3 -c "import fastapi; print(fastapi.__version__)"
```

**No memories being injected:**

1. Confirm `autoRecall: true` in config
2. Confirm there are stored memories: `openclaw metaclaw status`
3. Enable `debug: true` and check logs for `metaclaw-memory:` messages

**Plugin not discovered:**

```bash
openclaw plugins doctor          # run diagnostics
openclaw plugins info metaclaw-memory  # check plugin details
```
