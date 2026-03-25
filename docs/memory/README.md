# Memory Upgrade Docs

Last updated: 2026-03-12
Status: All phases and optional enhancements complete (529 tests)

This directory contains the working documentation system for the MetaClaw memory upgrade.

## Structure

### Master control

- [Master Plan](/Users/jiaqi/Myprojects/metaclaw-test/MEMORY_UPGRADE_PLAN.md)
- [Handoff](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/HANDOFF.md)

### Phase documents

- [Phase 0 - Planning and Research](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-0-planning.md)
- [Phase 1 - Base Memory System](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-1-base-memory.md)
- [Phase 2 - Adaptive Memory Policy](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-2-adaptive-policy.md)
- [Phase 3 - Replay Evaluation](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-3-replay-eval.md)
- [Phase 4 - Controlled Self-Upgrade](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/phases/phase-4-self-upgrade.md)

### Research reviews

- [SimpleMem Review](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/research/simplemem-review.md)
- [MetaMem Review](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/research/metamem-review.md)

### Logs

- [Decision Log](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/logs/decision-log.md)
- [Lessons Learned](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/logs/lessons-learned.md)
- [Progress Log](/Users/jiaqi/Myprojects/metaclaw-test/docs/memory/logs/progress-log.md)

## Operating Rules

1. The master plan owns scope, roadmap, and overall status.
2. Each phase file owns detailed deliverables, task tracking, and exit criteria for that phase.
3. Research reviews capture what we learned from external and reference systems.
4. The decision log records architectural choices and why they were made.
5. The lessons log records failures, constraints, and reusable insights.
6. The progress log records dated progress notes as execution moves forward.

## Update Rhythm

- Update the relevant phase doc whenever work advances inside that phase.
- Update the decision log immediately after a design choice is made.
- Update lessons learned immediately after discovering a failure mode or important constraint.
- Update the master plan when the overall status or phase boundaries change.
- Re-read the master plan and active phase document before each substantial new implementation segment.
- Reconcile documentation with repository state before ending a work block or reporting progress.
- Refresh the handoff document whenever ownership is expected to move to another agent or operator.
