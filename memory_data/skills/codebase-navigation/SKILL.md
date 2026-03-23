---
name: codebase-navigation
description: "Use this skill when exploring an unfamiliar codebase, tracing how a feature works end-to-end, or finding where a function is defined versus called. Provides a structured read-first strategy — entry points, imports, data model, tests, git log — before making any changes."
---

# Codebase Navigation

Before modifying unfamiliar code, build a mental model.

**Exploration strategy:**
1. Start with entry points: `main.py`, `__init__.py`, `index.ts`, `App.tsx`.
2. Follow imports to understand dependency structure.
3. Find the data model first — it shapes everything else.
4. Read tests: they document expected behavior better than comments.
5. Check git log: recent commits explain *why* things are the way they are.

**Efficient search:**
- Use file pattern search (glob) to find files by name/extension.
- Use content search (grep) to find where a function/class is defined vs. called.
- Search for the error message text to find the source location directly.

**Anti-patterns:**
- Modifying code without reading it first.
- Assuming file structure from another codebase.
- Grepping without a clear hypothesis of what you are looking for.
