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

[Aperçu](#-aperçu) • [Démarrage rapide](#-démarrage-rapide) • [Référence CLI](#️-référence-cli) • [Configuration](#️-configuration) • [Skills](#-skills) • [Mode RL](#-avancé-mode-rl) • [Mode OPD](#-avancé-mode-opd) • [Citation](#-citation)

</div>

---

<div align="center">

### Deux commandes. C'est tout.
</div>

```bash
metaclaw setup              # assistant de configuration unique
metaclaw start              # skills activés, OpenClaw connecté — prêt à discuter
metaclaw start --mode rl    # optionnel : + entraînement RL en direct via un backend compatible Tinker
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Actualités

- **[10/03/2026]** **v0.2** — Déploiement en un clic via la CLI `metaclaw`. Les skills sont activés par défaut, le RL est désormais optionnel.
- **[09/03/2026]** Lancement de **MetaClaw** — Parlez simplement à votre agent et laissez-le évoluer automatiquement. **Aucun** déploiement GPU requis ; connectez-vous simplement à l'**API**.

---

## 🎥 Démo

https://github.com/user-attachments/assets/1c2919fc-5612-40f7-bb97-c74ab50619d5

---

## 📖 Aperçu

**MetaClaw transforme automatiquement les conversations en direct en données d'entraînement continues.**
Parlez simplement à votre agent comme d'habitude, et MetaClaw gère la boucle d'apprentissage en coulisses.

Il encapsule votre modèle derrière un proxy compatible OpenAI, intercepte les interactions via OpenClaw, injecte les skills pertinents à chaque tour, et résume automatiquement de nouveaux skills après chaque session. Activez optionnellement un fine-tuning continu via un backend RL cloud compatible Tinker, comme Tinker ou MinT, avec hot-swap des poids sans interruption de service.

Aucun cluster GPU nécessaire. MetaClaw fonctionne avec n'importe quelle API LLM compatible OpenAI et peut connecter l'entraînement RL à un backend compatible Tinker comme [Tinker](https://www.thinkingmachines.ai/tinker/) ou MinT pour du fine-tuning LoRA dans le cloud.

## 🤖 Fonctionnalités principales

### **Déploiement en un clic**
Configurez une fois avec `metaclaw setup`, puis `metaclaw start` lance le proxy, injecte les skills et connecte OpenClaw automatiquement. Aucun script shell manuel nécessaire.

### **Deux modes de fonctionnement**

| Mode | Par défaut | Fonctionnement |
|------|-----------|----------------|
| `skills_only` | ✅ | Proxy → votre API LLM. Skills injectés, résumés automatiquement après chaque session. Pas de GPU/Tinker requis. |
| `rl` | désactivé | Proxy → RL cloud compatible Tinker. Boucle d'entraînement complète avec scoring PRM et évolution des skills. |

### **Injection de skills**
À chaque tour, MetaClaw récupère les instructions de skills les plus pertinentes et les injecte dans le prompt système de l'agent. Amélioration immédiate du comportement sans réentraînement.

### **Résumé automatique des skills**
Après chaque conversation, le même LLM que vous utilisez déjà analyse la session et distille automatiquement de nouveaux skills. Avec RL activé, un modèle juge dédié extrait les skills des épisodes échoués.

### **Aucun cluster GPU requis**
En mode `skills_only`, seule une connexion réseau est nécessaire. L'entraînement RL est délégué à un backend cloud compatible Tinker.

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
pip install -e .            # mode skills_only (léger)
pip install -e ".[rl]"      # + support d'entraînement RL (torch, transformers, tinker)
pip install -e ".[evolve]"  # + évolution des skills via LLM compatible OpenAI
pip install mindlab-toolkit # + backend de compatibilité MinT optionnel
```

`mindlab-toolkit` n'est nécessaire que si vous voulez utiliser `rl.backend=mint`. Liens MinT : [aperçu](https://mint-doc.macaron.im/), [compatibilité Tinker](https://mint-doc.macaron.im/using-the-api/tinker-compatibility), [liste des modèles](https://mint-doc.macaron.im/using-the-api/model-lineup), [GitHub](https://github.com/MindLab-Research/mindlab-toolkit).

### 2. Configuration

```bash
metaclaw setup
```

L'assistant interactif vous demande de choisir votre fournisseur LLM (Kimi, Qwen, ou personnalisé), votre clé API, et d'activer optionnellement l'entraînement RL.

La pile RL de MetaClaw garde Tinker comme backend de référence par défaut. `rl.backend=auto` est la valeur recommandée et peut aussi détecter MinT à partir d'identifiants ou de base URLs de style Mint quand le paquet de compatibilité MinT est installé. Si vous voulez pointer le même workflow vers MinT, vous pouvez configurer :

```bash
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-mint-...
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # Chine continentale ; sinon https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

Utilisez `https://mint-cn.macaron.xin/` pour la Chine continentale ou `https://mint.macaron.xin/` sinon.

Les alias hérités `rl.tinker_api_key` et `rl.tinker_base_url` restent acceptés pour compatibilité.

### 3. Démarrage

```bash
metaclaw start
```

C'est tout. MetaClaw démarre le proxy, configure automatiquement OpenClaw et redémarre la passerelle. Ouvrez OpenClaw et commencez à discuter — les skills sont injectés à chaque tour, et la session est automatiquement résumée en nouveaux skills à la fin.

---

## 🛠️ Référence CLI

```
metaclaw setup              # Assistant de configuration interactif initial
metaclaw start              # Démarrer MetaClaw (proxy + RL optionnel)
metaclaw start --mode rl    # Forcer le mode RL pour cette session
metaclaw stop               # Arrêter une instance MetaClaw en cours
metaclaw status             # Vérifier l'état du proxy et le mode en cours
metaclaw config show        # Afficher la configuration actuelle
metaclaw config KEY VALUE   # Définir une valeur de configuration
```

**Clés de configuration courantes :**

```bash
metaclaw config rl.enabled true           # Activer l'entraînement RL
metaclaw config rl.backend auto           # auto | tinker | mint
metaclaw config rl.api_key sk-...         # Définir la clé du backend RL
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # Endpoint MinT pour la Chine continentale ; sinon https://mint.macaron.xin/
metaclaw config skills.auto_evolve false  # Désactiver le résumé automatique des skills
metaclaw config proxy.port 31000          # Changer le port du proxy
```

---

## ⚙️ Configuration

La configuration se trouve dans `~/.metaclaw/config.yaml`, créée par `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # votre bibliothèque de skills
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # limite des skills spécifiques à la tâche (par défaut 10)
  auto_evolve: true         # résumer automatiquement les skills après chaque session

rl:
  enabled: false            # mettre à true pour activer l'entraînement RL
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # endpoint backend optionnel, par ex. https://mint-cn.macaron.xin/ (Chine continentale) ou https://mint.macaron.xin/ pour MinT
  tinker_api_key: ""        # alias hérité de api_key
  tinker_base_url: ""       # alias hérité de base_url
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

Activez l'entraînement RL pour affiner continuellement le modèle à partir des conversations en direct. Tinker reste le chemin de référence par défaut, et MetaClaw peut aussi viser MinT comme alternative compatible Tinker :

```bash
metaclaw config rl.enabled true
metaclaw config rl.backend auto
metaclaw config rl.api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

Si vous voulez exécuter le même workflow sur MinT, ajoutez le backend, l'endpoint et le modèle :

```bash
metaclaw config rl.backend mint
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # Chine continentale ; sinon https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

En mode RL :
- Chaque tour de conversation est tokenisé et soumis comme échantillon d'entraînement
- Un LLM juge (PRM) évalue les réponses de manière asynchrone
- Par défaut, Tinker Cloud exécute le fine-tuning LoRA ; MetaClaw peut aussi fonctionner avec une alternative compatible comme MinT, et les poids mis à jour sont hot-swappés toutes les `batch_size` samples
- Un LLM évolueur dédié extrait de nouveaux skills des épisodes échoués

Si vous restez sur Tinker Cloud, gardez `rl.backend=auto` ou utilisez `rl.backend=tinker`. Si vous utilisez MinT, passez à `rl.backend=mint` et indiquez l'endpoint correspondant.

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

## 🙏 Remerciements

MetaClaw est construit sur les projets open-source et collaborations suivants :

- [OpenClaw](https://openclaw.ai) — le framework d'agent central.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — notre framework RL augmenté de skills.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — le backend de référence principal pour l'entraînement RL en ligne dans MetaClaw.
- [MinT](https://mint-doc.macaron.im/) — une alternative compatible Tinker proposée par [Mind Lab](https://macaron.im/mindlab), disponible via [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit) ; les modèles pris en charge sont listés sur la [page officielle](https://mint-doc.macaron.im/using-the-api/model-lineup).
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — inspiration pour notre conception RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — fournit la base de notre banque de skills.

Le travail de compatibilité MinT dans ce dépôt est l'un des résultats d'une collaboration entre l'équipe du projet MetaClaw et [Mind Lab](https://macaron.im/mindlab). Dans cette collaboration, Mind Lab s'est concentré sur la recherche infra et l'optimisation des algorithmes LoRA RL.

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
