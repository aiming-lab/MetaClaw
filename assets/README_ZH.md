<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# 只需与你的 Agent 对话 —— 它会不断学习，持续进化。

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_完全异步-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_无需_GPU_集群-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Skill_进化-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_一键部署-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md)

<br/>

[概述](#-概述) • [快速开始](#-快速开始) • [CLI 命令](#️-cli-命令) • [配置说明](#️-配置说明) • [Skills](#-skills) • [RL 模式](#-进阶rl-模式) • [OPD 模式](#-进阶opd-模式) • [元学习调度器](#-进阶元学习调度器-v03) • [引用](#-引用)

</div>

---

<div align="center">

### 两条命令，搞定一切。
</div>

```bash
metaclaw setup              # 首次配置向导
metaclaw start              # 默认 madmax 模式：Skills + 定时 RL 训练
metaclaw start --mode rl    # 无调度器 RL（batch 满即训练）
metaclaw start --mode skills_only  # 仅 Skills，无 RL（无需 Tinker）
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 最新动态

- **[2026/03/13]** **v0.3** —— 持续元学习支持：慢速 RL 更新仅在睡眠时间、空闲期间或 Google Calendar 会议期间运行。新增 support/query 集分离，防止过时的奖励信号污染模型更新。
- **[2026/03/11]** **v0.2** —— 通过 `metaclaw` CLI 一键部署。Skill 默认开启，RL 现为可选。
- **[2026/03/09]** 正式发布 **MetaClaw** —— 只需与 Agent 对话，即可让其自动进化。**无需** GPU 部署，直接接入 **API** 即可。

---

## 🎥 演示

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 概述

**MetaClaw 是一个在真实场景中元学习并持续进化的 Agent。**
只需像平时一样与 Agent 对话 —— MetaClaw 将每一次实时对话转化为学习信号，让 Agent 在真实部署中持续进化，而非仅依赖离线训练。

在底层，它将你的模型封装为 OpenAI 兼容代理，通过 OpenClaw 拦截实时对话，在每轮对话中注入相关 Skill，并从积累的交互经验中元学习。每次会话结束后自动总结新 Skill；开启 RL 后，元学习调度器会将权重更新推迟到空闲窗口，确保活跃使用期间不受干扰。

无需 GPU 集群。MetaClaw 兼容任意 OpenAI 格式的 LLM API，并可选通过 [Tinker](https://www.thinkingmachines.ai/tinker/) 接入 **Kimi-K2.5** (1T MoE) 进行云端 LoRA 微调。

## 🤖 核心功能

### **一键部署**
使用 `metaclaw setup` 完成一次性配置，再执行 `metaclaw start` 即可自动启动代理、注入 Skill 并接入 OpenClaw。无需手动编写 Shell 脚本。

### **三种运行模式**

| 模式 | 默认 | 功能说明 |
|------|------|----------|
| `madmax` | ✅ | RL + 智能调度器。Skill 持续注入；RL 权重更新只在睡眠/空闲/会议窗口进行。 |
| `rl` | — | 无调度器 RL。batch 满后立即训练（v0.2 行为）。 |
| `skills_only` | — | 代理 → 你的 LLM API。注入 Skill，会话结束后自动总结。无需 GPU / Tinker。 |

### **Skill 注入**
每轮对话时，MetaClaw 检索最相关的 Skill 指令并注入 Agent 的 system prompt，无需重新训练即可立即提升行为表现。

### **Skill 自动总结**
每次对话结束后，你正在使用的同一个 LLM 会自动分析会话内容并提炼新 Skill。开启 RL 后，专属裁判模型会从失败的 episode 中提取 Skill。

### **无需 GPU 集群**
`skills_only` 模式只需网络连接。RL 训练完全在 Tinker 云端运行。

### **两种学习模式**
MetaClaw 同时支持：
- **RL（GRPO）**：从隐式反馈信号中学习
- **在线策略蒸馏（OPD）**：将更大的教师模型在线蒸馏到学生模型

在 OPD 模式下，学生模型正常生成回复，教师模型对相同回复提供每个 token 的对数概率。教师的 logprob 传入损失函数（如 `cispo`），引导学生学习教师的分布。教师模型需部署在 OpenAI 兼容的 `/v1/completions` 端点（如 vLLM、SGLang）。

### **完全异步设计**
推理服务、奖励建模与训练完全解耦。Agent 持续响应的同时，打分与优化在后台并行进行。

---

## 🚀 快速开始

### 1. 安装

```bash
pip install -e .                        # skills_only 模式（轻量）
pip install -e ".[rl]"                  # + RL 训练支持（torch、transformers、tinker）
pip install -e ".[evolve]"              # + 通过 OpenAI 兼容 LLM 进行 Skill 进化
pip install -e ".[scheduler]"           # + Google Calendar 调度器集成
pip install -e ".[rl,evolve,scheduler]" # 推荐：完整 RL + 调度器配置
```

### 2. 配置

```bash
metaclaw setup
```

交互式向导会引导你选择 LLM 提供商（Kimi、Qwen、MiniMax 或自定义），填写 API Key，并可选开启 RL 训练。

### 3. 启动

```bash
metaclaw start
```

就这些。MetaClaw 启动代理，自动配置 OpenClaw 并重启网关。打开 OpenClaw 开始对话 —— 每轮都会注入 Skill，对话结束后自动总结为新 Skill。

---

## 🛠️ CLI 命令

```
metaclaw setup                  # 首次交互式配置向导
metaclaw start                  # 启动 MetaClaw（默认 madmax 模式）
metaclaw start --mode rl        # 本次会话强制启用 RL 模式（无调度器）
metaclaw start --mode skills_only  # 本次会话强制仅 Skills 模式
metaclaw stop                   # 停止正在运行的 MetaClaw 实例
metaclaw status                 # 查看代理健康状态、运行模式与调度器状态
metaclaw config show            # 查看当前配置
metaclaw config KEY VALUE       # 设置配置项
```

**常用配置项：**

```bash
metaclaw config rl.enabled true           # 开启 RL 训练
metaclaw config rl.tinker_api_key sk-...  # 设置 Tinker Key
metaclaw config skills.auto_evolve false  # 关闭 Skill 自动总结
metaclaw config proxy.port 31000          # 修改代理端口
```

---

## ⚙️ 配置说明

配置文件位于 `~/.metaclaw/config.yaml`，由 `metaclaw setup` 自动生成。

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # 你的 Skill 库目录
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # 任务专属 Skill 上限（默认 10）
  auto_evolve: true         # 每次会话结束后自动总结 Skill

rl:
  enabled: false            # 设为 true 开启 RL 训练
  model: moonshotai/Kimi-K2.5
  tinker_api_key: ""
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # 可选：从检查点恢复训练
  evolver_api_base: ""      # 留空则复用 llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # 设为 true 开启 OPD（教师蒸馏）
  teacher_url: ""           # 教师模型 base URL（OpenAI 兼容 /v1/completions）
  teacher_model: ""         # 教师模型名称（如 Qwen/Qwen3-32B）
  teacher_api_key: ""       # 教师模型 API Key
  kl_penalty_coef: 1.0      # OPD 的 KL 惩罚系数

max_context_tokens: 20000   # 截断前的 prompt token 上限

scheduler:                  # v0.3：元学习调度器（madmax 模式下自动启用）
  enabled: false            # madmax 模式自动启用；rl 模式需手动设置
  sleep_start: "23:00"
  sleep_end: "07:00"
  idle_threshold_minutes: 30
  min_window_minutes: 15
  calendar:
    enabled: false
    credentials_path: ""
    token_path: ""
```

---

## 💪 Skills

Skill 是注入 Agent system prompt 的简短 Markdown 指令，存放在 Skill 目录（默认 `~/.metaclaw/skills/`），以独立的 `SKILL.md` 文件组织。

**Skill 自动总结**在每次对话结束后运行。配置的 LLM 自动分析发生了什么并生成新 Skill，无需人工整理 —— Skill 库随使用自动增长。

预加载内置 Skill 库（涵盖编码、安全、Agent 任务等 40+ 个 Skill）：

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 进阶：RL 模式

开启 RL 训练，从实时对话中持续微调模型：

```bash
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

RL 模式下：
- 每轮对话被 tokenize 并作为训练样本提交
- 裁判 LLM（PRM）异步为回复打分
- Tinker 云端执行 LoRA 微调，每累积 `batch_size` 个样本热更新权重
- 专属进化器 LLM 从失败的 episode 中提取新 Skill

**程序化 rollout**（无需 OpenClaw TUI）：将 `openclaw_env_data_dir` 设为包含 JSONL 任务文件的目录：

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 进阶：OPD 模式

在线策略蒸馏（OPD）允许在学生模型在线训练的同时，将更大的教师模型蒸馏进来。学生模型正常生成回复，教师模型对相同回复提供每个 token 的对数概率，KL 惩罚引导学生向教师分布靠拢。

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

教师模型需部署在 OpenAI 兼容的 `/v1/completions` 端点（如 vLLM、SGLang）。OPD 可与 PRM 打分同时使用，两者均异步运行。

参考 `examples/run_conversation_opd.py` 获取程序化示例，`scripts/run_openclaw_tinker_opd.sh` 提供现成的启动脚本。

---

## 🧠 进阶：元学习调度器 (v0.3)

RL 模式下，权重热更新会暂停 Agent 数分钟。调度器（madmax 模式默认启用）将 RL 更新推迟到用户不活跃的窗口，确保活跃使用期间不受干扰。

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# 可选：Google Calendar 集成
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

三种条件触发更新窗口（满足任一即可）：配置的睡眠时间、系统键盘空闲、Google Calendar 活跃事件。若用户在更新中途返回，部分 batch 会被保存并在下次窗口恢复。

每个 `ConversationSample` 带有 `skill_generation` 版本标签。当 Skill 进化增加 generation 时，RL buffer 被清空，仅使用进化后的样本进行梯度更新（MAML support/query 集分离）。

---

## 📚 引用

```bibtex
@misc{xia2026metaclaw,
  author       = {Xia, Peng and Chen, Jianwen and Yang, Xinyu and Tu, Haoqin and Han, Siwei and Qiu, Shi and Zheng, Zeyu and Xie, Cihang and Yao, Huaxiu},
  title        = {MetaClaw: Just Talk --- An Agent That Meta-Learns and Evolves in the Wild},
  year         = {2026},
  organization = {GitHub},
  url          = {https://github.com/aiming-lab/MetaClaw},
}
```

---

## 🙏 致谢

MetaClaw 基于以下开源项目构建：

- [OpenClaw](https://openclaw.ai) —— 核心 Agent 框架。
- [SkillRL](https://github.com/aiming-lab/SkillRL) —— 我们的 Skill 增强 RL 框架。
- [Tinker](https://www.thinkingmachines.ai/tinker/) —— 用于在线 RL 训练。
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) —— 我们 RL 设计的灵感来源。
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) —— 为我们的 Skill 库提供基础。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
