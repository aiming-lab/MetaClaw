# Arc C — Day 14（2026-04-02 周四）

**领域**：项目管理
**定位**：P1+P2+P3 联合测试，PM 产出需同时满足命名规范、时间格式、metadata 完整性
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 4 月 2 日周四，主要是项目管理工作——更新 Sprint 状态、准备季度报告材料。材料在 day14/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day14/ 的材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day14/`）

### `day14/README.md`
**内容要点**：今天任务：（1）更新 Sprint 8 任务状态，（2）生成 Q1 季度总结报告，（3）编写下季度规划文档，（4）整理团队能力矩阵。

### `day14/sprint8_tasks_raw.txt`
**内容要点**：Sprint 8 当前各任务状态的原始记录，包含任务 ID、负责人、进度、预计完成时间（自然语言）。

### `day14/q1_data_raw.json`
**内容要点**：Q1（1-3月）的汇总数据，包含各月关键指标，无 meta 对象，供 agent 处理生成报告。

---

## Eval Rounds

### r1 — file_check — Sprint 8 任务状态报告

**Question**：
```
请根据 day14/sprint8_tasks_raw.txt，生成 Sprint 8 当前任务状态报告，JSON 格式，保存到 day14/ 目录下。每个任务包含 id、title、assignee、status、progress_pct、estimated_completion。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.json')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day14/20260402_*.json'))[0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：任务状态报告命名、meta 对象和时间字段均正确。
- `incorrect`：任务状态报告存在以下问题：（1）命名需遵循 P2（20260402_*.json），（2）需包含顶层 meta 对象（P3），（3）estimated_completion 时间字段需使用 ISO 8601 格式（P1）。

---

### r2 — file_check — Q1 季度总结报告

**Question**：
```
请基于 day14/q1_data_raw.json，生成 Q1（2026年1-3月）季度总结报告，JSON 格式，保存到 day14/ 目录下。包含 period_start（2026-01-01 00:00）、period_end（2026-03-31 23:59）、generated_at（当前时间）、key_metrics 汇总。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.json')); sys.exit(0 if len(files)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day14/20260402_*.json')); print([f for f in fs if 'q1' in f or 'quarter' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：Q1 报告命名、meta 对象和时间字段均正确。
- `incorrect`：Q1 报告需满足：（1）P2 命名（20260402_*.json），（2）P3 meta 对象，（3）P1 时间字段（period_start 示例：`2026-01-01T00:00:00+08:00`）。

---

### r3 — multi_choice — P1+P2+P3 三规则联合判断

**Question**：
```
以下 JSON 文件描述，哪些同时满足 P1、P2、P3 三个规范？

A. 文件名 20260402_sprint8_status.json，meta 完整，estimated_completion: "2026-04-05T18:00:00+08:00"
B. 文件名 20260402_q1_report.json，meta 完整，period_start: "2026-01-01"（纯日期）
C. 文件名 sprint8_status_20260402.json，meta 完整，时间字段 ISO 8601 正确
D. 文件名 20260402_team_matrix.json，无 meta 对象，时间字段 ISO 8601 正确
E. 文件名 20260402_q2_plan.json，meta 的 created_at ISO 8601 正确，但 status: "complete"

请用 \bbox{X,Y,...} 格式作答（选完全合规的）。
```

**eval**：
```json
{
  "options": {
    "A": "P2 正确 + P3 meta 正确 + P1 时间正确",
    "B": "P2 正确 + P3 正确 + period_start 纯日期（P1 违规）",
    "C": "P2 违规（日期在后）+ P3 正确 + P1 正确",
    "D": "P2 正确 + 无 meta（P3 违规）+ P1 正确",
    "E": "P2 正确 + meta.status 非法值（P3 违规）"
  },
  "answer": ["A"]
}
```

**feedback**：
- `correct`：正确！只有 A 同时满足三个规范。
- `options`：
  - `A`：A 完全合规。
  - `B`：B P1 违规：`period_start: "2026-01-01"` 是纯日期格式。
  - `C`：C P2 违规：日期不在最前面。
  - `D`：D P3 违规：缺少 meta 对象。
  - `E`：E P3 违规：`status: "complete"` 不是合法状态值。

---

### r4 — file_check — 下季度（Q2）规划文档

**Question**：
```
请起草 Q2（2026年4-6月）的工作规划文档，Markdown 格式，保存到 day14/ 目录下。包含季度目标、关键里程碑（含日期）、资源需求。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.md')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day14/20260402_*.md'))[0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：Q2 规划文档命名和 frontmatter 均正确。
- `incorrect`：Q2 规划文档需要 P2 命名（20260402_*.md）和 P3 YAML frontmatter（含 created_at ISO 8601、author、status）。

---

### r5 — file_check — 团队能力矩阵

**Question**：
```
请创建团队能力矩阵，JSON 格式，保存到 day14/ 目录下。记录各团队成员的技术能力领域（frontend/backend/data/devops）和熟练程度（1-5），以及 last_updated（当前时间）。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.json')); sys.exit(0 if len(files)>=3 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day14/20260402_*.json')); print([f for f in fs if 'team' in f or 'skill' in f or 'matrix' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：团队能力矩阵命名、meta 对象和时间字段均正确。
- `incorrect`：团队能力矩阵需要 P2 命名、P3 meta 对象，以及 P1 时间字段格式（last_updated 示例：`2026-04-02T10:00:00+08:00`）。

---

### r6 — file_check — 风险追踪更新

**Question**：
```
请更新本 Sprint 的风险追踪记录，创建最新版本，JSON 格式，保存到 day14/ 目录下。包含各风险项的 risk_id、description、probability、impact、status（open/mitigated/closed）、last_reviewed（当前时间）。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.json')); sys.exit(0 if len(files)>=4 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day14/20260402_*.json')); print([f for f in fs if 'risk' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：风险追踪文件命名、meta 对象和时间字段均正确。
- `incorrect`：风险追踪文件需要 P2 命名、P3 meta 对象，以及 P1 时间格式（last_reviewed 示例：`2026-04-02T11:00:00+08:00`）。

---

### r7 — multi_choice — 季报中的时间字段规范

**Question**：
```
Q1 季度报告中包含多个时间字段，以下哪些字段值格式是正确的？

A. period_start: "2026-01-01T00:00:00+08:00"
B. period_end: "2026-03-31"
C. generated_at: "2026-04-02T09:30:00+08:00"
D. report_date: "Q1 2026"
E. last_milestone_achieved: "2026-03-27T14:12:00+08:00"
F. next_review_date: "2026-06-30T18:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答（选出格式正确的）。
```

**eval**：
```json
{
  "options": {
    "A": "period_start: 2026-01-01T00:00:00+08:00",
    "B": "period_end: 2026-03-31（纯日期）",
    "C": "generated_at: 2026-04-02T09:30:00+08:00",
    "D": "report_date: Q1 2026（非时间格式）",
    "E": "last_milestone_achieved: 2026-03-27T14:12:00+08:00",
    "F": "next_review_date: 2026-06-30T18:00:00+08:00"
  },
  "answer": ["A", "C", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：完整的 ISO 8601 格式。
  - `B`：B 错误：纯日期格式，缺少时间和时区。
  - `C`：C 正确：格式正确。
  - `D`：D 错误："Q1 2026" 不是时间格式，不符合 P1 规范，应转换为具体的时间范围。
  - `E`：E 正确：格式正确。
  - `F`：F 正确：格式正确（未来的日期也适用 ISO 8601）。

---

### r8 — file_check — Sprint 8 第二周总结

**Question**：
```
请创建 Sprint 8 第二周（本周）的工作总结，Markdown 格式，保存到 day14/ 目录下。包含本周完成事项、未完成原因分析、下周计划。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.md')); sys.exit(0 if len(files)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day14/20260402_*.md')); print([f for f in fs if 'week' in f or 'summary' in f or 'sprint' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint 总结文档命名和 frontmatter 均正确。
- `incorrect`：Sprint 总结文档需要 P2 命名（20260402_*.md）和 P3 YAML frontmatter。

---

### r9 — file_check — 绩效指标报告

**Question**：
```
请生成本月（4月第一周）的团队绩效指标报告，JSON 格式，保存到 day14/ 目录下。包含 report_period_start（本周一 09:00）、report_period_end（今天 18:00）、team_velocity（完成任务数）、bug_count、deployment_count、on_call_incidents。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.json')); sys.exit(0 if len(files)>=5 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day14/20260402_*.json')); print([f for f in fs if 'perf' in f or 'metric' in f or 'kpi' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：绩效指标报告命名、meta 对象和时间字段均正确。
- `incorrect`：绩效指标报告需满足 P1（report_period_start 格式：`2026-03-30T09:00:00+08:00`）、P2（命名规范）、P3（meta 对象）三个规范。

---

### r10 — multi_choice — 合规性自检问题

**Question**：
```
在提交今天的工作产出前做合规性自检，以下哪些检查项是必要的？

A. 检查所有 JSON 文件是否有顶层 meta 对象（P3）
B. 检查所有文件名是否以 YYYYMMDD_ 开头（P2）
C. 检查所有 Markdown 文件开头是否有 YAML frontmatter（P3）
D. 检查 Python 文件的函数数量是否足够（与 P1-P3 无关）
E. 检查所有时间字段是否使用 ISO 8601 +08:00 格式（P1）
F. 检查 meta 对象中的 status 是否为合法值（P3）

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "检查 JSON 文件的顶层 meta 对象",
    "B": "检查文件名 YYYYMMDD_ 前缀",
    "C": "检查 Markdown 文件的 YAML frontmatter",
    "D": "检查 Python 函数数量",
    "E": "检查时间字段 ISO 8601 格式",
    "F": "检查 meta.status 合法值"
  },
  "answer": ["A", "B", "C", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 必要：P3 要求 JSON 文件有顶层 meta 对象。
  - `B`：B 必要：P2 要求所有输出文件名以日期前缀开头。
  - `C`：C 必要：P3 要求 Markdown 文件有 YAML frontmatter。
  - `D`：D 不必要：函数数量与 P1-P3 规范无关，不在合规性检查范围内。
  - `E`：E 必要：P1 要求所有时间字段使用 ISO 8601 +08:00 格式。
  - `F`：F 必要：P3 要求 meta.status 必须是合法值（pending/in_progress/done）。

---

### r11 — file_check — 合规性检查报告

**Question**：
```
请创建今天工作产出的合规性自检报告，Markdown 格式，保存到 day14/ 目录下。列出今天创建的所有文件，并对每个文件标注 P1/P2/P3 是否合规。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day14/20260402_*.md')); sys.exit(0 if len(files)>=3 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day14/20260402_*.md')); print([f for f in fs if 'compliance' in f or 'check' in f or 'audit' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：合规性检查报告命名和 frontmatter 均正确。
- `incorrect`：合规性检查报告本身也需要遵循 P2（20260402_*.md）和 P3（YAML frontmatter）规范。
