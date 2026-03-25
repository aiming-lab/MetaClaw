# Arc D — Day 19（2026-04-09 周四）

**领域**：项目管理
**定位**：P1+P2+P4 联合测试，PM 文件的更新需同时满足时间格式、命名规范和备份要求
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 4 月 9 日周四，需要更新项目计划和风险追踪，同时要新建一些 Sprint 报告。材料在 day19/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day19/ 的材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day19/`）

### `day19/README.md`
**内容要点**：今天任务：（1）更新 Q2 项目计划，（2）修订风险矩阵，（3）更新 Sprint 8 状态板，（4）新建本周进度报告。有多个需要修改的已有文件。

### `day19/q2_project_plan.json`
**内容要点**：Q2 项目计划（已存在），需要更新 milestone 4 的 target_date（发现日期设置有误），时间字段需符合 P1。需要被修改。

### `day19/risk_matrix.json`
**内容要点**：风险矩阵（已存在），需要更新两个风险项的 status 和 last_reviewed 时间字段。需要被修改。

### `day19/sprint8_board.json`
**内容要点**：Sprint 8 状态板（已存在），需要将两个任务状态从 in_progress 改为 done，更新 completed_at 字段。需要被修改。

---

## Eval Rounds

### r1 — file_check — 更新 Q2 项目计划

**Question**：
```
请更新 day19/q2_project_plan.json，将 milestone 4 的 target_date 从当前错误值修正为 2026-06-15 18:00（CST）。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day19/q2_project_plan.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改前创建了 q2_project_plan.json.bak 备份。
- `incorrect`：修改 day19/q2_project_plan.json 前需要先创建 .bak 备份（P4），且修正后的 target_date 应为 ISO 8601 格式 `2026-06-15T18:00:00+08:00`（P1）。

---

### r2 — file_check — 更新风险矩阵

**Question**：
```
请更新 day19/risk_matrix.json：将 risk-003 的 status 改为 "mitigated"，将 last_reviewed 更新为当前时间。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day19/risk_matrix.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改前创建了 risk_matrix.json.bak 备份。
- `incorrect`：修改 day19/risk_matrix.json 前需要先备份（P4）。更新后的 last_reviewed 应为 ISO 8601 格式（P1），如 `2026-04-09T10:00:00+08:00`。

---

### r3 — multi_choice — P1+P4 联合场景

**Question**：
```
在更新已有 JSON 文件时，以下哪些操作顺序和规范是正确的？

A. 先备份（.bak），再修改文件内容（包括将时间字段改为 ISO 8601）
B. 先修改时间字段为 ISO 8601，再创建 .bak 备份
C. 备份和时间字段格式是相互独立的要求，先后顺序不影响最终结果
D. .bak 文件里的时间字段可以保留原始的错误格式（因为它是原文件的副本）
E. 修改后的文件需要满足 P1（时间字段 ISO 8601），修改前的 .bak 保留原始状态

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "先备份，再修改（含时间格式）",
    "B": "先改时间格式，再备份",
    "C": "P1 和 P4 独立，顺序不影响结果",
    "D": ".bak 里的时间字段可以保留原始格式",
    "E": "修改后满足 P1，.bak 保留原始状态"
  },
  "answer": ["A", "D", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：正确操作顺序：先备份（保留原始状态），再修改（使文件满足 P1）。
  - `B`：B 错误：先修改了文件再备份，.bak 里装的是修改后的版本，失去备份意义（P4 违规）。
  - `C`：C 部分正确但有误：虽然 P1 和 P4 是独立规范，但备份的顺序很关键（必须先备份再修改），说"顺序不影响最终结果"是错的。
  - `D`：D 正确：.bak 是原文件的精确副本，如果原文件的时间字段格式有误，.bak 也保留这个错误格式。这是正确的——.bak 的目的是保存**原始状态**。
  - `E`：E 正确：修改后的文件是 agent 的输出，需要满足 P1 规范；.bak 是原始备份，保留原始状态。

---

### r4 — file_check — 更新 Sprint 状态板

**Question**：
```
请更新 day19/sprint8_board.json：将任务 T-405 和 T-406 的 status 改为 "done"，分别添加 completed_at 字段（T-405 于今天上午 11:00 完成，T-406 于今天下午 14:30 完成）。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day19/sprint8_board.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改前创建了 sprint8_board.json.bak 备份。
- `incorrect`：修改 day19/sprint8_board.json 前需要先创建 .bak 备份（P4）。completed_at 字段需使用 ISO 8601 格式（P1），如 T-405: `2026-04-09T11:00:00+08:00`。

---

### r5 — file_check — 新建本周进度报告

**Question**：
```
请创建本周（4月6日至4月10日）的进度报告，JSON 格式，保存到 day19/ 目录下（新建文件）。包含 report_generated_at（当前时间）、sprint_week（Sprint 9 第一周）、completed_tasks、in_progress_tasks、blocked_tasks 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day19/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：进度报告文件命名规范正确。
- `incorrect`：进度报告命名需遵循 P2 规范（20260409_*.json），如 `20260409_sprint9_week1_progress.json`。这是新建文件，不需要 .bak。

---

### r6 — multi_choice — P2+P4 联合场景

**Question**：
```
今天需要修改已有文件 risk_matrix.json，同时新建一个进度报告文件。以下哪些说法是正确的？

A. risk_matrix.json 修改前需要创建 risk_matrix.json.bak
B. 新建的进度报告文件需要以 YYYYMMDD_ 开头（P2），不需要 .bak（P4 不适用）
C. 修改后的 risk_matrix.json 不需要遵循 P2（因为它不是新建文件，文件名已经存在）
D. 新建的进度报告如果当天又需要修改，则需要先创建它的 .bak
E. risk_matrix.json.bak 不需要满足 P2 命名规范

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "risk_matrix.json 修改前需要 .bak",
    "B": "新建报告需要 P2 命名，不需要 P4 备份",
    "C": "修改已有文件不受 P2 约束（文件名不变）",
    "D": "新建文件当天修改需要 .bak",
    "E": ".bak 文件不需要满足 P2 命名"
  },
  "answer": ["A", "B", "C", "D", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：修改已有文件前需要 .bak（P4）。
  - `B`：B 正确：新建文件需要 P2 命名，但不触发 P4（无原始文件可备份）。
  - `C`：C 正确：P2 针对 agent 生成文件的**命名**，已有文件（非 agent 新建的）的文件名不受 P2 约束。
  - `D`：D 正确：当天新建的文件一旦需要修改，就变成了"已有文件"，修改前需要 .bak。
  - `E`：E 正确：.bak 是原文件的副本，不是 agent 的输出，不受 P2 命名规范约束。

---

### r7 — file_check — 里程碑完成确认记录

**Question**：
```
请创建一份里程碑完成确认记录，JSON 格式，保存到 day19/ 目录下（新建文件）。记录本周已完成的里程碑：完成时间、验收结果、负责人签字（用字符串模拟）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day19/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：里程碑确认记录文件命名规范正确。
- `incorrect`：文件命名需遵循 P2 规范（20260409_*.json），如 `20260409_milestone_completion_record.json`。

---

### r8 — file_check — 更新资源分配计划

**Question**：
```
day19/ 下有一个预置的 resource_allocation.json（已存在），需要为下周新增任务 T-410 分配资源（assignee: "Bai"，estimated_hours: 8，allocated_at 字段设为今天下午 15:00）。请更新此文件。
```

**注**：subagent 需要预置 `day19/resource_allocation.json` 文件，包含现有资源分配数据。

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day19/resource_allocation.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改前创建了 resource_allocation.json.bak 备份。
- `incorrect`：修改 day19/resource_allocation.json 前需要先创建 .bak 备份（P4）。allocated_at 字段需使用 ISO 8601 格式（P1）：`2026-04-09T15:00:00+08:00`。

---

### r9 — multi_choice — 综合判断：操作是否合规

**Question**：
```
以下是今天的操作记录，哪些是合规的（P1+P2+P4 均满足）？

A. 修改 sprint8_board.json 时先创建了 sprint8_board.json.bak，修改后 completed_at 值为 "2026-04-09T11:00:00+08:00"
B. 新建进度报告文件，命名为 progress_report_20260409.json（无 .bak，因为是新建）
C. 修改 risk_matrix.json 时先创建了 .bak，修改后 last_reviewed 值为 "2026-04-09"（纯日期）
D. 新建里程碑记录文件，命名为 20260409_milestone_record.json，其中 achieved_at: "2026-04-09T10:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答（选完全合规的）。
```

**eval**：
```json
{
  "options": {
    "A": "备份正确 + 时间字段 ISO 8601（合规）",
    "B": "新建文件，命名违规（日期在后）",
    "C": "备份正确 + 时间字段纯日期（P1 违规）",
    "D": "新建文件，命名正确 + 时间字段 ISO 8601（合规）"
  },
  "answer": ["A", "D"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 完全合规：备份（P4）正确，时间字段（P1）正确。
  - `B`：B P2 违规：新建文件命名日期不在前面（`progress_report_20260409.json`），违反 P2 规范。
  - `C`：C P1 违规：`last_reviewed: "2026-04-09"` 是纯日期格式，违反 P1 规范（需要完整的 ISO 8601 格式）。
  - `D`：D 完全合规：新建文件（不需要 P4 备份），P2 命名正确，P1 时间字段正确。

---

### r10 — file_check — 本周 PM 工作总结

**Question**：
```
请创建本周（4月6-9日）项目管理工作的日终总结，Markdown 格式，保存到 day19/ 目录下。包含：完成的 PM 任务、更新的文件列表、下周优先项。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day19/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：PM 工作总结文件命名规范正确。
- `incorrect`：文件命名需遵循 P2 规范（20260409_*.md），如 `20260409_pm_weekly_summary.md`。

---

### r11 — multi_choice — 三规则综合回顾

**Question**：
```
在今天的 PM 工作中，同时涉及 P1、P2、P4 三个规范。以下哪些说法正确总结了三者的关系和应用场景？

A. P1 约束文件内容（时间字段格式），P2 约束文件名，P4 约束操作行为（备份时机）
B. 三个规范可以同时违反，也可以同时满足，相互之间没有依赖关系
C. 修改已有文件时，P4（备份）是前置步骤，然后才能开始 P1（时间格式）的修改
D. 新建文件时，P2（命名）和 P1（时间字段内容）都需要满足，P4 不适用
E. .bak 文件不受 P1 约束（时间字段格式），因为它是原始备份，不是 agent 的输出
F. 所有三个规范都是强制要求，没有优先级之分，必须同时满足

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "P1 约束内容，P2 约束文件名，P4 约束操作行为",
    "B": "三规范相互无依赖",
    "C": "修改时 P4（备份）是前置步骤",
    "D": "新建文件 P2+P1 适用，P4 不适用",
    "E": ".bak 不受 P1 约束",
    "F": "三规范都是强制要求"
  },
  "answer": ["A", "C", "D", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：准确描述了三个规范的适用维度。
  - `B`：B 错误：虽然三个规范在不同维度独立，但修改已有文件时 P4 有操作顺序依赖（必须先备份）。
  - `C`：C 正确：修改已有文件时，P4（创建 .bak）必须是第一步，然后才开始执行修改（包括 P1 的时间格式修正）。
  - `D`：D 正确：新建文件时 P2（命名）和 P1（内容）均适用，但不触发 P4（没有原文件可备份）。
  - `E`：E 正确：.bak 是原始备份，不是 agent 生成的输出，不受 P1 约束（它就是要保留原始状态，包括可能存在的不合规时间格式）。
  - `F`：F 正确：三个规范都是强制要求，需要同时满足。
