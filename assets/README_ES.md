<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# Habla con tu agente — aprende y *EVOLUCIONA*.

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

[Descripción](#-descripción) • [Inicio rápido](#-inicio-rápido) • [Referencia CLI](#️-referencia-cli) • [Configuración](#️-configuración) • [Skills](#-skills) • [Modo RL](#-avanzado-modo-rl) • [Modo OPD](#-avanzado-modo-opd) • [Cita](#-cita)

</div>

---

<div align="center">

### Dos comandos. Eso es todo.
</div>

```bash
metaclaw setup              # asistente de configuración inicial
metaclaw start              # skills activados, OpenClaw conectado — listo para chatear
metaclaw start --mode rl    # opcional: + entrenamiento RL en vivo mediante un backend compatible con Tinker
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Noticias

- **[10/03/2026]** **v0.2** — Despliegue en un clic mediante la CLI `metaclaw`. Skills activados por defecto, RL ahora es opcional.
- **[09/03/2026]** Lanzamos **MetaClaw** — Habla con tu agente y deja que evolucione automáticamente. **Sin** necesidad de despliegue de GPU; conéctate directamente a la **API**.

---

## 🎥 Demo

https://github.com/user-attachments/assets/1c2919fc-5612-40f7-bb97-c74ab50619d5

---

## 📖 Descripción

**MetaClaw convierte automáticamente las conversaciones en vivo en datos de entrenamiento continuos.**
Habla con tu agente como de costumbre, y MetaClaw gestiona el bucle de aprendizaje en segundo plano.

Envuelve tu modelo detrás de un proxy compatible con OpenAI, intercepta interacciones desde OpenClaw, inyecta skills relevantes en cada turno y resume automáticamente nuevas skills al final de cada sesión. Opcionalmente, activa fine-tuning continuo mediante un backend RL en la nube compatible con Tinker, como Tinker o MinT, con hot-swap de pesos sin interrumpir el servicio.

No se necesita cluster GPU. MetaClaw funciona con cualquier API de LLM compatible con OpenAI y puede conectar el entrenamiento RL a un backend compatible con Tinker, como [Tinker](https://www.thinkingmachines.ai/tinker/) o MinT, para fine-tuning LoRA en la nube.

## 🤖 Características principales

### **Despliegue en un clic**
Configura una vez con `metaclaw setup`, luego `metaclaw start` levanta el proxy, inyecta skills y conecta OpenClaw automáticamente. Sin necesidad de scripts de shell manuales.

### **Dos modos de operación**

| Modo | Por defecto | Función |
|------|------------|---------|
| `skills_only` | ✅ | Proxy → tu API LLM. Skills inyectados, resumidos automáticamente tras cada sesión. Sin GPU/Tinker requerido. |
| `rl` | desactivado | Proxy → RL cloud compatible con Tinker. Bucle de entrenamiento completo con scoring PRM y evolución de skills. |

### **Inyección de skills**
En cada turno, MetaClaw recupera las instrucciones de skills más relevantes y las inyecta en el prompt del sistema del agente. Mejora inmediata del comportamiento sin reentrenamiento.

### **Resumen automático de skills**
Tras cada conversación, el mismo LLM que ya estás usando analiza la sesión y destila nuevas skills automáticamente. Con RL activado, un modelo juez dedicado extrae skills de los episodios fallidos.

### **Sin cluster GPU requerido**
En modo `skills_only`, solo se necesita conexión a red. El entrenamiento RL se delega a un backend cloud compatible con Tinker.

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
pip install -e .            # modo skills_only (ligero)
pip install -e ".[rl]"      # + soporte de entrenamiento RL (torch, transformers, tinker)
pip install -e ".[evolve]"  # + evolución de skills via LLM compatible con OpenAI
pip install mindlab-toolkit # + backend de compatibilidad MinT opcional
```

Usa `mindlab-toolkit` solo si quieres `rl.backend=mint`. Enlaces de MinT: [overview](https://mint-doc.macaron.im/), [compatibilidad con Tinker](https://mint-doc.macaron.im/using-the-api/tinker-compatibility), [lista de modelos](https://mint-doc.macaron.im/using-the-api/model-lineup), [GitHub](https://github.com/MindLab-Research/mindlab-toolkit).

### 2. Configuración

```bash
metaclaw setup
```

El asistente interactivo te pedirá que elijas tu proveedor de LLM (Kimi, Qwen o personalizado), tu clave API y si deseas activar el entrenamiento RL.

La ruta RL de MetaClaw mantiene a Tinker como backend de referencia por defecto. `rl.backend=auto` es el valor recomendado y también puede detectar MinT a partir de credenciales o base URLs estilo Mint cuando el paquete de compatibilidad de MinT está instalado. Si quieres apuntar el mismo flujo a MinT, puedes configurar:

```bash
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-mint-...
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # China continental; fuera de China usa https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

Usa `https://mint-cn.macaron.xin/` para China continental o `https://mint.macaron.xin/` en otros casos.

Los alias heredados `rl.tinker_api_key` y `rl.tinker_base_url` siguen siendo válidos por compatibilidad.

### 3. Inicio

```bash
metaclaw start
```

Eso es todo. MetaClaw inicia el proxy, configura automáticamente OpenClaw y reinicia la pasarela. Abre OpenClaw y empieza a chatear — los skills se inyectan en cada turno, y la sesión se resume automáticamente en nuevos skills cuando terminas.

---

## 🛠️ Referencia CLI

```
metaclaw setup              # Asistente de configuración inicial interactivo
metaclaw start              # Iniciar MetaClaw (proxy + RL opcional)
metaclaw start --mode rl    # Forzar modo RL para esta sesión
metaclaw stop               # Detener una instancia de MetaClaw en ejecución
metaclaw status             # Verificar estado del proxy y modo en ejecución
metaclaw config show        # Ver configuración actual
metaclaw config KEY VALUE   # Establecer un valor de configuración
```

**Claves de configuración comunes:**

```bash
metaclaw config rl.enabled true           # Activar entrenamiento RL
metaclaw config rl.backend auto           # auto | tinker | mint
metaclaw config rl.api_key sk-...         # Establecer clave del backend RL
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # Endpoint de MinT para China continental; fuera de China usa https://mint.macaron.xin/
metaclaw config skills.auto_evolve false  # Desactivar resumen automático de skills
metaclaw config proxy.port 31000          # Cambiar puerto del proxy
```

---

## ⚙️ Configuración

La configuración se encuentra en `~/.metaclaw/config.yaml`, creada por `metaclaw setup`.

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
  dir: ~/.metaclaw/skills   # tu biblioteca de skills
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # límite de skills específicos de tarea (por defecto 10)
  auto_evolve: true         # resumir skills automáticamente tras cada sesión

rl:
  enabled: false            # poner a true para activar entrenamiento RL
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # endpoint opcional del backend, p. ej. https://mint-cn.macaron.xin/ (China continental) o https://mint.macaron.xin/ para MinT
  tinker_api_key: ""        # alias heredado de api_key
  tinker_base_url: ""       # alias heredado de base_url
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

Activa el entrenamiento RL para afinar continuamente el modelo a partir de conversaciones en vivo. Tinker sigue siendo la ruta de referencia por defecto, y MetaClaw también puede apuntar a MinT como alternativa compatible con Tinker:

```bash
metaclaw config rl.enabled true
metaclaw config rl.backend auto
metaclaw config rl.api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

Si quieres ejecutar el mismo flujo sobre MinT, añade backend, endpoint y modelo:

```bash
metaclaw config rl.backend mint
metaclaw config rl.base_url https://mint-cn.macaron.xin/  # China continental; fuera de China usa https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

En modo RL:
- Cada turno de conversación se tokeniza y se envía como muestra de entrenamiento
- Un LLM juez (PRM) puntúa las respuestas de forma asíncrona
- Por defecto, Tinker Cloud ejecuta el fine-tuning LoRA; MetaClaw también puede funcionar con una alternativa compatible como MinT, y los pesos actualizados se hot-swap cada `batch_size` muestras
- Un LLM evolucionador dedicado extrae nuevos skills de los episodios fallidos

Si te quedas con Tinker Cloud, usa `rl.backend=auto` o `rl.backend=tinker`. Si usas MinT, cambia a `rl.backend=mint` y configura el endpoint correspondiente.

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

## 📚 Cita

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

## 🙏 Agradecimientos

MetaClaw se construye sobre los siguientes proyectos de código abierto y colaboraciones:

- [OpenClaw](https://openclaw.ai) — el framework central de agentes.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — nuestro framework RL aumentado con skills.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — el backend de referencia principal para el entrenamiento RL en línea de MetaClaw.
- [MinT](https://mint-doc.macaron.im/) — una alternativa compatible con Tinker de [Mind Lab](https://macaron.im/mindlab), disponible vía [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit); los modelos soportados están en la [página oficial](https://mint-doc.macaron.im/using-the-api/model-lineup).
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — inspiración para nuestro diseño RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — proporciona la base de nuestro banco de skills.

El trabajo de compatibilidad con MinT en este repositorio es uno de los resultados de la colaboración entre el equipo del proyecto MetaClaw y [Mind Lab](https://macaron.im/mindlab). En esa colaboración, Mind Lab se ha centrado principalmente en la investigación de infraestructura y en la optimización de algoritmos LoRA RL.

---

## 📄 Licencia

Este proyecto está licenciado bajo la [Licencia MIT](LICENSE).
