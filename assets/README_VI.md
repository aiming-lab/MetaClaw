<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# Chi can noi chuyen voi agent cua ban, no se hoc hoi va *TIEN HOA*.

<p>Lay cam hung tu cach bo nao hoc tap. Meta-learning va tien hoa 🦞 cua ban tu moi cuoc hoi thoai thuc te. Khong can GPU. Ho tro Kimi, Qwen, Claude, MiniMax va nhieu hon nua.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Hoàn_toàn_bất_đồng_bộ-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Không_cần_GPU-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Tiến_hóa_Skill-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Triển_khai_một_cú_nhấp-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇵🇹 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇸🇦 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[Tong quan](#-tong-quan) • [Bat dau nhanh](#-bat-dau-nhanh) • [Cau hinh](#️-cau-hinh) • [Che do Skills](#-che-do-skills) • [Che do RL](#-che-do-rl) • [Che do Auto](#-che-do-auto-mac-dinh) • [Trich dan](#-trich-dan)

</div>

---

<div align="center">

### Hai lenh. Vay la xong.
</div>

```bash
metaclaw setup              # trinh huong dan cau hinh lan dau
metaclaw start              # mac dinh: che do auto, Skills + huan luyen RL theo lich
metaclaw start --mode rl    # RL khong co bo lap lich (huan luyen ngay khi du batch)
metaclaw start --mode skills_only  # chi Skills, khong RL (khong can Tinker)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 Tin moi

- **[19/04/2026]** **v0.4.2** — Tich hop context-engine OpenClaw: plugin bo nho dang ky la context-engine (vong doi assemble/compact) tren OpenClaw v2026.4.10+, loai bo su trung lap bo nho. Them capture tang dan moi luot voi flush cuoi phien, phan cau hinh tuong thich OpenClaw va che active memory cho injection skill tai proxy.
- **[11/04/2026]** **v0.4.1** — Nap bo nho tang dan: lop bo nho gio trich xuat va luu moi N luot (mac dinh 5) thay vi chi cuoi phien, giam thoi gian bo nho bi trong giua phien. Them cac endpoint sidecar moi `/buffer_turn` va `/flush_session`, benchmark voi co `--buffer-turns` va bao cao so sanh thuc nghiem.
- **[25/03/2026]** **v0.4.0** — Contexture layer: MetaClaw gio day luu tru bo nho xuyen phien lam viec cho nguoi dung va du an. Cac su kien, so thich va lich su du an lien quan duoc tu dong truy xuat va them vao prompt. Bao gom chinh sach bo nho thich ung, hop nhat nen va dich vu sidecar bo nho tuy chon.
- **[16/03/2026]** **v0.3.2** Ho tro da Claw: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw va NemoClaw nay duoc ho tro cung voi OpenClaw. NanoClaw qua endpoint tuong thich Anthropic `/v1/messages` moi; NemoClaw qua dinh tuyen suy luan OpenShell. Them OpenRouter lam nen tang LLM.
- **[13/03/2026]** **v0.3.1** MinT backend duoc ho tro: huan luyen RL hien ho tro ca Tinker va MinT. Cau hinh qua `rl.backend` (auto/tinker/mint).
- **[13/03/2026]** **v0.3** Ho tro meta-learning lien tuc: cap nhat RL cham chi chay trong gio ngu, thoi gian ranh hoac cuoc hop Google Calendar. Them phan tach tap support/query de ngan tin hieu thuong qua thoi lam nhiem mo hinh.
- **[11/03/2026]** **v0.2** Trien khai mot cu nhap qua `metaclaw` CLI. Skill duoc bat mac dinh, RL la tuy chon.
- **[09/03/2026]** Phat hanh **MetaClaw**. Chi can noi chuyen voi agent cua ban va de no tu dong tien hoa. **Khong can** trien khai GPU, chi can ket noi **API**.

---

## 🎥 Demo

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Tong quan

**MetaClaw la mot agent meta-learning va tien hoa trong moi truong thuc te.**
Chi can noi chuyen voi agent nhu binh thuong. MetaClaw bien moi cuoc hoi thoai truc tiep thanh tin hieu hoc tap, giup agent lien tuc cai thien thong qua trien khai thuc te thay vi chi huan luyen ngoai tuyen.

Ben trong, MetaClaw dat mo hinh cua ban phia sau mot proxy tuong thich OpenAI (cung cap endpoint tuong thich Anthropic `/v1/messages` cho cac agent nhu NanoClaw), chan cac tuong tac tu OpenClaw, NanoClaw, NemoClaw va cac Agent duoc ho tro khac, tiem cac Skill phu hop o moi luot hoi thoai va meta-learning tu kinh nghiem tich luy. Skill duoc tu dong tom tat sau moi phien; khi bat RL, bo lap lich meta-learning se hoan cap nhat trong so den cac khoang thoi gian ranh de agent khong bi gian doan khi dang su dung.

Khong can cum GPU. MetaClaw hoat dong voi bat ky LLM API tuong thich OpenAI nao va su dung backend tuong thich Tinker de huan luyen LoRA tren dam may. [Tinker](https://www.thinkingmachines.ai/tinker/) la duong dan tham chieu mac dinh, con MinT hoac Weaver co the duoc kich hoat thong qua goi tuong thich rieng khi can.

## 🤖 Tinh nang chinh

### **Trien khai mot cu nhap**
Cau hinh mot lan voi `metaclaw setup`, sau do `metaclaw start` se khoi dong proxy, tiem Skill va ket noi OpenClaw tu dong. Khong can viet script shell thu cong.

### **Ba che do van hanh**

| Che do | Mac dinh | Mo ta |
|--------|----------|-------|
| `skills_only` | | Proxy toi LLM API cua ban. Tiem Skill va tu dong tom tat sau moi phien. Khong can GPU / Tinker. |
| `rl` | | Skill + huan luyen RL (GRPO). Huan luyen ngay khi batch day. OPD tuy chon de chung cat tu mo hinh giao vien. |
| `auto` | ✅ | Skill + RL + bo lap lich thong minh. Cap nhat trong so RL chi chay trong khoang ngu/ranh/hop. |

### **Bộ nhớ dài hạn**
MetaClaw có thể lưu sự kiện, sở thích và lịch sử dự án qua các phiên và chèn ngữ cảnh liên quan mỗi lượt — để agent nhớ những gì bạn đã nói, kể cả nhiều tuần sau.

### **Thiet ke hoan toan bat dong bo**
Phuc vu, mo hinh hoa phan thuong va huan luyen duoc tach roi hoan toan. Agent tiep tuc phan hoi trong khi cham diem va toi uu hoa chay song song.

---

## 🚀 Bat dau nhanh

### 1. Cai dat

**OpenClaw (một cú nhấp):** dùng bản phát hành [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0) — chạy các lệnh bên dưới, rồi `metaclaw setup` và `metaclaw start`. Chi tiết (Windows, mirror, cấu hình, xử lý sự cố): [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md).

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip** (PyPI hoặc kho mã này):

```bash
pip install -e .                        # che do skills_only (nhe)
pip install -e ".[rl]"                  # + ho tro huan luyen RL (torch, transformers, tinker)
pip install -e ".[evolve]"              # + tien hoa Skill qua LLM tuong thich OpenAI
pip install -e ".[scheduler]"           # + tich hop Google Calendar cho bo lap lich
pip install -e ".[rl,evolve,scheduler]" # khuyen nghi: cau hinh day du RL + bo lap lich
```
(Tùy chọn) Tích hợp WeChat sử dụng plugin chính thức @tencent-weixin/openclaw-weixin. MetaClaw tự động cài đặt nó khi WeChat được bật:

```bash
metaclaw config wechat.enabled true
metaclaw start
```

Plugin được cài đặt tự động khi bắt đầu MetaClaw. Bạn cũng có thể cài đặt nó theo cách thủ công:

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

Để chuyển đổi tài khoản WeChat (đăng nhập lại bằng mã QR mới):

```bash
metaclaw start --wechat-relogin
```

Neu ban muon su dung `rl.backend=mint`, hay cai dat goi tuong thich MinT rieng trong cung moi truong, vi du [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). Neu ban muon su dung `rl.backend=weaver`, hay cai dat [`nex-weaver`](https://github.com/nex-agi/weaver) rieng. MetaClaw khong dua cac phu thuoc nay vao goi mac dinh de nguoi dung RL co the chon ro rang Tinker, MinT hoac Weaver.

### 2. Cau hinh

```bash
metaclaw setup
```

Trình hướng dẫn tương tác sẽ yêu cầu bạn:
1. **Chọn agent cá nhân** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` hoặc `none` (MetaClaw tự cấu hình khi khởi động)
2. **Chọn nhà cung cấp LLM** — Kimi, Qwen, OpenAI, Volcano Engine hoặc tùy chỉnh
3. **Nhập khóa API** và tùy chọn bật huấn luyện RL

Duong dan RL cua MetaClaw co the chuyen doi ro rang giua `tinker`, `mint` va `weaver`. `auto` la gia tri mac dinh duoc khuyen nghi va van se tu dong nhan dien MinT hoac Weaver tu cac thong tin xac thuc hoac base URL tuong ung khi goi da duoc cai dat.

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

Cac bi danh cu `rl.tinker_api_key` va `rl.tinker_base_url` van duoc chap nhan de tuong thich nguoc.

### 3. Khoi dong

```bash
metaclaw start
```

Xong. MetaClaw khoi dong proxy, tu cau hinh agent ca nhan da chon va khoi dong lai gateway. Mo agent va tro chuyen — skill duoc chen moi luot va phien duoc tom tat tu dong thanh skill moi khi ket thuc.

---

## ⚙️ Cau hinh

Tep cau hinh nam tai `~/.metaclaw/config.yaml`, duoc tao boi `metaclaw setup`.

**Lenh CLI:**

```
metaclaw setup                  # Trinh huong dan cau hinh lan dau
metaclaw start                  # Khoi dong MetaClaw (mac dinh: che do auto)
metaclaw start --mode rl        # Bat che do RL cho phien nay (khong co bo lap lich)
metaclaw start --mode skills_only  # Bat che do chi Skills cho phien nay
metaclaw stop                   # Dung phien ban MetaClaw dang chay
metaclaw status                 # Kiem tra tinh trang proxy, che do chay va trang thai bo lap lich
metaclaw config show            # Xem cau hinh hien tai
metaclaw config KEY VALUE       # Dat gia tri cau hinh
metaclaw config llm.oauth_token TOKEN               # Luu token OAuth cho nha cung cap CLI hien tai
metaclaw auth paste-token --provider anthropic      # Luu token OAuth (anthropic | openai-codex | gemini)
metaclaw auth status                                # Hien thi tat ca cac ho so xac thuc da luu
metaclaw uninstall              # Xoa tat ca du lieu MetaClaw, phan mo rong OpenClaw va goi pip
```

Su dung `metaclaw status` de kiem tra trang thai san sang va `metaclaw stop` de dung tien trinh.

<details>
<summary><b>Tham chieu cau hinh day du (nhan de mo rong)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # vi du oauth_token (token luu bang `metaclaw auth paste-token`):
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

proxy:
  port: 30000
  api_key: ""              # tuy chon: bearer token cho proxy MetaClaw cuc bo

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # thu muc thu vien Skill cua ban
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # gioi han Skill theo nhiem vu (mac dinh 10)
  auto_evolve: true         # tu dong tom tat Skill sau moi phien

rl:
  enabled: false            # dat thanh true de bat huan luyen RL
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # endpoint backend tuy chon, vi du https://mint.macaron.xin/ cho MinT hoac https://weaver-console.nex-agi.cn cho Weaver
  tinker_api_key: ""        # bi danh tuong thich cho api_key
  tinker_base_url: ""       # bi danh tuong thich cho base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # tuy chon: duong dan checkpoint de tiep tuc huan luyen
  evolver_api_base: ""      # de trong se tai su dung llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # dat thanh true de bat OPD (chung cat giao vien)
  teacher_url: ""           # URL goc cua mo hinh giao vien (tuong thich OpenAI /v1/completions)
  teacher_model: ""         # ten mo hinh giao vien (vi du Qwen/Qwen3-32B)
  teacher_api_key: ""       # API key cua mo hinh giao vien
  kl_penalty_coef: 1.0      # he so phat KL cho OPD

max_context_tokens: 20000   # gioi han token prompt truoc khi cat; 0 = khong cat
                            # (khuyen nghi trong skills_only voi mo hinh cloud ngu canh lon)
context_window: 0           # cua so ngu canh bao cho agent (vi du nguong nen OpenClaw);
                            # 0 = tu dong (khoang 200 000 trong skills_only, 32 768 trong rl/auto)

scheduler:                  # v0.3: bo lap lich meta-learning (tu dong bat trong che do auto)
  enabled: false            # che do auto tu dong bat; che do rl can dat thu cong
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

## 💪 Che do Skills

**`metaclaw start --mode skills_only`**

Che do nhe nhat. Khong can GPU, khong can backend RL. MetaClaw dat LLM cua ban phia sau mot proxy tiem cac Skill phu hop o moi luot hoi thoai, sau do tu dong tom tat Skill moi sau moi cuoc hoi thoai.

Với nhà cung cấp tùy chỉnh tương thích OpenAI, đặt `llm.api_base` thành URL cơ sở đầy đủ của API chat (thường kết thúc bằng `/v1`, ví dụ `https://your-gateway.example/v1`). Ở chế độ `skills_only`, MetaClaw tái sử dụng cùng endpoint đó để nén prompt và các lời gọi LLM phụ trợ, trừ khi bạn cấu hình endpoint evolver riêng.

Skill la cac huong dan Markdown ngan duoc luu trong `~/.metaclaw/skills/` duoi dang cac tep `SKILL.md` rieng le. Thu vien Skill se lon dan tu dong theo qua trinh su dung.

De tai truoc kho Skill co san (hon 40 Skill bao gom lap trinh, bao mat, tac vu agent, v.v.):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 Che do RL

**`metaclaw start --mode rl`**

Tat ca tinh nang cua Che do Skills, cong them tinh chinh RL lien tuc tu cac cuoc hoi thoai truc tiep. Moi luot hoi thoai duoc tokenize va gui di lam mau huan luyen. LLM giam khao (PRM) cham diem phan hoi bat dong bo, va backend tuong thich Tinker (Tinker cloud, MinT hoac Weaver) thuc hien tinh chinh LoRA voi cap nhat nong trong so.

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

LLM tien hoa chuyen dung cung trich xuat Skill moi tu cac episode that bai, dua chung tro lai thu vien Skill.

**Rollout tu dong** (khong can OpenClaw TUI): dat `openclaw_env_data_dir` thanh thu muc chua cac tep JSONL nhiem vu:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### On-Policy Distillation (OPD)

OPD la thanh phan bo sung tuy chon cho Che do RL. No chung cat mo hinh giao vien lon hon vao hoc sinh theo chinh sach truc tuyen: hoc sinh tao phan hoi binh thuong, con giao vien cung cap xac suat log tung token tren cung phan hoi do. Phat KL huong dan hoc sinh tien gan phan phoi cua giao vien.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

Mo hinh giao vien can duoc phuc vu qua endpoint `/v1/completions` tuong thich OpenAI (vi du vLLM, SGLang). OPD co the ket hop voi cham diem PRM, ca hai deu chay bat dong bo. Xem `examples/run_conversation_opd.py` va `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 Che do Auto (Mac dinh)

**`metaclaw start`**

Tat ca tinh nang cua Che do RL, cong them bo lap lich meta-learning hoan cap nhat trong so den cac khoang thoi gian nguoi dung khong hoat dong, dam bao agent khong bi gian doan khi dang su dung. Day la che do mac dinh.

Buoc cap nhat nong trong so RL tam dung agent trong vai phut. Thay vi huan luyen ngay khi batch day (nhu Che do RL), che do auto cho doi mot cua so thich hop.

Ba dieu kien kich hoat cua so cap nhat (chi can mot trong ba):

- **Gio ngu**: thoi gian bat dau/ket thuc co the cau hinh (vi du 23:00 den 07:00)
- **Ban phim khong hoat dong**: kich hoat sau N phut khong hoat dong
- **Su kien Google Calendar**: phat hien cuoc hop de chay cap nhat khi ban vang mat

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# Tuy chon: tich hop Google Calendar
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

Neu nguoi dung quay lai giua chung, batch chua hoan thanh se duoc luu va tiep tuc o cua so tiep theo.

Moi `ConversationSample` duoc gan nhan phien ban `skill_generation`. Khi tien hoa Skill tang generation, bo dem RL se duoc xoa sach va chi su dung cac mau sau tien hoa cho cap nhat gradient (phan tach tap support/query theo MAML).

---

## 🗑️ Go cai dat

```bash
metaclaw uninstall
```

Xoa tat ca trong mot buoc: dung phien ban dang chay, don sach tham chieu MetaClaw trong `~/.openclaw/openclaw.json`, xoa `~/.openclaw/extensions/metaclaw-openclaw/`, xoa `~/.metaclaw/`, go cai dat goi pip va khoi dong lai cong OpenClaw. Ban se duoc yeu cau xac nhan truoc khi xoa.

Sau khi go cai dat, xoa thu muc repo thu cong neu ban da clone:

```bash
rm -rf /path/to/MetaClaw
```

---

## 📚 Trich dan

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

## 🙏 Loi cam on

MetaClaw duoc xay dung tren cac du an ma nguon mo sau:

- [OpenClaw](https://openclaw.ai) , framework agent cot loi.
- [SkillRL](https://github.com/aiming-lab/SkillRL) , framework RL tang cuong Skill cua chung toi.
- [Tinker](https://www.thinkingmachines.ai/tinker/) , dung cho huan luyen RL truc tuyen.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) , backend thay the cho huan luyen RL truc tuyen.
- [Weaver](https://github.com/nex-agi/weaver) , backend thay the cho huan luyen RL truc tuyen.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) , nguon cam hung cho thiet ke RL cua chung toi.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) , cung cap nen tang cho kho Skill cua chung toi.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) , agent Claude ca nhan cua qwibitai, ket noi qua endpoint tuong thich Anthropic `/v1/messages`.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) , plugin agent OpenShell cua NVIDIA cho suy luan.

---

## 📄 Giay phep

Du an nay duoc cap phep theo [Giay phep MIT](LICENSE).
