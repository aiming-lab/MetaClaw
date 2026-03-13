<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# Parlez simplement à votre agent — il apprend et *ÉVOLUE*.

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Entièrement_Async-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Sans_cluster_GPU-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Évolution_des_skills-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Déploiement_en_un_clic-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md)

<br/>

[Aperçu](#-aperçu) • [Démarrage rapide](#-démarrage-rapide) • [Référence CLI](#️-référence-cli) • [Configuration](#️-configuration) • [Skills](#-skills) • [Mode RL](#-avancé-mode-rl) • [Mode OPD](#-avancé-mode-opd) • [Planificateur](#-avancé-planificateur-de-méta-apprentissage-v03) • [Citation](#-citation)

</div>

---

<div align="center">

### Deux commandes. C'est tout.
</div>

```bash
metaclaw setup              # assistant de configuration unique
metaclaw start              # par défaut : mode madmax — skills + entraînement RL planifié
metaclaw start --mode rl    # RL sans planificateur (entraîne dès qu'un batch est plein)
metaclaw start --mode skills_only  # skills uniquement, pas de RL (Tinker non requis)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Actualités

- **[13/03/2026]** **v0.3** — Support continu de méta-apprentissage : les mises à jour RL ne s'exécutent que pendant les heures de sommeil, les périodes d'inactivité ou les réunions Google Calendar. Ajout de la séparation support/query pour éviter que des signaux de récompense périmés ne polluent les mises à jour du modèle.
- **[11/03/2026]** **v0.2** — Déploiement en un clic via la CLI `metaclaw`. Les skills sont activés par défaut, le RL est désormais optionnel.
- **[09/03/2026]** Lancement de **MetaClaw** — Parlez simplement à votre agent et laissez-le évoluer automatiquement. **Aucun** déploiement GPU requis ; connectez-vous simplement à l'**API**.

---

## 🎥 Démo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Aperçu

**MetaClaw est un agent qui méta-apprend et évolue en conditions réelles.**
Parlez simplement à votre agent comme d'habitude — MetaClaw transforme chaque conversation en direct en signal d'apprentissage, permettant à l'agent de s'améliorer continuellement en déploiement réel plutôt que par entraînement hors ligne seul.

Sous le capot, il encapsule votre modèle derrière un proxy compatible OpenAI, intercepte les interactions via OpenClaw, injecte les skills pertinents à chaque tour, et méta-apprend à partir de l'expérience accumulée. Les skills sont résumés automatiquement après chaque session ; avec le RL activé, un planificateur de méta-apprentissage reporte les mises à jour des poids aux fenêtres d'inactivité pour ne jamais interrompre l'agent pendant l'utilisation active.

Aucun cluster GPU nécessaire. MetaClaw fonctionne avec n'importe quelle API LLM compatible OpenAI et intègre optionnellement **Kimi-K2.5** (1T MoE) via [Tinker](https://www.thinkingmachines.ai/tinker/) pour l'entraînement LoRA dans le cloud.

## 🤖 Fonctionnalités principales

### **Déploiement en un clic**
Configurez une fois avec `metaclaw setup`, puis `metaclaw start` lance le proxy, injecte les skills et connecte OpenClaw automatiquement. Aucun script shell manuel nécessaire.

### **Trois modes de fonctionnement**

| Mode | Par défaut | Fonctionnement |
|------|-----------|----------------|
| `madmax` | ✅ | RL + planificateur intelligent. Skills toujours actifs ; mises à jour RL uniquement pendant les fenêtres de sommeil/inactivité/réunion. |
| `rl` | — | RL sans planificateur. Entraîne immédiatement quand un batch est plein (comportement v0.2). |
| `skills_only` | — | Proxy → votre API LLM. Skills injectés, résumés automatiquement après chaque session. Pas de GPU/Tinker requis. |

### **Injection de skills**
À chaque tour, MetaClaw récupère les instructions de skills les plus pertinentes et les injecte dans le prompt système de l'agent. Amélioration immédiate du comportement sans réentraînement.

### **Résumé automatique des skills**
Après chaque conversation, le même LLM que vous utilisez déjà analyse la session et distille automatiquement de nouveaux skills. Avec RL activé, un modèle juge dédié extrait les skills des épisodes échoués.

### **Aucun cluster GPU requis**
En mode `skills_only`, seule une connexion réseau est nécessaire. L'entraînement RL est délégué au cloud Tinker.

### **Deux modes d'apprentissage**
MetaClaw supporte les deux :
- **RL (GRPO)** : apprentissage à partir de signaux de feedback implicites
- **Distillation On-Policy (OPD)** : distillation d'un modèle enseignant plus grand dans l'étudiant on-policy

En mode OPD, le modèle étudiant génère des réponses normalement, et le modèle enseignant fournit des log-probabilités par token sur ces mêmes réponses. Les logprobs de l'enseignant sont passés à la fonction de perte (ex. `cispo`) pour que l'étudiant apprenne la distribution de l'enseignant. L'enseignant doit être servi derrière un endpoint `/v1/completions` compatible OpenAI (ex. vLLM, SGLang).

### **Asynchrone par conception**
Le serving, la modélisation des récompenses et l'entraînement sont entièrement découplés. L'agent continue de répondre pendant que le scoring et l'optimisation s'exécutent en parallèle.

---

## 🚀 Démarrage rapide

### 1. Installation

```bash
pip install -e .                        # mode skills_only (léger)
pip install -e ".[rl]"                  # + support d'entraînement RL (torch, transformers, tinker)
pip install -e ".[evolve]"              # + évolution des skills via LLM compatible OpenAI
pip install -e ".[scheduler]"           # + intégration Google Calendar pour le planificateur
pip install -e ".[rl,evolve,scheduler]" # recommandé : configuration complète RL + planificateur
```

### 2. Configuration

```bash
metaclaw setup
```

L'assistant interactif vous demande de choisir votre fournisseur LLM (Kimi, Qwen, MiniMax, ou personnalisé), votre clé API, et d'activer optionnellement l'entraînement RL.

### 3. Démarrage

```bash
metaclaw start
```

C'est tout. MetaClaw démarre le proxy, configure automatiquement OpenClaw et redémarre la passerelle. Ouvrez OpenClaw et commencez à discuter — les skills sont injectés à chaque tour, et la session est automatiquement résumée en nouveaux skills à la fin.

---

## 🛠️ Référence CLI

```
metaclaw setup                  # Assistant de configuration interactif initial
metaclaw start                  # Démarrer MetaClaw (par défaut : mode madmax)
metaclaw start --mode rl        # Forcer le mode RL pour cette session (sans planificateur)
metaclaw start --mode skills_only  # Forcer le mode skills uniquement pour cette session
metaclaw stop                   # Arrêter une instance MetaClaw en cours
metaclaw status                 # Vérifier l'état du proxy, le mode en cours et le planificateur
metaclaw config show            # Afficher la configuration actuelle
metaclaw config KEY VALUE       # Définir une valeur de configuration
```

**Clés de configuration courantes :**

```bash
metaclaw config rl.enabled true           # Activer l'entraînement RL
metaclaw config rl.tinker_api_key sk-...  # Définir la clé Tinker
metaclaw config skills.auto_evolve false  # Désactiver le résumé automatique des skills
metaclaw config proxy.port 31000          # Changer le port du proxy
```

---

## ⚙️ Configuration

La configuration se trouve dans `~/.metaclaw/config.yaml`, créée par `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # votre bibliothèque de skills
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # limite des skills spécifiques à la tâche (par défaut 10)
  auto_evolve: true         # résumer automatiquement les skills après chaque session

rl:
  enabled: false            # mettre à true pour activer l'entraînement RL
  model: moonshotai/Kimi-K2.5
  tinker_api_key: ""
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # chemin de checkpoint optionnel pour reprendre l'entraînement
  evolver_api_base: ""      # laisser vide pour réutiliser llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # mettre à true pour activer OPD (distillation enseignant)
  teacher_url: ""           # URL de base du modèle enseignant (OpenAI-compatible /v1/completions)
  teacher_model: ""         # nom du modèle enseignant (ex. Qwen/Qwen3-32B)
  teacher_api_key: ""       # clé API du modèle enseignant
  kl_penalty_coef: 1.0      # coefficient de pénalité KL pour OPD

max_context_tokens: 20000   # limite de tokens de prompt avant troncature

scheduler:                  # v0.3 : planificateur de méta-apprentissage (auto-activé en mode madmax)
  enabled: false            # le mode madmax l'active automatiquement ; à définir manuellement pour rl
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

Les skills sont de courtes instructions Markdown injectées dans le prompt système de l'agent à chaque tour. Elles résident dans votre répertoire de skills (`~/.metaclaw/skills/` par défaut), organisées en fichiers `SKILL.md` individuels.

**Le résumé automatique des skills** s'exécute après chaque conversation. Le LLM configuré analyse ce qui s'est passé et génère automatiquement de nouveaux skills. Aucune curation manuelle nécessaire — la bibliothèque grandit avec l'utilisation.

Pour précharger la banque de skills intégrée (40+ skills pour le coding, la sécurité, les tâches agentiques, etc.) :

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Avancé : Mode RL

Activez l'entraînement RL pour affiner continuellement le modèle à partir des conversations en direct :

```bash
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

En mode RL :
- Chaque tour de conversation est tokenisé et soumis comme échantillon d'entraînement
- Un LLM juge (PRM) évalue les réponses de manière asynchrone
- Tinker exécute le fine-tuning LoRA dans le cloud ; les poids mis à jour sont hot-swappés toutes les `batch_size` samples
- Un LLM évolueur dédié extrait de nouveaux skills des épisodes échoués

**Rollout programmatique** (sans TUI OpenClaw) : définissez `openclaw_env_data_dir` sur un répertoire de fichiers JSONL de tâches :

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 Avancé : Mode OPD

La Distillation On-Policy (OPD) vous permet de distiller un modèle enseignant plus grand dans l'étudiant pendant qu'il s'entraîne on-policy. L'étudiant génère des réponses normalement ; l'enseignant fournit des log-probabilités par token sur ces mêmes réponses. Une pénalité KL oriente l'étudiant vers la distribution de l'enseignant.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

L'enseignant doit être servi derrière un endpoint `/v1/completions` compatible OpenAI (ex. vLLM, SGLang). L'OPD peut être combiné avec le scoring PRM — les deux s'exécutent de manière asynchrone.

Consultez `examples/run_conversation_opd.py` pour un exemple programmatique et `scripts/run_openclaw_tinker_opd.sh` pour un script de lancement prêt à l'emploi.

---

## 🧠 Avancé : Planificateur de méta-apprentissage (v0.3)

En mode RL, l'étape de hot-swap des poids met l'agent en pause pendant plusieurs minutes. Le planificateur (activé par défaut en mode madmax) reporte les mises à jour RL aux fenêtres d'inactivité de l'utilisateur pour éviter toute interruption.

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Optionnel : intégration Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Trois conditions déclenchent une fenêtre de mise à jour (une seule suffit) : heures de sommeil configurées, inactivité clavier du système, ou événement Google Calendar en cours. Si l'utilisateur revient en cours de mise à jour, le batch partiel est sauvegardé et repris à la prochaine fenêtre.

Chaque `ConversationSample` est étiqueté avec une version `skill_generation`. Lorsque l'évolution des skills incrémente la génération, le buffer RL est vidé afin que seuls les échantillons post-évolution soient utilisés pour les mises à jour de gradient (séparation support/query MAML).

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

## 🙏 Remerciements

MetaClaw est construit sur les projets open-source suivants :

- [OpenClaw](https://openclaw.ai) — le framework d'agent central.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — notre framework RL augmenté de skills.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — utilisé pour l'entraînement RL en ligne.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — inspiration pour notre conception RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — fournit la base de notre banque de skills.

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
