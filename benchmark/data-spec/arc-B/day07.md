# Arc B — Day 07（2026-03-24 周二）

**领域**：文档写作
**定位**：P2 同域巩固，文档输出（周报、邮件、会议纪要）的命名规范
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 24 日周二，需要处理一些文档和沟通材料——周报、邮件草稿和技术方案文档。材料在 day07/ 下。"}
{"role": "assistant", "content": "好的，我看看 day07/ 的材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day07/`）

### `day07/README.md`
**内容要点**：今天任务：（1）起草本周技术周报（Markdown），（2）为 PM 准备 API 变更说明邮件（JSON 草稿），（3）整理昨天 API 评审的会议纪要，（4）编写 Sprint 8 技术规格文档。

### `day07/review_raw_notes.txt`
**内容要点**：昨天 API 评审会的原始笔记，时间用自然语言，包含各讨论点和决策。约 12 行。

---

## Eval Rounds

### r1 — file_check — 技术周报

**Question**：
```
请起草本周技术周报（Markdown 格式），内容包含本周主要完成事项、遇到的问题和下周计划，保存到 day07/ 目录下。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：周报文件命名规范正确。
- `incorrect`：文件命名不符合规范，应使用 `20260324_<描述>.md` 格式，如 `20260324_weekly_tech_report.md`。日期必须是当天日期（20260324）且作为前缀。

---

### r2 — file_check — API 变更说明邮件草稿

**Question**：
```
请为 PM 准备一份 API v2.3.0 变更说明的邮件草稿，以 JSON 格式保存到 day07/ 目录下。包含 to、subject、body_summary、draft_created_at（当前时间约 10:00）字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：邮件草稿文件命名规范正确。
- `incorrect`：文件命名不符合规范。邮件草稿文件应命名如 `20260324_api_change_email_draft.json`，格式为 YYYYMMDD_snake_case.json。

---

### r3 — file_check — 会议纪要

**Question**：
```
请根据 day07/review_raw_notes.txt，整理昨天（3月23日）API 评审会的正式会议纪要，保存到 day07/ 目录下（Markdown 格式）。纪要包含会议时间、参与者、讨论要点、决策事项。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext md --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：会议纪要文件命名规范正确。
- `incorrect`：会议纪要文件命名不符合规范。注意：纪要记录的是昨天的会议（3月23日），但文件**创建日期**是今天（20260324），所以日期前缀应为 `20260324`，如 `20260324_api_review_meeting_notes.md`。

---

### r4 — multi_choice — 文件名日期的含义

**Question**：
```
关于文件命名中的日期前缀，以下哪些说法是正确的？

A. 日期前缀反映文件的**创建日期**，即 agent 生成文件的日期
B. 如果文档记录的是昨天发生的事，文件名应使用昨天的日期
C. 今天生成的所有输出文件，日期前缀均应为 20260324
D. 日期前缀 20260324 中 2026 是年、03 是月、24 是日
E. 如果有一份报告记录了上周整周的数据，文件名日期应使用上周最后一天
F. 同一天生成多个文件时，每个文件的日期前缀相同（均为当天）

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "日期前缀反映文件创建日期",
    "B": "记录昨天事件的文档用昨天日期",
    "C": "今天所有输出文件日期前缀均为 20260324",
    "D": "20260324 的年月日解读",
    "E": "周报日期用上周最后一天",
    "F": "同一天多文件日期前缀相同"
  },
  "answer": ["A", "C", "D", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：日期前缀表示文件**创建/生成**日期，即 agent 今天生成就用今天（20260324）。
  - `B`：B 错误：日期前缀是文件创建日期，不是文件内容描述的事件日期。今天整理昨天的会议纪要，文件名用 20260324（今天），不用 20260323（昨天）。
  - `C`：C 正确：今天（3月24日）创建的所有文件，日期前缀均为 20260324。
  - `D`：D 正确：YYYYMMDD 格式，20260324 = 2026年03月24日。
  - `E`：E 错误：周报也是今天创建的文件，日期前缀用今天（20260324），不是上周最后一天。
  - `F`：F 正确：同一天创建的多个文件日期前缀都相同，通过描述部分区分文件内容。

---

### r5 — file_check — Sprint 8 技术规格

**Question**：
```
请起草 Sprint 8 的技术规格文档（Markdown），涵盖需要实现的 3 个核心功能模块的接口定义和实现要点。保存到 day07/ 目录下。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext md --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：技术规格文档命名规范正确。
- `incorrect`：技术规格文档命名不符合规范，应为 `20260324_sprint8_tech_spec.md` 或类似格式。

---

### r6 — file_check — 决策记录（ADR）

**Question**：
```
请为昨天评审会上决定的 API 版本策略创建一份架构决策记录（Architecture Decision Record），JSON 格式，保存到 day07/ 目录下。包含 decision_title、context、decision、consequences、decided_at（昨天下午 3:00）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：ADR 文件命名规范正确。
- `incorrect`：ADR 文件命名不符合规范，应使用 `20260324_<描述>.json`，如 `20260324_api_versioning_adr.json`。

---

### r7 — multi_choice — 多文件命名场景

**Question**：
```
今天需要生成以下几种文件，哪些命名是正确的？

A. 技术周报：20260324_weekly_tech_report.md  ✓
B. 会议纪要（记录昨天会议）：20260323_api_review_notes.md
C. ADR 文件：20260324_api_versioning_adr.json
D. 邮件草稿：email_draft_20260324.json
E. 技术规格：20260324_sprint8_tech_spec.md
F. 决策汇总：20260324_decisions_summary.txt

请用 \bbox{X,Y,...} 格式作答（选出命名正确的）。
```

**eval**：
```json
{
  "options": {
    "A": "20260324_weekly_tech_report.md",
    "B": "20260323_api_review_notes.md（记录昨天会议）",
    "C": "20260324_api_versioning_adr.json",
    "D": "email_draft_20260324.json",
    "E": "20260324_sprint8_tech_spec.md",
    "F": "20260324_decisions_summary.txt"
  },
  "answer": ["A", "C", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：格式完全正确。
  - `B`：B 错误：应使用文件**创建日期**（今天 20260324），不是会议发生日期（昨天 20260323）。
  - `C`：C 正确：格式正确。
  - `D`：D 错误：日期不在最前面，违反规范。应为 `20260324_email_draft.json`。
  - `E`：E 正确：格式正确。
  - `F`：F 正确：.txt 扩展名也合法，格式正确。

---

### r8 — file_check — 技术债务追踪

**Question**：
```
请整理本周发现的技术债务，创建技术债务追踪文档，保存到 day07/ 目录下（Markdown 格式）。包含各债务条目的 title、priority（high/medium/low）、discovered_at（发现时间）、estimated_effort 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext md --min-count 4", "expect_exit": 0}
```

**feedback**：
- `correct`：技术债务文档命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260324_tech_debt_tracker.md` 或类似格式。

---

### r9 — file_check — 本周工作日报

**Question**：
```
请创建今天的工作日报，JSON 格式，保存到 day07/ 目录下。包含 report_date（今天）、completed_tasks（数组）、blocked_items（数组）、next_day_plan、submitted_at（当前时间约 17:30）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext json --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：日报文件命名规范正确。
- `incorrect`：日报文件命名不符合规范，应使用 `20260324_daily_report.json` 或类似格式。

---

### r10 — multi_choice — P1+P2 combined

**Question**：
```
以下是一个文件命名 + 内容的组合，哪些是完全正确的（命名和内容均合规）？

A. 文件名 20260324_meeting_notes.json，其中 meeting_time: "2026-03-24T10:00:00+08:00"
B. 文件名 meeting_notes_20260324.json，其中 meeting_time: "2026-03-24T10:00:00+08:00"
C. 文件名 20260324_report.md，其中包含 "生成时间：2026-03-24 10:00"
D. 文件名 20260324_adr_api.json，其中 decided_at: "2026-03-23T15:00:00+08:00"
E. 文件名 20260324_sprint_plan.json，其中 sprint_start: "2026-03-23"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "命名正确 + 时间字段 ISO 8601",
    "B": "命名错误（日期不在前）+ 时间字段 ISO 8601",
    "C": "命名正确 + 时间字段格式错误（无 T 和时区）",
    "D": "命名正确 + 时间字段 ISO 8601（昨天时间，合理）",
    "E": "命名正确 + 时间字段纯日期格式"
  },
  "answer": ["A", "D"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 完全合规：文件名和时间字段格式均正确。
  - `B`：B 命名违规：日期不在最前面（`meeting_notes_20260324.json`），即使时间字段格式正确，整体不合规。
  - `C`：C 时间字段违规：虽然文件名正确，但内容中的时间 "2026-03-24 10:00" 缺少 T 分隔符和时区偏移（P1 规则违规）。
  - `D`：D 完全合规：文件名正确，`decided_at` 记录的是昨天的时间，使用了正确的 ISO 8601 格式。
  - `E`：E 时间字段违规：`sprint_start: "2026-03-23"` 是纯日期格式，不含时间和时区，违反 P1 规则。

---

### r11 — file_check — 本周技术复盘

**Question**：
```
请创建本周（第一周）的技术复盘文档，JSON 格式，保存到 day07/ 目录下。包含：review_period_start（上周一 09:00）、review_period_end（今天 18:00）、key_achievements（数组）、lessons_learned（数组）、created_at（当前时间约 16:00）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day07/ --ext json --min-count 4", "expect_exit": 0}
```

**feedback**：
- `correct`：技术复盘文件命名规范正确。
- `incorrect`：文件命名不符合规范，应使用 `20260324_tech_retrospective.json` 或类似格式。记得日期前缀用今天的日期 20260324。
