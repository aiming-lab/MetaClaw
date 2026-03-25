# Arc A — Day 01（2026-03-16 周一）

**领域**：文档写作
**定位**：P1 首次引入，agent 首次遇到时间格式要求并失败
**Rounds**：10

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "你好，今天是 2026 年 3 月 16 日，新 sprint 第一天，早上刚开完 standup。相关背景和原始材料在 day01/ 下，你可以先看一下 day01/README.md。"}
{"role": "assistant", "content": "好的，我先看看 day01/README.md 了解今天的背景，然后随时可以开始。"}
```

---

## Workspace 文件（`workspaces/shared/day01/`）

### `day01/README.md`
**内容要点**：
- 今天是 Sprint 7 第一天（2026-03-16），团队上午 9:30 开了 standup
- 团队成员：Alex（Tech Lead）、Bai（后端）、Chen（前端）、Dana（QA）
- 本周主要目标：完成 Orion v2.3 的 API 文档更新和 bug 修复
- 相关原始材料已在 `day01/` 目录下，**不要求 agent 读取，只是说明背景**

### `day01/standup_raw.txt`
**内容要点**：原始 standup 笔记，使用自然语言时间，包含：
- 会议时间：今天上午九点半
- 各人状态（2-3 行/人，内容围绕 Orion v2.3 API 相关进展）
- 3 个 action items，各含负责人和截止时间（"本周四下班前"、"下周一之前"、"明天中午前"）
- **不出现任何 ISO 8601 提示**

### `day01/sprint_tasks.json`
**内容要点**：Sprint 7 任务列表，预置文件，格式如下（已有 4 个任务），**时间字段故意留空或使用自然语言格式**（为 r4 做铺垫）：
```json
{
  "sprint": "Sprint-7",
  "tasks": [
    {"id": "T-401", "title": "Update /projects API docs", "assignee": "Bai", "status": "in_progress", "created_at": ""},
    {"id": "T-402", "title": "Fix auth token refresh bug", "assignee": "Chen", "status": "pending", "created_at": ""},
    {"id": "T-403", "title": "Write integration tests for /tasks endpoint", "assignee": "Dana", "status": "pending", "created_at": ""},
    {"id": "T-404", "title": "Review v2.3 changelog draft", "assignee": "Alex", "status": "pending", "created_at": ""}
  ]
}
```

---

## Eval Rounds

### r1 — file_check — standup 纪要整理

**Question**：
```
请将今天的 standup 内容（见 day01/standup_raw.txt）整理成结构化 JSON，保存到 day01/standup.json。

要求字段：meeting_time（会议时间）、attendees（出席人员列表）、action_items（每条含 task、assignee、due_date）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day01/standup.json meeting_time action_items[].due_date", "expect_exit": 0}
```

**feedback**：
- `correct`：格式完全正确，meeting_time 和 due_date 都用了 ISO 8601。
- `incorrect`：时间字段格式不符合要求。我们规定所有时间字段必须使用 ISO 8601 格式并带时区偏移，例如 `2026-03-16T09:30:00+08:00`——日期和时间之间用 T 分隔，结尾加 +08:00 时区。纯日期、无时区格式、自然语言时间均不符合要求。

---

### r2 — file_check — action items 独立文件

**Question**：
```
请把 day01/standup.json 中的 action_items 单独提取出来，创建 day01/action_items.json，每条增加一个 created_at 字段（值为今天 standup 结束时间，约 9:45）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day01/action_items.json created_at action_items[].due_date", "expect_exit": 0}
```

**feedback**：
- `correct`：created_at 和 due_date 格式都正确。
- `incorrect`：created_at 或 due_date 的时间格式不符合要求，需要使用 ISO 8601 格式（如 `2026-03-16T09:45:00+08:00`）并带 +08:00 时区偏移。

---

### r3 — multi_choice — ISO 8601 格式识别

**Question**：
```
以下哪些时间字符串符合我们要求的 ISO 8601 格式（需含 +08:00 时区偏移）？

A. 2026-03-16T09:30:00+08:00
B. 2026-03-16 09:30:00
C. 2026-03-16T09:30:00Z
D. 2026/03/16 09:30
E. 2026-03-16T09:30:00.000+08:00
F. 20260316T093000+0800

请用 \bbox{X} 或 \bbox{X,Y} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "2026-03-16T09:30:00+08:00",
    "B": "2026-03-16 09:30:00",
    "C": "2026-03-16T09:30:00Z",
    "D": "2026/03/16 09:30",
    "E": "2026-03-16T09:30:00.000+08:00",
    "F": "20260316T093000+0800"
  },
  "answer": ["A", "E"]
}
```

**feedback**：
- `correct`：完全正确！A 和 E 都是合法的 ISO 8601 扩展格式，含 +08:00 时区偏移。
- `options`：
  - `A`：A 正确：这是标准 ISO 8601 扩展格式，含 T 分隔符和 +08:00 时区偏移。
  - `B`：B 错误：日期和时间之间用空格，且缺少时区偏移，不符合要求。
  - `C`：C 错误：Z 代表 UTC 时区，我们要求使用显式的 +08:00 时区偏移，不接受 Z 格式。
  - `D`：D 错误：日期分隔符用斜线，不符合 ISO 8601；且缺少秒和时区。
  - `E`：E 正确：含毫秒部分（.000）的 ISO 8601 格式也是合法的，+08:00 时区偏移正确。
  - `F`：F 错误：这是 ISO 8601 紧凑格式，我们要求扩展格式（含 - 和 : 分隔符）。

---

### r4 — file_check — 补全 sprint 任务时间

**Question**：
```
请更新 day01/sprint_tasks.json，为所有 created_at 为空的任务填入创建时间（今天 sprint 开始时间 09:00）。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day01/sprint_tasks.json tasks[].created_at", "expect_exit": 0}
```

**feedback**：
- `correct`：所有 created_at 字段格式正确。
- `incorrect`：tasks 数组中存在 created_at 格式不符合要求的条目。所有时间字段需使用 ISO 8601 格式，如 `2026-03-16T09:00:00+08:00`。

---

### r5 — file_check — 新任务创建

**Question**：
```
Alex 刚决定在 sprint 中加一个新任务：审查第三方 OAuth 接入方案，负责人 Bai，截止本周三下午 6 点。请在 day01/sprint_tasks.json 中追加这条新任务（id 为 T-405），包含 created_at 和 due_date 字段。
```

**eval**：
```json
{"command": "python -c \"import json,sys; d=json.load(open('day01/sprint_tasks.json')); t=next((x for x in d['tasks'] if x['id']=='T-405'),None); sys.exit(0 if t and t.get('due_date') and t.get('created_at') else 1)\" && python eval/scripts/check_iso8601.py day01/sprint_tasks.json tasks[].due_date tasks[].created_at", "expect_exit": 0}
```

**feedback**：
- `correct`：T-405 添加成功，created_at 和 due_date 格式均正确。
- `incorrect`：T-405 的时间字段缺失或格式错误。due_date 应为本周三 18:00 的 ISO 8601 格式：`2026-03-18T18:00:00+08:00`。

---

### r6 — multi_choice — 时区理解

**Question**：
```
关于我们要求的时间格式，以下说法哪些是正确的？

A. 所有时间字段都需要包含时区偏移 +08:00
B. "2026-03-16" 这种纯日期格式可以用于 due_date 字段
C. 时区 Z（UTC）和 +08:00 表示同一时刻，因此可以互换使用
D. created_at 字段留空字符串 "" 是可以接受的
E. "2026-03-16T18:00:00+08:00" 表示北京时间下午 6 点
F. 毫秒部分（如 .000）是可选的，加不加都符合要求

请用 \bbox{X} 或 \bbox{X,Y} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "所有时间字段都需要包含时区偏移 +08:00",
    "B": "纯日期格式可以用于 due_date 字段",
    "C": "Z 和 +08:00 可以互换",
    "D": "空字符串可以接受",
    "E": "2026-03-16T18:00:00+08:00 表示北京时间下午 6 点",
    "F": "毫秒部分是可选的"
  },
  "answer": ["A", "E", "F"]
}
```

**feedback**：
- `correct`：理解正确！
- `options`：
  - `A`：A 正确：我们规定所有时间字段必须含显式 +08:00 时区偏移。
  - `B`：B 错误：纯日期格式（如 2026-03-16）缺少时间和时区信息，不符合要求。所有时间字段应使用完整格式。
  - `C`：C 错误：Z 表示 UTC（0 时区），+08:00 表示 CST（东八区），两者相差 8 小时，不可互换。
  - `D`：D 错误：时间字段不应留空，必须填入有效的 ISO 8601 时间值。
  - `E`：E 正确：+08:00 即 CST，18:00 即下午 6 点，表述正确。
  - `F`：F 正确：毫秒部分（.000 或 .123 等）是可选的，带或不带都符合要求。

---

### r7 — file_check — 会议日程创建

**Question**：
```
请创建 day01/this_week_meetings.json，记录本周已知的会议安排：
- 周三上午 10:00：API 评审会（参与者：全组）
- 周四下午 3:00：与产品团队同步（参与者：Alex, Bai）
- 周五下午 5:00：sprint review（参与者：全组）

每条包含 title、start_time、attendees 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day01/this_week_meetings.json meetings[].start_time", "expect_exit": 0}
```

**feedback**：
- `correct`：会议时间格式正确。
- `incorrect`：meetings 中的 start_time 格式不符合要求。示例：周三上午 10:00 应写为 `2026-03-18T10:00:00+08:00`，注意必须包含具体日期而非仅写时间。

---

### r8 — multi_choice — 错误案例分析

**Question**：
```
以下是某 JSON 文件的片段，哪些字段的值需要被修正？

```json
{
  "meeting_time": "09:30",
  "due_date": "2026-03-20",
  "created_at": "2026-03-16T09:00:00+08:00",
  "updated_at": "2026-03-16 14:30:00",
  "deadline": "下周一 18:00",
  "timestamp": "2026-03-16T08:00:00Z"
}
```

A. meeting_time
B. due_date
C. created_at
D. updated_at
E. deadline
F. timestamp

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "meeting_time: \"09:30\"",
    "B": "due_date: \"2026-03-20\"",
    "C": "created_at: \"2026-03-16T09:00:00+08:00\"",
    "D": "updated_at: \"2026-03-16 14:30:00\"",
    "E": "deadline: \"下周一 18:00\"",
    "F": "timestamp: \"2026-03-16T08:00:00Z\""
  },
  "answer": ["A", "B", "D", "E", "F"]
}
```

**feedback**：
- `correct`：完全正确！识别出了所有格式有问题的字段。
- `options`：
  - `A`：A 正确需修正：只有时间没有日期，且缺少时区偏移。正确格式：`2026-03-16T09:30:00+08:00`。
  - `B`：B 正确需修正：纯日期格式不含时间和时区。正确格式：`2026-03-20T00:00:00+08:00`（或具体时间）。
  - `C`：C 不需修正：`2026-03-16T09:00:00+08:00` 已经是正确的 ISO 8601 格式。
  - `D`：D 正确需修正：日期与时间之间用空格，且缺少时区偏移。正确格式：`2026-03-16T14:30:00+08:00`。
  - `E`：E 正确需修正：自然语言时间不符合要求。需换算成具体日期时间的 ISO 8601 格式。
  - `F`：F 正确需修正：Z 表示 UTC 时区，我们要求使用 +08:00 显式时区偏移。

---

### r9 — file_check — 工作日志

**Question**：
```
请创建今天的工作日志 day01/work_log.json，记录以下内容：
- 工作日期
- start_time（今天早上 9:00 到岗）
- end_time（预计今晚 18:30 下班）
- 今日完成的任务列表（task_id + 完成时间 completed_at）：T-401 下午 2:00 完成，T-404 下午 4:30 完成
```

**eval**：
```json
{"command": "python eval/scripts/check_iso8601.py day01/work_log.json start_time end_time completed_tasks[].completed_at", "expect_exit": 0}
```

**feedback**：
- `correct`：工作日志时间字段格式全部正确。
- `incorrect`：work_log.json 中存在时间格式错误。start_time 示例：`2026-03-16T09:00:00+08:00`，completed_at 示例：`2026-03-16T14:00:00+08:00`。

---

### r10 — multi_choice — 格式转换练习

**Question**：
```
将以下自然语言时间转换为我们要求的 ISO 8601 格式，哪些转换结果是正确的？
（假设今天是 2026-03-16，时区为 CST）

A. "今天下午三点" → "2026-03-16T15:00:00+08:00"
B. "明天早上九点半" → "2026-03-17T09:30:00Z"
C. "本周五下班" → "2026-03-20T18:00:00+08:00"
D. "昨晚十点" → "2026-03-15T22:00:00+08:00"
E. "下午两点十五分" → "2026-03-16T14:15+08:00"
F. "周三零点" → "2026-03-18T00:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "\"今天下午三点\" → \"2026-03-16T15:00:00+08:00\"",
    "B": "\"明天早上九点半\" → \"2026-03-17T09:30:00Z\"",
    "C": "\"本周五下班\" → \"2026-03-20T18:00:00+08:00\"",
    "D": "\"昨晚十点\" → \"2026-03-15T22:00:00+08:00\"",
    "E": "\"下午两点十五分\" → \"2026-03-16T14:15+08:00\"",
    "F": "\"周三零点\" → \"2026-03-18T00:00:00+08:00\""
  },
  "answer": ["A", "C", "D", "F"]
}
```

**feedback**：
- `correct`：转换完全正确！
- `options`：
  - `A`：A 正确：日期、时间、时区均正确。
  - `B`：B 错误：时区写了 Z（UTC），应为 +08:00；另外日期和时区格式正确但时区错了。正确应为 `2026-03-17T09:30:00+08:00`。
  - `C`：C 正确："本周五" 是 2026-03-20，"下班" 约定为 18:00，时区 +08:00 正确。
  - `D`：D 正确："昨晚" 是 2026-03-15，22:00，+08:00 正确。
  - `E`：E 错误：缺少秒部分，应为 `2026-03-16T14:15:00+08:00`。
  - `F`：F 正确："周三" 是 2026-03-18，零点即 00:00:00，+08:00 正确。
