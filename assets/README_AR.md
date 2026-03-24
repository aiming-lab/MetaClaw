<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# فقط تحدّث مع الوكيل الخاص بك، وسيتعلّم ويتطوّر باستمرار.

<p>مستوحى من طريقة تعلّم الدماغ. اجعل 🦞 الخاص بك يتعلّم ويتطوّر من كل محادثة حقيقية. لا حاجة لوحدات GPU. يدعم Kimi وQwen وClaude وMiniMax والمزيد.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_غير_متزامن_بالكامل-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_بدون_GPU-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_تطور_المهارات-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_نشر_بنقرة_واحدة-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[نظرة عامة](#-نظرة-عامة) • [البدء السريع](#-البدء-السريع) • [الإعدادات](#️-الإعدادات) • [وضع المهارات](#-وضع-المهارات) • [وضع RL](#-وضع-rl) • [وضع MadMax](#-وضع-madmax-الافتراضي) • [الاقتباس](#-الاقتباس)

</div>

---

<div align="center">

### أمران فقط. هذا كل شيء.
</div>

```bash
metaclaw setup              # معالج الإعداد لمرة واحدة
metaclaw start              # الوضع الافتراضي: madmax، مهارات + تدريب RL مُجدوَل
metaclaw start --daemon     # تشغيل في الخلفية، السجلات -> ~/.metaclaw/metaclaw.log
metaclaw start --daemon --log-file /tmp/metaclaw.log  # مسار سجل مخصص
metaclaw start --mode rl    # RL بدون مُجدوِل (يتدرّب فورًا عند اكتمال الدُّفعة)
metaclaw start --mode skills_only  # مهارات فقط، بدون RL (لا حاجة لـ Tinker)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 آخر الأخبار

- **[2026/03/16]** **v0.3.2** دعم متعدد الـ Claw: أصبح IronClaw وPicoClaw وZeroClaw وCoPaw وNanoClaw وNemoClaw مدعومين إلى جانب OpenClaw. NanoClaw عبر نقطة النهاية الجديدة المتوافقة مع Anthropic `/v1/messages`؛ NemoClaw عبر توجيه الاستدلال OpenShell. إضافة OpenRouter كمنصة LLM مدعومة.
- **[2026/03/13]** **v0.3.1** دعم واجهة MinT الخلفية: يعمل تدريب RL الآن مع Tinker وMinT معًا. يمكن ضبطه عبر `rl.backend` (auto/tinker/mint).
- **[2026/03/13]** **v0.3** دعم التعلّم الفوقي المستمر: تحديثات RL البطيئة تعمل فقط خلال ساعات النوم أو فترات الخمول أو اجتماعات Google Calendar. تمت إضافة فصل مجموعات support/query لمنع إشارات المكافأة القديمة من تلويث تحديثات النموذج.
- **[2026/03/11]** **v0.2** نشر بنقرة واحدة عبر واجهة `metaclaw` CLI. المهارات مُفعّلة افتراضيًا، وRL أصبح اختياريًا.
- **[2026/03/09]** إطلاق **MetaClaw** رسميًا. فقط تحدّث مع الوكيل ودعه يتطوّر تلقائيًا. **لا حاجة** لنشر GPU، فقط اتصل بـ **API**.

---

## 🎥 عرض توضيحي

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 نظرة عامة

**MetaClaw وكيل يتعلّم فوقيًا ويتطوّر في البيئات الحقيقية.**
فقط تحدّث مع وكيلك كالمعتاد. يحوّل MetaClaw كل محادثة حيّة إلى إشارة تعلّم، مما يُمكّن الوكيل من التحسّن المستمر من خلال النشر الفعلي بدلًا من الاعتماد على التدريب دون اتصال فقط.

في الخلفية، يضع MetaClaw نموذجك خلف وكيل وسيط متوافق مع OpenAI (مع نقطة نهاية `/v1/messages` متوافقة مع Anthropic للوكلاء مثل NanoClaw) يعترض التفاعلات من OpenClaw وNanoClaw وNemoClaw وغيرها من الوكلاء المدعومين، ويحقن المهارات ذات الصلة في كل دور، ويتعلّم فوقيًا من التجارب المتراكمة. تُلخَّص المهارات تلقائيًا بعد كل جلسة. عند تفعيل RL، يؤجّل مُجدوِل التعلّم الفوقي تحديثات الأوزان إلى فترات الخمول حتى لا يُقاطَع الوكيل أثناء الاستخدام النشط.

لا حاجة لمجموعة GPU. يعمل MetaClaw مع أي واجهة LLM API متوافقة مع OpenAI مباشرةً، ويستخدم واجهة خلفية متوافقة مع Tinker لتدريب LoRA السحابي. [Tinker](https://www.thinkingmachines.ai/tinker/) هو المسار المرجعي الافتراضي، ويمكن تفعيل MinT من خلال حزمة توافق منفصلة عند الحاجة.

## 🤖 الميزات الرئيسية

### **نشر بنقرة واحدة**
قم بالإعداد مرة واحدة باستخدام `metaclaw setup`، ثم `metaclaw start` يُشغّل الوكيل الوسيط ويحقن المهارات ويربط OpenClaw تلقائيًا. لا حاجة لسكربتات shell يدوية.

### **ثلاثة أوضاع تشغيل**

| الوضع | افتراضي | الوصف |
|------|---------|-------|
| `skills_only` | | وكيل وسيط لواجهة LLM API الخاصة بك. يحقن المهارات ويُلخّصها تلقائيًا بعد كل جلسة. لا حاجة لـ GPU / Tinker. |
| `rl` | | المهارات + تدريب RL (GRPO). يتدرّب فورًا عند اكتمال الدُّفعة. OPD اختياري لتقطير المعلّم. |
| `madmax` | ✅ | المهارات + RL + مُجدوِل ذكي. تحديثات أوزان RL تعمل فقط خلال فترات النوم/الخمول/الاجتماعات. |

### **تصميم غير متزامن بالكامل**
الخدمة ونمذجة المكافآت والتدريب منفصلة تمامًا. يستمر الوكيل في الاستجابة بينما يعمل التقييم والتحسين بالتوازي في الخلفية.

---

## 🚀 البدء السريع

### 1. التثبيت

```bash
pip install -e .                        # وضع skills_only (خفيف الوزن)
pip install -e ".[rl]"                  # + دعم تدريب RL (torch، transformers، tinker)
pip install -e ".[evolve]"              # + تطوير المهارات عبر LLM متوافق مع OpenAI
pip install -e ".[scheduler]"           # + تكامل Google Calendar مع المُجدوِل
pip install -e ".[rl,evolve,scheduler]" # موصى به: إعداد RL + مُجدوِل كامل
```

إذا كنت تريد استخدام `rl.backend=mint`، قم بتثبيت حزمة توافق MinT بشكل منفصل في نفس البيئة، مثل [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). لا يضمّن MetaClaw هذه التبعية في الحزمة الافتراضية حتى يتمكّن مستخدمو RL من اختيار Tinker أو MinT بشكل صريح.

### 2. الإعداد

```bash
metaclaw setup
```

سيرشدك المعالج التفاعلي لاختيار مزوّد LLM (Kimi أو Qwen أو MiniMax أو مخصّص)، وإدخال مفتاح API الخاص بك، وتفعيل تدريب RL اختياريًا.

يمكن لمسار RL في MetaClaw التبديل صراحةً بين `tinker` و`mint`. القيمة الافتراضية الموصى بها هي `auto` وستظل تستنتج MinT من بيانات الاعتماد أو عناوين URL ذات النمط المشابه لـ Mint عندما تكون حزمة MinT مثبّتة.

**Tinker** (الافتراضي):

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

الأسماء المستعارة القديمة `rl.tinker_api_key` و`rl.tinker_base_url` لا تزال مقبولة للتوافق مع الإصدارات السابقة.

### 3. التشغيل

```bash
metaclaw start
```

هذا كل شيء. يُشغّل MetaClaw الوكيل الوسيط ويُعدّ OpenClaw تلقائيًا ويُعيد تشغيل البوابة. افتح OpenClaw وابدأ المحادثة، حيث تُحقن المهارات في كل دور وتُلخَّص الجلسة تلقائيًا إلى مهارات جديدة عند الانتهاء.

---

## ⚙️ الإعدادات

ملف الإعدادات موجود في `~/.metaclaw/config.yaml`، يُنشأ بواسطة `metaclaw setup`.

**أوامر CLI:**

```
metaclaw setup                  # معالج الإعداد التفاعلي لأول مرة
metaclaw start                  # تشغيل MetaClaw (الوضع الافتراضي: madmax)
metaclaw start --daemon         # تشغيل MetaClaw في الخلفية
metaclaw start --daemon --log-file /tmp/metaclaw.log  # مسار سجل مخصص
metaclaw start --mode rl        # فرض وضع RL لهذه الجلسة (بدون مُجدوِل)
metaclaw start --mode skills_only  # فرض وضع المهارات فقط لهذه الجلسة
metaclaw stop                   # إيقاف مثيل MetaClaw قيد التشغيل
metaclaw status                 # التحقق من صحة الوكيل الوسيط والوضع الحالي وحالة المُجدوِل
metaclaw config show            # عرض الإعدادات الحالية
metaclaw config KEY VALUE       # تعيين قيمة إعداد
```

عند تشغيل MetaClaw مع `--daemon`، ينتظر الأمر حتى يصبح الوكيل المحلي جاهزًا قبل الإرجاع. استخدم `metaclaw status` للتحقق من الجاهزية و `metaclaw stop` لإيقاف العملية في الخلفية.

<details>
<summary><b>المرجع الكامل للإعدادات (انقر للتوسيع)</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # اختياري: رمز bearer للوكيل الوسيط المحلي لـ MetaClaw

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # دليل مكتبة المهارات الخاصة بك
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # الحد الأقصى للمهارات الخاصة بالمهمة (افتراضي 10)
  auto_evolve: true         # تلخيص المهارات تلقائيًا بعد كل جلسة

rl:
  enabled: false            # اضبط على true لتفعيل تدريب RL
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # نقطة نهاية خلفية اختيارية، مثل https://mint.macaron.xin/ لـ MinT
  tinker_api_key: ""        # اسم مستعار متوافق لـ api_key
  tinker_base_url: ""       # اسم مستعار متوافق لـ base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # اختياري: استئناف التدريب من نقطة تفتيش
  evolver_api_base: ""      # اتركه فارغًا لإعادة استخدام llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # اضبط على true لتفعيل OPD (تقطير المعلّم)
  teacher_url: ""           # عنوان URL الأساسي لنموذج المعلّم (متوافق مع OpenAI /v1/completions)
  teacher_model: ""         # اسم نموذج المعلّم (مثل Qwen/Qwen3-32B)
  teacher_api_key: ""       # مفتاح API لنموذج المعلّم
  kl_penalty_coef: 1.0      # معامل عقوبة KL لـ OPD

max_context_tokens: 20000   # الحد الأقصى لرموز prompt قبل الاقتطاع

scheduler:                  # v0.3: مُجدوِل التعلّم الفوقي (يُفعَّل تلقائيًا في وضع madmax)
  enabled: false            # يُفعَّل تلقائيًا في وضع madmax، يجب ضبطه يدويًا في وضع rl
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

## 💪 وضع المهارات

**`metaclaw start --mode skills_only`**

أخف وضع تشغيل. لا حاجة لـ GPU أو واجهة RL خلفية. يضع MetaClaw واجهة LLM الخاصة بك خلف وكيل وسيط يحقن المهارات ذات الصلة في كل دور محادثة، ثم يُلخّص مهارات جديدة تلقائيًا بعد كل محادثة.

المهارات هي تعليمات Markdown قصيرة تُخزَّن في `~/.metaclaw/skills/` كملفات `SKILL.md` مستقلة. تنمو المكتبة تلقائيًا مع استخدامك.

لتحميل بنك المهارات المدمج مسبقًا (أكثر من 40 مهارة تشمل البرمجة والأمان ومهام الوكيل وغيرها):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 وضع RL

**`metaclaw start --mode rl`**

كل ما في وضع المهارات، بالإضافة إلى الضبط الدقيق المستمر بالتعلّم المعزّز من المحادثات الحيّة. يتم تحويل كل دور محادثة إلى رموز وإرساله كعيّنة تدريب. يقوم نموذج LLM حكم (PRM) بتقييم الاستجابات بشكل غير متزامن، وتُجري واجهة خلفية متوافقة مع Tinker (مثل Tinker السحابي أو MinT) ضبطًا دقيقًا لـ LoRA مع تبديل الأوزان تلقائيًا.

**Tinker** (الافتراضي):

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

يستخرج نموذج LLM مُطوِّر مخصّص أيضًا مهارات جديدة من الحلقات الفاشلة ويُعيدها إلى مكتبة المهارات.

**التنفيذ البرمجي** (بدون واجهة OpenClaw TUI): اضبط `openclaw_env_data_dir` على دليل يحتوي ملفات مهام JSONL:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### التقطير على السياسة (OPD)

OPD إضافة اختيارية لوضع RL. يُقطّر نموذج معلّم أكبر إلى نموذج الطالب على السياسة: يُنشئ نموذج الطالب الاستجابات كالمعتاد، بينما يوفّر نموذج المعلّم احتمالات لوغاريتمية لكل رمز على نفس الاستجابات. تُوجّه عقوبة KL نموذج الطالب نحو توزيع المعلّم.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

يجب نشر نموذج المعلّم خلف نقطة نهاية `/v1/completions` متوافقة مع OpenAI (مثل vLLM أو SGLang). يمكن الجمع بين OPD وتقييم PRM، حيث يعمل كلاهما بشكل غير متزامن. راجع `examples/run_conversation_opd.py` و`scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 وضع MadMax (الافتراضي)

**`metaclaw start`**

كل ما في وضع RL، بالإضافة إلى مُجدوِل تعلّم فوقي يؤجّل تحديثات الأوزان إلى فترات عدم نشاط المستخدم حتى لا يُقاطَع الوكيل أثناء الاستخدام النشط. هذا هو الوضع الافتراضي.

تُوقف خطوة تبديل أوزان RL الوكيل لعدة دقائق. بدلًا من التدريب فورًا عند اكتمال الدُّفعة (كما في وضع RL)، ينتظر MadMax نافذة مناسبة.

ثلاثة شروط تُفعّل نافذة التحديث (أي شرط منها كافٍ):

- **ساعات النوم**: وقت بداية/نهاية قابل للتعديل (مثل 23:00 إلى 07:00)
- **خمول لوحة المفاتيح**: يُفعَّل بعد N دقيقة من عدم النشاط
- **أحداث Google Calendar**: يكتشف الاجتماعات لتشغيل التحديثات أثناء غيابك

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# اختياري: تكامل Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

إذا عاد المستخدم أثناء التحديث، تُحفظ الدُّفعة الجزئية وتُستأنف في النافذة التالية.

يحمل كل `ConversationSample` علامة إصدار `skill_generation`. عندما يرفع تطوّر المهارات رقم الإصدار، يُفرَّغ مخزن RL المؤقت بحيث تُستخدم فقط العيّنات بعد التطوّر لتحديثات التدرّج (فصل مجموعات support/query في MAML).

---

## 📚 الاقتباس

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

## 🙏 شكر وتقدير

MetaClaw مبني على المشاريع مفتوحة المصدر التالية:

- [OpenClaw](https://openclaw.ai) , إطار عمل الوكيل الأساسي.
- [SkillRL](https://github.com/aiming-lab/SkillRL) , إطار عمل RL المُعزَّز بالمهارات.
- [Tinker](https://www.thinkingmachines.ai/tinker/) , يُستخدم لتدريب RL عبر الإنترنت.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) , واجهة خلفية بديلة لتدريب RL عبر الإنترنت.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) , مصدر إلهام لتصميم RL الخاص بنا.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) , يوفّر الأساس لبنك المهارات الخاص بنا.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) , وكيل Claude الشخصي من qwibitai، يتصل عبر نقطة النهاية `/v1/messages` المتوافقة مع Anthropic.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) , مكوّن إضافي لوكيل OpenShell من NVIDIA للاستدلال.

---

## 📄 الترخيص

هذا المشروع مرخّص بموجب [ترخيص MIT](LICENSE).
