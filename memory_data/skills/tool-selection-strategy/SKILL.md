---
name: tool-selection-strategy
description: "Use this skill when deciding which tool to call next in an agentic workflow — e.g. choosing between Bash, Grep, Read, or a dedicated tool. Applies the least-tool principle: answer from context first, prefer specific tools over heavy ones like Bash or Agent, read before writing, avoid speculative calls, and parallelize independent reads."
---

# Tool Selection Strategy

**Principles:**
- **Least tool principle:** Use the most specific, lightweight tool that accomplishes the goal.
- **Read before writing:** Always read a file before editing it to understand current state.
- **Avoid speculative calls:** Don't call a tool "just to see what happens". Have a clear hypothesis.
- **Parallelize independent calls:** If two reads don't depend on each other, fire them simultaneously.

**Decision heuristic:**
1. Can I answer this from memory/context? No tool call needed.
2. Is this a file operation? Use Read/Write/Edit tools.
3. Is this a code search? Use Grep/Glob tools.
4. Is this a system operation? Use Bash (last resort).

**Anti-pattern:** Using a heavy tool (Agent, Bash) when a lightweight dedicated tool suffices.
