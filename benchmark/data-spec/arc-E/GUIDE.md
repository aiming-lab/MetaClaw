# Arc E — 造数据执行手册

> 新 Claude Code 窗口完整工作入口。

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：E（Day 21–25，2026-04-13 周一 至 2026-04-17 周五）
**引入偏好**：P5 — 完成状态日志（done.log 追加）
**延续偏好**：P1、P2、P3、P4
**工作目录**：`data-synthesis/arc-E/`
**benchmark 输出**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/preferences.md` | P1-P5 全局定义（必读）|
| `data-spec/arc-E/narrative.md` | P5 真相基准：check_done_log.py 实现、各天领域、约束 |
| `data-spec/arc-E/day21.md` | Day 21（文档写作，P5 首次引入，10 rounds）|
| `data-spec/arc-E/day22.md` | Day 22（项目管理，11 rounds）|
| `data-spec/arc-E/day23.md` | Day 23（数据处理，12 rounds）|
| `data-spec/arc-E/day24.md` | Day 24（代码工程，P1+P3+P5，11 rounds）|
| `data-spec/arc-E/day25.md` | Day 25（综合，13 rounds）|

**必读顺序**：`preferences.md` → `narrative.md` → `day21.md`–`day25.md`

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc E
cat arc-E/uuid_registry.json
```

### Step 1：创建 eval 脚本

在 `benchmark/data/metaclaw-bench/eval/scripts/` 下创建 `check_done_log.py`。

脚本完整实现见 `data-spec/arc-E/narrative.md`。

### Step 2：逐天生成数据（串行）

对每天 N（21–25）顺序执行：

1. 读取 `data-spec/arc-E/dayN.md`，dispatch subagent
2. 验证：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N
   ```
3. 验证通过后追加 `all_tests.json` entry

### Step 3：整弧验证

```bash
python bench_data_tools.py validate --arc E
python bench_data_tools.py count --arc E
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark arc-E 中 dayXX 的数据。

## 关键设计要点（P5）
- 每个独立任务完成后，agent 应向 done.log 追加一行
- done.log 在 workspace 根目录（非 dayXX/ 子目录）
- 每天有多个任务，done.log 条目数应随任务推进递增
- eval 用 check_done_log.py --min-entries N 验证

## 核心约束
- **所有数据内容（session 消息、workspace 文件、question/feedback）必须用英文**
- question 不得含 "done.log"、"log"、"record completion" 等提示词
- P1-P4 规则同样适用

## 本天 spec
[粘贴 data-spec/arc-E/dayXX.md 全文]

## 偏好规则基准
[粘贴 data-spec/arc-E/narrative.md 全文]
[粘贴 data-spec/preferences.md P1-P5 部分]
```

---

## all_tests.json entry 格式

```json
{
  "id": "day21",
  "desc": "Day 21 — 文档写作，P5 done.log 首次引入",
  "agent": "metaclaw_agent",
  "session": "day21_<uuid>",
  "eval": "day21",
  "arc": "E",
  "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow", "completion_log"]
}
```

---

## 设计质量 Checklist

每天完成后：
- [ ] done.log 在 workspace 根目录（不是 dayXX/ 下）
- [ ] 每天有 3-5 个独立任务，eval 按递增 --min-entries 检查
- [ ] question 不含 P5 提示词
- [ ] feedback.incorrect 给出完整 done.log 行格式示例

整弧完成后：
- [ ] Day 21 是 P5 首次出现
- [ ] Day 22 开始 workspace 预置已有 done.log（测试追加不覆盖）
- [ ] Day 24 有 P1+P3+P5 联合测试
- [ ] Day 25 涉及 P1-P5 全部规则
