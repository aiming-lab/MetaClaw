# Arc F — 叙事基准（Narrative）

> 本弧真相基准。subagent 造数据时必须读取本文件。

---

## 本弧核心定位：P1-P5 全规则混合收尾

**本弧不引入新偏好规则。**

Arc F 是整个 benchmark 的最终考核弧。5 条偏好规则（P1-P5）同时生效，每天场景伪装最深——任务描述绝不暗示需要遵守哪条规则。Agent 必须凭已学习的行为模式自动触发全部规则，方可通过 eval。

**设计目标**：
1. 验证 MetaClaw 在习得所有规则后能否稳定泛化到新场景
2. 测试规则之间的交互理解（如 P4 备份后同样需要 P5 日志）
3. 在"最深伪装"条件下以 multi-rule eval 精准区分学会/未学会的 agent

---

## 日期设定

| Day | 日期 | 星期 |
|-----|------|------|
| 26 | 2026-04-20 | 周一 |
| 27 | 2026-04-21 | 周二 |
| 28 | 2026-04-22 | 周三 |
| 29 | 2026-04-23 | 周四 |
| 30 | 2026-04-24 | 周五 |

Sprint 10 第一周（2026-04-20 至 04-24）。

---

## 各天领域与规则覆盖

| Day | 领域 | 主要规则组合 | done.log 预期条目（当天追加数）|
|-----|------|------------|--------------------------|
| 26 | 代码工程 | P1+P2+P3+P4+P5 | 4-5 条 |
| 27 | 技术文档 | P1+P2+P3+P4+P5 | 4 条 |
| 28 | 数据处理 | P1+P2+P3+P4+P5 | 5 条 |
| 29 | 项目管理 | P1+P2+P3+P4+P5 | 4 条 |
| 30 | 综合收尾 | P1+P2+P3+P4+P5（全部，最难）| 5-6 条 |

---

## Eval 脚本复用

Arc F 全部复用既有脚本，**不新建**任何 eval 脚本：

| 脚本 | 检验规则 |
|------|---------|
| `eval/scripts/check_iso8601.py` | P1 — 时间格式 |
| `eval/scripts/check_filename.py` | P2 — 文件命名 |
| `eval/scripts/check_metadata.py` | P3 — metadata 完整性 |
| `eval/scripts/check_backup.py` | P4 — 操作前备份 |
| `eval/scripts/check_done_log.py` | P5 — done.log 追加 |

---

## 深度伪装原则

每个 question 只描述业务需求，绝对不含任何规则提示：
- 不出现 "ISO 8601"、"YYYYMMDD"、"metadata"、"backup"、".bak"、"done.log" 等关键词
- 时间字段通过自然业务语言触发（"include the creation time"、"add a timestamp"）
- 文件保存路径只说目录，不指定文件名（让 agent 自行命名，测试 P2）
- 修改任务只说"update"/"edit"，不提备份（测试 P4）
- 每天多个任务，任务完成后不提记录（测试 P5）

---

## Multi-Rule Eval 设计规范

Arc F 的 file_check eval 大量使用链式命令，典型模式：

```bash
# P2+P3+P5
python -c "import glob,sys; files=sorted(glob.glob('dayXX/20260420_*.ext')); sys.exit(0 if files else 1)" \
  && python eval/scripts/check_metadata.py $(python -c "import glob; print(sorted(glob.glob('dayXX/20260420_*.ext'))[0])") \
  && python eval/scripts/check_done_log.py done.log --min-entries N

# P1+P2+P3+P5 (JSON with time fields)
python -c "..." \
  && python eval/scripts/check_iso8601.py $(python -c "...") meta.created_at <other_time_field> \
  && python eval/scripts/check_metadata.py $(python -c "...") \
  && python eval/scripts/check_done_log.py done.log --min-entries N

# P4+P5 (modifying existing file)
python eval/scripts/check_backup.py dayXX/<existing_file> \
  && python eval/scripts/check_done_log.py done.log --min-entries N
```

---

## Workspace 预置设计

每天 workspace 包含多个预置的"待修改"已有文件（触发 P4），同时包含需新建的文件任务（触发 P2+P3）。

- Day 26-30 的 `done.log` 均**预置**，包含前几天的历史条目（测试追加不覆盖）
- 预置文件内容使用英文，格式合理但**刻意不符合**某些规则（如时间字段用纯日期、文件无 metadata）

---

## 预期 arc-F 失败方式

已学会的 agent（MetaClaw）应全部通过。基线模型的典型失败组合：
- 记住了 P1 但新文件类型（Python 文件 Meta section）不会
- 记住了 P2 但忘记 P3（文件名对了但没有 metadata）
- 记住了 P4 但忘记 P5（备份了但没追加 done.log）
- P5 条目数错误（任务数多但记录数少，说明部分任务完成后忘记追加）

---

## 语言约束

**所有数据内容必须用英文**：session JSONL 消息、workspace 文件内容、question/feedback 文本、multi_choice 选项。done.log 的 task_id 和 summary 必须用英文。

---

## 造数据约束

1. question 中绝对不出现任何 P1-P5 规则关键词提示
2. 每天有 4-6 个独立任务，done.log 条目数随任务推进递增
3. feedback.incorrect 必须明确指出违反了哪条规则（P1-P5），并给出完整正确示例
4. multi_choice 题目测试规则合理的边界理解，不只是重复规则定义
5. eval command 中使用 `python -c` glob 模式处理动态文件名（不能硬编码 agent 生成的文件名）
