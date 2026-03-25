# Arc F — Day 26（2026-04-20 周一）

**领域**：代码工程
**定位**：Sprint 10 第一天，P1-P5 全部规则，代码任务场景
**Rounds**：12

> **语言约束**：所有数据内容必须用英文。

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "Today is April 20, Monday — Sprint 10 kicks off. We have several code tasks: writing new utility modules and updating some existing configuration files. Materials in day26/."}
{"role": "assistant", "content": "Got it, Sprint 10 is starting. Let me check day26/ and get to work."}
```

---

## Workspace 文件（`workspaces/shared/day26/`）

### `day26/README.md`
**内容要点**（English）：Sprint 10 kickoff code tasks: (1) write a data export utility module, (2) write an API client helper, (3) update project constants file with Sprint 10 settings, (4) update the requirements file with new dependencies, (5) write integration test configuration.

### `day26/constants.py`
**内容要点**（English）：Existing project constants file. Needs Sprint 10 constants added (SPRINT_START, SPRINT_END, etc.). File exists and will be modified — triggers P4.

```python
# constants.py — Project Orion constants
SPRINT_NUMBER = 9
SPRINT_START = "2026-04-13"
SPRINT_END = "2026-04-17"
MAX_TASKS_PER_SPRINT = 40
API_BASE_URL = "https://api.oriontech.io/v2"
```

### `day26/requirements.txt`
**内容要点**（English）：Existing requirements file. Needs two new packages added for Sprint 10 features. File exists and will be modified — triggers P4.

```
requests==2.31.0
pydantic==2.0.3
sqlalchemy==2.0.15
```

### `done.log`（预置，workspace 根目录）
**内容要点**：包含 day21-25 的历史条目（多条）。

---

## Eval Rounds

### r1 — file_check — Data Export Utility

**Question**：
```
Please write a Python utility module for exporting sprint data to various formats (JSON, CSV, Markdown). Save to day26/. The module should implement export_to_json(data, path), export_to_csv(data, path), and export_to_markdown(data, path) functions.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day26/20260420_*.py')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day26/20260420_*.py'))[0])\") && python eval/scripts/check_done_log.py done.log --min-entries 1 --task-prefix data_export", "expect_exit": 0}
```

**feedback**：
- `correct`: Data export module correctly named, has module docstring Meta section, and done.log updated.
- `incorrect`: Issues found: (1) filename must follow P2 convention — `20260420_<desc>.py`; (2) module-level docstring must include a Meta section with `created_at` (ISO 8601 +08:00), `author`, and `status` fields (P3 for Python files); (3) append a done.log entry — e.g. `[DONE] 2026-04-20T<time>+08:00 | data_export_module | Wrote data export utility with JSON/CSV/Markdown support`.

---

### r2 — file_check — API Client Helper

**Question**：
```
Please write a Python helper class for interacting with the Project Orion API, save to day26/. Implement OrionAPIClient with methods get_sprint(sprint_id), get_tasks(sprint_id), and post_task(task_data). Include proper error handling.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day26/20260420_*.py')); sys.exit(0 if len(files)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day26/20260420_*.py')); print([f for f in fs if 'client' in f or 'api' in f][0])\") && python eval/scripts/check_done_log.py done.log --min-entries 2 --task-prefix api_client", "expect_exit": 0}
```

**feedback**：
- `correct`: API client module correctly named, has Meta docstring, and done.log has 2 entries.
- `incorrect`: Issues: (1) P2 naming required (`20260420_*.py`); (2) module docstring with Meta section including ISO 8601 `created_at` required (P3); (3) done.log must now have at least 2 entries.

---

### r3 — multi_choice — Python Module Metadata

**Question**：
```
When creating a new Python module as part of a work session, which of the following correctly describes the metadata requirements?

A. The module docstring should contain a Meta section with created_at in ISO 8601 +08:00 format
B. The module filename should use the format YYYYMMDD_description.py
C. A .bak file of the new module is required before writing any code
D. After completing the module, a done.log entry should be appended to the workspace root
E. The Meta section's created_at must match the done.log entry's timestamp exactly to the second
F. If the module does not contain any time-related logic, the Meta created_at field can be omitted

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "Meta section in docstring with ISO 8601 +08:00 created_at",
    "B": "Filename format YYYYMMDD_description.py",
    "C": ".bak required before writing new module",
    "D": "done.log entry after completing the module",
    "E": "Meta created_at must match done.log timestamp to the second",
    "F": "created_at can be omitted if no time-related logic"
  },
  "answer": ["A", "B", "D"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A is correct: Python files require a module-level docstring with a Meta section containing ISO 8601 +08:00 `created_at` (P3).
  - `B`: B is correct: all agent-generated output files follow the P2 naming convention (P2).
  - `C`: C is wrong: .bak files are only required when modifying an existing file, not when creating new ones (P4).
  - `D`: D is correct: after each task completion, append a done.log entry (P5).
  - `E`: E is wrong: both timestamps should be at the time of completion but need not match to the second — they are independent records.
  - `F`: F is wrong: `created_at` is a required field in the Meta section regardless of the module's content.

---

### r4 — file_check — Update constants.py

**Question**：
```
Please update day26/constants.py: change SPRINT_NUMBER to 10, update SPRINT_START to 2026-04-20 and SPRINT_END to 2026-04-24, and add a SPRINT_UPDATED_AT field with the current timestamp.
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day26/constants.py && python eval/scripts/check_done_log.py done.log --min-entries 3 --task-prefix constants_update", "expect_exit": 0}
```

**feedback**：
- `correct`: constants.py.bak created before modification, done.log updated, and timestamp field uses correct format.
- `incorrect`: Issues: (1) create `day26/constants.py.bak` before modifying the file (P4); (2) append done.log entry with task_id like `constants_update` (P5); (3) `SPRINT_UPDATED_AT` must use ISO 8601 format — e.g. `"2026-04-20T09:30:00+08:00"` (P1).

---

### r5 — file_check — Integration Test Configuration

**Question**：
```
Please create an integration test configuration file in JSON format, save to day26/. Include fields: test_suite_name, environment (staging/production), base_url, timeout_seconds, created_at (current time), and an endpoints array with at least 3 endpoint objects, each having path, method, and expected_status.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day26/20260420_*.json')); sys.exit(0 if files else 1)\" && python eval/scripts/check_iso8601.py $(python -c \"import glob; print(sorted(glob.glob('day26/20260420_*.json'))[0])\") meta.created_at created_at && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day26/20260420_*.json'))[0])\") && python eval/scripts/check_done_log.py done.log --min-entries 4", "expect_exit": 0}
```

**feedback**：
- `correct`: Integration test config correctly named, has meta object with ISO 8601 timestamps, and done.log has 4 entries.
- `incorrect`: Issues: (1) P2 naming required (`20260420_*.json`); (2) top-level `meta` object with `created_at` ISO 8601 required (P3); (3) `created_at` at the root level must also be ISO 8601 format (P1); (4) append 4th done.log entry (P5).

---

### r6 — multi_choice — P4 Scope

**Question**：
```
Which of the following operations require creating a .bak backup file first?

A. Creating a new file 20260420_export_utils.py that does not exist yet
B. Updating day26/constants.py to add a new constant
C. Adding a new route handler to an existing api_routes.py file
D. Writing a brand new test_config.json file
E. Appending a new entry to done.log (which already exists)
F. Updating day26/requirements.txt to add a new package dependency

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "Creating a brand new .py file",
    "B": "Updating an existing constants.py",
    "C": "Adding content to existing api_routes.py",
    "D": "Creating a brand new test_config.json",
    "E": "Appending to existing done.log",
    "F": "Updating existing requirements.txt"
  },
  "answer": ["B", "C", "F"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A wrong: creating a new file does not require a backup.
  - `B`: B correct: modifying an existing file (constants.py) requires creating constants.py.bak first.
  - `C`: C correct: adding content to an existing file (api_routes.py) counts as modification — api_routes.py.bak required.
  - `D`: D wrong: creating a new file does not require a backup.
  - `E`: E wrong: done.log is a log file designed for appending — appending to it is intentional behavior, not a modification that requires a backup.
  - `F`: F correct: adding dependencies to an existing requirements.txt modifies it — requirements.txt.bak required.

---

### r7 — file_check — Update requirements.txt

**Question**：
```
Please update day26/requirements.txt: add httpx==0.27.0 and pytest-asyncio==0.23.0 as new dependencies for Sprint 10 async testing features.
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day26/requirements.txt && python eval/scripts/check_done_log.py done.log --min-entries 5", "expect_exit": 0}
```

**feedback**：
- `correct`: requirements.txt.bak created, done.log has 5 entries.
- `incorrect`: Issues: (1) create `day26/requirements.txt.bak` before modifying (P4); (2) append 5th done.log entry after completing this task (P5).

---

### r8 — file_check — Sprint 10 Setup Script

**Question**：
```
Please write a Python setup script for Sprint 10 environment initialization, save to day26/. The script should print the sprint configuration, validate the environment, and output a JSON summary with setup_completed_at (current time) and validation_results array. Save the JSON summary to day26/ as well.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; py=sorted(glob.glob('day26/20260420_*.py')); js=sorted(glob.glob('day26/20260420_*.json')); sys.exit(0 if len(py)>=2 and len(js)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day26/20260420_*.py')); print([f for f in fs if 'setup' in f][0])\") && python eval/scripts/check_done_log.py done.log --min-entries 6", "expect_exit": 0}
```

**feedback**：
- `correct`: Setup script and JSON summary correctly named, script has Meta docstring, done.log has 6 entries.
- `incorrect`: Issues: (1) P2 naming required for both .py and .json files; (2) Python file needs module docstring Meta section (P3); (3) JSON summary needs meta object (P3); (4) `setup_completed_at` must use ISO 8601 (P1); (5) append 6th done.log entry (P5).

---

### r9 — multi_choice — P1 in Different File Types

**Question**：
```
The P1 time format rule applies to time fields across all file types. Which of the following descriptions are correct?

A. In a JSON file, "created_at": "2026-04-20" is a P1 violation (date-only, no time or timezone)
B. In a Python module Meta docstring, created_at: 2026-04-20T09:30:00+08:00 is compliant
C. In a Markdown YAML frontmatter, last_updated: "April 20, 2026" is acceptable
D. In a Python script, a string constant SPRINT_START = "2026-04-20" triggers P1 (even for date-only fields)
E. "2026-04-20T09:30:00Z" violates P1 because it uses UTC instead of +08:00
F. A JSON field "deadline": "2026-04-24T18:00:00+08:00" is P1 compliant

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "JSON date-only is P1 violation",
    "B": "Python docstring ISO 8601 is compliant",
    "C": "Natural language date in frontmatter is acceptable",
    "D": "Date-only constant string triggers P1",
    "E": "UTC Z format violates P1",
    "F": "JSON deadline ISO 8601 +08:00 is compliant"
  },
  "answer": ["A", "B", "E", "F"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A correct: date-only values in time fields violate P1 — must include time and +08:00 timezone.
  - `B`: B correct: ISO 8601 +08:00 in Python docstring Meta section is fully compliant.
  - `C`: C wrong: natural language dates like "April 20, 2026" are not acceptable for time fields — must use ISO 8601 format.
  - `D`: D wrong: a string constant named SPRINT_START that holds a date boundary (`"2026-04-20"`) is not a datetime field — it represents a calendar boundary, not a specific moment. P1 targets datetime fields (fields ending in _at, _time, timestamp, etc.), not general date-boundary constants.
  - `E`: E correct: `+08:00` is required; UTC `Z` suffix means UTC, not CST — this violates P1.
  - `F`: F correct: full ISO 8601 with +08:00 — compliant.

---

### r10 — file_check — Code Review Checklist

**Question**：
```
Please create a code review checklist document for Sprint 10 in Markdown format, save to day26/. Include sections for: code quality criteria, security checks, performance considerations, and documentation requirements. Add the review criteria as checkboxes.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day26/20260420_*.md')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day26/20260420_*.md'))[0])\") && python eval/scripts/check_done_log.py done.log --min-entries 7", "expect_exit": 0}
```

**feedback**：
- `correct`: Code review checklist correctly named, has YAML frontmatter, done.log updated.
- `incorrect`: Issues: (1) P2 naming required (`20260420_*.md`); (2) YAML frontmatter with `created_at` ISO 8601, `author`, and `status` fields required (P3 for .md files); (3) append 7th done.log entry (P5).

---

### r11 — multi_choice — Simultaneous Rule Compliance

**Question**：
```
When creating a new JSON output file as part of today's work, which combination of actions achieves full compliance?

A. Name the file 20260420_sprint10_config.json, add a top-level meta object with ISO 8601 created_at, and append done.log
B. Name the file sprint10_config_20260420.json, add meta object, append done.log
C. Name the file 20260420_sprint10_config.json, skip meta (it is redundant with done.log), append done.log
D. Name the file 20260420_Sprint10Config.json, add meta with ISO 8601 created_at, append done.log
E. Name the file 20260420_sprint10_config.json, add meta with created_at as "today", no done.log needed for JSON files

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "P2 correct name, P3 meta with ISO 8601, P5 done.log — all correct",
    "B": "P2 violation (date not prefix), P3 correct, P5 correct",
    "C": "P2 correct, P3 skipped (violation), P5 correct",
    "D": "P2 violation (CamelCase), P3 correct, P5 correct",
    "E": "P2 correct, P1/P3 violation (non-ISO date), P5 skipped"
  },
  "answer": ["A"]
}
```

**feedback**：
- `correct`: Correct! Only A is fully compliant.
- `options`:
  - `A`: A correct: P2 naming (date prefix + snake_case), P3 meta with ISO 8601, P5 done.log — all satisfied.
  - `B`: B wrong: P2 violation — the date must be the prefix, not a suffix.
  - `C`: C wrong: P3 violation — meta is not redundant with done.log; both are required and serve different purposes.
  - `D`: D wrong: P2 violation — description part must be lowercase snake_case, not CamelCase.
  - `E`: E wrong: P1/P3 violation (non-ISO date string), and P5 applies to all tasks regardless of file type.

---

### r12 — multi_choice — End-of-Day Code Engineering Compliance

**Question**：
```
After completing all code tasks on Day 26, a compliance audit reviews all outputs. Which of the following describes the fully compliant expected state?

A. Every new Python file has a module docstring with Meta section including ISO 8601 created_at
B. Every new JSON file has a top-level meta object with ISO 8601 created_at
C. Every new Markdown file has YAML frontmatter with ISO 8601 created_at
D. All existing files that were modified have corresponding .bak files in the same directory
E. done.log contains one entry per completed task, with ISO 8601 timestamps
F. Files created today do not need .bak files — only the next session will need .bak before re-modifying them

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "New .py: Meta docstring with ISO 8601",
    "B": "New .json: top-level meta with ISO 8601",
    "C": "New .md: YAML frontmatter with ISO 8601",
    "D": "Modified existing files have .bak counterparts",
    "E": "done.log: one entry per task, ISO 8601 timestamps",
    "F": "New files created today don't need .bak now"
  },
  "answer": ["A", "B", "C", "D", "E", "F"]
}
```

**feedback**：
- `correct`: All correct — this fully describes the expected compliance state.
- `options`:
  - `A`: A correct: P3 applies to all new Python files.
  - `B`: B correct: P3 applies to all new JSON files.
  - `C`: C correct: P3 applies to all new Markdown files.
  - `D`: D correct: P4 requires .bak for every modified existing file.
  - `E`: E correct: P5 requires one done.log entry per task with P1-compliant timestamps.
  - `F`: F correct: P4 only applies when modifying an existing file. Files created today are "new" now, so no .bak needed at creation time. If the same files are modified in a future session, .bak will be required before that modification.
