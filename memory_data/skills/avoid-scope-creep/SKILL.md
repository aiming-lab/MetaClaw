---
name: avoid-scope-creep
description: "Use this skill when completing a targeted bug fix, small edit, or focused change where you notice other issues and feel the urge to also refactor, rename, or clean up. Enforces the rule of changing only what was explicitly requested and surfacing other issues as notes instead."
---

# Avoid Scope Creep

**Mistake pattern:** User asks to fix a specific bug → you also refactor the function, rename variables, add docstrings, and restructure the file → harder to review, introduces new risk.

**Rule:** Only change what was asked. If you notice other issues while working, mention them as a note rather than silently fixing them.

**Exception:** If a requested change is impossible without fixing a directly blocking dependency, fix the minimum required dependency and explain why.

**Anti-pattern:** `while I'm here, I also improved...` without being asked.
