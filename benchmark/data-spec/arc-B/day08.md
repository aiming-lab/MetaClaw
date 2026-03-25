# Arc B — Day 08（2026-03-25 周三）

**领域**：数据处理
**定位**：跨域迁移，P2 在数据分析输出中出现，验证能否从"代码/文档"迁移到"数据处理"
**Rounds**：12

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 25 日周三，需要处理一些数据分析工作——指标统计、日志分析和报表生成。材料在 day08/ 下。"}
{"role": "assistant", "content": "好的，我来看看 day08/ 的数据材料，开始处理。"}
```

---

## Workspace 文件（`workspaces/shared/day08/`）

### `day08/README.md`
**内容要点**：今天任务：（1）分析本周 API 请求量趋势，（2）生成用户活跃度报告，（3）处理异常事件数据，（4）输出关键指标 CSV 供 PM 使用。

### `day08/api_requests_raw.csv`
**内容要点**：原始 CSV 数据，约 20 行，列为 timestamp（混合格式）、endpoint、status_code、response_ms。timestamp 使用非标格式。

### `day08/user_activity_raw.json`
**内容要点**：用户活跃度原始数据，包含各用户的 last_login（自然语言格式）、session_count、active_days。约 8 条记录。

---

## Eval Rounds

### r1 — file_check — API 请求量趋势分析

**Question**：
```
请分析 day08/api_requests_raw.csv 中的数据，按小时统计请求量和平均响应时间，将分析结果保存到 day08/ 目录下（JSON 格式）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：分析结果文件命名规范正确。
- `incorrect`：数据分析结果文件命名不符合规范，应使用 `20260325_<描述>.json` 格式，如 `20260325_api_request_trend.json`。

---

### r2 — file_check — 用户活跃度报告

**Question**：
```
请处理 day08/user_activity_raw.json，生成用户活跃度分析报告，保存到 day08/ 目录下（JSON 格式）。包含 generated_at（当前时间）、total_users、active_users（过去 7 天有登录）、avg_sessions 等汇总指标。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：活跃度报告文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260325_user_activity_report.json` 或类似格式。

---

### r3 — multi_choice — 数据输出文件命名

**Question**：
```
在数据处理场景中，以下哪些输出文件命名是正确的？

A. 20260325_api_request_trend.json
B. api_trend_analysis_20260325.csv
C. 20260325_user_activity_report.json
D. UserActivityReport.json
E. 20260325_metrics_export.csv
F. metrics_20260325.csv
G. 20260325_error_event_summary.json

请用 \bbox{X,Y,...} 格式作答（选正确的）。
```

**eval**：
```json
{
  "options": {
    "A": "20260325_api_request_trend.json",
    "B": "api_trend_analysis_20260325.csv（日期在后）",
    "C": "20260325_user_activity_report.json",
    "D": "UserActivityReport.json（无日期）",
    "E": "20260325_metrics_export.csv",
    "F": "metrics_20260325.csv（日期在后）",
    "G": "20260325_error_event_summary.json"
  },
  "answer": ["A", "C", "E", "G"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：日期前缀，snake_case 描述，格式正确。
  - `B`：B 错误：日期不在最前面。
  - `C`：C 正确：格式正确。
  - `D`：D 错误：缺少日期前缀，驼峰命名。
  - `E`：E 正确：格式正确，.csv 扩展名合法。
  - `F`：F 错误：日期不在最前面。
  - `G`：G 正确：格式正确。

---

### r4 — file_check — 指标 CSV 导出

**Question**：
```
请将今天的关键业务指标汇总导出为 CSV 格式，供 PM 使用，保存到 day08/ 目录下。列包含：date、metric_name、value、unit。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext csv", "expect_exit": 0}
```

**feedback**：
- `correct`：CSV 文件命名规范正确。
- `incorrect`：CSV 导出文件命名不符合规范，应使用 `20260325_<描述>.csv` 格式，如 `20260325_business_metrics_export.csv`。

---

### r5 — file_check — 异常事件摘要

**Question**：
```
请整理本周的 API 异常事件（5xx 错误和超时），生成异常事件摘要文件，JSON 格式，保存到 day08/ 目录下。包含 generated_at（当前时间）、total_errors、error_types（各类错误计数）、worst_endpoint。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext json --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：异常摘要文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260325_error_event_summary.json` 或类似格式。

---

### r6 — file_check — 数据质量报告

**Question**：
```
请对今天处理的原始数据（api_requests_raw.csv 和 user_activity_raw.json）做数据质量检查，生成质量报告，保存到 day08/ 目录下（Markdown 格式）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：数据质量报告文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260325_data_quality_report.md` 或类似格式。

---

### r7 — multi_choice — 数据文件命名的实践意义

**Question**：
```
在数据处理工作流中，使用 YYYYMMDD_desc.ext 命名规范有哪些实际好处？

A. 文件系统中按名称排序等同于按日期排序，方便查找历史数据
B. 命名规范使文件名更短，节省存储空间
C. 可以通过文件名快速判断数据的时效性（是否为最新）
D. 不同成员生成的同类文件不会因为文件名冲突而相互覆盖
E. snake_case 命名便于脚本使用 glob 模式批量处理特定类型的文件
F. 固定格式的文件名可以被自动化工具解析为元数据

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "按名称排序等于按日期排序",
    "B": "命名更短节省空间",
    "C": "快速判断数据时效性",
    "D": "避免同类文件名冲突",
    "E": "snake_case 便于 glob 模式处理",
    "F": "固定格式可被自动化工具解析"
  },
  "answer": ["A", "C", "E", "F"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 正确：YYYYMMDD 格式使字典序与时间序完全一致，便于按日期查找文件。
  - `B`：B 错误：命名规范通常会使文件名**更长**（加了日期前缀），不是更短。这不是命名规范的设计目标。
  - `C`：C 正确：看到 20260325 就知道是今天的数据，比 20260301 的旧很多，帮助快速判断时效性。
  - `D`：D 错误：YYYYMMDD 前缀实际上会增加同一天同类文件的区分度，但不同人不会因为规范而自动避免冲突（仍需描述部分区分）。此说法不准确。
  - `E`：E 正确：如 `20260325_*.json` 可以批量处理今天的 JSON 文件，snake_case 也便于正则匹配。
  - `F`：F 正确：固定的 YYYYMMDD 前缀可以被脚本直接提取日期信息，无需读取文件内容。

---

### r8 — file_check — 周趋势对比分析

**Question**：
```
请基于本周前三天的数据，生成 API 请求量日趋势对比分析，保存到 day08/ 目录下（JSON 格式）。包含 analysis_generated_at（当前时间）、days（每天的请求量摘要）、trend_summary。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext json --min-count 4", "expect_exit": 0}
```

**feedback**：
- `correct`：趋势对比分析文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260325_weekly_trend_comparison.json` 或类似格式。

---

### r9 — multi_choice — 文件命名与 P1 时间字段

**Question**：
```
分析报告文件需要同时满足 P2（命名规范）和 P1（时间格式）。以下哪些组合是完全正确的？

A. 文件名 20260325_api_trend.json，generated_at: "2026-03-25T10:30:00+08:00"
B. 文件名 20260325_metrics.csv（CSV，无时间字段）
C. 文件名 api_analysis_20260325.json，generated_at: "2026-03-25T10:30:00+08:00"
D. 文件名 20260325_user_report.json，generated_at: "2026/03/25 10:30"
E. 文件名 20260325_error_summary.json，generated_at: "2026-03-25T00:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "命名正确 + 时间字段 ISO 8601",
    "B": "命名正确 + 无时间字段（合规）",
    "C": "命名违规（日期不在前）+ 时间字段正确",
    "D": "命名正确 + 时间字段格式错误",
    "E": "命名正确 + 时间字段 ISO 8601（零点也合法）"
  },
  "answer": ["A", "B", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 完全合规：命名和时间字段均正确。
  - `B`：B 合规：命名正确，CSV 文件没有时间字段也是合规的（P1 只要求时间字段格式正确，不要求必须有时间字段）。
  - `C`：C 命名违规：日期不在最前面，即使时间字段正确，整体也不合规。
  - `D`：D 时间字段违规：`2026/03/25 10:30` 格式不符合 P1 规则（斜线分隔、缺时区）。
  - `E`：E 完全合规：命名正确，`00:00:00+08:00` 是合法的零点时间，格式正确。

---

### r10 — file_check — 错误率告警阈值分析

**Question**：
```
请分析今天的错误率数据，若某小时错误率超过 5% 则标记为告警，生成告警分析报告，JSON 格式，保存到 day08/ 目录下。包含 analysis_at（当前时间约 14:00）、alert_threshold_pct、alerts（触发的时间段列表）、recommendation。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext json --min-count 5", "expect_exit": 0}
```

**feedback**：
- `correct`：告警分析文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260325_error_rate_alert_analysis.json` 或类似格式。

---

### r11 — file_check — 日终数据摘要

**Question**：
```
请整合今天处理的所有数据分析结果，创建日终数据摘要，Markdown 格式，保存到 day08/ 目录下。摘要包含各项分析的主要发现和下一步行动建议。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day08/ --ext md --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：日终摘要文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260325_daily_data_summary.md` 或类似格式。

---

### r12 — multi_choice — 综合命名规范检验

**Question**：
```
在今天的数据处理工作结束后，检查输出文件清单。以下文件名组合中，哪组是全部合规的？

A 组: 20260325_api_request_trend.json, 20260325_user_activity_report.json, 20260325_metrics_export.csv
B 组: api_trend.json, user_activity_20260325.json, metrics_20260325.csv
C 组: 20260325_api_trend.json, 20260325_user_report.json, report_20260325.csv
D 组: 20260325_api_analysis.json, 20260325_user_metrics.json, 20260325_error_summary.csv

请用 \bbox{X} 格式选出全部合规的组。
```

**eval**：
```json
{
  "options": {
    "A": "A 组全部合规",
    "B": "B 组全部合规",
    "C": "C 组全部合规",
    "D": "D 组全部合规"
  },
  "answer": ["A", "D"]
}
```

**feedback**：
- `correct`：正确！A 组和 D 组都完全合规。
- `options`：
  - `A`：A 合规：三个文件名均符合 YYYYMMDD_snake_case.ext 规范。
  - `B`：B 不合规：`api_trend.json` 缺少日期前缀；`user_activity_20260325.json` 和 `metrics_20260325.csv` 的日期不在最前面。
  - `C`：C 不合规：`report_20260325.csv` 的日期不在最前面，违规。
  - `D`：D 合规：三个文件名均符合规范。
