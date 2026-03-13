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
metaclaw start              # skills on, OpenClaw wired — ready to chat
metaclaw start --mode rl    # optional: + live RL training via a Tinker-compatible backend
```

<div align="center">
<img src="assets/metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 News

- **[03/10/2026]** **v0.2** — One-click deployment via `metaclaw` CLI. Skills enabled by default, RL is now opt-in.
- **[03/09/2026]** We release **MetaClaw** — Just talk to your agent and let it evolve automatically. **NO** GPU deployment required; just plug into the **API**.

---

## 🎥 Demo

https://github.com/user-attachments/assets/1c2919fc-5612-40f7-bb97-c74ab50619d5

---

## 📖 Overview

**MetaClaw turns live conversations into continuous training data — automatically.**
Just talk to your agent as usual, and MetaClaw handles the learning loop behind the scenes.

It places your model behind an OpenAI-compatible proxy that intercepts interactions from OpenClaw, injects relevant skills at each step, and can optionally perform continuous fine-tuning through a Tinker-compatible cloud RL backend such as Tinker or MinT. Updated weights are hot-swapped seamlessly without interrupting the service.

There is no need to maintain a dedicated GPU cluster. MetaClaw works with any OpenAI-compatible LLM API out of the box, and can attach RL training to a Tinker-compatible backend such as [Tinker](https://www.thinkingmachines.ai/tinker/) or MinT for cloud-based LoRA fine-tuning.

## 🤖 Key Features

### **One-click deployment**
Configure once with `metaclaw setup`, then `metaclaw start` brings up the proxy, injects skills, and wires OpenClaw automatically. No manual shell scripts needed.

### **Two operating modes**

| Mode | Default | What it does |
|------|---------|--------------|
| `skills_only` | ✅ | Proxy → your LLM API. Skills injected, auto-summarized after each session. No GPU/Tinker required. |
| `rl` | off | Proxy → Tinker-compatible cloud RL. Full training loop with PRM scoring and skill evolution from failures. |

### **Skill injection**
At every turn, MetaClaw retrieves the most relevant skill instructions and injects them into the agent's system prompt. Immediate behavior improvement without retraining.

### **Automatic skill summarization**
After each conversation, the same LLM you're already using analyzes the session and distills new skills automatically. With RL enabled, a dedicated judge model extracts skills from failed episodes.

### **No GPU cluster required**
In `skills_only` mode, only a network connection is needed. RL training is offloaded to a Tinker-compatible cloud backend.

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
pip install -e .            # skills_only mode (lightweight)
pip install -e ".[rl]"      # + RL training support (torch, transformers, tinker)
pip install -e ".[evolve]"  # + skill evolution via OpenAI-compatible LLM
```

If you want to run `rl.backend=mint`, install the MinT compatibility package separately in the same environment, for example [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). The official MinT docs are at [`mint-doc-alpha.macaron.im`](https://mint-doc-alpha.macaron.im/). MetaClaw intentionally keeps that dependency out of the default package so RL users can choose Tinker or MinT explicitly.

### 2. Configure

```bash
metaclaw setup
```

The interactive wizard will ask you to choose your LLM provider (Kimi, Qwen, or custom), enter your API key, and optionally enable RL training.

MetaClaw's RL path can switch explicitly between `tinker` and `mint`. `auto` is the recommended default and will still infer MinT from Mint-like credentials/base URLs when the MinT package is installed. In practice that means you can keep one RL workflow and point it at either Tinker cloud or a MinT deployment just by changing config.

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

That's it. MetaClaw starts the proxy, automatically configures OpenClaw to use it, and restarts the gateway. Open OpenClaw and start chatting — skills are injected at every turn, and the session is automatically summarized into new skills when you're done.

---

## 🛠️ CLI Reference

```
metaclaw setup              # Interactive first-time configuration wizard
metaclaw start              # Start MetaClaw (proxy + optional RL)
metaclaw start --mode rl    # Force RL mode for this session
metaclaw stop               # Stop a running MetaClaw instance
metaclaw status             # Check proxy health and running mode
metaclaw config show        # View current configuration
metaclaw config KEY VALUE   # Set a config value
```

**Common config keys:**

```bash
metaclaw config rl.enabled true           # Enable RL training
metaclaw config rl.backend auto           # auto | tinker | mint
metaclaw config rl.api_key sk-...         # Set RL backend key
metaclaw config rl.base_url https://mint.macaron.xin/  # Optional backend endpoint, e.g. MinT
metaclaw config skills.auto_evolve false  # Disable auto skill summarization
metaclaw config proxy.port 31000          # Change proxy port
```

---

## ⚙️ Configuration

Configuration lives in `~/.metaclaw/config.yaml`, created by `metaclaw setup`.

```yaml
mode: skills_only          # "skills_only" | "rl"

llm:
  provider: kimi            # kimi | qwen | openai | custom
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

Enable RL training to continuously fine-tune the model from live conversations with either Tinker or MinT:

```bash
metaclaw config rl.enabled true
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-...
metaclaw config rl.base_url https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

In RL mode:
- Each conversation turn is tokenized and submitted as a training sample
- A judge LLM (PRM) scores responses asynchronously
- A Tinker-compatible backend such as Tinker cloud or MinT runs LoRA fine-tuning; updated weights are hot-swapped every `batch_size` samples
- A dedicated evolver LLM extracts new skills from failed episodes

If you prefer Tinker cloud, switch `rl.backend` to `tinker` or leave it on `auto` and omit the MinT endpoint.

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

## 📚 Citation

```bibtex
@misc{xia2026metaclaw,
  author       = {Xia, Peng and Chen, Jianwen and Yang, Xinyu and Tu, Haoqin and Han, Siwei and Qiu, Shi and Zheng, Zeyu and Xie, Cihang and Yao, Huaxiu},
  title        = {MetaClaw},
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
