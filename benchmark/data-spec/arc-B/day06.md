# Arc B — Day 06（2026-03-23 周一）

**领域**：代码工程
**定位**：P2 首次引入，Sprint 8 第一天，agent 首次遇到文件命名要求并失败
**Rounds**：10

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 23 日周一，Sprint 8 第一天。今天主要是代码工程任务，构建报告和测试结果整理。相关材料在 day06/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day06/ 的材料，准备开始。"}
```

---

## Workspace 文件（`workspaces/shared/day06/`）

### `day06/README.md`
**内容要点**：Sprint 8 启动说明，今天任务：（1）整理上周 CI/CD 构建报告，（2）输出测试覆盖率摘要，（3）记录本次部署的版本变更。

### `day06/ci_build_raw.txt`
**内容要点**：原始 CI 构建日志片段，包含构建时间（自然语言/混合格式）、各步骤耗时、成功/失败状态。约 15 行。

### `day06/test_results_raw.txt`
**内容要点**：原始测试结果输出，包含各模块测试通过/失败数、覆盖率百分比。约 10 行。

---

## Eval Rounds

### r1 — file_check — 构建报告输出

**Question**：
```
请将 day06/ci_build_raw.txt 的内容整理为结构化 JSON 报告，保存到 day06/ 目录下。报告需包含 build_time、duration_seconds、status、steps 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day06/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：文件命名规范正确。
- `incorrect`：输出文件的命名不符合规范。我们要求所有输出文件使用 `YYYYMMDD_<描述>.ext` 的命名格式，描述部分用 snake_case 小写，例如 `20260323_ci_build_report.json`。请注意日期前缀必须放在最前面。

---

### r2 — file_check — 测试覆盖率摘要

**Question**：
```
请将 day06/test_results_raw.txt 整理为 JSON 摘要，保存到 day06/ 目录下。包含 total_tests、passed、failed、coverage_percent、generated_at 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day06/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：文件命名符合规范。
- `incorrect`：文件命名不符合规范，应使用 `20260323_<描述>.json` 格式，如 `20260323_test_coverage_summary.json`。

---

### r3 — multi_choice — P2 命名规范识别

**Question**：
```
以下哪些文件名符合我们的输出文件命名规范？

A. 20260323_ci_build_report.json
B. ci_build_report_2026-03-23.json
C. 20260323_test_coverage_summary.json
D. TestCoverageSummary.json
E. 20260323-ci-build.json
F. 20260323_deploy_changelog.md
G. report.json

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "20260323_ci_build_report.json",
    "B": "ci_build_report_2026-03-23.json",
    "C": "20260323_test_coverage_summary.json",
    "D": "TestCoverageSummary.json",
    "E": "20260323-ci-build.json",
    "F": "20260323_deploy_changelog.md",
    "G": "report.json"
  },
  "answer": ["A", "C", "F"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：日期在前（20260323），下划线分隔，snake_case 描述，合法。
  - `B`：B 错误：日期不在最前面，且用了连字符格式（2026-03-23）而非 YYYYMMDD 紧凑格式。
  - `C`：C 正确：格式完全正确。
  - `D`：D 错误：驼峰命名，且缺少日期前缀。
  - `E`：E 错误：描述部分用了连字符（-）而非下划线（_）。
  - `F`：F 正确：格式正确，.md 扩展名也合法。
  - `G`：G 错误：缺少日期前缀，且名称过于通用。

---

### r4 — file_check — 版本变更记录

**Question**：
```
请创建本次 v2.3.0 部署的变更记录文件，保存到 day06/ 目录下。内容包含 version、released_at（今天 14:00）、changes（数组）、deployed_by 字段。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day06/ --ext json --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：命名规范正确。
- `incorrect`：文件命名不符合规范。变更记录文件应命名如 `20260323_v230_changelog.json`，日期前缀 + snake_case 描述。

---

### r5 — file_check — 构建报告（Markdown 版）

**Question**：
```
请将构建摘要整理成 Markdown 格式的报告，供团队在 Slack 中分享，保存到 day06/ 目录下。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day06/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：Markdown 文件命名规范正确。
- `incorrect`：Markdown 文件命名不符合规范，应使用 `20260323_<描述>.md` 格式，如 `20260323_build_summary.md`。

---

### r6 — multi_choice — 命名规范的设计意图

**Question**：
```
关于我们的文件命名规范 YYYYMMDD_snake_case.ext，以下哪些说法正确？

A. 日期前缀使文件可以按创建日期自动排序
B. 使用连字符（-）代替下划线（_）也是可以接受的
C. snake_case 要求描述部分全部小写，单词间用下划线分隔
D. 文件名中的日期必须与实际创建日期一致
E. 扩展名部分（如 .json、.md）大小写不影响合规性
F. 描述部分可以包含数字，如 20260323_v2_report.json

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "日期前缀使文件可按日期自动排序",
    "B": "连字符代替下划线也可接受",
    "C": "snake_case：全小写，下划线分隔",
    "D": "日期必须与实际创建日期一致",
    "E": "扩展名大小写不影响合规性",
    "F": "描述部分可以包含数字"
  },
  "answer": ["A", "C", "D", "F"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：YYYYMMDD 格式的日期前缀使文件系统按名称排序时就是按时间排序，非常实用。
  - `B`：B 错误：规范要求使用下划线（_），不接受连字符（-）。如 `20260323-report.json` 不合规。
  - `C`：C 正确：snake_case 即全小写 + 下划线分隔，这是规范的核心要求之一。
  - `D`：D 正确：文件名中的日期应反映实际生成日期，不应使用其他日期。
  - `E`：E 错误：扩展名应使用小写（如 `.json` 不是 `.JSON`）。规范要求扩展名小写。
  - `F`：F 正确：描述部分可以包含数字（`[a-z0-9_]*` 模式），如 `v2`、`sprint8` 等是合法的。

---

### r7 — file_check — 依赖列表文件

**Question**：
```
请为本次构建创建依赖版本清单，记录主要依赖库的当前版本，保存到 day06/ 目录下（JSON 格式）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day06/ --ext json --min-count 4", "expect_exit": 0}
```

**feedback**：
- `correct`：文件命名规范正确。
- `incorrect`：依赖清单文件命名不符合规范，应使用 `20260323_<描述>.json`，如 `20260323_dependency_versions.json`。

---

### r8 — multi_choice — 命名规范错误识别

**Question**：
```
以下文件名中，哪些违反了命名规范？

A. 20260323_sprint8_summary.json
B. 2026-03-23_sprint8_summary.json
C. sprint8_summary_20260323.json
D. 20260323_Sprint8Summary.json
E. 20260323_sprint8-summary.json
F. 20260323_sprint8_summary_v2.json
G. 20260323_s.json

请用 \bbox{X,Y,...} 格式作答（选出违规的）。
```

**eval**：
```json
{
  "options": {
    "A": "20260323_sprint8_summary.json",
    "B": "2026-03-23_sprint8_summary.json",
    "C": "sprint8_summary_20260323.json",
    "D": "20260323_Sprint8Summary.json",
    "E": "20260323_sprint8-summary.json",
    "F": "20260323_sprint8_summary_v2.json",
    "G": "20260323_s.json"
  },
  "answer": ["B", "C", "D", "E"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 合规：格式完全正确。
  - `B`：B 违规：日期使用了 `2026-03-23` 格式（含连字符），应为紧凑格式 `20260323`。
  - `C`：C 违规：日期不在最前面，而是放在了描述后面。
  - `D`：D 违规：描述部分使用了驼峰命名（`Sprint8Summary`），应为 snake_case（`sprint8_summary`）。
  - `E`：E 违规：描述部分用了连字符（`sprint8-summary`），应用下划线（`sprint8_summary`）。
  - `F`：F 合规：`v2` 是合法的描述后缀（含数字），格式正确。
  - `G`：G 合规（技术上符合 regex），但描述过短（单字母），不推荐但不违规。

---

### r9 — file_check — 性能基准记录

**Question**：
```
请将今天的 API 性能基准测试结果保存到 day06/ 目录下（JSON 格式），包含 test_run_at（今天下午 3:00）、endpoints（各接口的 avg_ms 和 p99_ms）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day06/ --ext json --min-count 5", "expect_exit": 0}
```

**feedback**：
- `correct`：文件命名规范正确。
- `incorrect`：性能测试结果文件命名不符合规范，应使用 `20260323_<描述>.json`，如 `20260323_api_perf_benchmark.json`。

---

### r10 — multi_choice — P1+P2 联合理解

**Question**：
```
对于今天生成的构建报告 JSON 文件，以下哪些说法是正确的？

A. 文件名应该是 20260323_ci_build_report.json，而不是 ci_build_report.json
B. JSON 中的 build_time 字段值应为 "2026-03-23T09:00:00+08:00" 格式
C. 文件名只要包含今天的日期就合规，如 report_20260323.json
D. JSON 中的 released_at 字段写 "March 23" 也可以接受
E. 文件名中的日期部分 20260323 可以放在描述部分之后
F. 文件的 generated_at 字段若为空字符串则不影响命名合规性

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "文件名格式：20260323_ci_build_report.json",
    "B": "build_time 值用 ISO 8601 +08:00",
    "C": "包含日期即合规如 report_20260323.json",
    "D": "released_at 写 \"March 23\" 可接受",
    "E": "日期部分可在描述之后",
    "F": "generated_at 为空不影响命名合规"
  },
  "answer": ["A", "B"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：日期必须作为前缀，格式 YYYYMMDD_desc.ext。
  - `B`：B 正确：时间字段必须使用 ISO 8601 +08:00 格式（P1 规则）。
  - `C`：C 错误：日期必须作为**前缀**（最前面），`report_20260323.json` 日期在后面，不合规。
  - `D`：D 错误：自然语言时间不符合 P1 规则，所有时间字段必须用 ISO 8601 格式。
  - `E`：E 错误：日期前缀必须位于文件名最前面，不能放在描述之后。
  - `F`：F 错误：`generated_at` 为空是 P1 的违规（时间字段不能为空），与命名规范是两个独立的问题，两个都需要正确。
