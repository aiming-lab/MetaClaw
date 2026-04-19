<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# Apenas converse com seu agente, ele aprende e *EVOLUI*.

<p>Inspirado em como o cerebro aprende. Meta-aprenda e evolua seu 🦞 a partir de cada conversa real. Sem necessidade de GPU. Compativel com Kimi, Qwen, Claude, MiniMax e mais.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Totalmente_Assíncrono-yellow?style=flat&labelColor=555" alt="Totalmente Assíncrono" />
  <img src="https://img.shields.io/badge/☁️_Sem_Cluster_GPU-blue?style=flat&labelColor=555" alt="Sem Cluster GPU" />
  <img src="https://img.shields.io/badge/🛠️_Evolução_de_Skills-orange?style=flat&labelColor=555" alt="Evolução de Skills" />
  <img src="https://img.shields.io/badge/🚀_Deploy_com_Um_Clique-green?style=flat&labelColor=555" alt="Deploy com Um Clique" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇸🇦 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[Visao Geral](#-visao-geral) • [Inicio Rapido](#-inicio-rapido) • [Configuracao](#️-configuracao) • [Modo Skills](#-modo-skills) • [Modo RL](#-modo-rl) • [Modo Auto](#-modo-auto-padrao) • [Citacao](#-citacao)

</div>

---

<div align="center">

### Dois comandos. So isso.
</div>

```bash
metaclaw setup              # assistente de configuracao inicial
metaclaw start              # padrao: modo auto, Skills + treinamento RL agendado
metaclaw start --mode rl    # RL sem agendador (treina imediatamente com batch completo)
metaclaw start --mode skills_only  # apenas Skills, sem RL (sem necessidade de Tinker)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Novidades

- **[19/04/2026]** **v0.4.2** — Integracao context-engine OpenClaw: o plugin de memoria registra-se como context-engine (ciclo assemble/compact) no OpenClaw v2026.4.10+, eliminando a dupla injeção de memorias. Adiciona captura incremental por turno com flush final, secao de configuracao de compatibilidade OpenClaw e supressao de memoria ativa para injeção de skills no lado do proxy.
- **[11/04/2026]** **v0.4.1** — Ingestao incremental de memoria: a camada de memoria agora extrai e persiste turnos a cada N turnos (padrao 5) em vez de apenas no final da sessao, reduzindo o blackout de memoria no meio da sessao. Adiciona os novos endpoints sidecar `/buffer_turn` e `/flush_session`, um harness de benchmark com a flag `--buffer-turns` e relatorios comparativos de experimentos.
- **[25/03/2026]** **v0.4.0** — Contexture layer: MetaClaw agora persiste a memoria entre sessoes para usuarios e projetos. Fatos relevantes, preferencias e historico do projeto sao recuperados automaticamente e injetados nos prompts. Inclui politica de memoria adaptativa, consolidacao em segundo plano e servico sidecar de memoria opcional.
- **[16/03/2026]** **v0.3.2** Suporte multi-Claw: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw e NemoClaw agora sao suportados junto ao OpenClaw. NanoClaw via novo endpoint compativel com Anthropic `/v1/messages`; NemoClaw via roteamento de inferencia OpenShell. OpenRouter adicionado como plataforma LLM.
- **[13/03/2026]** **v0.3.1** Suporte ao backend MinT: o treinamento RL agora funciona tanto com Tinker quanto com MinT. Configuravel via `rl.backend` (auto/tinker/mint).
- **[13/03/2026]** **v0.3** Suporte a meta-aprendizado continuo: atualizacoes lentas de RL agora so ocorrem durante horarios de sono, tempo ocioso ou reunioes do Google Calendar. Adicionada separacao de conjuntos support/query para evitar que sinais de recompensa obsoletos contaminem as atualizacoes do modelo.
- **[11/03/2026]** **v0.2** Deploy com um clique via CLI `metaclaw`. Skills habilitadas por padrao, RL agora e opcional.
- **[09/03/2026]** Lancamento do **MetaClaw**. Apenas converse com seu agente e deixe-o evoluir automaticamente. **Sem necessidade** de deploy com GPU, basta conectar na **API**.

---

## 🎥 Demonstracao

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Visao Geral

**MetaClaw e um agente que meta-aprende e evolui em cenarios reais.**
Basta conversar com seu agente normalmente. O MetaClaw transforma cada conversa ao vivo em um sinal de aprendizado, permitindo que o agente melhore continuamente por meio de implantacao no mundo real, e nao apenas por treinamento offline.

Internamente, ele posiciona seu modelo atras de um proxy compativel com OpenAI (com endpoint compativel com Anthropic `/v1/messages` para agentes como NanoClaw) que intercepta interacoes do OpenClaw, NanoClaw, NemoClaw e outros agentes suportados, injeta skills relevantes a cada turno e meta-aprende a partir da experiencia acumulada. As skills sao resumidas automaticamente apos cada sessao; com RL habilitado, um agendador de meta-aprendizado adia atualizacoes de pesos para janelas ociosas, garantindo que o agente nunca seja interrompido durante o uso ativo.

Sem necessidade de cluster GPU. O MetaClaw funciona com qualquer API LLM compativel com OpenAI, e utiliza um backend compativel com Tinker para treinamento LoRA na nuvem. O [Tinker](https://www.thinkingmachines.ai/tinker/) e o caminho de referencia padrao, e o MinT ou Weaver podem ser habilitados por meio de pacotes de compatibilidade separados quando necessario.

## 🤖 Funcionalidades Principais

### **Deploy com um clique**
Configure uma vez com `metaclaw setup`, depois `metaclaw start` inicia o proxy, injeta skills e conecta o OpenClaw automaticamente. Sem necessidade de scripts shell manuais.

### **Tres modos de operacao**

| Modo | Padrao | O que faz |
|------|--------|-----------|
| `skills_only` | | Proxy para sua API LLM. Skills injetadas, resumidas automaticamente apos cada sessao. Sem necessidade de GPU/Tinker. |
| `rl` | | Skills + treinamento RL (GRPO). Treina imediatamente quando o batch esta completo. OPD opcional para destilacao do professor. |
| `auto` | ✅ | Skills + RL + agendador inteligente. Atualizacoes de pesos RL ocorrem apenas durante janelas de sono/ociosidade/reuniao. |

### **Memória de longo prazo**
O MetaClaw pode manter fatos, preferências e histórico do projeto entre sessões e injetar contexto relevante a cada turno — para que seu agente lembre do que você disse, mesmo semanas depois.

### **Assincrono por design**
Servico, modelagem de recompensa e treinamento sao totalmente desacoplados. O agente continua respondendo enquanto a pontuacao e a otimizacao ocorrem em paralelo.

---

## 🚀 Inicio Rapido

### 1. Instalacao

**OpenClaw (instalação em um clique):** use o release [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) — execute os comandos abaixo, depois `metaclaw setup` e `metaclaw start`. Mais detalhes (Windows, mirrors, configuração, solução de problemas): [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md).

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip** (PyPI ou este repositório):

```bash
pip install -e .                        # modo skills_only (leve)
pip install -e ".[rl]"                  # + suporte a treinamento RL (torch, transformers, tinker)
pip install -e ".[evolve]"              # + evolucao de skills via LLM compativel com OpenAI
pip install -e ".[scheduler]"           # + integracao com Google Calendar para agendador
pip install -e ".[rl,evolve,scheduler]" # recomendado para configuracao completa RL + agendador
```
(Opcional) A integração WeChat usa o plugin oficial @tencent-weixin/openclaw-weixin. MetaClaw instala automaticamente quando WeChat está habilitado:

```bash
metaclaw config wechat.enabled true
metaclaw start
```

O plugin é instalado automaticamente ao iniciar MetaClaw. Você também pode instalar manualmente:

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

Para alternar contas do WeChat (faça login novamente com um novo código QR):

```bash
metaclaw start --wechat-relogin
```

Se voce deseja usar `rl.backend=mint`, instale o pacote de compatibilidade MinT separadamente no mesmo ambiente, por exemplo [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). Para `rl.backend=weaver`, instale separadamente [`nex-weaver`](https://github.com/nex-agi/weaver). O MetaClaw mantem essas dependencias fora do pacote padrao para que usuarios de RL possam escolher explicitamente entre Tinker, MinT ou Weaver.

### 2. Configuracao

```bash
metaclaw setup
```

O assistente interativo pedirá que você:
1. **Escolha seu agente pessoal** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` ou `none` (o MetaClaw configura ao iniciar)
2. **Escolha o provedor LLM** — Kimi, Qwen, OpenAI, Volcano Engine ou personalizado
3. **Informe sua chave de API** e, opcionalmente, ative o treinamento RL

O caminho de RL do MetaClaw pode alternar explicitamente entre `tinker`, `mint` e `weaver`. O valor padrao recomendado e `auto`, que ainda consegue inferir o MinT ou Weaver a partir de credenciais ou base URLs correspondentes quando os pacotes estao instalados.

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

Os aliases legados `rl.tinker_api_key` e `rl.tinker_base_url` continuam sendo aceitos para compatibilidade retroativa.

### 3. Iniciar

```bash
metaclaw start
```

Pronto. O MetaClaw inicia o proxy, configura automaticamente o agente pessoal escolhido e reinicia o gateway. Abra seu agente e converse — as skills são injetadas a cada turno e a sessão é resumida automaticamente em novas skills ao terminar.

---

## ⚙️ Configuracao

O arquivo de configuracao fica em `~/.metaclaw/config.yaml`, criado por `metaclaw setup`.

**Comandos CLI:**

```
metaclaw setup                  # Assistente interativo de configuracao inicial
metaclaw start                  # Iniciar MetaClaw (padrao: modo auto)
metaclaw start --mode rl        # Forcar modo RL (sem agendador) nesta sessao
metaclaw start --mode skills_only  # Forcar modo apenas Skills nesta sessao
metaclaw stop                   # Parar uma instancia MetaClaw em execucao
metaclaw status                 # Verificar saude do proxy, modo de execucao e estado do agendador
metaclaw config show            # Visualizar configuracao atual
metaclaw config KEY VALUE       # Definir um valor de configuracao
metaclaw config llm.oauth_token TOKEN               # Armazenar token OAuth para o provedor CLI atual
metaclaw auth paste-token --provider anthropic      # Armazenar token OAuth (anthropic | openai-codex | gemini)
metaclaw auth status                                # Exibir todos os perfis de autenticacao armazenados
metaclaw uninstall              # Remover todos os dados MetaClaw, extensao OpenClaw e pacote pip
```

Use `metaclaw status` para verificar a disponibilidade e `metaclaw stop` para parar o processo.

<details>
<summary><b>Referencia completa de configuracao (clique para expandir)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # exemplo oauth_token (token armazenado via `metaclaw auth paste-token`):
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

proxy:
  port: 30000
  api_key: ""              # opcional: bearer token para o proxy local do MetaClaw

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # diretorio da sua biblioteca de skills
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # limite de skills especificas por tarefa (padrao 10)
  auto_evolve: true         # resumir skills automaticamente apos cada sessao

rl:
  enabled: false            # defina como true para habilitar treinamento RL
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # endpoint opcional do backend, ex.: https://mint.macaron.xin/ para MinT ou https://weaver-console.nex-agi.cn para Weaver
  tinker_api_key: ""        # alias legado para api_key
  tinker_base_url: ""       # alias legado para base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # opcional: caminho do checkpoint para retomar treinamento
  evolver_api_base: ""      # deixe vazio para reutilizar llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # defina como true para habilitar OPD (destilacao do professor)
  teacher_url: ""           # URL base do modelo professor (OpenAI compativel /v1/completions)
  teacher_model: ""         # nome do modelo professor (ex.: Qwen/Qwen3-32B)
  teacher_api_key: ""       # chave de API do modelo professor
  kl_penalty_coef: 1.0      # coeficiente de penalidade KL para OPD

max_context_tokens: 20000   # limite de tokens do prompt antes do truncamento; 0 = sem truncar
                            # (recomendado em skills_only com modelos cloud de grande contexto)
context_window: 0           # janela de contexto informada ao agente (ex.: limiar de compactação do OpenClaw);
                            # 0 = auto (≈200 000 em skills_only, 32 768 em rl/auto)

scheduler:                  # v0.3: agendador de meta-aprendizado (habilitado automaticamente no modo auto)
  enabled: false            # modo auto habilita automaticamente; defina manualmente para modo rl
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

## 💪 Modo Skills

**`metaclaw start --mode skills_only`**

O modo mais leve. Sem GPU, sem backend RL necessario. O MetaClaw posiciona seu LLM atras de um proxy que injeta skills relevantes a cada turno e resume novas skills automaticamente apos cada conversa.

Para provedores personalizados compatíveis com OpenAI, defina `llm.api_base` com a URL base completa do chat (geralmente terminando em `/v1`, por exemplo `https://your-gateway.example/v1`). No modo `skills_only`, o MetaClaw reutiliza o mesmo endpoint para compressão de prompt e chamadas auxiliares ao LLM, salvo se configurar um endpoint evolver separado.

Skills sao instrucoes curtas em Markdown armazenadas em `~/.metaclaw/skills/` como arquivos `SKILL.md` individuais. A biblioteca cresce automaticamente com o uso.

Para pre-carregar o banco de skills integrado (mais de 40 skills em codificacao, seguranca, tarefas de agente, etc.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Modo RL

**`metaclaw start --mode rl`**

Tudo do Modo Skills, mais fine-tuning RL continuo a partir de conversas ao vivo. Cada turno de conversa e tokenizado e submetido como amostra de treinamento. Um LLM juiz (PRM) pontua respostas de forma assincrona, e um backend compativel com Tinker (Tinker cloud, MinT ou Weaver) executa fine-tuning LoRA com troca a quente de pesos.

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

Um LLM evoluidor dedicado tambem extrai novas skills de episodios que falharam, alimentando-as de volta na biblioteca de skills.

**Rollout programatico** (sem necessidade de TUI OpenClaw): defina `openclaw_env_data_dir` para um diretorio de arquivos JSONL de tarefas:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### Destilacao On-Policy (OPD)

OPD e um complemento opcional para o Modo RL. Ele destila um modelo professor maior para o aluno on-policy: o aluno gera respostas normalmente, e o professor fornece log-probabilidades por token nas mesmas respostas. Uma penalidade KL direciona o aluno para a distribuicao do professor.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

O professor deve estar servido atras de um endpoint `/v1/completions` compativel com OpenAI (ex.: vLLM, SGLang). OPD pode ser combinado com pontuacao PRM, ambos executam de forma assincrona. Consulte `examples/run_conversation_opd.py` e `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 Modo Auto (Padrao)

**`metaclaw start`**

Tudo do Modo RL, mais um agendador de meta-aprendizado que adia atualizacoes de pesos para janelas de inatividade do usuario, garantindo que o agente nunca seja interrompido durante o uso ativo. Este e o modo padrao.

A etapa de troca a quente de pesos RL pausa o agente por varios minutos. Em vez de treinar imediatamente quando o batch esta completo (como o Modo RL faz), o modo auto aguarda uma janela apropriada.

Tres condicoes acionam uma janela de atualizacao (qualquer uma e suficiente):

- **Horarios de sono**: horario de inicio/fim configuravel (ex.: 23:00 a 07:00)
- **Inatividade do teclado**: aciona apos N minutos de tempo ocioso
- **Eventos do Google Calendar**: detecta reunioes para que atualizacoes ocorram enquanto voce esta ausente

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Opcional: integracao com Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Se o usuario retornar durante uma atualizacao, o batch parcial e salvo e retomado na proxima janela.

Cada `ConversationSample` e marcado com uma versao `skill_generation`. Quando a evolucao de skills incrementa a geracao, o buffer RL e esvaziado para que apenas amostras pos-evolucao sejam usadas nas atualizacoes de gradiente (separacao de conjuntos support/query MAML).

---

## 🗑️ Desinstalacao

```bash
metaclaw uninstall
```

Remove tudo de uma so vez: para a instancia em execucao, limpa as referencias do MetaClaw em `~/.openclaw/openclaw.json`, exclui `~/.openclaw/extensions/metaclaw-openclaw/`, exclui `~/.metaclaw/`, desinstala o pacote pip e reinicia o gateway OpenClaw. Uma confirmacao e solicitada antes de qualquer exclusao.

Apos a desinstalacao, remova manualmente o repositorio se o clonou:

```bash
rm -rf /path/to/MetaClaw
```

---

## 📚 Citacao

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

## 🙏 Agradecimentos

O MetaClaw e construido sobre os seguintes projetos de codigo aberto:

- [OpenClaw](https://openclaw.ai), o framework de agente principal.
- [SkillRL](https://github.com/aiming-lab/SkillRL), nosso framework de RL aprimorado com skills.
- [Tinker](https://www.thinkingmachines.ai/tinker/), usado para treinamento RL online.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit), backend alternativo para treinamento RL online.
- [Weaver](https://github.com/nex-agi/weaver), backend alternativo para treinamento RL online.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL), inspiracao para nosso design de RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills), fornece a base para nosso banco de skills.
- [NanoClaw](https://github.com/qwibitai/nanoclaw), agente Claude pessoal da qwibitai, conectado via endpoint compativel com Anthropic `/v1/messages`.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw), plugin de agente OpenShell da NVIDIA para inferencia.

---

## 📄 Licenca

Este projeto e licenciado sob a [Licenca MIT](LICENSE).
