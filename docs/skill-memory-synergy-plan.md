# Skill-Memory 协同改进方案

## 1. 问题定义

### 1.1 现象

Skill 和 Memory 模块各自单独开启时均能显著提升 agent 性能，但同时开启后性能反而低于仅开 Memory：

| 配置         | 模型    | 准确率    | passed | 与 baseline 对比                |
| ------------ | ------- | --------- | ------ | ------------------------------- |
| Baseline     | GPT-5.2 | 46.0%     | —      | —                               |
| Memory-only  | GPT-5.2 | **53.3%** | 0.211  | +7.3%                           |
| Memory+Skill | GPT-5.2 | 48.5%     | 0.162  | +2.5%（但比 Memory-only -4.8%） |
| Baseline     | Kimi    | 40.2%     | —      | —                               |
| Skills-only  | Kimi    | 45.1%     | 0.142  | +4.9%                           |
| Memory-only  | Kimi    | 48.0%     | —      | +7.8%                           |

逐任务对比 Memory-only vs Memory+Skill（GPT-5.2），退化最严重的任务：

| 任务  | Memory-only | Memory+Skill | 差值       |
| ----- | ----------- | ------------ | ---------- |
| day19 | 90.9%       | 51.2%        | **-39.7%** |
| day03 | 58.3%       | 40.3%        | -18.0%     |
| day06 | 66.7%       | 48.3%        | -18.4%     |
| day20 | 83.3%       | 66.4%        | -16.9%     |
| day16 | 68.3%       | 58.3%        | -10.0%     |

**规律**：Memory 效果越好的任务，加入 Skill 后退化越严重。说明 Skill 注入正在稀释/干扰 Memory 的强信号。

### 1.2 根因分析

通过阅读 `api_server.py:1114-1119` 的注入逻辑，定位到以下根因：

#### 根因 1：Token 预算独立，无全局管控

Memory 使用 `max_injected_tokens=800`，而 Skill **没有 token 预算限制**——直接注入所有检索到的 skill（通常 10+ 个文档），token 占用远大于 Memory。两者合计可能消耗 2000+ tokens，挤占宝贵的对话上下文空间。

#### 根因 2：检索完全独立，无交叉感知

```python
# api_server.py:1114-1119 — 当前实现
if turn_type == "main":
    if self.memory_manager:
        messages = await self._inject_memory(messages, scope_id=...)
    if self.skill_manager:
        messages = self._inject_skills(messages)
```

两个模块各自以 `task_desc`（最后一条 user message）为 query 独立检索，互不知道对方会注入什么内容。结果：
- Memory 的 `PROCEDURAL_OBSERVATION` 类型与 Skill 高度重叠（都是"应该怎么做"）
- 无法实现互补选择（Memory 提供具体经验 + Skill 提供通用方法论）

#### 根因 3：Prompt 中角色定位模糊

Memory 渲染为 `## Relevant Long-Term Memory`，Skill 渲染为 `## Active Skills`，两段文字紧邻拼接到 system message 中。LLM 缺乏明确指导来区分这两类信息的定位和优先级，容易被冗余甚至矛盾的信息困惑。

#### 根因 4：无反馈闭环

- Skill Evolution 分析失败 sample 时不参考 Memory
- Memory 的 reinforcement_score 不考虑当时哪些 Skill 在场
- 两个模块无法从彼此的成功/失败中学习

## 2. 设计原则

1. **非侵入性**：Skill 或 Memory 各自单独开启时的行为完全不变，协同逻辑仅在两者同时启用时激活
2. **渐进式**：分层实施，每层独立可测，先做最小改动验证效果
3. **冲突处理**：当两者内容冲突时，在 prompt 中引导 agent 自行根据具体情况判断，但通过检索策略减少冲突发生

## 3. 改进方案（四层）

### Layer 1：注入层协调（最小改动，预期最大收益）

**目标**：消除 token 挤占、内容冗余、角色模糊三个直接问题。

#### 1.1 共享 Token 预算

在 `config.py` 新增配置：

```python
# 仅在 skill + memory 同时启用时生效
augmentation_token_budget: int = 1200   # 两个模块合计的 token 上限
skill_token_ratio: float = 0.35         # skill 占比（memory 信号更强，分配更多预算）
```

在 `api_server.py` 中新增 `_inject_augmentation()` 方法，替换现有的分别注入逻辑：

```python
if turn_type == "main":
    if self.memory_manager and self.skill_manager:
        # 协同模式：共享预算，统一注入
        messages = await self._inject_augmentation(messages, scope_id=effective_memory_scope)
    elif self.memory_manager:
        messages = await self._inject_memory(messages, scope_id=effective_memory_scope)
    elif self.skill_manager:
        messages = self._inject_skills(messages)
```

预算分配策略：
- Skill 固定获得 `budget * skill_token_ratio` tokens（约 420 tokens）
- Memory 获得剩余部分（约 780 tokens）
- Skill 侧需在 `format_for_conversation()` 中增加 truncation 逻辑，优先保留 top 相关 skill

**改动文件**：`config.py`、`api_server.py`、`skill_manager.py`（增加 token-aware format）

#### 1.2 语义去重

在 `_inject_augmentation()` 中，检索到 skills 和 memories 后，进行语义去重：

```python
async def _inject_augmentation(self, messages, scope_id):
    memories = await self._retrieve_memories(task_desc, scope_id)
    skills = self._retrieve_skills(task_desc)

    # 语义去重：复用 memory retriever 的 embedder
    if memories and skills:
        memories = self._dedup_against_skills(memories, skills, threshold=0.75)

    # 分配预算、格式化、注入
    ...
```

去重方向：当一条 memory 与某个 skill 语义相似度 > 阈值时，丢弃该 memory（因为 skill 更结构化、更 actionable）。特别针对 `PROCEDURAL_OBSERVATION` 类型的 memory。

**改动文件**：`api_server.py`（新增 `_dedup_against_skills` 方法）

#### 1.3 角色区分 Prompt Wrapper

替换原来的两段独立 markdown，改用统一结构并加入角色引导：

```markdown
## Augmented Context

Below are two complementary sources of guidance. Use both to inform your response:

### Skills (General Strategies — HOW to approach this type of task)
These are proven patterns and best practices applicable to similar tasks.
[truncated skill content]

### Memories (Project-Specific Experience — WHAT worked/failed before)
These are concrete observations from past sessions in this project.
When a memory provides project-specific context that refines or overrides
a general skill, consider the memory's specificity.
[truncated memory content]
```

**改动文件**：`api_server.py`（修改 format 逻辑）

#### 预期效果

- 消除 token 挤占：从无限制降到 1200 tokens 上限
- 消除冗余：去重可减少 20-40% 的重复内容
- 清晰定位：LLM 知道何时用 skill（通用方法论）何时用 memory（具体经验）

---

### Layer 2：跨模块感知检索

**目标**：让检索阶段就实现互补而非冗余。

#### 2.1 Memory-Aware Skill 检索

检索 memory 后，将其 topics/entities 传给 skill 检索，让 skill 选择互补内容：

```python
# 先检索 memory
memories = await self._retrieve_memories(task_desc, scope_id)
memory_topics = extract_topics(memories)  # 提取 memory 覆盖的主题

# 再检索 skill，带上 memory 已覆盖的主题
skills = self.skill_manager.retrieve(
    task_desc,
    top_k=self.config.skill_top_k,
    covered_topics=memory_topics,  # 新参数
)
```

`skill_manager.retrieve()` 在 embedding 模式下：对与 memory topics 高度重叠的 skill 施加 penalty；在 template 模式下：降低已覆盖类别的 skill 优先级。

**改动文件**：`skill_manager.py`（`retrieve` 方法增加 `covered_topics` 参数）

#### 2.2 Memory 类型过滤

当 skill 同时启用时，memory 检索自动降低 `PROCEDURAL_OBSERVATION` 类型的权重（因为 skill 已覆盖"怎么做"的信息），提升 `EPISODIC`、`PROJECT_STATE`、`WORKING_SUMMARY` 类型的权重。

```python
def retrieve_for_prompt(self, task_description, scope_id=None, coexist_with_skills=False):
    query = MemoryQuery(
        scope_id=effective_scope,
        query_text=task_description,
        top_k=self.policy.max_injected_units,
        max_tokens=self.policy.max_injected_tokens,
    )
    if coexist_with_skills:
        # 降低与 skill 重叠度高的类型权重
        query.type_boosts = {
            "procedural_observation": -0.3,
            "episodic": 0.1,
            "working_summary": 0.15,
            "project_state": 0.1,
        }
    hits = self.retriever.retrieve(query)
    ...
```

**改动文件**：`memory/manager.py`、`memory/retriever.py`（支持 `type_boosts`）

#### 预期效果

- Skill 和 Memory 在检索阶段就互补：skill 提供方法论，memory 提供具体经验
- 减少 `PROCEDURAL_OBSERVATION` 与 skill 的冲突
- 特别有利于 Memory 效果好的任务（如 day19）——memory 的强信号不会被冗余 skill 稀释

---

### Layer 3：反馈闭环

**目标**：让两个模块从彼此的成功/失败中学习。

#### 3.1 记录协同上下文

在 sample 提交时，记录当时活跃的 skill 和 memory：

```python
# api_server.py 的 sample 提交逻辑中
sample.active_skills = [s["name"] for s in injected_skills]
sample.active_memory_ids = [m.memory_id for m in injected_memories]
```

扩展 `ConversationSample` 增加这两个字段。

**改动文件**：`data_formatter.py`（扩展 dataclass）、`api_server.py`（记录时传入）

#### 3.2 Skill-Conditioned Memory Reinforcement

Session 结束后，根据 PRM reward 调整 memory 的 reinforcement_score，但考虑当时有哪些 skill 在场：

- 成功 session + skill 和 memory 共同在场 → memory reinforcement +0.05（验证了协同有效）
- 失败 session + memory 与某 skill 内容冲突 → 该 memory reinforcement -0.03（可能冲突导致失败）

**改动文件**：`memory/manager.py`（新增 `adjust_reinforcement_with_skills` 方法）

#### 3.3 Memory-Informed Skill Evolution

`skill_evolver.py` 在分析失败 sample 生成新 skill 时，同时传入相关 memory 作为上下文：

```python
# skill_evolver.py 的 evolve 方法
async def evolve(self, failed_samples, current_skills, relevant_memories=None):
    prompt = self._build_analysis_prompt(
        failed_samples, current_skills,
        memories=relevant_memories,  # 新增
    )
```

这让 Evolver 生成的 skill 能吸收项目特定经验，生成更贴合实际的 skill 而非泛化的通用规则。

**改动文件**：`skill_evolver.py`（`evolve` 和 `_build_analysis_prompt` 增加 memories 参数）

#### 3.4 高频 Procedural Observation 自动晋升为 Skill

当一条 `PROCEDURAL_OBSERVATION` 类型的 memory 被反复检索（access_count >= 5）且 reinforcement_score 高，自动调用 `skill_evolver` 将其整理为正式 skill，并从 memory pool 中标记为 "promoted"。

这形成闭环：observation → 验证有效 → 晋升为 skill → memory pool 减少冗余。

**改动文件**：`memory/manager.py`（晋升检测）、`skill_evolver.py`（promotion 接口）

---

### Layer 4：动态预算自适应

**目标**：根据上下文动态调整 skill/memory 的 token 分配。

#### 4.1 Turn-Aware 预算调整

```python
def _compute_skill_ratio(self, turn_num: int, session_history: list) -> float:
    base_ratio = self.config.skill_token_ratio  # 0.35

    if turn_num <= 2:
        # 早期 turn：agent 刚接触任务，更需要方法论指导
        return min(base_ratio + 0.15, 0.6)
    elif turn_num >= 5:
        # 后期 turn：agent 已了解任务，更需要具体经验
        return max(base_ratio - 0.15, 0.15)

    return base_ratio
```

#### 4.2 RL-Optimized 注入策略（可选）

将 `augmentation_token_budget`、`skill_token_ratio`、`dedup_threshold` 等参数加入 RL 的 meta-parameter 优化空间。利用现有的 `MemoryPolicyOptimizer` 模式，基于 PRM reward 信号自动搜索最优配置。

**改动文件**：`config.py`、`api_server.py`、`trainer.py`（可选）

---

## 4. 实施路线图

```
Layer 1（注入层协调）    ─────────────────
  ├── 1.1 共享 token 预算     → config.py, api_server.py, skill_manager.py
  ├── 1.2 语义去重             → api_server.py
  └── 1.3 角色区分 wrapper     → api_server.py
  │
  ▼ 评测验证（与 memory-only 对比，目标：≥53.3%）
  │
Layer 2（跨模块感知检索）─────────────────
  ├── 2.1 Memory-aware skill 检索  → skill_manager.py
  └── 2.2 Memory 类型过滤          → memory/manager.py, memory/retriever.py
  │
  ▼ 评测验证（目标：>55%，超过两者各自单独使用）
  │
Layer 3（反馈闭环）      ─────────────────
  ├── 3.1 协同上下文记录       → data_formatter.py, api_server.py
  ├── 3.2 Skill-conditioned reinforcement → memory/manager.py
  ├── 3.3 Memory-informed evolution       → skill_evolver.py
  └── 3.4 Observation → Skill 晋升       → memory/manager.py, skill_evolver.py
  │
  ▼ 评测验证（目标：长期运行后持续改善）
  │
Layer 4（动态自适应）    ─────────────────（根据前三层结果决定是否实施）
  ├── 4.1 Turn-aware 预算调整  → api_server.py
  └── 4.2 RL-optimized 策略    → trainer.py
```

## 5. 关键指标

| 指标                            | 含义                       | 目标                        |
| ------------------------------- | -------------------------- | --------------------------- |
| Accuracy（同开 vs Memory-only） | 协同是否不低于最优单模块   | ≥ 53.3%（Memory-only 水平） |
| Accuracy（同开 vs Baseline）    | 协同的绝对提升             | > 55%（超过任一单模块）     |
| 注入 token 数                   | 上下文占用                 | ≤ 1200 tokens（当前无限制） |
| 语义去重率                      | 冗余消除比例               | 20-40% 的 memory 被合理去重 |
| 逐任务退化率                    | 不应有任务因协同而大幅退化 | 无任务退化超过 5%           |

## 6. 改动文件清单

| 文件                           | Layer 1                  | Layer 2                 | Layer 3          | Layer 4    |
| ------------------------------ | ------------------------ | ----------------------- | ---------------- | ---------- |
| `metaclaw/config.py`           | ✓ 新增配置字段           |                         |                  | ✓          |
| `metaclaw/api_server.py`       | ✓ `_inject_augmentation` | ✓ 检索顺序调整          | ✓ 记录协同上下文 | ✓ 动态比例 |
| `metaclaw/skill_manager.py`    | ✓ token-aware format     | ✓ `covered_topics`      |                  |            |
| `metaclaw/memory/manager.py`   |                          | ✓ `coexist_with_skills` | ✓ reinforcement  |            |
| `metaclaw/memory/retriever.py` |                          | ✓ `type_boosts`         |                  |            |
| `metaclaw/data_formatter.py`   |                          |                         | ✓ 扩展 fields    |            |
| `metaclaw/skill_evolver.py`    |                          |                         | ✓ memories 参数  |            |
| `metaclaw/trainer.py`          |                          |                         |                  | ✓ 可选     |
