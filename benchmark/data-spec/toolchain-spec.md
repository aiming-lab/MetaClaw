# MetaClaw Evolution Benchmark — 造数据工具链与 GUIDE 模板

> 本文件是所有弧通用的工具参考文档，每个弧的具体 GUIDE.md 应参照本文件的 GUIDE 模板编写。

---

## 一、环境配置

```bash
conda activate smem
# 若需要 LLM API（subagent 调用等）：
source /home/xkaiwen/workspace/utils/apikey/<对应文件>
```

---

## 二、工具路径与快速参考

工具脚本：`/home/xkaiwen/workspace/metaclaw-test/data-synthesis/bench_data_tools.py`

benchmark 数据目录：`/home/xkaiwen/workspace/metaclaw-test/benchmark/data/metaclaw-bench/`

| 子命令 | 用途 | 示例 |
|--------|------|------|
| `init --arc X` | 创建目录骨架 + 生成 UUID | `python bench_data_tools.py init --arc A` |
| `validate --day N` | 验证单天数据格式 | `python bench_data_tools.py validate --day 3` |
| `validate --arc X` | 验证整弧 | `python bench_data_tools.py validate --arc A` |
| `count --arc X` | 估算整弧 token 量 | `python bench_data_tools.py count --arc A` |
| `preview --day N` | 展示 agent 看到的消息序列 | `python bench_data_tools.py preview --day 1` |

`validate` 仅检查本地格式（session JSONL + questions.json），不需要 all_tests.json 完整。最终整体检查用 `metaclaw-bench check`。

---

## 三、目录结构约定

```
data-synthesis/
├── bench_data_tools.py        # 共用工具脚本
├── arc-A/                     # main agent 工作空间（弧 A 的 Claude 窗口专用）
│   ├── uuid_registry.json     # 由 init 自动生成，记录 day01–05 的 UUID
│   ├── day01/                 # subagent 工作空间
│   │   ├── draft_questions.json    # subagent 草稿（未移入最终目录前）
│   │   └── notes.md               # subagent 工作笔记
│   ├── day02/
│   └── ...
├── arc-B/
└── ...
```

benchmark 最终输出目录：
```
benchmark/data/metaclaw-bench/
├── all_tests.json
├── eval/
│   ├── day01/questions.json
│   └── ...
├── openclaw_state/
│   └── agents/metaclaw_agent/sessions/day01_<uuid>.jsonl
└── workspaces/
    └── shared/
        ├── AGENTS.md / IDENTITY.md / SOUL.md / TOOLS.md / USER.md  # 全局共享
        ├── day01/               # 任务素材
        └── ...
```

---

## 四、造数据流程（每弧标准流程）

### Step 0：初始化

```bash
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
conda activate smem
python bench_data_tools.py init --arc A
```

查看生成的 UUID：`cat arc-A/uuid_registry.json`

### Step 1：逐天生成数据（subagent 编排）

main agent 按顺序为每天 dispatch 一个 subagent。**串行**，不并发（避免 workspace 文件冲突）。

每个 subagent 完成后，main agent 立即运行：
```bash
python bench_data_tools.py validate --day N
python bench_data_tools.py preview --day N   # 人工检查消息序列
```

确认无误后，main agent 将该天 entry 追加到 `all_tests.json`（见下方格式）。

### Step 2：整弧验证

```bash
python bench_data_tools.py validate --arc A
python bench_data_tools.py count --arc A
```

### Step 3：最终格式检查

```bash
metaclaw-bench check /path/to/benchmark/data/metaclaw-bench/all_tests.json
```

---

## 五、all_tests.json entry 格式

main agent 在每天 validate 通过后追加一条：

```json
{
  "id": "day01",
  "desc": "Day 1 — <一句话描述场景>",
  "agent": "metaclaw_agent",
  "session": "day01_<uuid>",
  "eval": "day01",
  "arc": "A",
  "preference_tags": ["output_format"]
}
```

`uuid` 从 `data-synthesis/arc-A/uuid_registry.json` 中读取对应 `day01` 的值。

---

## 六、GUIDE.md 模板（复制到 data-spec/arc-X/GUIDE.md 并填写）

---

```markdown
# Arc X — 造数据执行手册

> 本文件是新 Claude Code 窗口的完整工作入口。打开此文件后无需查看历史对话。

## 语言约束（全局，所有弧适用）

**所有 benchmark 数据内容必须用英文**，包括：
- session JSONL 的 user/assistant 消息内容
- workspace 文件内容（README、raw notes、JSON 字段值等）
- questions.json 的 question、feedback（correct/incorrect/options）、multi_choice 选项文本
- done.log 的 task_id 和 summary

规范文档（spec 文件）可以用中文，但**实际生成的数据文件内容必须全是英文**。

---

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：X（Day XX–XX）
**引入偏好**：PX — <偏好名称>
**延续偏好**：<P1, P2, ...>
**数据目录**：`data-synthesis/arc-X/`
**输出目录**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/arc-X/narrative.md` | 偏好规则真相基准：PX 的具体规则，预期失败模式，测试方式 |
| `data-spec/arc-X/dayXX.md` | 每天的详细 spec（session context、workspace 文件、eval rounds）|

**必读顺序**：narrative.md → dayXX.md（按天顺序）

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc X
```

读取 `arc-X/uuid_registry.json`，后续步骤用到的所有 UUID 都来自这里。

必读：`data-spec/arc-X/narrative.md`（理解本弧偏好规则）

### Step 1：生成每天数据（串行，一天一 subagent）

对每天 N（XX 到 XX）：

1. main agent 读取 `data-spec/arc-X/dayXX.md`
2. dispatch subagent（见下方 subagent prompt 模板）
3. subagent 完成后 main agent 运行验证：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N
   ```
4. 确认无误，追加 all_tests.json entry

### Step 2：整弧验证

```bash
python bench_data_tools.py validate --arc X
python bench_data_tools.py count --arc X
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

每次 dispatch subagent 时，使用以下结构：

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark 中 dayXX 的数据。
完成后将所有文件直接写到最终目标路径，不要使用中间路径。

## 环境
conda activate smem
工作目录：/home/xkaiwen/workspace/metaclaw-test/data-synthesis/arc-X/dayXX/

## 你的任务

生成以下三类文件：

1. **Session init 文件**
   路径：benchmark/data/metaclaw-bench/openclaw_state/agents/metaclaw_agent/sessions/dayXX_<uuid>.jsonl
   内容：2 行 {"role": "user"/"assistant", "content": "..."} 引导对话
   UUID：<从 uuid_registry.json 读取>

2. **Workspace 文件**
   路径：benchmark/data/metaclaw-bench/workspaces/shared/dayXX/<文件名>
   内容：<按 spec 创建任务素材文件>

3. **questions.json**
   路径：benchmark/data/metaclaw-bench/eval/dayXX/questions.json
   格式：见 data-spec/data-structure.md 中的 Round 对象格式

## 约束
- 所有偏好规则见 data-spec/arc-X/narrative.md
- 本天详细 spec 见 data-spec/arc-X/dayXX.md
- session init 只有 1–2 轮引导对话，不含具体任务
- questions.json 的 question 字段是完整任务描述，eval 字段内容不拼入消息
- feedback.incorrect 必须包含具体的纠错说明（训练信号）

## 本天 spec

[粘贴 data-spec/arc-X/dayXX.md 全文]

## narrative（偏好规则基准）

[粘贴 data-spec/arc-X/narrative.md 全文]

## UUID

dayXX 的 session UUID：<从 uuid_registry.json 读取对应值>
```

---

## 设计质量 Checklist（每天完成后检查）

- [ ] session init 第一行 role="user"，引导内容介绍用户角色 + 当天背景
- [ ] questions.json rounds 数量在 spec 指定范围内（10–20）
- [ ] 第一个 round 不含 feedback 前缀（首次提问无反馈）
- [ ] 每个 round 的 feedback.incorrect 包含具体纠错原因（不能是空文本）
- [ ] file_check round 的 command 在 workspace 环境下可执行
- [ ] multi_choice 的 answer 只包含 options 中存在的 key
- [ ] validate 通过，preview 人工目测无异常
```

---

## 七、注意事项

- `init` 生成的 UUID 对整个 benchmark 是一次性的，不要重复运行（除非加 `--force`）
- `all_tests.json` 由 main agent 手动追加，每天 validate 通过后再追加，保证增量可用
- `metaclaw-bench check` 需要 all_tests.json 中列出的所有 entry 对应数据都存在才能全部通过；在数据制造过程中只要已完成的 entry 对应数据完整即可
- workspace 全局共享文件（AGENTS.md 等）只需创建一次，在第一个弧（弧 A）造数据时完成
