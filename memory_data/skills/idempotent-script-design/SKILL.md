---
name: idempotent-script-design
description: "Use this skill when writing scripts, cron jobs, data pipelines, or database migrations that may run more than once. Apply check-before-create guards, upsert patterns, and atomic writes so that re-running the script never causes duplicate data, partial writes, or crashes."
---

# Idempotent Script Design

An idempotent operation produces the same result whether run once or ten times.

**Techniques:**
- **Check before create:** `CREATE TABLE IF NOT EXISTS`, `mkdir -p`, check file existence before writing.
- **Upsert instead of insert:** Use `INSERT ... ON CONFLICT DO UPDATE` in SQL.
- **Atomic writes:** Write to a temp file, then rename — prevents corrupt partial output.
- **Track progress:** Write a completion marker or checkpoint so reruns skip done work.

**Testing idempotency:** Run your script twice on the same input and verify the output is identical.

**Anti-patterns:**
- Appending to a file without checking if the data is already there.
- Inserting rows without checking for duplicates.
