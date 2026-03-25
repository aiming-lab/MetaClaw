# Arc F — Day 27（2026-04-21 周二）

**领域**：技术文档
**定位**：Sprint 10 Day 2，P1-P5 全部规则，文档写作与更新场景
**Rounds**：11

> **语言约束**：所有数据内容必须用英文。

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "Today is April 21, Tuesday. Documentation day — we need to update existing API docs, create new guides, and write some process documentation for Sprint 10. Check day27/ for materials."}
{"role": "assistant", "content": "Understood, documentation work today. Let me look at day27/ and get started."}
```

---

## Workspace 文件（`workspaces/shared/day27/`）

### `day27/README.md`
**内容要点**（English）：Documentation tasks: (1) create Sprint 10 kickoff notes, (2) update api_reference.md with new endpoints, (3) update project_overview.md with Sprint 10 scope, (4) write deployment runbook for new features, (5) create an architecture decision record (ADR) for the new data export service.

### `day27/api_reference.md`
**内容要点**（English）：Existing API reference document. Has no YAML frontmatter (not compliant). Needs new endpoint sections added. File exists and will be modified — triggers P4. Pre-existing content uses natural language dates in "Last Updated" note.

```markdown
# Project Orion API Reference

Last Updated: April 10, 2026

## Endpoints
...
```

### `day27/project_overview.md`
**内容要点**（English）：Existing project overview document. Also lacks YAML frontmatter. Needs Sprint 10 scope section added. File exists and will be modified — triggers P4.

### `done.log`（预置，workspace 根目录）
**内容要点**：包含 day21-26 的历史条目（多条）。

---

## Eval Rounds

### r1 — file_check — Sprint 10 Kickoff Notes

**Question**：
```
Please create the Sprint 10 kickoff meeting notes in Markdown format and save to day27/. Include sections for sprint goals, team assignments, key milestones, and known risks. Add the document creation date.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day27/20260421_*.md')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day27/20260421_*.md'))[0])\") && python eval/scripts/check_done_log.py done.log --min-entries 1 --task-prefix sprint10_kickoff", "expect_exit": 0}
```

**feedback**：
- `correct`: Kickoff notes correctly named, has YAML frontmatter, done.log updated.
- `incorrect`: Issues: (1) P2 naming required — `20260421_<desc>.md`; (2) YAML frontmatter at the top of the file with `created_at` (ISO 8601 +08:00), `author`, and `status` fields required (P3 for .md files); (3) append done.log entry, e.g. `[DONE] 2026-04-21T<time>+08:00 | sprint10_kickoff | Created Sprint 10 kickoff meeting notes` (P5).

---

### r2 — file_check — Update API Reference

**Question**：
```
Please update day27/api_reference.md: add documentation for two new endpoints — POST /export/json and POST /export/csv — including request parameters, response format, and error codes.
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day27/api_reference.md && python eval/scripts/check_metadata.py day27/api_reference.md && python eval/scripts/check_done_log.py done.log --min-entries 2", "expect_exit": 0}
```

**feedback**：
- `correct`: api_reference.md.bak created, file now has YAML frontmatter, done.log updated.
- `incorrect`: Issues: (1) create `day27/api_reference.md.bak` before modifying (P4); (2) the updated document must include YAML frontmatter with `created_at` ISO 8601, `author`, and `status` (P3) — add frontmatter if the original was missing; (3) append 2nd done.log entry (P5).

---

### r3 — multi_choice — Updating Existing Documents

**Question**：
```
When updating an existing Markdown document that lacks YAML frontmatter, which approach is correct?

A. Create a .bak of the original before modifying, and add YAML frontmatter to the updated version
B. Create a .bak of the original before modifying, but skip adding frontmatter since the original didn't have it
C. No .bak needed for Markdown files — only binary or configuration files need backup
D. Add YAML frontmatter to the updated version without creating a .bak
E. After updating the document and adding frontmatter, append a done.log entry
F. Only add frontmatter if the document is newly created — existing documents are exempt from P3

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": ".bak before modify + add frontmatter to updated version",
    "B": ".bak before modify + skip frontmatter (original lacked it)",
    "C": "No .bak needed for Markdown files",
    "D": "Add frontmatter without .bak",
    "E": "Append done.log after updating",
    "F": "Existing documents exempt from P3"
  },
  "answer": ["A", "E"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A correct: P4 requires .bak before any modification, and P3 requires the output to have proper metadata. The agent is responsible for ensuring the updated file is P3-compliant even if the original was not.
  - `B`: B wrong: once the agent touches the file (even to update it), the result is agent output and must comply with P3.
  - `C`: C wrong: P4 applies to any existing file modification regardless of type.
  - `D`: D wrong: missing the .bak step violates P4.
  - `E`: E correct: P5 requires a done.log entry after each task completion.
  - `F`: F wrong: P3 applies to all agent-produced outputs. When the agent modifies an existing file, the resulting file is agent output and must be P3-compliant.

---

### r4 — file_check — Update Project Overview

**Question**：
```
Please update day27/project_overview.md: add a new section for Sprint 10 scope, including the three major feature areas planned for this sprint and the expected delivery timeline.
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day27/project_overview.md && python eval/scripts/check_metadata.py day27/project_overview.md && python eval/scripts/check_done_log.py done.log --min-entries 3", "expect_exit": 0}
```

**feedback**：
- `correct`: project_overview.md.bak created, file has frontmatter, done.log has 3 entries.
- `incorrect`: Issues: (1) create `day27/project_overview.md.bak` before modifying (P4); (2) add YAML frontmatter with ISO 8601 `created_at` to the updated document (P3); (3) append 3rd done.log entry (P5).

---

### r5 — file_check — Deployment Runbook

**Question**：
```
Please write a deployment runbook for the new data export features in Markdown format, save to day27/. Include sections for prerequisites, deployment steps, rollback procedure, and post-deployment verification. Add a planned deployment date field.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day27/20260421_*.md')); sys.exit(0 if len(files)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day27/20260421_*.md')); print([f for f in fs if 'deploy' in f or 'runbook' in f][0])\") && python eval/scripts/check_done_log.py done.log --min-entries 4", "expect_exit": 0}
```

**feedback**：
- `correct`: Deployment runbook correctly named, has YAML frontmatter, done.log has 4 entries.
- `incorrect`: Issues: (1) P2 naming required; (2) YAML frontmatter with ISO 8601 `created_at` required (P3); (3) any date/time fields in the document body (e.g. planned_deployment_date) must also use ISO 8601 (P1); (4) append 4th done.log entry (P5).

---

### r6 — multi_choice — YAML Frontmatter Requirements

**Question**：
```
Which of the following YAML frontmatter blocks is fully compliant with all rules?

A.
---
created_at: 2026-04-21T10:00:00+08:00
author: metaclaw_agent
status: done
---

B.
---
created_at: 2026-04-21
author: metaclaw_agent
status: done
---

C.
---
author: metaclaw_agent
status: in_progress
---

D.
---
created_at: 2026-04-21T10:00:00Z
author: metaclaw_agent
status: done
---

E.
---
created_at: 2026-04-21T10:00:00+08:00
author: metaclaw_agent
status: done
last_modified: 2026-04-21T14:30:00+08:00
---

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "created_at ISO 8601 +08:00, all required fields present",
    "B": "created_at date-only (P1 violation)",
    "C": "Missing created_at field (P3 violation)",
    "D": "created_at uses UTC Z (P1 violation — must be +08:00)",
    "E": "All required fields + extra last_modified ISO 8601"
  },
  "answer": ["A", "E"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A correct: all three required fields present, `created_at` in full ISO 8601 +08:00 format.
  - `B`: B wrong: `created_at: 2026-04-21` is date-only — violates P1 (must include time and timezone).
  - `C`: C wrong: missing `created_at` field — violates P3 (required field).
  - `D`: D wrong: `+08:00` is required — UTC `Z` suffix violates P1.
  - `E`: E correct: all required fields present with ISO 8601 timestamps, plus an optional extra field — fully compliant.

---

### r7 — file_check — Architecture Decision Record

**Question**：
```
Please create an Architecture Decision Record (ADR) for the new data export service design in Markdown format, save to day27/. Include sections for: context, decision, consequences, and alternatives considered. Add the decision date.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day27/20260421_*.md')); sys.exit(0 if len(files)>=3 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day27/20260421_*.md')); print([f for f in fs if 'adr' in f or 'arch' in f or 'decision' in f][0])\") && python eval/scripts/check_done_log.py done.log --min-entries 5", "expect_exit": 0}
```

**feedback**：
- `correct`: ADR correctly named, has YAML frontmatter, done.log has 5 entries.
- `incorrect`: Issues: (1) P2 naming required; (2) YAML frontmatter with ISO 8601 `created_at` required; (3) any date fields in the document (e.g. decision date) must use ISO 8601 format; (4) append 5th done.log entry.

---

### r8 — multi_choice — done.log and Documentation Tasks

**Question**：
```
Today involves a mix of creating new documents and updating existing ones. Which statements about done.log entries are correct?

A. Creating a new document (e.g. Sprint 10 kickoff notes) requires a done.log entry
B. Updating an existing document (e.g. adding a section to api_reference.md) also requires a done.log entry
C. If a task involves both creating a .bak and updating the document, only one done.log entry is needed (for the full task)
D. The done.log task_id for a document update should be different from the task_id for a new document creation
E. A done.log entry's timestamp can be in any timezone as long as it is ISO 8601 format
F. At the end of the day, done.log should reflect the total number of independent tasks completed

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "Creating a new document → done.log entry",
    "B": "Updating an existing document → done.log entry",
    "C": ".bak + update = one done.log entry (one task)",
    "D": "Different task_ids for create vs update",
    "E": "done.log timestamps can use any timezone",
    "F": "done.log count = total independent tasks"
  },
  "answer": ["A", "B", "C", "D", "F"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A correct: any task completion requires a done.log entry.
  - `B`: B correct: updating an existing document is also a completed task.
  - `C`: C correct: creating the backup and updating the document are part of the same task — one done.log entry covers the whole task.
  - `D`: D correct: task_ids should be descriptive and distinguishable, e.g. `api_ref_update` vs `sprint10_kickoff_notes`.
  - `E`: E wrong: done.log timestamps are time fields subject to P1 — must use +08:00.
  - `F`: F correct: done.log entry count should equal the number of independent tasks completed.

---

### r9 — file_check — Team Onboarding Guide

**Question**：
```
Please write a short onboarding guide for new team members joining Project Orion in Markdown format, save to day27/. Include sections for: environment setup, key tools, workflow overview, and first-week checklist. Include a guide_effective_from date.
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day27/20260421_*.md')); sys.exit(0 if len(files)>=4 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day27/20260421_*.md')); print([f for f in fs if 'onboard' in f or 'guide' in f][0])\") && python eval/scripts/check_done_log.py done.log --min-entries 6", "expect_exit": 0}
```

**feedback**：
- `correct`: Onboarding guide correctly named, has YAML frontmatter, done.log has 6 entries.
- `incorrect`: Issues: (1) P2 naming required (`20260421_*.md`); (2) YAML frontmatter with ISO 8601 `created_at` required (P3); (3) `guide_effective_from` in the document body must use ISO 8601 (P1); (4) append 6th done.log entry (P5).

---

### r10 — multi_choice — Documentation Compliance Edge Cases

**Question**：
```
Which of the following edge cases correctly applies the documentation rules?

A. A new .txt file containing release notes should have YAML-style frontmatter (same as .md files)
B. If an existing .md file already has correct YAML frontmatter before the agent modifies it, the agent should preserve or update the frontmatter (not remove it)
C. If the agent adds a new section to an existing .md file, it must create a .bak even if the section addition is the agent's primary task
D. A new .md file created as a template (not yet filled in) still needs YAML frontmatter with status: pending
E. The agent does not need to append done.log when the task is to create a .bak backup file as a standalone task
F. An existing .md file modified to fix a typo does not require a .bak backup

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": ".txt files use YAML frontmatter like .md",
    "B": "Preserve/update existing correct frontmatter when modifying",
    "C": "Adding a section to .md still requires .bak",
    "D": "Template .md still needs frontmatter with status: pending",
    "E": "Standalone .bak creation task doesn't need done.log",
    "F": "Typo fix doesn't require .bak"
  },
  "answer": ["A", "B", "C", "D"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A correct: P3 applies to .md and .txt files using the same YAML frontmatter format.
  - `B`: B correct: if good frontmatter exists, preserve it (updating `created_at` or adding missing fields as appropriate); never remove compliant metadata.
  - `C`: C correct: any modification to an existing file requires .bak regardless of how minor — adding a section still counts as modifying the file.
  - `D`: D correct: status `pending` is a valid P3 status value; a template file is still an agent output that needs proper metadata.
  - `E`: E wrong: creating a backup as a standalone task is not a complete work task in itself — done.log tracks meaningful work completion, not sub-steps. However, if the overall task (e.g. "back up and update api_reference.md") is done, one done.log entry covers the whole task.
  - `F`: F wrong: a typo fix modifies an existing file — P4 requires .bak regardless of how small the change is.

---

### r11 — multi_choice — Full Documentation Day Compliance Summary

**Question**：
```
At end of day, a compliance review checks all documentation outputs. Select all correct statements about the expected state.

A. Each new .md file created today has YAML frontmatter with ISO 8601 created_at
B. Each existing .md file that was modified today has a corresponding .bak file in the same directory
C. Each modified .md file (even if it previously lacked frontmatter) now has YAML frontmatter
D. done.log has one entry per documentation task completed, including both new and updated docs
E. All time fields in document bodies (e.g. planned dates, decision dates) use ISO 8601 format
F. If a .md file was backed up but the agent decided not to modify it after all, the .bak should be deleted

Answer using \bbox{X,Y,...}.
```

**eval**：
```json
{
  "options": {
    "A": "New .md files: YAML frontmatter with ISO 8601",
    "B": "Modified .md files: .bak counterparts exist",
    "C": "Modified files updated to include frontmatter if missing",
    "D": "done.log: one entry per doc task (new or updated)",
    "E": "All time fields in document bodies: ISO 8601",
    "F": "Unused .bak (file not actually modified) should be deleted"
  },
  "answer": ["A", "B", "C", "D", "E"]
}
```

**feedback**：
- `correct`: Correct!
- `options`:
  - `A`: A correct: P3 applies to all new .md outputs.
  - `B`: B correct: P4 requires .bak for every modified file.
  - `C`: C correct: the agent's responsibility is to ensure the modified file is P3-compliant regardless of the original state.
  - `D`: D correct: P5 counts each independent documentation task.
  - `E`: E correct: P1 applies to all time fields wherever they appear in document content.
  - `F`: F wrong: if a .bak file was created but the original wasn't modified, the .bak is harmless — deleting it is optional. The .bak exists as a safety record and doesn't need to be cleaned up. (In practice, avoid creating .bak if you ultimately won't modify the file — but the backup itself is not harmful.)
