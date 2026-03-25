# Arc C — Day 11（2026-03-30 周一）

**领域**：文档写作（Markdown）
**定位**：P3 首次引入，Markdown 文件缺少 YAML frontmatter 时失败
**Rounds**：10

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 30 日周一，Sprint 8 第二周开始。今天主要是文档整理工作。相关材料在 day11/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day11/ 的材料，准备开始。"}
```

---

## Workspace 文件（`workspaces/shared/day11/`）

### `day11/README.md`
**内容要点**：今天任务：（1）整理上周 Sprint Review 的结论文档，（2）更新项目 README，（3）编写本周工作计划。预置文件均为普通 Markdown（无 frontmatter），供参考。

### `day11/sprint_review_notes_raw.txt`
**内容要点**：上周 Sprint Review 的原始笔记，纯文本，包含讨论点和决策。

### `day11/existing_readme.md`
**内容要点**：项目现有的 README.md 草稿，无 frontmatter，内容包含项目简介和安装说明。

---

## Eval Rounds

### r1 — file_check — Sprint Review 结论文档

**Question**：
```
请根据 day11/sprint_review_notes_raw.txt，整理上周 Sprint Review 的正式结论文档，Markdown 格式，保存到 day11/ 目录下。文档需包含会议概要、主要决策、行动项。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day11/20260330_*.md')); sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; print(sorted(glob.glob('day11/20260330_*.md'))[0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：文件命名规范且包含正确的 YAML frontmatter。
- `incorrect`：输出文件存在以下问题之一：（1）命名不符合规范（需要 20260330_desc.md 格式），（2）缺少 YAML frontmatter。所有 Markdown 输出文件必须在开头包含以下格式的 frontmatter：\n```\n---\ncreated_at: 2026-03-30T<time>+08:00\nauthor: metaclaw_agent\nstatus: done\n---\n```

---

### r2 — file_check — 本周工作计划

**Question**：
```
请创建本周（3月30日至4月3日）的工作计划文档，Markdown 格式，保存到 day11/ 目录下。包含本周目标、每天的主要任务安排。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day11/20260330_*.md')); sys.exit(0 if len(files)>=2 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day11/20260330_*.md')); [f for f in fs if 'plan' in f or 'schedule' in f or 'week' in f]; print(fs[-1])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：工作计划文档命名和 frontmatter 均正确。
- `incorrect`：工作计划文档需要：（1）命名格式 `20260330_<desc>.md`，（2）开头包含 YAML frontmatter（含 created_at、author、status 字段）。

---

### r3 — multi_choice — Markdown frontmatter 格式识别

**Question**：
```
以下哪些 Markdown 文件的开头格式是符合规范的？

A.
---
created_at: 2026-03-30T09:00:00+08:00
author: metaclaw_agent
status: done
---
# 文档标题

B.
# 文档标题
---
created_at: 2026-03-30T09:00:00+08:00
---

C.
---
created_at: 2026-03-30T09:00:00+08:00
author: metaclaw_agent
status: in_progress
---

D.
---
author: metaclaw_agent
status: done
---
# 文档标题

E.
---
created_at: 2026-03-30
author: metaclaw_agent
status: done
---

F.
---
created_at: 2026-03-30T09:00:00+08:00
author: metaclaw_agent
status: done
extra_field: allowed
---

请用 \bbox{X,Y,...} 格式作答（选出符合规范的）。
```

**eval**：
```json
{
  "options": {
    "A": "完整正确的 frontmatter，status: done",
    "B": "frontmatter 不在文件开头",
    "C": "完整 frontmatter，status: in_progress",
    "D": "frontmatter 缺少 created_at",
    "E": "created_at 为纯日期（缺时间和时区）",
    "F": "完整 frontmatter，含额外字段"
  },
  "answer": ["A", "C", "F"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：frontmatter 位置正确，三个必填字段均有且格式正确。
  - `B`：B 错误：frontmatter 必须在文件**最开头**（第一行为 `---`），不能在正文之后。
  - `C`：C 正确：status 为 `in_progress` 是合法的状态值。
  - `D`：D 错误：缺少必填字段 `created_at`，不合规。
  - `E`：E 错误：`created_at: 2026-03-30` 是纯日期，违反 P1 规范（需要含时间和时区的 ISO 8601 格式）。
  - `F`：F 正确：额外字段（`extra_field`）是允许的，规范只要求必填字段存在，不限制额外字段。

---

### r4 — file_check — 项目 README 更新

**Question**：
```
请更新 day11/existing_readme.md 的内容，添加 API v2.3.0 的相关说明，保存为新文件到 day11/ 目录下（Markdown 格式）。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day11/20260330_*.md')); sys.exit(0 if len(files)>=3 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day11/20260330_*.md')); print([f for f in fs if 'readme' in f.lower() or 'api' in f.lower()][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：README 更新文件命名和 frontmatter 均正确。
- `incorrect`：README 更新文件需要：（1）保存为新文件（而非覆盖）并遵循 P2 命名规范，（2）包含 YAML frontmatter。示例：文件名 `20260330_project_readme_v2.md`，开头有 frontmatter。

---

### r5 — multi_choice — frontmatter 字段要求

**Question**：
```
关于 Markdown 文件的 YAML frontmatter，以下哪些说法是正确的？

A. frontmatter 必须是文件的第一行开始（以 --- 开头）
B. status 字段的合法值包括：pending、in_progress、done
C. status 字段写 "complete" 或 "finished" 也可以接受
D. created_at 字段必须使用 ISO 8601 格式（含 +08:00 时区）
E. author 字段的值可以是任意非空字符串
F. frontmatter 中可以添加项目特定的额外字段（如 category、version）

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "frontmatter 必须在文件第一行开始",
    "B": "status 合法值：pending、in_progress、done",
    "C": "complete 或 finished 也可以接受",
    "D": "created_at 必须用 ISO 8601 +08:00",
    "E": "author 可以是任意非空字符串",
    "F": "可以添加额外字段"
  },
  "answer": ["A", "B", "D", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：YAML frontmatter 必须从文件第一行的 `---` 开始。
  - `B`：B 正确：`pending`、`in_progress`、`done` 是规范定义的三个合法状态。
  - `C`：C 错误：`complete` 和 `finished` 不是合法的 status 值，只接受规范定义的三个值。
  - `D`：D 正确：`created_at` 必须使用 ISO 8601 格式并含 +08:00，这是 P1 和 P3 的双重要求。
  - `E`：E 正确：`author` 字段可以是任意非空字符串，如 `"metaclaw_agent"`、`"Alex"` 等均合法。
  - `F`：F 正确：规范只要求三个必填字段，不限制额外字段。

---

### r6 — file_check — 技术决策文档

**Question**：
```
请创建本周第一个技术决策记录（ADR），Markdown 格式，保存到 day11/ 目录下。记录关于 API 版本管理策略的决策，包含背景、决策内容、影响分析。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=[f for f in glob.glob('day11/20260330_*.md') if 'adr' in f or 'decision' in f or 'arch' in f]; sys.exit(0 if files else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; files=[f for f in glob.glob('day11/20260330_*.md') if 'adr' in f or 'decision' in f or 'arch' in f]; print(files[0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：ADR 文件命名和 frontmatter 正确。
- `incorrect`：ADR 文件需包含 YAML frontmatter，且命名须遵循 P2 规范。示例：文件名 `20260330_api_versioning_adr.md`，包含完整 frontmatter。

---

### r7 — file_check — 本周 Sprint 目标说明

**Question**：
```
请编写本周 Sprint 8 第二周的目标说明文档，Markdown 格式，保存到 day11/ 目录下。包含本周 OKR、关键里程碑和成功标准。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day11/20260330_*.md')); sys.exit(0 if len(files)>=4 else 1)\" && python eval/scripts/check_metadata.py $(python -c \"import glob; fs=sorted(glob.glob('day11/20260330_*.md')); print([f for f in fs if 'sprint' in f or 'goal' in f or 'okr' in f][0])\")", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint 目标文档命名和 frontmatter 正确。
- `incorrect`：Sprint 目标文档缺少符合规范的命名或 frontmatter，请确保文件以 `20260330_` 开头，且包含 YAML frontmatter。

---

### r8 — multi_choice — status 字段的使用场景

**Question**：
```
在使用 frontmatter 的 status 字段时，以下哪些情景与 status 值的对应关系是正确的？

A. 文档刚创建，内容还未填写 → status: pending
B. 文档内容已完成，等待他人审阅 → status: done
C. 文档正在编写中，尚未完成 → status: in_progress
D. 文档已审阅通过，正式发布 → status: done
E. 文档需要修订，有 review comment → status: pending
F. 空白文档（只有 frontmatter）→ status: in_progress

请用 \bbox{X,Y,...} 格式作答（选出正确的对应关系）。
```

**eval**：
```json
{
  "options": {
    "A": "刚创建未填写 → pending",
    "B": "内容完成等待审阅 → done",
    "C": "正在编写中 → in_progress",
    "D": "审阅通过正式发布 → done",
    "E": "需要修订 → pending",
    "F": "空白文档 → in_progress"
  },
  "answer": ["A", "C", "D", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：文档刚创建还未填写内容，使用 `pending` 表示待处理。
  - `B`：B 错误：内容完成但等待审阅，应使用 `in_progress`（流程未完全结束），而非 `done`（done 通常表示最终完成）。
  - `C`：C 正确：正在编写中使用 `in_progress`。
  - `D`：D 正确：审阅通过并正式发布，流程彻底完成，使用 `done`。
  - `E`：E 正确：有修改意见需要修订，退回到 `pending` 状态等待处理。
  - `F`：F 错误：空白文档应使用 `pending`（待处理），而非 `in_progress`（处理中）。

---

### r9 — file_check — 本周 onboarding 文档

**Question**：
```
请为新加入团队的成员编写 onboarding 指南，Markdown 格式，保存到 day11/ 目录下。包含环境配置步骤、代码规范要点、常用命令。
```

**eval**：
```json
{"command": "python -c \"import glob,sys; files=sorted(glob.glob('day11/20260330_*.md')); sys.exit(0 if len(files)>=5 else 1)\"", "expect_exit": 0}
```

**feedback**：
- `correct`：onboarding 文档已创建且命名规范，frontmatter 格式正确。
- `incorrect`：onboarding 文档缺少正确的命名（需 20260330_*.md）或缺少 YAML frontmatter。

---

### r10 — multi_choice — P2+P3 联合判断（MD 文件）

**Question**：
```
以下 Markdown 文件，哪些同时满足 P2（命名）和 P3（frontmatter）两个规范？

A. 文件名 20260330_sprint_review.md，开头有完整 frontmatter（created_at ISO 8601、author、status）
B. 文件名 sprint_review_20260330.md，开头有完整 frontmatter
C. 文件名 20260330_weekly_plan.md，无 frontmatter，直接正文
D. 文件名 20260330_adr_api.md，frontmatter 中 created_at: "2026-03-30"（纯日期）
E. 文件名 20260330_onboarding_guide.md，frontmatter 中 status: "complete"

请用 \bbox{X} 格式选出唯一完全合规的选项。
```

**eval**：
```json
{
  "options": {
    "A": "命名正确 + 完整合规 frontmatter",
    "B": "命名违规（日期不在前）+ frontmatter 正确",
    "C": "命名正确 + 无 frontmatter（P3 违规）",
    "D": "命名正确 + created_at 纯日期（P1 违规）",
    "E": "命名正确 + status 非法值（P3 违规）"
  },
  "answer": ["A"]
}
```

**feedback**：
- `correct`：正确！只有 A 同时满足 P2 和 P3 规范。
- `options`：
  - `A`：A 完全合规：P2 命名正确，P3 frontmatter 完整且格式正确。
  - `B`：B P2 违规：日期在描述后面，不符合 P2 规范。
  - `C`：C P3 违规：缺少 YAML frontmatter。
  - `D`：D P1 违规（同时也是 P3 违规）：`created_at` 纯日期不符合 ISO 8601 要求。
  - `E`：E P3 违规：`status: "complete"` 不是合法状态值，必须是 pending/in_progress/done 之一。
