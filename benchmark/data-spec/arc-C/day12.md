# Arc C — Day 12（2026-03-31 周二）

**领域**：数据处理（JSON）
**定位**：P3 在 JSON 文件中的应用，缺少顶层 `meta` 对象时失败
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 31 日，处理一些数据分析和统计工作，输出 JSON 格式的报告。相关材料在 day12/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day12/ 的数据材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day12/`）

### `day12/README.md`
**内容要点**：今天任务：（1）分析本月 API 调用统计，（2）生成用户使用报告，（3）整理异常事件统计，（4）输出月度汇总数据。

### `day12/monthly_api_stats_raw.json`
**内容要点**：原始 API 统计数据（无 meta 对象），包含各端点的调用次数、平均响应时间、错误率。供 agent 处理后生成规范化输出。

### `day12/user_sessions_raw.json`
**内容要点**：用户会话原始数据（无 meta 对象），包含各用户的 session 信息。

---

## Eval Rounds

### r1 — file_check — 月度 API 统计报告

**Question**：
```
请处理 day12/monthly_api_stats_raw.json，生成规范化的月度 API 统计报告，JSON 格式，保存到 day12/ 目录下。包含 endpoint 汇总数据和整体指标。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day12/20260331_*.json'))[0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：JSON 报告命名和 meta 对象均符合规范。
- `incorrect`：JSON 输出文件存在以下问题：（1）命名需遵循 P2 规范（20260331_desc.json），（2）必须包含顶层 `meta` 对象，格式如：\n```json\n{"meta": {"created_at": "2026-03-31T<time>+08:00", "author": "metaclaw_agent", "status": "done"}, "content": {...}}\n```

---

### r2 — multi_choice — JSON meta 对象格式识别

**Question**：
```
以下哪些 JSON 结构包含符合规范的 meta 对象？

A. {"meta": {"created_at": "2026-03-31T09:00:00+08:00", "author": "metaclaw_agent", "status": "done"}, "data": [...]}
B. {"metadata": {"created_at": "2026-03-31T09:00:00+08:00", "author": "metaclaw_agent", "status": "done"}, "data": [...]}
C. {"meta": {"created_at": "2026-03-31T09:00:00+08:00", "author": "metaclaw_agent"}, "data": [...]}
D. {"data": [...], "meta": {"created_at": "2026-03-31T09:00:00+08:00", "author": "metaclaw_agent", "status": "pending"}}
E. {"meta": {"created_at": "2026/03/31 09:00", "author": "metaclaw_agent", "status": "done"}, "data": [...]}
F. {"meta": {"created_at": "2026-03-31T09:00:00+08:00", "author": "metaclaw_agent", "status": "done", "version": "1.0"}, "data": [...]}

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "完整正确的 meta 对象",
    "B": "字段名错误（metadata 不是 meta）",
    "C": "缺少 status 字段",
    "D": "meta 不在顶层（data 之后，JSON 键序不影响）",
    "E": "created_at 格式错误（斜线+空格）",
    "F": "完整 meta 加额外字段 version"
  },
  "answer": ["A", "D", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：meta 对象完整，三个必填字段格式均正确。
  - `B`：B 错误：顶层键名必须是 `meta`，不是 `metadata`。
  - `C`：C 错误：缺少必填字段 `status`。
  - `D`：D 正确：JSON 对象中键的顺序不影响合规性，`meta` 在 `data` 之后也是合法的。
  - `E`：E 错误：`created_at` 使用了斜线格式（P1 违规），必须是 ISO 8601 格式。
  - `F`：F 正确：三个必填字段完整，额外字段 `version` 是允许的。

---

### r3 — file_check — 用户活跃度分析

**Question**：
```
请处理 day12/user_sessions_raw.json，生成用户活跃度分析报告，JSON 格式，保存到 day12/ 目录下。包含各用户的活跃度分类（高/中/低）、整体活跃率。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if len(files)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day12/20260331_*.json')); print([f for f in fs if 'user' in f or 'activity' in f or 'session' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：用户活跃度报告命名和 meta 对象正确。
- `incorrect`：用户活跃度报告需要正确的命名格式（20260331_desc.json）和顶层 meta 对象（含 created_at、author、status）。

---

### r4 — file_check — 异常事件统计

**Question**：
```
请统计本月的 API 异常事件，生成统计报告，JSON 格式，保存到 day12/ 目录下。包含各类错误的发生次数、占比、受影响端点。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if len(files)>=3 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day12/20260331_*.json')); print([f for f in fs if 'error' in f or 'exception' in f or 'anomaly' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：异常统计文件命名和 meta 对象正确。
- `incorrect`：异常统计文件需要 P2 命名（20260331_*.json）和 P3 顶层 meta 对象。

---

### r5 — multi_choice — meta 字段语义理解

**Question**：
```
对于 JSON 报告文件中的 meta 对象，以下说法哪些是正确的？

A. meta.created_at 记录这个 JSON 文件被生成的时间
B. meta.author 应填写最终用户（Alex）的名字，因为这是他的数据
C. meta.status 为 "done" 表示该报告的内容已完成，不再修改
D. meta 对象应该是 JSON 的顶层（根级别）字段，不能嵌套在其他对象中
E. 如果 JSON 文件只是中间临时数据，可以不加 meta 对象
F. meta 对象中的 created_at 和 JSON 内容中的分析时间字段可以不同

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "meta.created_at 记录文件生成时间",
    "B": "meta.author 应填写用户 Alex",
    "C": "meta.status: done 表示内容完成",
    "D": "meta 必须是顶层字段",
    "E": "临时数据可不加 meta",
    "F": "meta.created_at 和内容分析时间可以不同"
  },
  "answer": ["A", "C", "D", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：`meta.created_at` 记录的是文件本身（由 agent）生成的时间。
  - `B`：B 错误：`meta.author` 记录的是**生成文件的执行者**，即 `metaclaw_agent`，不是请求数据的用户。
  - `C`：C 正确：`status: "done"` 表示该报告的内容已完成。
  - `D`：D 正确：`meta` 必须是 JSON 根对象的顶层字段，不能嵌套在 `data` 或其他子对象中。
  - `E`：E 错误：所有 agent 生成的输出文件均需要 meta 对象，不区分是否临时。
  - `F`：F 正确：`meta.created_at` 是文件生成时间，而内容中的分析时间（如 `analysis_period`）是数据覆盖的时间范围，两者完全可以不同。

---

### r6 — file_check — 月度汇总数据

**Question**：
```
请生成本月（3月份）的数据汇总，JSON 格式，保存到 day12/ 目录下。整合本周处理的 API 统计、用户活跃度、异常事件三类数据的关键指标。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if len(files)>=4 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day12/20260331_*.json')); print([f for f in fs if 'monthly' in f or 'summary' in f or 'march' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：月度汇总文件命名和 meta 对象正确。
- `incorrect`：月度汇总文件需要正确命名（20260331_*.json）和顶层 meta 对象。

---

### r7 — file_check — 数据质量评估报告

**Question**：
```
请对今天处理的原始数据做质量评估，生成评估报告，JSON 格式，保存到 day12/ 目录下。包含：数据完整性评分、发现的问题列表、建议的修复措施。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if len(files)>=5 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day12/20260331_*.json')); print([f for f in fs if 'quality' in f or 'assessment' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：数据质量报告命名和 meta 对象正确。
- `incorrect`：数据质量报告需要 P2 命名和 P3 meta 对象。

---

### r8 — multi_choice — JSON meta 在实际场景中的应用

**Question**：
```
在以下场景中，哪些 meta 对象的内容是正确的？

A. API 统计报告刚生成：{"created_at": "2026-03-31T09:30:00+08:00", "author": "metaclaw_agent", "status": "done"}
B. 正在处理的中间报告：{"created_at": "2026-03-31T09:30:00+08:00", "author": "metaclaw_agent", "status": "in_progress"}
C. 数据质量报告（等待人工审阅）：{"created_at": "2026-03-31T09:30:00+08:00", "author": "metaclaw_agent", "status": "pending"}
D. 月度汇总（已完成）：{"created_at": "2026-03-31", "author": "metaclaw_agent", "status": "done"}
E. 用户活跃度报告：{"created_at": "2026-03-31T14:00:00+08:00", "author": "Alex", "status": "done"}

请用 \bbox{X,Y,...} 格式作答（选出正确的 meta 内容）。
```

**eval**：
```json
{
  "options": {
    "A": "新生成报告，status: done",
    "B": "处理中的报告，status: in_progress",
    "C": "等待审阅，status: pending",
    "D": "已完成，但 created_at 是纯日期",
    "E": "author 填了 Alex（应填 metaclaw_agent）"
  },
  "answer": ["A", "B", "C"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：内容正确，三个字段均合法。
  - `B`：B 正确：status 为 in_progress 表示正在处理，合法。
  - `C`：C 正确：status 为 pending 表示等待处理（如等待审阅），合法。
  - `D`：D 错误：`created_at: "2026-03-31"` 是纯日期格式，违反 P1 规范，必须是完整的 ISO 8601 格式。
  - `E`：E 错误：`author` 应填写生成文件的执行者（`metaclaw_agent`），不是请求任务的用户（Alex）。

---

### r9 — file_check — 报告索引文件

**Question**：
```
请创建今天生成的所有数据报告的索引，JSON 格式，保存到 day12/ 目录下。每条包含报告文件名、类型、生成时间。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if len(files)>=6 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day12/20260331_*.json')); print([f for f in fs if 'index' in f or 'catalog' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：报告索引文件命名和 meta 对象正确。
- `incorrect`：报告索引文件需要 P2 命名（20260331_*.json）和 P3 顶层 meta 对象。

---

### r10 — multi_choice — P1+P2+P3 联合判断（JSON）

**Question**：
```
以下 JSON 文件描述，哪些同时满足 P1、P2、P3 三个规范？

A. 文件名 20260331_api_stats.json，meta.created_at: "2026-03-31T09:00:00+08:00"，有 author 和 status
B. 文件名 20260331_user_report.json，meta 中 created_at: "2026-03-31"，有 author 和 status
C. 文件名 api_stats_20260331.json，meta 完整且 created_at 格式正确
D. 文件名 20260331_error_stats.json，无 meta 对象，但内容中的时间字段均为 ISO 8601
E. 文件名 20260331_monthly_summary.json，meta 完整，内容中 analysis_end: "2026-03-31T23:59:59+08:00"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "P2 正确 + P3 完整 + P1 正确",
    "B": "P2 正确 + created_at 纯日期（P1 违规）",
    "C": "P2 违规（日期在后）+ P3 正确",
    "D": "P2 正确 + 无 meta（P3 违规）",
    "E": "P2 正确 + P3 完整 + 内容时间字段 P1 正确"
  },
  "answer": ["A", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 完全合规：P2 命名正确，P3 meta 完整，P1 时间格式正确。
  - `B`：B P1 违规：meta.created_at 是纯日期格式，违反 P1 规范。
  - `C`：C P2 违规：日期在描述后面（api_stats_20260331），违反 P2 命名规范。
  - `D`：D P3 违规：缺少顶层 meta 对象，违反 P3 规范。
  - `E`：E 完全合规：P2 命名正确，P3 meta 完整，内容中的时间字段也符合 P1。

---

### r11 — file_check — 月末总结报告

**Question**：
```
今天是三月的最后一天，请创建 3 月份的月末总结报告，JSON 格式，保存到 day12/ 目录下。包含：本月完成的主要工作、关键指标变化趋势、下月规划重点。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day12/20260331_*.json')); sys.exit(0 if len(files)>=7 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day12/20260331_*.json')); print([f for f in fs if 'month' in f or 'march' in f or 'end' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：月末总结报告命名和 meta 对象正确。
- `incorrect`：月末总结报告需要 P2 命名（20260331_*.json）和 P3 顶层 meta 对象（含 created_at ISO 8601、author、status）。
