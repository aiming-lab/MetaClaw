---
name: context-window-management
description: "Use this skill when a conversation is getting long, a session is approaching token limits, or key decisions risk being lost in a multi-turn agentic task. Proactively summarize state, prioritize active context, and offload resolved information to file-based memory to keep the working context focused."
---

# Context Window Management

**Proactive summarization:**
- At natural breakpoints, summarize key decisions and state into a compact form.
- Keep the active context focused on the current task; move resolved context to a summary.

**Prioritization:**
- Most important: current task description, constraints, and already-confirmed decisions.
- Less important: verbose tool outputs that have been processed; intermediate reasoning.

**File-based memory:** For long-running sessions, write important state to a file rather than keeping it all in the conversation.

**Avoid:** Repeatedly re-reading large files you already have in context; re-running expensive searches for information already retrieved.
