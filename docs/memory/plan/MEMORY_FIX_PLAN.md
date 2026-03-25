# MetaClaw Memory System Fix Plan

## Bug Summary

| # | Bug | Severity | Status |
|---|-----|----------|--------|
| 1 | Memory scope triple-nesting across turns | CRITICAL | FIXED |
| 2 | Memory injection gated on `skill_manager` not `memory_manager` | CRITICAL | FIXED |
| 3 | RL mode never buffers turns for memory extraction | CRITICAL | FIXED |
| 4 | Turns lost to memory when skill evolution triggers mid-session | HIGH | FIXED |
| 5 | Cross-session memory retrieval is scope-locked | CRITICAL | FIXED |
| 6 | Memory injection blocks async event loop (sync in async) | MEDIUM | FIXED |
| 7 | Missing `@pytest.mark.asyncio` in live tinker tests | MEDIUM | FIXED |

---

## Verification Results

| Test Suite | Result |
|------------|--------|
| Unit tests | 535/535 passed |
| Live Tinker tests (with API key) | 9/9 passed |
| E2E test (skills_only + memory) | 10/10 passed |
| RL training experiment | 3/3 steps, memory active (28 units, 11 active) |

### Key before/after comparisons

| Metric | Before | After |
|--------|--------|-------|
| Memory scope (3 turns) | `default\|session:X\|session:X\|session:X` | `default\|session:X` (stable) |
| Cross-session memory recall | Broken (scope mismatch) | Working ("PostgreSQL + FastAPI" recalled in session 2) |
| Memory in RL mode | 0 units extracted | 28 units extracted (11 active) |
| Memory injection w/o skills | Skipped entirely | Works independently |
| Async safety | Blocking SQLite in event loop | `asyncio.to_thread()` |
| Memory health score | 0 | 65.7 |
| Skill evolution in RL | 0 skills | 10 new skills generated |

---

## Fix 1: Memory scope triple-nesting across turns

**Files modified:** `metaclaw/api_server.py`

**Root cause:** `derive_memory_scope()` was called on every turn with
`default_scope=_get_memory_scope(session_id)`. On turn 2+, the cached scope
(e.g. `default|session:X`) was passed back in as `default_scope`, and
`derive_memory_scope` appended `|session:X` again, growing indefinitely.

**Fix:** Reuse cached scope for existing sessions; only call
`derive_memory_scope` on the first turn or when explicit overrides are
provided. When deriving fresh, use `memory_manager.scope_id` as default
instead of the previously derived (and potentially nested) scope.

---

## Fix 2: Memory injection gated on `skill_manager`

**Files modified:** `metaclaw/api_server.py`

**Root cause:** Both `_inject_memory` and `_inject_skills` were inside a
single `if self.skill_manager and turn_type == "main":` block. When skills
were disabled (`skill_manager=None`), memory injection was also skipped.

**Fix:** Separated the conditions:
```python
if turn_type == "main":
    if self.memory_manager:
        messages = await self._inject_memory(messages, scope_id=...)
    if self.skill_manager:
        messages = self._inject_skills(messages)
```

---

## Fix 3: RL mode never buffers turns for memory extraction

**Files modified:** `metaclaw/api_server.py`

**Root cause:** The turn buffering code in the tokenizer path (RL mode) was
guarded by `self.config.mode == "skills_only"`, preventing turns from being
buffered for memory extraction in RL mode.

**Fix:** Removed the mode gate. Turns are now buffered for memory extraction
in all modes when `self.memory_manager is not None`.

---

## Fix 4: Turns lost when skill evolution triggers mid-session

**Files modified:** `metaclaw/api_server.py`

**Root cause:** When the skill evolution turn buffer reached
`evolution_every_n` turns, the buffer was popped (destructively) and passed
to skill evolution. If `session_done` fired later, the popped turns were no
longer available for memory ingestion.

**Fix:** Introduced a dedicated `_session_memory_turns` buffer that is
independent of the skill evolution `_session_turns` buffer:
- `_session_turns`: used for skill evolution, cleared on evolution trigger
- `_session_memory_turns`: used for memory ingestion, only cleared on
  `session_done`

Both buffers receive the same turn data, but lifecycle management is
independent.

---

## Fix 5: Cross-session memory retrieval is scope-locked

**Files modified:** `metaclaw/memory/scope.py`, `metaclaw/api_server.py`

**Root cause:** Each session got a unique scope like
`default|session:session_001`, and memory retrieval filtered strictly by
`scope_id`. Memories from session_001 could never be found in session_002.

**Fix:** Two-part fix:
1. Added `base_scope()` utility in `scope.py` that strips `|session:...`
   suffixes (e.g., `default|session:X` → `default`).
2. Both `_ingest_memory_for_session` and `_inject_memory` now use
   `base_scope()` to derive the storage/retrieval scope. Memories are stored
   under the shared base scope, making them accessible across all sessions.
   The `source_session_id` field on `MemoryUnit` still tracks which session
   produced each memory.

---

## Fix 6: Memory injection blocks async event loop

**Files modified:** `metaclaw/api_server.py`

**Root cause:** `_inject_memory()` was synchronous but called from the async
request handler. It performed blocking SQLite queries via
`retrieve_for_prompt()`, blocking the entire event loop.

**Fix:** Made `_inject_memory` an `async` method and wrapped the blocking
`retrieve_for_prompt()` call in `asyncio.to_thread()`:
```python
memories = await asyncio.to_thread(
    self.memory_manager.retrieve_for_prompt, task_desc, scope_id=retrieval_scope,
)
```

---

## Fix 7: Missing `@pytest.mark.asyncio` in live tinker tests

**Files modified:** `tests/test_v03_live_tinker.py`

**Root cause:** Three `async def test_*` functions lacked the
`@pytest.mark.asyncio` decorator, causing pytest to fail with "async def
functions are not natively supported".

**Fix:** Added `import pytest` and `@pytest.mark.asyncio` decorator to:
- `test_live_tinker_training` (line 315)
- `test_live_tinker_maml_multistep` (line 391)
- `test_outer_loop_with_tinker` (line 495)
