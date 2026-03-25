# MetaClaw Memory Upgrade Plan

Last updated: 2026-03-13
Status: Phases 0-4 complete; all optional enhancements complete; production tooling finalized (529 tests)
Working branch: `memory-upgrade`
Project root: `/Users/jiaqi/Myprojects/metaclaw-test`

## Purpose

This document is the control plane for the MetaClaw memory upgrade.

It defines:

- what we are building
- why we are building it
- what not to do
- how the system should be designed
- how implementation should be phased
- how progress, findings, and lessons should be recorded over time

This file should be updated continuously during the project. It is not only a plan; it is also the running memory of the upgrade effort itself.

## Document Map

This file is the master document. Detailed work should be tracked in subdocuments.

Primary subdocuments:

- [Memory Master Index](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/README.md)
- [Memory Upgrade Handoff](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/HANDOFF.md)
- [Phase 0 - Planning and Research](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-0-planning.md)
- [Phase 1 - Base Memory System](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-1-base-memory.md)
- [Phase 2 - Adaptive Memory Policy](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-2-adaptive-policy.md)
- [Phase 3 - Replay Evaluation](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-3-replay-eval.md)
- [Phase 4 - Controlled Self-Upgrade](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-4-self-upgrade.md)
- [Reference Review - SimpleMem](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/research/simplemem-review.md)
- [Reference Review - MetaMem](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/research/metamem-review.md)
- [Decision Log](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/logs/decision-log.md)
- [Lessons Learned](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/logs/lessons-learned.md)

Usage rule:

- keep high-level scope, status, and roadmap in this master file
- put phase-specific implementation detail into the corresponding phase file
- put cross-cutting decisions into the decision log
- put unexpected constraints and learnings into lessons learned
- update this master file whenever subdocument status meaningfully changes

## Documentation Discipline

This project is large enough that execution quality depends on documentation discipline.

Required review and update loop:

- review the master plan before starting a substantial new implementation segment
- review the active phase document before changing phase scope or deliverables
- update the progress log after each meaningful implementation checkpoint
- update the decision log immediately after a real architecture or policy decision
- update lessons learned whenever a test failure, design mismatch, or operational constraint reveals something reusable
- update this master file whenever the current phase status or next-phase boundary changes

Working rule:

- do not leave code state ahead of documentation state for long
- treat the Markdown system as the project memory for the upgrade itself
- maintain the handoff document whenever ownership or execution context is expected to change

## Core Thesis

MetaClaw already has a strong `skill` loop:

- retrieve procedural guidance from `SKILL.md`
- inject skills into the system prompt
- summarize sessions into new skills
- optionally train via RL/OPD

What MetaClaw does not yet have is a strong `long-term memory` loop for:

- user identity and preferences
- project history
- cross-session factual continuity
- recurring task context
- durable working summaries

The goal is not to improve the model's raw reasoning ability. The goal is to improve long-term memory quality and continuity.

The more ambitious goal is to make memory a living subsystem:

- memory content evolves over time
- memory policies evolve over time
- retrieval and consolidation strategies adapt to the user's changing data distribution
- slow memory-system upgrades are evaluated safely before adoption

Current refinement focus (second-loop quality pass):

- extraction quality: pattern-based extraction from both prompt and response sides
- consolidation quality: near-duplicate merging, importance decay for old unused memories
- retrieval quality: IDF-weighted scoring for keyword and hybrid retrieval
- replay quality: grounding and coverage scores as new evaluation signals
- self-upgrade governance: weight-variant candidate diversity, enhanced scoring
- policy optimization: type-distribution-aware tuning with low-volume safety guard
- prompt rendering: type-grouped bullet-point format for token efficiency
- telemetry: retrieval quality signals for downstream optimization
- test coverage: 83 tests including scope isolation, store robustness, integration, and e2e

## What We Are Building

We will build a new memory subsystem inside MetaClaw with three layers.

### Layer 1: Base Memory

A production-oriented long-term memory layer for MetaClaw that:

- extracts memory from completed sessions
- stores structured memory units
- retrieves relevant memory for future turns
- injects relevant memory into prompts
- maintains memory quality through consolidation, deduplication, and retention rules

### Layer 2: Adaptive Memory Policy

A controlled self-adjustment layer that can change:

- retrieval weights
- top-k and token budgets
- consolidation frequency
- retention and decay thresholds
- memory type priorities
- routing logic across retrieval modes

This layer changes policy, not code.

### Layer 3: Safe Self-Upgrade

A candidate-evaluation layer inspired by MetaMem:

- generate candidate memory strategies or architectures offline
- evaluate them on replayed session data and memory benchmarks
- only promote candidates that outperform the current baseline

This layer does not directly mutate the production memory system in-place.

## Non-Goals

The following are explicitly out of scope for phase 1:

- automatic live code mutation of the memory subsystem
- turning the online proxy path into a heavy benchmark-style reflection pipeline
- replacing the skill system
- changing the RL trainer before the memory layer exists
- trying to fully reproduce MetaMem's research harness inside the request-serving path

## Why This Direction Fits MetaClaw

MetaClaw already has the right extension points:

- request interception in `metaclaw/api_server.py`
- session-end hooks already used by skill evolution
- asynchronous background work
- scheduler windows for slow updates
- configuration via `ConfigStore` and `MetaClawConfig`

This means the memory system can be added as a sibling to the skill system rather than as a separate external stack.

## Current System Assessment

### Existing strengths in MetaClaw

- strong prompt-time skill retrieval and injection
- session recording already exists
- session-end summarization already exists
- optional scheduler can defer slow work to idle windows
- system is already structured around proxy + background workers

### Existing gaps in MetaClaw

- no durable long-term fact memory for users/projects
- no explicit memory data model
- no memory retrieval budget or reranking pipeline
- no memory consolidation stage
- no adaptive memory policy loop
- no offline candidate evaluation loop for memory changes

## Reference Systems

### MetaMem

Local copy:

- `/Users/jiaqi/Myprojects/metaclaw-test/MetaMem`

What it contributes:

- strong research framing for self-evolving memory
- evidence that memory architecture can be benchmarked and iterated
- examples of multi-stage memory pipelines
- examples of candidate evaluation and evolution loops

What it does not directly provide:

- a production-ready online memory service for MetaClaw
- a low-latency request path
- a safe in-place upgrade mechanism for a live agent proxy

Decision:

- use MetaMem as the conceptual and evaluation reference for long-term self-upgrade
- do not directly embed its current harness into the online request path

### SimpleMem

Local copy:

- `/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem`

What it contributes:

- a strong practical base architecture
- semantic structured compression
- hybrid retrieval
- cross-session memory concepts
- session lifecycle and context injection ideas

Key files reviewed:

- [SimpleMem README](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/README.md)
- [SimpleMem Cross README](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/cross/README.md)
- [memory_builder.py](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/core/memory_builder.py)
- [hybrid_retriever.py](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/core/hybrid_retriever.py)
- [orchestrator.py](/Users/jiaqi/Myprojects/metaclaw-test/SimpleMem/cross/orchestrator.py)

Decision:

- use SimpleMem as the main engineering base for phase 1 design inspiration
- port concepts, not code wholesale
- keep MetaClaw-native interfaces and lifecycle

## Design Principles

1. Composition over replacement

The memory system must extend MetaClaw, not fight its architecture.

2. Fast path vs slow path separation

The online path must stay lightweight. Heavy consolidation and adaptation belong in background tasks or scheduler windows.

3. Facts and skills are different objects

Skills are procedural instructions. Memory is factual, episodic, or preference-oriented context. They should be stored and injected separately.

4. Controlled adaptivity before self-modification

The system should first learn to tune parameters and strategies inside a bounded design space before any architecture evolution is attempted.

5. Every upgrade needs feedback

No adaptive or self-upgrading mechanism should be introduced without explicit evaluation signals.

6. Provenance matters

Every memory unit should preserve traceability back to source session and turn ranges.

7. Memory quality over memory quantity

Aggressive storage without consolidation will degrade retrieval quality and pollute prompts.

## Proposed Architecture

### New modules to add

Planned new MetaClaw modules:

- `metaclaw/memory_manager.py`
- `metaclaw/memory_store.py`
- `metaclaw/memory_models.py`
- `metaclaw/memory_retriever.py`
- `metaclaw/memory_consolidator.py`
- `metaclaw/memory_policy.py`
- `metaclaw/memory_metrics.py`
- `metaclaw/memory_replay.py`

Possible later modules:

- `metaclaw/memory_optimizer.py`
- `metaclaw/memory_candidate_runner.py`

### Main responsibilities

#### `MemoryManager`

Top-level facade for:

- ingesting session data
- retrieving relevant memory
- writing memory units
- running consolidation jobs
- exposing metrics and status

#### `MemoryStore`

Persistent storage for:

- memory units
- memory embeddings
- access statistics
- provenance
- retention and consolidation metadata
- policy snapshots

Initial storage recommendation:

- JSONL or SQLite for durable metadata
- optional embeddings sidecar
- avoid introducing a heavy external dependency in phase 1 unless clearly needed

#### `MemoryRetriever`

Retrieval pipeline for:

- semantic search
- keyword search
- structured filtering
- recency / importance prior
- reranking
- token-budgeted selection

#### `MemoryConsolidator`

Background write-side processing for:

- session summarization into memory units
- deduplication
- merge and supersede operations
- importance scoring
- decay / archival
- working-summary refresh

#### `MemoryPolicy`

Defines adaptive decisions such as:

- per-memory-type top-k
- max injected memory token budget
- retrieval mode weights
- session-end extraction mode
- consolidation frequency
- retention thresholds
- escalation from raw memory to summary memory

## Memory Data Model

Phase 1 target schema for a memory unit:

- `memory_id`
- `tenant_id`
- `project_id`
- `user_id` or `agent_identity_scope`
- `type`
- `content`
- `summary`
- `source_session_id`
- `source_turn_range`
- `created_at`
- `updated_at`
- `time_range`
- `entities`
- `topics`
- `importance`
- `confidence`
- `last_accessed_at`
- `access_count`
- `reinforcement_score`
- `status`
- `supersedes`
- `superseded_by`
- `embedding`

### Memory types

Initial memory taxonomy:

- `episodic`
- `semantic`
- `preference`
- `project_state`
- `working_summary`
- `procedural_observation`

Notes:

- `procedural_observation` is still not the same as a skill
- some procedural observations may later be converted into skills, but they should not be collapsed together initially

## Prompt Injection Design

Prompt injection should become a two-block structure:

1. `Relevant Long-Term Memory`
2. `Active Skills`

This should replace the current single-source skill-only augmentation model.

### Injection rules

- memory injection must be token-budgeted
- memory injection must be relevant to the current task
- long-term memory and recent working summary should be merged carefully
- facts should be written as factual context, not directives
- skills remain directive instructions

### Injection point

Planned integration point:

- extend the logic near `_inject_skills()` in [api_server.py](/Users/jiaqi/Myprojects/metaclaw-test/metaclaw/api_server.py)
- likely introduce `_inject_memory_and_skills()` or a staged injection flow

## Online vs Offline Work Split

### Fast path

Must stay low-latency:

- lightweight query analysis
- retrieval across prebuilt indices
- rerank
- prompt injection
- simple access-stat updates

### Slow path

May run async or during idle windows:

- memory extraction from session
- memory consolidation
- summary refresh
- reindexing
- policy adjustment
- candidate evaluation

## Adaptive Memory: The Living-System Layer

The living-system concept should first be implemented as adaptive policy, not code mutation.

### What can adapt safely

- top-k per memory type
- semantic vs keyword vs structured retrieval weights
- recency prior strength
- prompt token budget for memory
- promotion threshold from episodic to semantic memory
- consolidation cadence
- decay thresholds
- whether reflection-style secondary retrieval should run for certain task classes

### What should not adapt automatically at first

- public interfaces
- persistence schema
- code structure
- prompt formats used for safety-critical instruction handling
- anything that can break the online proxy path without replay validation

## Self-Upgrade Strategy

Long-term, memory should be able to improve itself, but through a gated pipeline.

### Safe self-upgrade loop

1. Production system collects session and memory telemetry.
2. Replay dataset is built from real historical usage.
3. Candidate policies or candidate memory pipelines are generated offline.
4. Candidates are evaluated against baseline.
5. Only better candidates are promoted.

This is how MetaMem's evolution idea should be translated into MetaClaw.

### Candidate types

Initial candidate space should be limited to:

- retrieval weight presets
- reranking strategies
- memory-type routing strategies
- consolidation thresholds
- prompt rendering formats for memory blocks

Later candidate space may include:

- alternative extraction prompts
- alternative memory schemas
- alternative multi-stage consolidation logic

## Evaluation Framework

Without evaluation, adaptive memory will drift.

### Phase 1 evaluation signals

- memory retrieval hit rate
- memory injection token count
- retrieval latency
- access frequency per memory type
- duplicate / superseded rate
- memory growth rate

### Phase 2 evaluation signals

- estimated usefulness of injected memory
- user correction rate after memory-backed answers
- contradiction rate
- repeated-question resolution rate
- project continuity quality
- PRM score lift with vs without memory injection

### Phase 3 evaluation signals

- replay benchmark score
- candidate policy win rate vs baseline
- per-task-class improvements
- token-efficiency improvements

## Implementation Roadmap

### Phase 0: Planning and Design

Goal:

- complete architecture, interfaces, storage strategy, and phased execution plan

Deliverables:

- this document
- design decisions and open questions
- reference analysis of MetaMem and SimpleMem

Status:

- Phase 0 complete
- Phase 1 complete
- Phase 2 complete
- Phase 3 complete
- Phase 4 complete

### Phase 1: Minimum Viable Memory

Goal:

- add a MetaClaw-native long-term memory layer with stable retrieval and prompt injection

Scope:

- memory data model
- memory persistence
- session-end extraction
- retrieval before prompt send
- token-budgeted injection
- basic metrics

Not in scope:

- adaptive policy optimization
- self-upgrade

Exit criteria:

- system can persist long-term memory across sessions
- retrieved memory is injected separately from skills
- no severe latency regression in the main request path

### Phase 2: Adaptive Memory Policy

Goal:

- make retrieval and consolidation behavior adapt to observed usage

Scope:

- policy object and policy snapshots
- online telemetry
- scheduled policy recalibration
- bounded search over retrieval and consolidation parameters

Exit criteria:

- policy updates occur without code changes
- policy changes are logged and reversible
- measurable improvements or at least safe stability

### Phase 3: Offline Candidate Evaluation

Goal:

- make memory evolution evidence-driven

Scope:

- session replay dataset
- candidate runner
- baseline vs candidate comparison
- promotion criteria

Exit criteria:

- memory strategy changes can be validated offline
- production upgrades are gated by replay wins

### Phase 4: Controlled Self-Upgrade

Goal:

- allow the memory subsystem to evolve within a safe promotion framework

Scope:

- candidate generation
- bounded architecture/policy search
- automated reporting
- human-review optional promotion flow

Exit criteria:

- memory can self-improve through candidate evaluation without destabilizing the live system

## Detailed Task Breakdown

### Phase 0 tasks

- [x] Create working branch `memory-upgrade`
- [x] Clone and inspect `MetaMem`
- [x] Clone and inspect `SimpleMem`
- [ ] Finalize Memory system planning document
- [ ] Confirm storage choice for phase 1
- [ ] Confirm initial memory taxonomy
- [ ] Confirm prompt injection format
- [ ] Confirm phase 1 implementation boundaries

### Phase 1 tasks

- [ ] Add `memory` section to config model and config store
- [ ] Define `MemoryUnit` and related data classes
- [ ] Implement persistent `MemoryStore`
- [ ] Implement session-end memory extraction pipeline
- [ ] Implement `MemoryRetriever`
- [ ] Implement memory prompt renderer
- [ ] Integrate memory retrieval into `api_server.py`
- [ ] Integrate session-end write path into `api_server.py`
- [ ] Add basic metrics and logging
- [ ] Add tests for storage, retrieval, and injection

### Phase 2 tasks

- [ ] Define `MemoryPolicy` schema
- [ ] Persist policy snapshots
- [ ] Collect retrieval and usage telemetry
- [ ] Implement scheduled policy tuning job
- [ ] Add rollback mechanism for policy changes
- [ ] Add evaluation dashboards or CLI inspection path

### Phase 3 tasks

- [ ] Define replay data format
- [ ] Build session replay loader from existing records
- [ ] Add candidate strategy runner
- [ ] Add baseline vs candidate comparator
- [ ] Define promotion thresholds
- [ ] Add reports for candidate evaluation

### Phase 4 tasks

- [ ] Define bounded candidate search space
- [ ] Integrate offline candidate generation workflow
- [ ] Add human-review option for promotions
- [ ] Add automatic candidate archival and history
- [ ] Document failure and rollback paths

## SimpleMem Reading Tasks

These tasks are tracked explicitly because SimpleMem is part of the design input.

- [x] Review top-level README
- [x] Review cross-session architecture README
- [x] Review `core/memory_builder.py`
- [x] Review `core/hybrid_retriever.py`
- [x] Review `cross/orchestrator.py`
- [ ] Review `cross/context_injector.py`
- [ ] Review `cross/consolidation.py`
- [ ] Review `cross/session_manager.py`
- [ ] Review `cross/storage_sqlite.py`
- [ ] Review `cross/storage_lancedb.py`
- [ ] Extract directly reusable design ideas into this document

## MetaMem Reading Tasks

- [x] Review README
- [x] Review interface and evaluator
- [x] Review evolution harness
- [x] Review best generated memory system
- [ ] Extract replay-evaluation ideas for MetaClaw memory self-upgrade
- [ ] Define which MetaMem concepts belong in phase 3 versus phase 4

## Initial Design Decisions

### Decision 1

Memory and skills will remain separate subsystems.

Reason:

- skills are procedural guidance
- memory is factual and contextual
- merging them too early will reduce observability and make retrieval harder to debug

### Decision 2

The first adaptive layer will change policy, not code.

Reason:

- safer
- easier to evaluate
- aligns with current MetaClaw architecture
- still satisfies the living-system requirement in a meaningful way

### Decision 3

SimpleMem is the phase 1 engineering reference. MetaMem is the phase 3 and 4 evolution reference.

Reason:

- SimpleMem is closer to a practical base pipeline
- MetaMem is better as the conceptual source for controlled self-upgrade

### Decision 4

Memory extraction and consolidation should happen at session boundaries or idle windows, not inline on every turn.

Reason:

- protects latency
- fits existing MetaClaw scheduler model
- reduces instability in the main request path

## Open Questions

These questions must be resolved before or during phase 1.

- Should phase 1 storage be SQLite-first, JSONL-first, or hybrid?
- Should embeddings be optional behind a feature flag initially?
- How should user identity be scoped when MetaClaw is used in multiple environments?
- What is the initial token budget split between memory and skills?
- Should working-summary memory be regenerated every session or periodically?
- How should memory provenance be surfaced for debugging?
- What is the minimal safe replay benchmark for phase 3?

## Risks

### Risk 1: Prompt pollution

Too much injected memory will degrade model behavior.

Mitigation:

- strict token budget
- reranking
- separate memory and skills blocks

### Risk 2: Retrieval drift

Adaptive policy may worsen relevance.

Mitigation:

- bounded parameter space
- snapshot and rollback
- replay evaluation before promotion

### Risk 3: Memory bloat

Session-level extraction without consolidation will explode storage and hurt retrieval.

Mitigation:

- consolidation pipeline
- decay and supersede relations
- memory type promotion rules

### Risk 4: Engineering overreach

Trying to build self-evolving memory too early will stall delivery.

Mitigation:

- strict phase boundaries
- complete phase 1 before adaptive layers

### Risk 5: Conflating research goals with production goals

MetaMem-style evolution may not map directly to a stable online system.

Mitigation:

- keep online serving conservative
- keep research-style evolution offline

## Definition of Success

### Phase 1 success

- MetaClaw remembers cross-session user/project facts
- memory retrieval improves continuity without obvious instability
- request latency remains acceptable

### Phase 2 success

- memory policy adapts safely to usage patterns
- changes are observable and reversible

### Phase 3 success

- candidate memory strategies can be compared offline
- baseline system can be improved through replay-tested upgrades

### Phase 4 success

- memory behaves like a living subsystem with controlled self-improvement

## Working Notes

### 2026-03-12

- Initial assessment complete.
- MetaClaw currently has strong skill memory but weak long-term factual memory.
- MetaMem is best treated as an evolution and benchmark reference, not as a direct online subsystem.
- SimpleMem is the best phase 1 base reference.
- The right route is:
  - build base memory
  - add adaptive policy
  - add replay evaluation
  - then add controlled self-upgrade
- Documentation system split into master file plus phase, research, and log subdocuments.

## Update Protocol

Whenever work progresses, update this file with:

- task status changes
- decisions made
- implementation notes
- failures and lessons learned
- changes in scope
- benchmark or latency results

Recommended update rhythm:

- after each major reading pass
- after each implementation milestone
- after each test or replay-evaluation milestone
- immediately after discovering a design constraint or failure mode
