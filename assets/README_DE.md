<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# Sprich einfach mit deinem Agenten — er lernt und *ENTWICKELT* sich weiter.

<p>Inspiriert davon, wie das Gehirn lernt. Meta-lernen und entwickeln Sie Ihren 🦞 aus jedem Gespräch. Keine GPU nötig. Kompatibel mit Kimi, Qwen, Claude, MiniMax und mehr.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Vollständig_Async-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Kein_GPU--Cluster-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Skill--Evolution-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Ein--Klick--Deployment-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇦🇪 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[Übersicht](#-übersicht) • [Schnellstart](#-schnellstart) • [Konfiguration](#️-konfiguration) • [Skills-Modus](#-skills-modus) • [RL-Modus](#-rl-modus) • [Auto-Modus](#-auto-modus-standard) • [Zitierung](#-zitierung)

</div>

---

<div align="center">

### Zwei Befehle. Das ist alles.
</div>

```bash
metaclaw setup              # Einmaliger Konfigurationsassistent
metaclaw start              # Standard: Auto-Modus, Skills + geplantes RL-Training
metaclaw start --mode rl    # RL ohne Scheduler (trainiert sofort bei vollem Batch)
metaclaw start --mode skills_only  # Nur Skills, kein RL (kein Tinker nötig)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Neuigkeiten

- **[19.04.2026]** **v0.4.2** — OpenClaw Context-Engine-Integration: Das Memory-Plugin registriert sich als Context-Engine (Assemble/Compact-Lebenszyklus) auf OpenClaw v2026.4.10+ und eliminiert doppelte Memory-Injektion. Ergänzt inkrementelle pro-Turn-Erfassung mit Final-Flush, OpenClaw-Kompatibilitäts-Konfiguration und Active-Memory-Unterdrückung für nahtlose proxyseitige Skill-Injektion.
- **[11.04.2026]** **v0.4.1** — Inkrementelle Speichererfassung: die Speicherschicht extrahiert und speichert jetzt alle N Turns (Standard 5) statt nur am Sitzungsende, wodurch der Speicher-Blackout mitten in einer Sitzung verkürzt wird. Fügt neue `/buffer_turn`- und `/flush_session`-Sidecar-Endpunkte, ein Benchmark-Harness mit `--buffer-turns`-Flag und Experiment-Vergleichsberichte hinzu.
- **[25.03.2026]** **v0.4.0** — Contexture layer: MetaClaw speichert nun sitzungsübergreifend Erinnerungen für Nutzer und Projekte. Relevante Fakten, Präferenzen und Projektverlauf werden automatisch abgerufen und in Prompts injiziert. Enthält adaptive Speicherrichtlinie, Hintergrundkonsolidierung und einen optionalen Memory-Sidecar-Dienst.
- **[16.03.2026]** **v0.3.2** Multi-Claw-Unterstützung: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw und NemoClaw werden neben OpenClaw unterstützt. NanoClaw über den neuen `/v1/messages` Anthropic-kompatiblen Endpunkt; NemoClaw über OpenShell-Inferenz-Routing. OpenRouter als LLM-Plattform hinzugefügt.
- **[13.03.2026]** **v0.3.1** MinT-Backend-Unterstützung: RL-Training funktioniert jetzt mit Tinker und MinT. Konfigurierbar über `rl.backend` (auto/tinker/mint).
- **[13.03.2026]** **v0.3** Kontinuierliche Meta-Learning-Unterstützung: RL-Gewichtsupdates laufen nur noch während Schlafenszeiten, Leerlaufphasen oder Google-Calendar-Meetings. Support/Query-Set-Trennung hinzugefügt, um veraltete Belohnungssignale von Modell-Updates fernzuhalten.
- **[11.03.2026]** **v0.2** Ein-Klick-Deployment über `metaclaw` CLI. Skills standardmäßig aktiviert, RL jetzt optional.
- **[09.03.2026]** **MetaClaw** veröffentlicht. Sprich einfach mit deinem Agenten und lass ihn automatisch weiterentwickeln. **Kein** GPU-Deployment erforderlich; einfach an die **API** anschließen.

---

## 🎥 Demo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Übersicht

**MetaClaw ist ein Agent, der in realen Einsatzszenarien meta-lernt und sich weiterentwickelt.**
Sprich einfach wie gewohnt mit deinem Agenten. MetaClaw verwandelt jedes Live-Gespräch in ein Lernsignal und ermöglicht dem Agenten, sich durch den realen Einsatz kontinuierlich zu verbessern, statt nur auf Offline-Training zu setzen.

Unter der Haube kapselt es dein Modell hinter einem OpenAI-kompatiblen Proxy (für Anthropic-native Agenten wie NanoClaw wird zusätzlich ein `/v1/messages`-kompatibler Endpunkt bereitgestellt), fängt Interaktionen über OpenClaw, NanoClaw, NemoClaw und andere unterstützte Agenten ab, injiziert relevante Skills bei jedem Schritt und meta-lernt aus den gesammelten Erfahrungen. Nach jeder Session werden Skills automatisch zusammengefasst; mit aktiviertem RL verschiebt ein Meta-Learning-Scheduler die Gewichtsaktualisierungen in inaktive Zeitfenster, damit der Agent während der aktiven Nutzung nie unterbrochen wird.

Kein GPU-Cluster nötig. MetaClaw funktioniert mit jeder OpenAI-kompatiblen LLM-API und nutzt ein Tinker-kompatibles Backend für Cloud-basiertes LoRA-Training. [Tinker](https://www.thinkingmachines.ai/tinker/) ist der Standard-Referenzpfad; bei Bedarf können MinT oder Weaver über separate Kompatibilitätspakete aktiviert werden.

## 🤖 Hauptfunktionen

### **Ein-Klick-Deployment**
Einmal mit `metaclaw setup` konfigurieren, dann startet `metaclaw start` den Proxy, injiziert Skills und verbindet OpenClaw automatisch. Keine manuellen Shell-Skripte nötig.

### **Drei Betriebsmodi**

| Modus | Standard | Funktion |
|-------|---------|----------|
| `skills_only` | | Proxy für deine LLM-API. Skills werden injiziert und nach jeder Session automatisch zusammengefasst. Kein GPU/Tinker erforderlich. |
| `rl` | | Skills + RL-Training (GRPO). Trainiert sofort, wenn ein Batch voll ist. Optional OPD für Lehrer-Destillation. |
| `auto` | ✅ | Skills + RL + Smart-Scheduler. RL-Gewichtsupdates laufen nur in Schlaf-/Leerlauf-/Meeting-Fenstern. |

### **Langzeitgedächtnis**
MetaClaw kann Fakten, Präferenzen und Projektverlauf über Sitzungen hinweg speichern und pro Runde relevanten Kontext einspielen — dein Agent erinnert sich an das, was du gesagt hast, auch Wochen später.

### **Asynchron by Design**
Serving, Reward Modeling und Training sind vollständig entkoppelt. Der Agent antwortet weiterhin, während Bewertung und Optimierung parallel laufen.

---

## 🚀 Schnellstart

### 1. Installation

**OpenClaw (One-Click):** Nutze das Release [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) — führe die Befehle unten aus, dann `metaclaw setup` und `metaclaw start`. Mehr Infos (Windows, Spiegelserver, Konfiguration, Troubleshooting): [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md).

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip** (PyPI oder dieses Repository):

```bash
pip install -e .                        # skills_only-Modus (leichtgewichtig)
pip install -e ".[rl]"                  # + RL-Trainingsunterstützung (torch, transformers, tinker)
pip install -e ".[evolve]"              # + Skill-Evolution via OpenAI-kompatibler LLM
pip install -e ".[scheduler]"           # + Google Calendar Integration für Scheduler
pip install -e ".[rl,evolve,scheduler]" # empfohlen: vollständiges RL + Scheduler-Setup
```
(Freiwillig) WeChat-Integration verwendet das offizielle Plugin @tencent-weixin/openclaw-weixin. MetaClaw installiert es automatisch, wenn WeChat aktiviert ist:

```bash
metaclaw config wechat.enabled true
metaclaw start
```

Das Plugin wird beim Starten von MetaClaw automatisch installiert. Du kannst es auch manuell installieren:

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

Um WeChat-Konten zu wechseln (mit neuem QR-Code erneut anmelden):

```bash
metaclaw start --wechat-relogin
```

Wenn du `rl.backend=mint` verwenden willst, installiere das MinT-Kompatibilitätspaket separat in derselben Umgebung, zum Beispiel [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). Für `rl.backend=weaver` installiere separat [`nex-weaver`](https://github.com/nex-agi/weaver). MetaClaw hält diese Abhängigkeiten absichtlich aus dem Standardpaket heraus, damit RL-Nutzer Tinker, MinT oder Weaver explizit wählen können.

### 2. Konfiguration

```bash
metaclaw setup
```

Der interaktive Assistent führt dich durch:
1. **Persönlichen Agenten wählen** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` oder `none` (MetaClaw konfiguriert ihn beim Start automatisch)
2. **LLM-Anbieter wählen** — Kimi, Qwen, OpenAI, Volcano Engine oder benutzerdefiniert
3. **API-Schlüssel eingeben** und optional RL-Training aktivieren

Der RL-Pfad von MetaClaw kann explizit zwischen `tinker`, `mint` und `weaver` wechseln. `auto` ist die empfohlene Voreinstellung und kann MinT oder Weaver weiterhin aus den entsprechenden Credentials oder Base-URLs ableiten, wenn die Pakete installiert sind.

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

Die Legacy-Aliase `rl.tinker_api_key` und `rl.tinker_base_url` werden weiterhin aus Kompatibilitätsgründen akzeptiert.

### 3. Start

```bash
metaclaw start
```

Das war's. MetaClaw startet den Proxy, konfiguriert OpenClaw automatisch und startet das Gateway neu. Öffne OpenClaw und beginne zu chatten. Skills werden bei jedem Schritt injiziert, und die Session wird automatisch zu neuen Skills zusammengefasst, wenn du fertig bist.

---

## ⚙️ Konfiguration

Die Konfiguration liegt in `~/.metaclaw/config.yaml`, erstellt durch `metaclaw setup`.

**CLI-Befehle:**

```
metaclaw setup                  # Interaktiver Erstkonfigurations-Assistent
metaclaw start                  # MetaClaw starten (Standard: Auto-Modus)
metaclaw start --mode rl        # RL-Modus für diese Session erzwingen (ohne Scheduler)
metaclaw start --mode skills_only  # Nur-Skills-Modus für diese Session erzwingen
metaclaw stop                   # Laufende MetaClaw-Instanz stoppen
metaclaw status                 # Proxy-Status, laufenden Modus und Scheduler prüfen
metaclaw config show            # Aktuelle Konfiguration anzeigen
metaclaw config KEY VALUE       # Konfigurationswert setzen
metaclaw config llm.oauth_token TOKEN               # OAuth-Token fuer den aktuellen CLI-Anbieter speichern
metaclaw auth paste-token --provider anthropic      # OAuth-Token speichern (anthropic | openai-codex | gemini)
metaclaw auth status                                # Alle gespeicherten Authentifizierungsprofile anzeigen
metaclaw uninstall              # Alle MetaClaw-Daten, OpenClaw-Erweiterung und pip-Paket entfernen
```

Verwenden Sie `metaclaw status` zur Überprüfung der Bereitschaft und `metaclaw stop` zum Stoppen des Prozesses.

<details>
<summary><b>Vollständige Konfigurationsreferenz (zum Aufklappen klicken)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # oauth_token-Beispiel (Token gespeichert via `metaclaw auth paste-token`):
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

proxy:
  port: 30000
  api_key: ""              # optionales Bearer-Token für den lokalen MetaClaw-Proxy

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # deine Skill-Bibliothek
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # Obergrenze für aufgabenspezifische Skills (Standard 10)
  auto_evolve: true         # Skills nach jeder Session automatisch zusammenfassen

rl:
  enabled: false            # auf true setzen, um RL-Training zu aktivieren
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # optionaler Backend-Endpunkt, z.B. https://mint.macaron.xin/ für MinT oder https://weaver-console.nex-agi.cn für Weaver
  tinker_api_key: ""        # Legacy-Alias für api_key
  tinker_base_url: ""       # Legacy-Alias für base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # optionaler Checkpoint-Pfad zum Fortsetzen des Trainings
  evolver_api_base: ""      # leer lassen, um llm.api_base wiederzuverwenden
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # auf true setzen, um OPD (Lehrer-Destillation) zu aktivieren
  teacher_url: ""           # Basis-URL des Lehrermodells (OpenAI-kompatibles /v1/completions)
  teacher_model: ""         # Name des Lehrermodells (z.B. Qwen/Qwen3-32B)
  teacher_api_key: ""       # API-Schlüssel des Lehrermodells
  kl_penalty_coef: 1.0      # KL-Strafkoeffizient für OPD

max_context_tokens: 20000   # Obergrenze für Prompt-Tokens vor Trunkierung; 0 = keine Trunkierung
                            # (empfohlen in skills_only mit großen Cloud-Modellen)
context_window: 0           # dem Agenten gemeldetes Kontextfenster (z. B. OpenClaw-Kompaktierungsschwelle);
                            # 0 = auto (ca. 200 000 in skills_only, 32 768 in rl/auto)

scheduler:                  # v0.3: Meta-Learning-Scheduler (auto-aktiviert im Auto-Modus)
  enabled: false            # Auto-Modus aktiviert automatisch; für RL-Modus manuell setzen
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

## 💪 Skills-Modus

**`metaclaw start --mode skills_only`**

Der leichteste Modus. Kein GPU, kein RL-Backend nötig. MetaClaw kapselt dein LLM hinter einem Proxy, der bei jedem Schritt relevante Skills injiziert und nach jedem Gespräch automatisch neue Skills zusammenfasst.

Für benutzerdefinierte OpenAI-kompatible Anbieter setze `llm.api_base` auf die vollständige Chat-API-Basis (meist mit `/v1`, z. B. `https://your-gateway.example/v1`). Im Modus `skills_only` nutzt MetaClaw denselben Endpunkt für Prompt-Kompression und zugehörige Hilfs-LLM-Aufrufe, sofern kein separater Evolver-Endpunkt konfiguriert ist.

Skills sind kurze Markdown-Anweisungen in `~/.metaclaw/skills/` als einzelne `SKILL.md`-Dateien. Die Bibliothek wächst automatisch mit der Nutzung.

Um die eingebaute Skill-Bank vorzuladen (40+ Skills für Coding, Security, agentische Aufgaben usw.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL-Modus

**`metaclaw start --mode rl`**

Alles aus dem Skills-Modus, plus kontinuierliches RL-Fine-Tuning aus Live-Gesprächen. Jeder Gesprächszug wird tokenisiert und als Trainingsbeispiel eingereicht. Ein Richter-LLM (PRM) bewertet Antworten asynchron, und ein Tinker-kompatibles Backend (Tinker Cloud, MinT oder Weaver) führt LoRA-Fine-Tuning mit Hot-Swap-Gewichten durch.

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

Ein dediziertes Evolver-LLM extrahiert außerdem neue Skills aus fehlgeschlagenen Episoden und speist sie zurück in die Skill-Bibliothek.

**Programmatisches Rollout** (keine OpenClaw TUI nötig): `openclaw_env_data_dir` auf ein Verzeichnis mit JSONL-Aufgabendateien setzen:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### On-Policy Distillation (OPD)

OPD ist ein optionales Add-on für den RL-Modus. Es destilliert ein größeres Lehrermodell on-policy in den Schüler: Der Schüler generiert Antworten wie gewohnt, und der Lehrer liefert token-weise Log-Wahrscheinlichkeiten für dieselben Antworten. Eine KL-Strafe lenkt den Schüler zur Verteilung des Lehrers hin.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

Das Lehrermodell muss hinter einem OpenAI-kompatiblen `/v1/completions`-Endpunkt (z.B. vLLM, SGLang) betrieben werden. OPD kann mit PRM-Bewertung kombiniert werden, beide laufen asynchron. Siehe `examples/run_conversation_opd.py` und `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 Auto-Modus (Standard)

**`metaclaw start`**

Alles aus dem RL-Modus, plus ein Meta-Learning-Scheduler, der Gewichtsupdates in Benutzer-Inaktivitätsfenster verschiebt, damit der Agent während der aktiven Nutzung nie unterbrochen wird. Dies ist der Standardmodus.

Der RL-Gewichts-Hot-Swap-Schritt pausiert den Agenten für mehrere Minuten. Anstatt sofort zu trainieren, wenn ein Batch voll ist (wie im RL-Modus), wartet der Auto-Modus auf ein geeignetes Zeitfenster.

Drei Bedingungen lösen ein Update-Fenster aus (eine reicht aus):

- **Schlafenszeiten**: konfigurierbarer Start-/Endzeitpunkt (z.B. 23:00 bis 07:00)
- **Tastatur-Inaktivität**: wird nach N Minuten Leerlauf ausgelöst
- **Google-Calendar-Events**: erkennt Meetings, sodass Updates laufen können, während du unterwegs bist

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Optional: Google Calendar Integration
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Wenn der Benutzer während eines Updates zurückkehrt, wird der partielle Batch gespeichert und im nächsten Fenster fortgesetzt.

Jedes `ConversationSample` wird mit einer `skill_generation`-Version getaggt. Wenn die Skill-Evolution die Generation erhöht, wird der RL-Buffer geleert, sodass nur Post-Evolutions-Samples für Gradient-Updates verwendet werden (MAML Support/Query-Set-Trennung).

---

## 🗑️ Deinstallation

```bash
metaclaw uninstall
```

Entfernt alles in einem Schritt: Stoppt die laufende Instanz, bereinigt MetaClaw-Referenzen in `~/.openclaw/openclaw.json`, loescht `~/.openclaw/extensions/metaclaw-openclaw/`, loescht `~/.metaclaw/`, deinstalliert das pip-Paket und startet das OpenClaw-Gateway neu. Vor dem Loeschen wird eine Bestaetigung angefordert.

Nach der Deinstallation das Repository manuell loeschen, falls geklont:

```bash
rm -rf /path/to/MetaClaw
```

---

## 📚 Zitierung

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

## 🙏 Danksagungen

MetaClaw baut auf folgenden Open-Source-Projekten auf:

- [OpenClaw](https://openclaw.ai) - das zentrale Agent-Framework.
- [SkillRL](https://github.com/aiming-lab/SkillRL) - unser skill-erweitertes RL-Framework.
- [Tinker](https://www.thinkingmachines.ai/tinker/) - für Online-RL-Training verwendet.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) - alternatives Backend für Online-RL-Training.
- [Weaver](https://github.com/nex-agi/weaver) - alternatives Backend für Online-RL-Training.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) - Inspiration für unser RL-Design.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) - stellt die Grundlage für unsere Skill-Bank bereit.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) - persönlicher Claude-Agent von qwibitai, verbunden über den `/v1/messages` Anthropic-kompatiblen Endpunkt.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) - NVIDIA OpenShell-Inferenz-Agenten-Plugin.

---

## 📄 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) lizenziert.
