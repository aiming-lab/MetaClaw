# Arc B — Day 10（2026-03-27 周五）

**领域**：综合（Sprint 8 第一周收尾）
**定位**：P2 最强泛化测试，多文件类型混合场景，P1+P2 全部出现，命名伪装最深
**Rounds**：13

---

## Session 初始上下文

```jsonl
{"role": "user", "content": "今天是 3 月 27 日周五，Sprint 8 第一周最后一天，要整理本周所有产出，准备下午的 Sprint Review。材料在 day10/ 下。"}
{"role": "assistant", "content": "好的，Sprint 第一周收尾工作，我来看看 day10/ 的材料。"}
```

---

## Workspace 文件（`workspaces/shared/day10/`）

### `day10/README.md`
**内容要点**：今天任务：（1）整合本周所有输出文件到归档索引，（2）生成 Sprint Review 材料，（3）起草下周 Sprint 8 第二周计划，（4）创建本周产出的汇总报告。

### `day10/this_week_outputs.txt`
**内容要点**：本周（day06-day09）生成的文件列表（文件名混乱，有规范有不规范），供 agent 整理时参考。约 15 行，每行一个文件名，包含一些故意写错的命名（如 `report.json`、`SprintSummary.md`）用于 multi_choice 题。

---

## Eval Rounds

### r1 — file_check — Sprint Review 主报告

**Question**：
```
请生成本周 Sprint Review 的主报告，JSON 格式，保存到 day10/ 目录下。包含 review_date（今天）、sprint_week（第一周，2026-03-23 至 2026-03-27）、generated_at（当前时间）、completed_tasks（数组）、key_metrics（汇总指标）、blockers（本周遇到的阻碍）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext json", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint Review 主报告命名规范正确。
- `incorrect`：文件命名不符合规范，应使用 `20260327_<描述>.json`，如 `20260327_sprint8_week1_review.json`。

---

### r2 — file_check — Sprint Review 演示文稿大纲

**Question**：
```
请创建 Sprint Review 演示文稿的大纲，Markdown 格式，保存到 day10/ 目录下。包含议程、各团队成员展示模块、Q&A 时间安排。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext md", "expect_exit": 0}
```

**feedback**：
- `correct`：演示大纲文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260327_sprint_review_agenda.md` 或类似格式。

---

### r3 — multi_choice — 本周命名规范执行检查

**Question**：
```
回顾本周生成的文件（来自 day10/this_week_outputs.txt），以下文件名中哪些需要重命名？

A. 20260323_ci_build_report.json
B. test_coverage_20260323.json
C. 20260324_weekly_tech_report.md
D. SprintMeetingNotes.json
E. 20260325_api_request_trend.json
F. user_activity_report.json
G. 20260326_sprint8_midpoint_report.json
H. risk_assessment_v2.md

请用 \bbox{X,Y,...} 格式作答（选出需要重命名的）。
```

**eval**：
```json
{
  "options": {
    "A": "20260323_ci_build_report.json",
    "B": "test_coverage_20260323.json",
    "C": "20260324_weekly_tech_report.md",
    "D": "SprintMeetingNotes.json",
    "E": "20260325_api_request_trend.json",
    "F": "user_activity_report.json",
    "G": "20260326_sprint8_midpoint_report.json",
    "H": "risk_assessment_v2.md"
  },
  "answer": ["B", "D", "F", "H"]
}
```

**feedback**：
- `correct`：完全正确！识别出了所有需要重命名的文件。
- `options`：
  - `A`：A 合规，无需重命名。
  - `B`：B 需重命名：日期不在最前面。应为 `20260323_test_coverage.json`。
  - `C`：C 合规，无需重命名。
  - `D`：D 需重命名：缺少日期前缀，驼峰命名。应为 `20260324_sprint_meeting_notes.json`。
  - `E`：E 合规，无需重命名。
  - `F`：F 需重命名：缺少日期前缀。应为 `20260325_user_activity_report.json`。
  - `G`：G 合规，无需重命名。
  - `H`：H 需重命名：缺少日期前缀。应为 `20260326_risk_assessment_v2.md`（或对应实际创建日期）。

---

### r4 — file_check — 本周归档索引

**Question**：
```
请创建本周产出文件的归档索引，JSON 格式，保存到 day10/ 目录下。列出本周（day06-day09）所有输出文件的文件名、类型、创建时间（archived_at 用今天下午 17:00）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext json --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：归档索引文件命名规范正确。
- `incorrect`：归档索引文件命名不符合规范，应为 `20260327_week1_archive_index.json` 或类似格式。

---

### r5 — file_check — 下周计划（Sprint 8 第二周）

**Question**：
```
请起草 Sprint 8 第二周的工作计划，JSON 格式，保存到 day10/ 目录下。包含 plan_week（下周日期范围：2026-03-30 至 2026-04-03）、plan_created_at（当前时间）、goals（数组）、tasks（含 task_id、assignee、due_date）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext json --min-count 3", "expect_exit": 0}
```

**feedback**：
- `correct`：下周计划文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260327_sprint8_week2_plan.json` 或类似格式。

---

### r6 — file_check — P1 时间字段检查（Sprint Review 报告）

**Question**：
```
请检查 day10/ 下的 Sprint Review 主报告，确认 generated_at 和 review_date 字段格式正确，如有错误请修正（覆盖原文件）。
```

**eval**：
```json
{"command": "python -c \"import json,re,glob,sys; files=sorted(glob.glob('day10/[0-9]*_*review*.json')); f=files[0] if files else sys.exit(1); d=json.load(open(f)); pat=re.compile(r'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.[0-9]+)?\\+08:00$'); ok=pat.match(str(d.get('generated_at',''))); sys.exit(0 if ok else 1)\"", "expect_exit": 0}
```

**feedback**：
- `correct`：Sprint Review 报告中的时间字段格式正确。
- `incorrect`：Sprint Review 报告的 generated_at 或 review_date 格式不符合 ISO 8601 要求（需含 +08:00 时区偏移）。

---

### r7 — multi_choice — 本周工作总结：P2 规范理解

**Question**：
```
经过本周的工作，关于文件命名规范，以下哪些总结是正确的？

A. 所有 agent 生成的输出文件，无论格式（JSON/MD/CSV），都需要日期前缀
B. 文件名中的日期反映文件生成日期，不是内容描述的事件日期
C. 预置的参考资料文件（如 standup_raw.txt）也需要遵循 P2 规范
D. 日期格式必须是 YYYYMMDD（8位），不能是 YYYY-MM-DD（10位带连字符）
E. 描述部分可以包含数字（如 sprint8、v2），只要都是小写
F. 同一天同类型的多个文件通过描述部分区分，日期前缀相同

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "所有输出文件（无论格式）都需要日期前缀",
    "B": "日期反映文件生成日期",
    "C": "预置参考文件也需要 P2 规范",
    "D": "日期必须是 8 位 YYYYMMDD 格式",
    "E": "描述部分可含数字（小写）",
    "F": "同天同类文件通过描述区分"
  },
  "answer": ["A", "B", "D", "E", "F"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 正确：P2 对所有输出文件类型一律适用。
  - `B`：B 正确：日期前缀 = 生成日期，不是内容日期。
  - `C`：C 错误：预置的参考文件（workspace 素材）不需要遵循 P2，只有 agent 生成的输出才需要。
  - `D`：D 正确：必须是 YYYYMMDD 8位紧凑格式，不接受 YYYY-MM-DD。
  - `E`：E 正确：描述部分允许数字（`[a-z0-9_]*` 模式），如 `sprint8`、`v2` 合法。
  - `F`：F 正确：同一天多个文件日期前缀相同，通过描述部分区分内容。

---

### r8 — file_check — 本周技术债务更新

**Question**：
```
请更新本周技术债务记录，创建本周技术债务总结文档，JSON 格式，保存到 day10/ 目录下。包含 summary_generated_at（当前时间）、total_debt_items、high_priority_count、items（数组，每条含 id、title、priority、created_at、sprint）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext json --min-count 4", "expect_exit": 0}
```

**feedback**：
- `correct`：技术债务总结文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260327_tech_debt_weekly_summary.json` 或类似格式。

---

### r9 — file_check — 团队周总结（CSV）

**Question**：
```
请生成本周团队任务完成情况的 CSV 汇总，供报表使用，保存到 day10/ 目录下。列为：member_name、tasks_completed、hours_logged、blocker_count。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext csv", "expect_exit": 0}
```

**feedback**：
- `correct`：团队周总结 CSV 文件命名规范正确。
- `incorrect`：CSV 文件命名不符合规范，应为 `20260327_team_weekly_stats.csv` 或类似格式。

---

### r10 — multi_choice — 综合场景命名

**Question**：
```
在 Sprint Review 后，团队决定将本周所有产出归档。以下归档文件名，哪些是完全合规的？

A. 20260327_sprint8_week1_review.json
B. 20260327_archive_index.json
C. sprint8_week1_summary_20260327.md
D. 20260327_team_weekly_stats.csv
E. 20260327_next_week_plan.json
F. TechDebtSummary_20260327.json
G. 20260327_sprint_review_agenda.md

请用 \bbox{X,Y,...} 格式作答（选合规的）。
```

**eval**：
```json
{
  "options": {
    "A": "20260327_sprint8_week1_review.json",
    "B": "20260327_archive_index.json",
    "C": "sprint8_week1_summary_20260327.md（日期在后）",
    "D": "20260327_team_weekly_stats.csv",
    "E": "20260327_next_week_plan.json",
    "F": "TechDebtSummary_20260327.json（驼峰+日期在后）",
    "G": "20260327_sprint_review_agenda.md"
  },
  "answer": ["A", "B", "D", "E", "G"]
}
```

**feedback**：
- `correct`：完全正确！
- `options`：
  - `A`：A 合规：格式正确。
  - `B`：B 合规：格式正确。
  - `C`：C 不合规：日期在最后，不符合规范。
  - `D`：D 合规：格式正确。
  - `E`：E 合规：格式正确。
  - `F`：F 不合规：驼峰命名且日期在后，两项均违规。
  - `G`：G 合规：格式正确。

---

### r11 — file_check — 下周 OKR 追踪

**Question**：
```
请创建下周的 OKR 追踪文件，JSON 格式，保存到 day10/ 目录下。包含 tracking_period_start（下周一 09:00）、tracking_period_end（下周五 18:00）、created_at（当前时间）、objectives（数组，每个含 title、key_results 数组）。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext json --min-count 5", "expect_exit": 0}
```

**feedback**：
- `correct`：OKR 追踪文件命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260327_next_week_okr_tracker.json` 或类似格式。

---

### r12 — multi_choice — P1+P2 最终综合

**Question**：
```
以下是 Sprint Review 结束后的最终文件清单，哪些文件在命名 AND 关键时间字段上均合规？

A. 文件名 20260327_sprint8_review.json，generated_at: "2026-03-27T14:00:00+08:00"
B. 文件名 20260327_week2_plan.json，plan_start: "2026-03-30"（纯日期）
C. 文件名 archive_index.json，archived_at: "2026-03-27T17:00:00+08:00"
D. 文件名 20260327_team_stats.csv（无时间字段）
E. 文件名 20260327_okr_tracker.json，tracking_period_start: "2026-03-30T09:00:00+08:00"

请用 \bbox{X,Y,...} 格式作答。
```

**eval**：
```json
{
  "options": {
    "A": "命名正确 + 时间字段 ISO 8601",
    "B": "命名正确 + plan_start 为纯日期（P1 违规）",
    "C": "命名违规（无日期前缀）+ 时间字段正确",
    "D": "命名正确 + 无时间字段（合规）",
    "E": "命名正确 + 时间字段 ISO 8601"
  },
  "answer": ["A", "D", "E"]
}
```

**feedback**：
- `correct`：正确！
- `options`：
  - `A`：A 完全合规。
  - `B`：B P1 违规：`plan_start` 是纯日期格式，缺少时间和时区，违反 P1 规范。
  - `C`：C P2 违规：文件名缺少日期前缀。
  - `D`：D 完全合规：命名正确，CSV 无时间字段无需满足 P1。
  - `E`：E 完全合规：命名和时间字段均正确。

---

### r13 — file_check — 整周复盘文档

**Question**：
```
请创建本周（Sprint 8 第一周）的完整工作复盘文档，Markdown 格式，保存到 day10/ 目录下。包含：本周亮点、遇到的问题、改进建议、对下周的期望。
```

**eval**：
```json
{"command": "python eval/scripts/check_filename.py --dir day10/ --ext md --min-count 2", "expect_exit": 0}
```

**feedback**：
- `correct`：周复盘文档命名规范正确。
- `incorrect`：文件命名不符合规范，应为 `20260327_week1_retrospective.md` 或类似格式。
