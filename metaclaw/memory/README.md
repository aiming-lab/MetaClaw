# MetaClaw Memory Subsystem

A self-evolving long-term memory system with adaptive retrieval policy, replay-based evaluation, and bounded self-upgrade — all backed by SQLite + FTS5.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MemoryManager                                │
│  (facade: retrieval, rendering, session extraction, maintenance)    │
├────────┬───────────┬──────────────┬───────────────┬────────────────┤
│ Store  │ Retriever │ Consolidator │ PolicyOptimzr │   Embedder     │
│(SQLite)│ (search)  │  (cleanup)   │  (auto-tune)  │ (hash/sbert)  │
└───┬────┴─────┬─────┴──────┬───────┴───────┬───────┴────────────────┘
    │          │            │               │
    ▼          ▼            ▼               ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────────────────────┐
│ Models │ │ Policy │ │ Metrics  │ │   Self-Upgrade Pipeline   │
│ (data) │ │ (tune) │ │ (stats)  │ │ Candidate → Replay →     │
└────────┘ └────┬───┘ └──────────┘ │ Promotion → Orchestrator │
                │                   └──────────┬───────────────┘
                ▼                              ▼
         ┌──────────┐                  ┌───────────────┐
         │ PolicyStr│                  │ UpgradeWorker │
         │ (persist)│                  │ (background)  │
         └──────────┘                  └───────────────┘
```

## Module Reference

| Module | Key Exports | Purpose |
|--------|-------------|---------|
| `manager` | `MemoryManager` | Central facade — initialization, retrieval, rendering, extraction, maintenance |
| `store` | `MemoryStore` | SQLite + FTS5 persistence with corruption recovery and thread safety |
| `models` | `MemoryUnit`, `MemoryType`, `MemoryQuery`, `MemoryStatus` | Core data structures and enums |
| `policy` | `MemoryPolicy` | Retrieval behavior parameters (weights, budgets, mode) |
| `policy_store` | `MemoryPolicyStore`, `MemoryPolicyState` | JSON persistence with JSONL revision history |
| `policy_optimizer` | `MemoryPolicyOptimizer` | Bounded auto-tuning based on store state and telemetry |
| `retriever` | `MemoryRetriever` | Multi-mode search: keyword, embedding, hybrid, auto |
| `embeddings` | `HashingEmbedder`, `SentenceTransformerEmbedder`, `create_embedder` | Pluggable vector encoders |
| `consolidator` | `MemoryConsolidator` | Deduplication, near-duplicate merging, importance decay |
| `candidate` | `generate_policy_candidates` | Bounded candidate set generation for self-upgrade |
| `replay` | `MemoryReplayEvaluator`, `run_policy_candidate_replay` | Offline evaluation against historical turns |
| `promotion` | `MemoryPromotionCriteria`, `should_promote` | Safety-gated promotion decisions |
| `self_upgrade` | `MemorySelfUpgradeOrchestrator` | End-to-end upgrade pipeline with optional human review |
| `upgrade_worker` | `MemoryUpgradeWorker` | Async background loop for continuous self-improvement |
| `scope` | `derive_memory_scope` | Scope derivation from session/user/workspace context |
| `metrics` | `summarize_memory_store` | Aggregate store statistics |
| `telemetry` | `MemoryTelemetryStore` | Append-only event log for ingestion and policy changes |

## Key Advantages

### 1. Self-Evolving Retrieval Policy

The system does not rely on a fixed retrieval strategy. Instead, it continuously improves its own policy through a closed-loop pipeline:

- **Candidate generation** explores bounded policy variants (retrieval mode, budget, weights)
- **Replay evaluation** tests each candidate against real historical conversation turns
- **Promotion gating** enforces minimum improvement thresholds across multiple quality signals
- **Human review** can optionally gate any upgrade before activation

This means the memory system adapts to the actual usage patterns of each deployment without manual tuning.

### 2. Zero External Dependencies for Core Operation

The memory subsystem runs entirely on SQLite (with FTS5 for full-text search) and Python stdlib. No external vector database, no Redis, no Elasticsearch. The `HashingEmbedder` provides deterministic vector representations using SHA256 without any ML library. For deployments that want semantic search, the `SentenceTransformerEmbedder` adds sentence-transformers as an optional dependency.

### 3. Multi-Mode Retrieval with Automatic Selection

Four retrieval modes are available:

- **keyword** — FTS5 full-text search with BM25 scoring
- **embedding** — cosine similarity against stored vectors
- **hybrid** — IDF-weighted fusion of keyword + embedding results
- **auto** — dynamically selects the best mode based on query characteristics and store state

The `auto` mode analyzes query length, store density, and available embeddings to choose the optimal strategy per query.

### 4. Structured Memory Types

Six memory types capture different knowledge facets:

| Type | Use Case |
|------|----------|
| `EPISODIC` | Specific events and interactions |
| `SEMANTIC` | Facts, definitions, domain knowledge |
| `PREFERENCE` | User preferences and style choices |
| `PROJECT_STATE` | Current project context and status |
| `WORKING_SUMMARY` | Rolling compressed context |
| `PROCEDURAL_OBSERVATION` | Learned patterns, workflows, process notes |

Type-aware retrieval applies configurable boosts per type, and the policy optimizer adapts these boosts based on observed retrieval patterns.

### 5. Bounded Safety Model

Every parameter in the self-upgrade pipeline is bounded:

- Candidate generation produces a finite set (~8-12 variants per cycle)
- Policy weights have hard min/max constraints
- Promotion requires improvement across multiple independent signals
- Zero-retrieval increase is capped to prevent regression
- Minimum sample count prevents noisy upgrades
- Optional human-in-the-loop review queue

### 6. Comprehensive Diagnostics

Built-in operator tools:

- **Health check** — validates store integrity, policy consistency, retriever readiness
- **Action plan** — generates prioritized maintenance recommendations
- **Capacity forecast** — projects memory growth and storage needs
- **Feedback analysis** — detects patterns in user feedback signals
- **Store summary** — type distribution, density, activity metrics

## Self-Upgrade Flow

```
┌──────────────────┐
│  UpgradeWorker   │ ← runs on timer / respects window constraints
│  (background)    │
└────────┬─────────┘
         │ run_once()
         ▼
┌──────────────────┐
│ generate_policy_ │ → produces ~8-12 bounded policy variants
│ candidates()     │   (mode × units × tokens × weights)
└────────┬─────────┘
         │ for each candidate
         ▼
┌──────────────────┐
│ run_policy_      │ → evaluates against historical replay samples
│ candidate_replay │   computing overlap, specificity, focus,
│ ()               │   density, grounding, coverage scores
└────────┬─────────┘
         │ composite_score comparison
         ▼
┌──────────────────┐
│ should_promote() │ → checks delta thresholds across all signals
│                  │   enforces min samples, max regression
└────────┬─────────┘
         │ if promoted
         ▼
┌──────────────────┐
│ SelfUpgrade      │ → logs decision, writes new policy,
│ Orchestrator     │   optionally queues for human review
└────────┬─────────┘
         │ activate
         ▼
┌──────────────────┐
│ PolicyStore      │ → persists active policy JSON + revision log
└──────────────────┘
```

**Composite Score** combines six weighted signals:

- Query overlap (0.25) — relevance to the user's query
- Continuation overlap (0.15) — predictiveness of next-turn context
- Focus score (0.20) — retrieval precision
- Grounding score (0.15) — factual anchoring
- Coverage score (0.15) — breadth of relevant memory coverage
- Value density (0.10) — information density of retrieved results

A zero-retrieval penalty is applied when the candidate retrieves nothing for too many samples.

## Usage Guide

### Initialization

```python
from metaclaw.memory import MemoryManager

# From MetaClawConfig
manager = MemoryManager.from_config(config)

# Manual initialization
from metaclaw.memory import MemoryStore, MemoryPolicy
store = MemoryStore("/path/to/memory.db")
manager = MemoryManager(store=store)
```

### Storing Memories

```python
manager.ingest(
    content="The user prefers Python type hints in all code.",
    memory_type="preference",
    scope_id="user:alice",
    importance=0.8,
    tags=["coding-style", "python"],
)
```

### Retrieving Memories

```python
from metaclaw.memory import MemoryQuery

query = MemoryQuery(
    scope_id="user:alice",
    text="What coding conventions does the user follow?",
    top_k=5,
    max_tokens=800,
)
hits = manager.search_memories(query)
for hit in hits:
    print(f"[{hit['score']:.2f}] {hit['content'][:80]}...")
```

### Multi-Turn Context Extraction

```python
# During a conversation session
manager.extract_and_store(
    session_id="sess-123",
    scope_id="user:alice",
    messages=[
        {"role": "user", "content": "I need help with the auth module"},
        {"role": "assistant", "content": "Sure, I see the JWT handler..."},
    ],
)
```

### Running Maintenance

```python
# Consolidation (dedup, merge, decay)
report = manager.run_consolidation(scope_id="user:alice")

# Health check
health = manager.run_system_health_check(scope_id="user:alice")

# Action plan
plan = manager.generate_action_plan(scope_id="user:alice")
```

### Self-Upgrade (Programmatic)

```python
from metaclaw.memory import MemorySelfUpgradeOrchestrator

orchestrator = MemorySelfUpgradeOrchestrator(config=config)
decision = orchestrator.evaluate_candidate(
    replay_path="memory_data/replay/samples.jsonl",
    scope_id="user:alice",
)
print(f"Promoted: {decision.promoted}, Reason: {decision.reason}")
```

### Background Upgrade Worker

```python
from metaclaw.memory import MemoryUpgradeWorker

worker = MemoryUpgradeWorker(config=config)
# In an async context:
await worker.run()  # runs until stopped
# Or single cycle:
await worker.run_once()
```

### Scope Derivation

```python
from metaclaw.memory import derive_memory_scope

scope = derive_memory_scope(
    session_id="sess-123",
    user_id="alice",
    workspace_id="project-x",
)
# Returns: "user:alice|workspace:project-x"
```

## Testing

The memory subsystem is covered by 529 tests in `tests/test_memory_system.py`:

```bash
python -m pytest tests/test_memory_system.py -q
```

Test coverage includes:

- Store CRUD, FTS5 search, corruption recovery
- All retrieval modes (keyword, embedding, hybrid, auto)
- Embedder implementations (hashing, sentence-transformers, fallback)
- Policy optimizer proposals and bounds enforcement
- Candidate generation deduplication and bound constraints
- Replay evaluation scoring and composite metric calculation
- Promotion criteria enforcement
- Self-upgrade orchestration with review queue
- Multi-turn context extraction and continuation detection
- Consolidation (dedup, merge, decay)
- Telemetry recording and querying
- Scope derivation logic
- API endpoint integration
- Upgrade worker lifecycle and health tracking
- Memory injection quality (token budget, type diversity, importance ordering)
- Concurrent access safety
