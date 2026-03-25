# Arc F — 造数据执行手册

> 新 Claude Code 窗口完整工作入口。

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：F（Day 26–30，2026-04-20 周一 至 2026-04-24 周五）
**引入偏好**：无（混合收尾，P1-P5 全部规则同时生效）
**延续偏好**：P1、P2、P3、P4、P5
**工作目录**：`data-synthesis/arc-F/`
**benchmark 输出**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/preferences.md` | P1-P5 全局定义（必读）|
| `data-spec/arc-F/narrative.md` | Arc-F 设计原则：深度伪装、multi-rule eval、各天覆盖 |
| `data-spec/arc-F/day26.md` | Day 26（代码工程，P1-P5 全部，12 rounds）|
| `data-spec/arc-F/day27.md` | Day 27（技术文档，P1-P5，11 rounds）|
| `data-spec/arc-F/day28.md` | Day 28（数据处理，P1-P5，13 rounds）|
| `data-spec/arc-F/day29.md` | Day 29（项目管理，P1-P5，11 rounds）|
| `data-spec/arc-F/day30.md` | Day 30（综合收尾，P1-P5，15 rounds，最终最难）|

**必读顺序**：`preferences.md` → `narrative.md` → `day26.md`–`day30.md`

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc F
cat arc-F/uuid_registry.json
```

### Step 1：逐天生成数据（串行）

对每天 N（26–30）顺序执行：

1. 读取 `data-spec/arc-F/dayN.md`，dispatch subagent
2. 验证：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N
   ```
3. 验证通过后追加 `all_tests.json` entry

**注意**：Arc F 不需要新建 eval 脚本，全部复用弧 A-E 已创建的 5 个脚本。

### Step 2：整弧验证

```bash
python bench_data_tools.py validate --arc F
python bench_data_tools.py count --arc F
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark arc-F 中 dayXX 的数据。

## 关键设计要点（Arc F：混合收尾）
- 本弧无新规则，P1-P5 全部规则同时生效
- 所有 question 不得含任何规则提示词，只描述业务需求
- 每个 file_check eval 需用 `&&` 链式检验多条规则
- 文件名动态时使用 python -c + glob 模式获取文件路径
- 每天有 4-6 个独立任务，done.log 条目递增

## 核心约束
- **所有数据内容（session 消息、workspace 文件、question/feedback）必须用英文**
- question 不得含 "ISO 8601"、"YYYYMMDD"、"metadata"、"backup"、".bak"、"done.log" 等提示词
- feedback.incorrect 必须明确指出违反了哪条规则（P1-P5），并给出完整正确示例
- P1-P5 规则全部适用

## 本天 spec
[粘贴 data-spec/arc-F/dayXX.md 全文]

## 偏好规则基准
[粘贴 data-spec/arc-F/narrative.md 全文]
[粘贴 data-spec/preferences.md 全文]
```

---

## all_tests.json entry 格式

```json
{
  "id": "day26",
  "desc": "Day 26 — Sprint 10 代码工程，P1-P5 全部规则",
  "agent": "metaclaw_agent",
  "session": "day26_<uuid>",
  "eval": "day26",
  "arc": "F",
  "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow", "completion_log"]
}
```

---

## 设计质量 Checklist

每天完成后：
- [ ] question 不含任何 P1-P5 提示词
- [ ] 每个 file_check eval 覆盖至少 2-3 条规则（链式命令）
- [ ] feedback.incorrect 明确指出违反规则编号（P1/P2/P3/P4/P5）
- [ ] done.log --min-entries 随任务推进递增
- [ ] 使用 glob 动态定位文件（不硬编码文件名）

整弧完成后：
- [ ] Day 26-30 每天都有至少一个同时测 3 条以上规则的 file_check round
- [ ] Day 30 有覆盖全部 P1-P5 的综合 round
- [ ] multi_choice 题目聚焦规则交互与边界，不只是重述规则定义
- [ ] 所有 eval 脚本均为已有脚本（不新建）
