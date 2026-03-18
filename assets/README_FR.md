<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# Parlez simplement a votre agent, il apprend et *EVOLUE*.

<p>Inspire par l'apprentissage du cerveau. Meta-apprenez et faites evoluer votre 🦞 a partir de chaque conversation. Sans GPU. Compatible Kimi, Qwen, Claude, MiniMax, et plus.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Entièrement_Async-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Sans_cluster_GPU-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Évolution_des_skills-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Déploiement_en_un_clic-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇦🇪 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[Apercu](#-aperçu) • [Demarrage rapide](#-démarrage-rapide) • [Configuration](#️-configuration) • [Mode Skills](#-mode-skills) • [Mode RL](#-mode-rl) • [Mode MadMax](#-mode-madmax-par-défaut) • [Citation](#-citation)

</div>

---

<div align="center">

### Deux commandes. C'est tout.
</div>

```bash
metaclaw setup              # assistant de configuration unique
metaclaw start              # par defaut : mode madmax, skills + entrainement RL planifie
metaclaw start --daemon     # executer en arriere-plan, logs -> ~/.metaclaw/metaclaw.log
metaclaw start --daemon --log-file /tmp/metaclaw.log  # chemin de log personnalise
metaclaw start --mode rl    # RL sans planificateur (entraine des qu'un batch est plein)
metaclaw start --mode skills_only  # skills uniquement, pas de RL (Tinker non requis)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Actualites

- **[16/03/2026]** **v0.3.2** Support multi-Claw : IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw et NemoClaw sont desormais supportes aux cotes d'OpenClaw. NanoClaw via le nouvel endpoint compatible Anthropic `/v1/messages` ; NemoClaw via le routage d'inference OpenShell. OpenRouter ajoute comme plateforme LLM.
- **[13/03/2026]** **v0.3.1** Support du backend MinT : l'entrainement RL fonctionne desormais avec Tinker et MinT. Configurable via `rl.backend` (auto/tinker/mint).
- **[13/03/2026]** **v0.3** Support continu de meta-apprentissage : les mises a jour RL ne s'executent que pendant les heures de sommeil, les periodes d'inactivite ou les reunions Google Calendar. Ajout de la separation support/query pour eviter que des signaux de recompense perimes ne polluent les mises a jour du modele.
- **[11/03/2026]** **v0.2** Deploiement en un clic via la CLI `metaclaw`. Les skills sont actives par defaut, le RL est desormais optionnel.
- **[09/03/2026]** Lancement de **MetaClaw**. Parlez simplement a votre agent et laissez-le evoluer automatiquement. **Aucun** deploiement GPU requis, connectez-vous simplement a l'**API**.

---

## 🎥 Demo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Apercu

**MetaClaw est un agent qui meta-apprend et evolue en conditions reelles.**
Parlez simplement a votre agent comme d'habitude. MetaClaw transforme chaque conversation en direct en signal d'apprentissage, permettant a l'agent de s'ameliorer continuellement en deploiement reel plutot que par entrainement hors ligne seul.

Sous le capot, il encapsule votre modele derriere un proxy compatible OpenAI (avec un endpoint `/v1/messages` compatible Anthropic pour les agents comme NanoClaw), intercepte les interactions via OpenClaw, NanoClaw, NemoClaw et autres agents supportes, injecte les skills pertinents a chaque tour, et meta-apprend a partir de l'experience accumulee. Les skills sont resumes automatiquement apres chaque session ; avec le RL active, un planificateur de meta-apprentissage reporte les mises a jour des poids aux fenetres d'inactivite pour ne jamais interrompre l'agent pendant l'utilisation active.

Aucun cluster GPU necessaire. MetaClaw fonctionne avec n'importe quelle API LLM compatible OpenAI et utilise un backend compatible Tinker pour l'entrainement LoRA dans le cloud. [Tinker](https://www.thinkingmachines.ai/tinker/) reste le chemin de reference par defaut ; MinT peut etre active via un paquet de compatibilite separe si necessaire.

## 🤖 Fonctionnalites principales

### **Deploiement en un clic**
Configurez une fois avec `metaclaw setup`, puis `metaclaw start` lance le proxy, injecte les skills et connecte OpenClaw automatiquement. Aucun script shell manuel necessaire.

### **Trois modes de fonctionnement**

| Mode | Par defaut | Fonctionnement |
|------|-----------|----------------|
| `skills_only` | | Proxy vers votre API LLM. Skills injectes, resumes automatiquement apres chaque session. Pas de GPU/Tinker requis. |
| `rl` | | Skills + entrainement RL (GRPO). Entraine immediatement quand un batch est plein. OPD optionnel pour la distillation enseignant. |
| `madmax` | ✅ | Skills + RL + planificateur intelligent. Mises a jour RL uniquement pendant les fenetres de sommeil/inactivite/reunion. |

### **Asynchrone par conception**
Le serving, la modelisation des recompenses et l'entrainement sont entierement decouples. L'agent continue de repondre pendant que le scoring et l'optimisation s'executent en parallele.

---

## 🚀 Demarrage rapide

### 1. Installation

```bash
pip install -e .                        # mode skills_only (leger)
pip install -e ".[rl]"                  # + support d'entrainement RL (torch, transformers, tinker)
pip install -e ".[evolve]"              # + evolution des skills via LLM compatible OpenAI
pip install -e ".[scheduler]"           # + integration Google Calendar pour le planificateur
pip install -e ".[rl,evolve,scheduler]" # recommande : configuration complete RL + planificateur
```

Si vous voulez utiliser `rl.backend=mint`, installez separement le paquet de compatibilite MinT dans le meme environnement, par exemple [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). MetaClaw garde volontairement cette dependance hors du paquet par defaut afin que les utilisateurs RL choisissent explicitement entre Tinker et MinT.

### 2. Configuration

```bash
metaclaw setup
```

L'assistant interactif vous demande de choisir votre fournisseur LLM (Kimi, Qwen, MiniMax, ou personnalise), votre cle API, et d'activer optionnellement l'entrainement RL.

La pile RL de MetaClaw peut basculer explicitement entre `tinker` et `mint`. `auto` est la valeur recommandee et continuera d'inferer MinT a partir d'identifiants ou de base URLs de style Mint lorsque le paquet MinT est installe.

**Tinker** (par défaut) :

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

Les alias herites `rl.tinker_api_key` et `rl.tinker_base_url` restent acceptes pour compatibilite.

### 3. Demarrage

```bash
metaclaw start
```

C'est tout. MetaClaw demarre le proxy, configure automatiquement OpenClaw et redemarre la passerelle. Ouvrez OpenClaw et commencez a discuter. Les skills sont injectes a chaque tour, et la session est automatiquement resumee en nouveaux skills a la fin.

---

## ⚙️ Configuration

La configuration se trouve dans `~/.metaclaw/config.yaml`, creee par `metaclaw setup`.

**Commandes CLI :**

```
metaclaw setup                  # Assistant de configuration interactif initial
metaclaw start                  # Demarrer MetaClaw (par defaut : mode madmax)
metaclaw start --daemon         # Demarrer MetaClaw en arriere-plan
metaclaw start --daemon --log-file /tmp/metaclaw.log  # Chemin de log personnalise
metaclaw start --mode rl        # Forcer le mode RL pour cette session (sans planificateur)
metaclaw start --mode skills_only  # Forcer le mode skills uniquement pour cette session
metaclaw stop                   # Arreter une instance MetaClaw en cours
metaclaw status                 # Verifier l'etat du proxy, le mode en cours et le planificateur
metaclaw config show            # Afficher la configuration actuelle
metaclaw config KEY VALUE       # Definir une valeur de configuration
```

Lorsque vous demarrez MetaClaw avec `--daemon`, la commande attend que le proxy local soit operationnel avant de retourner. Utilisez `metaclaw status` pour verifier l'etat et `metaclaw stop` pour arreter le processus en arriere-plan.

<details>
<summary><b>Reference de configuration complete (cliquez pour developper)</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # jeton bearer optionnel pour le proxy local MetaClaw

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # votre bibliotheque de skills
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # limite des skills specifiques a la tache (par defaut 10)
  auto_evolve: true         # resumer automatiquement les skills apres chaque session

rl:
  enabled: false            # mettre a true pour activer l'entrainement RL
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # endpoint backend optionnel, p. ex. https://mint.macaron.xin/ pour MinT
  tinker_api_key: ""        # alias herite de api_key
  tinker_base_url: ""       # alias herite de base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # chemin de checkpoint optionnel pour reprendre l'entrainement
  evolver_api_base: ""      # laisser vide pour reutiliser llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # mettre a true pour activer OPD (distillation enseignant)
  teacher_url: ""           # URL de base du modele enseignant (OpenAI-compatible /v1/completions)
  teacher_model: ""         # nom du modele enseignant (ex. Qwen/Qwen3-32B)
  teacher_api_key: ""       # cle API du modele enseignant
  kl_penalty_coef: 1.0      # coefficient de penalite KL pour OPD

max_context_tokens: 20000   # limite de tokens de prompt avant troncature

scheduler:                  # v0.3 : planificateur de meta-apprentissage (auto-active en mode madmax)
  enabled: false            # le mode madmax l'active automatiquement ; a definir manuellement pour rl
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

## 💪 Mode Skills

**`metaclaw start --mode skills_only`**

Le mode le plus leger. Pas de GPU, pas de backend RL necessaire. MetaClaw place votre LLM derriere un proxy qui injecte les skills pertinents a chaque tour, puis resume automatiquement de nouveaux skills apres chaque conversation.

Les skills sont de courtes instructions Markdown stockees dans `~/.metaclaw/skills/` sous forme de fichiers `SKILL.md` individuels. La bibliotheque grandit automatiquement avec l'utilisation.

Pour precharger la banque de skills integree (40+ skills pour le coding, la securite, les taches agentiques, etc.) :

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Mode RL

**`metaclaw start --mode rl`**

Tout ce que le Mode Skills offre, plus le fine-tuning RL continu a partir des conversations en direct. Chaque tour de conversation est tokenise et soumis comme echantillon d'entrainement. Un LLM juge (PRM) evalue les reponses de maniere asynchrone, et un backend compatible Tinker (Tinker Cloud ou MinT) execute le fine-tuning LoRA avec hot-swap des poids.

**Tinker** (par défaut) :

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

Un LLM evolueur dedie extrait egalement de nouveaux skills des episodes echoues, les reinjectant dans la bibliotheque de skills.

**Rollout programmatique** (sans TUI OpenClaw) : definissez `openclaw_env_data_dir` sur un repertoire de fichiers JSONL de taches :

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### Distillation On-Policy (OPD)

L'OPD est un complement optionnel du Mode RL. Il distille un modele enseignant plus grand dans l'etudiant on-policy : l'etudiant genere des reponses normalement, et l'enseignant fournit des log-probabilites par token sur ces memes reponses. Une penalite KL oriente l'etudiant vers la distribution de l'enseignant.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

L'enseignant doit etre servi derriere un endpoint `/v1/completions` compatible OpenAI (ex. vLLM, SGLang). L'OPD peut etre combine avec le scoring PRM, les deux s'executent de maniere asynchrone. Consultez `examples/run_conversation_opd.py` et `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 Mode MadMax (par defaut)

**`metaclaw start`**

Tout ce que le Mode RL offre, plus un planificateur de meta-apprentissage qui reporte les mises a jour des poids aux fenetres d'inactivite de l'utilisateur pour eviter toute interruption pendant l'utilisation active. C'est le mode par defaut.

L'etape de hot-swap des poids RL met l'agent en pause pendant plusieurs minutes. Au lieu d'entrainer immediatement quand un batch est plein (comme le fait le Mode RL), MadMax attend une fenetre appropriee.

Trois conditions declenchent une fenetre de mise a jour (une seule suffit) :

- **Heures de sommeil** : heure de debut/fin configurable (ex. 23:00 a 07:00)
- **Inactivite clavier** : se declenche apres N minutes d'inactivite
- **Evenements Google Calendar** : detecte les reunions pour lancer les mises a jour pendant votre absence

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Optionnel : integration Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Si l'utilisateur revient en cours de mise a jour, le batch partiel est sauvegarde et repris a la prochaine fenetre.

Chaque `ConversationSample` est etiquete avec une version `skill_generation`. Lorsque l'evolution des skills incremente la generation, le buffer RL est vide afin que seuls les echantillons post-evolution soient utilises pour les mises a jour de gradient (separation support/query MAML).

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

- [OpenClaw](https://openclaw.ai) le framework d'agent central.
- [SkillRL](https://github.com/aiming-lab/SkillRL) notre framework RL augmente de skills.
- [Tinker](https://www.thinkingmachines.ai/tinker/) utilise pour l'entrainement RL en ligne.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) backend alternatif pour l'entrainement RL en ligne.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) inspiration pour notre conception RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) fournit la base de notre banque de skills.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) agent Claude personnel de qwibitai, connecte via l'endpoint compatible Anthropic `/v1/messages`.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) plugin agent OpenShell de NVIDIA pour l'inference.

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
