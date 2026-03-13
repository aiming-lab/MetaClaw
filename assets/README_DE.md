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

[Übersicht](#-übersicht) • [Schnellstart](#-schnellstart) • [CLI-Referenz](#️-cli-referenz) • [Konfiguration](#️-konfiguration) • [Skills](#-skills) • [RL-Modus](#-erweitert-rl-modus) • [OPD-Modus](#-erweitert-opd-modus) • [Zitierung](#-zitierung)

</div>

---

<div align="center">

### Zwei Befehle. Das ist alles.
</div>

```bash
metaclaw setup              # Einmaliger Konfigurationsassistent
metaclaw start              # Skills aktivieren, OpenClaw verbinden — bereit zum Chatten
metaclaw start --mode rl    # Optional: + Live-RL-Training über ein Tinker-kompatibles Backend
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Neuigkeiten

- **[03.10.2026]** **v0.2** — Ein-Klick-Deployment über `metaclaw` CLI. Skills standardmäßig aktiviert, RL jetzt optional.
- **[03.09.2026]** **MetaClaw** veröffentlicht — Sprich einfach mit deinem Agenten und lass ihn automatisch weiterentwickeln. **Kein** GPU-Deployment erforderlich; einfach an die **API** anschließen.

---

## 🎥 Demo

https://github.com/user-attachments/assets/1c2919fc-5612-40f7-bb97-c74ab50619d5

---

## 📖 Übersicht

**MetaClaw verwandelt Live-Gespräche automatisch in kontinuierliche Trainingsdaten.**
Sprich einfach wie gewohnt mit deinem Agenten — MetaClaw kümmert sich im Hintergrund um die Lernschleife.

Es kapselt dein Modell hinter einem OpenAI-kompatiblen Proxy, fängt Interaktionen über OpenClaw ab, injiziert relevante Skills bei jedem Schritt und fasst nach jeder Session automatisch neue Skills zusammen. Optional kann kontinuierliches Fine-Tuning über ein Tinker-kompatibles Cloud-RL-Backend wie Tinker oder MinT aktiviert werden — Gewichte werden hot-geswappt ohne Dienstunterbrechung.

Kein GPU-Cluster nötig. MetaClaw funktioniert mit jeder OpenAI-kompatiblen LLM-API und kann RL-Training an ein Tinker-kompatibles Backend wie [Tinker](https://www.thinkingmachines.ai/tinker/) oder MinT für Cloud-basiertes LoRA-Fine-Tuning anbinden.

## 🤖 Hauptfunktionen

### **Ein-Klick-Deployment**
Einmal mit `metaclaw setup` konfigurieren, dann startet `metaclaw start` den Proxy, injiziert Skills und verbindet OpenClaw automatisch. Keine manuellen Shell-Skripte nötig.

### **Zwei Betriebsmodi**

| Modus | Standard | Funktion |
|-------|---------|----------|
| `skills_only` | ✅ | Proxy → deine LLM-API. Skills werden injiziert und nach jeder Session automatisch zusammengefasst. Kein GPU/Tinker erforderlich. |
| `rl` | aus | Proxy → Tinker-kompatibles Cloud RL. Vollständige Trainingsschleife mit PRM-Bewertung und Skill-Evolution aus Fehlern. |

### **Skill-Injektion**
Bei jedem Schritt ruft MetaClaw die relevantesten Skill-Anweisungen ab und injiziert sie in den System-Prompt des Agenten. Sofortige Verhaltensverbesserung ohne erneutes Training.

### **Automatische Skill-Zusammenfassung**
Nach jedem Gespräch analysiert dasselbe LLM, das du bereits verwendest, die Session und destilliert automatisch neue Skills. Mit aktiviertem RL extrahiert ein dediziertes Richtermodell Skills aus fehlgeschlagenen Episoden.

### **Kein GPU-Cluster erforderlich**
Im `skills_only`-Modus ist nur eine Netzwerkverbindung nötig. RL-Training wird an ein Tinker-kompatibles Cloud-Backend ausgelagert.

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
pip install -e .            # skills_only-Modus (leichtgewichtig)
pip install -e ".[rl]"      # + RL-Trainingsunterstützung (torch, transformers, tinker)
pip install -e ".[evolve]"  # + Skill-Evolution via OpenAI-kompatibler LLM
pip install mindlab-toolkit # + optionales MinT-Kompatibilitäts-Backend
```

`mindlab-toolkit` wird nur benötigt, wenn du `rl.backend=mint` verwenden willst. MinT-Links: [Überblick](https://mint-doc.macaron.im/), [Tinker-Kompatibilität](https://mint-doc.macaron.im/using-the-api/tinker-compatibility), [Modellliste](https://mint-doc.macaron.im/using-the-api/model-lineup), [GitHub](https://github.com/MindLab-Research/mindlab-toolkit).

### 2. Konfiguration

```bash
metaclaw setup
```

Der interaktive Assistent führt dich durch die Auswahl des LLM-Anbieters (Kimi, Qwen oder benutzerdefiniert), API-Schlüssel und optionale RL-Aktivierung.

Der RL-Pfad von MetaClaw behält Tinker als Standard-Referenzbackend. `rl.backend=auto` ist die empfohlene Voreinstellung und kann bei installiertem MinT-Kompatibilitätspaket auch MinT anhand Mint-typischer Credentials oder Base-URLs erkennen. Wenn du denselben Workflow auf MinT richten willst, kannst du Folgendes setzen:

```bash
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-mint-...
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # Festlandchina; sonst https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

Nutze `https://mint-cn.macaron.xin/` für Festlandchina oder `https://mint.macaron.xin/` andernfalls.

Die Legacy-Aliase `rl.tinker_api_key` und `rl.tinker_base_url` werden aus Kompatibilitätsgründen weiterhin akzeptiert.

### 3. Start

```bash
metaclaw start
```

Das war's. MetaClaw startet den Proxy, konfiguriert OpenClaw automatisch und startet das Gateway neu. Öffne OpenClaw und beginne zu chatten — Skills werden bei jedem Schritt injiziert, und die Session wird automatisch zu neuen Skills zusammengefasst, wenn du fertig bist.

---

## 🛠️ CLI-Referenz

```
metaclaw setup              # Interaktiver Erstkonfigurations-Assistent
metaclaw start              # MetaClaw starten (Proxy + optionales RL)
metaclaw start --mode rl    # RL-Modus für diese Session erzwingen
metaclaw stop               # Laufende MetaClaw-Instanz stoppen
metaclaw status             # Proxy-Status und laufenden Modus prüfen
metaclaw config show        # Aktuelle Konfiguration anzeigen
metaclaw config KEY VALUE   # Konfigurationswert setzen
```

**Häufig verwendete Konfigurationsschlüssel:**

```bash
metaclaw config rl.enabled true           # RL-Training aktivieren
metaclaw config rl.backend auto           # auto | tinker | mint
metaclaw config rl.api_key sk-...         # Schlüssel für das RL-Backend setzen
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # MinT-Endpunkt für Festlandchina; sonst https://mint.macaron.xin/
metaclaw config skills.auto_evolve false  # Automatische Skill-Zusammenfassung deaktivieren
metaclaw config proxy.port 31000          # Proxy-Port ändern
```

---

## ⚙️ Konfiguration

Die Konfiguration liegt in `~/.metaclaw/config.yaml`, erstellt durch `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # deine Skill-Bibliothek
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # Obergrenze für aufgabenspezifische Skills (Standard 10)
  auto_evolve: true         # Skills nach jeder Session automatisch zusammenfassen

rl:
  enabled: false            # auf true setzen, um RL-Training zu aktivieren
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # optionaler Backend-Endpunkt, z. B. https://mint-cn.macaron.xin/ (Festlandchina) oder https://mint.macaron.xin/ für MinT
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

max_context_tokens: 20000   # Token-Obergrenze vor Kürzung
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

RL-Training aktivieren, um das Modell kontinuierlich aus Live-Gesprächen feinabzustimmen. Tinker bleibt der Standard-Referenzpfad, und MetaClaw kann denselben Workflow auch auf MinT als Tinker-kompatible Alternative richten:

```bash
metaclaw config rl.enabled true
metaclaw config rl.backend auto
metaclaw config rl.api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

Wenn du denselben Workflow auf MinT ausführen willst, ergänze Backend, Endpunkt und Modell:

```bash
metaclaw config rl.backend mint
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # Festlandchina; sonst https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

Im RL-Modus:
- Jeder Gesprächszug wird tokenisiert und als Trainingsbeispiel eingereicht
- Ein Richter-LLM (PRM) bewertet Antworten asynchron
- Standardmäßig übernimmt Tinker Cloud das LoRA-Fine-Tuning; MetaClaw kann aber auch mit einer kompatiblen Alternative wie MinT arbeiten, und aktualisierte Gewichte werden alle `batch_size` Samples hot-geswappt
- Ein dediziertes Evolver-LLM extrahiert neue Skills aus fehlgeschlagenen Episoden

Wenn du bei Tinker Cloud bleiben willst, nutze `rl.backend=auto` oder `rl.backend=tinker`. Für MinT setze `rl.backend=mint` und konfiguriere den entsprechenden Endpunkt.

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

## 📚 Zitierung

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

## 🙏 Danksagungen

MetaClaw baut auf folgenden Open-Source-Projekten und Kollaborationen auf:

- [OpenClaw](https://openclaw.ai) — das zentrale Agent-Framework.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — unser skill-erweitertes RL-Framework.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — das primäre Referenz-Backend für Online-RL-Training in MetaClaw.
- [MinT](https://mint-doc.macaron.im/) — eine Tinker-kompatible Alternative von [Mind Lab](https://macaron.im/mindlab), verfügbar über [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit); unterstützte Modelle stehen auf der [offiziellen Modellliste](https://mint-doc.macaron.im/using-the-api/model-lineup).
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — Inspiration für unser RL-Design.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — stellt die Grundlage für unsere Skill-Bank bereit.

Die MinT-Kompatibilitätsarbeit in diesem Repository ist ein Ergebnis der Zusammenarbeit zwischen dem MetaClaw-Projektteam und [Mind Lab](https://macaron.im/mindlab). Mind Lab konzentriert sich in dieser Zusammenarbeit vor allem auf Infrastrukturforschung und LoRA-RL-Algorithmusoptimierung.

---

## 📄 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) lizenziert.
