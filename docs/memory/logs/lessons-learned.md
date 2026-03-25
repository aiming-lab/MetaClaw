# Memory Upgrade Lessons Learned

Last updated: 2026-03-13

## 2026-03-12

- Pluggable embedding architecture with graceful fallback is essential for optional ML dependencies — not all deployment environments will have sentence-transformers/PyTorch installed.
- Batch encoding via encode_batch() is critical for re_embed_scope() performance; encoding 5000 memories one-by-one with a transformer model would be prohibitively slow.
- The embedding column in SQLite is `embedding_json` (TEXT storing JSON array), not a bare `embedding` column — always check schema before writing raw SQL.

## 2026-03-13

- CLI commands that need a MemoryManager should always use `MemoryManager.from_config()` instead of constructing store + manager separately; the previous pattern led to an undefined `_build_manager` helper.
- Event callbacks on the manager must be best-effort — wrapping them in try/except prevents external hook failures from breaking core memory operations.
- Graph-based features (links, clusters) add significant organizational value but must stay lightweight at query time; BFS on in-memory adjacency lists keeps cluster detection fast.
- Per-memory quality scoring is most useful when combined with batch operations (batch-archive by quality threshold), creating a feedback loop between quality assessment and cleanup.
- Scope access control needs to be simple at this stage — a flat read/write/admin model with admin-implies-all avoids the complexity of role hierarchies while supporting multi-tenant deployments.

## 2026-03-12

- MetaClaw already has a good procedural memory loop through skills, so the first memory upgrade should target factual and cross-session continuity instead of overlapping with the skill system.
- A living memory subsystem is feasible, but only if adaptivity is bounded and evaluated.
- MetaMem should be translated into an offline upgrade discipline rather than copied into the online serving path.
- SimpleMem is the right place to borrow phase 1 architecture ideas such as write-side compression, hybrid retrieval, and token-budgeted context injection.
- A keyword-first SQLite memory layer is enough to establish the full phase 1 path before adding heavier retrieval infrastructure.
- Making `metaclaw/__init__.py` tolerant of missing serving dependencies is important for testing lighter modules in isolation.
- For a multi-phase upgrade like this one, the Markdown docs need to be treated as a maintained control plane, not a one-time planning artifact; otherwise implementation quickly outruns the recorded design state.
- Lightweight deterministic embeddings are a useful bridge: they let the retrieval interfaces, storage schema, and tests mature before committing to a heavyweight model-serving dependency.
- Any persisted adaptive-policy artifact must be isolated in tests; otherwise policy state leaks across runs and produces misleading failures.
- Adaptive behavior needs operator-grade controls early; revision history and rollback are not polish, they are part of making policy adaptation safe enough to iterate on.
- Autonomous upgrade loops should key off real artifact changes such as replay-record mtime; otherwise they waste cycles re-evaluating the same data.
- Once a human review queue exists, stale pending items become an operational issue; surfacing queue age is necessary because "pending count" alone hides whether the system has been blocked for hours or days.
- Self-upgrade artifacts need retention rules early. Candidate and report directories grow continuously in autonomous mode, so cleanup has to preserve active review evidence while trimming the rest.
- Replay quality signals need both recall and precision pressure. Query/response overlap helps detect useful recall, but a separate focus signal is needed to catch candidates that improve overlap by spraying in too much loosely related memory.
- Human review queues need age semantics in runtime state, not just in offline inspection. Once autonomous upgrade is enabled, stale review should show up as a first-class blocked condition, not just a number in a report.
- Replay precision needs a budget-aware signal, not just relevance-aware signals. Focus catches noisy text, but value density is what catches policies that simply retrieve more units to raise overlap scores.
- Worker state alone is not enough for long-running supervision. Blocking conditions that matter to operators should also exist as durable alert artifacts so they remain visible across restarts and inactive periods.
- Once durable alerts exist, operators also need alert history. Otherwise repeated or long-lived review blockage still looks like a one-off snapshot instead of a trend.
- Raw alert history quickly becomes another log stream to sift through. For autonomous subsystems, summary counters are part of usability, not polish.
- Per-candidate reports are useful for debugging, but operationally you also need a batch summary. Otherwise every self-upgrade cycle becomes too expensive to inspect.
- Review workflow needs its own event stream. If queued/approved/rejected actions only appear indirectly inside upgrade history, operators lose the ability to audit human intervention cleanly.
- A healthy review system is not just one that records approvals and rejections. You also need latency, otherwise a slow but eventually resolving queue looks identical to a responsive one.
- Even latency is not enough on its own. Operational pressure comes from latency multiplied by current pending load, so review observability needs a backlog-pressure estimate rather than isolated counters.
- Throughput metrics alone still miss review quality. Approval and rejection rates are needed to tell whether the self-upgrade loop is sending humans mostly good candidates or mostly noise.
- Repo-local test invocation details matter. In this repo the reliable memory-suite command is `python -m unittest discover -s tests -p 'test_memory_system.py'`, not module-style discovery through `tests.test_memory_system`.
- Cumulative governance metrics are not enough once the system runs continuously. Operators also need short-window summaries to tell whether review and alert conditions are currently improving or degrading.
- Last-value artifacts are not enough for autonomous subsystems. If a metric matters operationally, it eventually needs append-only history as well as the latest snapshot.
- Once history exists, ratios usually matter as much as counts. Cycle-level governance gets easier to compare across time windows when promotion and pending-review are exposed as rates.
- Alert streams follow the same rule: snapshot counts become much more interpretable once they are paired with per-window rates.
- Once governance metrics mature, operators need a compact judgment layer too. Health levels should be built on top of the underlying counters, not instead of them.
- Once a judgment layer exists, it also needs history. Otherwise health becomes just another opaque last-value indicator with no trend context.
- Once a multi-phase system is handed between agents, logs alone are too expensive to reconstruct. A dedicated handoff document becomes part of the control plane, not optional process overhead.
- Near-duplicate merging threshold must be conservative (0.80+) because extraction patterns already produce similar-looking memories from adjacent turns; aggressive merging can collapse legitimately distinct facts and break downstream test expectations.
- IDF-weighted keyword scoring is a cheap win for retrieval quality: it requires no external dependencies and naturally prioritizes rare discriminative terms over common ones.
- Response-side extraction should use lower confidence than prompt-side extraction because the assistant may be paraphrasing or speculating rather than reflecting ground-truth user intent.
- Policy optimization should not fire before sufficient data accumulates. A low-volume guard (e.g., <5 active memories) prevents premature tuning that could create poor defaults for later sessions.
- Prompt rendering should prioritize token efficiency. Grouping by type and using bullets instead of per-unit sections reduces token waste without losing information structure.
- FTS5 virtual tables need graceful fallback because not all SQLite builds include FTS5 support. The FTS path should be a fast-path optimization, not a hard dependency.
- Corrupted SQLite files should be backed up and replaced, not deleted. Operators may need to inspect the original file for forensics.
- Multi-turn extraction needs explicit continuation detection rather than blanket context carry-forward. Injecting all prior context into every turn's extraction would produce false matches from unrelated prior exchanges.
- Query expansion should penalize expansion-only matches (e.g., 0.85x score) to prefer direct term hits while still improving recall for abbreviation/synonym gaps.
- Pre-ingestion deduplication prevents content-identical memories from accumulating when the same session is ingested multiple times, which is cheaper than relying only on post-hoc consolidation.
- Retrieval type diversity enforcement is better implemented as a reordering step before token budget fitting than as a scoring modification, because it preserves the original ranking within each type while ensuring variety.
- Entity reinforcement across memory types is a lightweight way to surface cross-cutting information without merging semantically different memory units.
- Confidence-weighted retrieval scoring helps differentiate between high-certainty facts and low-certainty observations when both match the query equally well.
- Pre-ingestion deduplication is more efficient than relying solely on post-hoc consolidation because it avoids writing to disk and building FTS indexes for content that already exists.
- Type diversity enforcement is better implemented as a reordering step than as a scoring modification because it preserves ranking quality within each type.
- Importance auto-calibration based on access frequency creates a natural feedback loop where useful memories surface more reliably over time.
- SQLite VACUUM is needed after GC because deleted rows leave dead space in the file that is not reclaimed automatically.
- Extraction pattern coverage should grow incrementally with tests for each new pattern. Testing each pattern ensures false positive rates stay low as the pattern set expands.

## 2026-03-12 - Fourth-loop integration and operator tooling

- A composite quality score across all replay metrics is essential for quick operator comparison. Individual metric deltas are too fragmented to scan at scale; a single weighted number with zero-retrieval penalty makes evaluation loops practical.
- Telemetry-weighted replay sampling is a natural extension once retrieval telemetry exists. Sessions with richer retrieval history are more informative for replay evaluation and should be sampled preferentially.
- Retrieval feedback (helpful/not helpful) creates a user-driven signal path for memory importance that complements the automatic access-count calibration. Negative feedback is more impactful (-0.05) than positive (+0.03) to ensure noisy memories decay faster.
- Retrieval explanations are not just debugging tools; they also help operators build trust in the memory system by showing exactly why each memory was selected.
- Diagnostics should combine store, access, retrieval, and policy signals into a single view. Operator debugging is too slow when each signal lives in a separate CLI command.
- Store-level garbage collection methods belong in the store module, not inline in CLI code. This allows programmatic GC from background workers and tests.
- Integration tests simulating the full request injection flow catch issues that unit tests miss, especially around message list manipulation and system message merging.

## 2026-03-12 - Fifth-loop advanced features

- TTL filtering at list_active time is the simplest and most reliable approach. It avoids requiring a separate background job and ensures expired memories never appear in any retrieval path.
- Cross-scope sharing needs a confidence reduction signal to distinguish shared memories from directly extracted ones. A 0.05 reduction is enough to affect ranking without being too aggressive.
- Import should always generate fresh IDs to prevent collisions across databases. Access stats should be reset since the original context doesn't apply.
- Memory merge is a natural complement to automatic consolidation. Manual merge gives operators explicit control when automatic deduplication's similarity threshold doesn't catch a pair that should be combined.
- User-defined tags serve a different purpose than auto-extracted topics/entities. Tags are organizational metadata (reviewed, deprecated, team-shared), while topics/entities are content-derived signals for retrieval scoring.
- Schema migrations with column addition (ALTER TABLE ADD COLUMN) are safe and backward-compatible. Checking column existence before ALTER avoids errors on databases that already have the column.
- Consolidating background maintenance into the upgrade worker (TTL expiry + upgrade cycle) keeps the async architecture simpler than having separate periodic tasks.
