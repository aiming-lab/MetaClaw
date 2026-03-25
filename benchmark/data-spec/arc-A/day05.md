# Arc A — Day 05（2026-03-20 周五）

**领域**：综合（sprint 收尾）
**定位**：强泛化测试，多类型文件同时出现时间字段，P1 出现在最自然、最容易被忽视的位置
**Rounds**：13

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 20 日周五，sprint 最后一天，今天要整理本周所有产出，准备下午的 sprint review。相关材料在 day05/ 下。"}
{"role": "assistant", "content": "好的，周五收尾工作，我来看看 day05/ 的材料，准备整理。"}
```

---

## Workspace 文件（`workspaces/shared/day05/`）

### `day05/README.md`
**内容要点**：Sprint 7 最后一天，需要（1）汇总全周数据，（2）生成 sprint review 文档，（3）归档本周产出，（4）为下个 sprint 做预备记录。包含今天日程：14:00 sprint review 会议。

### `day05/weekly_raw_data.json`
**内容要点**：预置文件，包含本周各天的简报数据，**时间字段格式刻意混乱**（各天用不同格式：有 Apache 格式、自然语言、ISO 无时区等），agent 需要规范化后生成报告：
```json
{
  "week": "2026-W12",
  "days": [
    {"date": "2026-03-16", "standup_time": "09:30 AM", "tasks_completed": 2},
    {"date": "2026-03-17", "standup_time": "2026-03-17 09:28:00", "tasks_completed": 3},
    {"date": "2026-03-18", "standup_time": "09/30 09:31 AM CST", "tasks_completed": 4},
    {"date": "2026-03-19", "standup_time": "2026-03-19T09:29:00Z", "tasks_completed": 3},
    {"date": "2026-03-20", "standup_time": "TBD", "tasks_completed": 0}
  ]
}
```

### `day05/sprint_review_template.md`
**内容要点**：Sprint review 文档模板，Markdown 格式，有标题和章节占位符，**无任何时间字段提示**。

### `day05/archive_index_stub.json`
**内容要点**：归档索引骨架，包含本周各天产出文件的引用（文件名占位），但所有 `archived_at` 字段为空。

---

## Eval Rounds

### r1 — file_check — 周数据规范化

**Question**：
```
请读取 day05/weekly_raw_data.json，将所有 standup_time 字段规范化为 ISO 8601 格式，今天（day05）的 standup 时间填入 09:30。结果保存为 day05/weekly_data_normalized.json，保留原始 date 字段（纯日期不做要求），仅规范化 standup_time。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/weekly_data_normalized.json days[].standup_time", "expect_exit": 0}
```

**feedback**：
- `correct`：所有 standup_time 已正确规范化为 ISO 8601 格式。
- `incorrect`：days 中的 standup_time 仍有格式不符合要求的条目。注意各天的原始格式各不相同，均需统一转换为 `YYYY-MM-DDTHH:MM:SS+08:00` 格式，例如周一的 "09:30 AM" 应转换为 `2026-03-16T09:30:00+08:00`。

---

### r2 — file_check — Sprint Review 文档生成

**Question**：
```
请基于本周的工作成果，填写 day05/sprint_review_template.md，生成正式的 Sprint Review 文档，保存为 day05/sprint_review_final.md。文档中需要包含以下时间信息（格式须符合规范）：sprint 起止时间（2026-03-16 09:00 到今天 18:00）、文档生成时间（当前，约 10:00）、review 会议时间（今天 14:00）。
```

**eval**：
```json
{"command": "python -c \"import re,sys; text=open('day05/sprint_review_final.md').read(); iso_pat=re.compile(r'\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.[0-9]+)?\\+08:00'); matches=iso_pat.findall(text); natural_bad=re.search(r'(上午|下午|周[一二三四五六日]|\\d+月\\d+日)',text); sys.exit(0 if len(matches)>=3 and not natural_bad else 1)\"", "expect_exit": 0}
```

**feedback**：
- `correct`：sprint_review_final.md 中的时间字段格式正确，且没有自然语言时间。
- `incorrect`：sprint_review_final.md 中的时间格式不符合要求：文档中的时间信息需使用 ISO 8601 格式（如 `2026-03-16T09:00:00+08:00`），不能使用自然语言（如"下午2点"）或纯日期。

---

### r3 — multi_choice — Markdown 文档中的时间格式

**Question**：
```
在 Markdown 格式的 Sprint Review 文档中，以下哪些时间表示方式是正确的？

A. **Sprint 周期**：2026-03-16T09:00:00+08:00 至 2026-03-20T18:00:00+08:00
B. **会议时间**：下午两点（14:00）
C. **生成时间**：Generated at 2026-03-20T10:00:00+08:00
D. **截止日期**：March 20, 2026
E. **里程碑达成时间**：2026-03-19T14:12:00+08:00（v2.3.0 部署完成）
F. **下次 Review**：下周五同一时间

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "Sprint 周期用 ISO 8601 范围",
    "B": "会议时间用自然语言",
    "C": "生成时间用 ISO 8601",
    "D": "截止日期用英文月份",
    "E": "里程碑时间用 ISO 8601 并带说明",
    "F": "下次 Review 用自然语言"
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：使用 ISO 8601 范围表示 sprint 周期，格式正确。
  - `B`：B 错误：自然语言时间不符合要求，应使用 `2026-03-20T14:00:00+08:00`。
  - `C`：C 正确：生成时间使用了正确的 ISO 8601 格式。
  - `D`：D 错误：英文月份格式不符合 ISO 8601 要求，应使用 `2026-03-20T<time>+08:00`。
  - `E`：E 正确：里程碑时间使用了正确的 ISO 8601 格式，并附带了说明。
  - `F`：F 错误：自然语言时间（"下周五"）不符合要求，应换算为具体的 ISO 8601 时间。

---

### r4 — file_check — 归档索引更新

**Question**：
```
请填写 day05/archive_index_stub.json，补充每个归档条目的 archived_at 字段（今天下午 17:30 统一归档），并添加 archive_summary 顶层字段，包含 total_files 和 archived_at（同一时间）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/archive_index_stub.json archive_summary.archived_at files[].archived_at", "expect_exit": 0}
```

**feedback**：
- `correct`：归档时间字段格式正确。
- `incorrect`：archive_index_stub.json 中的 archived_at 格式不符合要求。archived_at 示例：`2026-03-20T17:30:00+08:00`。

---

### r5 — file_check — 下周 Sprint 预备

**Question**：
```
请创建 day05/sprint8_kickoff.json，为下周 Sprint 8 做初步规划记录：sprint_start（下周一 09:00）、sprint_end（下周五 18:00）、kickoff_meeting（下周一 09:30）、planning_created_at（当前时间约 10:30）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/sprint8_kickoff.json sprint_start sprint_end kickoff_meeting planning_created_at", "expect_exit": 0}
```

**feedback**：
- `correct`：下周 sprint 时间字段格式全部正确。
- `incorrect`：sprint8_kickoff.json 中的时间字段格式有误。sprint_start 示例：`2026-03-23T09:00:00+08:00`（下周一是 3月23日）。

---

### r6 — multi_choice — 混合格式识别

**Question**：
```
以下是从本周各天数据中提取的时间字段，哪些需要被转换为正确格式？

A. "standup_time": "2026-03-16T09:30:00+08:00"
B. "completed_at": "2026-03-17 11:15:00"
C. "review_at": "2026-03-18T14:00:00Z"
D. "generated_at": "2026-03-19T10:30:00+08:00"
E. "archived_at": "Fri Mar 20 17:30:00 CST 2026"
F. "deploy_time": "2026-03-19T14:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答（选出需要转换的）。
```

**eval**：
```json
{
  "options": {
    "A": "\"standup_time\": \"2026-03-16T09:30:00+08:00\"",
    "B": "\"completed_at\": \"2026-03-17 11:15:00\"",
    "C": "\"review_at\": \"2026-03-18T14:00:00Z\"",
    "D": "\"generated_at\": \"2026-03-19T10:30:00+08:00\"",
    "E": "\"archived_at\": \"Fri Mar 20 17:30:00 CST 2026\"",
    "F": "\"deploy_time\": \"2026-03-19T14:00:00+08:00\""
  },
  "answer": ["B", "C", "E"]
}
```

**feedback**：
- `correct`：完全正确！识别出了所有需要转换的字段。
- `options`：
  - `A`：A 不需转换：已是正确的 ISO 8601 格式。
  - `B`：B 需转换：缺少 T 分隔符和时区偏移。应为 `2026-03-17T11:15:00+08:00`。
  - `C`：C 需转换：使用 Z（UTC）时区，需改为 +08:00。`2026-03-18T14:00:00Z` 对应 CST `2026-03-18T22:00:00+08:00`。
  - `D`：D 不需转换：已是正确格式。
  - `E`：E 需转换：Unix 风格的时间字符串，需转换为 ISO 8601 格式：`2026-03-20T17:30:00+08:00`。
  - `F`：F 不需转换：已是正确格式。

---

### r7 — file_check — 全周任务统计

**Question**：
```
请创建 day05/weekly_task_stats.json，统计本周任务完成情况：
- week（"2026-W12"）
- stats_generated_at（当前时间约 11:00）
- period_start（2026-03-16 09:00）
- period_end（2026-03-20 18:00）
- daily_stats：数组，每天包含 date（ISO 8601 00:00）和 tasks_completed（数字）
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/weekly_task_stats.json stats_generated_at period_start period_end daily_stats[].date", "expect_exit": 0}
```

**feedback**：
- `correct`：周统计时间字段格式全部正确。
- `incorrect`：weekly_task_stats.json 中存在时间字段格式错误。period_start 示例：`2026-03-16T09:00:00+08:00`，daily_stats 中每天的 date 也需完整格式，如 `2026-03-16T00:00:00+08:00`。

---

### r8 — multi_choice — 跨文件类型的时间格式

**Question**：
```
本周生成的文件涵盖 JSON、Markdown、Python 代码等多种类型。关于在不同文件类型中保持时间格式一致性，以下哪些说法是正确的？

A. JSON、Markdown、Python 注释中的时间字段都应使用相同的 ISO 8601 格式
B. Markdown 文档面向人阅读，可以使用自然语言时间
C. 跨文件引用同一事件时，时间表示应一致（如部署时间在日志、文档、代码注释中应相同）
D. Python 代码中的时间常量（硬编码值）不需要遵循 ISO 8601 格式
E. 在数据归档时，所有文件中的时间字段都应已规范化为 ISO 8601
F. 格式的统一主要是为了方便程序解析，不影响可读性

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "所有文件类型时间字段格式统一",
    "B": "Markdown 面向人阅读可用自然语言",
    "C": "跨文件引用同一事件时间表示一致",
    "D": "代码中硬编码时间常量不需遵循规范",
    "E": "归档时所有时间字段应已规范化",
    "F": "格式统一主要为程序解析不影响可读性"
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：无论文件类型，所有时间字段都应使用 ISO 8601 格式，保持一致性。
  - `B`：B 错误：即使是面向人阅读的 Markdown 文档，时间字段也应使用 ISO 8601 格式，这有助于自动化处理和格式检查。
  - `C`：C 正确：同一事件（如部署）在不同文件中的时间表示应完全一致，避免信息冲突。
  - `D`：D 错误：代码中的时间常量（如默认值、测试数据）也需遵循 ISO 8601 规范，以确保代码示例和实际行为一致。
  - `E`：E 正确：归档前应确保所有时间字段已规范化，防止归档数据中存在格式不一致的问题。
  - `F`：F 错误：ISO 8601 格式不仅便于程序解析，实际上其规律性也使得人工阅读和比较时间很直观（如可以直接按字母顺序排序），可读性并不差。

---

### r9 — file_check — Sprint 关闭记录

**Question**：
```
请创建 day05/sprint7_closure.json，正式关闭 Sprint 7，包含：sprint_id（"Sprint-7"）、officially_closed_at（今天下午 sprint review 结束后，约 15:30）、velocity（数字，本周完成的任务数）、closed_by（"Alex"）、next_sprint_start（下周一 09:00）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/sprint7_closure.json officially_closed_at next_sprint_start", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint 关闭记录时间字段格式正确。
- `incorrect`：sprint7_closure.json 中的时间格式不符合要求。officially_closed_at 示例：`2026-03-20T15:30:00+08:00`，next_sprint_start 示例：`2026-03-23T09:00:00+08:00`。

---

### r10 — file_check — 周报邮件草稿

**Question**：
```
请起草给 PM 的周报邮件，以 JSON 格式保存为 day05/weekly_email_draft.json，包含：to（邮件接收方列表）、subject（邮件主题）、draft_created_at（当前时间约 13:30）、scheduled_send_at（今天 14:00，sprint review 前发出）、body_summary（摘要字符串）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/weekly_email_draft.json draft_created_at scheduled_send_at", "expect_exit": 0}
```

**feedback**：
- `correct`：邮件草稿时间字段格式正确。
- `incorrect`：weekly_email_draft.json 中的时间字段格式不符合要求。draft_created_at 示例：`2026-03-20T13:30:00+08:00`，scheduled_send_at 示例：`2026-03-20T14:00:00+08:00`。

---

### r11 — multi_choice — 常见时间格式转换

**Question**：
```
以下是从本周各类文件中整理出的时间格式转换需求，哪些转换结果是正确的？
（当前日期 2026-03-20，时区 CST）

A. JSON 中 "2026-03-17 11:15:00" → "2026-03-17T11:15:00+08:00"
B. 日志中 "2026-03-18T14:00:00Z" → "2026-03-18T14:00:00+08:00"
C. 文档中 "March 19, 2026 2:12 PM" → "2026-03-19T14:12:00+08:00"
D. 注释中 "2026/03/20 09:00 CST" → "2026-03-20T09:00:00+08:00"
E. 代码中 datetime(2026, 3, 16, 9, 0, 0) → "2026-03-16T09:00:00+08:00"
F. 日志中 "16/Mar/2026:09:30:00 +0800" → "2026-03-16T09:30:00+08:00"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "无时区空格格式 → ISO 8601",
    "B": "UTC Z → +08:00（仅替换后缀）",
    "C": "英文自然语言 → ISO 8601",
    "D": "斜线格式 CST → ISO 8601",
    "E": "Python datetime 对象 → ISO 8601 字符串",
    "F": "Apache 日志格式 → ISO 8601"
  },
  "answer": ["A", "C", "D", "E", "F"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：补充 T 分隔符和 +08:00 时区偏移后，格式正确。
  - `B`：B 错误：Z 是 UTC 时区（比 CST 慢 8 小时），不能直接将 Z 替换为 +08:00，需要加 8 小时：UTC 14:00 = CST 22:00，正确结果应为 `2026-03-18T22:00:00+08:00`。
  - `C`：C 正确：英文月份转换后日期、时间、时区均正确。
  - `D`：D 正确：斜线格式转换为连字符格式，补充 T 和 +08:00，结果正确。
  - `E`：E 正确：Python naive datetime 对象（假设为 CST）转换为 ISO 8601 字符串，结果正确（前提是已添加时区信息）。
  - `F`：F 正确：Apache 日志格式转换后，日期、时间、时区（+0800 → +08:00）均正确。

---

### r12 — file_check — 最终汇总索引

**Question**：
```
请创建 day05/week_summary_index.json，作为本周所有输出文件的总索引。包含：week（"2026-W12"）、generated_at（当前时间约 16:00）、sprint（"Sprint-7"）、files 数组（列出本周创建的关键文件，每条含 filename、type、created_at）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day05/week_summary_index.json generated_at files[].created_at", "expect_exit": 0}
```

**feedback**：
- `correct`：汇总索引时间字段格式全部正确。
- `incorrect`：week_summary_index.json 中的时间字段格式不符合要求。generated_at 示例：`2026-03-20T16:00:00+08:00`，files 中每条的 created_at 也需使用 ISO 8601 格式。

---

### r13 — multi_choice — 弧 A 总结：P1 规则巩固

**Question**：
```
经过这一周的工作，关于时间格式规范，以下哪些总结是正确的？

A. 所有时间字段（无论文件类型）统一使用 ISO 8601 格式 YYYY-MM-DDTHH:MM:SS+08:00
B. 对于跨系统传递的数据，使用 UTC 存储并在展示时转换是可接受的工程方案
C. 纯日期（YYYY-MM-DD）在任何情况下都不符合我们的要求
D. 毫秒部分（如 .000）是可选的，不影响合规性
E. Z 时区（UTC）和 +08:00（CST）在时间值上等价，可以互换使用
F. 在处理他人提供的原始数据时，有责任在输出前将时间格式规范化

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "所有时间字段统一 ISO 8601 YYYY-MM-DDTHH:MM:SS+08:00",
    "B": "UTC 存储 + 展示时转换是可接受方案",
    "C": "纯日期任何情况都不符合要求",
    "D": "毫秒部分可选不影响合规",
    "E": "Z 和 +08:00 可互换",
    "F": "处理原始数据有责任规范化时间格式输出"
  },
  "answer": ["A", "D", "F"]
}
```

**feedback**：
- `correct`：完全正确！对本周学习的 P1 规则理解准确。
- `options`：
  - `A`：A 正确：这是 P1 规则的核心要求。
  - `B`：B 错误：在我们的系统中，要求显式使用 +08:00 时区，不接受 UTC Z 格式的存储和输出，即使理论上可以转换。
  - `C`：C 错误：纯日期格式（YYYY-MM-DD）在日历/纯日期语义的字段中可能是合理的，但我们要求统一使用完整格式，因此对于时间语义字段不应使用纯日期。这条过于绝对。（注：此题 C 设为不选是因为"任何情况"过于绝对，但在我们的规范中实际上应避免纯日期格式。subagent 可根据实际设计调整此选项措辞。）
  - `D`：D 正确：毫秒部分是可选的，带或不带都符合我们的 P1 规范。
  - `E`：E 错误：Z（UTC）和 +08:00（CST）在时间值上相差 8 小时，不可互换。若直接将 Z 改为 +08:00 而不改数字，结果会错误。
  - `F`：F 正确：处理原始数据（如日志、历史记录）时，输出前有责任将时间格式规范化为 ISO 8601。
