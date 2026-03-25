# Memory Upgrade Decision Log

Last updated: 2026-03-13

## 2026-03-12 - Semantic embedding architecture

Decision:
- Embedder interface is pluggable via BaseEmbedder ABC with encode(), encode_batch(), and dimensions.
- SentenceTransformerEmbedder defaults to all-MiniLM-L6-v2 (384d, fast, good quality).
- Graceful fallback: if sentence-transformers not installed, factory returns HashingEmbedder.
- re_embed_scope() uses batch encoding for efficiency.
- Config adds memory_embedding_mode ("hashing"|"semantic") and memory_embedding_model fields.

Reason:
- Hash-based embeddings provide no real semantic similarity, limiting retrieval quality for natural language queries.
- Pluggable design avoids hard dependency on sentence-transformers for environments where it isn't available.
- Batch encoding amortizes model loading cost across all memories in a scope.

## 2026-03-13 - Sixth-loop integration features

Decision:
- Tag-based retrieval boosting uses a 15% per-tag multiplicative factor to avoid overwhelming keyword/IDF signals.
- Event callbacks are best-effort: errors are logged but never block operations.
- Scope access control uses a flat permission model (read/write/admin) with admin implying all.
- Memory links are directed with typed relationships; the system does not enforce referential integrity (links can reference archived memories).
- Graph clustering uses BFS and only includes non-isolated nodes (at least one link).
- Batch archive always excludes pinned and working_summary memories as a safety guarantee.
- Per-memory quality scoring is a 5-factor composite (0-100) designed to complement the scope-level health score.

Rationale:
- Keeping tag boost multiplicative prevents it from dominating the score.
- Best-effort callbacks avoid coupling external hooks to core memory operations.
- Flat permission model is simple enough for current multi-tenant needs without overengineering.
- Directed links enable dependency and elaboration tracking beyond bidirectional similarity.

## 2026-03-12 - Add recent-window governance summaries

Decision:

- keep cumulative review/alert summaries for long-run health tracking
- add a second layer of fixed recent-window summaries for short-term operational diagnosis

Why:

- cumulative counters alone hide whether the system is improving or actively degrading
- review and alert surfaces are now used as operator tooling, not just artifact dumps

Consequence:

- `review-history`, `review-queue`, `alerts`, and `memory status` can now surface both total history and recent behavior
- future governance metrics should prefer the same pattern: total plus recent-window view

## 2026-03-12 - Apply recent-window summaries to upgrade decisions too

Decision:

- extend the total-plus-recent pattern from review and alert history into upgrade decision history

Why:

- operator diagnosis should not require mixing three different summary styles across adjacent CLI surfaces

Consequence:

- `upgrade-history` and `memory status` now expose recent promotion and pending-review activity alongside total counts

## 2026-03-12 - Persist cycle history, not just the latest cycle artifact

Decision:

- store every auto-upgrade cycle summary in append-only history alongside the latest-cycle JSON snapshot

Why:

- the latest artifact is useful for immediate inspection, but it does not show whether autonomous upgrade quality is stable across runs

Consequence:

- CLI surfaces can now summarize promoted/pending cycle frequency and average best-score behavior across recent windows

## 2026-03-12 - Show cycle quality as rates, not just counts

Decision:

- expose promoted and pending-review cycle rates alongside raw cycle counts

Why:

- once cycle history exists, raw counts still make it hard to compare behavior across short and long windows

Consequence:

- operators can compare recent and total self-upgrade quality without manually normalizing cycle counts

## 2026-03-12 - Treat alert history as a rate-bearing signal too

Decision:

- extend alert-history summaries from raw counts into snapshot rates

Why:

- a count alone does not show whether alert states are sparse across many clean snapshots or present on most runs

Consequence:

- CLI alert inspection now communicates alert frequency directly for both total and recent windows

## 2026-03-12 - Add operational health summaries on top of raw governance metrics

Decision:

- expose a simple health level plus reasons for the self-upgrade loop in addition to the underlying counters

Why:

- governance metrics are now rich enough that the system can summarize likely trouble states directly instead of making operators interpret every number manually

Consequence:

- `memory status` and `memory review-queue` now provide a compact operational judgment while still preserving the raw drill-down data

## 2026-03-12 - Persist health judgments as history, not just live summaries

Decision:

- append operational-health snapshots to their own history stream

Why:

- once health is a first-class operator signal, it needs the same trend visibility as alerts, reviews, and cycles

Consequence:

- operators can now inspect whether the upgrade loop spends most of its time healthy, warning, or critical across recent windows

## 2026-03-12 - Add a first-class handoff document

Decision:

- keep a dedicated handoff document in the memory docs tree instead of forcing future agents to reconstruct state from the logs alone

Why:

- the project has crossed the point where phase docs and logs are enough for continuity, but too fragmented for fast ownership transfer

Consequence:

- the next agent has a single entry point for goals, reading order, current progress, remaining work, boundaries, and operating rules

## 2026-03-12

Decision: Keep skills and memory as separate subsystems.
Reason: They serve different semantic roles and need separate observability.

Decision: Use SimpleMem as the phase 1 engineering reference.
Reason: It offers a practical base memory architecture and cross-session design patterns.

Decision: Use MetaMem as the evolution and replay-evaluation reference.
Reason: Its strongest value is controlled self-upgrade thinking, not direct online integration.

Decision: Implement the living-system concept first as adaptive policy, not automatic code mutation.
Reason: This yields real adaptivity without destabilizing production.

Decision: Split documentation into a master file plus phase, research, and log subdocuments.
Reason: The project is too large to manage sanely in a single growing Markdown file.

Decision: Use SQLite as the phase 1 memory store.
Reason: It is sufficient for the initial factual memory layer, easy to ship, easy to test, and avoids premature infrastructure complexity.

Decision: Make embedding retrieval optional rather than required in phase 1.
Reason: The first cut should deliver stable cross-session memory with the lowest dependency and operational risk.

Decision: Inject memory as a separate prompt block named `Relevant Long-Term Memory`.
Reason: Facts and skills should remain semantically distinct and debuggable.

Decision: Upgrade phase 1 extraction from full-turn persistence to pattern-based factual capture.
Reason: Whole-turn storage is sufficient for a smoke test but too noisy for a usable long-term memory layer.

Decision: Add store-level active-type breakdown and dominant-type summaries in phase 1.
Reason: Adaptive policy and replay evaluation will need lightweight observability before heavier evaluation infrastructure exists.

Decision: Make `memory_retrieval_mode` live in phase 1 with `keyword` and lightweight `hybrid` modes.
Reason: The first adaptive retrieval boundary should exist before embedding infrastructure is introduced.

Decision: Accept `memory_scope` as an explicit request/session input.
Reason: A long-term memory system without scope separation will collapse multiple users or workspaces into one noisy memory pool.

Decision: Implement phase 1 optional embeddings with a deterministic local hashing embedder first.
Reason: This creates a real semantic-retrieval path and stable interfaces now, without blocking on heavyweight embedding-model dependencies.

Decision: Derive memory scope from explicit scope, then user/workspace identity, then session fallback.
Reason: Phase 1 needs practical isolation semantics for multi-user and multi-workspace usage before deeper adaptive memory behavior is added.

Decision: Start adaptive memory policy with persisted rule-based updates instead of learned online tuning.
Reason: Phase 2 needs reversible, inspectable behavior changes before introducing heavier optimization loops.

Decision: Persist memory-policy history as append-only revisions and expose rollback through the CLI.
Reason: Adaptive policy changes are not acceptable unless they are auditable and reversible in normal operator workflows.

Decision: Record memory ingest and policy updates in an append-only telemetry log.
Reason: Replay evaluation and later self-upgrade work will need a lightweight operational trace of how memory behavior changed over time.

Decision: Start replay evaluation with simple overlap-based offline metrics before model-graded evaluation.
Reason: Phase 3 first needs a stable replay harness and comparison contract; richer evaluation can layer on later.

Decision: Make replay promotion criteria explicit in code rather than only in prose.
Reason: Candidate gating needs a concrete contract before offline evaluation can safely influence production policy decisions.

Decision: Replay candidate evaluation should compare against a separate candidate policy artifact.
Reason: A replay harness that evaluates the same live policy twice does not provide a meaningful promotion boundary.

Decision: Phase 4 promotion should be orchestrated as replay evaluation plus explicit promotion, not as direct candidate overwrite.
Reason: Controlled self-upgrade only means anything if there is a clear gating step between candidate creation and live-policy mutation.

Decision: Bound candidate generation to a small neighborhood around the live policy.
Reason: Phase 4 needs a safe, auditable candidate space before any broader search or learned proposal mechanism is introduced.

Decision: Expose candidate generation and directory-level evaluation as explicit offline workflows.
Reason: Controlled self-upgrade needs an operational path that can be run repeatedly and inspected, not just internal helper functions.

Decision: Keep human review as an explicit queue and approval step instead of mixing it into automatic promotion state.
Reason: Manual oversight only works if pending decisions remain visible and separately actionable.

Decision: Run autonomous memory self-upgrade behind a dedicated background worker that can respect scheduler windows.
Reason: The second loop should evolve automatically in production-like operation, but only within the same idle-window safety envelope as other slow updates.

Decision: Expand replay gating beyond query/continuation overlap to include response overlap and specificity.
Reason: Promotion should reward memory that better matches actual answers while discouraging overly generic injected memory.

Decision: Each auto-upgrade cycle should select only one best candidate for action.
Reason: Promoting or queueing multiple candidates from the same evaluation batch weakens the promotion boundary and makes upgrade history harder to reason about.

Decision: Persist upgrade-worker state and deduplicate review-queue entries.
Reason: Autonomous background loops need explicit operational visibility, and review queues should model pending decisions rather than duplicate reminders.

Decision: Pause autonomous upgrade cycles when the review queue is non-empty.
Reason: The system should not keep generating fresh candidate decisions while earlier review-gated decisions are still unresolved.

Decision: Persist a cycle-summary artifact and restore worker progress from state on restart.
Reason: Long-running autonomous loops need both per-cycle auditability and restart continuity to behave predictably in real operation.

Decision: Surface review-queue age and stale-review counts in operator-facing status.
Reason: A human-gated upgrade loop is only safe long-term if pending decisions can visibly age instead of silently blocking automation forever.

Decision: Prune candidate and report artifacts automatically while protecting queued and current-cycle candidates.
Reason: Autonomous self-upgrade needs bounded artifact growth; otherwise long-running systems accumulate stale files faster than operators can inspect them.

Decision: Attach cleanup results to the cycle-summary artifact and include queue counts in worker waiting state.
Reason: Long-running automation needs auditability for both what was evaluated and what was later pruned or blocked.

Decision: Add a replay focus metric and gate promotions on non-regressing focus.
Reason: Overlap alone can reward injecting larger but noisier memory blocks; promotion should prefer memory that stays relevant to the actual task and answer context.

Decision: Make stale-review thresholds configurable and represent them as a separate worker state.
Reason: A blocked queue with fresh pending items and a blocked queue that has been stale for days are different operational situations and should not collapse into one status.

Decision: Add a replay value-density metric and use it in promotion gating.
Reason: Candidate policies should not be rewarded for increasing overlap merely by retrieving more memories; the replay gate should also measure useful signal per injected unit.

Decision: Persist upgrade alerts separately from worker state.
Reason: Operational blockers such as stale review should survive restarts and be visible even when the worker is not actively running a cycle.

Decision: Keep an append-only history of upgrade alert snapshots and expose it via CLI.
Reason: Operators need to see whether blockers are recurring, sustained, or already resolved; a single latest alert snapshot is not enough.

Decision: Add aggregated alert-history summaries on top of raw alert snapshots.
Reason: Once alert history exists, operators still need a compressed signal of recurrence and severity distribution instead of reading every snapshot line-by-line.

Decision: Add aggregated candidate-metric summaries to each cycle artifact.
Reason: A self-upgrade batch should be inspectable at the batch level; operators should not need to open every per-candidate report to understand whether a cycle broadly improved or regressed.

Decision: Separate review-event history from general upgrade history.
Reason: Human review is its own workflow with queue/approval/rejection semantics; mixing it only into upgrade-history makes the review path harder to audit directly.

Decision: Include review resolution latency in review-history summaries.
Reason: Queue size alone does not say whether review operations are healthy; the system also needs a direct measure of how long approvals and rejections take.

Decision: Estimate review backlog pressure from pending volume and historical resolution latency.
Reason: A pending count is not enough to understand operational load; the same queue size means very different things under fast and slow human review throughput.

Decision: Include approval and rejection rates in review-history summaries.
Reason: Review operations need quality signals as well as throughput signals; outcome balance helps reveal whether the candidate generator is producing mostly acceptable or mostly poor proposals.

## 2026-03-12 - Second-loop quality improvements

Decision: Add response-side pattern extraction in addition to prompt-side extraction.
Reason: Many factual signals appear in assistant responses (e.g. "the project uses X"), not just user prompts. Extracting from both sides with appropriate confidence differences produces richer memory without introducing noise.

Decision: Add near-duplicate merging to consolidation using Jaccard token similarity at threshold 0.80.
Reason: Exact-content dedup misses memories that differ by a few words but carry the same information. Jaccard similarity at 0.80 catches these while being conservative enough to avoid merging genuinely distinct memories.

Decision: Replace flat keyword match count with IDF-weighted scoring in keyword retrieval.
Reason: Simple match count treats every term equally, which means common terms dominate scoring. IDF weighting lets rare, more informative terms drive ranking, improving retrieval precision.

Decision: Add grounding score and coverage score as new replay evaluation metrics.
Reason: Term overlap alone cannot distinguish task-relevant from coincidentally overlapping memories. Grounding score measures entity/topic alignment with the task context. Coverage score measures how much of the response was anticipated by memory. Both are needed for promotion to reward memory that is genuinely useful to the task.

Decision: Include grounding and coverage in candidate_beats_baseline and promotion criteria.
Reason: New metrics that are not gated can be silently regressed by promoted candidates. Every quality signal should also be a promotion constraint.

Decision: Add importance decay to consolidation for old, unused memories.
Reason: Without decay, the active memory pool grows indefinitely and retrieval quality degrades because low-value old memories compete with fresh relevant ones. Decay uses the later of last_accessed_at and updated_at as the reference point, with configurable thresholds and a minimum importance floor.

Decision: Make working summaries structured with topic lines and turn-count context.
Reason: Raw transcript excerpts are hard to scan during retrieval. Topics and turn counts make summaries more useful as retrieval targets and more informative when injected into prompts.

Decision: Enhance policy optimizer with type-distribution-aware tuning.
Reason: The phase-2 optimizer only used volume thresholds. By analyzing the active memory type distribution (factual ratio, episodic ratio), the optimizer can make better weight decisions that improve retrieval relevance. A low-volume safety guard prevents premature tuning on sparse data.

Decision: Render memories grouped by type with bullet-point format.
Reason: Per-unit headings waste tokens and are harder to scan. Grouping by type with bullets produces a more compact, structured prompt block that is easier for the model to process.

Decision: Add telemetry-driven policy optimization.
Reason: Rule-based optimization from store stats alone cannot see how retrieval behaves at runtime. By feeding retrieval telemetry (saturation rate, zero-result rate, token usage) into the optimizer, policy proposals become responsive to actual usage patterns rather than only static pool characteristics.

## 2026-03-13 - Third-loop production hardening

Decision: Add FTS5 virtual table with graceful fallback.
Reason: Manual keyword scan over all active units becomes expensive at hundreds of memories. FTS5 provides near-instant text matching while falling back to manual scan when FTS5 is not compiled into the SQLite build.

Decision: Handle corrupted SQLite stores with automatic backup and reset.
Reason: A corrupted database file should not crash the system. Backing up the corrupt file preserves forensic evidence while allowing the system to continue operating.

Decision: Add multi-turn context accumulation for extraction.
Reason: Per-turn extraction misses cross-turn patterns like pronoun references and "also" continuations. A sliding window context accumulator allows continuation turns to inherit entities and context from recent prior turns.

Decision: Add entity-based cross-type reinforcement instead of cross-type merging.
Reason: Merging memories across types would lose semantic distinction. Reinforcement scoring preserves each memory's type while boosting the ranking of memories that share entities with other memories.

Decision: Add query expansion with synonym/abbreviation mapping.
Reason: Users often use abbreviations (db, auth, k8s) while memories store full terms. Expansion improves recall without requiring the user to know which terms exist in the memory pool. Expansion-only matches are scored at 0.85x to prefer direct hits.

Decision: Add pre-ingestion deduplication against existing store contents.
Reason: Post-hoc consolidation catches duplicates but wastes storage and processing. Pre-ingestion dedup prevents identical content from entering the store in the first place.

Decision: Add retrieval type diversity enforcement.
Reason: Without diversity enforcement, a query matching many same-type memories would produce homogeneous results. Capping any single type at 60% of slots ensures the user sees a varied set of relevant memories.

Decision: Add confidence-weighted scoring to hybrid retrieval.
Reason: Memories extracted from response patterns have lower confidence than prompt patterns. Confidence weighting ensures that uncertain observations rank below confirmed facts when both match equally.

Decision: Add pre-ingestion deduplication.
Reason: Relying only on post-hoc consolidation is wasteful. Checking for content-identical units before inserting prevents duplicates from entering the store.

Decision: Add retrieval type diversity enforcement.
Reason: Without diversity caps, a query matching many units of the same type produces homogeneous results. Capping any single type at 60% ensures diverse context injection.

Decision: Add memory export/import and garbage collection CLI commands.
Reason: Operators need backup/migration paths and the ability to clean up superseded chains. These are operational necessities, not polish.

Decision: Add importance auto-calibration for frequently accessed memories.
Reason: Access patterns indicate real-world relevance. Memories retrieved 3+ times deserve a small importance boost to reinforce their ranking in future retrievals.

Decision: Add threading.Lock to MemoryStore.
Reason: The background upgrade worker and request-time retrieval may access the store concurrently. A lock prevents sqlite3 threading issues.

Decision: Add store compaction after garbage collection.
Reason: SQLite doesn't automatically reclaim space after deletions. VACUUM after GC prevents the database file from growing indefinitely.

Decision: Add zero-retrieval regression gating to promotion criteria.
Reason: A candidate policy that improves overlap scores but causes many more zero-retrieval samples has reduced coverage. The promotion gate should catch this regression.

Decision: Add policy state validation before promotion.
Reason: Candidate policies generated by bounded perturbation are generally safe, but a validation step ensures no out-of-range parameters slip through to production.

Decision: Add stratified session-balanced sampling for large replay datasets.
Reason: Simple truncation would bias evaluation toward the first session's data. Stratified round-robin across sessions ensures each session contributes equally to the evaluation.

## 2026-03-12 - Fourth-loop integration and operator tooling

Decision: Add a composite replay quality score.
Reason: Individual metric deltas are too fragmented for quick operator comparison. A weighted composite with zero-retrieval penalty provides a single actionable number.

Decision: Add telemetry-weighted replay sampling.
Reason: Sessions with richer retrieval history are more informative for replay evaluation and should be sampled preferentially over sessions with sparse retrieval data.

Decision: Integrate composite score into self-upgrade decision scoring.
Reason: The decision_score function should use the composite when available for consistency between operator-facing metrics and automated promotion decisions.

Decision: Add retrieval feedback (helpful/not helpful) with asymmetric importance adjustment.
Reason: Negative feedback (-0.05) should outweigh positive feedback (+0.03) to ensure noisy or incorrect memories decay faster than useful ones accumulate.

Decision: Add store-level garbage_collect method.
Reason: GC logic belongs in the store for programmatic access from background workers and tests, not only inline in CLI code.

Decision: Add retrieval explanations (reason field on search hits).
Reason: Operators need to understand why each memory was selected to build trust and debug retrieval quality issues.

Decision: Add memory diagnostics combining store, access, retrieval, and policy signals.
Reason: Operator debugging is too slow when each signal lives in a separate CLI command. A single diagnostic view reduces time-to-insight.

Decision: Add memory conflict detection based on topic/entity overlap.
Reason: Contradictory memories (e.g., "we use MySQL" vs "we use PostgreSQL") degrade retrieval quality. Automatic detection helps operators identify and resolve inconsistencies.

Decision: Add memory pinning with importance=0.99 for guaranteed retrieval ranking.
Reason: Some memories (critical project facts, compliance requirements) should always appear in retrieval regardless of scoring. Pinning provides explicit operator control.

Decision: Add pool summary generator for operator inspection.
Reason: Operators need a quick overview of the memory pool without running multiple commands. A single summary with type breakdown, top items, and conflict detection covers the most common inspection use case.

Decision: Add retention policy for automatic memory archival.
Reason: Without active retention, memory pools grow indefinitely and retrieval quality degrades. Archiving old, low-importance, never-accessed memories keeps the active pool focused.

Decision: Add LLM-judge interface as an abstract base class, not a concrete implementation.
Reason: The judge needs an actual LLM endpoint which may not be available in all deployments. An interface allows deployment-specific implementations without coupling the core system to a specific LLM provider.

### Fifth-loop decisions

Decision: Add expires_at field to MemoryUnit for TTL-based expiry.
Reason: Time-bounded facts (sprint goals, temporary credentials, event dates) should automatically expire rather than requiring manual cleanup. Filtering at list_active time ensures expired memories never pollute retrieval.

Decision: Reduce confidence by 0.05 when sharing memories across scopes.
Reason: Shared memories lack the original conversational context. A slight confidence reduction signals that the memory was inherited rather than directly extracted, affecting scoring in retrieval.

Decision: Generate fresh IDs on import rather than preserving originals.
Reason: Imported memories may come from a different database with conflicting IDs. Fresh IDs prevent collision while the content and metadata are preserved.

Decision: Reset access statistics on import.
Reason: Access counts from a source scope don't reflect relevance in the target scope. Starting from zero lets the new scope's retrieval feedback naturally adjust importance.

Decision: Memory merge supersedes both originals and takes max importance/confidence.
Reason: A merge represents a curated consolidation of conflicting or overlapping facts. Taking the maximum importance ensures the merged memory inherits the strongest signal from either parent.

Decision: Add user-defined tags as a lightweight metadata field separate from topics/entities.
Reason: Topics and entities are auto-extracted and represent content semantics. Tags are operator-assigned categories (e.g., "reviewed", "archived", "team-shared") that serve organizational rather than retrieval purposes.

Decision: Store tags as sorted JSON array for consistency.
Reason: Sorted storage ensures deterministic comparison and display regardless of insertion order, simplifying deduplication and test assertions.

Decision: Integrate TTL expiry into upgrade worker rather than creating a separate background job.
Reason: The upgrade worker already runs on a periodic schedule. Adding TTL expiry as a lightweight pre-step avoids a separate async task and keeps the background maintenance consolidated.

Decision: Use SQLite-backed event log for audit trail rather than file-based logging.
Reason: SQLite provides structured queries, scope filtering, and limit/pagination natively. The event log shares the same database as the memory store, simplifying deployment and backup.

Decision: Make event logging best-effort (never block mutations).
Reason: Audit trail is valuable but should never block or delay memory operations. A failed event log write should not prevent a memory from being created or merged.

Decision: Health score uses four equally-weighted components (access, importance, diversity, freshness) for simplicity.
Reason: A composite score needs to be interpretable by operators. Four clear components with equal 25-point weights make it easy to identify which aspect needs attention.

Decision: Scope snapshots archive current state before restoring, never delete.
Reason: Destructive restore (deleting current memories) risks data loss. Archiving preserves history and allows recovery if the restored snapshot is incorrect.

Decision: Auto retrieval mode selects based on query length threshold of 4 words.
Reason: Short queries (1-3 words) work well with keyword search. Longer queries benefit from hybrid mode's embedding similarity. The threshold is deliberately simple and can be tuned via the policy optimizer.

Decision: Consolidation dry-run is a separate method rather than a flag on consolidate().
Reason: Dry-run needs to return detailed preview information (counts per category) that differs from the apply result. A separate method keeps both interfaces clean.

Decision: Pinned memories are rendered first in prompt regardless of grouping.
Reason: Pinned memories represent operator-designated critical facts. If token budget is limited, they should never be cut. Rendering them first ensures they are always included.
