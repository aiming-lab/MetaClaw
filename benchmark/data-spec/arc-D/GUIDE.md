# Arc D — 造数据执行手册

> 新 Claude Code 窗口完整工作入口。

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：D（Day 16–20，2026-04-06 周一 至 2026-04-10 周五）
**引入偏好**：P4 — 操作前备份（修改已有文件前创建 .bak）
**延续偏好**：P1、P2、P3
**工作目录**：`data-synthesis/arc-D/`
**benchmark 输出**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/preferences.md` | P1-P5 全局定义（必读）|
| `data-spec/arc-D/narrative.md` | P4 真相基准：check_backup.py 实现、各天领域、约束 |
| `data-spec/arc-D/day16.md` | Day 16（文档写作，P4 首次引入，10 rounds）|
| `data-spec/arc-D/day17.md` | Day 17（数据处理，11 rounds）|
| `data-spec/arc-D/day18.md` | Day 18（代码工程，12 rounds）|
| `data-spec/arc-D/day19.md` | Day 19（项目管理，P1+P2+P4，11 rounds）|
| `data-spec/arc-D/day20.md` | Day 20（综合，13 rounds）|

**必读顺序**：`preferences.md` → `narrative.md` → `day16.md`–`day20.md`

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc D
cat arc-D/uuid_registry.json
```

### Step 1：创建 eval 脚本

在 `benchmark/data/metaclaw-bench/eval/scripts/` 下创建 `check_backup.py`。

脚本完整实现见 `data-spec/arc-D/narrative.md`。

### Step 2：逐天生成数据（串行）

对每天 N（16–20）顺序执行：

1. 读取 `data-spec/arc-D/dayN.md`，dispatch subagent
2. 验证：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N
   ```
3. 验证通过后追加 `all_tests.json` entry

### Step 3：整弧验证

```bash
python bench_data_tools.py validate --arc D
python bench_data_tools.py count --arc D
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark arc-D 中 dayXX 的数据。

## 关键设计要点（P4）
- workspace 中必须有预置的已有文件供 agent 修改
- question 说 "update/modify <filename>"，但不提备份
- feedback.incorrect 解释需在修改前创建 .bak 文件
- eval 用 check_backup.py 检查 <原文件>.bak 是否存在且内容不同

## 核心约束
- **所有数据内容（session 消息、workspace 文件、question/feedback）必须用英文**
- question 不得含 "backup"、".bak"、"copy first" 等提示
- P1-P3 规则同样适用

## 本天 spec
[粘贴 data-spec/arc-D/dayXX.md 全文]

## 偏好规则基准
[粘贴 data-spec/arc-D/narrative.md 全文]
[粘贴 data-spec/preferences.md P1-P4 部分]
```

---

## all_tests.json entry 格式

```json
{
  "id": "day16",
  "desc": "Day 16 — 文档更新，P4 备份首次引入",
  "agent": "metaclaw_agent",
  "session": "day16_<uuid>",
  "eval": "day16",
  "arc": "D",
  "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow"]
}
```

---

## 设计质量 Checklist

每天完成后：
- [ ] workspace 预置了需要被修改的已有文件
- [ ] question 明确说修改已有文件，但不提备份
- [ ] feedback.incorrect 说明需先创建 .bak
- [ ] eval.command 正确使用 check_backup.py <filepath>

整弧完成后：
- [ ] Day 16 是 P4 首次出现，workspace 有 1-2 个需修改的文件
- [ ] 有 round 测试"新建文件不需要 .bak"（验证 agent 理解边界）
- [ ] Day 19 有 P1+P2+P4 联合测试
