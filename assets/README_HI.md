<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# बस अपने Agent से बात करें, यह सीखता रहेगा और *विकसित* होता रहेगा।

<p>मस्तिष्क की सीखने की प्रक्रिया से प्रेरित। अपने 🦞 को वास्तविक बातचीत में मेटा-लर्निंग और विकास करने दें। GPU की आवश्यकता नहीं। Kimi, Qwen, Claude, MiniMax आदि के साथ काम करता है।</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_पूर्ण_असिंक्रोनस-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_GPU_क्लस्टर_अनावश्यक-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_स्किल_विकास-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_एक_क्लिक_डिप्लॉय-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇵🇹 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇸🇦 العربية](./README_AR.md)

<br/>

[अवलोकन](#-अवलोकन) • [त्वरित शुरुआत](#-त्वरित-शुरुआत) • [कॉन्फ़िगरेशन](#️-कॉन्फ़िगरेशन) • [Skills मोड](#-skills-मोड) • [RL मोड](#-rl-मोड) • [Auto मोड](#-auto-मोड-डिफ़ॉल्ट) • [उद्धरण](#-उद्धरण)

</div>

---

<div align="center">

### दो कमांड। बस इतना ही।
</div>

```bash
metaclaw setup              # पहली बार का कॉन्फ़िगरेशन विज़ार्ड
metaclaw start              # डिफ़ॉल्ट auto मोड: Skills + शेड्यूल्ड RL ट्रेनिंग
metaclaw start --mode rl    # बिना शेड्यूलर के RL (batch भरते ही ट्रेनिंग)
metaclaw start --mode skills_only  # केवल Skills, कोई RL नहीं (Tinker की ज़रूरत नहीं)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 ताज़ा अपडेट

- **[2026/04/19]** **v0.4.2** — OpenClaw context-engine एकीकरण: मेमोरी प्लगइन OpenClaw v2026.4.10+ पर context-engine (assemble/compact लाइफसाइकल) के रूप में पंजीकृत होता है, जिससे मेमोरी का डबल इंजेक्शन समाप्त होता है। प्रति-टर्न इंक्रीमेंटल कैप्चर, सेशन-एंड फाइनल फ्लश, OpenClaw कम्पैटिबिलिटी कॉन्फिग सेक्शन और सीमलेस प्रॉक्सी-साइड स्किल इंजेक्शन के लिए एक्टिव मेमोरी सप्रेशन जोड़ा गया।
- **[2026/04/11]** **v0.4.1** — इंक्रीमेंटल मेमोरी इन्जेशन: मेमोरी लेयर अब केवल सत्र के अंत में नहीं बल्कि हर N टर्न (डिफ़ॉल्ट 5) पर एक्सट्रैक्ट और पर्सिस्ट करती है, जिससे सत्र के बीच मेमोरी ब्लैकआउट कम होता है। नए `/buffer_turn` और `/flush_session` sidecar एंडपॉइंट्स, `--buffer-turns` फ़्लैग के साथ बेंचमार्क हार्नेस और प्रयोग तुलना रिपोर्ट जोड़े गए।
- **[2026/03/25]** **v0.4.0** — Contexture layer（संदर्भ परत）: MetaClaw अब उपयोगकर्ताओं और प्रोजेक्ट्स के लिए सत्रों के पार मेमोरी को बनाए रखता है। प्रासंगिक तथ्य, प्राथमिकताएं और प्रोजेक्ट इतिहास स्वचालित रूप से पुनर्प्राप्त होकर प्रॉम्प्ट में इंजेक्ट किए जाते हैं। इसमें अनुकूली मेमोरी नीति, बैकग्राउंड एकत्रीकरण और वैकल्पिक मेमोरी साइडकार सेवा शामिल है।
- **[2026/03/16]** **v0.3.2** मल्टी-Claw सपोर्ट: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw और NemoClaw अब OpenClaw के साथ सपोर्टेड हैं। NanoClaw नए `/v1/messages` Anthropic-संगत एंडपॉइंट के माध्यम से; NemoClaw OpenShell इनफरेंस रूटिंग के माध्यम से। OpenRouter को LLM प्लेटफ़ॉर्म के रूप में जोड़ा गया।
- **[2026/03/13]** **v0.3.1** MinT बैकएंड सपोर्ट: RL ट्रेनिंग अब Tinker और MinT दोनों के साथ काम करती है। `rl.backend` (auto/tinker/mint) के माध्यम से कॉन्फ़िगर करें।
- **[2026/03/13]** **v0.3** सतत मेटा-लर्निंग सपोर्ट: स्लो RL अपडेट अब केवल नींद के समय, निष्क्रिय अवधि, या Google Calendar मीटिंग के दौरान चलते हैं। पुराने रिवॉर्ड सिग्नल से मॉडल अपडेट को दूषित होने से बचाने के लिए support/query सेट विभाजन जोड़ा गया।
- **[2026/03/11]** **v0.2** `metaclaw` CLI के माध्यम से एक-क्लिक डिप्लॉयमेंट। Skill डिफ़ॉल्ट रूप से सक्रिय, RL अब वैकल्पिक है।
- **[2026/03/09]** **MetaClaw** का आधिकारिक रिलीज़। बस Agent से बात करें और उसे स्वचालित रूप से विकसित होने दें। GPU डिप्लॉयमेंट की **कोई ज़रूरत नहीं**, बस **API** से कनेक्ट करें।

---

## 🎥 डेमो

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 अवलोकन

**MetaClaw एक ऐसा Agent है जो वास्तविक परिस्थितियों में मेटा-लर्निंग करता है और लगातार विकसित होता रहता है।**
बस अपने Agent से सामान्य तरीके से बात करें। MetaClaw हर लाइव बातचीत को एक सीखने के संकेत में बदल देता है, जिससे Agent केवल ऑफ़लाइन ट्रेनिंग पर निर्भर रहने के बजाय वास्तविक डिप्लॉयमेंट के दौरान लगातार सुधार करता रहता है।

आंतरिक रूप से, यह आपके मॉडल को एक OpenAI-संगत प्रॉक्सी के पीछे रखता है (NanoClaw जैसे Anthropic-नेटिव Agent के लिए `/v1/messages` Anthropic-संगत एंडपॉइंट भी प्रदान करता है) जो OpenClaw, NanoClaw, NemoClaw और अन्य समर्थित Agent से इंटरैक्शन को इंटरसेप्ट करता है, हर टर्न पर प्रासंगिक Skills इंजेक्ट करता है, और संचित अनुभव से मेटा-लर्निंग करता है। हर सेशन के बाद Skills स्वचालित रूप से सारांशित होती हैं; RL सक्रिय होने पर, मेटा-लर्निंग शेड्यूलर वेट अपडेट को निष्क्रिय समय में स्थगित कर देता है ताकि सक्रिय उपयोग के दौरान Agent में कोई बाधा न आए।

GPU क्लस्टर की ज़रूरत नहीं। MetaClaw किसी भी OpenAI-संगत LLM API के साथ सीधे काम करता है, और क्लाउड-आधारित LoRA ट्रेनिंग के लिए Tinker-संगत बैकएंड का उपयोग करता है। [Tinker](https://www.thinkingmachines.ai/tinker/) डिफ़ॉल्ट संदर्भ पथ है; आवश्यकता होने पर MinT या Weaver को अलग संगतता पैकेज के माध्यम से सक्रिय किया जा सकता है।

## 🤖 मुख्य विशेषताएँ

### **एक-क्लिक डिप्लॉयमेंट**
`metaclaw setup` से एक बार कॉन्फ़िगर करें, फिर `metaclaw start` प्रॉक्सी शुरू करता है, Skills इंजेक्ट करता है, और OpenClaw को स्वचालित रूप से कनेक्ट करता है। मैनुअल शेल स्क्रिप्ट की ज़रूरत नहीं।

### **तीन ऑपरेटिंग मोड**

| मोड | डिफ़ॉल्ट | विवरण |
|------|---------|--------|
| `skills_only` | | प्रॉक्सी के माध्यम से आपका LLM API। Skills इंजेक्ट, सेशन के बाद ऑटो-सारांश। GPU / Tinker की ज़रूरत नहीं। |
| `rl` | | Skills + RL ट्रेनिंग (GRPO)। batch भरते ही तुरंत ट्रेनिंग। शिक्षक डिस्टिलेशन के लिए वैकल्पिक OPD। |
| `auto` | ✅ | Skills + RL + स्मार्ट शेड्यूलर। RL वेट अपडेट केवल नींद/निष्क्रिय/मीटिंग विंडो में चलते हैं। |

### **दीर्घकालिक स्मृति**
MetaClaw सत्रों के बीच तथ्य, प्राथमिकताएँ और प्रोजेक्ट इतिहास रख सकता है और हर चक्र में संबंधित संदर्भ डाल सकता है — ताकि आपका एजेंट हफ्तों बाद भी याद रखे कि आपने क्या कहा।

### **पूरी तरह असिंक्रोनस डिज़ाइन**
सर्विंग, रिवॉर्ड मॉडलिंग, और ट्रेनिंग पूरी तरह अलग-अलग हैं। Agent जवाब देता रहता है जबकि स्कोरिंग और ऑप्टिमाइज़ेशन पृष्ठभूमि में समानांतर चलते हैं।

---

## 🚀 त्वरित शुरुआत

### 1. इंस्टॉलेशन

**OpenClaw (एक-क्लिक):** रिलीज़ [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) का उपयोग करें — नीचे दिए गए आदेश चलाएँ, फिर `metaclaw setup` और `metaclaw start`। विवरण (Windows, मिरर, कॉन्फ़िग, समस्या निवारण): [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md)।

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip** (PyPI या यह रेपो):

```bash
pip install -e .                        # skills_only मोड (हल्का)
pip install -e ".[rl]"                  # + RL ट्रेनिंग सपोर्ट (torch, transformers, tinker)
pip install -e ".[evolve]"              # + OpenAI-संगत LLM के माध्यम से Skill विकास
pip install -e ".[scheduler]"           # + Google Calendar शेड्यूलर इंटीग्रेशन
pip install -e ".[rl,evolve,scheduler]" # अनुशंसित: पूर्ण RL + शेड्यूलर सेटअप
```
(वैकल्पिक) WeChat इंटीग्रेशन आधिकारिक @tencent-weixin/openclaw-weixin प्लगइन का उपयोग करता है। WeChat सक्षम होने पर MetaClaw इसे स्वतः इंस्टॉल करता है:

```bash
metaclaw config wechat.enabled true
metaclaw start
```

प्लगइन MetaClaw शुरू करने पर स्वतः इंस्टॉल हो जाता है। आप इसे मैनुअली भी इंस्टॉल कर सकते हैं:

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

WeChat खाता स्विच करने के लिए (नए QR कोड से दोबारा लॉगिन करें):

```bash
metaclaw start --wechat-relogin
```

यदि आप `rl.backend=mint` का उपयोग करना चाहते हैं, तो उसी एनवायरनमेंट में MinT संगतता पैकेज अलग से इंस्टॉल करें, उदाहरण के लिए [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit)। `rl.backend=weaver` के लिए [`nex-weaver`](https://github.com/nex-agi/weaver) अलग से इंस्टॉल करें। MetaClaw इन डिपेंडेंसी को डिफ़ॉल्ट पैकेज से बाहर रखता है ताकि RL उपयोगकर्ता स्पष्ट रूप से Tinker, MinT या Weaver चुन सकें।

### 2. कॉन्फ़िगरेशन

```bash
metaclaw setup
```

इंटरैक्टिव विज़ार्ड आपसे कहेगा:
1. **अपना व्यक्तिगत एजेंट चुनें** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` या `none` (MetaClaw आरंभ पर स्वतः कॉन्फ़िग करेगा)
2. **LLM प्रदाता चुनें** — Kimi, Qwen, OpenAI, Volcano Engine या कस्टम
3. **API कुंजी दर्ज करें** और वैकल्पिक रूप से RL प्रशिक्षण चालू करें

MetaClaw का RL पथ `tinker`, `mint` और `weaver` के बीच स्पष्ट रूप से स्विच किया जा सकता है। `auto` अनुशंसित डिफ़ॉल्ट है और MinT या Weaver पैकेज इंस्टॉल होने पर संबंधित क्रेडेंशियल्स या base URL से स्वचालित रूप से पहचान लेगा।

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

पुराने अलियास `rl.tinker_api_key` और `rl.tinker_base_url` अभी भी बैकवर्ड संगतता के लिए स्वीकार किए जाते हैं।

### 3. शुरू करें

```bash
metaclaw start
```

बस। MetaClaw प्रॉक्सी शुरू करता है, आपके चुने हुए व्यक्तिगत एजेंट को स्वतः कॉन्फ़िगर करता है, और गेटवे पुनः आरंभ करता है। अपना एजेंट खोलें और चैट शुरू करें — हर चक्र पर स्किल इंजेक्ट होती हैं और समाप्ति पर सत्र स्वचालित रूप से नई स्किल में सारांशित होता है।

---

## ⚙️ कॉन्फ़िगरेशन

कॉन्फ़िगरेशन फ़ाइल `~/.metaclaw/config.yaml` में स्थित है, जो `metaclaw setup` द्वारा स्वचालित रूप से बनाई जाती है।

**CLI कमांड:**

```
metaclaw setup                  # पहली बार का इंटरैक्टिव कॉन्फ़िगरेशन विज़ार्ड
metaclaw start                  # MetaClaw शुरू करें (डिफ़ॉल्ट: auto मोड)
metaclaw start --mode rl        # इस सेशन के लिए RL मोड सक्रिय करें (बिना शेड्यूलर)
metaclaw start --mode skills_only  # इस सेशन के लिए केवल Skills मोड सक्रिय करें
metaclaw stop                   # चल रहे MetaClaw इंस्टेंस को रोकें
metaclaw status                 # प्रॉक्सी स्वास्थ्य, चल रहा मोड, और शेड्यूलर स्थिति देखें
metaclaw config show            # वर्तमान कॉन्फ़िगरेशन देखें
metaclaw config KEY VALUE       # कॉन्फ़िगरेशन मान सेट करें
metaclaw config llm.oauth_token TOKEN               # वर्तमान CLI प्रदाता के लिए OAuth टोकन संग्रहीत करें
metaclaw config llm.oauth_token TOKEN               # वर्तमान CLI प्रदाता के लिए OAuth टोकन संग्रहीत करें
metaclaw auth paste-token --provider anthropic      # OAuth टोकन संग्रहीत करें (anthropic | openai-codex | gemini)
metaclaw auth status                                # सभी संग्रहीत प्रमाणीकरण प्रोफ़ाइल दिखाएं
metaclaw uninstall              # सभी MetaClaw डेटा, OpenClaw एक्सटेंशन और pip पैकेज हटाएं
metaclaw uninstall              # सभी MetaClaw डेटा, OpenClaw एक्सटेंशन और pip पैकेज हटाएं
```

तत्परता की जाँच के लिए `metaclaw status` और प्रक्रिया को रोकने के लिए `metaclaw stop` का उपयोग करें।

<details>
<summary><b>पूर्ण कॉन्फ़िगरेशन संदर्भ (विस्तार के लिए क्लिक करें)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # oauth_token उदाहरण (टोकन `metaclaw auth paste-token` से संग्रहीत):
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

proxy:
  port: 30000
  api_key: ""              # वैकल्पिक: स्थानीय MetaClaw प्रॉक्सी bearer token

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # आपकी Skill लाइब्रेरी डायरेक्टरी
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # कार्य-विशिष्ट Skill की सीमा (डिफ़ॉल्ट 10)
  auto_evolve: true         # हर सेशन के बाद स्वचालित Skill सारांशण

rl:
  enabled: false            # RL ट्रेनिंग सक्रिय करने के लिए true सेट करें
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # वैकल्पिक बैकएंड endpoint, जैसे MinT के लिए https://mint.macaron.xin/ या Weaver के लिए https://weaver-console.nex-agi.cn
  tinker_api_key: ""        # api_key का संगत अलियास
  tinker_base_url: ""       # base_url का संगत अलियास
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # वैकल्पिक: चेकपॉइंट से ट्रेनिंग पुनः आरंभ करें
  evolver_api_base: ""      # खाली छोड़ें तो llm.api_base का पुनः उपयोग होगा
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # OPD (शिक्षक डिस्टिलेशन) सक्रिय करने के लिए true सेट करें
  teacher_url: ""           # शिक्षक मॉडल base URL (OpenAI-संगत /v1/completions)
  teacher_model: ""         # शिक्षक मॉडल का नाम (जैसे Qwen/Qwen3-32B)
  teacher_api_key: ""       # शिक्षक मॉडल API Key
  kl_penalty_coef: 1.0      # OPD के लिए KL पेनल्टी गुणांक

max_context_tokens: 20000   # काटने से पहले प्रॉम्प्ट टोकन सीमा；0 = कोई काट नहीं
                            # (बड़े-संदर्भ क्लाउड मॉडलों के साथ skills_only में अनुशंसित)
context_window: 0           # एजेंट को बताई गई संदर्भ खिड़की (उदा. OpenClaw संकुचन थ्रेशोल्ड)；
                            # 0 = ऑटो (skills_only में ≈200000, rl/auto में 32768)

scheduler:                  # v0.3: मेटा-लर्निंग शेड्यूलर (auto मोड में स्वचालित सक्रिय)
  enabled: false            # auto मोड में स्वचालित सक्रिय; rl मोड में मैनुअल सेट करें
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

## 💪 Skills मोड

**`metaclaw start --mode skills_only`**

सबसे हल्का मोड। GPU या RL बैकएंड की ज़रूरत नहीं। MetaClaw आपके LLM को एक प्रॉक्सी के पीछे रखता है जो हर टर्न पर प्रासंगिक Skills इंजेक्ट करता है, फिर हर बातचीत के बाद स्वचालित रूप से नई Skills सारांशित करता है।

OpenAI-संगत कस्टम प्रदाताओं के लिए `llm.api_base` को पूर्ण चैट API बेस पर सेट करें (आमतौर पर `/v1` पर समाप्त, उदा. `https://your-gateway.example/v1`)। `skills_only` मोड में MetaClaw प्रॉम्प्ट संपीड़न और संबंधित सहायक LLM कॉल के लिए वही एंडपॉइंट दोबारा उपयोग करता है, जब तक अलग evolver एंडपॉइंट कॉन्फ़िग न करें।

Skills छोटे Markdown निर्देश हैं जो `~/.metaclaw/skills/` में व्यक्तिगत `SKILL.md` फ़ाइलों के रूप में संग्रहित होते हैं। लाइब्रेरी उपयोग के साथ स्वचालित रूप से बढ़ती है।

बिल्ट-इन Skill बैंक (कोडिंग, सुरक्षा, Agent कार्यों आदि में 40+ Skills) प्री-लोड करने के लिए:

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL मोड

**`metaclaw start --mode rl`**

Skills मोड की सभी सुविधाएँ, साथ ही लाइव बातचीत से सतत RL फ़ाइन-ट्यूनिंग। हर बातचीत टर्न को tokenize करके ट्रेनिंग सैंपल के रूप में सबमिट किया जाता है। जज LLM (PRM) असिंक्रोनस रूप से प्रतिक्रियाओं को स्कोर करता है, और Tinker-संगत बैकएंड (Tinker क्लाउड, MinT या Weaver) LoRA फ़ाइन-ट्यूनिंग करता है जिसमें वेट हॉट-स्वैप किए जाते हैं।

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

एक समर्पित इवॉल्वर LLM विफल एपिसोड से नई Skills निकालता है और उन्हें Skill लाइब्रेरी में वापस जोड़ता है।

**प्रोग्रामैटिक रोलआउट** (OpenClaw TUI की ज़रूरत नहीं): `openclaw_env_data_dir` को JSONL टास्क फ़ाइलों वाली डायरेक्टरी पर सेट करें:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### ऑन-पॉलिसी डिस्टिलेशन (OPD)

OPD, RL मोड के लिए एक वैकल्पिक ऐड-ऑन है। यह एक बड़े शिक्षक मॉडल को छात्र मॉडल में ऑन-पॉलिसी डिस्टिल करता है: छात्र मॉडल सामान्य रूप से प्रतिक्रियाएँ उत्पन्न करता है, और शिक्षक मॉडल उन्हीं प्रतिक्रियाओं पर प्रति-टोकन लॉग-प्रायिकताएँ प्रदान करता है। KL पेनल्टी छात्र को शिक्षक के वितरण की ओर मार्गदर्शन करती है।

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

शिक्षक मॉडल को OpenAI-संगत `/v1/completions` एंडपॉइंट (जैसे vLLM, SGLang) पर डिप्लॉय किया जाना चाहिए। OPD को PRM स्कोरिंग के साथ संयोजित किया जा सकता है, दोनों असिंक्रोनस रूप से चलते हैं। `examples/run_conversation_opd.py` और `scripts/run_openclaw_tinker_opd.sh` देखें।

---

## 🧠 Auto मोड (डिफ़ॉल्ट)

**`metaclaw start`**

RL मोड की सभी सुविधाएँ, साथ ही एक मेटा-लर्निंग शेड्यूलर जो वेट अपडेट को उपयोगकर्ता-निष्क्रिय विंडो तक स्थगित कर देता है ताकि सक्रिय उपयोग के दौरान Agent में बाधा न आए। यह डिफ़ॉल्ट मोड है।

RL वेट हॉट-स्वैप स्टेप Agent को कई मिनट के लिए रोक देता है। batch भरते ही तुरंत ट्रेनिंग शुरू करने के बजाय (जैसा RL मोड करता है), auto मोड एक उपयुक्त विंडो की प्रतीक्षा करता है।

तीन स्थितियाँ अपडेट विंडो ट्रिगर करती हैं (कोई भी एक पर्याप्त है):

- **नींद के घंटे**: कॉन्फ़िगर करने योग्य शुरू/समाप्ति समय (जैसे 23:00 से 07:00)
- **कीबोर्ड निष्क्रियता**: N मिनट की निष्क्रियता के बाद ट्रिगर
- **Google Calendar इवेंट**: मीटिंग का पता लगाकर आपकी अनुपस्थिति में अपडेट चलाता है

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# वैकल्पिक: Google Calendar इंटीग्रेशन
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

यदि अपडेट के बीच में उपयोगकर्ता लौटता है, तो आंशिक batch सहेजा जाता है और अगली विंडो में पुनः आरंभ किया जाता है।

हर `ConversationSample` को `skill_generation` वर्शन टैग के साथ चिह्नित किया जाता है। जब Skill विकास generation बढ़ाता है, तो RL buffer फ़्लश किया जाता है ताकि ग्रेडिएंट अपडेट के लिए केवल विकास-उत्तर सैंपल का उपयोग हो (MAML support/query सेट विभाजन)।

---

## 🗑️ अनइंस्टॉल

```bash
metaclaw uninstall
```

एक ही चरण में सब कुछ हटा देता है: चल रहे इंस्टेंस को रोकता है, `~/.openclaw/openclaw.json` से MetaClaw संदर्भ साफ करता है, `~/.openclaw/extensions/metaclaw-openclaw/` हटाता है, `~/.metaclaw/` हटाता है, pip पैकेज अनइंस्टॉल करता है और OpenClaw गेटवे को पुनः आरंभ करता है। हटाने से पहले पुष्टि मांगी जाती है।

अनइंस्टॉल के बाद, यदि आपने रिपॉजिटरी क्लोन की थी तो उसे मैन्युअल रूप से हटाएं:

```bash
rm -rf /path/to/MetaClaw
```

---

## 📚 उद्धरण

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

## 🙏 आभार

MetaClaw निम्नलिखित ओपन-सोर्स परियोजनाओं पर आधारित है:

- [OpenClaw](https://openclaw.ai) , कोर Agent फ़्रेमवर्क।
- [SkillRL](https://github.com/aiming-lab/SkillRL) , हमारा Skill-संवर्धित RL फ़्रेमवर्क।
- [Tinker](https://www.thinkingmachines.ai/tinker/) , ऑनलाइन RL ट्रेनिंग के लिए।
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) , ऑनलाइन RL ट्रेनिंग का वैकल्पिक बैकएंड।
- [Weaver](https://github.com/nex-agi/weaver) , ऑनलाइन RL ट्रेनिंग का वैकल्पिक बैकएंड।
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) , हमारे RL डिज़ाइन की प्रेरणा।
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) , हमारे Skill बैंक की नींव।
- [NanoClaw](https://github.com/qwibitai/nanoclaw) , qwibitai का व्यक्तिगत Claude Agent, `/v1/messages` Anthropic-संगत एंडपॉइंट के माध्यम से कनेक्ट।
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) , NVIDIA का OpenShell इनफरेंस Agent प्लगइन।

---

## 📄 लाइसेंस

यह प्रोजेक्ट [MIT लाइसेंस](LICENSE) के तहत लाइसेंस प्राप्त है।
