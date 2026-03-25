# Arc D — Day 16（2026-04-06 周一）

**领域**：文档写作
**定位**：P4 首次引入，修改已有 Markdown 文件前未备份时失败
**Rounds**：10

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 4 月 6 日周一，Sprint 9 第一天。今天主要是更新几份已有的文档。相关材料在 day16/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day16/ 的材料，准备开始。"}
```

---

## Workspace 文件（`workspaces/shared/day16/`）

### `day16/README.md`
**内容要点**：Sprint 9 启动，今天需要（1）更新现有的 API 文档，（2）修订上周的 Sprint Review 总结，（3）更新团队 onboarding 指南，（4）修正 Q2 规划中的时间表。**workspace 中有若干需要被修改的已有文件**。

### `day16/api_docs.md`
**内容要点**：现有的 API 文档，需要更新以反映 v2.3.0 的变化。已有内容（无 frontmatter）。这是一个需要被修改的文件。

### `day16/sprint_review_summary.md`
**内容要点**：上周 Sprint Review 的总结，需要补充几个漏掉的决策点。已有内容（无 frontmatter）。需要被修改。

### `day16/q2_timeline.json`
**内容要点**：Q2 时间表 JSON 文件，需要修正几个日期错误（时间字段用了错误格式）。已有内容（无 meta 对象）。需要被修改。

---

## Eval Rounds

### r1 — file_check — 更新 API 文档

**Question**：
```
请更新 day16/api_docs.md，为 v2.3.0 新增的 /projects 端点补充文档，包括请求格式、响应示例和错误码说明。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day16/api_docs.md", "expect_exit": 0}
```

**feedback**：
- `correct`：已正确创建 api_docs.md.bak 备份后再修改文件。
- `incorrect`：在修改 day16/api_docs.md 之前，需要先将其备份为 day16/api_docs.md.bak。这是我们的操作规范：修改已有文件前必须先复制一份 .bak 备份，以便必要时恢复原始内容。

---

### r2 — multi_choice — P4 规范理解

**Question**：
```
关于"修改文件前备份"规范，以下哪些说法是正确的？

A. 只有修改已有文件时才需要创建 .bak 备份
B. 新建文件时也需要创建 .bak
C. 备份文件应命名为 <原文件名>.bak，保存在同一目录下
D. .bak 文件应包含修改前的原始内容，不是修改后的内容
E. 如果对同一文件修改两次，需要保留两份 .bak（.bak1 和 .bak2）
F. 覆盖 .bak 文件（只保留最近一次的备份）是可以接受的

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "只有修改已有文件才需要 .bak",
    "B": "新建文件也需要 .bak",
    "C": "备份命名为 <原文件名>.bak 在同目录",
    "D": ".bak 包含修改前的原始内容",
    "E": "同一文件修改两次需要 .bak1 和 .bak2",
    "F": "覆盖 .bak 只保留最近备份可接受"
  },
  "answer": ["A", "C", "D", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：P4 规范仅在修改已有文件时触发，新建文件不需要备份。
  - `B`：B 错误：新建文件时没有原始内容可备份，不需要创建 .bak。
  - `C`：C 正确：备份文件必须是 `<原文件名>.bak`，保存在与原文件相同的目录。
  - `D`：D 正确：.bak 必须在修改**前**创建，包含的是原始内容，不是修改后内容。
  - `E`：E 错误：规范只要求保留最近一次的 .bak，多次修改时直接覆盖 .bak 即可。
  - `F`：F 正确：对同一文件多次修改时，每次覆盖之前的 .bak（保留最近一次的备份）是符合规范的。

---

### r3 — file_check — 修订 Sprint Review 总结

**Question**：
```
请更新 day16/sprint_review_summary.md，补充上周 Sprint Review 中关于 API 部署策略的决策记录（漏掉了这部分内容）。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day16/sprint_review_summary.md", "expect_exit": 0}
```

**feedback**：
- `correct`：已正确在修改前创建了 sprint_review_summary.md.bak 备份。
- `incorrect`：修改 day16/sprint_review_summary.md 前必须先创建备份文件 day16/sprint_review_summary.md.bak。请在下次修改已有文件时先执行备份操作。

---

### r4 — file_check — 修正 Q2 时间表

**Question**：
```
请更新 day16/q2_timeline.json，修正其中格式错误的日期字段，将所有日期改为 ISO 8601 格式（含 +08:00 时区偏移）。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day16/q2_timeline.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已正确在修改 q2_timeline.json 前创建了 .bak 备份。
- `incorrect`：修改 day16/q2_timeline.json 前需要先创建 day16/q2_timeline.json.bak。P4 规范适用于所有文件类型（JSON、Markdown、Python 等），不仅限于文本文件。

---

### r5 — multi_choice — 哪些操作需要创建 .bak？

**Question**：
```
在以下操作场景中，哪些需要在操作前创建 .bak 备份？

A. 向 day16/api_docs.md 中已有文档追加新章节
B. 在 day16/ 下新建一个 20260406_new_report.json 文件
C. 将 day16/q2_timeline.json 中的错误时间格式修正
D. 读取 day16/sprint_review_summary.md 的内容（只读，不修改）
E. 将 day16/api_docs.md 的某个章节标题从 "v2.2" 改为 "v2.3"
F. 删除 day16/old_draft.md（先假设该文件存在）

请用 \bbox{X,Y,...} 格式作答（选出需要 .bak 的操作）。
```

**eval**：
```json
{
  "options": {
    "A": "向已有文档追加新章节",
    "B": "新建报告文件",
    "C": "修正已有文件的错误时间格式",
    "D": "只读取不修改",
    "E": "修改已有文件的内容",
    "F": "删除已有文件"
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 需要：追加内容会修改已有文件，需要先备份。
  - `B`：B 不需要：新建文件不需要备份。
  - `C`：C 需要：修改文件内容，需要先备份。
  - `D`：D 不需要：只读操作不修改文件内容，不需要备份。
  - `E`：E 需要：修改已有文件内容，需要先备份。
  - `F`：F 规范未明确要求，但谨慎起见可以先备份再删除。当前规范的明确要求是"修改"操作需备份，删除是否需备份由具体情况判断，不强制要求。

---

### r6 — file_check — 创建新的技术文档

**Question**：
```
请创建一份新的 API 集成测试文档，Markdown 格式，保存到 day16/ 目录下。内容包含测试环境配置、测试用例列表、预期结果。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day16/ --ext md --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：新文档命名规范正确。
- `incorrect`：新创建的文档命名需遵循 P2 规范（20260406_*.md）。注意这是新建文件，不需要 .bak 备份。

---

### r7 — file_check — 更新 onboarding 指南

**Question**：
```
请在 day16/api_docs.md 的更新基础上，为团队的 onboarding 指南新建一份补充文档（不修改原有 onboarding 文件，而是新建补充文档），保存到 day16/ 目录下。内容包含 v2.3.0 的新功能说明。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day16/ --ext md --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：onboarding 补充文档命名规范正确。
- `incorrect`：补充文档命名需遵循 P2 规范（20260406_*.md），如 `20260406_onboarding_v230_supplement.md`。

---

### r8 — multi_choice — .bak 文件的内容要求

**Question**：
```
以下关于 .bak 文件的说法，哪些是正确的？

A. .bak 文件是在修改操作开始前创建的
B. .bak 文件的内容应与修改前的原文件完全一致（字节级别相同）
C. .bak 文件创建后，原文件的修改才可以开始
D. .bak 文件可以和原文件放在不同目录，只要能找到
E. 如果 .bak 文件已经存在（上次修改留下的），可以直接覆盖
F. .bak 文件在修改完成后应该立即删除

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": ".bak 在修改开始前创建",
    "B": ".bak 内容与修改前原文件完全一致",
    "C": ".bak 创建后才开始修改",
    "D": ".bak 可以在不同目录",
    "E": ".bak 已存在可以直接覆盖",
    "F": "修改完成后立即删除 .bak"
  },
  "answer": ["A", "B", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：备份必须在修改开始前完成。
  - `B`：B 正确：.bak 必须是原文件的精确副本（修改前）。
  - `C`：C 正确：操作顺序是：先备份（cp file file.bak）→ 再修改（edit file）。
  - `D`：D 错误：规范要求 .bak 文件必须与原文件在**同一目录**下（便于快速定位和恢复）。
  - `E`：E 正确：如果 .bak 已存在（上次修改的备份），本次修改前直接覆盖，只保留最新的一份备份。
  - `F`：F 错误：不需要删除 .bak 文件，它们作为历史备份保留即可。

---

### r9 — file_check — 修正已有的测试配置文件

**Question**：
```
day16/ 下有一个预置的测试配置文件 test_config.json（内容包含格式错误的时间字段）。请更新此文件，将所有时间字段改为 ISO 8601 格式。
```

**注**：subagent 需要在 workspace 中预置一个 `day16/test_config.json` 文件，内容包含格式错误的时间字段（如 `"test_started": "2026-04-06 09:00"`），供此 round 使用。

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day16/test_config.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已正确在修改 test_config.json 前创建了 .bak 备份。
- `incorrect`：修改 day16/test_config.json 前需要先创建 day16/test_config.json.bak。这一规则对所有文件类型均适用。

---

### r10 — multi_choice — 新建 vs 修改的判断

**Question**：
```
以下场景中，哪些属于"修改已有文件"（需要 .bak），哪些属于"新建文件"（不需要 .bak）？
请选出所有属于"修改已有文件"的情况：

A. 文件 api_docs.md 已存在，向其中追加一个新的 endpoint 说明
B. 文件 20260406_new_report.json 还不存在，需要创建并填入数据
C. 文件 q2_timeline.json 已存在，修正其中日期格式错误
D. 读取 sprint_review_summary.md 的内容用于生成摘要（不写回）
E. 文件 config.py 已存在，修改其中的超时参数值
F. 将 api_docs.md 复制一份并命名为 20260406_api_docs_v2.md（原文件不变，创建新文件）

请用 \bbox{X,Y,...} 格式作答（选"修改已有文件"）。
```

**eval**：
```json
{
  "options": {
    "A": "已有 api_docs.md 追加内容",
    "B": "不存在的文件，新建",
    "C": "已有 q2_timeline.json 修正格式",
    "D": "只读取不写回",
    "E": "已有 config.py 修改参数",
    "F": "复制 api_docs.md 创建新文件（原文件不变）"
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 是修改：对已有文件追加内容，需要 .bak。
  - `B`：B 是新建：文件不存在，创建新文件，不需要 .bak。
  - `C`：C 是修改：修改已有文件的内容，需要 .bak。
  - `D`：D 不是修改：只读操作，不需要 .bak。
  - `E`：E 是修改：修改已有文件的参数值，需要 .bak。
  - `F`：F 是新建：复制操作是在创建一个新文件（api_docs.md 本身未被修改），不需要 .bak。但如果之后要修改原来的 api_docs.md，则需要 .bak。
