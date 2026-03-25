# MetaClaw Evolution Benchmark — Data Structure Spec

## 目录结构

```
metaclaw-bench/
├── all_tests.json
├── eval/
│   ├── scripts/               # exec_check 用的预置验证脚本（跨 scenario 共用）
│   │   ├── check_iso8601.py
│   │   └── ...
│   ├── day01/
│   │   └── questions.json
│   ├── day02/
│   └── ...
├── openclaw_state/
│   ├── openclaw.json
│   └── agents/
│       └── metaclaw_agent/
│           └── sessions/
│               ├── day01_<uuid>.jsonl
│               ├── day02_<uuid>.jsonl
│               └── ...
└── workspaces/
    └── shared/                # 所有 scenario 共用同一 workspace 源目录
        ├── AGENTS.md
        ├── IDENTITY.md
        ├── SOUL.md
        ├── TOOLS.md
        ├── USER.md
        ├── day01/             # 每天任务素材互不依赖
        ├── day02/
        └── ...
```

**Workspace 隔离**：runner 在整体运行前将 `workspaces/shared/` 复制到临时目录多份，每份副本路径通过 `openclaw.json` 的 `workspace` 字段注入（runner 动态覆盖），且只包含标记为该天内容(dayXX)，不包含其他日期。源目录保持只读。

**Agent 与 workspace 的交互**：agent 通过工具调用（read_file / write_file / execute_command 等）与 workspace 目录交互，输出内容直接写入 workspace 文件，不依赖回复文本内联。eval 只有两种类型：`multi_choice`（agent 回复中给出选项）和 `file_check`（执行命令验证 workspace 文件或脚本输出）。

---

## all_tests.json

```json
{
  "name": "MetaClaw-Evolution-Bench",
  "openclaw_state_dir": "./data/metaclaw-bench/openclaw_state",
  "eval_dir": "./data/metaclaw-bench/eval",
  "workspace_src": "./data/metaclaw-bench/workspaces/shared",
  "test": [
    {
      "id": "day01",
      "desc": "Day 1 — 引入时间格式偏好",
      "agent": "metaclaw_agent",
      "session": "day01_<uuid>",
      "history_sessions": [],
      "eval": "day01",
      "arc": "A",
      "preference_tags": ["output_format"]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `workspace_src` | 共享 workspace 源目录，runner 每次复制后使用副本 |
| `arc` | 所属学习弧（`A`/`B`/`C`/`mixed`），供分组统计 |
| `preference_tags` | 涉及的偏好类别代号列表，供学习曲线分析，实际代码不使用 |

---

## questions.json

每个 `eval/dayXX/questions.json` 是一个对象，包含若干 round：

```json
{
  "id": "day01",
  "desc": "时间格式偏好引入",
  "rounds": [
    { ...round 对象... },
    { ...round 对象... }
  ]
}
```

---

## Round 对象

```json
{
  "id": "r1",
  "type": "<eval_type>",
  "question": "请整理今天下午三点的会议纪要，保存到 tasks/day01/meeting.json。",
  "feedback": { },
  "eval": { },
  "update": []
}
```

`feedback` 的结构因 `type` 而异，见下方各类型说明。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | round 唯一标识，如 `r1` |
| `type` | string | 是 | eval 类型，见下方定义 |
| `question` | string | 是 | 本轮任务描述，由 runner 原样注入为 user 消息；`eval` 字段内容不拼入消息 |
| `feedback` | object | 是 | 反馈文本，结构因 eval type 而异（见下方各类型说明） |
| `eval` | object | 是 | 类型相关的评判字段，见下方各类型定义 |
| `update` | array | 否 | 本轮**问题发布前**执行的状态变更（保留字段，当前数据集不使用）|

### Feedback 注入机制

runner 评分后，在发布下一轮 question 前，将反馈以固定模板拼接：

```
[上一步反馈] {feedback_text}

{question_text}
```

**最后一轮**无后续 question，runner 单独发送一条 user 消息：

```
[上一步反馈] {feedback_text}
```

该消息不计入评分，仅作为训练信号供 MetaClaw 学习。

`feedback_text` 的生成方式因 eval type 而异：

- **`file_check`**：通过 → `feedback.correct`；失败 → `feedback.incorrect`
- **`multi_choice`**：见下方「multi_choice feedback 生成规则」


---

## Eval 类型

### multi_choice

agent 以 `\bbox{X}` 或 `\bbox{A,B}` 格式作答，提取字母做集合精确匹配。每题 5–10 个选项，选项数量在题目间有所波动。

**完整 round 示例：**

```json
{
  "id": "r1",
  "type": "multi_choice",
  "question": "以下关于时间格式的说法，哪些正确？\n\nA. ISO 8601 示例：2026-03-13T15:00:00+08:00\nB. Unix 时间戳属于 ISO 8601\nC. 时区偏移不可省略\nD. 日期与时间之间用空格分隔符合 ISO 8601\n\n请用 \\bbox{X} 或 \\bbox{X,Y} 格式作答。",
  "feedback": {
    "correct": "完全正确！对 ISO 8601 格式的理解很准确。",
    "options": {
      "A": "A 正确：这是标准 ISO 8601 格式，含日期、时间和时区偏移。",
      "B": "B 错误：Unix 时间戳是整数，不是 ISO 8601 格式。",
      "C": "C 正确：时区偏移（如 +08:00）是必须的，不能省略。",
      "D": "D 错误：ISO 8601 要求用 'T' 分隔日期与时间，不是空格。"
    }
  },
  "eval": {
    "options": {
      "A": "ISO 8601 示例：2026-03-13T15:00:00+08:00",
      "B": "Unix 时间戳属于 ISO 8601",
      "C": "时区偏移不可省略",
      "D": "日期与时间之间用空格分隔符合 ISO 8601"
    },
    "answer": ["A", "C"]
  },
  "update": []
}
```

**feedback 字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feedback.correct` | string | 是 | 精确匹配（全对无多选）时注入的鼓励反馈 |
| `feedback.options` | object | 是 | 每个选项的解释文本，key 与 `eval.options` 完全一致 |
| `feedback.options[X]` | string | 是 | 解释该选项为何正确或为何错误（用于动态组装错误反馈） |

**multi_choice feedback 生成规则：**

- **精确匹配** → 注入 `feedback.correct`
- **未精确匹配** → 动态拼接，按选项字母顺序：
  - 漏选的正确选项（应选未选）：`你漏选了 {X}：{feedback.options[X]}`
  - 错选的错误选项（不该选但选了）：`你错选了 {Y}：{feedback.options[Y]}`

示例（正确答案 A、C，agent 选了 A、B）：

```
你漏选了 C：C 正确：时区偏移（如 +08:00）是必须的，不能省略。
你错选了 B：B 错误：Unix 时间戳是整数，不是 ISO 8601 格式。
```

---

### file_check

验证 agent 在 workspace 生成的文件能否通过已有脚本评测，或者生成本身就能以特定命令执行的脚本。

**feedback 字段：**

```json
"feedback": {
  "correct": "文件格式正确！",
  "incorrect": "时间字段格式有误，请使用 ISO 8601 格式（如 2026-03-13T15:00:00+08:00）。"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feedback.correct` | string | 是 | 命令通过时注入的正向反馈 |
| `feedback.incorrect` | string | 是 | 命令失败时注入的纠错反馈，需包含具体说明 |

**eval 字段：**

```json
"eval": {
  "command": "python script/check_meeting.py day01/meeting.json",
  "expect_exit": 0,
  "expect_stdout": "OK"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是 | 在 workspace 目录下执行的 shell 命令 |
| `expect_exit` | int | 否 | 期望的退出码，默认 0 |
| `expect_stdout` | string | 否 | 期望 stdout 包含的字符串 |
| `expect_stdout_regex` | bool | 否 | 为 true 时 expect_stdout 作正则匹配，默认 false |
| `timeout` | int | 否 | 超时秒数，默认 30 |

---

## Session 文件格式（初始上下文）

每个 `dayXX_<uuid>.jsonl` 包含 1–2 轮引导对话，内容极简：

```jsonl
{"role": "user", "content": "你好，我是 Alex，今天是周一。本周我主要在处理项目 Orion 的交付工作，相关文件都在 tasks/day01/ 下，你可以先看一下 tasks/day01/README.md 了解背景。"}
{"role": "assistant", "content": "好的，我已经了解了今天的任务背景，随时可以开始。"}
```

不包含任何具体任务，任务全部由 eval round 注入。

---

## openclaw.json

```json
{
  "agents": {
    "defaults": {
      "model": { "primary": "benchmark/${BENCHMARK_MODEL}" },
      "compaction": { "mode": "safeguard" }
    },
    "list": [
      {
        "id": "metaclaw_agent",
        "name": "metaclaw_agent",
        "workspace": "${BENCHMARK_WORKSPACE_DIR}",
        "agentDir": "${SIMPLEMEM_ROOT}/benchmark/data/metaclaw-bench/openclaw_state/agents/metaclaw_agent/agent"
      }
    ]
  }
}
```

`BENCHMARK_WORKSPACE_DIR` 是占位符，由 runner 在每次 scenario 运行前设置为 workspace 副本路径。
