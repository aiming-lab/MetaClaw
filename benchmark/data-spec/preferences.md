# MetaClaw Evolution Benchmark — 隐式偏好规则定义

> 本文件是所有弧通用的偏好真相基准。各弧的 narrative.md 引用此文件，描述偏好在具体场景中的表现，不重复定义规则本身。

---

## 用户人设（全局）

- **姓名**：Alex Zhang，Orion Tech 后端团队 Tech Lead
- **公司**：Orion Tech，一家 B2B SaaS 公司，主力产品是项目管理平台 "Project Orion"
- **日常工作**：团队协调、任务跟进、数据整理、代码审查、文档编写
- **工作时区**：CST（UTC+08:00）
- **工作语言**：会话用中文，代码/文件名用英文

---

## P1：时间格式统一

**规则**：所有时间/日期字段必须使用 ISO 8601 扩展格式，含显式时区偏移（CST 固定为 +08:00）：

```
YYYY-MM-DDTHH:MM:SS+08:00
```

- 允许秒后带毫秒：`2026-03-16T09:30:00.000+08:00`
- 不允许纯日期（`2026-03-16`）、自然语言（"下午3点"）、无时区格式（`2026-03-16T09:30:00`）、UTC Z 格式（`2026-03-16T09:30:00Z`）

**验证 regex**：`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$`

**适用字段名**（出现即需符合）：`*_at`、`*_time`、`*_date`、`deadline`、`due`、`timestamp` 等所有时间语义字段

**eval 脚本**：`eval/scripts/check_iso8601.py`（接口见 arc-A/narrative.md）

---

## P2：文件命名规范

**规则**：所有 agent 生成的输出文件，命名格式为：

```
YYYYMMDD_<描述>.<ext>
```

- 日期部分：8 位数字，如 `20260316`
- 描述部分：snake_case，只含小写字母、数字、下划线，如 `meeting_notes`
- 扩展名：小写，如 `.json`、`.md`、`.csv`

**合法示例**：`20260316_standup_notes.json`、`20260317_sprint_report.md`

**非法示例**：`output.json`、`MeetingNotes.json`、`report-2026-03-17.md`、`standup_2026-03-17.json`

**验证 regex**：`^\d{8}_[a-z][a-z0-9_]*\.[a-z0-9]+$`

**eval 脚本**：`eval/scripts/check_filename.py`（接口见 arc-B/narrative.md）

---

## P3：文件 metadata 完整性

**规则**：agent 生成的所有输出文件，必须包含 metadata 块，具体格式依文件类型：

| 文件类型 | Metadata 格式 | 位置 |
|---------|--------------|------|
| `.md` / `.txt` | YAML frontmatter | 文件开头 `---\n...\n---\n` |
| `.json` | 顶层 `meta` 对象 | JSON 根对象中 |
| `.py` | 模块级 docstring metadata 段 | 文件头部 docstring |
| `.csv` | 首行注释 `# meta: ...` | 第一行 |

**最少必填字段**（跨类型统一语义）：

| 字段 | 说明 | 格式要求 |
|------|------|---------|
| `created_at` | 文件创建时间 | ISO 8601 P1 格式 |
| `author` | 创建者 | 字符串，如 `"metaclaw_agent"` |
| `status` | 当前状态 | `pending` / `in_progress` / `done` |

各弧 narrative 可在此基础上添加更多必填字段。

**Markdown 示例**：
```md
---
created_at: 2026-03-16T09:30:00+08:00
author: metaclaw_agent
status: done
---

正文内容...
```

**JSON 示例**：
```json
{
  "meta": {
    "created_at": "2026-03-16T09:30:00+08:00",
    "author": "metaclaw_agent",
    "status": "done"
  },
  "content": { ... }
}
```

**eval 脚本**：`eval/scripts/check_metadata.py`（接口见 arc-C/narrative.md）

---

## P4：操作前备份

**规则**：修改已有文件前，必须先将原文件复制为 `<原文件名>.bak`（保留在同一目录下）。

- 只有**修改已有文件**时需要备份，**新建文件**不需要
- `.bak` 文件内容须为操作前的原始内容（不是操作后）
- 若同一文件被多次修改，只需保留最近一次的 `.bak`（覆盖）

**验证方式**：`ls <path_to>.bak && diff <original>.bak <original> | head -1`（exit 0 且 diff 有变化则通过）

**eval 脚本**：`eval/scripts/check_backup.py`（接口见 arc-D/narrative.md）

---

## P5：完成状态日志

**规则**：每次任务完成后，在 workspace 根目录的 `done.log` 文件末尾追加一行：

```
[DONE] <ISO 8601 timestamp> | <task_id> | <one-line summary>
```

- `task_id` 对应 round 编号或任务描述缩写（agent 自行拟定，合理即可）
- `one-line summary` 不超过 80 字符，简述完成内容
- 多个任务各追加一行，不合并
- 文件不存在时自动创建

**合法示例**：
```
[DONE] 2026-03-21T10:15:00+08:00 | standup_notes | 整理了周一 standup 纪要，输出到 day21/standup.json
```

**验证方式**：`python eval/scripts/check_done_log.py done.log <expected_task_id_prefix>`

**eval 脚本**：`eval/scripts/check_done_log.py`（接口见 arc-E/narrative.md）
