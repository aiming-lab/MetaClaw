## MetaClaw Plugin for OpenClaw v0.4.0

One-click installer for [MetaClaw](https://github.com/aiming-lab/MetaClaw) as an OpenClaw extension. No `git clone` required — download the zip, enable, and go.

### One-Click Install

#### macOS / Linux

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions/metaclaw-openclaw
openclaw plugins enable metaclaw-openclaw
openclaw gateway restart
```

> **China users**: If GitHub downloads are slow or timeout, use a mirror:
> ```bash
> curl -LO https://ghfast.top/https://github.com/aiming-lab/MetaClaw/releases/download/v0.4/metaclaw-plugin.zip
> ```

#### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri https://github.com/aiming-lab/MetaClaw/releases/download/v0.4/metaclaw-plugin.zip -OutFile metaclaw-plugin.zip
Expand-Archive metaclaw-plugin.zip -DestinationPath $env:USERPROFILE\.openclaw\extensions\metaclaw-openclaw
openclaw plugins enable metaclaw-openclaw
openclaw gateway restart
```

> **China users**: If GitHub downloads are slow or timeout, replace the download URL with:
> ```
> https://ghfast.top/https://github.com/aiming-lab/MetaClaw/releases/download/v0.4/metaclaw-plugin.zip
> ```

### Then run

```bash
metaclaw setup
metaclaw start
```

### What the plugin does automatically

- Creates an isolated Python virtual environment (`.venv`)
- Installs MetaClaw (`[rl,evolve,scheduler]`) via pip
- Installs `metaclaw` CLI wrapper and configures PATH (macOS / Linux / Windows)
- Patches outbound LLM `fetch` to inject `X-Session-Id` / `X-Turn-Type` headers

### Requirements

- **Python ≥ 3.11**
- **OpenClaw** (any version)
- macOS, Linux, or Windows
- **RAM ≥ 4 GB recommended.** On machines with ≤ 2 GB RAM, add swap before installing:
  ```bash
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  ```

### What's new in v0.4.0

- **Long-term memory system** — MetaClaw now persists cross-session memory for users and projects. Relevant facts, preferences, and project history are automatically retrieved and injected into prompts
- **Adaptive memory policy** — retrieval weights, top-k budgets, and consolidation frequency adapt to observed usage patterns without code changes
- **Memory consolidation** — automatic deduplication, importance decay, and session summarization keep memory quality high over time
- **Offline candidate evaluation** — memory strategy changes are validated against replayed session data before promotion to production
- **Memory sidecar service** — optional standalone memory server (`openclaw-metaclaw-memory`) for deployments requiring process isolation

### Previous releases

---

## MetaClaw Plugin for OpenClaw v0.3.3

### What's new in v0.3.3

- **PyPI-based install** — MetaClaw is now installed from PyPI (`aiming-metaclaw`) instead of GitHub, with Chinese mirror support built in
- **Auto venv creation** — no more system-wide `pip install` or `--break-system-packages` workarounds
- **Auto `pip` recovery** — if venv is missing pip, the plugin runs `ensurepip` automatically
- **CLI wrapper** — `metaclaw` command works directly without activating the venv
- **Cross-platform PATH setup** — automatically adds wrapper to PATH on macOS (`.zshrc` / `.bash_profile`), Linux (`.bashrc`), and Windows (user environment variable)
- **Full pip output** — shows all package downloads and progress bars with speed/size info

### Full auto mode (optional)

```bash
openclaw config set plugins.entries.metaclaw-openclaw.config.oneClickMetaclaw true
```

Enables: venv + pip + default config + `metaclaw start` on gateway load.

### Configuration

See [README](https://github.com/aiming-lab/MetaClaw/blob/main/extensions/metaclaw-openclaw/README.md) for all config options.
