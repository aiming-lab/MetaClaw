# Arc A — 叙事基准（Narrative）

> 本文件是 arc-A 的真相基准。subagent 造数据时必须读取本文件，确保每天的数据与此一致。

---

## 本弧核心偏好：P1 时间格式统一

**精确规则**：见 `data-spec/preferences.md` P1 节。

**本弧要点**：
- Day 1 是 P1 的**首次引入**：workspace 和任务描述中不出现任何 ISO 8601 提示，agent 首次必然使用错误格式
- Day 2 在同领域（文档/项目管理）换场景复测
- Day 3 跨域（数据处理），测试 P1 能否迁移
- Day 4 再跨域（代码工程），测试 P1 在代码上下文中的应用
- Day 5 综合多场景，伪装更深，最难

**预期失败方式**（base model 常见错误）：
- 自然语言时间："下午3点"、"周五下班前"
- 无时区格式："2026-03-16T09:30:00"、"2026-03-16 09:30:00"
- 纯日期："2026-03-16"（用于应含完整时间的字段）
- 其他时区："2026-03-16T01:30:00Z"（UTC 而非 CST）

---

## 日期设定

| Day | 日期 | 星期 |
|-----|------|------|
| 01 | 2026-03-16 | 周一 |
| 02 | 2026-03-17 | 周二 |
| 03 | 2026-03-18 | 周三 |
| 04 | 2026-03-19 | 周四 |
| 05 | 2026-03-20 | 周五 |

---

## workspace 初始化说明

- `workspaces/shared/AGENTS.md` 等 5 个全局文件只在 arc-A 首次创建，后续弧复用
- 全局文件中**不得出现**时间格式偏好的任何提示
- 每天的 `dayXX/` 子目录只包含当天任务相关文件

---

## eval 脚本：check_iso8601.py

**存放路径**：`eval/scripts/check_iso8601.py`（arc-A 数据创建时一并创建）

**接口**：
```
python eval/scripts/check_iso8601.py <json_file> <field> [<field> ...]
```

- `field` 支持：
  - 顶层字段：`meeting_time`
  - 嵌套字段：`meta.created_at`
  - 数组子字段：`tasks[].due_date`（检查 `tasks` 数组所有元素的 `due_date`）
- Exit 0 + stdout `OK`：所有字段均合法
- Exit 1 + stdout `FAIL: <field>: <value>`：第一个不合法字段

**合法 pattern**：`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$`

**完整实现**（subagent 按此创建脚本）：

```python
#!/usr/bin/env python3
"""check_iso8601.py — validate ISO 8601 +08:00 fields in a JSON file."""
import json, re, sys

PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$')


def get_values(obj, path):
    """Yield (display_path, value) for each value at path. Supports list[]."""
    parts = path.split('.')
    def _walk(cur, parts_left, prefix):
        if not parts_left:
            yield prefix, cur
            return
        p = parts_left[0]
        rest = parts_left[1:]
        if p.endswith('[]'):
            key = p[:-2]
            arr = cur.get(key, [])
            for i, item in enumerate(arr):
                yield from _walk(item, rest, f"{prefix}.{key}[{i}]")
        else:
            if isinstance(cur, dict) and p in cur:
                yield from _walk(cur[p], rest, f"{prefix}.{p}")
            else:
                yield f"{prefix}.{p}", None
    yield from _walk(obj, parts, '')


def main():
    if len(sys.argv) < 3:
        print("Usage: check_iso8601.py <json_file> <field> [<field> ...]")
        sys.exit(2)

    try:
        with open(sys.argv[1], encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAIL: cannot read {sys.argv[1]}: {e}")
        sys.exit(1)

    for field in sys.argv[2:]:
        for path, val in get_values(data, field):
            if val is None:
                print(f"FAIL: {field}: field not found")
                sys.exit(1)
            if not PATTERN.match(str(val)):
                print(f"FAIL: {field}: {val!r}")
                sys.exit(1)

    print("OK")
    sys.exit(0)


if __name__ == '__main__':
    main()
```

---

## 各天领域与 P1 表现

| Day | 领域 | 核心任务 | P1 触发点 |
|-----|------|---------|----------|
| 01 | 文档写作 | 整理会议纪要、创建任务条目 | `meeting_time`、`due_date`、`created_at` |
| 02 | 项目管理 | 更新 sprint 里程碑、发布周报 | `deadline`、`updated_at`、报告时间段 |
| 03 | 数据处理 | 解析服务器日志、输出分析报告 | 日志时间戳转换、报告 `generated_at` |
| 04 | 代码工程 | 编写工具函数、更新 API 文档 | 代码注释中的示例时间、文档字段示例值 |
| 05 | 综合（项目收尾） | 周报 + 数据汇总 + 代码配置 | 多类型文件中散布的时间字段 |

---

## 语言约束

**所有数据内容必须用英文**，包括：
- session JSONL 中的 user/assistant 消息内容
- workspace 文件的所有文本内容（README.md、raw notes、JSON 字段值等）
- questions.json 的 question 字段、feedback 字段（correct/incorrect/options）、multi_choice 选项文本
- done.log 的 task_id 和 summary

规范名称、代码标识符、eval 命令保持英文（本身已是英文）。

---

## 造数据约束

1. workspace 文件中的原始素材（如 standup_raw.txt）应使用**自然语言时间**（"9:30 AM"、"end of Friday"），让 agent 自己转换
2. 任务描述（question 字段）**不得出现** "ISO 8601"、"+08:00"、"timezone" 等提示词
3. `feedback.incorrect` 必须包含正确格式的示例（如 `2026-03-16T09:30:00+08:00`），这是最重要的训练信号
4. multi_choice 选项数量在 5–8 个之间，干扰项要合理（不能太明显错）
