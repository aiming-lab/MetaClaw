# Phase 2 - Adaptive Memory Policy

Last updated: 2026-03-12
Status: Complete
Goal: Make memory behavior adapt safely through policy changes

## Scope

- policy schema
- telemetry collection
- scheduled recalibration
- rollback support

## Deliverables

- [x] policy model defined
- [x] policy persistence added
- [x] telemetry signals implemented
- [x] tuning job implemented
- [x] rollback mechanism implemented
- [x] policy inspection tooling implemented

## Exit Criteria

- policy can change without code edits
- policy changes are observable and reversible
- system remains stable under policy updates

## Current Implementation Notes

- `MemoryPolicyState` now exists as a persisted JSON policy artifact.
- Policy persistence now includes revision history and rollback support.
- `MemoryPolicyOptimizer` can propose bounded retrieval-mode and budget changes from memory-store statistics.
- `MemoryManager` now refreshes policy state after ingestion and can swap retrieval policy without code edits.
- Memory ingest and policy-update events now write to a telemetry log.
- Current optimizer logic is intentionally conservative and rule-based; this is the safe starting point for later adaptive work.
- CLI status now exposes active memory policy information, `metaclaw memory status` can inspect the current memory-policy state directly, and `metaclaw memory rollback` can restore an earlier policy revision.
- Memory configuration now includes explicit auto-upgrade worker controls so adaptive behavior can run as a managed background loop.
