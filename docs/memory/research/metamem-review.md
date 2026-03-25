# Reference Review - MetaMem

Last updated: 2026-03-12
Status: Initial review complete
Reference root: `/Users/jiaqi/Myprojects/metaclaw-test/MetaMem`

## Why It Matters

MetaMem is the main reference for:

- memory-system evolution
- candidate evaluation loops
- benchmark-centered iteration
- the broader "living memory" thesis

## Files Reviewed

- [README](/Users/jiaqi/Myprojects/metaclaw-test/MetaMem/README.md)
- [src/interface.py](/Users/jiaqi/Myprojects/metaclaw-test/MetaMem/src/interface.py)
- [src/evaluator.py](/Users/jiaqi/Myprojects/metaclaw-test/MetaMem/src/evaluator.py)
- [src/evolution_harness.py](/Users/jiaqi/Myprojects/metaclaw-test/MetaMem/src/evolution_harness.py)
- [best generated system sample](/Users/jiaqi/Myprojects/metaclaw-test/MetaMem/generations/claude_v1/round_3/memory_system.py)
- [docs/HANDOFF.md](/Users/jiaqi/Myprojects/metaclaw-test/MetaMem/docs/HANDOFF.md)

## Key Takeaways

- The valuable idea is not "let production code rewrite itself live".
- The valuable idea is "use dense feedback plus benchmarked comparison to evolve memory strategies safely".
- MetaMem's strongest contribution to MetaClaw is phase 3 and phase 4, not phase 1.
- A living memory system needs a replay or benchmark harness, otherwise adaptation will drift.

## Directly Reusable Ideas for MetaClaw

- replay-based comparison of candidate memory strategies
- explicit baseline versus candidate evaluation
- rich error-analysis loops for memory retrieval failures
- architecture search only inside a controlled promotion workflow

## Not Recommended for Direct Porting

- heavy benchmark-time reflection in the request-serving path
- unbounded code generation as part of normal online operation
- direct coupling of research harness logic to the main proxy
