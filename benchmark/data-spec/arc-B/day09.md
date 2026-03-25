# Arc B — Day 09（2026-03-26 周四）

**领域**：项目管理
**定位**：P1+P2 联合测试，PM 产出需要同时满足命名规范和时间格式
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 26 日周四，主要是项目管理任务——Sprint 8 中期回顾和资源规划。材料在 day09/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day09/ 的材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day09/`）

### `day09/README.md`
**内容要点**：Sprint 8 第四天，今天需要：（1）Sprint 中期进度回顾，（2）更新里程碑状态，（3）准备下周人员排班，（4）生成风险评估报告。

### `day09/sprint8_progress_raw.txt`
**内容要点**：各任务的原始进度记录，时间用自然语言（"昨天完成"、"预计明天"），含任务 ID、负责人、进度百分比。

### `day09/resource_availability.txt`
**内容要点**：下周人员可用性原始信息，包含各人姓名和休假/外出安排（自然语言时间）。

---

## Eval Rounds

### r1 — file_check — Sprint 中期进度报告

**Question**：
```
请基于 day09/sprint8_progress_raw.txt，生成 Sprint 8 中期进度报告，JSON 格式，保存到 day09/ 目录下。包含 report_generated_at（当前时间）、sprint_progress_pct（整体进度）、tasks（各任务状态）、risks（识别到的风险）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：进度报告文件命名规范正确。
- `incorrect`：进度报告文件命名不符合规范，应使用 `20260326_<描述>.json`，如 `20260326_sprint8_midpoint_report.json`。

---

### r2 — file_check — 里程碑状态更新

**Question**：
```
请创建当前里程碑状态快照，JSON 格式，保存到 day09/ 目录下。每个里程碑包含 id、title、target_date、status、last_updated（当前时间）、progress_pct。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：里程碑快照文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260326_milestone_status_snapshot.json` 或类似格式。

---

### r3 — file_check — P1 时间字段检查（进度报告）

**Question**：
```
请检查 day09/ 目录下最新创建的进度报告 JSON 文件，确认其中 report_generated_at 字段的时间格式是否符合要求。如果不符合，请修正后重新保存（覆盖原文件，保持文件名不变）。
```

**eval**：
```json
{"command": "python -c \"import json,re,glob,sys; files=sorted(glob.glob('day09/[0-9]*_*midpoint*.json')+glob.glob('day09/[0-9]*_*progress*.json')); d=json.load(open(files[0])) if files else sys.exit(1); v=d.get('report_generated_at',''); sys.exit(0 if re.match(r'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.[0-9]+)?\\+08:00$',str(v)) else 1)\"", "expect_exit": 0}
```

**feedback**：
- `correct`：进度报告中的时间字段格式正确。
- `incorrect`：进度报告中的 report_generated_at 格式不符合 ISO 8601 要求，应为 `2026-03-26T<HH:MM:SS>+08:00` 格式。

---

### r4 — multi_choice — P1+P2 联合判断

**Question**：
```
以下是几份 PM 文档的文件名和部分内容，哪些是完全合规的（P1 和 P2 均满足）？

A. 文件名 20260326_sprint8_midpoint.json，含 generated_at: "2026-03-26T09:00:00+08:00"
B. 文件名 sprint8_midpoint_report.json，含 generated_at: "2026-03-26T09:00:00+08:00"
C. 文件名 20260326_milestone_snapshot.json，含 target_date: "本周五"
D. 文件名 20260326_resource_plan.json，含 available_from: "2026-03-30T09:00:00+08:00"
E. 文件名 20260326_risk_assessment.md（无时间字段）

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "命名正确 + 时间字段 ISO 8601",
    "B": "命名违规（无日期前缀）+ 时间字段正确",
    "C": "命名正确 + 时间字段为自然语言",
    "D": "命名正确 + 时间字段 ISO 8601",
    "E": "命名正确 + 无时间字段（合规）"
  },
  "answer": ["A", "D", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 合规：命名和时间字段均正确。
  - `B`：B 命名违规：缺少日期前缀，违反 P2 规范。
  - `C`：C 时间违规：`target_date: "本周五"` 是自然语言，违反 P1 规范，应为 `2026-03-27T18:00:00+08:00`。
  - `D`：D 合规：命名和时间字段均正确。
  - `E`：E 合规：命名正确，Markdown 文件没有时间字段，不涉及 P1 规范，整体合规。

---

### r5 — file_check — 下周人员排班

**Question**：
```
请根据 day09/resource_availability.txt，生成下周（3月30日-4月3日）的人员排班计划，JSON 格式，保存到 day09/ 目录下。每人包含 name、available_days（日期数组，ISO 8601 格式）、unavailable_reason（如有）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext json --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：排班计划文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260326_next_week_resource_plan.json` 或类似格式。

---

### r6 — file_check — 风险评估报告

**Question**：
```
请基于当前 sprint 进度，生成风险评估报告，Markdown 格式，保存到 day09/ 目录下。每项风险包含 risk_id、description、probability（high/medium/low）、impact、mitigation。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：风险报告文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260326_sprint8_risk_assessment.md` 或类似格式。

---

### r7 — multi_choice — PM 文档命名场景

**Question**：
```
今天需要生成以下 PM 文档，哪些命名是正确的？

A. Sprint 8 中期报告：20260326_sprint8_midpoint_report.json
B. 里程碑快照：milestone_snapshot_20260326.json
C. 下周排班：20260326_next_week_schedule.json
D. 风险评估：20260326_risk_assessment.md
E. 会议决策：decisions_20260326.json
F. 项目看板快照：20260326_kanban_snapshot.json

请用 \bbox{X,Y,...} 格式作答（选出命名正确的）。
```

**eval**：
```json
{
  "options": {
    "A": "20260326_sprint8_midpoint_report.json",
    "B": "milestone_snapshot_20260326.json",
    "C": "20260326_next_week_schedule.json",
    "D": "20260326_risk_assessment.md",
    "E": "decisions_20260326.json",
    "F": "20260326_kanban_snapshot.json"
  },
  "answer": ["A", "C", "D", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：格式完全正确。
  - `B`：B 错误：日期不在最前面。
  - `C`：C 正确：格式正确。
  - `D`：D 正确：格式正确。
  - `E`：E 错误：日期不在最前面。
  - `F`：F 正确：格式正确。

---

### r8 — file_check — 项目看板快照

**Question**：
```
请生成当前项目看板的状态快照，JSON 格式，保存到 day09/ 目录下。按状态（backlog/in_progress/done/blocked）分类，记录各状态的任务数和任务列表。包含 snapshot_at（当前时间）字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext json --min-count 4", "expect_exit": 0}
```

**feedback**：
- `correct`：看板快照文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260326_kanban_snapshot.json` 或类似格式。

---

### r9 — file_check — 下周计划邮件草稿

**Question**：
```
请起草发给团队的下周工作计划邮件草稿，JSON 格式，保存到 day09/ 目录下。包含 subject、to（数组）、scheduled_send_at（今天下午 5:00）、body_summary（Markdown 摘要）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext json --min-count 5", "expect_exit": 0}
```

**feedback**：
- `correct`：邮件草稿文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260326_next_week_plan_email.json` 或类似格式。

---

### r10 — multi_choice — 里程碑日期格式

**Question**：
```
在项目管理文档中，以下 target_date 字段值，哪些格式是正确的？

A. "2026-03-27T18:00:00+08:00"（本周五 18:00）
B. "EOD Friday"
C. "2026-04-03T18:00:00+08:00"（下周五 18:00）
D. "2026-03-31"（纯日期，月底）
E. "2026-03-30T09:00:00+08:00"（下周一上午 9:00）
F. "TBD"

请用 \bbox{X,Y,...} 格式作答（选出正确的）。
```

**eval**：
```json
{
  "options": {
    "A": "2026-03-27T18:00:00+08:00",
    "B": "EOD Friday",
    "C": "2026-04-03T18:00:00+08:00",
    "D": "2026-03-31（纯日期）",
    "E": "2026-03-30T09:00:00+08:00",
    "F": "TBD"
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：完整的 ISO 8601 格式，含时区偏移。
  - `B`：B 错误：英文自然语言，不符合 P1 规范。
  - `C`：C 正确：格式正确，下周五的 ISO 8601 时间。
  - `D`：D 错误：纯日期格式，缺少时间和时区。
  - `E`：E 正确：格式正确。
  - `F`：F 错误："TBD" 不是时间值，如确实未定可以设为 null，但字段值必须是 ISO 8601 或 null，不能是字符串 "TBD"。

---

### r11 — file_check — 日终 PM 汇总

**Question**：
```
请创建今天的 PM 工作汇总，Markdown 格式，保存到 day09/ 目录下。汇总今天更新的所有 PM 产出和关键决策。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day09/ --ext md --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：PM 汇总文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260326_pm_daily_summary.md` 或类似格式。
