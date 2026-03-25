# Phase 1 - Base Memory System

Last updated: 2026-03-12
Status: Complete
Goal: Add a stable MetaClaw-native long-term memory layer

## Scope

- memory data model
- persistence
- session-end extraction
- retrieval pipeline
- prompt injection
- basic metrics and tests

## Planned Modules

- `metaclaw/memory_models.py`
- `metaclaw/memory_store.py`
- `metaclaw/memory_manager.py`
- `metaclaw/memory_retriever.py`
- `metaclaw/memory_consolidator.py`
- `metaclaw/memory_policy.py`

## Deliverables

- [x] `memory` config added
- [x] memory model defined
- [x] store implemented
- [x] extraction pipeline implemented
- [x] retrieval pipeline implemented
- [x] prompt rendering implemented
- [x] `api_server.py` integrated
- [x] tests added
- [x] logging and metrics added

## Entry Conditions

- phase 0 decisions complete enough for implementation

## Exit Criteria

- cross-session memory persists and retrieves correctly
- request-serving latency remains acceptable
- memory injection works independently of skill injection
- basic observability exists

## Open Design Slots

- store backend
- embedding strategy
- extraction prompt strategy
- top-k and token-budget defaults

## Current Implementation Notes

- Phase 1 currently uses SQLite-backed storage via `MemoryStore`.
- Retrieval is keyword-first with room for later hybrid extension.
- Retrieval now supports `keyword`, lightweight `hybrid`, and optional `embedding` modes.
- Session-end write path now performs pattern-based factual extraction plus working-summary synthesis.
- Prompt injection now supports a separate `Relevant Long-Term Memory` block.
- Minimal consolidation is in place for exact duplicates and stale working summaries.
- Store-level stats now expose active-memory type breakdown and dominant-type summaries.
- Memory injection and session-end ingestion now emit lightweight operational logs for observability.
- Memory scope can now be passed explicitly per request/session instead of being locked to a single global default.
- Optional embeddings are currently implemented through a deterministic local hashing embedder so semantic retrieval can be exercised without introducing a heavy serving dependency.
- Scope derivation now supports explicit scope, user identity, workspace identity, and session-scoped fallback.

## Remaining Work Inside Phase 1

- [x] replace heuristic extraction with stronger factual extraction
- [x] add optional embedding retrieval path
- [x] add more precise scope and identity handling
- [x] add richer tests for injection and session-end ingestion
- [x] expose memory status and debugging surfaces through CLI or logs
