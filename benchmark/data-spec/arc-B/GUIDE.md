# Arc B — 造数据执行手册

> 新 Claude Code 窗口完整工作入口。

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：B（Day 06–10，2026-03-23 周一 至 2026-03-27 周五）
**引入偏好**：P2 — 文件命名规范（YYYYMMDD_snake_case.ext）
**延续偏好**：P1（时间格式）
**工作目录**：`data-synthesis/arc-B/`
**benchmark 输出**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/preferences.md` | P1-P5 全局定义（必读）|
| `data-spec/arc-B/narrative.md` | P2 真相基准：脚本接口、各天领域、失败方式、约束 |
| `data-spec/arc-B/day06.md` | Day 06（代码工程，P2 首次引入，10 rounds）|
| `data-spec/arc-B/day07.md` | Day 07（文档写作，11 rounds）|
| `data-spec/arc-B/day08.md` | Day 08（数据处理，12 rounds）|
| `data-spec/arc-B/day09.md` | Day 09（项目管理，P1+P2，11 rounds）|
| `data-spec/arc-B/day10.md` | Day 10（综合收尾，13 rounds）|

**必读顺序**：`preferences.md` → `narrative.md` → `day06.md`–`day10.md`

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc B
cat arc-B/uuid_registry.json
```

### Step 1：创建 eval 脚本

在 `benchmark/data/metaclaw-bench/eval/scripts/` 下创建 `check_filename.py`。

脚本完整实现见 `data-spec/arc-B/narrative.md`。

### Step 2：逐天生成数据（串行）

对每天 N（06–10）顺序执行：

1. 读取 `data-spec/arc-B/dayN.md`，dispatch subagent
2. subagent 完成后运行：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N
   ```
3. 验证通过后追加 `all_tests.json` entry

### Step 3：整弧验证

```bash
python bench_data_tools.py validate --arc B
python bench_data_tools.py count --arc B
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark arc-B 中 dayXX 的数据。
将所有文件直接写到最终目标路径。

## 目标文件
1. Session init: benchmark/data/metaclaw-bench/openclaw_state/agents/metaclaw_agent/sessions/dayXX_<UUID>.jsonl
2. Workspace 文件: benchmark/data/metaclaw-bench/workspaces/shared/dayXX/<文件>
3. questions.json: benchmark/data/metaclaw-bench/eval/dayXX/questions.json

## 核心约束
- **所有数据内容（session 消息、workspace 文件、question/feedback）必须用英文**
- question 字段不得出现 P2 提示（YYYYMMDD、snake_case、naming convention 等）
- question 只说 "save to dayXX/ directory"，不指定文件名
- feedback.incorrect 必须给出正确命名示例（如 20260323_test_report.json）
- P1 规则同样适用：含时间字段的文件时间格式需正确
- UUID 从 arc-B/uuid_registry.json 读取

## 本天详细 spec
[粘贴 data-spec/arc-B/dayXX.md 全文]

## 偏好规则基准
[粘贴 data-spec/arc-B/narrative.md 全文]
[粘贴 data-spec/preferences.md P1、P2 部分]
```

---

## all_tests.json entry 格式

```json
{
  "id": "day06",
  "desc": "Day 06 — Sprint 8 开始，代码工程任务（P2 首次引入）",
  "agent": "metaclaw_agent",
  "session": "day06_<uuid>",
  "eval": "day06",
  "arc": "B",
  "preference_tags": ["output_format", "file_naming"]
}
```

---

## 设计质量 Checklist

每天完成后：
- [ ] workspace 预置参考文件用普通名称（不强制 P2）
- [ ] question 不含命名规范提示词
- [ ] Day 06 第一个 round 的 feedback.incorrect 给出具体正确命名示例
- [ ] file_check 的 eval.command 使用 check_filename.py --dir
- [ ] validate 和 preview 通过

整弧完成后：
- [ ] Day 06 是 P2 首次出现（无提示）
- [ ] Day 08 的领域与 Day 06/07 明显不同
- [ ] Day 09 有 P1+P2 联合测试的 round
- [ ] check_filename.py 已创建
