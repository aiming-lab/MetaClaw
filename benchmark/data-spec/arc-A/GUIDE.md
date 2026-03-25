# Arc A — 造数据执行手册

> 本文件是新 Claude Code 窗口的完整工作入口。打开此文件后无需查看历史对话。

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：A（Day 01–05，2026-03-16 周一 至 2026-03-20 周五）
**引入偏好**：P1 — 时间格式统一（ISO 8601 with +08:00）
**延续偏好**：无（首弧）
**工作目录**：`data-synthesis/arc-A/`
**benchmark 输出**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/preferences.md` | P1-P5 全局定义（必读，理解 P1 精确规则）|
| `data-spec/arc-A/narrative.md` | P1 在 arc-A 的真相基准：日期设定、脚本接口、各天领域分布、造数据约束 |
| `data-spec/arc-A/day01.md` | Day 01 完整 spec（文档写作，10 rounds）|
| `data-spec/arc-A/day02.md` | Day 02 spec（项目管理，11 rounds）|
| `data-spec/arc-A/day03.md` | Day 03 spec（数据处理，12 rounds）|
| `data-spec/arc-A/day04.md` | Day 04 spec（代码工程，10 rounds）|
| `data-spec/arc-A/day05.md` | Day 05 spec（综合收尾，13 rounds）|

**必读顺序**：`preferences.md` → `narrative.md` → 按天顺序读 day01.md–day05.md

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc A
cat arc-A/uuid_registry.json   # 记录 day01-day05 的 UUID
```

### Step 1：创建全局共享 workspace 文件

首次运行（其他弧复用）：在 `benchmark/data/metaclaw-bench/workspaces/shared/` 下创建：
- `AGENTS.md`：agent 角色说明，**不得含任何时间格式偏好提示**
- `IDENTITY.md`：agent 身份设定
- `SOUL.md`：agent 行为原则
- `TOOLS.md`：可用工具列表
- `USER.md`：Alex Zhang 的基本信息（姓名、职位、公司、时区），**不含时间格式偏好**

### Step 2：创建 eval 脚本

在 `benchmark/data/metaclaw-bench/eval/scripts/` 下创建 `check_iso8601.py`。

脚本完整实现见 `data-spec/arc-A/narrative.md` 的「eval 脚本」节。

### Step 3：逐天生成数据（串行，一天一 subagent）

对每天 N（01–05）顺序执行：

1. main agent 读取 `data-spec/arc-A/dayN.md`
2. dispatch subagent（见下方 subagent prompt 模板）
3. subagent 完成后，main agent 运行验证：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N   # 目测检查消息序列是否合理
   ```
4. 验证通过后，main agent 追加 `all_tests.json` entry（见下方格式）

### Step 4：整弧验证

```bash
python bench_data_tools.py validate --arc A
python bench_data_tools.py count --arc A
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

为每天 dispatch 一个 subagent，使用以下结构：

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark arc-A 中 dayXX 的数据。
将所有文件直接写到最终目标路径。

## 环境
conda activate smem
工作目录：/home/xkaiwen/workspace/metaclaw-test/data-synthesis/arc-A/dayXX/

## 目标文件路径

1. Session init：
   benchmark/data/metaclaw-bench/openclaw_state/agents/metaclaw_agent/sessions/dayXX_<UUID>.jsonl
   格式：2 行 {"role": "user/assistant", "content": "..."} 引导对话
   UUID：<从 arc-A/uuid_registry.json 中读取 dayXX 对应值>

2. Workspace 文件：
   benchmark/data/metaclaw-bench/workspaces/shared/dayXX/<文件名>
   （按 spec 创建所有文件，内容见下方 spec）

3. questions.json：
   benchmark/data/metaclaw-bench/eval/dayXX/questions.json
   格式：见 data-spec/data-structure.md

## 造数据约束
- **所有数据内容（session 消息、workspace 文件内容、question/feedback 文本）必须用英文**
- 时间场景素材（如 standup_raw.txt）中使用自然语言时间（英文），不出现 ISO 8601
- question 字段不得出现 "ISO 8601"、"+08:00"、"timezone" 等提示词
- feedback.incorrect 必须包含正确格式的示例（这是最重要的训练信号）
- multi_choice 每题 5-8 个选项，干扰项要合理

## 本天详细 spec
[粘贴 data-spec/arc-A/dayXX.md 全文]

## P1 规则基准
[粘贴 data-spec/arc-A/narrative.md 全文]
```

---

## all_tests.json entry 格式

每天 validate 通过后追加：

```json
{
  "id": "day01",
  "desc": "Day 01 — Sprint 7 开始，会议纪要整理（P1 首次引入）",
  "agent": "metaclaw_agent",
  "session": "day01_<uuid_registry 中的 day01 UUID>",
  "eval": "day01",
  "arc": "A",
  "preference_tags": ["output_format"]
}
```

`arc` 字段统一为 `"A"`，`preference_tags` 统一为 `["output_format"]`。

---

## 设计质量 Checklist

每天完成后检查：

- [ ] session init 第一行 role="user"，内容介绍当天背景，不含任务
- [ ] workspace 原始素材文件中的时间使用自然语言（不含 ISO 8601）
- [ ] questions.json 中所有 question 字段不含 "ISO 8601"、"+08:00" 等提示
- [ ] 第一个 round 的 feedback.incorrect 包含明确的纠错说明和正确示例
- [ ] file_check 的 eval.command 在 workspace 目录下可正确执行
- [ ] multi_choice 的 answer 只包含 eval.options 中存在的 key
- [ ] feedback.options 的 key 与 eval.options 的 key 完全一致
- [ ] validate 通过，preview 目测无异常
- [ ] 每天 uuid 使用 uuid_registry.json 中对应的值，不自行生成

整弧完成后检查：

- [ ] Day 01 是 P1 的真正首次出现（workspace 和 session 中无提示）
- [ ] Day 03 的领域与 Day 01/02 明显不同（数据处理 vs 文档/项目管理）
- [ ] Day 05 的场景比 Day 01 更复杂（多文件类型、时间格式更混乱的素材）
- [ ] check_iso8601.py 脚本已创建且接口正确
- [ ] all_tests.json 包含 5 条 entry，UUID 与 session 文件名一致
