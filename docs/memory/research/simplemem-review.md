# Reference Review - SimpleMem

Last updated: 2026-03-12
Status: Initial review complete
Reference root: `/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem`

## Why It Matters

SimpleMem is the main engineering reference for phase 1 because it already solves:

- semantic structured compression
- hybrid retrieval
- cross-session orchestration
- context injection
- memory consolidation

## Files Reviewed

- [README](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/README.md)
- [cross/README](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/cross/README.md)
- [core/memory_builder.py](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/core/memory_builder.py)
- [core/hybrid_retriever.py](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/core/hybrid_retriever.py)
- [cross/orchestrator.py](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/cross/orchestrator.py)

## Key Takeaways

- The strongest reusable concept is the separation between write-side compression and read-side retrieval.
- Cross-session memory should be attached to lifecycle hooks, not bolted on manually.
- Context injection should be token-budgeted and rendered explicitly.
- Consolidation is a first-class component, not an optional cleanup step.
- Composition over modification is the right integration style.

## Follow-up Reading

- [x] `cross/context_injector.py`
- [x] `cross/consolidation.py`
- [x] `cross/session_manager.py`
- [x] `cross/storage_sqlite.py`
- [ ] `cross/storage_lancedb.py`

## Directly Reusable Ideas for MetaClaw

- split fast retrieval path from slow consolidation path
- preserve provenance for memory entries
- make context injection explicit and budgeted
- centralize orchestration through a top-level memory facade
- start with relational storage and only add heavier vector infrastructure when truly needed
