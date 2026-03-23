---
name: debug-systematically
description: "Use this skill when a test is failing, code behaves unexpectedly, or there is a bug to diagnose. Follow a structured reproduce-isolate-hypothesize-test-fix-verify cycle instead of randomly changing code or guessing at the cause."
---

# Debug Systematically

**Process:**
1. **Reproduce** the bug with the smallest possible input.
2. **Isolate** — narrow down which component/function causes it.
3. **Hypothesize** — form a specific, falsifiable hypothesis.
4. **Test** — verify or disprove the hypothesis with a minimal experiment.
5. **Fix** — address the root cause, not just the symptom.
6. **Verify** — re-run the failing test and related tests.

**Useful tools:** `print`/`logging`, `pdb`/`ipdb`, unit tests, `git bisect`.

**Anti-patterns:**
- Changing multiple things at once and not knowing what fixed it.
- Ignoring related test failures.
- Commenting out code instead of understanding it.
