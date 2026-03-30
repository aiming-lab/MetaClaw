---
name: test-before-ship
description: "Use this skill when implementing a feature, fixing a bug, or reviewing a pull request. Ensures code is covered by unit, integration, and end-to-end tests using a test pyramid — validates tests actually fail when code breaks, covers error cases, and requires a regression test before fixing any bug."
---

# Test Before Ship

**Test pyramid:**
- Unit tests for pure functions and business logic (fast, many).
- Integration tests for service interactions and DB queries (medium).
- End-to-end tests for critical user journeys (slow, few).

**Test quality checklist:**
- Does the test actually fail when the code is broken?
- Does it cover the happy path AND the most likely error cases?
- Is the test name descriptive enough to diagnose a failure from the name alone?

**For bug fixes:** add a regression test that reproduces the bug before fixing it.

**Anti-patterns:**
- Tests that only test the mock, not the real behavior.
- Skipping tests because "it probably works".
