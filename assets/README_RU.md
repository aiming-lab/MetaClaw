<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# Просто разговаривайте с вашим агентом, и он будет учиться и *ЭВОЛЮЦИОНИРОВАТЬ*.

<p>Вдохновлено тем, как учится мозг. Мета-обучение и эволюция вашего 🦞 в каждом реальном диалоге. GPU не требуется. Поддерживает Kimi, Qwen, Claude, MiniMax и другие.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Полностью_асинхронно-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Без_GPU_кластера-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Эволюция_навыков-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Развертывание_в_один_клик-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇸🇦 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[Обзор](#-обзор) • [Быстрый старт](#-быстрый-старт) • [Конфигурация](#️-конфигурация) • [Режим навыков](#-режим-навыков) • [Режим RL](#-режим-rl) • [Режим Auto](#-режим-auto-по-умолчанию) • [Цитирование](#-цитирование)

</div>

---

<div align="center">

### Две команды. Это все.
</div>

```bash
metaclaw setup              # одноразовый мастер настройки
metaclaw start              # по умолчанию: режим auto, навыки + плановое RL-обучение
metaclaw start --mode rl    # RL без планировщика (обучение сразу по заполнении batch)
metaclaw start --mode skills_only  # только навыки, без RL (Tinker не нужен)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Новости

- **[19.04.2026]** **v0.4.2** — Интеграция context-engine OpenClaw: плагин памяти регистрируется как context-engine (цикл assemble/compact) в OpenClaw v2026.4.10+, устраняя двойную инъекцию памяти. Добавлена инкрементальная обработка каждого хода с финальным сбросом, секция конфигурации совместимости OpenClaw и подавление активной памяти для прозрачной инъекции навыков на стороне прокси.
- **[11.04.2026]** **v0.4.1** — Инкрементальная загрузка памяти: слой памяти теперь извлекает и сохраняет ходы каждые N ходов (по умолчанию 5), а не только в конце сессии, сокращая «слепую зону» памяти в середине сессии. Добавляет новые sidecar-эндпоинты `/buffer_turn` и `/flush_session`, бенчмарк с флагом `--buffer-turns` и отчёты сравнения экспериментов.
- **[25.03.2026]** **v0.4.0** — Contexture layer: MetaClaw теперь сохраняет память между сессиями для пользователей и проектов. Релевантные факты, предпочтения и история проекта автоматически извлекаются и вставляются в промпты. Включает адаптивную политику памяти, фоновую консолидацию и опциональный сервис sidecar для памяти.
- **[16.03.2026]** **v0.3.2** Поддержка нескольких Claw: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw и NemoClaw теперь поддерживаются наряду с OpenClaw. NanoClaw через новый эндпоинт `/v1/messages`, совместимый с Anthropic; NemoClaw через маршрутизацию инференса OpenShell. Добавлен OpenRouter как поддерживаемая платформа LLM.
- **[13.03.2026]** **v0.3.1** Поддержка бэкенда MinT: RL-обучение теперь работает как с Tinker, так и с MinT. Настраивается через `rl.backend` (auto/tinker/mint).
- **[13.03.2026]** **v0.3** Поддержка непрерывного мета-обучения: медленные RL-обновления запускаются только во время сна, простоя или встреч в Google Calendar. Добавлено разделение на support/query множества для предотвращения загрязнения обновлений модели устаревшими сигналами вознаграждения.
- **[11.03.2026]** **v0.2** Развертывание в один клик через CLI `metaclaw`. Навыки включены по умолчанию, RL теперь опционален.
- **[09.03.2026]** Выпущен **MetaClaw**. Просто общайтесь с агентом, и он будет эволюционировать автоматически. GPU-развертывание **не требуется**, достаточно подключить **API**.

---

## 🎥 Демонстрация

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Обзор

**MetaClaw это агент, который мета-обучается и эволюционирует в реальных условиях.**
Просто общайтесь с агентом, как обычно. MetaClaw превращает каждый живой диалог в обучающий сигнал, позволяя агенту непрерывно совершенствоваться через реальное развертывание, а не только через офлайн-обучение.

Под капотом MetaClaw размещает вашу модель за OpenAI-совместимым прокси (для Anthropic-нативных агентов вроде NanoClaw дополнительно предоставляется `/v1/messages`-совместимый эндпоинт), который перехватывает взаимодействия через OpenClaw, NanoClaw, NemoClaw и другие поддерживаемые агенты, внедряет релевантные навыки на каждом шаге и мета-обучается на накопленном опыте. После каждой сессии навыки автоматически суммируются; при включенном RL планировщик мета-обучения откладывает обновление весов до окон простоя, чтобы агент не прерывался во время активного использования.

GPU-кластер не требуется. MetaClaw работает с любым OpenAI-совместимым LLM API «из коробки» и использует Tinker-совместимый бэкенд для облачного LoRA-дообучения. [Tinker](https://www.thinkingmachines.ai/tinker/) является путем по умолчанию, а MinT или Weaver можно подключить через отдельные пакеты совместимости при необходимости.

## 🤖 Ключевые возможности

### **Развертывание в один клик**
Настройте один раз с помощью `metaclaw setup`, затем `metaclaw start` запускает прокси, внедряет навыки и автоматически подключает OpenClaw. Ручные shell-скрипты не нужны.

### **Три режима работы**

| Режим | По умолчанию | Описание |
|-------|-------------|----------|
| `skills_only` | | Прокси для вашего LLM API. Навыки внедряются, после каждой сессии автоматически суммируются. GPU/Tinker не требуются. |
| `rl` | | Навыки + RL-обучение (GRPO). Обучение запускается сразу при заполнении batch. Опциональный OPD для дистилляции учителя. |
| `auto` | ✅ | Навыки + RL + интеллектуальный планировщик. Обновление весов RL происходит только во время сна/простоя/встреч. |

### **Долговременная память**
MetaClaw может сохранять факты, предпочтения и историю проекта между сессиями и подмешивать релевантный контекст на каждом ходу — ваш агент помнит то, что вы ему сказали, даже через недели.

### **Полностью асинхронная архитектура**
Обслуживание, моделирование вознаграждений и обучение полностью разделены. Агент продолжает отвечать, пока оценка и оптимизация выполняются параллельно.

---

## 🚀 Быстрый старт

### 1. Установка

**OpenClaw (в один клик):** используйте релиз [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) — выполните команды ниже, затем `metaclaw setup` и `metaclaw start`. Подробнее (Windows, зеркала, конфигурация, устранение неполадок): [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md).

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip** (PyPI или этот репозиторий):

```bash
pip install -e .                        # режим skills_only (легковесный)
pip install -e ".[rl]"                  # + поддержка RL-обучения (torch, transformers, tinker)
pip install -e ".[evolve]"              # + эволюция навыков через OpenAI-совместимый LLM
pip install -e ".[scheduler]"           # + интеграция с Google Calendar для планировщика
pip install -e ".[rl,evolve,scheduler]" # рекомендуется для полной конфигурации RL + планировщик
```
(Необязательно) Интеграция WeChat использует официальный плагин @tencent-weixin/openclaw-weixin. MetaClaw автоматически устанавливает его при включении WeChat:

```bash
metaclaw config wechat.enabled true
metaclaw start
```

Плагин устанавливается автоматически при запуске MetaClaw. Вы также можете установить его вручную:

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

Чтобы переключить аккаунты WeChat (переподключитесь с новым QR-кодом):

```bash
metaclaw start --wechat-relogin
```

Если вы хотите использовать `rl.backend=mint`, установите пакет совместимости MinT отдельно в том же окружении, например [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). Для `rl.backend=weaver` отдельно установите [`nex-weaver`](https://github.com/nex-agi/weaver). MetaClaw не включает эти зависимости в пакет по умолчанию, чтобы пользователи RL могли явно выбирать между Tinker, MinT и Weaver.

### 2. Настройка

```bash
metaclaw setup
```

Интерактивный мастер попросит:
1. **Выбрать личного агента** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` или `none` (MetaClaw настроит при запуске)
2. **Выбрать поставщика LLM** — Kimi, Qwen, OpenAI, Volcano Engine или свой
3. **Ввести API-ключ** и при желании включить обучение RL

RL-путь MetaClaw позволяет явно переключаться между `tinker`, `mint` и `weaver`. Рекомендуемое значение по умолчанию: `auto`. При установленных пакетах MinT или Weaver он по-прежнему способен распознать их по соответствующим учётным данным или base URL.

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

Устаревшие псевдонимы `rl.tinker_api_key` и `rl.tinker_base_url` по-прежнему поддерживаются для обратной совместимости.

### 3. Запуск

```bash
metaclaw start
```

Готово. MetaClaw запускает прокси, автоматически настраивает выбранного личного агента и перезапускает шлюз. Откройте агента и общайтесь — навыки подмешиваются каждый ход, а по завершении сессия автоматически суммируется в новые навыки.

---

## ⚙️ Конфигурация

Файл конфигурации находится в `~/.metaclaw/config.yaml` и создается командой `metaclaw setup`.

**Команды CLI:**

```
metaclaw setup                  # Интерактивный мастер первоначальной настройки
metaclaw start                  # Запуск MetaClaw (по умолчанию: режим auto)
metaclaw start --mode rl        # Принудительно включить режим RL (без планировщика) для этой сессии
metaclaw start --mode skills_only  # Принудительно включить режим только навыков для этой сессии
metaclaw stop                   # Остановить работающий экземпляр MetaClaw
metaclaw status                 # Проверить состояние прокси, режим работы и статус планировщика
metaclaw config show            # Просмотр текущей конфигурации
metaclaw config KEY VALUE       # Установить значение конфигурации
metaclaw config llm.oauth_token TOKEN               # Сохранить OAuth-токен для текущего CLI-провайдера
metaclaw auth paste-token --provider anthropic      # Сохранить OAuth-токен (anthropic | openai-codex | gemini)
metaclaw auth status                                # Показать все сохранённые профили аутентификации
metaclaw uninstall              # Удалить все данные MetaClaw, расширение OpenClaw и pip-пакет
```

Используйте `metaclaw status` для проверки готовности и `metaclaw stop` для остановки процесса.

<details>
<summary><b>Полная справка по конфигурации (нажмите, чтобы развернуть)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # пример oauth_token (токен сохраняется через `metaclaw auth paste-token`):
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

proxy:
  port: 30000
  api_key: ""              # необязательный bearer-токен для локального прокси MetaClaw

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # каталог вашей библиотеки навыков
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # лимит навыков для конкретных задач (по умолчанию 10)
  auto_evolve: true         # автоматическое суммирование навыков после каждой сессии

rl:
  enabled: false            # установите true для включения RL-обучения
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # необязательная точка доступа бэкенда, например https://mint.macaron.xin/ для MinT или https://weaver-console.nex-agi.cn для Weaver
  tinker_api_key: ""        # устаревший псевдоним для api_key
  tinker_base_url: ""       # устаревший псевдоним для base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # необязательный путь к контрольной точке для возобновления обучения
  evolver_api_base: ""      # оставьте пустым для использования llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # установите true для включения OPD (дистилляция учителя)
  teacher_url: ""           # base URL модели-учителя (OpenAI-совместимый /v1/completions)
  teacher_model: ""         # имя модели-учителя (например, Qwen/Qwen3-32B)
  teacher_api_key: ""       # API-ключ модели-учителя
  kl_penalty_coef: 1.0      # коэффициент KL-штрафа для OPD

max_context_tokens: 20000   # лимит токенов промпта до усечения; 0 = без усечения
                            # (рекомендуется в skills_only с облачными моделями большого контекста)
context_window: 0           # окно контекста, сообщаемое агенту (напр. порог сжатия OpenClaw);
                            # 0 = авто (≈200 000 в skills_only, 32 768 в rl/auto)

scheduler:                  # v0.3: планировщик мета-обучения (автоматически включается в режиме auto)
  enabled: false            # в режиме auto включается автоматически; для режима rl установите вручную
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

## 💪 Режим навыков

**`metaclaw start --mode skills_only`**

Самый легкий режим. Не требуется ни GPU, ни RL-бэкенд. MetaClaw размещает ваш LLM за прокси, который внедряет релевантные навыки на каждом шаге, а затем автоматически суммирует новые навыки после каждого диалога.

Для своих поставщиков, совместимых с OpenAI, задайте `llm.api_base` как полный базовый URL чата (обычно с `/v1` на конце, например `https://your-gateway.example/v1`). В режиме `skills_only` MetaClaw повторно использует тот же endpoint для сжатия промпта и вспомогательных вызовов LLM, если не задан отдельный endpoint evolver.

Навыки представляют собой короткие Markdown-инструкции, хранящиеся в `~/.metaclaw/skills/` в виде отдельных файлов `SKILL.md`. Библиотека навыков растет автоматически вместе с использованием.

Для предварительной загрузки встроенного банка навыков (более 40 навыков по программированию, безопасности, агентным задачам и др.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Режим RL

**`metaclaw start --mode rl`**

Все возможности режима навыков плюс непрерывное RL-дообучение на основе живых диалогов. Каждый шаг диалога токенизируется и отправляется как обучающий пример. Модель-судья (PRM) асинхронно оценивает ответы, а Tinker-совместимый бэкенд (Tinker cloud, MinT или Weaver) выполняет LoRA-дообучение с горячей заменой весов.

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

Специализированная модель-эволюционер также извлекает новые навыки из неудачных эпизодов и возвращает их в библиотеку навыков.

**Программный rollout** (без TUI OpenClaw): установите `openclaw_env_data_dir` на каталог с JSONL-файлами задач:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### Дистилляция с политикой на лету (OPD)

OPD является опциональным дополнением к режиму RL. Он дистиллирует большую модель-учителя в модель-ученика на его собственной политике: ученик генерирует ответы как обычно, а учитель предоставляет потокенные логарифмические вероятности для тех же ответов. KL-штраф направляет ученика к распределению учителя.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

Учитель должен быть развернут за OpenAI-совместимой точкой доступа `/v1/completions` (например, vLLM, SGLang). OPD можно комбинировать с оценкой PRM, оба процесса выполняются асинхронно. См. `examples/run_conversation_opd.py` и `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 Режим Auto (По умолчанию)

**`metaclaw start`**

Все возможности режима RL плюс планировщик мета-обучения, который откладывает обновление весов до окон неактивности пользователя, чтобы агент не прерывался во время активного использования. Это режим по умолчанию.

Шаг горячей замены весов RL приостанавливает агента на несколько минут. Вместо того чтобы обучаться сразу при заполнении batch (как в режиме RL), режим auto ожидает подходящего окна.

Три условия запускают окно обновления (достаточно любого одного):

- **Часы сна**: настраиваемое время начала/окончания (например, 23:00 до 07:00)
- **Неактивность клавиатуры**: срабатывает после N минут простоя
- **События Google Calendar**: обнаруживает встречи, чтобы обновления выполнялись, пока вы отсутствуете

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Необязательно: интеграция с Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Если пользователь возвращается во время обновления, частичный batch сохраняется и возобновляется в следующем окне.

Каждый `ConversationSample` помечается версией `skill_generation`. Когда эволюция навыков увеличивает поколение, RL-буфер очищается, и для градиентных обновлений используются только пост-эволюционные примеры (разделение MAML support/query множеств).

---

## 🗑️ Удаление

```bash
metaclaw uninstall
```

Удаляет всё за один шаг: останавливает запущенный экземпляр, очищает ссылки на MetaClaw в `~/.openclaw/openclaw.json`, удаляет `~/.openclaw/extensions/metaclaw-openclaw/`, удаляет `~/.metaclaw/`, удаляет pip-пакет и перезапускает шлюз OpenClaw. Перед удалением запрашивается подтверждение.

После удаления вручную удалите репозиторий, если клонировали:

```bash
rm -rf /path/to/MetaClaw
```

---

## 📚 Цитирование

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

## 🙏 Благодарности

MetaClaw построен на основе следующих проектов с открытым исходным кодом:

- [OpenClaw](https://openclaw.ai), основной фреймворк агента.
- [SkillRL](https://github.com/aiming-lab/SkillRL), наш фреймворк RL с расширением навыков.
- [Tinker](https://www.thinkingmachines.ai/tinker/), используется для онлайн RL-обучения.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit), альтернативный бэкенд для онлайн RL-обучения.
- [Weaver](https://github.com/nex-agi/weaver), альтернативный бэкенд для онлайн RL-обучения.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL), вдохновение для нашего дизайна RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills), основа для нашего банка навыков.
- [NanoClaw](https://github.com/qwibitai/nanoclaw), персональный Claude-агент от qwibitai, подключается через `/v1/messages`-совместимый эндпоинт Anthropic.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw), плагин агента OpenShell от NVIDIA для инференса.

---

## 📄 Лицензия

Этот проект распространяется под лицензией [MIT](LICENSE).
