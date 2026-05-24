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

[개요](#-개요) • [빠른 시작](#-빠른-시작) • [설정](#️-설정) • [스킬 모드](#-스킬-모드) • [RL 모드](#-rl-모드) • [Auto 모드](#-auto-모드-기본) • [인용](#-인용)

</div>

---

<div align="center">

### 명령어 두 개. 그게 전부입니다.
</div>

```bash
metaclaw setup              # 최초 설정 마법사
metaclaw start              # 기본: auto 모드, 스킬 + 예약된 RL 학습
metaclaw start --mode rl    # 스케줄러 없는 RL (배치가 차면 즉시 학습)
metaclaw start --mode skills_only  # 스킬만, RL 없음 (Tinker 불필요)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 새소식

- **[2026/04/19]** **v0.4.2** — OpenClaw 컨텍스트 엔진 통합: 메모리 플러그인이 OpenClaw v2026.4.10+의 컨텍스트 엔진(assemble/compact 라이프사이클)으로 등록되어 메모리 이중 주입을 제거. 턴별 증분 캡처와 세션 종료 플러시, OpenClaw 호환성 설정 섹션, 프록시 측 스킬 주입을 위한 활성 메모리 억제 추가.
- **[2026/04/11]** **v0.4.1** — 증분 메모리 수집: 메모리 레이어가 세션 종료 시점뿐 아니라 N 턴(기본 5)마다 추출하고 저장하도록 변경되어 세션 중간의 메모리 공백 구간이 줄어듦. 새로운 `/buffer_turn`·`/flush_session` 사이드카 엔드포인트, `--buffer-turns` 플래그를 지원하는 벤치마크, 실험 비교 리포트 추가.
- **[2026/03/25]** **v0.4.0** — Contexture layer（컨텍스처 레이어）：MetaClaw가 사용자와 프로젝트의 메모리를 세션을 넘어 지속적으로 저장. 관련 사실, 선호도, 프로젝트 히스토리를 자동으로 검색해 프롬프트에 주입. 적응형 메모리 정책, 백그라운드 통합, 선택적 메모리 사이드카 서비스 포함.
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

GPU 클러스터가 필요 없습니다. MetaClaw는 OpenAI 호환 LLM API와 함께 동작하며, 클라우드 기반 LoRA 학습에는 Tinker 호환 백엔드를 사용합니다. [Tinker](https://www.thinkingmachines.ai/tinker/)가 기본 기준 경로이고, 필요하면 별도 호환 패키지를 통해 MinT 또는 Weaver도 활성화할 수 있습니다.

## 🤖 주요 기능

### **원클릭 배포**
`metaclaw setup`으로 한 번 설정하면, `metaclaw start`로 프록시 시작, 스킬 주입, OpenClaw 연결까지 자동화됩니다. 수동 쉘 스크립트 불필요.

### **세 가지 동작 모드**

| 모드 | 기본값 | 기능 |
|------|--------|------|
| `skills_only` | | LLM API 프록시. 스킬 주입, 세션 후 자동 요약. GPU/Tinker 불필요. |
| `rl` | | 스킬 + RL 학습(GRPO). 배치가 차면 즉시 학습. 교사 증류를 위한 선택적 OPD. |
| `auto` | ✅ | 스킬 + RL + 스마트 스케줄러. RL 가중치 업데이트는 수면/유휴/회의 창에서만 실행. |

### **장기 기억**
MetaClaw는 세션 간에 사실·선호·프로젝트 기록을 유지하고 매 턴마다 관련 컨텍스트를 넣을 수 있어, 몇 주가 지나도 에이전트가 당신이 말한 내용을 기억합니다.

### **설계 단계의 비동기 처리**
서빙, 보상 모델링, 학습이 완전히 분리됩니다. 에이전트가 응답하는 동안 채점과 최적화가 병렬로 실행됩니다.

---

## 🚀 빠른 시작

### 1. 설치

**OpenClaw(원클릭):** 릴리스 [v0.4.0](https://github.com/aiming-lab/MetaClaw/releases/tag/v0.4.0)을 사용하고 아래 명령을 실행한 뒤 `metaclaw setup` 및 `metaclaw start`를 실행하세요. 자세한 내용(Windows, 미러, 설정, 문제 해결): [`extensions/metaclaw-openclaw/README.md`](../extensions/metaclaw-openclaw/README.md).

```bash
curl -LO https://github.com/aiming-lab/MetaClaw/releases/download/v0.4.0/metaclaw-plugin.zip
unzip metaclaw-plugin.zip -d ~/.openclaw/extensions
openclaw plugins enable metaclaw-openclaw && openclaw gateway restart
```

**pip**(PyPI 또는 이 저장소):

```bash
pip install -e .                        # skills_only 모드 (경량)
pip install -e ".[rl]"                  # + RL 학습 지원 (torch, transformers, tinker)
pip install -e ".[evolve]"              # + OpenAI 호환 LLM을 통한 스킬 진화
pip install -e ".[scheduler]"           # + Google Calendar 스케줄러 통합
pip install -e ".[rl,evolve,scheduler]" # 권장: 전체 RL + 스케줄러 설정
```
(선택) WeChat 통합은 공식 @tencent-weixin/openclaw-weixin 플러그인을 사용합니다. WeChat이 활성화되면 MetaClaw가 자동으로 설치합니다:

```bash
metaclaw config wechat.enabled true
metaclaw start
```

플러그인은 MetaClaw 시작 시 자동으로 설치됩니다. 다음과 같이 수동으로 설치할 수도 있습니다:

```bash
npx -y @tencent-weixin/openclaw-weixin-cli@latest install
```

WeChat 계정을 전환하려면 (새 QR 코드로 다시 로그인):

```bash
metaclaw start --wechat-relogin
```

`rl.backend=mint`를 사용하려면 같은 환경에 MinT 호환 패키지를 별도로 설치하세요. 예를 들면 [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit)입니다. `rl.backend=weaver`를 사용하려면 [`nex-weaver`](https://github.com/nex-agi/weaver)를 별도로 설치하세요. MetaClaw는 이러한 의존성을 기본 패키지에 넣지 않아 RL 사용자가 Tinker, MinT, Weaver를 명시적으로 선택할 수 있게 합니다.

### 2. 설정

```bash
metaclaw setup
```

대화형 마법사에서 다음을 묻습니다:
1. **개인 에이전트 선택** — `openclaw`, `copaw`, `ironclaw`, `picoclaw`, `zeroclaw`, `nanoclaw`, `nemoclaw` 또는 `none`(시작 시 MetaClaw가 자동 구성)
2. **LLM 제공자 선택** — Kimi, Qwen, OpenAI, Volcano Engine 또는 사용자 정의
3. **API 키 입력** 및 선택적으로 RL 학습 활성화

MetaClaw의 RL 경로는 `tinker`, `mint`, `weaver`를 명시적으로 전환할 수 있습니다. 권장 기본값은 `auto`이며, MinT 또는 Weaver 패키지가 설치되어 있으면 해당 스타일의 credentials나 base URL로 자동 추론할 수 있습니다.

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

하위 호환성을 위해 기존 `rl.tinker_api_key`와 `rl.tinker_base_url`도 계속 지원합니다.

### 3. 시작

```bash
metaclaw start
```

끝입니다. MetaClaw가 프록시를 시작하고 선택한 개인 에이전트를 자동으로 설정한 뒤 게이트웨이를 다시 시작합니다. 에이전트를 열고 대화하세요 — 매 턴마다 스킬이 주입되고 세션이 끝나면 새 스킬로 자동 요약됩니다.

---

## ⚙️ 설정

설정 파일은 `~/.metaclaw/config.yaml`에 저장되며, `metaclaw setup`으로 생성됩니다.

**CLI 명령어:**

```
metaclaw setup                  # 최초 대화형 설정 마법사
metaclaw start                  # MetaClaw 시작 (기본: auto 모드)
metaclaw start --mode rl        # 이 세션에서 RL 모드 강제 적용 (스케줄러 없음)
metaclaw start --mode skills_only  # 이 세션에서 스킬 전용 모드 강제 적용
metaclaw stop                   # 실행 중인 MetaClaw 인스턴스 중지
metaclaw status                 # 프록시 상태, 실행 모드 및 스케줄러 상태 확인
metaclaw config show            # 현재 설정 보기
metaclaw config KEY VALUE       # 설정값 변경
metaclaw config llm.oauth_token TOKEN               # 현재 CLI 프로바이더의 OAuth 토큰 저장
metaclaw auth paste-token --provider anthropic      # OAuth 토큰 저장 (anthropic | openai-codex | gemini)
metaclaw auth status                                # 저장된 모든 인증 프로필 표시
metaclaw uninstall              # 모든 MetaClaw 데이터, OpenClaw 확장, pip 패키지 삭제
```

`metaclaw status`로 준비 상태를 확인하고 `metaclaw stop`으로 프로세스를 중지할 수 있습니다.

<details>
<summary><b>전체 설정 참조 (클릭하여 펼치기)</b></summary>

```yaml
mode: auto                 # "auto" | "rl" | "skills_only"
claw_type: openclaw        # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" | "nanoclaw" | "nemoclaw" | "hermes" | "none"

llm:
  auth_method: api_key      # "api_key" | "oauth_token"
  provider: kimi            # kimi | qwen | openai | minimax | novita | openrouter | volcengine | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...
  # oauth_token 예시 (토큰은 `metaclaw auth paste-token`으로 저장):
  # auth_method: oauth_token
  # provider: anthropic     # anthropic | openai-codex | gemini
  # model_id: claude-sonnet-4-6

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
  backend: auto             # "auto" | "tinker" | "mint" | "weaver"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # 선택적 backend endpoint. 예: MinT용 https://mint.macaron.xin/ 또는 Weaver용 https://weaver-console.nex-agi.cn
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

max_context_tokens: 20000   # 잘라내기 전 프롬프트 토큰 상한；0 = 잘라내지 않음
                            # (대용량 컨텍스트 클라우드 모델의 skills_only에 권장)
context_window: 0           # 에이전트에 알리는 컨텍스트 창(예: OpenClaw 압축 임계값)；
                            # 0 = 자동(skills_only에서 약 200000, rl/auto에서 32768)

scheduler:                  # v0.3: 메타러닝 스케줄러 (auto 모드에서 자동 활성화)
  enabled: false            # auto 모드에서 자동 활성화; rl 모드에서는 수동 설정
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

OpenAI 호환 사용자 정의 제공자의 경우 `llm.api_base`를 전체 채팅 API 베이스(보통 `/v1`로 끝남, 예: `https://your-gateway.example/v1`)로 설정하세요. `skills_only` 모드에서는 별도의 evolver 엔드포인트를 설정하지 않으면 프롬프트 압축 및 관련 보조 LLM 호출에 동일한 엔드포인트가 재사용됩니다.

스킬은 `~/.metaclaw/skills/`에 개별 `SKILL.md` 파일로 저장되는 짧은 Markdown 지침입니다. 사용과 함께 라이브러리가 자동으로 성장합니다.

내장 스킬 뱅크를 미리 로드하려면 (코딩, 보안, 에이전트 작업 등 40개 이상의 스킬):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL 모드

**`metaclaw start --mode rl`**

스킬 모드의 모든 기능에 더해, 실시간 대화로부터 지속적인 RL 파인튜닝을 수행합니다. 각 대화 턴이 토크나이즈되어 학습 샘플로 제출됩니다. 심판 LLM(PRM)이 비동기로 응답을 채점하고, Tinker 호환 백엔드(Tinker 클라우드, MinT 또는 Weaver)가 가중치 핫스왑과 함께 LoRA 파인튜닝을 실행합니다.

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

## 🧠 Auto 모드 (기본)

**`metaclaw start`**

RL 모드의 모든 기능에 더해, 메타러닝 스케줄러가 가중치 업데이트를 사용자 비활성 창으로 연기하여 활성 사용 중에 에이전트가 중단되지 않도록 합니다. 기본 모드입니다.

RL 가중치 핫스왑 단계는 에이전트를 수 분간 일시 정지시킵니다. RL 모드처럼 배치가 차면 즉시 학습하는 대신, auto 모드는 적절한 창을 기다립니다.

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

## 🗑️ 제거

```bash
metaclaw uninstall
```

모든 것을 한 번에 삭제합니다: 실행 중인 인스턴스 중지, `~/.openclaw/openclaw.json`에서 MetaClaw 참조 제거, `~/.openclaw/extensions/metaclaw-openclaw/` 삭제, `~/.metaclaw/` 삭제, pip 패키지 제거, OpenClaw 게이트웨이 재시작. 삭제 전 확인을 요청합니다.

제거 후 리포지토리를 클론했다면 수동으로 삭제하세요:

```bash
rm -rf /path/to/MetaClaw
```

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
- [Weaver](https://github.com/nex-agi/weaver) 온라인 RL 학습의 대체 백엔드.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) RL 설계의 영감.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) 스킬 뱅크의 기반 제공.
- [NanoClaw](https://github.com/qwibitai/nanoclaw) qwibitai의 개인 Claude Agent, `/v1/messages` 호환 엔드포인트로 연결.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw) NVIDIA의 OpenShell 추론 Agent 플러그인.

---

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.
