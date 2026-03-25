# Quick Start — MetaClaw Memory for OpenClaw

Get running in 3 minutes.

## Install

```bash
# From npm (after publish)
openclaw plugins install @metaclaw/memory

# Or from local directory (dev)
openclaw plugins install -l /path/to/openclaw-metaclaw-memory
```

## Configure

Add to `~/.openclaw/openclaw.json`:

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

## Initialize

```bash
openclaw metaclaw setup    # creates Python venv + installs sidecar
openclaw metaclaw status   # verify: should show "Status: ok"
```

## Use

Everything works automatically once configured:

- **Auto-recall**: relevant memories are injected into every prompt
- **Auto-capture**: memories are extracted from completed sessions

Manual control:

```
/remember project uses PostgreSQL 14    # save a memory
/recall database                        # search memories
/memory-status                          # check health
```

## That's it

The plugin handles everything else: sidecar lifecycle, memory consolidation,
deduplication, and decay — all locally, no cloud needed.

For full configuration options and troubleshooting, see [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md).
