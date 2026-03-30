---
name: graceful-error-recovery
description: "Use this skill when a tool call, shell command, or API request returns an error or unexpected result. Read the full error message and stack trace, identify the root cause (typo, missing dependency, permission, network, logic bug), fix it, then retry — never swallow errors silently or loop on the same failing call."
---

# Graceful Error Recovery

When something fails, diagnose before retrying.

**Process:**
1. Read the full error message — do not skip the stack trace.
2. Identify the root cause: typo, missing dependency, permission, network, logic bug?
3. Fix the root cause, not just the symptom.
4. If the fix is uncertain, try the simplest hypothesis first.
5. If two retries fail, step back and consider an alternative approach.

**Anti-patterns:**
- Retrying the same failed call in a loop.
- Swallowing errors silently with bare `except: pass`.
- Blaming the environment before checking your own code.
