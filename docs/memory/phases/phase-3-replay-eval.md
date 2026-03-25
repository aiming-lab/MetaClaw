# Phase 3 - Replay Evaluation

Last updated: 2026-03-12
Status: Complete
Goal: Evaluate memory candidates offline before promotion

## Scope

- replay dataset definition
- baseline versus candidate comparisons
- promotion thresholds
- replay reporting

## Deliverables

- [x] replay format defined
- [x] replay loader implemented
- [x] candidate runner implemented
- [x] comparator implemented
- [x] promotion criteria documented
- [x] reporting added

## Exit Criteria

- memory strategy changes can be tested safely offline
- production changes are gated by replay performance

## Current Implementation Notes

- Replay samples can now be loaded from `records/conversations.jsonl`-style JSONL data.
- `MemoryReplayEvaluator` can run an offline retrieval pass and compare baseline versus candidate summary metrics.
- Replay metrics now include retrieval count, query overlap, continuation overlap, response overlap, a lightweight specificity score, a focus score that penalizes broad low-relevance memory injection, and a value-density score that rewards useful signal per retrieved memory unit.
- CLI now exposes a lightweight `metaclaw memory replay-report` entry point for replay summaries.
- Promotion criteria now exist as explicit threshold logic instead of being left implicit.
- Replay now supports a separate candidate policy file so baseline-versus-candidate comparisons are real policy comparisons rather than same-manager no-op checks.
