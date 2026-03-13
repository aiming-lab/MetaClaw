<div align="center">

<img src="assets/new_logo.png" alt="MetaClaw" width="600">

<br/>

# Just talk to your agent — it learns and *EVOLVES*.

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Fully_Async-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_No_GPU_Cluster-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Skill_Evolution-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_One--Click_Deploy-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇨🇳 中文](./assets/README_ZH.md) • [🇯🇵 日本語](./assets/README_JA.md) • [🇰🇷 한국어](./assets/README_KO.md) • [🇫🇷 Français](./assets/README_FR.md) • [🇩🇪 Deutsch](./assets/README_DE.md) • [🇪🇸 Español](./assets/README_ES.md)

<br/>

</div>

---

<div align="center">

### Two commands. That's it.
</div>

```bash
metaclaw setup              # one-time config wizard
metaclaw start              # default: madmax mode — skills + scheduled RL training
metaclaw start --mode rl    # RL without scheduler (trains immediately on full batch)
metaclaw start --mode skills_only  # skills only, no RL (no Tinker needed)
```

<div align="center">
<img src="assets/metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 News

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

Under the hood, it places your model behind an OpenAI-compatible proxy that intercepts interactions from OpenClaw, injects relevant skills at each turn, and meta-learns from accumulated experience. Skills are summarized automatically after each session; with RL enabled, a meta-learning scheduler defers weight updates to idle windows so the agent is never interrupted during active use.

No GPU cluster required. MetaClaw works with any OpenAI-compatible LLM API out of the box, and optionally integrates **Kimi-K2.5** (1T MoE) via [Tinker](https://www.thinkingmachines.ai/tinker/) for cloud-based LoRA training.

## 🤖 Key Features

### **One-click deployment**
Configure once with `metaclaw setup`, then `metaclaw start` brings up the proxy, injects skills, and wires OpenClaw automatically. No manual shell scripts needed.

### **Three operating modes**

| Mode | Default | What it does |
|------|---------|--------------|
| `madmax` | ✅ | RL + smart scheduler. Skills always on; RL weight updates only run during sleep/idle/meeting windows. |
| `rl` | — | RL without scheduler. Trains immediately when a batch is full (original v0.2 behavior). |
| `skills_only` | — | Proxy → your LLM API. Skills injected, auto-summarized after each session. No GPU/Tinker required. |

### **Skill injection**
At every turn, MetaClaw retrieves the most relevant skill instructions and injects them into the agent's system prompt. Immediate behavior improvement without retraining.

### **Automatic skill summarization**
After each conversation, the same LLM you're already using analyzes the session and distills new skills automatically. With RL enabled, a dedicated judge model extracts skills from failed episodes.

### **No GPU cluster required**
In `skills_only` mode, only a network connection is needed. RL training is offloaded to Tinker cloud.

### **Two learning modes**
MetaClaw supports both:
- **RL (GRPO)** for learning from implicit feedback signals
- **On-Policy Distillation (OPD)** for distilling a larger teacher model into the student on-policy

In OPD mode, the student generates responses as usual, and a teacher model provides per-token log-probabilities on those same responses. The teacher logprobs are passed to the loss function (e.g., `cispo`) so the student learns to match the teacher's distribution. The teacher must be served behind an OpenAI-compatible `/v1/completions` endpoint (e.g., vLLM, SGLang).

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

### 2. Configure

```bash
metaclaw setup
```

The interactive wizard will ask you to choose your LLM provider (Kimi, Qwen, MiniMax, or custom), enter your API key, and optionally enable RL training.

### 3. Start

```bash
metaclaw start
```

That's it. MetaClaw starts the proxy, automatically configures OpenClaw to use it, and restarts the gateway. Open OpenClaw and start chatting — skills are injected at every turn, and the session is automatically summarized into new skills when you're done.

---

## 🛠️ CLI Reference

```
metaclaw setup                  # Interactive first-time configuration wizard
metaclaw start                  # Start MetaClaw (default: madmax mode)
metaclaw start --mode rl        # Force RL mode (no scheduler) for this session
metaclaw start --mode skills_only  # Force skills-only mode for this session
metaclaw stop                   # Stop a running MetaClaw instance
metaclaw status                 # Check proxy health, running mode, and scheduler state
metaclaw config show            # View current configuration
metaclaw config KEY VALUE       # Set a config value
```

**Common config keys:**

```bash
metaclaw config rl.enabled true           # Enable RL training
metaclaw config rl.tinker_api_key sk-...  # Set Tinker key
metaclaw config skills.auto_evolve false  # Disable auto skill summarization
metaclaw config proxy.port 31000          # Change proxy port
```

---

## ⚙️ Configuration

Configuration lives in `~/.metaclaw/config.yaml`, created by `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # your skill library
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # cap task-specific skills (default 10)
  auto_evolve: true         # auto-summarize skills after each session

rl:
  enabled: false            # set to true to enable RL training
  model: moonshotai/Kimi-K2.5
  tinker_api_key: ""
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
  sleep_start: "23:00"      # HH:MM local time — start of sleep window
  sleep_end: "07:00"        # HH:MM local time — end of sleep window
  idle_threshold_minutes: 30  # trigger RL after N minutes of keyboard inactivity
  min_window_minutes: 15    # minimum window length required to start an RL step
  calendar:
    enabled: false          # use Google Calendar to detect meeting slots
    credentials_path: ""    # path to client_secrets.json from Google Cloud Console
    token_path: ""          # saved OAuth token (default: ~/.metaclaw/calendar_token.json)
```

---

## 💪 Skills

Skills are short Markdown instructions injected into the agent's system prompt at each turn. They live in your skills directory (`~/.metaclaw/skills/` by default), organized as individual `SKILL.md` files.

**Skill auto-summarization** runs after each conversation. The LLM you configured analyzes what happened and generates new skills automatically. No manual curation needed — the library grows with your usage.

To pre-load the built-in skill bank (40+ skills across coding, security, agentic tasks, etc.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Advanced: RL Mode

Enable RL training to continuously fine-tune the model from live conversations:

```bash
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

In RL mode:
- Each conversation turn is tokenized and submitted as a training sample
- A judge LLM (PRM) scores responses asynchronously
- Tinker cloud runs LoRA fine-tuning; updated weights are hot-swapped every `batch_size` samples
- A dedicated evolver LLM extracts new skills from failed episodes

**Programmatic rollout** (no OpenClaw TUI needed): set `openclaw_env_data_dir` to a directory of JSONL task files:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 Advanced: OPD Mode

On-Policy Distillation (OPD) lets you distill a larger teacher model into the student while it trains on-policy. The student generates responses as usual; the teacher provides per-token log-probabilities on those same responses. A KL penalty steers the student toward the teacher's distribution.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

The teacher must be served behind an OpenAI-compatible `/v1/completions` endpoint (e.g., vLLM, SGLang). OPD can be combined with PRM scoring — both run asynchronously.

See `examples/run_conversation_opd.py` for a programmatic example and `scripts/run_openclaw_tinker_opd.sh` for a ready-made launch script.

---

## 🧠 Advanced: Meta-Learning Scheduler (v0.3)

In RL mode, the weight hot-swap step pauses the agent for several minutes. The scheduler (enabled by default in `madmax` mode) defers RL updates to user-inactive windows so the agent is never interrupted during active use.

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Optional: Google Calendar integration
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Three conditions trigger an update window (any one is sufficient): configured sleep hours, system keyboard inactivity, or an active Google Calendar event. If the user returns mid-update, the partial batch is saved and resumed at the next window.

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

- [OpenClaw](https://openclaw.ai) – the core agent framework.
- [SkillRL](https://github.com/aiming-lab/SkillRL) – our skill-augmented RL framework.
- [Tinker](https://www.thinkingmachines.ai/tinker/) – used for online RL training.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) – inspiration for our RL design.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) – provides the foundation for our skill bank.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
