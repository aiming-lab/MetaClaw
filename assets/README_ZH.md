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

[概述](#-概述) • [快速开始](#-快速开始) • [配置说明](#️-配置说明) • [Skills 模式](#-skills-模式) • [RL 模式](#-rl-模式) • [Auto 模式](#-auto-模式默认) • [引用](#-引用)

</div>

---

<div align="center">

### 两条命令,搞定一切。
</div>

```bash
metaclaw setup              # 首次配置向导
metaclaw start              # 默认 auto 模式：Skills + 定时 RL 训练
metaclaw start --mode rl    # 无调度器 RL（batch 满即训练）
metaclaw start --mode skills_only  # 仅 Skills，无 RL（无需 Tinker）
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 最新动态

- **[2026/04/11]** **v0.4.1** — 增量记忆摄取：记忆层现在每 N 轮（默认 5）抽取并持久化一次对话，而非只在会话结束时处理，缩小了会话中途的记忆空白期。新增 `/buffer_turn` 与 `/flush_session` sidecar 端点、带 `--buffer-turns` 参数的 benchmark 工具，以及实验对比报告。
- **[2026/03/25]** **v0.4.0** — Contexture layer（上下文层）：MetaClaw 现可跨会话持久化用户和项目记忆。相关事实、偏好和项目历史自动检索并注入提示中。包含自适应记忆策略、后台整合及可选的记忆边车服务。
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

无需 GPU 集群。MetaClaw 兼容任意 OpenAI 格式的 LLM API,并通过 Tinker 兼容后端进行云端 LoRA 微调。[Tinker](https://www.thinkingmachines.ai/tinker/) 是默认参考路径；如果需要,也可以通过单独安装的兼容包接入 MinT 或 Weaver。

## 🤖 核心功能

### **一键部署**
使用 `metaclaw setup` 完成一次性配置,再执行 `metaclaw start` 即可自动启动代理、注入 Skill 并接入 OpenClaw。无需手动编写 Shell 脚本。

### **三种运行模式**

| 模式 | 默认 | 功能说明 |
|------|------|----------|
| `skills_only` | | 代理你的 LLM API。注入 Skill,会话结束后自动总结。无需 GPU / Tinker。 |
| `rl` | | Skills + RL 训练（GRPO）。batch 满后立即训练。可选 OPD 进行教师蒸馏。 |
| `auto` | ✅ | Skills + RL + 智能调度器。RL 权重更新只在睡眠/空闲/会议窗口进行。 |

### **长期记忆**
MetaClaw 可跨会话持久保存事实、偏好与项目历史，并在每轮对话中检索相关上下文注入提示——让你的 Agent 记得你说过的话，即使相隔数周。

### **完全异步设计**
推理服务、奖励建模与训练完全解耦。Agent 持续响应的同时,打分与优化在后台并行进行。

---

## 🚀 快速开始

### 1. 安装

**OpenClaw（一键安装）：** 请使用 [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) 版本：运行下方命令后执行 `metaclaw setup` 与 `metaclaw start`。更多说明（Windows、镜像、配置、排错）见 [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md)。

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip**（PyPI 或本仓库）：

```bash
pip install -e .                        # skills_only 模式（轻量）
pip install -e ".[rl]"                  # + RL 训练支持（torch、transformers、tinker）
pip install -e ".[evolve]"              # + 通过 OpenAI 兼容 LLM 进行 Skill 进化
pip install -e ".[scheduler]"           # + Google Calendar 调度器集成
pip install -e ".[rl,evolve,scheduler]" # 推荐：完整 RL + 调度器配置
```
（可选）微信集成使用官方 @tencent-weixin/openclaw-weixin 插件。启用微信时，MetaClaw 会自动安装该插件：

```bash
metaclaw config wechat.enabled true
metaclaw start
```

该插件在 `metaclaw start` 时自动安装。你也可以手动安装：

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

要切换微信账号（使用新的二维码重新登录）：

```bash
metaclaw start --wechat-relogin
```

如果你要使用 `rl.backend=mint`,请在同一环境里额外安装 MinT 兼容包,例如 [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit)。如果你要使用 `rl.backend=weaver`,请另行安装 [`nex-weaver`](https://github.com/nex-agi/weaver)。MetaClaw 不会把这些依赖放进默认安装中,这样 RL 用户可以明确选择 Tinker、MinT 或 Weaver。

### 2. 配置

```bash
metaclaw setup
```

交互式向导会引导你完成：
1. **选择个人 Agent** — `openclaw`、`copaw`、`ironclaw`、`picoclaw`、`zeroclaw`、`nanoclaw`、`nemoclaw` 或 `none`（`metaclaw start` 时会自动配置）
2. **选择认证方式** — `api_key`（直连 API）或 `oauth_token`（CLI 子进程）
3. **选择 LLM 提供商**
   - **api_key**：Kimi、Qwen、OpenAI、Minimax、Novita、OpenRouter、Volcengine、BytePlus 或自定义
   - **Volcengine / BytePlus**：再选择 `standard` 或 `coding-plan` 变体，并填写对应 API Key
   - **oauth_token**：Anthropic（Claude Code）、OpenAI Codex 或 Gemini CLI
4. **填写模型 ID**，并可选择是否启用 RL 训练

MetaClaw 的 RL 路径可以显式切换 `tinker`、`mint` 和 `weaver`。推荐默认值是 `auto`；当环境里安装了 MinT 或 Weaver 兼容包时,它仍然可以根据对应风格的凭证或 base URL 自动识别。

**Tinker**:

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

**Weaver**:

```bash
metaclaw config rl.backend weaver
metaclaw config rl.api_key sk-...
metaclaw config rl.base_url https://weaver-console.nex-agi.cn
metaclaw config rl.model Qwen/Qwen3-8B
```

兼容旧配置的 `rl.tinker_api_key` 和 `rl.tinker_base_url` 仍然可以继续使用。

### 3. 启动

```bash
metaclaw start
```

就这些。MetaClaw 启动代理，自动配置你所选的个人 Agent 并重启网关。打开你的 Agent 开始对话——每轮都会注入 Skill，会话结束后会自动总结为新 Skill。

---

## ⚙️ 配置说明

配置文件位于 `~/.metaclaw/config.yaml`,由 `metaclaw setup` 自动生成。

**CLI 命令：**

```
metaclaw setup                  # 首次交互式配置向导
metaclaw start                  # 启动 MetaClaw（默认 auto 模式）
metaclaw start --mode rl        # 本次会话强制启用 RL 模式（无调度器）
metaclaw start --mode skills_only  # 本次会话强制仅 Skills 模式
metaclaw stop                   # 停止正在运行的 MetaClaw 实例
metaclaw status                 # 查看代理健康状态、运行模式与调度器状态
metaclaw config show            # 查看当前配置
metaclaw config KEY VALUE       # 设置配置项
metaclaw config llm.oauth_token TOKEN               # 为当前 CLI provider 存储 OAuth token
metaclaw auth paste-token --provider anthropic      # 存储 OAuth token（anthropic | openai-codex | gemini）
metaclaw auth status                                # 显示所有已存储的认证配置
metaclaw uninstall              # 删除所有 MetaClaw 数据、OpenClaw 扩展和 pip 包
```

使用 `metaclaw status` 验证就绪状态，使用 `metaclaw stop` 停止进程。

<details>
<summary><b>完整配置参考（点击展开）</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | byteplus | custom
  plan_variant: ""          # 仅 volcengine/byteplus 使用："standard" | "coding-plan"
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # oauth_token 示例（token 通过 `metaclaw auth paste-token` 存储）：
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

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
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # 可选后端 endpoint，例如 MinT 的 https://mint.macaron.xin/ 或 Weaver 的 https://weaver-console.nex-agi.cn
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

max_context_tokens: 20000   # 截断前 prompt token 上限；0 表示不截断（大上下文云端模型在 skills_only 下推荐）
                            #
context_window: 0           # 向 Agent 声明的上下文窗口（如 OpenClaw 压缩阈值）；0 为自动
                            # （skills_only 约 200000，rl/auto 约 32768）

scheduler:                  # v0.3：元学习调度器（auto 模式下自动启用）
  enabled: false            # auto 模式自动启用；rl 模式需手动设置
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

若使用 OpenAI 兼容的自定义服务商，请将 `llm.api_base` 设为完整的对话 API 根地址（通常以 `/v1` 结尾，例如 `https://your-gateway.example/v1`）。在 `skills_only` 模式下，除非你单独配置 evolver 端点，否则 MetaClaw 会用同一地址完成提示压缩等辅助 LLM 调用。

Skill 是存放在 `~/.metaclaw/skills/` 中的简短 Markdown 指令,以独立的 `SKILL.md` 文件组织。Skill 库随使用自动增长。

预加载内置 Skill 库（涵盖编码、安全、Agent 任务等 40+ 个 Skill）：

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL 模式

**`metaclaw start --mode rl`**

在 Skills 模式基础上,增加基于实时对话的持续 RL 微调。每轮对话被 tokenize 并作为训练样本提交。裁判 LLM（PRM）异步为回复打分,Tinker 兼容后端（Tinker 云端、MinT 或 Weaver）执行 LoRA 微调并热更新权重。

**Tinker**:

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

**Weaver**:

```bash
metaclaw config rl.backend weaver
metaclaw config rl.api_key sk-...
metaclaw config rl.base_url https://weaver-console.nex-agi.cn
metaclaw config rl.model Qwen/Qwen3-8B
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

## 🧠 Auto 模式（默认）

**`metaclaw start`**

在 RL 模式基础上,增加元学习调度器,将权重更新推迟到用户不活跃的窗口,确保活跃使用期间不受干扰。这是默认模式。

RL 权重热更新会暂停 Agent 数分钟。auto 模式不像 RL 模式那样 batch 满后立即训练,而是等待合适的窗口。

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

## 🗑️ 卸载

```bash
metaclaw uninstall
```

一键删除所有内容：停止运行实例、清理 `~/.openclaw/openclaw.json` 中的 MetaClaw 引用、删除 `~/.openclaw/extensions/metaclaw-openclaw/`、删除 `~/.metaclaw/`、卸载 pip 包并重启 OpenClaw 网关。删除前会要求确认。

卸载后如有克隆的源码仓库，请手动删除：

```bash
rm -rf /path/to/MetaClaw
```

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
- [Weaver](https://github.com/nex-agi/weaver), 在线 RL 训练的备选后端。
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL), 我们 RL 设计的灵感来源。
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills), 为我们的 Skill 库提供基础。
- [NanoClaw](https://github.com/qwibitai/nanoclaw) , qwibitai 开发的个人 Claude Agent，通过 `/v1/messages` 兼容端点接入。
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) , NVIDIA 开发的 OpenShell 推理 Agent 插件。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
