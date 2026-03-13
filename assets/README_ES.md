<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# Habla con tu agente — aprende y *EVOLUCIONA*.

<p>Inspirado en cómo aprende el cerebro. Meta-aprende y evoluciona tu 🦞 con cada conversación. Sin GPU. Compatible con Kimi, Qwen, Claude, MiniMax y más.</p>

<table>
<tr>
<td align="center" width="100">
  <a href="https://kimi.ai">
    <img src="https://github.com/MoonshotAI.png?size=200" width="48" height="48" alt="Kimi" />
  </a><br/>
  <sub><a href="https://kimi.ai"><b>Kimi</b></a></sub>
</td>
<td align="center" width="100">
  <a href="https://qwen.ai">
    <img src="https://github.com/QwenLM.png?size=200" width="48" height="48" alt="Qwen" />
  </a><br/>
  <sub><a href="https://qwen.ai"><b>Qwen</b></a></sub>
</td>
<td align="center" width="100">
  <a href="https://www.anthropic.com/claude">
    <img src="https://cdn.simpleicons.org/claude/D97757" width="48" height="48" alt="Claude" />
  </a><br/>
  <sub><a href="https://www.anthropic.com/claude"><b>Claude</b></a></sub>
</td>
<td align="center" width="100">
  <a href="https://www.minimax.io">
    <img src="https://github.com/minimax-ai.png?size=200" width="48" height="48" alt="MiniMax" />
  </a><br/>
  <sub><a href="https://www.minimax.io"><b>MiniMax</b></a></sub>
</td>
<td align="center" width="100">
  <a href="https://openai.com">
    <img src="https://github.com/openai.png?size=200" width="48" height="48" alt="OpenAI" />
  </a><br/>
  <sub><a href="https://openai.com"><b>OpenAI</b></a></sub>
</td>
<td align="center" width="100">
  <a href="https://gemini.google.com">
    <img src="https://github.com/google-gemini.png?size=200" width="48" height="48" alt="Gemini" />
  </a><br/>
  <sub><a href="https://gemini.google.com"><b>Gemini</b></a></sub>
</td>
<td align="center" width="100">
  <sub><b>+ Much<br/>More</b></sub>
</td>
</tr>
</table>

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Totalmente_Asíncrono-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Sin_cluster_GPU-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Evolución_de_skills-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Despliegue_en_un_clic-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md)

<br/>

[Descripción](#-descripción) • [Inicio rápido](#-inicio-rápido) • [Referencia CLI](#️-referencia-cli) • [Configuración](#️-configuración) • [Skills](#-skills) • [Modo RL](#-avanzado-modo-rl) • [Modo OPD](#-avanzado-modo-opd) • [Planificador](#-avanzado-planificador-de-meta-aprendizaje-v03) • [Cita](#-cita)

</div>

---

<div align="center">

### Dos comandos. Eso es todo.
</div>

```bash
metaclaw setup              # asistente de configuración inicial
metaclaw start              # por defecto: modo madmax — skills + entrenamiento RL programado
metaclaw start --mode rl    # RL sin planificador (entrena inmediatamente al llenar batch)
metaclaw start --mode skills_only  # solo skills, sin RL (no requiere Tinker)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Noticias

- **[13/03/2026]** **v0.3** — Soporte de meta-aprendizaje continuo: las actualizaciones RL solo se ejecutan durante horas de sueño, periodos de inactividad o reuniones de Google Calendar. Se agrega separación de conjuntos support/query para evitar que señales de recompensa obsoletas contaminen las actualizaciones del modelo.
- **[11/03/2026]** **v0.2** — Despliegue en un clic mediante la CLI `metaclaw`. Skills activados por defecto, RL ahora es opcional.
- **[09/03/2026]** Lanzamos **MetaClaw** — Habla con tu agente y deja que evolucione automáticamente. **Sin** necesidad de despliegue de GPU; conéctate directamente a la **API**.

---

## 🎥 Demo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Descripción

**MetaClaw es un agente que meta-aprende y evoluciona en entornos reales.**
Habla con tu agente como de costumbre — MetaClaw convierte cada conversación en vivo en una señal de aprendizaje, permitiendo que el agente mejore continuamente a través del despliegue real en lugar de depender únicamente del entrenamiento offline.

Internamente, envuelve tu modelo detrás de un proxy compatible con OpenAI, intercepta interacciones desde OpenClaw, inyecta skills relevantes en cada turno y meta-aprende de la experiencia acumulada. Las skills se resumen automáticamente tras cada sesión; con RL activado, un planificador de meta-aprendizaje posterga las actualizaciones de pesos a ventanas de inactividad para no interrumpir al agente durante el uso activo.

No se necesita cluster GPU. MetaClaw funciona con cualquier API de LLM compatible con OpenAI e integra opcionalmente **Kimi-K2.5** (1T MoE) via [Tinker](https://www.thinkingmachines.ai/tinker/) para entrenamiento LoRA en la nube.

## 🤖 Características principales

### **Despliegue en un clic**
Configura una vez con `metaclaw setup`, luego `metaclaw start` levanta el proxy, inyecta skills y conecta OpenClaw automáticamente. Sin necesidad de scripts de shell manuales.

### **Tres modos de operación**

| Modo | Por defecto | Función |
|------|------------|---------|
| `madmax` | ✅ | RL + planificador inteligente. Skills siempre activos; actualizaciones de pesos RL solo durante ventanas de sueño/inactividad/reunión. |
| `rl` | — | RL sin planificador. Entrena inmediatamente cuando un batch está lleno (comportamiento v0.2). |
| `skills_only` | — | Proxy → tu API LLM. Skills inyectados, resumidos automáticamente tras cada sesión. Sin GPU/Tinker requerido. |

### **Inyección de skills**
En cada turno, MetaClaw recupera las instrucciones de skills más relevantes y las inyecta en el prompt del sistema del agente. Mejora inmediata del comportamiento sin reentrenamiento.

### **Resumen automático de skills**
Tras cada conversación, el mismo LLM que ya estás usando analiza la sesión y destila nuevas skills automáticamente. Con RL activado, un modelo juez dedicado extrae skills de los episodios fallidos.

### **Sin cluster GPU requerido**
En modo `skills_only`, solo se necesita conexión a red. El entrenamiento RL se delega al cloud de Tinker.

### **Dos modos de aprendizaje**
MetaClaw soporta ambos:
- **RL (GRPO)**: aprendizaje a partir de señales de feedback implícitas
- **Destilación On-Policy (OPD)**: destilar un modelo profesor más grande en el estudiante on-policy

En modo OPD, el modelo estudiante genera respuestas normalmente, y el modelo profesor proporciona log-probabilidades por token en esas mismas respuestas. Los logprobs del profesor se pasan a la función de pérdida (p. ej. `cispo`) para que el estudiante aprenda la distribución del profesor. El profesor debe servirse detrás de un endpoint `/v1/completions` compatible con OpenAI (p. ej. vLLM, SGLang).

### **Asíncrono por diseño**
El serving, el modelado de recompensas y el entrenamiento están completamente desacoplados. El agente continúa respondiendo mientras el scoring y la optimización se ejecutan en paralelo.

---

## 🚀 Inicio rápido

### 1. Instalación

```bash
pip install -e .                        # modo skills_only (ligero)
pip install -e ".[rl]"                  # + soporte de entrenamiento RL (torch, transformers, tinker)
pip install -e ".[evolve]"              # + evolución de skills via LLM compatible con OpenAI
pip install -e ".[scheduler]"           # + integración Google Calendar para planificador
pip install -e ".[rl,evolve,scheduler]" # recomendado: configuración completa RL + planificador
```

### 2. Configuración

```bash
metaclaw setup
```

El asistente interactivo te pedirá que elijas tu proveedor de LLM (Kimi, Qwen, MiniMax o personalizado), tu clave API y si deseas activar el entrenamiento RL.

### 3. Inicio

```bash
metaclaw start
```

Eso es todo. MetaClaw inicia el proxy, configura automáticamente OpenClaw y reinicia la pasarela. Abre OpenClaw y empieza a chatear — los skills se inyectan en cada turno, y la sesión se resume automáticamente en nuevos skills cuando terminas.

---

## 🛠️ Referencia CLI

```
metaclaw setup                  # Asistente de configuración inicial interactivo
metaclaw start                  # Iniciar MetaClaw (por defecto: modo madmax)
metaclaw start --mode rl        # Forzar modo RL para esta sesión (sin planificador)
metaclaw start --mode skills_only  # Forzar modo solo skills para esta sesión
metaclaw stop                   # Detener una instancia de MetaClaw en ejecución
metaclaw status                 # Verificar estado del proxy, modo en ejecución y planificador
metaclaw config show            # Ver configuración actual
metaclaw config KEY VALUE       # Establecer un valor de configuración
```

**Claves de configuración comunes:**

```bash
metaclaw config rl.enabled true           # Activar entrenamiento RL
metaclaw config rl.tinker_api_key sk-...  # Establecer clave Tinker
metaclaw config skills.auto_evolve false  # Desactivar resumen automático de skills
metaclaw config proxy.port 31000          # Cambiar puerto del proxy
```

---

## ⚙️ Configuración

La configuración se encuentra en `~/.metaclaw/config.yaml`, creada por `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # tu biblioteca de skills
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # límite de skills específicos de tarea (por defecto 10)
  auto_evolve: true         # resumir skills automáticamente tras cada sesión

rl:
  enabled: false            # poner a true para activar entrenamiento RL
  model: moonshotai/Kimi-K2.5
  tinker_api_key: ""
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # ruta de checkpoint opcional para reanudar entrenamiento
  evolver_api_base: ""      # dejar vacío para reutilizar llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # poner a true para activar OPD (destilación profesor)
  teacher_url: ""           # URL base del modelo profesor (OpenAI-compatible /v1/completions)
  teacher_model: ""         # nombre del modelo profesor (p. ej. Qwen/Qwen3-32B)
  teacher_api_key: ""       # clave API del modelo profesor
  kl_penalty_coef: 1.0      # coeficiente de penalización KL para OPD

max_context_tokens: 20000   # límite de tokens de prompt antes del truncamiento

scheduler:                  # v0.3: planificador de meta-aprendizaje (auto-habilitado en modo madmax)
  enabled: false            # modo madmax lo habilita automáticamente; configurar manualmente para rl
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

Los skills son instrucciones cortas en Markdown inyectadas en el prompt del sistema del agente en cada turno. Residen en tu directorio de skills (`~/.metaclaw/skills/` por defecto), organizados como archivos `SKILL.md` individuales.

**El resumen automático de skills** se ejecuta tras cada conversación. El LLM configurado analiza lo que ocurrió y genera nuevos skills automáticamente. Sin curación manual necesaria — la biblioteca crece con el uso.

Para precargar el banco de skills integrado (40+ skills para coding, seguridad, tareas agénticas, etc.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Avanzado: Modo RL

Activa el entrenamiento RL para afinar continuamente el modelo a partir de conversaciones en vivo:

```bash
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

En modo RL:
- Cada turno de conversación se tokeniza y se envía como muestra de entrenamiento
- Un LLM juez (PRM) puntúa las respuestas de forma asíncrona
- Tinker Cloud ejecuta el fine-tuning LoRA; los pesos actualizados se hot-swap cada `batch_size` muestras
- Un LLM evolucionador dedicado extrae nuevos skills de los episodios fallidos

**Rollout programático** (sin TUI de OpenClaw): establece `openclaw_env_data_dir` en un directorio de archivos JSONL de tareas:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 Avanzado: Modo OPD

La Destilación On-Policy (OPD) te permite destilar un modelo profesor más grande en el estudiante mientras entrena on-policy. El estudiante genera respuestas normalmente; el profesor proporciona log-probabilidades por token en esas mismas respuestas. Una penalización KL guía al estudiante hacia la distribución del profesor.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

El profesor debe servirse detrás de un endpoint `/v1/completions` compatible con OpenAI (p. ej. vLLM, SGLang). OPD puede combinarse con scoring PRM — ambos se ejecutan de forma asíncrona.

Consulta `examples/run_conversation_opd.py` para un ejemplo programático y `scripts/run_openclaw_tinker_opd.sh` para un script de lanzamiento listo para usar.

---

## 🧠 Avanzado: Planificador de meta-aprendizaje (v0.3)

En modo RL, el paso de hot-swap de pesos pausa el agente durante varios minutos. El planificador (habilitado por defecto en modo madmax) pospone las actualizaciones RL a ventanas de inactividad del usuario para que el agente nunca se interrumpa durante el uso activo.

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Opcional: integración con Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Tres condiciones activan una ventana de actualización (cualquiera es suficiente): horas de sueño configuradas, inactividad del teclado del sistema, o un evento activo de Google Calendar. Si el usuario regresa durante una actualización, el batch parcial se guarda y se retoma en la siguiente ventana.

Cada `ConversationSample` se etiqueta con una versión `skill_generation`. Cuando la evolución de skills incrementa la generación, el buffer RL se vacía para que solo las muestras post-evolución se usen en las actualizaciones de gradiente (separación de conjuntos support/query MAML).

---

## 📚 Cita

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

## 🙏 Agradecimientos

MetaClaw se construye sobre los siguientes proyectos de código abierto:

- [OpenClaw](https://openclaw.ai) — el framework central de agentes.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — nuestro framework RL aumentado con skills.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — usado para entrenamiento RL en línea.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — inspiración para nuestro diseño RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — proporciona la base de nuestro banco de skills.

---

## 📄 Licencia

Este proyecto está licenciado bajo la [Licencia MIT](LICENSE).
