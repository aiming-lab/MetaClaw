# @metaclaw/memory — OpenClaw Plugin

Self-evolving local-first memory for OpenClaw. No cloud required.

## Features

- **6 structured memory types**: episodic, semantic, preference, project_state, working_summary, procedural_observation
- **4 retrieval modes**: keyword, embedding, hybrid, auto
- **Self-evolving policy**: candidate → replay → promotion pipeline
- **Local consolidation**: deduplication, merging, decay — all on-device
- **FTS5 + vector hybrid search**: fast keyword matching with optional semantic embeddings
- **Auto-recall & auto-capture**: transparent memory injection and extraction
- **Self-upgrade worker**: background maintenance and policy optimization
- **Memory slot compatible**: plugs into OpenClaw's `plugins.slots.memory` system

## Architecture

```
┌──────────────────────┐         localhost:19823        ┌──────────────────────┐
│   OpenClaw Gateway   │  ←── HTTP (fetch) ──────────→  │  MetaClaw Sidecar    │
│  ┌────────────────┐  │                                │  (FastAPI + uvicorn) │
│  │ TS Plugin      │──│── /retrieve, /ingest ────────→ │  MemoryManager       │
│  │  • auto-recall │  │── /search, /store ───────────→ │  MemoryStore         │
│  │  • auto-capture│  │── /health, /stats ───────────→ │  UpgradeWorker       │
│  │  • AI tools    │  │── /forget, /consolidate ─────→ │  (background)        │
│  │  • CLI cmds    │  │── /upgrade/* ────────────────→ │        ↕ SQLite+FTS5 │
│  └────────────────┘  │                                └──────────────────────┘
└──────────────────────┘
```

The TypeScript plugin communicates with a Python sidecar process via localhost HTTP.
The sidecar wraps the full MetaClaw Memory system (MemoryManager, MemoryStore, UpgradeWorker)
and keeps the SQLite database connection, embedder, and caches warm.

## Installation

```bash
# 1. Install the plugin
openclaw plugins install @metaclaw/memory

# 2. Set up the Python sidecar (creates venv + installs dependencies)
openclaw metaclaw setup

# 3. Verify
openclaw metaclaw status
```

### Requirements

- Node.js >= 18
- Python >= 3.10
- OpenClaw (latest)

## Configuration

Add to your `openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "metaclaw-memory": {
        "enabled": true,
        "config": {
          "autoRecall": true,
          "autoCapture": true,
          "sidecarPort": 19823,
          "scope": "default",
          "retrievalMode": "hybrid",
          "maxInjectedTokens": 800,
          "maxInjectedUnits": 6,
          "memoryDir": "~/.metaclaw/memory",
          "autoUpgradeEnabled": false,
          "pythonPath": "python3"
        }
      }
    },
    "slots": {
      "memory": "metaclaw-memory"
    }
  }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `autoRecall` | `true` | Inject relevant memories into every prompt automatically |
| `autoCapture` | `true` | Extract memories from completed sessions automatically |
| `sidecarPort` | `19823` | Port for the Python sidecar HTTP server |
| `scope` | `"default"` | Memory scope identifier |
| `retrievalMode` | `"hybrid"` | `"keyword"`, `"embedding"`, or `"hybrid"` |
| `maxInjectedTokens` | `800` | Token budget for injected memory context |
| `maxInjectedUnits` | `6` | Max memory units to inject per prompt |
| `memoryDir` | `"~/.metaclaw/memory"` | SQLite database location |
| `autoUpgradeEnabled` | `false` | Enable background self-upgrade worker |
| `pythonPath` | `"python3"` | Python interpreter path |
| `debug` | `false` | Enable verbose debug logging |

## How It Works

### Auto-Recall (every prompt)

```
User message → before_agent_start hook
  → POST /retrieve {task_description}
  → Sidecar: retrieve_for_prompt() + render_for_prompt()
  → Plugin: returns { prependContext: rendered_markdown }
  → LLM sees: [memory context] + [user message]
```

### Auto-Capture (session end)

```
Session ends → agent_end hook
  → Plugin extracts turns from event.messages
  → POST /ingest {session_id, turns}
  → Sidecar: ingest_session_turns() → consolidate()
  → Memories extracted & stored in SQLite+FTS5
```

## AI Tools

The plugin registers 4 tools that the LLM can call directly:

| Tool | Description |
|------|-------------|
| `metaclaw_memory_search` | Search long-term memories by keyword or semantic query |
| `metaclaw_memory_store` | Store a new memory explicitly |
| `metaclaw_memory_forget` | Archive a specific memory by ID |
| `metaclaw_memory_status` | Get memory system health and statistics |

## Slash Commands

| Command | Description |
|---------|-------------|
| `/remember <text>` | Save information to long-term memory |
| `/recall <query>` | Search memories by query |
| `/memory-status` | Show memory system health |

## CLI Commands

```bash
openclaw metaclaw setup      # Create venv, install deps
openclaw metaclaw status     # Show health and statistics
openclaw metaclaw search Q   # Search memories by query
openclaw metaclaw wipe       # Delete all memories (with --yes)
openclaw metaclaw upgrade    # Trigger self-upgrade cycle
```

## Sidecar API

The Python sidecar exposes these HTTP endpoints on `localhost:19823`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status, memory count, scope |
| POST | `/retrieve` | Retrieve & render memories for a task |
| POST | `/ingest` | Ingest session turns into memory |
| POST | `/search` | Search memories with scoring |
| POST | `/store` | Store a memory explicitly |
| POST | `/forget` | Archive a memory by ID |
| GET | `/stats` | Detailed scope statistics |
| POST | `/consolidate` | Run dedup/merge/decay |
| GET | `/upgrade/status` | Self-upgrade worker state |
| POST | `/upgrade/trigger` | Trigger upgrade cycle |

### Running the sidecar standalone

```bash
python -m metaclaw_memory_sidecar --port 19823 --memory-dir ~/.metaclaw/memory
curl http://127.0.0.1:19823/health
```

## Comparison with Other Memory Plugins

| Feature | memory-core | Supermemory | MemOS Cloud | **MetaClaw** |
|---------|-------------|-------------|-------------|--------------|
| Self-hosting | built-in | no | no | **fully local** |
| Cloud dependency | none | required | required | **none** |
| Self-evolving policy | no | no | no | **yes** |
| Retrieval modes | FTS only | semantic | vector | **4 modes** |
| Memory types | generic | 2 | generic | **6 structured** |
| Consolidation | none | cloud-side | none | **local** |
| Self-upgrade | no | no | no | **yes** |
| Diagnostics | basic | basic | none | **health/forecast** |

## Development

```bash
# Build TypeScript
npm run build

# Watch mode
npm run dev

# Install sidecar in dev mode
cd sidecar && pip install -e ../../ && pip install -e .
```

## Publishing

```bash
# Build and publish to npm
npm run build
npm publish --access public

# Users install with:
openclaw plugins install @metaclaw/memory
```

## License

MIT
