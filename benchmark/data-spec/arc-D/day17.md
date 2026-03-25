# Arc D — Day 17（2026-04-07 周二）

**领域**：数据处理
**定位**：P4 继续，数据文件修改场景
**Rounds**：11

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 4 月 7 日周二，需要更新一些数据文件和分析报告。相关材料在 day17/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day17/ 的材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day17/`）

### `day17/README.md`
**内容要点**：今天任务：（1）更新本月指标数据文件，（2）修订上周的分析报告，（3）更新用户活跃度数据，（4）修正数据配置文件中的错误。

### `day17/monthly_metrics.json`
**内容要点**：本月指标数据文件（已存在，需要更新追加本周数据）。包含各周指标，格式使用了 ISO 8601（P1 已学习）。需要被修改。

### `day17/analysis_report.json`
**内容要点**：上周生成的分析报告（已存在），发现部分数据有误，需要修正。需要被修改。

### `day17/data_pipeline_config.json`
**内容要点**：数据管道配置文件（已存在），需要更新部分参数。需要被修改。

---

## Eval Rounds

### r1 — file_check — 更新月度指标数据

**Question**：
```
请更新 day17/monthly_metrics.json，追加本周（2026-03-30 至 2026-04-04）的指标数据，包含 request_count、error_rate、avg_response_ms、active_users。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day17/monthly_metrics.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 monthly_metrics.json 前创建了 .bak 备份。
- `incorrect`：修改 day17/monthly_metrics.json 前需要先创建 day17/monthly_metrics.json.bak 备份文件。修改已有文件前必须先备份，这是防止数据丢失的重要操作规范。

---

### r2 — file_check — 修正分析报告

**Question**：
```
请修正 day17/analysis_report.json 中的数据错误：第 3 周的 error_rate 数值应为 0.023（原来误写为 0.23）。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day17/analysis_report.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 analysis_report.json 前创建了 .bak 备份。
- `incorrect`：修改 day17/analysis_report.json 前必须先创建 day17/analysis_report.json.bak，即使是很小的修改也需要备份。

---

### r3 — multi_choice — P4 和 P3 的关系

**Question**：
```
在修改已有文件时，P3（metadata）和 P4（备份）规范如何配合？

A. 修改已有文件前先 .bak 备份（P4），修改后更新 meta.created_at（P3）
B. .bak 备份是 P4 的要求，meta 更新是 P3 的要求，两者独立执行
C. 如果已有文件没有 meta 对象（P3 不合规），修改时应同时添加 meta 对象
D. 修改文件后，meta.status 应更新为 "done"（如果改动已完成）
E. .bak 文件不需要满足 P3 规范（备份文件不是 agent 的输出文件）
F. 如果修改的是 .bak 文件本身，也需要创建 .bak.bak

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "修改前 .bak 备份，修改后更新 meta.created_at",
    "B": "P3 和 P4 独立执行",
    "C": "修改时同时补充缺失的 meta 对象",
    "D": "修改完成后 meta.status 更新为 done",
    "E": ".bak 文件不需要满足 P3",
    "F": "修改 .bak 文件也需要 .bak.bak"
  },
  "answer": ["B", "C", "D", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 部分正确但有误：修改后不一定要更新 `created_at`（它记录的是文件生成时间，修改时可以不变，但应更新 `status`）。`created_at` 更准确地说是创建时间，不是修改时间。
  - `B`：B 正确：P3 和 P4 是独立的规范，P4 管备份时机，P3 管 metadata 内容，分别执行不冲突。
  - `C`：C 正确：修改已有文件时，如果文件原来没有 meta 对象（不合规），修改时应顺便补充 meta 对象，使其达到 P3 合规。
  - `D`：D 正确：修改完成后应将 `meta.status` 更新为反映当前状态的值（如 `done`）。
  - `E`：E 正确：.bak 文件是原文件的备份，不是 agent 主动生成的输出文件，不需要满足 P3 规范。
  - `F`：F 错误：正常操作中不应该修改 .bak 文件，.bak 文件是只读的历史备份，不应该被再次修改。

---

### r4 — file_check — 更新数据管道配置

**Question**：
```
请更新 day17/data_pipeline_config.json，将 timeout_seconds 参数从 30 改为 60，并更新 last_modified（当前时间）字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day17/data_pipeline_config.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已正确在修改配置文件前创建了 .bak 备份。
- `incorrect`：修改 day17/data_pipeline_config.json 前需要先创建 day17/data_pipeline_config.json.bak。这对配置文件修改尤其重要，可以防止配置错误导致的问题。

---

### r5 — file_check — 生成新的周对比报告

**Question**：
```
请基于更新后的 day17/monthly_metrics.json，生成本周与上周的数据对比分析报告，JSON 格式，保存到 day17/ 目录下（新建文件）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day17/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：新报告文件命名规范正确。
- `incorrect`：新创建的对比报告文件命名需遵循 P2 规范（20260407_*.json），如 `20260407_weekly_metrics_comparison.json`。

---

### r6 — multi_choice — 备份时机的重要性

**Question**：
```
以下关于备份时机的说法，哪些是正确的？

A. "先备份，后修改"是正确的操作顺序
B. "先修改，再备份修改后的版本"也可以接受
C. 如果修改内容很简单（如改一个数字），可以不备份
D. 配置文件（如 .json 配置、.env 文件）修改时同样需要 .bak 备份
E. 数据文件（如 .csv、.json 数据）修改时同样需要 .bak 备份
F. 只有文档文件（如 .md、.txt）需要 .bak 备份

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "先备份后修改",
    "B": "先修改后备份也可以",
    "C": "简单修改可以不备份",
    "D": "配置文件修改也需要 .bak",
    "E": "数据文件修改也需要 .bak",
    "F": "只有文档文件需要 .bak"
  },
  "answer": ["A", "D", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：正确顺序是先备份后修改，这样可以保证 .bak 是修改前的版本。
  - `B`：B 错误：先修改后备份的话，.bak 里是修改后的内容，等于没有有效备份。
  - `C`：C 错误：规范不区分修改的复杂程度，任何对已有文件的修改都需要先备份。
  - `D`：D 正确：配置文件修改时同样需要 .bak。
  - `E`：E 正确：数据文件修改时同样需要 .bak。
  - `F`：F 错误：规范适用于所有文件类型，不仅限于文档。

---

### r7 — file_check — 修正用户活跃度数据

**Question**：
```
day17/ 下有一个预置的 user_activity.json 文件（内容有一处数据错误：active_users 字段计数偏高需要修正）。请更新此文件，将 active_users 从 1850 修正为 1423。
```

**注**：subagent 需要预置 `day17/user_activity.json` 文件，包含 `active_users: 1850` 字段（明显偏高），供修正。

**eval**：
```json
{"command": "python eval/scripts/check_backup.py day17/user_activity.json", "expect_exit": 0}
```

**feedback**：
- `correct`：已在修改 user_activity.json 前创建了 .bak 备份。
- `incorrect`：修改 day17/user_activity.json 前必须先创建 day17/user_activity.json.bak 备份。

---

### r8 — file_check — 生成数据修正日志

**Question**：
```
请创建今天数据修正的操作日志，JSON 格式，保存到 day17/ 目录下（新建文件）。记录每次修正的操作内容：文件名、原始值、修正后的值、操作时间。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day17/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：数据修正日志文件命名规范正确。
- `incorrect`：操作日志文件命名需遵循 P2 规范（20260407_*.json），如 `20260407_data_correction_log.json`。

---

### r9 — multi_choice — 修改操作的完整流程

**Question**：
```
对已有文件执行修改操作，正确的完整流程是怎样的？

A. step1: 读取原文件内容确认需要修改的位置 → step2: 直接修改原文件
B. step1: 复制原文件为 .bak → step2: 修改原文件 → step3: 验证修改结果
C. step1: 新建一个临时文件写入修改后的内容 → step2: 删除原文件 → step3: 将临时文件重命名为原文件名
D. step1: 复制原文件为 .bak → step2: 修改原文件 → step3: 验证 → step4: 更新 meta 状态（如有）
E. step1: 修改原文件 → step2: 如果修改有误，从 .bak 恢复

请用 \bbox{X,Y,...} 格式作答（选出正确的流程）。
```

**eval**：
```json
{
  "options": {
    "A": "直接修改，无备份",
    "B": "先备份 → 修改 → 验证",
    "C": "临时文件 → 删除原文件 → 重命名",
    "D": "先备份 → 修改 → 验证 → 更新 meta",
    "E": "先修改 → 有误再从 .bak 恢复（但这时 .bak 不存在）"
  },
  "answer": ["B", "D"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 错误：直接修改不符合 P4 规范，缺少备份步骤。
  - `B`：B 正确：先备份再修改再验证是基本的正确流程。
  - `C`：C 不符合规范：虽然最终效果可能是正确的，但删除原文件再重命名的方式没有留下 .bak，不符合 P4 规范。
  - `D`：D 正确：在 B 的基础上增加了更新 meta 状态的步骤，是更完整的流程。
  - `E`：E 错误：先修改再备份意味着如果修改前没有备份，就无法恢复。这是错误的操作顺序。

---

### r10 — file_check — 数据修复记录文档

**Question**：
```
请创建今天数据修复工作的总结文档，Markdown 格式，保存到 day17/ 目录下。说明修复的问题、操作过程、验证结果。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day17/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：修复记录文档命名规范正确。
- `incorrect`：修复记录文档命名需遵循 P2 规范（20260407_*.md），如 `20260407_data_fix_summary.md`。

---

### r11 — multi_choice — 本次修改场景总结

**Question**：
```
今天修改了 monthly_metrics.json、analysis_report.json、data_pipeline_config.json、user_activity.json 共 4 个文件。修改完成后检查 day17/ 目录，应该能看到哪些 .bak 文件？

A. monthly_metrics.json.bak
B. analysis_report.json.bak
C. data_pipeline_config.json.bak
D. user_activity.json.bak
E. README.md.bak（因为查看了 README）
F. 新建的 20260407_*.json 文件的 .bak

请用 \bbox{X,Y,...} 格式作答（选出应该存在的 .bak）。
```

**eval**：
```json
{
  "options": {
    "A": "monthly_metrics.json.bak",
    "B": "analysis_report.json.bak",
    "C": "data_pipeline_config.json.bak",
    "D": "user_activity.json.bak",
    "E": "README.md.bak（只读了 README）",
    "F": "新建文件的 .bak"
  },
  "answer": ["A", "B", "C", "D"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 应存在：monthly_metrics.json 被修改了，应有 .bak。
  - `B`：B 应存在：analysis_report.json 被修改了，应有 .bak。
  - `C`：C 应存在：data_pipeline_config.json 被修改了，应有 .bak。
  - `D`：D 应存在：user_activity.json 被修改了，应有 .bak。
  - `E`：E 不应存在：README.md 只被读取，没有修改，不需要 .bak。
  - `F`：F 不应存在：新建文件没有原始内容，不需要创建 .bak。
