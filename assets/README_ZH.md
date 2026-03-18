<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# 只需与你的 Agent 对话,它会不断学习,持续进化。

<p>受大脑学习方式启发。让你的 🦞 在真实对话中持续元学习与进化。无需 GPU。支持 Kimi、Qwen、Claude、MiniMax 等。</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_完全异步-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_无需_GPU_集群-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Skill_进化-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_一键部署-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇦🇪 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[概述](#-概述) • [快速开始](#-快速开始) • [配置说明](#️-配置说明) • [Skills 模式](#-skills-模式) • [RL 模式](#-rl-模式) • [MadMax 模式](#-madmax-模式默认) • [引用](#-引用)

</div>

---

<div align="center">

### 两条命令,搞定一切。
</div>

```bash
metaclaw setup              # 首次配置向导
metaclaw start              # 默认 madmax 模式：Skills + 定时 RL 训练
metaclaw start --daemon     # 后台运行，日志 -> ~/.metaclaw/metaclaw.log
metaclaw start --daemon --log-file /tmp/metaclaw.log  # 自定义日志路径
metaclaw start --mode rl    # 无调度器 RL（batch 满即训练）
metaclaw start --mode skills_only  # 仅 Skills，无 RL（无需 Tinker）
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 最新动态

- **[2026/03/16]** **v0.3.2** 多 Claw 支持：现已支持 IronClaw、PicoClaw、ZeroClaw、CoPaw、NanoClaw 和 NemoClaw，与 OpenClaw 并列。NanoClaw 通过新增的 `/v1/messages` Anthropic 兼容端点接入；NemoClaw 通过 OpenShell 推理路由接入。新增 OpenRouter 作为受支持的 LLM 平台。
- **[2026/03/13]** **v0.3.1** MinT 后端支持：RL 训练现同时支持 Tinker 和 MinT。通过 `rl.backend`（auto/tinker/mint）配置。
- **[2026/03/13]** **v0.3** 持续元学习支持：慢速 RL 更新仅在睡眠时间、空闲期间或 Google Calendar 会议期间运行。新增 support/query 集分离,防止过时的奖励信号污染模型更新。
- **[2026/03/11]** **v0.2** 通过 `metaclaw` CLI 一键部署。Skill 默认开启,RL 现为可选。
- **[2026/03/09]** 正式发布 **MetaClaw**,只需与 Agent 对话,即可让其自动进化。**无需** GPU 部署,直接接入 **API** 即可。

---

## 🎥 演示

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 概述

**MetaClaw 是一个在真实场景中元学习并持续进化的 Agent。**
只需像平时一样与 Agent 对话, MetaClaw 将每一次实时对话转化为学习信号,让 Agent 在真实部署中持续进化,而非仅依赖离线训练。

在底层,它将你的模型封装为 OpenAI 兼容代理（对 NanoClaw 等 Anthropic 原生 Agent 还提供 `/v1/messages` 兼容端点），通过 OpenClaw、NanoClaw、NemoClaw 等支持的 Agent 拦截实时对话,在每轮对话中注入相关 Skill,并从积累的交互经验中元学习。每次会话结束后自动总结新 Skill；开启 RL 后,元学习调度器会将权重更新推迟到空闲窗口,确保活跃使用期间不受干扰。

无需 GPU 集群。MetaClaw 兼容任意 OpenAI 格式的 LLM API,并通过 Tinker 兼容后端进行云端 LoRA 微调。[Tinker](https://www.thinkingmachines.ai/tinker/) 是默认参考路径；如果需要,也可以通过单独安装的兼容包接入 MinT。

## 🤖 核心功能

### **一键部署**
使用 `metaclaw setup` 完成一次性配置,再执行 `metaclaw start` 即可自动启动代理、注入 Skill 并接入 OpenClaw。无需手动编写 Shell 脚本。

### **三种运行模式**

| 模式 | 默认 | 功能说明 |
|------|------|----------|
| `skills_only` | | 代理你的 LLM API。注入 Skill,会话结束后自动总结。无需 GPU / Tinker。 |
| `rl` | | Skills + RL 训练（GRPO）。batch 满后立即训练。可选 OPD 进行教师蒸馏。 |
| `madmax` | ✅ | Skills + RL + 智能调度器。RL 权重更新只在睡眠/空闲/会议窗口进行。 |

### **完全异步设计**
推理服务、奖励建模与训练完全解耦。Agent 持续响应的同时,打分与优化在后台并行进行。

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

如果你要使用 `rl.backend=mint`,请在同一环境里额外安装 MinT 兼容包,例如 [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit)。MetaClaw 不会把这个依赖放进默认安装中,这样 RL 用户可以明确选择 Tinker 或 MinT。

### 2. 配置

```bash
metaclaw setup
```

交互式向导会引导你选择 LLM 提供商（Kimi、Qwen、MiniMax 或自定义）,填写 API Key,并可选开启 RL 训练。

MetaClaw 的 RL 路径可以显式切换 `tinker` 和 `mint`。推荐默认值是 `auto`；当环境里安装了 MinT 兼容包时,它仍然可以根据 Mint 风格的凭证或 base URL 自动识别 MinT。

**Tinker**（默认）:

```bash
metaclaw config rl.backend tinker
metaclaw config rl.api_key sk-...
metaclaw config rl.model moonshotai/Kimi-K2.5
```

**MinT**:

```bash
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-mint-...
metaclaw config rl.base_url https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

兼容旧配置的 `rl.tinker_api_key` 和 `rl.tinker_base_url` 仍然可以继续使用。

### 3. 启动

```bash
metaclaw start
```

就这些。MetaClaw 启动代理,自动配置 OpenClaw 并重启网关。打开 OpenClaw 开始对话,每轮都会注入 Skill,对话结束后自动总结为新 Skill。

---

## ⚙️ 配置说明

配置文件位于 `~/.metaclaw/config.yaml`,由 `metaclaw setup` 自动生成。

**CLI 命令：**

```
metaclaw setup                  # 首次交互式配置向导
metaclaw start                  # 启动 MetaClaw（默认 madmax 模式）
metaclaw start --daemon         # 在后台启动 MetaClaw
metaclaw start --daemon --log-file /tmp/metaclaw.log  # 自定义日志路径
metaclaw start --mode rl        # 本次会话强制启用 RL 模式（无调度器）
metaclaw start --mode skills_only  # 本次会话强制仅 Skills 模式
metaclaw stop                   # 停止正在运行的 MetaClaw 实例
metaclaw status                 # 查看代理健康状态、运行模式与调度器状态
metaclaw config show            # 查看当前配置
metaclaw config KEY VALUE       # 设置配置项
```

使用 `--daemon` 启动 MetaClaw 时，命令会等待本地代理就绪后才返回。使用 `metaclaw status` 检查状态，使用 `metaclaw stop` 停止后台进程。

<details>
<summary><b>完整配置参考（点击展开）</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # 可选：本地 MetaClaw 代理 bearer token

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # 你的 Skill 库目录
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # 任务专属 Skill 上限（默认 10）
  auto_evolve: true         # 每次会话结束后自动总结 Skill

rl:
  enabled: false            # 设为 true 开启 RL 训练
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # 可选后端 endpoint，例如 MinT 的 https://mint.macaron.xin/
  tinker_api_key: ""        # api_key 的兼容别名
  tinker_base_url: ""       # base_url 的兼容别名
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

</details>

---

## 💪 Skills 模式

**`metaclaw start --mode skills_only`**

最轻量的模式。无需 GPU,无需 RL 后端。MetaClaw 将你的 LLM 封装在代理后面,每轮注入相关 Skill,对话结束后自动总结新 Skill。

Skill 是存放在 `~/.metaclaw/skills/` 中的简短 Markdown 指令,以独立的 `SKILL.md` 文件组织。Skill 库随使用自动增长。

预加载内置 Skill 库（涵盖编码、安全、Agent 任务等 40+ 个 Skill）：

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL 模式

**`metaclaw start --mode rl`**

在 Skills 模式基础上,增加基于实时对话的持续 RL 微调。每轮对话被 tokenize 并作为训练样本提交。裁判 LLM（PRM）异步为回复打分,Tinker 兼容后端（Tinker 云端或 MinT）执行 LoRA 微调并热更新权重。

**Tinker**（默认）:

```bash
metaclaw config rl.backend tinker
metaclaw config rl.api_key sk-...
metaclaw config rl.model moonshotai/Kimi-K2.5
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start --mode rl
```

**MinT**:

```bash
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-mint-...
metaclaw config rl.base_url https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start --mode rl
```

专属进化器 LLM 还会从失败的 episode 中提取新 Skill,反馈到 Skill 库中。

**程序化 rollout**（无需 OpenClaw TUI）：将 `openclaw_env_data_dir` 设为包含 JSONL 任务文件的目录：

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### 在线策略蒸馏（OPD）

OPD 是 RL 模式的可选附加功能。它将更大的教师模型在线蒸馏到学生模型：学生模型正常生成回复,教师模型对相同回复提供每个 token 的对数概率。KL 惩罚引导学生向教师分布靠拢。

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

教师模型需部署在 OpenAI 兼容的 `/v1/completions` 端点（如 vLLM、SGLang）。OPD 可与 PRM 打分同时使用,两者均异步运行。参考 `examples/run_conversation_opd.py` 和 `scripts/run_openclaw_tinker_opd.sh`。

---

## 🧠 MadMax 模式（默认）

**`metaclaw start`**

在 RL 模式基础上,增加元学习调度器,将权重更新推迟到用户不活跃的窗口,确保活跃使用期间不受干扰。这是默认模式。

RL 权重热更新会暂停 Agent 数分钟。MadMax 不像 RL 模式那样 batch 满后立即训练,而是等待合适的窗口。

三种条件触发更新窗口（满足任一即可）：

- **睡眠时间**：可配置的起止时间（如 23:00 到 07:00）
- **键盘空闲**：空闲 N 分钟后触发
- **Google Calendar 事件**：检测到会议时运行更新

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# 可选：Google Calendar 集成
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

若用户在更新中途返回,部分 batch 会被保存并在下次窗口恢复。

每个 `ConversationSample` 带有 `skill_generation` 版本标签。当 Skill 进化增加 generation 时,RL buffer 被清空,仅使用进化后的样本进行梯度更新（MAML support/query 集分离）。

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

- [OpenClaw](https://openclaw.ai), 核心 Agent 框架。
- [SkillRL](https://github.com/aiming-lab/SkillRL), 我们的 Skill 增强 RL 框架。
- [Tinker](https://www.thinkingmachines.ai/tinker/), 用于在线 RL 训练。
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit), 在线 RL 训练的备选后端。
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL), 我们 RL 设计的灵感来源。
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills), 为我们的 Skill 库提供基础。
- [NanoClaw](https://github.com/qwibitai/nanoclaw) , qwibitai 开发的个人 Claude Agent，通过 `/v1/messages` 兼容端点接入。
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) , NVIDIA 开发的 OpenShell 推理 Agent 插件。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
