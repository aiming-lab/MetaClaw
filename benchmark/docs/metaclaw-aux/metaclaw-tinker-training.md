# MetaClaw Tinker 远程训练机制详解

> 基于 `/home/xkaiwen/workspace/metaclaw-test/metaclaw/` 源码分析
> 版本：v0.3（2026-03-11 发布）

---

## 1. 整体架构

MetaClaw 的核心思路：**将 OpenClaw 的对话流量拦截为训练数据，通过 Tinker 云端 LoRA 训练持续微调模型，无需本地 GPU**。

```
用户/任务 → OpenClaw → MetaClaw Proxy (FastAPI)
                           ↓
              Tinker SamplingClient.sample_async  ← 推理
                           ↓
              PRM Judge (异步评分)
                           ↓
              output_queue → MetaClawTrainer
                           ↓
              forward_backward → optim_step → save_weights  ← 训练
                           ↓
              Tinker SamplingClient (热替换权重)
```

关键文件：
- `metaclaw/trainer.py` — 训练主循环
- `metaclaw/api_server.py` — 代理服务器（数据收集）
- `metaclaw/data_formatter.py` — 数据格式转换（→ `tinker.Datum`）
- `metaclaw/config.py` — 所有可调参数
- `metaclaw/scheduler.py` — 慢更新调度器
- `metaclaw/prm_scorer.py` — 奖励打分器
- `metaclaw/skill_evolver.py` — 技能自动演化

---

## 2. Tinker 连接与 LoRA 训练初始化

**源码位置**：`trainer.py:99-153`（`setup()` 方法）

```python
service_client = tinker.ServiceClient()
self.training_client = await service_client.create_lora_training_client_async(
    base_model=self.config.model_name,   # 如 "moonshotai/Kimi-K2.5"
    rank=self.config.lora_rank,          # 默认 32
)
# 可选：从 checkpoint 恢复
if self.config.resume_from_ckpt:
    await self.training_client.load_state_async(self.config.resume_from_ckpt)

# 获取初始采样客户端（权重 = base weights）
self.sampling_client = await self.training_client.save_weights_and_get_sampling_client_async()
```

- Tinker API key 通过环境变量 `TINKER_API_KEY` 或 `config.yaml` 中 `rl.tinker_api_key` 传入。
- 支持的模型：默认配置为 `moonshotai/Kimi-K2.5`（~200B MoE）；示例中也使用 `Qwen/Qwen3-4B`、`Qwen/Qwen3-8B`。
- `renderer_name` 控制 tokenizer/chat template 格式，支持 `"qwen3"`、`"llama3"`、`"kimi"`、`"role_colon"`。

---

## 3. 训练方式：GRPO-style RL

**源码位置**：`trainer.py:236-309`（`_train_on_batch()` 方法）

### 3.1 训练时钟周期（Clock Cycle）

```
模块注释（trainer.py:1-15）：
1. Resume rollout worker → 从 API server 收集 batch
2. Pause rollout worker
3. 计算 advantages（GRPO 风格）
4. 转换为 tinker.Datum
5. forward_backward_async → optim_step_async（先后异步调用）
6. save_weights_and_get_sampling_client → 推送给 rollout worker
7. Resume rollout worker
8. 可选：技能演化
```

### 3.2 Advantage 计算（GRPO 风格）

**源码位置**：`data_formatter.py:217-230`

```python
def compute_advantages(batch):
    rewards = [s.reward for s in batch]
    mean_r = sum(rewards) / len(rewards)
    std_r = (sum((r - mean_r)**2 for r in rewards) / len(rewards)) ** 0.5
    return [(r - mean_r) / (std_r + 1e-8) for r in rewards]
```

在 batch 内做中心化归一化（center-and-scale）。

### 3.3 损失函数选项

通过 `config.loss_fn` 控制，传给 `training_client.forward_backward_async(data_D, loss_fn=...)`:

| loss_fn | 含义 |
|---------|------|
| `"importance_sampling"` | 默认；重要性采样 RL 损失 |
| `"ppo"` | PPO clip 损失 |
| `"cispo"` | OPD 模式推荐；结合 KL penalty |

### 3.4 Tinker Datum 结构

**源码位置**：`data_formatter.py:56-184`

```
tinker.Datum:
  model_input       = all_tokens[:-1]         （全序列去最后一个 token）
  loss_fn_inputs:
    target_tokens   = all_tokens[1:]           （左移一位）
    logprobs        = [0...0, resp_logprobs]   （prompt 位置 = 0）
    advantages      = [0...0, adv * loss_mask] （prompt 位置 = 0）
```

- OPD 模式额外将 KL penalty 加入 advantages：
  `resp_advantages[i] += -kl_penalty_coef * (log_p_student - log_p_teacher)`

### 3.5 优化器

```python
await self.training_client.optim_step_async(
    tinker.AdamParams(learning_rate=self.config.learning_rate)
)
```

使用 Adam，学习率由 `config.learning_rate`（默认 `1e-4`）控制。

### 3.6 权重热替换

每个 step 完成后：
- `save_weights_and_get_sampling_client_async(name="openclaw_lora")` —— 新权重推送给推理端
- 每 5 步保存一次 checkpoint：`save_state_async(name=f"step_{step_idx:04d}")`

超时由 `config.save_weights_timeout_s`（默认 200 秒）控制。

---

## 4. 数据来源

MetaClaw 支持两种数据收集模式：

### 4.1 被动代理模式（Passive Proxy）

- MetaClaw 作为 OpenAI-compatible 代理运行在 `localhost:30000`
- OpenClaw 配置为使用该代理
- 每次对话请求自动被拦截、tokenized、打分，成为训练样本
- 无需额外配置，OpenClaw 正常使用即可

### 4.2 程序化任务模式（Programmatic Rollout）

**源码位置**：`openclaw_env_rollout.py`、`trainer.py:441-460`

需要提供 JSONL 任务文件：

```
<openclaw_env_data_dir>/<split>.jsonl
每行格式：{"task_id": "...", "instruction": "..."}
```

Agent 循环自动驱动任务，工具调用格式为 Qwen3 XML（`<tool_call>...</tool_call>`）。

**控制参数**：
```python
openclaw_env_data_dir: str = ""      # 任务目录，非空时启用
openclaw_env_split: str = "train"    # jsonl 文件名前缀
openclaw_env_concurrency: int = 4    # 并行 episode 数
openclaw_env_max_steps: int = 15     # 每个 episode 最大轮数
```

示例任务文件见 `examples/train.jsonl`（真实 OpenClaw 操作任务）。

### 4.3 数据流

```
HTTP POST /v1/chat/completions (含 X-Session-Id, X-Turn-Type headers)
    ↓
api_server.py 拦截 → Tinker.sample_async 推理
    ↓
tokenize → PRMScorer 异步评分
    ↓
ConversationSample(prompt_tokens, response_tokens, logprobs, reward, ...)
    ↓
output_queue → MetaClawTrainer.drain_batch()
```

---

## 5. 上下文窗口长度控制

**源码位置**：`config.py:65-66`、`api_server.py:740-743`、`api_server.py:1070-1124`

### 5.1 最大上下文 Token 数

```python
max_context_tokens: int = 20000
# 注释：必须 <= Tinker max_seq_len - 响应 headroom
```

**实际计算**：
```python
# api_server.py:741
max_prompt = self.config.max_context_tokens - int(body.get("max_tokens") or 2048)
```
即：prompt 最多占用 `max_context_tokens - max_tokens`，默认约 17952 tokens。

### 5.2 截断策略

当 prompt 超过限制时，保留 system message + 最近的消息，丢弃最旧的非 system 消息：

```
[system] + [最近 N 条消息]  ← 始终保留 system
                              ← 保留最近消息，直到 token 预算耗尽
                              ← 至少保留一条 user 消息
```

**config.yaml 对应设置**：
```yaml
max_context_tokens: 20000    # 可调整
```

**注意**：Tinker 端也有 `max_seq_len` 限制。如果要支持更长上下文，需要确认 Tinker 服务端配置支持（目前 MetaClaw 未直接暴露该参数）。

---

## 6. OPD 模式（在线策略蒸馏）

**源码位置**：`examples/run_conversation_opd.py`、`scripts/run_openclaw_tinker_opd.sh`

```python
use_opd=True,
loss_fn="cispo",
teacher_url="http://localhost:8082/v1",   # teacher OpenAI-compatible endpoint
teacher_model="Qwen/Qwen3-32B",
kl_penalty_coef=1.0,
```

- 学生模型（LoRA）正常 rollout 生成响应
- 教师模型对同一响应计算 per-token logprobs
- Loss 加入反向 KL penalty：`-coef * KL[student||teacher]`
- 教师模型需要部署在 `/v1/completions` 端点（vLLM/SGLang）

---

## 7. 奖励模型（PRM）

**源码位置**：`prm_scorer.py`

- 使用任意 OpenAI-compatible `/v1/chat/completions` API 作为 judge
- 评分标准：`+1`（有帮助）/ `0`（不确定）/ `-1`（无帮助）
- 多数投票：并发查询 `prm_m`（默认 3）次，取多数
- 评分提示：比较 instruction vs. response，判断是否完成任务

支持 **AWS Bedrock** 作为 PRM provider（通过 `prm_provider="bedrock"`）。

---

## 8. 技能演化机制（Skill Evolution）

### 8.1 触发条件

当 batch success rate（reward > 0 的比例）< `skill_update_threshold`（默认 0.4）时触发。

### 8.2 MAML 支持/查询集分离

v0.3 引入关键修复：技能演化后，立即清空 RL sample buffer，避免旧 sample 污染梯度更新：

```
session 1,2,3 → 技能演化 → 写入新 skill 文件
                              ↓
                  清空旧 sample（support set 不再进入 outer loop）
                              ↓
session 4,5,6 → 新样本（query set）→ RL 梯度更新
```

### 8.3 技能存储格式

每个技能是独立的 `SKILL.md` 文件，位于 `skills_dir/` 目录下。

---

## 9. 调度器（Meta-Learning Scheduler）

**源码位置**：`scheduler.py`，v0.3 新增

```
IDLE_WAIT → (sleep/idle/calendar) → WINDOW_OPEN
WINDOW_OPEN → (trainer acks)     → UPDATING
UPDATING → (user active)          → PAUSING
PAUSING → (trainer done)          → IDLE_WAIT
```

三种触发条件（任意满足即可）：
1. **Sleep hours**：本地时间在 `sleep_start`~`sleep_end` 之间
2. **System idle**：键盘不活跃超过 `idle_threshold_minutes` 分钟
3. **Google Calendar**：当前有日历事件（用户在会议中）

调度器每 60 秒检查一次（`_CHECK_INTERVAL_SECONDS = 60`）。

---

## 10. 完整可调参数清单

所有参数定义于 `metaclaw/config.py`，用户配置文件为 `~/.metaclaw/config.yaml`。

### 10.1 模型与 LoRA

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `model_name` | `"Qwen/Qwen3-4B"` | Tinker 训练的 base model |
| `lora_rank` | `32` | LoRA rank |
| `renderer_name` | `"qwen3"` | chat template 格式 (`qwen3`/`llama3`/`kimi`/`role_colon`) |
| `resume_from_ckpt` | `""` | Tinker checkpoint 路径，如 `tinker://.../weights/step_0003` |

### 10.2 训练超参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `learning_rate` | `1e-4` | Adam 学习率 |
| `batch_size` | `4` | 每步训练的 ConversationSample 数 |
| `max_steps` | `1000` | 最大训练步数 |
| `loss_fn` | `"importance_sampling"` | 损失函数：`ppo` / `importance_sampling` / `cispo` |
| `save_weights_timeout_s` | `200.0` | 权重保存超时（秒） |

### 10.3 上下文窗口

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_context_tokens` | `20000` | prompt token 上限（需 <= Tinker max_seq_len - 响应预留） |

### 10.4 奖励模型（PRM）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `use_prm` | `True` | 是否启用 PRM 评分 |
| `prm_provider` | `"openai"` | `"openai"` 或 `"bedrock"` |
| `prm_url` | `"https://api.openai.com/v1"` | Judge API base URL |
| `prm_model` | `"gpt-5.2"` | Judge 模型名 |
| `prm_api_key` | `""` | Judge API key |
| `prm_m` | `3` | 多数投票次数 |
| `prm_temperature` | `0.6` | Judge 采样温度 |
| `prm_max_new_tokens` | `1024` | Judge 最大生成 tokens |

### 10.5 OPD 模式

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `use_opd` | `False` | 是否启用在线策略蒸馏 |
| `teacher_url` | `""` | 教师模型 OpenAI-compatible endpoint |
| `teacher_model` | `""` | 教师模型名 |
| `teacher_api_key` | `""` | 教师模型 API key |
| `kl_penalty_coef` | `1.0` | KL penalty 系数 |

### 10.6 技能系统

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `use_skills` | `False` | 是否注入技能到 system prompt |
| `skills_dir` | `"memory_data/skills"` | 技能文件目录 |
| `retrieval_mode` | `"template"` | 检索模式：`template`（关键词）或 `embedding` |
| `embedding_model_path` | `"Qwen/Qwen3-Embedding-0.6B"` | Embedding 模型路径 |
| `skill_top_k` | `6` | 每次注入的通用技能数 |
| `task_specific_top_k` | `10` | 任务特定技能上限 |
| `enable_skill_evolution` | `False` | 是否自动演化技能 |
| `skill_evolution_every_n_turns` | `10` | 每 N 轮对话触发一次技能演化 |
| `skill_update_threshold` | `0.4` | 成功率低于此值时触发技能演化 |
| `max_new_skills` | `3` | 每次演化最多生成的新技能数 |

### 10.7 数据收集（程序化 Rollout）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `openclaw_env_data_dir` | `""` | 任务 JSONL 目录；空=被动代理模式 |
| `openclaw_env_split` | `"train"` | JSONL 文件名前缀 |
| `openclaw_env_concurrency` | `4` | 并行 episode 数 |
| `openclaw_env_max_steps` | `15` | 每 episode 最大步数 |

### 10.8 调度器

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scheduler_enabled` | `True` | auto 模式自动开启 |
| `scheduler_sleep_start` | `"23:00"` | 睡眠窗口开始时间（HH:MM 本地时间）|
| `scheduler_sleep_end` | `"07:00"` | 睡眠窗口结束时间 |
| `scheduler_idle_threshold_minutes` | `30` | 空闲多少分钟后触发训练 |
| `scheduler_min_window_minutes` | `15` | 最小有效窗口时长（分钟） |
| `scheduler_calendar_enabled` | `False` | 是否使用 Google Calendar 检测 |

### 10.9 代理服务器

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `proxy_port` | `30000` | 代理监听端口 |
| `proxy_host` | `"0.0.0.0"` | 代理监听地址 |
| `api_key` | `""` | 代理 Bearer token（可选鉴权）|
| `record_enabled` | `True` | 是否记录对话到 `records/` |
| `record_dir` | `"records/"` | 对话记录目录 |

### 10.10 运行模式

| `mode` | 说明 |
|--------|------|
| `"auto"` | RL + 调度器（默认，训练在空闲/睡眠窗口执行）|
| `"rl"` | RL 无调度器（batch 满即训练）|
| `"skills_only"` | 仅技能注入，无 Tinker/RL |

---

## 11. 环境变量

| 变量 | 用途 |
|------|------|
| `TINKER_API_KEY` | Tinker 服务 API key |
| `OPENAI_API_KEY` | PRM judge / SkillEvolver API key |
| `OPENAI_BASE_URL` | SkillEvolver API base URL |
| `SKILL_EVOLVER_MODEL` | SkillEvolver 模型名（默认 `gpt-5.2`）|
| `WANDB_DISABLED` | 设为 `"true"` 禁用 W&B 日志 |
| `WANDB_PROJECT` | W&B 项目名（默认 `"metaclaw"`）|
| `WANDB_RUN_NAME` | W&B run 名称 |
| `TEACHER_URL` | OPD 教师模型 URL（脚本用）|
| `TEACHER_MODEL` | OPD 教师模型名（脚本用）|

---

## 12. 关键限制与注意事项

1. **上下文窗口上限受 Tinker 约束**：`max_context_tokens` 必须 <= Tinker 服务端 `max_seq_len - 响应 token 预留`。MetaClaw 不直接暴露 Tinker 的 `max_seq_len` 设置。

2. **batch_size 较小（默认 4）**：对于 GRPO 这类依赖 group normalization 的方法，建议适当增大（示例 `run_conversation_rl.py` 用了 `batch_size=8`，OPD 示例用了 `32`）。

3. **save_weights 阻塞**：`save_weights_and_get_sampling_client` 会暂停服务数分钟，这是 auto 模式引入调度器的根本原因。

4. **技能演化 LLM**：需要独立的 LLM（evolver），默认配置与 PRM judge 使用同一 API，可通过 `evolver_api_base`/`evolver_model_id` 分离。

5. **Tinker 仅支持特定模型**：`model_name` 必须是 Tinker 云平台支持的模型，目前主要为 Kimi-K2.5 和 Qwen3 系列。
