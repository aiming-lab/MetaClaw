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

[Apercu](#-aperçu) • [Demarrage rapide](#-démarrage-rapide) • [Configuration](#️-configuration) • [Mode Skills](#-mode-skills) • [Mode RL](#-mode-rl) • [Mode Auto](#-mode-auto-par-défaut) • [Citation](#-citation)

</div>

---

<div align="center">

### Deux commandes. C'est tout.
</div>

```bash
metaclaw setup              # assistant de configuration unique
metaclaw start              # par defaut : mode auto, skills + entrainement RL planifie
metaclaw start --mode rl    # RL sans planificateur (entraine des qu'un batch est plein)
metaclaw start --mode skills_only  # skills uniquement, pas de RL (Tinker non requis)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Actualites

- **[19/04/2026]** **v0.4.2** — Integration context-engine OpenClaw : le plugin memoire s'enregistre comme context-engine (cycle assemble/compact) sur OpenClaw v2026.4.10+, eliminant la double injection de memoires. Ajout capture incrementale par tour avec vidage final, section config compatibilite OpenClaw et suppression memoire active pour injection de skills transparente cote proxy.
- **[11/04/2026]** **v0.4.1** — Ingestion memoire incrementale : la couche memoire extrait et persiste desormais les tours tous les N tours (5 par defaut) au lieu d'attendre la fin de la session, reduisant le blackout memoire en cours de session. Ajoute les nouveaux endpoints sidecar `/buffer_turn` et `/flush_session`, un harnais de benchmark avec l'option `--buffer-turns` et des rapports de comparaison d'experiences.
- **[25/03/2026]** **v0.4.0** — Contexture layer : MetaClaw persiste desormais la memoire inter-sessions pour les utilisateurs et les projets. Les faits pertinents, preferences et historiques de projet sont automatiquement recuperes et injectes dans les prompts. Inclut une politique de memoire adaptative, une consolidation en arriere-plan et un service sidecar memoire optionnel.
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

Aucun cluster GPU necessaire. MetaClaw fonctionne avec n'importe quelle API LLM compatible OpenAI et utilise un backend compatible Tinker pour l'entrainement LoRA dans le cloud. [Tinker](https://www.thinkingmachines.ai/tinker/) reste le chemin de reference par defaut ; MinT ou Weaver peuvent etre actives via des paquets de compatibilite separes si necessaire.

## 🤖 Fonctionnalites principales

### **Deploiement en un clic**
Configurez une fois avec `metaclaw setup`, puis `metaclaw start` lance le proxy, injecte les skills et connecte OpenClaw automatiquement. Aucun script shell manuel necessaire.

### **Trois modes de fonctionnement**

| Mode | Par defaut | Fonctionnement |
|------|-----------|----------------|
| `skills_only` | | Proxy vers votre API LLM. Skills injectes, resumes automatiquement apres chaque session. Pas de GPU/Tinker requis. |
| `rl` | | Skills + entrainement RL (GRPO). Entraine immediatement quand un batch est plein. OPD optionnel pour la distillation enseignant. |
| `auto` | ✅ | Skills + RL + planificateur intelligent. Mises a jour RL uniquement pendant les fenetres de sommeil/inactivite/reunion. |

### **Mémoire à long terme**
MetaClaw peut conserver faits, préférences et historique de projet entre les sessions et injecter le contexte pertinent à chaque tour — votre agent se souvient de ce que vous lui avez dit, même des semaines plus tard.

### **Asynchrone par conception**
Le serving, la modelisation des recompenses et l'entrainement sont entierement decouples. L'agent continue de repondre pendant que le scoring et l'optimisation s'executent en parallele.

---

## 🚀 Demarrage rapide

### 1. Installation

**OpenClaw (installation en un clic) :** utilisez la version [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) — exécutez les commandes ci-dessous, puis `metaclaw setup` et `metaclaw start`. Plus de détails (Windows, miroirs, configuration, dépannage) : [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md).

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip** (PyPI ou ce dépôt) :

```bash
pip install -e .                        # mode skills_only (leger)
pip install -e ".[rl]"                  # + support d'entrainement RL (torch, transformers, tinker)
pip install -e ".[evolve]"              # + evolution des skills via LLM compatible OpenAI
pip install -e ".[scheduler]"           # + integration Google Calendar pour le planificateur
pip install -e ".[rl,evolve,scheduler]" # recommande : configuration complete RL + planificateur
```
(Facultatif) L'intégration WeChat utilise le plugin officiel @tencent-weixin/openclaw-weixin. MetaClaw l'installe automatiquement lorsque WeChat est activé :

```bash
metaclaw config wechat.enabled true
metaclaw start
```

Le plugin s'installe automatiquement lors du démarrage de MetaClaw. Vous pouvez également l'installer manuellement :

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

Pour changer de compte WeChat (se reconnecter avec un nouveau code QR) :

```bash
metaclaw start --wechat-relogin
```

Si vous voulez utiliser `rl.backend=mint`, installez separement le paquet de compatibilite MinT dans le meme environnement, par exemple [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). Pour `rl.backend=weaver`, installez separement [`nex-weaver`](https://github.com/nex-agi/weaver). MetaClaw garde volontairement ces dependances hors du paquet par defaut afin que les utilisateurs RL choisissent explicitement entre Tinker, MinT et Weaver.

### 2. Configuration

```bash
metaclaw setup
```

L'assistant interactif vous demandera de :
1. **Choisir votre agent personnel** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` ou `none` (MetaClaw le configurera au démarrage)
2. **Choisir votre fournisseur LLM** — Kimi, Qwen, OpenAI, Volcano Engine ou personnalisé
3. **Saisir votre clé API** et activer éventuellement l'entraînement RL

La pile RL de MetaClaw peut basculer explicitement entre `tinker`, `mint` et `weaver`. `auto` est la valeur recommandee et continuera d'inferer MinT ou Weaver a partir d'identifiants ou de base URLs correspondants lorsque les paquets sont installes.

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

**Weaver**:

```bash
metaclaw config rl.backend weaver
metaclaw config rl.api_key sk-...
metaclaw config rl.base_url https://weaver-console.nex-agi.cn
metaclaw config rl.model Qwen/Qwen3-8B
```

Les alias herites `rl.tinker_api_key` et `rl.tinker_base_url` restent acceptes pour compatibilite.

### 3. Demarrage

```bash
metaclaw start
```

C'est tout. MetaClaw demarre le proxy, configure automatiquement l'agent personnel choisi et redemarre la passerelle. Ouvrez votre agent et conversez — les skills sont injectes a chaque tour et la session est automatiquement resumee en nouveaux skills a la fin.

---

## ⚙️ Configuration

La configuration se trouve dans `~/.metaclaw/config.yaml`, creee par `metaclaw setup`.

**Commandes CLI :**

```
metaclaw setup                  # Assistant de configuration interactif initial
metaclaw start                  # Demarrer MetaClaw (par defaut : mode auto)
metaclaw start --mode rl        # Forcer le mode RL pour cette session (sans planificateur)
metaclaw start --mode skills_only  # Forcer le mode skills uniquement pour cette session
metaclaw stop                   # Arreter une instance MetaClaw en cours
metaclaw status                 # Verifier l'etat du proxy, le mode en cours et le planificateur
metaclaw config show            # Afficher la configuration actuelle
metaclaw config KEY VALUE       # Definir une valeur de configuration
metaclaw config llm.oauth_token TOKEN               # Stocker le token OAuth pour le fournisseur CLI actuel
metaclaw auth paste-token --provider anthropic      # Stocker un token OAuth (anthropic | openai-codex | gemini)
metaclaw auth status                                # Afficher tous les profils d'authentification enregistres
metaclaw uninstall              # Supprimer toutes les donnees MetaClaw, l'extension OpenClaw et le paquet pip
```

Utilisez `metaclaw status` pour verifier la disponibilite et `metaclaw stop` pour arreter le processus.

<details>
<summary><b>Reference de configuration complete (cliquez pour developper)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # exemple oauth_token (token stocke via `metaclaw auth paste-token`) :
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

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
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # endpoint backend optionnel, p. ex. https://mint.macaron.xin/ pour MinT ou https://weaver-console.nex-agi.cn pour Weaver
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

max_context_tokens: 20000   # plafond de tokens de prompt avant troncature ; 0 = pas de troncature
                            # (recommande en skills_only avec grands modeles cloud)
context_window: 0           # fenetre de contexte annoncee a l'agent (p. ex. seuil de compaction OpenClaw) ;
                            # 0 = auto (environ 200 000 en skills_only, 32 768 en rl/auto)

scheduler:                  # v0.3 : planificateur de meta-apprentissage (auto-active en mode auto)
  enabled: false            # le mode auto l'active automatiquement ; a definir manuellement pour rl
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

Pour un fournisseur personnalisé compatible OpenAI, définissez `llm.api_base` sur l'URL de base complète du chat (souvent terminée par `/v1`, par ex. `https://your-gateway.example/v1`). En mode `skills_only`, MetaClaw réutilise ce point de terminaison pour la compression de prompt et les appels LLM auxiliaires, sauf si vous configurez un endpoint evolver séparé.

Les skills sont de courtes instructions Markdown stockees dans `~/.metaclaw/skills/` sous forme de fichiers `SKILL.md` individuels. La bibliotheque grandit automatiquement avec l'utilisation.

Pour precharger la banque de skills integree (40+ skills pour le coding, la securite, les taches agentiques, etc.) :

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Mode RL

**`metaclaw start --mode rl`**

Tout ce que le Mode Skills offre, plus le fine-tuning RL continu a partir des conversations en direct. Chaque tour de conversation est tokenise et soumis comme echantillon d'entrainement. Un LLM juge (PRM) evalue les reponses de maniere asynchrone, et un backend compatible Tinker (Tinker Cloud, MinT ou Weaver) execute le fine-tuning LoRA avec hot-swap des poids.

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

## 🧠 Mode Auto (par defaut)

**`metaclaw start`**

Tout ce que le Mode RL offre, plus un planificateur de meta-apprentissage qui reporte les mises a jour des poids aux fenetres d'inactivite de l'utilisateur pour eviter toute interruption pendant l'utilisation active. C'est le mode par defaut.

L'etape de hot-swap des poids RL met l'agent en pause pendant plusieurs minutes. Au lieu d'entrainer immediatement quand un batch est plein (comme le fait le Mode RL), le mode auto attend une fenetre appropriee.

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

## 🗑️ Desinstallation

```bash
metaclaw uninstall
```

Supprime tout en une seule etape : arrete l'instance en cours, nettoie les references MetaClaw dans `~/.openclaw/openclaw.json`, supprime `~/.openclaw/extensions/metaclaw-openclaw/`, supprime `~/.metaclaw/`, desinstalle le paquet pip et redemarre la passerelle OpenClaw. Une confirmation est demandee avant toute suppression.

Apres la desinstallation, supprimez manuellement le depot si vous l'avez clone :

```bash
rm -rf /path/to/MetaClaw
```

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
- [Weaver](https://github.com/nex-agi/weaver) backend alternatif pour l'entrainement RL en ligne.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) inspiration pour notre conception RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) fournit la base de notre banque de skills.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) agent Claude personnel de qwibitai, connecte via l'endpoint compatible Anthropic `/v1/messages`.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) plugin agent OpenShell de NVIDIA pour l'inference.

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
