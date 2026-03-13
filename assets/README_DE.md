<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# Sprich einfach mit deinem Agenten — er lernt und *ENTWICKELT* sich weiter.

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Vollständig_Async-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Kein_GPU--Cluster-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Skill--Evolution-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Ein--Klick--Deployment-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇪🇸 Español](./README_ES.md)

<br/>

[Übersicht](#-übersicht) • [Schnellstart](#-schnellstart) • [CLI-Referenz](#️-cli-referenz) • [Konfiguration](#️-konfiguration) • [Skills](#-skills) • [RL-Modus](#-erweitert-rl-modus) • [OPD-Modus](#-erweitert-opd-modus) • [Meta-Learning-Scheduler](#-erweitert-meta-learning-scheduler-v03) • [Zitierung](#-zitierung)

</div>

---

<div align="center">

### Zwei Befehle. Das ist alles.
</div>

```bash
metaclaw setup              # Einmaliger Konfigurationsassistent
metaclaw start              # Standard: Auto-Modus — Skills + geplantes RL-Training
metaclaw start --mode rl    # RL ohne Scheduler (trainiert sofort bei vollem Batch)
metaclaw start --mode skills_only  # Nur Skills, kein RL (kein Tinker nötig)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Neuigkeiten

- **[13.03.2026]** **v0.3** — Kontinuierliche Meta-Learning-Unterstützung: RL-Gewichtsupdates laufen nur noch während Schlafenszeiten, Leerlaufphasen oder Google-Calendar-Meetings. Support/Query-Set-Trennung hinzugefügt, um veraltete Belohnungssignale von Modell-Updates fernzuhalten.
- **[11.03.2026]** **v0.2** — Ein-Klick-Deployment über `metaclaw` CLI. Skills standardmäßig aktiviert, RL jetzt optional.
- **[09.03.2026]** **MetaClaw** veröffentlicht — Sprich einfach mit deinem Agenten und lass ihn automatisch weiterentwickeln. **Kein** GPU-Deployment erforderlich; einfach an die **API** anschließen.

---

## 🎥 Demo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Übersicht

**MetaClaw ist ein Agent, der in realen Einsatzszenarien meta-lernt und sich weiterentwickelt.**
Sprich einfach wie gewohnt mit deinem Agenten — MetaClaw verwandelt jedes Live-Gespräch in ein Lernsignal und ermöglicht dem Agenten, sich durch den realen Einsatz kontinuierlich zu verbessern, statt nur auf Offline-Training zu setzen.

Unter der Haube kapselt es dein Modell hinter einem OpenAI-kompatiblen Proxy, fängt Interaktionen über OpenClaw ab, injiziert relevante Skills bei jedem Schritt und meta-lernt aus den gesammelten Erfahrungen. Nach jeder Session werden Skills automatisch zusammengefasst; mit aktiviertem RL verschiebt ein Meta-Learning-Scheduler die Gewichtsaktualisierungen in inaktive Zeitfenster, damit der Agent während der aktiven Nutzung nie unterbrochen wird.

Kein GPU-Cluster nötig. MetaClaw funktioniert mit jeder OpenAI-kompatiblen LLM-API und integriert optional **Kimi-K2.5** (1T MoE) via [Tinker](https://www.thinkingmachines.ai/tinker/) für Cloud-basiertes LoRA-Training.

## 🤖 Hauptfunktionen

### **Ein-Klick-Deployment**
Einmal mit `metaclaw setup` konfigurieren, dann startet `metaclaw start` den Proxy, injiziert Skills und verbindet OpenClaw automatisch. Keine manuellen Shell-Skripte nötig.

### **Drei Betriebsmodi**

| Modus | Standard | Funktion |
|-------|---------|----------|
| `madmax` | ✅ | RL + Smart-Scheduler. Skills immer aktiv; RL-Gewichtsupdates laufen nur in Schlaf-/Leerlauf-/Meeting-Fenstern. |
| `rl` | — | RL ohne Scheduler. Trainiert sofort, wenn ein Batch voll ist (v0.2-Verhalten). |
| `skills_only` | — | Proxy → deine LLM-API. Skills werden injiziert und nach jeder Session automatisch zusammengefasst. Kein GPU/Tinker erforderlich. |

### **Skill-Injektion**
Bei jedem Schritt ruft MetaClaw die relevantesten Skill-Anweisungen ab und injiziert sie in den System-Prompt des Agenten. Sofortige Verhaltensverbesserung ohne erneutes Training.

### **Automatische Skill-Zusammenfassung**
Nach jedem Gespräch analysiert dasselbe LLM, das du bereits verwendest, die Session und destilliert automatisch neue Skills. Mit aktiviertem RL extrahiert ein dediziertes Richtermodell Skills aus fehlgeschlagenen Episoden.

### **Kein GPU-Cluster erforderlich**
Im `skills_only`-Modus ist nur eine Netzwerkverbindung nötig. RL-Training wird an die Tinker Cloud ausgelagert.

### **Zwei Lernmodi**
MetaClaw unterstützt beide:
- **RL (GRPO)**: Lernen aus impliziten Feedbacksignalen
- **On-Policy Distillation (OPD)**: Destillation eines größeren Lehrermodells in das Schülermodell on-policy

Im OPD-Modus generiert das Schülermodell Antworten wie gewohnt, und das Lehrermodell liefert token-weise Log-Wahrscheinlichkeiten für dieselben Antworten. Die Lehrer-Logprobs werden an die Verlustfunktion (z.B. `cispo`) übergeben, damit der Schüler die Verteilung des Lehrers lernt. Das Lehrermodell muss hinter einem OpenAI-kompatiblen `/v1/completions`-Endpunkt (z.B. vLLM, SGLang) betrieben werden.

### **Asynchron by Design**
Serving, Reward Modeling und Training sind vollständig entkoppelt. Der Agent antwortet weiterhin, während Bewertung und Optimierung parallel laufen.

---

## 🚀 Schnellstart

### 1. Installation

```bash
pip install -e .                        # skills_only-Modus (leichtgewichtig)
pip install -e ".[rl]"                  # + RL-Trainingsunterstützung (torch, transformers, tinker)
pip install -e ".[evolve]"              # + Skill-Evolution via OpenAI-kompatibler LLM
pip install -e ".[scheduler]"           # + Google Calendar Integration für Scheduler
pip install -e ".[rl,evolve,scheduler]" # empfohlen: vollständiges RL + Scheduler-Setup
```

### 2. Konfiguration

```bash
metaclaw setup
```

Der interaktive Assistent führt dich durch die Auswahl des LLM-Anbieters (Kimi, Qwen, MiniMax oder benutzerdefiniert), API-Schlüssel und optionale RL-Aktivierung.

### 3. Start

```bash
metaclaw start
```

Das war's. MetaClaw startet den Proxy, konfiguriert OpenClaw automatisch und startet das Gateway neu. Öffne OpenClaw und beginne zu chatten — Skills werden bei jedem Schritt injiziert, und die Session wird automatisch zu neuen Skills zusammengefasst, wenn du fertig bist.

---

## 🛠️ CLI-Referenz

```
metaclaw setup                  # Interaktiver Erstkonfigurations-Assistent
metaclaw start                  # MetaClaw starten (Standard: Auto-Modus)
metaclaw start --mode rl        # RL-Modus für diese Session erzwingen (ohne Scheduler)
metaclaw start --mode skills_only  # Nur-Skills-Modus für diese Session erzwingen
metaclaw stop                   # Laufende MetaClaw-Instanz stoppen
metaclaw status                 # Proxy-Status, laufenden Modus und Scheduler prüfen
metaclaw config show            # Aktuelle Konfiguration anzeigen
metaclaw config KEY VALUE       # Konfigurationswert setzen
```

**Häufig verwendete Konfigurationsschlüssel:**

```bash
metaclaw config rl.enabled true           # RL-Training aktivieren
metaclaw config rl.tinker_api_key sk-...  # Tinker-Schlüssel setzen
metaclaw config skills.auto_evolve false  # Automatische Skill-Zusammenfassung deaktivieren
metaclaw config proxy.port 31000          # Proxy-Port ändern
```

---

## ⚙️ Konfiguration

Die Konfiguration liegt in `~/.metaclaw/config.yaml`, erstellt durch `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # deine Skill-Bibliothek
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # Obergrenze für aufgabenspezifische Skills (Standard 10)
  auto_evolve: true         # Skills nach jeder Session automatisch zusammenfassen

rl:
  enabled: false            # auf true setzen, um RL-Training zu aktivieren
  model: moonshotai/Kimi-K2.5
  tinker_api_key: ""
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

max_context_tokens: 20000   # Token-Obergrenze vor Kürzung

scheduler:                  # v0.3: Meta-Learning-Scheduler (auto-aktiviert im madmax-Modus)
  enabled: false            # madmax-Modus aktiviert automatisch; für rl-Modus manuell setzen
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

Skills sind kurze Markdown-Anweisungen, die bei jedem Schritt in den System-Prompt des Agenten injiziert werden. Sie befinden sich in deinem Skills-Verzeichnis (`~/.metaclaw/skills/` standardmäßig) als einzelne `SKILL.md`-Dateien.

**Automatische Skill-Zusammenfassung** läuft nach jedem Gespräch. Das konfigurierte LLM analysiert, was passiert ist, und generiert automatisch neue Skills. Keine manuelle Pflege nötig — die Bibliothek wächst mit der Nutzung.

Um die eingebaute Skill-Bank vorzuladen (40+ Skills für Coding, Security, agentische Aufgaben usw.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Erweitert: RL-Modus

RL-Training aktivieren, um das Modell kontinuierlich aus Live-Gesprächen feinabzustimmen:

```bash
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

Im RL-Modus:
- Jeder Gesprächszug wird tokenisiert und als Trainingsbeispiel eingereicht
- Ein Richter-LLM (PRM) bewertet Antworten asynchron
- Tinker Cloud führt LoRA-Fine-Tuning durch; aktualisierte Gewichte werden alle `batch_size` Samples hot-geswappt
- Ein dediziertes Evolver-LLM extrahiert neue Skills aus fehlgeschlagenen Episoden

**Programmatisches Rollout** (keine OpenClaw TUI nötig): `openclaw_env_data_dir` auf ein Verzeichnis mit JSONL-Aufgabendateien setzen:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 Erweitert: OPD-Modus

On-Policy Distillation (OPD) ermöglicht die Destillation eines größeren Lehrermodells in den Schüler, während dieser on-policy trainiert. Der Schüler generiert Antworten wie gewohnt; der Lehrer liefert token-weise Log-Wahrscheinlichkeiten für dieselben Antworten. Eine KL-Strafe lenkt den Schüler zur Verteilung des Lehrers hin.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

Das Lehrermodell muss hinter einem OpenAI-kompatiblen `/v1/completions`-Endpunkt (z.B. vLLM, SGLang) betrieben werden. OPD kann mit PRM-Bewertung kombiniert werden — beide laufen asynchron.

Siehe `examples/run_conversation_opd.py` für ein programmatisches Beispiel und `scripts/run_openclaw_tinker_opd.sh` für ein fertiges Startskript.

---

## 🧠 Erweitert: Meta-Learning-Scheduler (v0.3)

Im RL-Modus pausiert der Gewichts-Hot-Swap-Schritt den Agenten für mehrere Minuten. Der Scheduler (im madmax-Modus standardmäßig aktiviert) verschiebt RL-Updates in Benutzer-Inaktivitätsfenster, damit der Agent während der aktiven Nutzung nie unterbrochen wird.

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Optional: Google Calendar Integration
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Drei Bedingungen lösen ein Update-Fenster aus (eine reicht aus): konfigurierte Schlafenszeiten, Tastatur-Inaktivität des Systems oder ein laufendes Google-Calendar-Event. Wenn der Benutzer während eines Updates zurückkehrt, wird der partielle Batch gespeichert und im nächsten Fenster fortgesetzt.

Jedes `ConversationSample` wird mit einer `skill_generation`-Version getaggt. Wenn die Skill-Evolution die Generation erhöht, wird der RL-Buffer geleert, sodass nur Post-Evolutions-Samples für Gradient-Updates verwendet werden (MAML Support/Query-Set-Trennung).

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

- [OpenClaw](https://openclaw.ai) — das zentrale Agent-Framework.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — unser skill-erweitertes RL-Framework.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — für Online-RL-Training verwendet.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — Inspiration für unser RL-Design.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — stellt die Grundlage für unsere Skill-Bank bereit.

---

## 📄 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) lizenziert.
