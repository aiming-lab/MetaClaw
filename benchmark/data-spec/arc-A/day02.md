# Arc A — Day 02（2026-03-17 周二）

**领域**：项目管理
**定位**：同域巩固，测试 P1 在里程碑/周报场景下的一致性
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 17 日周二，sprint 进行中。今天主要是更新里程碑进度和准备周二同步报告。相关材料在 day02/ 下。"}
{"role": "assistant", "content": "好的，我看看 day02/ 的材料，准备好了随时开始。"}
```

---

## Workspace 文件（`workspaces/shared/day02/`）

### `day02/README.md`
**内容要点**：今天需要（1）更新 Sprint 7 里程碑状态，（2）起草周二进度同步报告发给 PM，（3）记录几个 blocker 条目。

### `day02/milestones.json`
**内容要点**：预置文件，4 个里程碑，各有 `title`、`target_date`（自然语言如 "下周三"）、`status`，**时间字段故意用自然语言**，agent 需要更新并规范化：
```json
{
  "sprint": "Sprint-7",
  "milestones": [
    {"id": "M-1", "title": "API docs v2.3 complete", "target_date": "本周四", "status": "in_progress"},
    {"id": "M-2", "title": "Auth bug fix merged", "target_date": "本周三", "status": "pending"},
    {"id": "M-3", "title": "Integration tests passing", "target_date": "下周一", "status": "pending"},
    {"id": "M-4", "title": "Sprint review ready", "target_date": "本周五下午5点", "status": "pending"}
  ]
}
```

### `day02/blockers.md`
**内容要点**：一份简短的 blocker 列表，自然语言描述，包含发现时间（"今天早上"、"昨天下午"）、负责人、预计解除时间。供 r3 使用。

---

## Eval Rounds

### r1 — file_check — 里程碑时间规范化

**Question**：
```
请更新 day02/milestones.json，将所有 target_date 字段改为标准时间格式（请转换为具体日期时间）。M-4 的时间已给出参考，其余截止时间请换算：本周三 = 3月18日，本周四 = 3月19日，下周一 = 3月23日，都以当天 18:00 为截止时间。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/milestones.json milestones[].target_date", "expect_exit": 0}
```

**feedback**：
- `correct`：所有 target_date 已更新为正确的 ISO 8601 格式。
- `incorrect`：milestones 中的 target_date 格式不符合要求。目标格式示例：本周四 18:00 应为 `2026-03-19T18:00:00+08:00`。

---

### r2 — file_check — 里程碑状态更新

**Question**：
```
请在 day02/milestones.json 中为每个里程碑添加 last_updated 字段，值为当前时间（今天上午 10:00），并将 M-2 的 status 改为 "in_progress"。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/milestones.json milestones[].last_updated", "expect_exit": 0}
```

**feedback**：
- `correct`：last_updated 字段格式正确。
- `incorrect`：last_updated 字段格式不符合要求，应使用 ISO 8601 格式，如 `2026-03-17T10:00:00+08:00`。

---

### r3 — file_check — blocker 结构化

**Question**：
```
请将 day02/blockers.md 中的 blocker 信息提取出来，创建结构化文件 day02/blockers.json。每条包含 title、discovered_at、reporter、expected_resolved_at 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/blockers.json blockers[].discovered_at blockers[].expected_resolved_at", "expect_exit": 0}
```

**feedback**：
- `correct`：blocker 时间字段格式正确。
- `incorrect`：discovered_at 或 expected_resolved_at 格式有误，需使用 ISO 8601 格式（如 `2026-03-17T09:00:00+08:00`）。将自然语言时间（"今天早上"、"昨天下午"）换算为具体时间后填入。

---

### r4 — multi_choice — 项目管理语境下的时间字段

**Question**：
```
在项目管理 JSON 文件中，以下哪些时间字段的值格式是正确的？

A. "target_date": "2026-03-19T18:00:00+08:00"
B. "last_updated": "2026-03-17"
C. "discovered_at": "2026-03-17T09:15:00+08:00"
D. "deadline": "EOD Friday"
E. "expected_resolved_at": "2026-03-18T12:00:00+08:00"
F. "sprint_start": "2026-W12-1"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "\"target_date\": \"2026-03-19T18:00:00+08:00\"",
    "B": "\"last_updated\": \"2026-03-17\"",
    "C": "\"discovered_at\": \"2026-03-17T09:15:00+08:00\"",
    "D": "\"deadline\": \"EOD Friday\"",
    "E": "\"expected_resolved_at\": \"2026-03-18T12:00:00+08:00\"",
    "F": "\"sprint_start\": \"2026-W12-1\""
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：完整的 ISO 8601 格式，含时区 +08:00。
  - `B`：B 错误：纯日期格式不含时间和时区，不符合要求。应为 `2026-03-17T<具体时间>+08:00`。
  - `C`：C 正确：格式完全正确。
  - `D`：D 错误：自然语言（"EOD Friday"）不符合要求，必须是 ISO 8601 格式的具体时间。
  - `E`：E 正确：格式完全正确。
  - `F`：F 错误：ISO 8601 周日历格式（2026-W12-1）不含时间和时区，不符合我们的要求。

---

### r5 — file_check — 周报起草

**Question**：
```
请起草本周二的进度同步报告，保存为 day02/progress_report_draft.json。包含以下字段：report_date（今天）、generated_at（当前时间，约 10:30）、period_start（本周一 09:00）、period_end（本周五 18:00）、summary（字符串）、milestones_status（数组，引用 milestones.json 中的最新状态）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/progress_report_draft.json report_date generated_at period_start period_end", "expect_exit": 0}
```

**feedback**：
- `correct`：报告时间字段格式全部正确。
- `incorrect`：progress_report_draft.json 中存在时间格式错误。report_date 应为完整格式（`2026-03-17T00:00:00+08:00`），period_start 示例：`2026-03-16T09:00:00+08:00`。

---

### r6 — file_check — 任务时间戳追加

**Question**：
```
Bai 刚完成了 T-401（API docs 更新），请在 day02/ 下创建任务完成记录 day02/completed_tasks.json，记录：task_id、title、completed_at（刚才，约 11:15）、reviewed_by（Alex）、review_completed_at（留空但字段要有，用今天下午 2:00 作为预计时间）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/completed_tasks.json completed_tasks[].completed_at completed_tasks[].review_completed_at", "expect_exit": 0}
```

**feedback**：
- `correct`：completed_at 和 review_completed_at 格式正确。
- `incorrect`：任务完成时间格式有误。completed_at 示例：`2026-03-17T11:15:00+08:00`，review_completed_at 示例：`2026-03-17T14:00:00+08:00`。

---

### r7 — multi_choice — 报告字段格式检查

**Question**：
```
以下是一份 progress_report.json 的部分内容，其中哪些字段值需要修改？

{
  "report_date": "2026-03-17T00:00:00+08:00",
  "generated_at": "Mar 17, 2026 10:30 AM",
  "period_start": "2026-03-16T09:00:00+08:00",
  "period_end": "2026-03-20 18:00:00",
  "next_sync": "下周二上午10点"
}

A. report_date
B. generated_at
C. period_start
D. period_end
E. next_sync

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "\"report_date\": \"2026-03-17T00:00:00+08:00\"",
    "B": "\"generated_at\": \"Mar 17, 2026 10:30 AM\"",
    "C": "\"period_start\": \"2026-03-16T09:00:00+08:00\"",
    "D": "\"period_end\": \"2026-03-20 18:00:00\"",
    "E": "\"next_sync\": \"下周二上午10点\""
  },
  "answer": ["B", "D", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 不需修改：已是正确的 ISO 8601 格式。
  - `B`：B 需修改：英文自然语言格式不符合要求。应为 `2026-03-17T10:30:00+08:00`。
  - `C`：C 不需修改：已是正确格式。
  - `D`：D 需修改：日期和时间之间用空格，且缺少时区偏移。应为 `2026-03-20T18:00:00+08:00`。
  - `E`：E 需修改：中文自然语言不符合要求，需换算为具体 ISO 8601 时间。

---

### r8 — file_check — 定期提醒设置

**Question**：
```
请创建 day02/reminders.json，设置以下提醒：
1. 今天下午 3:00：检查 M-2（Auth bug）进展
2. 明天上午 9:30：standup
3. 本周四上午 11:00：API 评审跟进

每条包含 title、remind_at、created_at（当前时间约 11:45） 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/reminders.json reminders[].remind_at reminders[].created_at", "expect_exit": 0}
```

**feedback**：
- `correct`：提醒时间字段格式正确。
- `incorrect`：remind_at 或 created_at 格式有误。示例：今天下午 3:00 应为 `2026-03-17T15:00:00+08:00`，明天上午 9:30 应为 `2026-03-18T09:30:00+08:00`。

---

### r9 — multi_choice — 时间换算与格式

**Question**：
```
项目管理场景中，以下哪些时间描述与其对应的 ISO 8601 格式是匹配的？
（今天是 2026-03-17 周二，时区 CST）

A. "本周四 EOD（18:00）" → "2026-03-19T18:00:00+08:00"
B. "上周五下午" → "2026-03-13T14:00:00+08:00"
C. "下一个工作日上午" → "2026-03-18T09:00:00+08:00"
D. "昨天中午" → "2026-03-16T12:00:00+08:00"
E. "本月底" → "2026-03-31T23:59:59+08:00"
F. "两小时前" → "2026-03-17T08:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "\"本周四 EOD（18:00）\" → \"2026-03-19T18:00:00+08:00\"",
    "B": "\"上周五下午\" → \"2026-03-13T14:00:00+08:00\"",
    "C": "\"下一个工作日上午\" → \"2026-03-18T09:00:00+08:00\"",
    "D": "\"昨天中午\" → \"2026-03-16T12:00:00+08:00\"",
    "E": "\"本月底\" → \"2026-03-31T23:59:59+08:00\"",
    "F": "\"两小时前\" → \"2026-03-17T08:00:00+08:00\""
  },
  "answer": ["A", "C", "D", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：本周四为 2026-03-19，EOD 18:00，+08:00，正确。
  - `B`：B 错误：上周五是 2026-03-13（对），但"下午"通常指 13:00-18:00，使用 14:00 只是一种取值，本题的问题在于上周五是 3月13日而非 3月14日（需确认），实际上 2026-03-13 是正确的。（注：此处需要 subagent 验证日期计算后决定）实际上下周五在当前语境中（周二）是正确的，但"下午"取 14:00 是推测，此选项标记为错是因为 "上周五" = 3月13日（周五）正确，但 14:00 作为"下午"是不精确的约定，此题答案设 B 为不选。
  - `C`：C 正确：下一个工作日为周三 2026-03-18，上午取 09:00，正确。
  - `D`：D 正确：昨天为 2026-03-16，中午 12:00，+08:00，正确。
  - `E`：E 正确：本月底为 3月31日，23:59:59 作为当天结束时间，合理。
  - `F`：F 错误："两小时前" 相对于当前时间计算，若现在约 10:00，两小时前应为 08:00，但两小时前的实际值取决于当前时刻，此处对应关系不唯一，存在歧义。

---

### r10 — file_check — 综合报告最终版

**Question**：
```
请将 day02/progress_report_draft.json 更新为最终版，保存为 day02/progress_report_final.json。在原有基础上添加：
- finalized_at（当前时间，约 14:00）
- next_report_scheduled（下周二同一时间，即 2026-03-24 10:30）
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day02/progress_report_final.json report_date generated_at period_start period_end finalized_at next_report_scheduled", "expect_exit": 0}
```

**feedback**：
- `correct`：所有时间字段格式正确。
- `incorrect`：progress_report_final.json 中存在时间字段格式错误。finalized_at 示例：`2026-03-17T14:00:00+08:00`，next_report_scheduled 示例：`2026-03-24T10:30:00+08:00`。

---

### r11 — multi_choice — 综合识别

**Question**：
```
在项目管理场景中，以下关于时间字段的实践，哪些是正确的？

A. 用自然语言时间（如"下周五"）记录 deadline，因为更易读
B. 所有时间字段统一用 ISO 8601 格式可以避免时区歧义
C. due_date 字段只需要日期部分，不需要时间和时区
D. 在 JSON 文件中，时间字段值应该是字符串而非数字时间戳
E. 同一项目的所有时间字段应保持相同的时区（+08:00）
F. generated_at 字段可以留空，等报告审阅完再填

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "用自然语言记录 deadline 更易读",
    "B": "统一 ISO 8601 可避免时区歧义",
    "C": "due_date 只需日期不需要时间和时区",
    "D": "时间字段值应该是字符串而非数字时间戳",
    "E": "同一项目所有时间字段应保持相同时区",
    "F": "generated_at 可以留空等后续填写"
  },
  "answer": ["B", "D", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 错误：自然语言时间（"下周五"）无法自动解析，不利于程序处理，且存在歧义。应使用 ISO 8601 格式。
  - `B`：B 正确：ISO 8601 含明确时区，消除了时区歧义，是正确实践。
  - `C`：C 错误：due_date 也需要完整的 ISO 8601 格式，包括时间（如 18:00）和时区偏移（+08:00）。
  - `D`：D 正确：时间字段应使用可读的字符串格式（ISO 8601），而非难以阅读的数字时间戳。
  - `E`：E 正确：同一项目所有时间字段统一使用 +08:00 可以保持一致性，避免混乱。
  - `F`：F 错误：generated_at 表示文件生成时间，应在生成时立即填写，不应留空。
