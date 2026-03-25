# Arc D — 叙事基准（Narrative）

> 本弧真相基准。subagent 造数据时必须读取本文件。

---

## 本弧核心偏好：P4 操作前备份

**精确规则**：见 `data-spec/preferences.md` P4 节。

**核心要求**：修改已有文件前，必须先将原文件复制为 `<原文件名>.bak`（保留在同一目录）。

- **触发条件**：「修改已有文件」——文件已存在于 workspace，agent 需要更新/覆盖其内容
- **不触发条件**：「新建文件」——不需要 .bak
- `.bak` 文件须为**修改前**的内容，不是修改后

**P1、P2、P3 仍然有效**：输出文件需同时满足前三个规则。

---

## 日期设定

| Day | 日期 | 星期 |
|-----|------|------|
| 16 | 2026-04-06 | 周一 |
| 17 | 2026-04-07 | 周二 |
| 18 | 2026-04-08 | 周三 |
| 19 | 2026-04-09 | 周四 |
| 20 | 2026-04-10 | 周五 |

---

## eval 脚本：check_backup.py

**存放路径**：`eval/scripts/check_backup.py`（arc-D 数据创建时一并创建）

**接口**：
```
python eval/scripts/check_backup.py <original_filepath>
```

- 检查 `<original_filepath>.bak` 是否存在
- 检查 `.bak` 内容与当前文件内容**不同**（说明备份了修改前的版本）
- Exit 0 + `OK`：.bak 存在且与当前文件不同
- Exit 1 + `FAIL: <说明>`：.bak 不存在，或 .bak 与当前文件完全相同

**完整实现**：

```python
#!/usr/bin/env python3
"""check_backup.py — validate P4 pre-modification backup."""
import sys, os

def main():
    if len(sys.argv) < 2:
        print("Usage: check_backup.py <original_file>")
        sys.exit(2)
    orig = sys.argv[1]
    bak = orig + '.bak'
    if not os.path.exists(orig):
        print(f"FAIL: original file not found: {orig}")
        sys.exit(1)
    if not os.path.exists(bak):
        print(f"FAIL: backup file not found: {bak} (must create .bak before modifying)")
        sys.exit(1)
    orig_content = open(orig, 'rb').read()
    bak_content = open(bak, 'rb').read()
    if orig_content == bak_content:
        print(f"FAIL: {bak} has identical content to {orig} — backup was not made before modification")
        sys.exit(1)
    print("OK")
    sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## 各天领域与 P4 表现

| Day | 领域 | P4 触发场景（修改已有文件）|
|-----|------|--------------------------|
| 16 | 文档写作 | 更新已有 Markdown 报告、追加会议纪要 |
| 17 | 数据处理 | 更新已有 JSON 数据文件、追加日志 |
| 18 | 代码工程 | 修改已有配置文件、更新 Python 脚本 |
| 19 | 项目管理 | P1+P2+P4：更新 PM 文件，需备份并遵守前两个规则 |
| 20 | 综合 | P4 最复杂场景，多文件修改，P1-P4 全部出现 |

---

## Workspace 设计要求

每天的 workspace 预置文件中，**必须有 1-3 个已存在的文件供 agent 修改**。这些文件不需要符合 P2/P3（它们是预置的，不是 agent 生成的）。任务描述指示 agent 更新这些文件。

典型预置文件示例：
- `day16/current_report.md`：需要更新的现有报告
- `day17/metrics.json`：需要更新数据的现有 JSON 文件
- `day18/config.py`：需要修改的配置文件

---

## 预期 P4 失败方式

- 直接覆盖文件，未创建 .bak
- 创建 .bak 但内容与修改后相同（备份时机错误，应在修改**前**备份）
- 新建了一个不同名的"备份文件"（如 `current_report_backup.md`）而非 `.bak` 后缀

---

## 语言约束

**所有数据内容必须用英文**：session JSONL 消息、workspace 文件内容、question/feedback 文本、multi_choice 选项。

---

## 造数据约束

1. question 中不得出现 "backup"、".bak"、"copy first" 等提示词
2. question 必须明确指出是**修改已有文件**（避免歧义），但不提示需要备份
3. `feedback.incorrect` 必须解释应在修改前创建 `.bak` 文件，并给出正确操作示例
4. P1-P3 规则同样适用
