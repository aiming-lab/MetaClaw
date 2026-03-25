# Arc E — 叙事基准（Narrative）

> 本弧真相基准。subagent 造数据时必须读取本文件。

---

## 本弧核心偏好：P5 完成状态日志

**精确规则**：见 `data-spec/preferences.md` P5 节。

**核心要求**：每次任务完成后，在 workspace 根目录的 `done.log` 末尾追加一行：

```
[DONE] <ISO 8601 +08:00 timestamp> | <task_id> | <one-line summary>
```

- `task_id`：agent 自定，建议反映任务内容（如 `standup_notes`、`api_report`）
- `summary`：不超过 80 字符，简述完成内容
- 文件不存在时自动创建
- 每完成一个独立任务追加一行，不合并

**合法示例**：
```
[DONE] 2026-04-13T10:30:00+08:00 | weekly_plan | 创建了第五周工作计划，5个任务条目
[DONE] 2026-04-13T11:15:00+08:00 | sprint9_kickoff | 整理了 Sprint 9 启动材料
```

**P1-P4 仍然有效**：所有前序规则继续适用。

---

## 日期设定

| Day | 日期 | 星期 |
|-----|------|------|
| 21 | 2026-04-13 | 周一 |
| 22 | 2026-04-14 | 周二 |
| 23 | 2026-04-15 | 周三 |
| 24 | 2026-04-16 | 周四 |
| 25 | 2026-04-17 | 周五 |

---

## eval 脚本：check_done_log.py

**存放路径**：`eval/scripts/check_done_log.py`（arc-E 数据创建时一并创建）

**接口**：
```
python eval/scripts/check_done_log.py done.log [--task-prefix <prefix>] [--min-entries N]
```

- 检查 `done.log` 存在且非空
- 检查最后一行（或所有行）符合 `[DONE] <ISO8601+08:00> | <task_id> | <summary>` 格式
- `--task-prefix`：若指定，检查最后一条 task_id 以该前缀开头
- `--min-entries N`：检查至少有 N 条记录
- Exit 0 + `OK`：通过
- Exit 1 + `FAIL: <说明>`：格式错误或条件不满足

**完整实现**：

```python
#!/usr/bin/env python3
"""check_done_log.py — validate P5 done.log entries."""
import argparse, re, sys, os

LINE_PATTERN = re.compile(
    r'^\[DONE\] (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00) \| ([^\|]+) \| (.+)$'
)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('logfile')
    parser.add_argument('--task-prefix', default=None)
    parser.add_argument('--min-entries', type=int, default=1)
    args = parser.parse_args()

    if not os.path.exists(args.logfile):
        fail(f"done.log not found: {args.logfile}")

    lines = [l.rstrip('\n') for l in open(args.logfile, encoding='utf-8') if l.strip()]
    if len(lines) < args.min_entries:
        fail(f"expected >= {args.min_entries} entries, found {len(lines)}")

    for i, line in enumerate(lines):
        m = LINE_PATTERN.match(line)
        if not m:
            fail(f"line {i+1} does not match format: {line!r}")
        summary = m.group(4).strip()
        if len(summary) > 80:
            fail(f"line {i+1} summary exceeds 80 chars ({len(summary)}): {summary!r}")

    if args.task_prefix:
        last = lines[-1]
        m = LINE_PATTERN.match(last)
        task_id = m.group(3).strip()
        if not task_id.startswith(args.task_prefix):
            fail(f"last entry task_id {task_id!r} does not start with {args.task_prefix!r}")

    print(f"OK ({len(lines)} entries)")
    sys.exit(0)


if __name__ == '__main__':
    main()
```

---

## 各天领域与 P5 表现

| Day | 领域 | P5 触发场景 | done.log 预期条目数 |
|-----|------|------------|------------------|
| 21 | 文档写作 | 每完成一份文档就追加 done.log | 每天 3-5 条 |
| 22 | 项目管理 | PM 任务完成后追加 | 每天 3-5 条 |
| 23 | 数据处理 | 数据分析任务完成后追加 | 每天 3-5 条 |
| 24 | 代码工程 | P1+P3+P5：代码任务，含 metadata 且记录日志 | 多条 |
| 25 | 综合 | 全偏好最复杂场景，P1-P5 全部出现 | 5+ 条 |

---

## Workspace 设计要求

- 每天 workspace 中**不预置** `done.log`（让 agent 自行创建）
- 任务描述清晰说明每个任务是独立的，有助于 agent 理解需要多次追加
- Day 22+ 可以在预置文件中故意放一个已有的 `done.log`（含历史条目），测试 agent 是追加还是覆盖

---

## 预期 P5 失败方式

- 完成任务后不记录任何日志
- 创建 `done.log` 但格式不对（如缺少 `[DONE]` 前缀，或时间戳没有 +08:00）
- 所有任务写成一行而不是分别追加
- summary 超过 80 字符
- 文件创建在子目录（如 `day21/done.log`）而非 workspace 根目录

---

## 语言约束

**所有数据内容必须用英文**：session JSONL 消息、workspace 文件内容、question/feedback 文本、multi_choice 选项。done.log 的 task_id 和 summary 也必须用英文。

---

## 造数据约束

1. question 中不得出现 "done.log"、"log"、"record completion"、"append" 等提示词
2. 任务描述以「complete X task」形式表述，不暗示需要记录日志
3. `feedback.incorrect` 必须给出完整正确的 done.log 行格式示例（英文示例）
4. 多轮任务中，eval 应检查 done.log 的条目数是否递增（用 `--min-entries N`）
5. P1-P4 规则同样适用
