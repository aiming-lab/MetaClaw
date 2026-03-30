---
name: do-not-retry-without-diagnosis
description: "Use this skill when a command, tool call, or API request fails. Stop before retrying — read the error message, classify it as transient or permanent, and fix the root cause first. Prevents wasted retries on errors that will never self-resolve."
---

# Do Not Retry Without Diagnosis

**Mistake pattern:** Tool call fails → retry the same call → fails again → repeat.

**Fix:** After the first failure, read the error message carefully and diagnose the root cause before retrying.

**Questions to ask:**
- Is this a transient error (network timeout, rate limit)? Retry with backoff.
- Is this a permanent error (wrong input, missing resource, permission denied)? Fix the cause.

**Anti-pattern:** Blindly retrying or escalating without examining the error output.
