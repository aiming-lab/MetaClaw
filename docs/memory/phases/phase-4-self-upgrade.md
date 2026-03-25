# Phase 4 - Controlled Self-Upgrade

Last updated: 2026-03-12
Status: Complete
Goal: Enable safe self-improvement of the memory subsystem

## Scope

- bounded candidate generation
- offline candidate evaluation
- promotion and rollback flows
- optional human review

## Deliverables

- [x] bounded candidate space defined
- [x] offline generation workflow defined
- [x] promotion path implemented
- [x] rollback path implemented
- [x] history tracking implemented

## Exit Criteria

- memory can improve through validated candidate promotion
- live system is not directly mutated without safeguards

## Current Implementation Notes

- `MemorySelfUpgradeOrchestrator` now evaluates a candidate policy via replay before promotion.
- Promotion writes the candidate into the live policy path only after replay gating passes.
- Replay reports and upgrade-history records are persisted as artifacts.
- Rollback currently reuses the policy-store revision history introduced in phase 2.
- Candidate policies are now generated from a bounded search space around the current live policy instead of allowing arbitrary unbounded mutation.
- Candidate generation and directory-level replay evaluation are now available as explicit offline workflows.
- Optional human review is now supported through a review queue plus explicit approve/reject actions.
- Artifact management now includes default candidate/report directories plus history and candidate-directory inspection helpers.
- An end-to-end bounded auto-upgrade cycle now exists: generate candidates, replay-evaluate them, and either promote or queue them for review.
- A background `MemoryUpgradeWorker` now exists and can be gated by scheduler windows for autonomous upgrade cycles.
- Directory-level candidate evaluation now selects a single best candidate per cycle instead of promoting or queueing multiple candidates at once.
- Worker state is now persisted for observability, and review-queue enqueueing is deduplicated by candidate path.
- Autonomous upgrade now pauses when the review queue is non-empty, which keeps the system from generating new decisions while older ones remain unresolved.
- Upgrade-history and status surfaces now expose summary counts, not just raw event lists.
- Each auto-upgrade cycle now writes a cycle-summary artifact, and the worker restores its last processed progress across restarts.
- Review-queue summaries now expose stale-count and queue age, which makes human-gated blocking visible from CLI status.
- Candidate/report artifact cleanup now runs after auto-upgrade cycles, while preserving queued review items and current-cycle references.
- Cycle summaries now include cleanup results, and worker waiting states include pending/stale review counts for better runtime diagnosis.
- Review staleness is now configurable, and the worker enters a distinct `waiting_review_stale` state when the queue has aged beyond the configured threshold.
- The worker now persists `upgrade_alerts.json`, which turns stale review blockage into a durable operator-facing alert instead of only a transient worker state.
- Alert snapshots are now appended to `upgrade_alerts_history.jsonl`, and the CLI exposes a dedicated alert-inspection command instead of forcing operators to infer alert history from the current snapshot.
- Alert history now has aggregated summaries, so operators can see whether blockage is rare, recurring, or dominated by stale-review failures without scanning raw JSONL by hand.
- Cycle summaries now also include aggregated candidate-metric summaries, which makes each auto-upgrade batch easier to inspect without reading every candidate report individually.
- Review handling now has its own append-only history and CLI surface, which separates human approval workflow from the broader upgrade-decision history.
- Review history summaries now include resolution latency, so operators can see whether human review is merely present or actually keeping up with the queue.
- Review history summaries now also estimate backlog pressure, combining pending review volume with historical resolution latency to expose when the queue is operationally overloaded.
- Review history summaries now expose approval and rejection rates, so review quality can be tracked alongside latency and queue pressure.
- Review and alert summaries now also include recent-window counters and rates, which separates long-run cumulative totals from the current operational trend.
- Upgrade-decision history now follows the same pattern, so promotion/review/rejection activity can be inspected as both cumulative totals and recent behavior.
- Per-cycle upgrade summaries are now appended into cycle history, making autonomous upgrade behavior inspectable across runs instead of only through the latest cycle artifact.
- Cycle-history summaries now expose promoted/pending cycle rates in addition to raw counts, which makes batch-level self-upgrade quality easier to judge at a glance.
- Alert-history summaries now expose snapshot rates as well as counts, which makes it easier to tell whether blocked/stale states are occasional or routine.
- The self-upgrade governance layer now emits a compact operational-health summary, combining queue staleness, backlog pressure, and recent cycle behavior into a readable health level plus reasons.
- Operational-health snapshots are now persisted over time, so health levels can be inspected as a trend instead of only as a current computed state.
