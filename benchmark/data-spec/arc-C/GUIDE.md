# Arc C — 造数据执行手册

> 新 Claude Code 窗口完整工作入口。

## 环境

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/data-synthesis
```

## 本弧概述

**弧**：C（Day 11–15，2026-03-30 周一 至 2026-04-03 周五）
**引入偏好**：P3 — 文件 metadata 完整性
**延续偏好**：P1（时间格式）、P2（文件命名）
**工作目录**：`data-synthesis/arc-C/`
**benchmark 输出**：`benchmark/data/metaclaw-bench/`

## Spec 文件索引

| 文件 | 内容 |
|------|------|
| `data-spec/preferences.md` | P1-P5 全局定义（必读）|
| `data-spec/arc-C/narrative.md` | P3 真相基准：check_metadata.py 完整实现、各天领域、约束 |
| `data-spec/arc-C/day11.md` | Day 11（文档/MD，P3 首次引入，10 rounds）|
| `data-spec/arc-C/day12.md` | Day 12（数据/JSON，11 rounds）|
| `data-spec/arc-C/day13.md` | Day 13（代码/Python，12 rounds）|
| `data-spec/arc-C/day14.md` | Day 14（项目管理，P1+P2+P3，11 rounds）|
| `data-spec/arc-C/day15.md` | Day 15（综合，13 rounds）|

**必读顺序**：`preferences.md` → `narrative.md` → `day11.md`–`day15.md`

## 执行步骤

### Step 0：初始化

```bash
python bench_data_tools.py init --arc C
cat arc-C/uuid_registry.json
```

### Step 1：创建 eval 脚本

在 `benchmark/data/metaclaw-bench/eval/scripts/` 下创建 `check_metadata.py`。

脚本完整实现见 `data-spec/arc-C/narrative.md`。

### Step 2：逐天生成数据（串行）

对每天 N（11–15）顺序执行：

1. 读取 `data-spec/arc-C/dayN.md`，dispatch subagent
2. 验证：
   ```bash
   python bench_data_tools.py validate --day N
   python bench_data_tools.py preview --day N
   ```
3. 验证通过后追加 `all_tests.json` entry

### Step 3：整弧验证

```bash
python bench_data_tools.py validate --arc C
python bench_data_tools.py count --arc C
metaclaw-bench check benchmark/data/metaclaw-bench/all_tests.json
```

---

## Subagent Prompt 模板

```
你是一个数据制造 agent，负责生成 MetaClaw Evolution Benchmark arc-C 中 dayXX 的数据。

## 核心约束
- **所有数据内容（session 消息、workspace 文件、question/feedback）必须用英文**
- question 不得出现 "metadata"、"frontmatter"、"meta field" 等提示词
- workspace 预置文件可以没有 metadata，只有 agent 生成的输出才需要
- feedback.incorrect 必须给出完整正确的 metadata 格式示例
- P1、P2 规则同样适用

## 本天 spec
[粘贴 data-spec/arc-C/dayXX.md 全文]

## 偏好规则基准
[粘贴 data-spec/arc-C/narrative.md 全文]
[粘贴 data-spec/preferences.md P1、P2、P3 部分]
```

---

## all_tests.json entry 格式

```json
{
  "id": "day11",
  "desc": "Day 11 — 文档写作，P3 metadata 首次引入",
  "agent": "metaclaw_agent",
  "session": "day11_<uuid>",
  "eval": "day11",
  "arc": "C",
  "preference_tags": ["output_format", "file_naming", "field_completeness"]
}
```

---

## 设计质量 Checklist

每天完成后：
- [ ] question 不含 metadata 相关提示词
- [ ] feedback.incorrect 给出完整 metadata 格式（JSON meta 对象或 YAML frontmatter 示例）
- [ ] eval.command 正确引用 check_metadata.py 和对应文件路径
- [ ] P2 规则：输出文件命名遵循 YYYYMMDD_desc.ext

整弧完成后：
- [ ] Day 11 首次失败在 MD 文件缺 frontmatter
- [ ] Day 12 首次失败在 JSON 文件缺 meta 对象
- [ ] Day 13 首次失败在 Python 文件缺 Meta docstring 段
- [ ] Day 14 有 P1+P2+P3 联合验证的 round
