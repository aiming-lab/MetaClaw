<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# 에이전트와 대화하기만 하면 됩니다, 학습하고 *진화*합니다.

<p>뇌의 학습 방식에서 영감을 받았습니다. 모든 대화에서 🦞 를 메타학습하고 진화시킵니다. GPU 불필요. Kimi, Qwen, Claude, MiniMax 등 지원.</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_완전_비동기-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_GPU_클러스터_불필요-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_스킬_진화-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_원클릭_배포-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇦🇪 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[개요](#-개요) • [빠른 시작](#-빠른-시작) • [설정](#️-설정) • [스킬 모드](#-스킬-모드) • [RL 모드](#-rl-모드) • [MadMax 모드](#-madmax-모드-기본) • [인용](#-인용)

</div>

---

<div align="center">

### 명령어 두 개. 그게 전부입니다.
</div>

```bash
metaclaw setup              # 최초 설정 마법사
metaclaw start              # 기본: madmax 모드, 스킬 + 예약된 RL 학습
metaclaw start --daemon     # 백그라운드에서 실행, 로그 -> ~/.metaclaw/metaclaw.log
metaclaw start --daemon --log-file /tmp/metaclaw.log  # 사용자 지정 로그 경로
metaclaw start --mode rl    # 스케줄러 없는 RL (배치가 차면 즉시 학습)
metaclaw start --mode skills_only  # 스킬만, RL 없음 (Tinker 불필요)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 새소식

- **[2026/03/16]** **v0.3.2** 멀티 Claw 지원: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw, NemoClaw가 OpenClaw와 함께 지원됨. NanoClaw는 새로운 `/v1/messages` Anthropic 호환 엔드포인트를 통해, NemoClaw는 OpenShell 추론 라우팅을 통해 연결. OpenRouter를 LLM 플랫폼으로 추가.
- **[2026/03/13]** **v0.3.1** MinT 백엔드 지원: RL 학습이 Tinker와 MinT 모두에서 작동. `rl.backend`(auto/tinker/mint)로 설정 가능.
- **[2026/03/13]** **v0.3** 지속적 메타러닝 지원: RL 가중치 업데이트를 수면 시간, 유휴 시간, Google Calendar 회의 중에만 실행. support/query 집합 분리를 추가하여 오래된 보상 신호가 모델 업데이트를 오염시키는 것을 방지.
- **[2026/03/11]** **v0.2** `metaclaw` CLI를 통한 원클릭 배포. 스킬은 기본 활성화, RL은 이제 선택적으로 적용.
- **[2026/03/09]** **MetaClaw** 출시. 에이전트와 대화하면 자동으로 진화. GPU 배포 **불필요**, **API**만 연결하면 됩니다.

---

## 🎥 데모

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 개요

**MetaClaw는 실제 환경에서 메타러닝하며 진화하는 에이전트입니다.**
평소처럼 에이전트와 대화하기만 하면 MetaClaw가 모든 실시간 대화를 학습 신호로 변환하여, 오프라인 학습에만 의존하지 않고 실제 배포를 통해 에이전트를 지속적으로 개선합니다.

내부적으로 모델을 OpenAI 호환 프록시 뒤에 배치하고(NanoClaw 같은 Anthropic 네이티브 에이전트를 위해 `/v1/messages` 호환 엔드포인트도 제공), OpenClaw, NanoClaw, NemoClaw 등 지원 에이전트를 통해 인터랙션을 인터셉트하며, 매 턴마다 관련 스킬을 주입하고, 축적된 경험으로부터 메타러닝합니다. 세션 종료 후 스킬이 자동 요약되며, RL 활성화 시 메타러닝 스케줄러가 가중치 업데이트를 유휴 시간대로 연기하여 활성 사용 중 에이전트 중단을 방지합니다.

GPU 클러스터가 필요 없습니다. MetaClaw는 OpenAI 호환 LLM API와 함께 동작하며, 클라우드 기반 LoRA 학습에는 Tinker 호환 백엔드를 사용합니다. [Tinker](https://www.thinkingmachines.ai/tinker/)가 기본 기준 경로이고, 필요하면 별도 호환 패키지를 통해 MinT도 활성화할 수 있습니다.

## 🤖 주요 기능

### **원클릭 배포**
`metaclaw setup`으로 한 번 설정하면, `metaclaw start`로 프록시 시작, 스킬 주입, OpenClaw 연결까지 자동화됩니다. 수동 쉘 스크립트 불필요.

### **세 가지 동작 모드**

| 모드 | 기본값 | 기능 |
|------|--------|------|
| `skills_only` | | LLM API 프록시. 스킬 주입, 세션 후 자동 요약. GPU/Tinker 불필요. |
| `rl` | | 스킬 + RL 학습(GRPO). 배치가 차면 즉시 학습. 교사 증류를 위한 선택적 OPD. |
| `madmax` | ✅ | 스킬 + RL + 스마트 스케줄러. RL 가중치 업데이트는 수면/유휴/회의 창에서만 실행. |

### **설계 단계의 비동기 처리**
서빙, 보상 모델링, 학습이 완전히 분리됩니다. 에이전트가 응답하는 동안 채점과 최적화가 병렬로 실행됩니다.

---

## 🚀 빠른 시작

### 1. 설치

```bash
pip install -e .                        # skills_only 모드 (경량)
pip install -e ".[rl]"                  # + RL 학습 지원 (torch, transformers, tinker)
pip install -e ".[evolve]"              # + OpenAI 호환 LLM을 통한 스킬 진화
pip install -e ".[scheduler]"           # + Google Calendar 스케줄러 통합
pip install -e ".[rl,evolve,scheduler]" # 권장: 전체 RL + 스케줄러 설정
```

`rl.backend=mint`를 사용하려면 같은 환경에 MinT 호환 패키지를 별도로 설치하세요. 예를 들면 [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit)입니다. MetaClaw는 이 의존성을 기본 패키지에 넣지 않아 RL 사용자가 Tinker와 MinT를 명시적으로 선택할 수 있게 합니다.

### 2. 설정

```bash
metaclaw setup
```

대화형 마법사에서 LLM 공급자(Kimi, Qwen, MiniMax, 또는 커스텀), API 키, RL 활성화 여부를 설정합니다.

MetaClaw의 RL 경로는 `tinker`와 `mint`를 명시적으로 전환할 수 있습니다. 권장 기본값은 `auto`이며, MinT 패키지가 설치되어 있으면 Mint 스타일 credentials나 base URL로 MinT를 계속 추론할 수 있습니다.

**Tinker** (기본값):

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

하위 호환성을 위해 기존 `rl.tinker_api_key`와 `rl.tinker_base_url`도 계속 지원합니다.

### 3. 시작

```bash
metaclaw start
```

끝입니다. MetaClaw가 프록시를 시작하고, OpenClaw를 자동 설정하여 게이트웨이를 재시작합니다. OpenClaw를 열고 대화를 시작하세요. 매 턴마다 스킬이 주입되고, 종료 후 자동으로 새 스킬로 요약됩니다.

---

## ⚙️ 설정

설정 파일은 `~/.metaclaw/config.yaml`에 저장되며, `metaclaw setup`으로 생성됩니다.

**CLI 명령어:**

```
metaclaw setup                  # 최초 대화형 설정 마법사
metaclaw start                  # MetaClaw 시작 (기본: madmax 모드)
metaclaw start --daemon         # MetaClaw 백그라운드에서 시작
metaclaw start --daemon --log-file /tmp/metaclaw.log  # 사용자 지정 로그 경로
metaclaw start --mode rl        # 이 세션에서 RL 모드 강제 적용 (스케줄러 없음)
metaclaw start --mode skills_only  # 이 세션에서 스킬 전용 모드 강제 적용
metaclaw stop                   # 실행 중인 MetaClaw 인스턴스 중지
metaclaw status                 # 프록시 상태, 실행 모드 및 스케줄러 상태 확인
metaclaw config show            # 현재 설정 보기
metaclaw config KEY VALUE       # 설정값 변경
```

`--daemon`으로 MetaClaw를 시작하면 로컬 프록시가 정상 작동할 때까지 명령이 대기합니다. `metaclaw status`로 상태를 확인하고 `metaclaw stop`으로 백그라운드 프로세스를 중지할 수 있습니다.

<details>
<summary><b>전체 설정 참조 (클릭하여 펼치기)</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # 로컬 MetaClaw 프록시용 선택적 bearer token

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # 스킬 라이브러리 디렉토리
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # 태스크별 스킬 상한 (기본값 10)
  auto_evolve: true         # 각 세션 후 스킬 자동 요약

rl:
  enabled: false            # true로 설정하면 RL 학습 활성화
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # 선택적 backend endpoint. 예: MinT용 https://mint.macaron.xin/
  tinker_api_key: ""        # api_key의 호환 별칭
  tinker_base_url: ""       # base_url의 호환 별칭
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # 학습 재개 체크포인트 경로 (선택)
  evolver_api_base: ""      # 비워두면 llm.api_base 재사용
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # true로 설정하면 OPD(교사 증류) 활성화
  teacher_url: ""           # 교사 모델 베이스 URL (OpenAI 호환 /v1/completions)
  teacher_model: ""         # 교사 모델명 (예: Qwen/Qwen3-32B)
  teacher_api_key: ""       # 교사 모델 API 키
  kl_penalty_coef: 1.0      # OPD의 KL 페널티 계수

max_context_tokens: 20000   # 잘라내기 전 프롬프트 토큰 상한

scheduler:                  # v0.3: 메타러닝 스케줄러 (madmax 모드에서 자동 활성화)
  enabled: false            # madmax 모드에서 자동 활성화; rl 모드에서는 수동 설정
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

## 💪 스킬 모드

**`metaclaw start --mode skills_only`**

가장 가벼운 모드입니다. GPU도, RL 백엔드도 필요 없습니다. MetaClaw가 LLM을 프록시 뒤에 배치하고, 매 턴마다 관련 스킬을 주입한 뒤, 각 대화 후 새 스킬을 자동 요약합니다.

스킬은 `~/.metaclaw/skills/`에 개별 `SKILL.md` 파일로 저장되는 짧은 Markdown 지침입니다. 사용과 함께 라이브러리가 자동으로 성장합니다.

내장 스킬 뱅크를 미리 로드하려면 (코딩, 보안, 에이전트 작업 등 40개 이상의 스킬):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL 모드

**`metaclaw start --mode rl`**

스킬 모드의 모든 기능에 더해, 실시간 대화로부터 지속적인 RL 파인튜닝을 수행합니다. 각 대화 턴이 토크나이즈되어 학습 샘플로 제출됩니다. 심판 LLM(PRM)이 비동기로 응답을 채점하고, Tinker 호환 백엔드(Tinker 클라우드 또는 MinT)가 가중치 핫스왑과 함께 LoRA 파인튜닝을 실행합니다.

**Tinker** (기본값):

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

전용 에볼버 LLM이 실패한 에피소드에서 새 스킬을 추출하여 스킬 라이브러리에 피드백합니다.

**프로그래매틱 롤아웃** (OpenClaw TUI 불필요): `openclaw_env_data_dir`를 JSONL 태스크 파일 디렉토리로 설정:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### 온폴리시 증류 (OPD)

OPD는 RL 모드의 선택적 추가 기능입니다. 더 큰 교사 모델을 학생 모델에 온폴리시로 증류합니다. 학생 모델이 평소처럼 응답을 생성하고, 교사 모델이 동일한 응답에 대해 토큰별 로그 확률을 제공합니다. KL 페널티가 학생을 교사의 분포 방향으로 유도합니다.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

교사 모델은 OpenAI 호환 `/v1/completions` 엔드포인트(예: vLLM, SGLang)에서 서비스되어야 합니다. OPD는 PRM 채점과 함께 사용할 수 있으며, 두 가지 모두 비동기로 실행됩니다. `examples/run_conversation_opd.py`와 `scripts/run_openclaw_tinker_opd.sh`를 참조하세요.

---

## 🧠 MadMax 모드 (기본)

**`metaclaw start`**

RL 모드의 모든 기능에 더해, 메타러닝 스케줄러가 가중치 업데이트를 사용자 비활성 창으로 연기하여 활성 사용 중에 에이전트가 중단되지 않도록 합니다. 기본 모드입니다.

RL 가중치 핫스왑 단계는 에이전트를 수 분간 일시 정지시킵니다. RL 모드처럼 배치가 차면 즉시 학습하는 대신, MadMax는 적절한 창을 기다립니다.

세 가지 조건이 업데이트 창을 트리거합니다 (하나만 충족하면 충분):

- **수면 시간**: 시작/종료 시간 설정 가능 (예: 23:00~07:00)
- **키보드 비활성**: N분간 유휴 시 트리거
- **Google Calendar 이벤트**: 회의를 감지하여 자리를 비운 동안 업데이트 실행

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# 선택 사항: Google Calendar 통합
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

사용자가 업데이트 중에 돌아오면, 부분 배치가 저장되고 다음 창에서 재개됩니다.

각 `ConversationSample`에는 `skill_generation` 버전이 태그됩니다. 스킬 진화가 generation을 증가시키면, RL 버퍼가 플러시되어 진화 후 샘플만 그래디언트 업데이트에 사용됩니다 (MAML support/query 집합 분리).

---

## 📚 인용

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

## 🙏 감사의 말

MetaClaw는 다음 오픈소스 프로젝트를 기반으로 구축되었습니다:

- [OpenClaw](https://openclaw.ai) 핵심 에이전트 프레임워크.
- [SkillRL](https://github.com/aiming-lab/SkillRL) 스킬 강화 RL 프레임워크.
- [Tinker](https://www.thinkingmachines.ai/tinker/) 온라인 RL 학습에 사용.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit) 온라인 RL 학습의 대체 백엔드.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) RL 설계의 영감.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) 스킬 뱅크의 기반 제공.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) qwibitai의 개인 Claude Agent, `/v1/messages` 호환 엔드포인트로 연결.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) NVIDIA의 OpenShell 추론 Agent 플러그인.

---

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.
