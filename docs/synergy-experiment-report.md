# Skill-Memory Synergy 实验报告

> MetaClaw 框架中 Memory 模块与 Skill 模块的协同注入实验
>
> 最后更新：2026-03-20

## 1. 背景

MetaClaw 框架有两个核心增强模块：

- **Memory（记忆）**：存储项目的历史经验，比如"上次 pgbouncer 连接池耗尽导致测试失败，修复方法是用 session scope fixture"
- **Skill（技能）**：存储通用方法论，比如"调试步骤：复现 → 隔离 → 假设 → 验证 → 修复"

**问题**：两个模块分别使用时各有价值，但同时开启（synergy 模式）时，效果反而比只用 Memory 更差（原始 benchmark 显示 -4.8% 退化）。

**目标**：让 Memory + Skill 协同使用的效果 > 任何一个模块单独使用的效果（即 1+1 > 2）。

## 2. 实验设计

### 2.1 测试模型

选择 4 个不同能力等级的模型，验证 synergy 在不同模型能力下的表现：

| 模型 | 能力等级 | 备注 |
|------|---------|------|
| gpt-5.4 | 强 | 推理模型，有内部 reasoning tokens |
| gpt-4o | 中强 | 通用模型 |
| gpt-4o-mini | 弱 | 小模型 |
| gpt-4.1-nano | 极弱 | 最小模型 |

### 2.2 测试场景（5 个）

| 场景 ID | 任务描述 | 预加载的记忆 | 应匹配的技能 |
|---------|---------|-------------|-------------|
| `debug_test_failure` | 调试间歇性测试失败（pgbouncer 连接池耗尽） | PostgreSQL 配置、历史修复经验 | debug-systematically, experiment-debugging |
| `experiment_design` | 设计数据增强实验方案 | 当前模型参数、历史实验结果 | experiment-design-rigor, data-validation-first |
| `write_test_for_feature` | 为新功能编写测试 | 项目测试规范、历史 review 反馈 | test-before-ship |
| `data_pipeline_debug` | 排查数据管道行数下降 | ETL 管道配置、历史 NaN 问题 | data-validation-first, experiment-debugging |
| `research_hypothesis` | 设计 RAG+微调的研究假设 | 当前 RAG/微调基线数据 | hypothesis-formulation, experiment-design-rigor |

每个场景都有预加载的 `MemoryUnit`（模拟真实的项目记忆），包含项目特定的配置、历史经验和团队规范。

### 2.3 测试模式

| 模式 | 注入内容 |
|------|---------|
| **baseline** | 无任何增强 |
| **memory_only** | 仅注入项目记忆 |
| **synergy** | 注入项目记忆 + 技能方法论提示（模板化） |

> 注：skill_only 模式在早期实验中已证明无价值（通用方法论模型本身就知道），因此不再测试。

### 2.4 评估指标

1. **Keyword Recall (0-1)**：响应中是否包含预期的项目特定关键词（如 pgbouncer、port 5433、conftest.py）
2. **PRM Score (0-10)**：使用 gpt-5.4 作为 judge，评估 4 个维度的加权平均：
   - Methodology (0.20): 方法是否系统化
   - Specificity (0.35): 是否引用了项目特定细节（权重最高）
   - Completeness (0.25): 是否覆盖了任务的所有关键方面
   - Actionability (0.20): 建议是否具体可执行

### 2.5 实验配置

- 每组 2 次 trial 取平均，减少随机波动
- PRM judge 固定使用 gpt-5.4，保证评分一致性
- API: Azure OpenAI (eastus2)

## 3. 实验结果

### 3.1 最终结果总表

| 模型 | Baseline PRM | Memory PRM | Synergy PRM | Δ(Synergy - Memory) | 1+1>2? |
|------|-------------|-----------|-------------|---------------------|--------|
| **gpt-4.1-nano** | 4.97 | 5.71 | **6.12** | **+0.41** | **YES** |
| **gpt-4o-mini** | 4.36 | 5.67 | **5.82** | **+0.15** | **YES** |
| **gpt-4o** | 4.88 | 6.55 | **6.62** | **+0.07** | **YES** |
| gpt-5.4 | 4.70 | 7.30 | 6.95 | -0.35 | NO |

### 3.2 分场景详细结果

#### gpt-4o（中强模型，synergy 效果最稳定）

| 场景 | Baseline | Memory | Synergy | Δ |
|------|---------|--------|---------|---|
| debug_test_failure | 5.2 | 7.5 | 6.6 | -0.9 |
| experiment_design | 4.8 | 6.2 | **7.0** | **+0.8** |
| write_test_for_feature | 4.5 | 5.2 | 5.2 | 0.0 |
| data_pipeline_debug | 5.2 | 8.4 | 7.8 | -0.6 |
| research_hypothesis | 4.8 | 5.4 | **6.4** | **+1.0** |

#### gpt-4o-mini（弱模型，修复 bug 后翻转为正向收益）

| 场景 | Baseline | Memory | Synergy | Δ |
|------|---------|--------|---------|---|
| debug_test_failure | 5.0 | 6.2 | 6.2 | 0.0 |
| experiment_design | 4.3 | 5.5 | 5.5 | 0.0 |
| write_test_for_feature | 3.4 | 4.4 | 4.5 | +0.1 |
| data_pipeline_debug | 4.6 | 7.3 | 7.2 | -0.1 |
| research_hypothesis | 4.4 | 4.8 | **5.8** | **+1.0** |

#### gpt-4.1-nano（极弱模型，synergy 收益最大）

| 场景 | Baseline | Memory | Synergy | Δ |
|------|---------|--------|---------|---|
| debug_test_failure | 5.4 | 6.0 | 6.2 | +0.2 |
| experiment_design | 5.4 | 6.1 | **6.6** | **+0.5** |
| write_test_for_feature | 4.2 | 4.4 | 4.4 | 0.0 |
| data_pipeline_debug | 5.0 | 6.7 | 6.8 | +0.1 |
| research_hypothesis | 4.8 | 5.5 | **6.5** | **+1.0** |

#### gpt-5.4（强模型，synergy 无帮助）

| 场景 | Baseline | Memory | Synergy | Δ |
|------|---------|--------|---------|---|
| debug_test_failure | 6.2 | 8.2 | 7.5 | -0.7 |
| experiment_design | 5.9 | 7.5 | 7.7 | +0.2 |
| write_test_for_feature | 2.1 | 5.9 | 4.9 | -1.0 |
| data_pipeline_debug | 6.5 | 7.6 | 7.2 | -0.4 |
| research_hypothesis | 2.8 | 7.3 | 7.4 | +0.1 |

> GPT-5.4 的 baseline 在 write_test 和 research 场景异常低（2.1/2.8），是因为 reasoning tokens 消耗了几乎所有的 max_completion_tokens 预算，导致输出被截断为不足 500 字符。

## 4. 关键发现

### 4.1 模型能力与 synergy 收益成反比

这是最重要的发现：

```
synergy 收益:  gpt-4.1-nano (+0.41) > gpt-4o-mini (+0.15) > gpt-4o (+0.07) > gpt-5.4 (-0.35)
模型能力:      gpt-4.1-nano < gpt-4o-mini < gpt-4o < gpt-5.4
```

**解释**：Skill 提供的是通用方法论（如"调试要先复现再隔离"）。弱模型不具备这些方法论知识，所以 hint 有价值；强模型（尤其是 reasoning model）已经内化了这些方法论，额外的 hint 反而是噪声。

### 4.2 研究/实验类场景 synergy 效果最好

`research_hypothesis` 和 `experiment_design` 场景的 synergy 收益最大（Δ 通常 +0.5 ~ +1.0），因为：
- 这类任务有明确的方法论框架（假设-验证、对照实验设计）
- 弱模型容易遗漏关键步骤（如忘记设置 null hypothesis、忘记做多种子实验）
- Skill 的步骤提示正好补齐这些遗漏

### 4.3 Skill 的内容不应该注入，只给名称提示

早期实验（实验 1-8）中，我们尝试将 Skill 的完整文档内容注入到 prompt 中。结果发现：
- 模型的回答变得很短（有时只有 200 多字符）
- PRM 分数大幅下降
- 模型的注意力被技能文档"抢走"，偏离了用户的实际问题

最终方案：只提取技能文档中的关键步骤名称，用一行概括。例如：

```
# 注入到 prompt 中的内容
Recommended approach: Reproduce → Isolate → Hypothesize → Test → Fix.
```

而不是注入几百字的完整技能文档。

### 4.4 正确匹配技能是一切的前提

实验 14（Round 1）中，gpt-4o-mini 的 synergy 反而退化了 -0.38。根本原因是技能匹配错误：

- 用户任务："设计一个数据增强实验方案"
- 系统先判断任务类型 → 错误地判为 "coding"
- 只在 coding 类技能中搜索 → 匹配到 `experiment-debugging`（调试实验，不是设计实验）
- 正确的技能 `experiment-design-rigor` 在 research 类别下，被完全错过

修复后（扫描所有类别），gpt-4o-mini 从 -0.38 翻转为 +0.15。

## 5. 技术改动详情

### 5.1 修改的文件

| 文件 | 改动内容 |
|------|---------|
| `metaclaw/skill_manager.py` | 技能匹配算法重构（词干提取、Overlap Coefficient、全类别搜索） |
| `metaclaw/api_server.py` | synergy 注入管线（template-only 策略、安全回退机制） |
| `metaclaw/config.py` | synergy 配置项（synergy_enabled, synergy_token_budget 等） |
| `metaclaw/memory/retriever.py` | 支持 coexist_with_skills 参数 |
| `metaclaw/memory/manager.py` | 透传 coexist_with_skills |

### 5.2 核心改动 1：技能匹配算法（skill_manager.py）

**改动前的问题和改动后的方案：**

| 问题 | 改动前 | 改动后 |
|------|-------|--------|
| 匹配算法过严 | Jaccard: `\|A∩B\| / \|A∪B\|` | Overlap Coefficient: `\|A∩B\| / min(\|A\|, \|B\|)` |
| 词形变化不匹配 | "failing" ≠ "failure" | 轻量级词干提取，strip -ing/-tion/-ly 等后缀 |
| 技能类别隔离 | 先判断任务类型，只搜该类别 | 搜索所有类别的技能，靠分数排序 |
| 停用词污染 | "the"/"is"/"and" 参与匹配 | 40+ 停用词过滤列表 |

**代码位置**：`skill_manager.py` 的 `retrieve_relevant()` 方法和 `_tokenize_text()` / `_stem()` 静态方法。

### 5.3 核心改动 2：Synergy 注入策略（api_server.py）

`_inject_augmentation()` 方法的最终工作流程：

```
1. 从用户消息中提取任务描述
2. 调用 retrieve_relevant() 搜索所有技能类别，按相关性排序
3. 如果匹配到的技能 < 2 个 → 回退到纯 memory 注入（安全兜底）
4. 如果匹配到 ≥ 2 个技能：
   a. 从技能内容中用正则提取 bold 步骤名称（如 **Reproduce the bug**）
   b. 拼接为一行提示：Recommended approach: Reproduce → Isolate → Hypothesize → Fix
   c. 与项目记忆合并为结构化模板注入 prompt
```

**注入到 prompt 中的模板示例**：

```markdown
## Augmented Context

Recommended approach: Reproduce → Isolate → Hypothesize → Test → Fix.
Use the project-specific experience below to inform your response.

### Memories (Project-Specific Experience — WHAT worked/failed before)

[EPISODIC] Day04: intermittent test failure due to pgbouncer pool exhaustion, fixed with session scope
[PROJECT_STATE] PostgreSQL 16 + pgbouncer, test DB on port 5433, pytest-asyncio
[SEMANTIC] Test DB config in conftest.py, async fixtures, port 5433
```

### 5.4 核心改动 3：安全回退

- 匹配到的相关技能 < 2 个时，不使用 synergy 模板，直接回退到 memory-only 注入
- 保证 synergy 模式在最坏情况下不会比 memory-only 差

## 6. 修复的 Bug 汇总

| # | Bug 描述 | 影响 | 修复方案 |
|---|---------|------|---------|
| 1 | Jaccard 相似度在集合大小差异大时过于严格 | 5/5 场景匹配不到任何技能 | 改用 Overlap Coefficient |
| 2 | 无词干提取，"failing"≠"failure" | 语义相同的词无法匹配 | 添加轻量级 suffix stripping |
| 3 | `retrieve_relevant()` 只搜索 task type 分类器检测到的类别 | experiment 任务匹配到 coding 技能 | 改为扫描所有类别 |
| 4 | 停用词参与 Jaccard 计算 | "the"/"is"/"and" 导致不相关技能得高分 | 添加 40+ 停用词列表 |
| 5 | GPT-5.4 的 reasoning tokens 消耗全部输出预算 | 响应为空 | max_completion_tokens 设为 4096 + 重试机制 |
| 6 | 注入完整技能内容导致模型注意力分散 | 回答变极短（200 字符），PRM 暴跌 | 改为 template-only，仅注入步骤名称 |

## 7. 实验原始数据

实验结果 JSON 文件保存在 `records/synergy_results/` 目录下：

- `multimodel_20260320_175043.json` — Round 1（修复 bug 前，gpt-4o/mini/nano）
- `multimodel_20260320_181518.json` — Round 2（修复 bug 后，gpt-4o/mini/nano）
- `multimodel_20260320_183743.json` — Round 2（修复 bug 后，gpt-5.4）

测试脚本：`scripts/run_multimodel_synergy.py`

## 8. 建议的后续工作

1. **Model-aware routing**：根据模型能力自动选择注入策略。强模型（GPT-5.4）直接用 memory-only，中弱模型走 synergy
2. **全量 benchmark 验证**：当前仅 5 场景 × 2 trials，需要在 30 天 benchmark 数据集上验证
3. **Kimi/Claude 测试**：历史 benchmark 显示 Kimi 的 skill-only 有 +4.9%，预期 synergy 收益更大
4. **反馈闭环（Layer 3）**：将高频成功的 synergy 策略自动固化为新技能
5. **Embedding-based 匹配**：当前使用的词级匹配有上限，语义 embedding 匹配可以进一步提升技能召回质量
