<div align="center">

<img src="assets/new_logo2.png" alt="MetaClaw" width="600">

<br/>

# Just talk to your agent — it learns and *EVOLVES*.

<p>Inspired by how brains learn. Meta-learn and evolve your 🦞 from every conversation in the wild. No GPU required.
  
<br/>


<img src="assets/metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<br/>


<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Fully_Async-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_No_GPU_Cluster-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Skill_Evolution-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_One--Click_Deploy-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

[🇨🇳 中文](./assets/README_ZH.md) • [🇯🇵 日本語](./assets/README_JA.md) • [🇰🇷 한국어](./assets/README_KO.md) • [🇫🇷 Français](./assets/README_FR.md) • [🇩🇪 Deutsch](./assets/README_DE.md) • [🇪🇸 Español](./assets/README_ES.md) • [🇧🇷 Português](./assets/README_PT.md) • [🇷🇺 Русский](./assets/README_RU.md) • [🇮🇹 Italiano](./assets/README_IT.md) • [🇻🇳 Tiếng Việt](./assets/README_VI.md) • [🇦🇪 العربية](./assets/README_AR.md) • [🇮🇳 हिन्दी](./assets/README_HI.md)

<br/>

[Overview](#-overview) • [Quick Start](#-quick-start) • [Multi-Claw Support](#-multi-claw-support) • [Configuration](#️-configuration) • [Skills Mode](#-skills-mode) • [RL Mode](#-rl-mode) • [MadMax Mode](#-madmax-mode-default) • [Citation](#-citation)

</div>

---

<div align="center">

### Two commands. That's it.
</div>

```bash
metaclaw setup              # one-time config wizard
metaclaw start              # default: madmax mode — skills + scheduled RL training
metaclaw start --daemon     # run in background, logs -> ~/.metaclaw/metaclaw.log
metaclaw start --daemon --log-file /tmp/metaclaw.log  # custom daemon log path
metaclaw start --mode rl    # RL without scheduler (trains immediately on full batch)
metaclaw start --mode skills_only  # skills only, no RL (no Tinker needed)
```

<div align="center">
<img src="assets/metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 News

- **[03/16/2026]** **v0.3.2** — Multi-claw support: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw, and NemoClaw now supported alongside OpenClaw. NanoClaw connected via new `/v1/messages` Anthropic-compatible endpoint; NemoClaw via OpenShell inference routing. Added OpenRouter as a supported LLM platform.
- **[03/13/2026]** **v0.3.1** — MinT backend support: RL training now works with both Tinker and MinT. Configurable via `rl.backend` (auto/tinker/mint).
- **[03/13/2026]** **v0.3** — Continual meta-learning support: slow RL updates now only run during sleep hours, idle time, or Google Calendar meetings. Added support/query set separation to prevent stale reward signals from polluting model updates.
- **[03/11/2026]** **v0.2** — One-click deployment via `metaclaw` CLI. Skills enabled by default, RL is now opt-in.
- **[03/09/2026]** We release **MetaClaw** — Just talk to your agent and let it evolve automatically. **NO** GPU deployment required; just plug into the **API**.

---

## 🎥 Demo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Overview

**MetaClaw is an agent that meta-learns and evolves in the wild.**
Just talk to your agent as you normally would — MetaClaw turns every live conversation into a learning signal, enabling the agent to continuously improve through real-world deployment rather than offline training alone.

Under the hood, it places your model behind a proxy that intercepts interactions from your personal agent (OpenClaw, CoPaw, IronClaw, PicoClaw, ZeroClaw, NanoClaw, NemoClaw, or any OpenAI-compatible client), injects relevant skills at each turn, and meta-learns from accumulated experience. For Anthropic-native agents like NanoClaw, MetaClaw also exposes a `/v1/messages` Anthropic-compatible endpoint so the full pipeline works without any agent-side changes. Skills are summarized automatically after each session; with RL enabled, a meta-learning scheduler defers weight updates to idle windows so the agent is never interrupted during active use.

No GPU cluster required. MetaClaw works with any OpenAI-compatible LLM API out of the box, and uses a Tinker-compatible backend for cloud-based LoRA training. [Tinker](https://www.thinkingmachines.ai/tinker/) is the default reference path, and MinT can be enabled through a separate compatibility package when needed.

## 🤖 Key Features

### **One-click deployment**
Configure once with `metaclaw setup`, then `metaclaw start` brings up the proxy, injects skills, and wires your chosen personal agent (OpenClaw, CoPaw, or IronClaw) automatically. No manual shell scripts needed.

### **Three operating modes**

| Mode | Default | What it does |
|------|---------|--------------|
| `skills_only` | | Proxy your LLM API. Skills injected and auto-summarized after each session. No GPU/Tinker required. |
| `rl` | | Skills + RL training (GRPO). Trains immediately when a batch is full. Optional OPD for teacher distillation. |
| `madmax` | ✅ | Skills + RL + smart scheduler. RL weight updates only run during sleep/idle/meeting windows. |

### **Asynchronous by design**
Serving, reward modeling, and training are fully decoupled. The agent continues responding while scoring and optimization run in parallel.

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -e .                        # skills_only mode (lightweight)
pip install -e ".[rl]"                  # + RL training support (torch, transformers, tinker)
pip install -e ".[evolve]"              # + skill evolution via OpenAI-compatible LLM
pip install -e ".[scheduler]"           # + Google Calendar integration for scheduler
pip install -e ".[rl,evolve,scheduler]" # recommended for full RL + scheduler setup
```

If you want to run `rl.backend=mint`, install the MinT compatibility package separately in the same environment, for example [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). MetaClaw keeps that dependency out of the default package so RL users can choose Tinker or MinT explicitly.

### 2. Configure

```bash
metaclaw setup
```

The interactive wizard will ask you to:
1. **Choose your personal agent** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw`, or `none` (MetaClaw will auto-configure it on start)
2. **Choose your LLM provider** — Kimi, Qwen, MiniMax, or custom
3. **Enter your API key** and optionally enable RL training

MetaClaw's RL path can switch explicitly between `tinker` and `mint`. `auto` is the recommended default and will still infer MinT from Mint-like credentials or base URLs when the MinT package is installed.

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

Legacy aliases `rl.tinker_api_key` and `rl.tinker_base_url` are still accepted for backward compatibility.

### 3. Start

```bash
metaclaw start
```

That's it. MetaClaw starts the proxy, automatically configures your chosen personal agent to use it, and restarts the gateway. Open your agent and start chatting — skills are injected at every turn, and the session is automatically summarized into new skills when you're done.

---

## 🦞 Multi-Claw Support

MetaClaw works as a transparent proxy in front of any personal agent that supports an OpenAI-compatible LLM backend. The `claw_type` setting tells MetaClaw which agent to auto-configure when it starts.

| `claw_type` | Agent | What MetaClaw does on `start` |
|---|---|---|
| `openclaw` | [OpenClaw](https://openclaw.ai) | Runs `openclaw config set models.providers.metaclaw …` + `gateway restart` |
| `copaw` | [CoPaw](https://github.com/agentscope-ai/CoPaw) | Patches `~/.copaw/config.json` → `models.default` → `openai_compatible` pointing at the proxy port. CoPaw's ConfigWatcher hot-reloads automatically. |
| `ironclaw` | [IronClaw](https://github.com/nearai/ironclaw) | Patches `~/.ironclaw/.env` → `LLM_BACKEND=openai_compatible` + `LLM_BASE_URL/MODEL/API_KEY`. Runs `ironclaw service restart`. |
| `picoclaw` | [PicoClaw](https://github.com/sipeed/picoclaw) | Injects a `metaclaw` entry into `~/.picoclaw/config.json` `model_list` and sets it as the default model. Runs `picoclaw gateway restart`. |
| `zeroclaw` | [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw) | Patches `~/.zeroclaw/config.toml` → `provider = "openai-compatible"` + `base_url/model/api_key`. Runs `zeroclaw service restart`. |
| `nanoclaw` | [NanoClaw](https://github.com/qwibitai/nanoclaw) | Patches nanoclaw's `.env` → `ANTHROPIC_BASE_URL` pointing at the proxy's `/v1/messages` Anthropic-compatible endpoint. Restarts via `launchctl` (macOS) or `systemctl --user` (Linux). |
| `nemoclaw` | [NemoClaw](https://github.com/NVIDIA/NemoClaw) | Registers a `metaclaw` provider in OpenShell via `openshell provider create` and sets it as the active inference route via `openshell inference set`. Persists config to `~/.nemoclaw/config.json`. |
| `none` | — | Skips auto-configuration. Point your agent at the proxy manually. |

### Setup

Pick your agent during `metaclaw setup` (the first question in the wizard):

```
Personal agent to configure (openclaw/copaw/ironclaw/picoclaw/zeroclaw/nanoclaw/nemoclaw/none) [openclaw]:
```

Or set it directly at any time:

```bash
metaclaw config claw_type copaw      # switch to CoPaw
metaclaw config claw_type ironclaw   # switch to IronClaw
metaclaw config claw_type picoclaw   # switch to PicoClaw
metaclaw config claw_type zeroclaw   # switch to ZeroClaw
metaclaw config claw_type nanoclaw   # switch to NanoClaw
metaclaw config claw_type nemoclaw   # switch to NemoClaw
metaclaw config claw_type none       # manual / custom agent
```

Then run `metaclaw start` as usual — the proxy comes up and the chosen agent is wired automatically.

### Manual wiring (claw_type=none)

Point any OpenAI-compatible client at the MetaClaw proxy:

```
base_url: http://127.0.0.1:30000/v1
api_key:  metaclaw          # or whatever proxy.api_key is set to
model:    <your model id>
```

For Anthropic-native clients (e.g. the Claude SDK or NanoClaw's credential proxy), use the Anthropic-compatible endpoint instead:

```
ANTHROPIC_BASE_URL: http://127.0.0.1:30000
ANTHROPIC_API_KEY:  metaclaw
```

---

## ⚙️ Configuration

Configuration lives in `~/.metaclaw/config.yaml`, created by `metaclaw setup`.

**CLI commands:**

```
metaclaw setup                  # Interactive first-time configuration wizard
metaclaw start                  # Start MetaClaw (default: madmax mode)
metaclaw start --daemon         # Start MetaClaw in background
metaclaw start --daemon --log-file /tmp/metaclaw.log  # Custom daemon log path
metaclaw start --mode rl        # Force RL mode (no scheduler) for this session
metaclaw start --mode skills_only  # Force skills-only mode for this session
metaclaw stop                   # Stop a running MetaClaw instance
metaclaw status                 # Check proxy health, running mode, and scheduler state
metaclaw config show            # View current configuration
metaclaw config KEY VALUE       # Set a config value
```

When you start MetaClaw with `--daemon`, the command waits until the local proxy becomes healthy before returning. Use `metaclaw status` to verify readiness and `metaclaw stop` to stop the background process.

<details>
<summary><b>Full config reference (click to expand)</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "none"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # optional bearer token for the local MetaClaw proxy

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # your skill library
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # cap task-specific skills (default 10)
  auto_evolve: true         # auto-summarize skills after each session

rl:
  enabled: false            # set to true to enable RL training
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # optional backend endpoint, e.g. https://mint.macaron.xin/ for MinT
  tinker_api_key: ""        # legacy alias for api_key
  tinker_base_url: ""       # legacy alias for base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # optional checkpoint path to resume training
  evolver_api_base: ""      # leave empty to reuse llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # set to true to enable OPD (teacher distillation)
  teacher_url: ""           # teacher model base URL (OpenAI-compatible /v1/completions)
  teacher_model: ""         # teacher model name (e.g., Qwen/Qwen3-32B)
  teacher_api_key: ""       # teacher model API key
  kl_penalty_coef: 1.0      # KL penalty coefficient for OPD

max_context_tokens: 20000   # prompt token cap before truncation

scheduler:                  # v0.3: meta-learning scheduler (auto-enabled in madmax mode)
  enabled: false            # madmax mode enables this automatically; set manually for rl mode
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

## 💪 Skills Mode

**`metaclaw start --mode skills_only`**

The lightest mode. No GPU, no RL backend needed. MetaClaw places your LLM behind a proxy that injects relevant skills at every turn, then auto-summarizes new skills after each conversation.

For OpenAI-compatible custom providers, set `llm.api_base` to the full chat API base (usually ending in `/v1`, for example `https://your-gateway.example/v1`). In `skills_only` mode, MetaClaw reuses that same endpoint for prompt compression and related helper LLM calls unless you configure a separate evolver endpoint.

Skills are short Markdown instructions stored in `~/.metaclaw/skills/` as individual `SKILL.md` files. The library grows automatically with your usage.

To pre-load the built-in skill bank (40+ skills across coding, security, agentic tasks, etc.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL Mode

**`metaclaw start --mode rl`**

Everything in Skills Mode, plus continuous RL fine-tuning from live conversations. Each conversation turn is tokenized and submitted as a training sample. A judge LLM (PRM) scores responses asynchronously, and a Tinker-compatible backend (Tinker cloud or MinT) runs LoRA fine-tuning with hot-swapped weights.

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

A dedicated evolver LLM also extracts new skills from failed episodes, feeding them back into the skill library.

**Programmatic rollout** (no OpenClaw TUI needed): set `openclaw_env_data_dir` to a directory of JSONL task files:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### On-Policy Distillation (OPD)

OPD is an optional add-on for RL Mode. It distills a larger teacher model into the student on-policy: the student generates responses as usual, and the teacher provides per-token log-probabilities on those same responses. A KL penalty steers the student toward the teacher's distribution.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

The teacher must be served behind an OpenAI-compatible `/v1/completions` endpoint (e.g., vLLM, SGLang). OPD can be combined with PRM scoring, both run asynchronously. See `examples/run_conversation_opd.py` and `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 MadMax Mode (Default)

**`metaclaw start`**

Everything in RL Mode, plus a meta-learning scheduler that defers weight updates to user-inactive windows so the agent is never interrupted during active use. This is the default mode.

The RL weight hot-swap step pauses the agent for several minutes. Instead of training immediately when a batch is full (like RL Mode does), MadMax waits for an appropriate window.

Three conditions trigger an update window (any one is sufficient):

- **Sleep hours**: configurable start/end time (e.g., 23:00 to 07:00)
- **Keyboard inactivity**: triggers after N minutes of idle time
- **Google Calendar events**: detects meetings so updates can run while you're away

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Optional: Google Calendar integration
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

If the user returns mid-update, the partial batch is saved and resumed at the next window.

Each `ConversationSample` is tagged with a `skill_generation` version. When skill evolution bumps the generation, the RL buffer is flushed so only post-evolution samples are used for gradient updates (MAML support/query set separation).

---

## 📚 Citation

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

## 🙏 Acknowledgements

MetaClaw builds on top of the following open-source projects:

- [OpenClaw](https://openclaw.ai) – the primary supported personal agent.
- [CoPaw](https://github.com/agentscope-ai/CoPaw) – multi-channel personal agent support.
- [IronClaw](https://github.com/nearai/ironclaw) – Rust-native personal agent support.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) – container-isolated Anthropic-native personal agent.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) – NVIDIA OpenShell-sandboxed personal agent with NIM inference.
- [SkillRL](https://github.com/aiming-lab/SkillRL) – our skill-augmented RL framework.
- [Tinker](https://www.thinkingmachines.ai/tinker/) – used for online RL training.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) – alternative backend for online RL training.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) – inspiration for our RL design.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) – provides the foundation for our skill bank.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
