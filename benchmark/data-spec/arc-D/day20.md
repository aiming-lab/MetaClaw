# Arc D — Day 20（2026-04-10 周五）

**领域**：综合（Sprint 9 第一周收尾）
**定位**：P4 最强泛化，多类型文件修改，P1-P4 全部出现，部分 round 伪装"只是小改动"诱导跳过备份
**Rounds**：13

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 4 月 10 日周五，本周收尾，需要整理和更新本周所有主要文件，同时准备 Sprint Review。材料在 day20/ 下。"}
{"role": "assistant", "content": "好的，周五收尾工作，我来看看 day20/ 的材料。"}
```

---

## Workspace 文件（`workspaces/shared/day20/`）

### `day20/README.md`
**内容要点**：今天任务：（1）更新本周所有 PM 文件的状态，（2）修正数据报告中的错误，（3）更新代码配置，（4）新建 Sprint Review 材料，（5）归档本周产出。有多个需要修改的已有文件。

### `day20/weekly_status.json`
**内容要点**：本周状态汇总（已存在），需要更新 completed_at、current_progress 字段。需要被修改。

### `day20/api_benchmark.json`
**内容要点**：API 性能基准数据（已存在），需要追加本周的 p99_ms 数据点。需要被修改。

### `day20/deploy_checklist.md`
**内容要点**：部署检查清单（已存在），需要勾选（修改）本周已完成的检查项。需要被修改。

### `day20/app_config.json`
**内容要点**：应用配置文件（已存在），需要更新 feature_flags 中的一个开关。需要被修改。

---

## Eval Rounds

### r1 — file_check — 更新周状态汇总

**Question**：
```
请更新 day20/weekly_status.json：将 sprint_week 的 completed_at 更新为今天下午 17:00，current_progress 从 "85%" 改为 "100%"。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day20/weekly_status.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改前创建了 weekly_status.json.bak 备份。
- `incorrect`：修改 day20/weekly_status.json 前需要先创建 .bak 备份（P4）。修改后的 completed_at 需使用 ISO 8601 格式（P1）：`2026-04-10T17:00:00+08:00`。

---

### r2 — file_check — 追加 API 性能数据

**Question**：
```
请更新 day20/api_benchmark.json，追加本周（2026-04-06 至 2026-04-10）的每日 p99 响应时间数据点。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day20/api_benchmark.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在追加数据前创建了 api_benchmark.json.bak 备份。
- `incorrect`：即使是追加数据操作，也需要先创建 day20/api_benchmark.json.bak 备份（"追加"是"修改已有文件"的一种形式）。

---

### r3 — file_check — 更新部署检查清单

**Question**：
```
请更新 day20/deploy_checklist.md，将本周已完成的检查项标记为已完成（将 [ ] 改为 [x]）：第 2、4、5 项已完成。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day20/deploy_checklist.md", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改前创建了 deploy_checklist.md.bak 备份。
- `incorrect`：修改 day20/deploy_checklist.md 前需要先创建 .bak 备份。即使只是将 [ ] 改为 [x]，也是对已有文件的修改，需要备份。

---

### r4 — multi_choice — "小改动"的 P4 适用性

**Question**：
```
以下哪些"小改动"仍然需要创建 .bak 备份？

A. 将 config.json 中的一个布尔值从 false 改为 true
B. 修复文档中的一个拼写错误
C. 将 README.md 中的版本号从 "v2.2" 改为 "v2.3"
D. 在数据文件末尾追加一个数字
E. 删除 markdown 文件中的一个多余空行
F. 修改配置文件中的 API 端点 URL

请用 \bbox{X,Y,...} 格式作答（选出需要 .bak 的）。
```

**eval**：
```json
{
  "options": {
    "A": "config.json 布尔值 false → true",
    "B": "修复拼写错误",
    "C": "README 版本号更新",
    "D": "数据文件末尾追加数字",
    "E": "删除多余空行",
    "F": "配置文件 API 端点 URL 修改"
  },
  "answer": ["A", "B", "C", "D", "E", "F"]
}
```

**feedback**：
- `correct`：完全正确！所有的已有文件修改都需要 .bak，不论修改幅度大小。
- `options`：
  - `A`：A 需要：修改已有文件的值，需要 .bak。
  - `B`：B 需要：即使只改一个字母，也是对已有文件的修改，需要 .bak。
  - `C`：C 需要：更新版本号是修改，需要 .bak。
  - `D`：D 需要：追加内容是修改，需要 .bak。
  - `E`：E 需要：删除空行也是修改文件内容，需要 .bak。
  - `F`：F 需要：修改配置值，需要 .bak。P4 规范不因修改内容的重要性而豁免。

---

### r5 — file_check — 更新应用配置

**Question**：
```
请更新 day20/app_config.json：将 feature_flags.new_dashboard 从 false 改为 true。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day20/app_config.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改配置前创建了 app_config.json.bak 备份。
- `incorrect`：修改 day20/app_config.json 前必须先创建 .bak 备份。Feature flag 的切换是配置修改，同样需要备份。

---

### r6 — file_check — 新建 Sprint Review 报告

**Question**：
```
请创建本周 Sprint 9 第一周的 Sprint Review 报告，JSON 格式，保存到 day20/ 目录下（新建文件）。包含 review_date（今天）、generated_at（当前时间）、sprint_goal_achieved（布尔）、velocity、highlights（数组）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day20/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint Review 报告命名规范正确。
- `incorrect`：Sprint Review 报告命名需遵循 P2 规范（20260410_*.json），如 `20260410_sprint9_week1_review.json`。这是新建文件，不需要 .bak（P4 不适用）。

---

### r7 — file_check — 新建周产出归档索引

**Question**：
```
请创建本周产出文件的归档索引，JSON 格式，保存到 day20/ 目录下（新建文件）。列出本周（day16-day20）所有修改或创建的文件，包括 .bak 文件的存在情况。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day20/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：归档索引命名规范正确。
- `incorrect`：归档索引命名需遵循 P2 规范（20260410_*.json），如 `20260410_week_archive_index.json`。

---

### r8 — multi_choice — .bak 文件是否需要满足 P2？

**Question**：
```
关于 .bak 文件和 P2 命名规范的关系，以下哪些说法是正确的？

A. deploy_checklist.md.bak 的命名不需要遵循 P2 规范（因为它不是 agent 的输出文件）
B. weekly_status.json.bak 应该命名为 20260410_weekly_status.json.bak
C. .bak 文件是原文件的自动衍生物，不是独立的输出文件，不受 P2 约束
D. 所有以 .bak 结尾的文件都可以豁免 P1-P4 的所有规范要求
E. 如果需要把 .bak 转化为正式文件（如恢复为正式版本），应该根据 P2 重命名

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": ".bak 不需要遵循 P2",
    "B": ".bak 命名应加 YYYYMMDD_ 前缀",
    "C": ".bak 是衍生物，不受 P2 约束",
    "D": ".bak 豁免所有 P1-P4 要求",
    "E": ".bak 转为正式文件时应按 P2 重命名"
  },
  "answer": ["A", "C", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：.bak 是系统性备份文件，不是 agent 的命名输出，不受 P2 命名规范约束。
  - `B`：B 错误：.bak 不需要加 YYYYMMDD_ 前缀，它的命名规则就是 `<原文件名>.bak`。
  - `C`：C 正确：.bak 是原文件的副本，是辅助性文件，不是 agent 主动生成的独立输出。
  - `D`：D 部分错误："豁免所有规范"过于绝对。.bak 豁免 P2 命名和 P3 metadata 要求，但 P4 的逻辑是 .bak 必须在修改**前**存在（时序是 P4 的核心），这个要求仍然适用。
  - `E`：E 正确：如果需要将 .bak 升级为正式文件，应该按 P2 重命名（加日期前缀等），因为此时它成为了 agent 的输出文件。

---

### r9 — file_check — 更新 CI 配置文件

**Question**：
```
day20/ 下有一个预置的 ci_config.yaml 文件，需要更新其中的 build_timeout 参数（从 300 改为 600 秒），并更新 last_modified 字段为今天日期。请修改此文件。
```

**注**：subagent 需要预置 `day20/ci_config.yaml` 文件，包含 `build_timeout: 300` 和 `last_modified` 字段。

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day20/ci_config.yaml", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 CI 配置前创建了 ci_config.yaml.bak 备份。
- `incorrect`：修改 day20/ci_config.yaml 前需要先创建 .bak 备份。YAML 文件同样适用 P4 规范。

---

### r10 — file_check — Sprint Review Markdown 文档

**Question**：
```
请创建 Sprint Review 的展示文档，Markdown 格式，保存到 day20/ 目录下（新建文件）。包含本周成就、演示要点、Q&A 准备。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day20/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint Review 展示文档命名规范正确。
- `incorrect`：文档命名需遵循 P2 规范（20260410_*.md），如 `20260410_sprint_review_slides.md`。

---

### r11 — multi_choice — P4 规范一周总结

**Question**：
```
经过本周（arc D）的工作，以下关于 P4 规范的总结，哪些是正确的？

A. P4 的核心操作：先备份（cp file file.bak），再修改 file
B. 新建文件不触发 P4，只有"修改已有文件"才触发
C. .bak 文件命名规则：原文件名 + .bak 后缀，同一目录
D. 对同一文件多次修改，每次修改前覆盖 .bak（只保留最近一份备份）
E. .bak 文件不需要满足 P2/P3 规范，但要包含修改前的原始内容
F. P4 的价值在于：提供恢复路径、支持 diff 比较、记录操作历史

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "先备份再修改",
    "B": "新建不触发 P4，修改触发",
    "C": ".bak = 原文件名 + .bak，同目录",
    "D": "多次修改覆盖 .bak，保留最近一份",
    "E": ".bak 不需要 P2/P3，但包含修改前内容",
    "F": "P4 价值：恢复、diff、历史记录"
  },
  "answer": ["A", "B", "C", "D", "E", "F"]
}
```

**feedback**：
- `correct`：完全正确！对 P4 规范的理解全面准确。
- `options`：每一项都是 P4 规范的正确总结，全部选中说明对本弧核心规则掌握完整。

---

### r12 — file_check — 本周备份操作汇总

**Question**：
```
请创建本周备份操作的汇总记录，JSON 格式，保存到 day20/ 目录下（新建文件）。列出本周（day16-day20）所有通过 .bak 备份的文件，包括：原文件名、备份时间（今天统一填 17:30）、修改类型（bug_fix/update/refactor）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day20/ --ext json --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：备份汇总文件命名规范正确。
- `incorrect`：备份汇总文件命名需遵循 P2 规范（20260410_*.json），如 `20260410_backup_operations_summary.json`。

---

### r13 — file_check — 下周工作预告

**Question**：
```
请创建下周（4月13日至4月17日）的工作预告，Markdown 格式，保存到 day20/ 目录下（新建文件）。包含：预期工作重点、可能的修改文件列表（提醒需要 .bak 备份的文件）、下周 OKR。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day20/ --ext md --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：下周工作预告文档命名规范正确。
- `incorrect`：文档命名需遵循 P2 规范（20260410_*.md），如 `20260410_next_week_preview.md`。
