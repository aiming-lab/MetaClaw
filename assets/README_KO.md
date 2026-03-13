<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# 에이전트와 대화하기만 하면 됩니다 — 학습하고 *진화*합니다.

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_완전_비동기-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_GPU_클러스터_불필요-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_스킬_진화-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_원클릭_배포-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md)

<br/>

[개요](#-개요) • [빠른 시작](#-빠른-시작) • [CLI 참조](#️-cli-참조) • [설정](#️-설정) • [스킬](#-스킬) • [RL 모드](#-고급-rl-모드) • [OPD 모드](#-고급-opd-모드) • [메타러닝 스케줄러](#-고급-메타러닝-스케줄러-v03) • [인용](#-인용)

</div>

---

<div align="center">

### 명령어 두 개. 그게 전부입니다.
</div>

```bash
metaclaw setup              # 최초 설정 마법사
metaclaw start              # 기본: madmax 모드 — 스킬 + 예약된 RL 학습
metaclaw start --mode rl    # 스케줄러 없는 RL (배치가 차면 즉시 학습)
metaclaw start --mode skills_only  # 스킬만, RL 없음 (Tinker 불필요)
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 새소식

- **[2026/03/13]** **v0.3** — 지속적 메타러닝 지원: RL 가중치 업데이트를 수면 시간, 유휴 시간, Google Calendar 회의 중에만 실행. support/query 집합 분리를 추가하여 오래된 보상 신호가 모델 업데이트를 오염시키는 것을 방지.
- **[2026/03/11]** **v0.2** — `metaclaw` CLI를 통한 원클릭 배포. 스킬은 기본 활성화, RL은 이제 선택적으로 적용.
- **[2026/03/09]** **MetaClaw** 출시 — 에이전트와 대화하면 자동으로 진화. GPU 배포 **불필요**, **API**만 연결하면 됩니다.

---

## 🎥 데모

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 개요

**MetaClaw는 실제 환경에서 메타러닝하며 진화하는 에이전트입니다.**
평소처럼 에이전트와 대화하기만 하면 — MetaClaw가 모든 실시간 대화를 학습 신호로 변환하여, 오프라인 학습에만 의존하지 않고 실제 배포를 통해 에이전트를 지속적으로 개선합니다.

내부적으로 모델을 OpenAI 호환 프록시 뒤에 배치하고, OpenClaw를 통해 인터랙션을 인터셉트하며, 매 턴마다 관련 스킬을 주입하고, 축적된 경험으로부터 메타러닝합니다. 세션 종료 후 스킬이 자동 요약되며, RL 활성화 시 메타러닝 스케줄러가 가중치 업데이트를 유휴 시간대로 연기하여 활성 사용 중 에이전트 중단을 방지합니다.

GPU 클러스터가 필요 없습니다. MetaClaw는 OpenAI 호환 LLM API와 함께 동작하며, 선택적으로 **Kimi-K2.5** (1T MoE)를 [Tinker](https://www.thinkingmachines.ai/tinker/)를 통해 클라우드 기반 LoRA 학습에 통합합니다.

## 🤖 주요 기능

### **원클릭 배포**
`metaclaw setup`으로 한 번 설정하면, `metaclaw start`로 프록시 시작·스킬 주입·OpenClaw 연결까지 자동화됩니다. 수동 쉘 스크립트 불필요.

### **세 가지 동작 모드**

| 모드 | 기본값 | 기능 |
|------|--------|------|
| `madmax` | ✅ | RL + 스마트 스케줄러. 스킬은 항상 활성화. RL 가중치 업데이트는 수면/유휴/회의 창에서만 실행. |
| `rl` | — | 스케줄러 없는 RL. 배치가 차면 즉시 학습 (v0.2 동작). |
| `skills_only` | — | 프록시 → LLM API. 스킬 주입, 세션 후 자동 요약. GPU/Tinker 불필요. |

### **스킬 주입**
매 턴마다 MetaClaw가 가장 관련성 높은 스킬 지침을 검색해 에이전트의 시스템 프롬프트에 주입합니다. 재학습 없이 즉시 동작 개선.

### **스킬 자동 요약**
각 대화가 끝날 때마다, 사용 중인 동일한 LLM이 세션을 분석해 새 스킬을 자동 생성합니다. 수동 큐레이션 불필요 — 라이브러리가 사용과 함께 성장합니다.

### **GPU 클러스터 불필요**
`skills_only` 모드는 네트워크 연결만 필요합니다. RL 학습은 Tinker 클라우드에 오프로드됩니다.

### **두 가지 학습 모드**
MetaClaw는 다음 두 가지를 모두 지원합니다:
- **RL(GRPO)**: 암묵적 피드백 신호로부터 학습
- **온폴리시 증류(OPD)**: 더 큰 교사 모델을 학생 모델에 온폴리시로 증류

OPD 모드에서는 학생 모델이 평소와 같이 응답을 생성하고, 교사 모델이 동일한 응답에 대해 토큰별 로그 확률을 제공합니다. 교사의 logprob이 손실 함수(예: `cispo`)에 전달되어 학생이 교사의 분포를 학습합니다. 교사는 OpenAI 호환 `/v1/completions` 엔드포인트(예: vLLM, SGLang)에서 서비스되어야 합니다.

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

### 2. 설정

```bash
metaclaw setup
```

대화형 마법사에서 LLM 공급자(Kimi, Qwen, MiniMax, 또는 커스텀), API 키, RL 활성화 여부를 설정합니다.

### 3. 시작

```bash
metaclaw start
```

끝입니다. MetaClaw가 프록시를 시작하고, OpenClaw를 자동 설정하여 게이트웨이를 재시작합니다. OpenClaw를 열고 대화를 시작하세요 — 매 턴마다 스킬이 주입되고, 종료 후 자동으로 새 스킬로 요약됩니다.

---

## 🛠️ CLI 참조

```
metaclaw setup                  # 최초 대화형 설정 마법사
metaclaw start                  # MetaClaw 시작 (기본: madmax 모드)
metaclaw start --mode rl        # 이 세션에서 RL 모드 강제 적용 (스케줄러 없음)
metaclaw start --mode skills_only  # 이 세션에서 스킬 전용 모드 강제 적용
metaclaw stop                   # 실행 중인 MetaClaw 인스턴스 중지
metaclaw status                 # 프록시 상태, 실행 모드 및 스케줄러 상태 확인
metaclaw config show            # 현재 설정 보기
metaclaw config KEY VALUE       # 설정값 변경
```

**자주 사용하는 설정 키:**

```bash
metaclaw config rl.enabled true           # RL 학습 활성화
metaclaw config rl.tinker_api_key sk-...  # Tinker 키 설정
metaclaw config skills.auto_evolve false  # 스킬 자동 요약 비활성화
metaclaw config proxy.port 31000          # 프록시 포트 변경
```

---

## ⚙️ 설정

설정 파일은 `~/.metaclaw/config.yaml`에 저장되며, `metaclaw setup`으로 생성됩니다.

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
  dir: ~/.metaclaw/skills   # 스킬 라이브러리 디렉토리
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # 태스크별 스킬 상한 (기본값 10)
  auto_evolve: true         # 각 세션 후 스킬 자동 요약

rl:
  enabled: false            # true로 설정하면 RL 학습 활성화
  model: moonshotai/Kimi-K2.5
  tinker_api_key: ""
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

---

## 💪 스킬

스킬은 매 턴마다 에이전트의 시스템 프롬프트에 주입되는 짧은 Markdown 지침입니다. 스킬 디렉토리(기본값 `~/.metaclaw/skills/`)에 개별 `SKILL.md` 파일로 저장됩니다.

**스킬 자동 요약**은 각 대화 후에 실행됩니다. 설정한 LLM이 무슨 일이 있었는지 분석하여 새 스킬을 자동 생성합니다. 수동 큐레이션 불필요 — 라이브러리가 사용과 함께 성장합니다.

내장 스킬 뱅크를 미리 로드하려면 (코딩, 보안, 에이전트 작업 등 40개 이상의 스킬):

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 고급: RL 모드

RL 학습을 활성화하여 실시간 대화로부터 모델을 지속적으로 파인튜닝:

```bash
metaclaw config rl.enabled true
metaclaw config rl.tinker_api_key sk-...
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

RL 모드에서:
- 각 대화 턴이 토크나이즈되어 학습 샘플로 제출됨
- 심판 LLM(PRM)이 비동기로 응답 채점
- Tinker 클라우드가 LoRA 파인튜닝 실행. `batch_size` 샘플마다 가중치 핫스왑
- 전용 에볼버 LLM이 실패한 에피소드에서 새 스킬 추출

**프로그래매틱 롤아웃** (OpenClaw TUI 불필요): `openclaw_env_data_dir`를 JSONL 태스크 파일 디렉토리로 설정:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 고급: OPD 모드

온폴리시 증류(OPD)를 사용하면 학생 모델이 온폴리시로 학습하면서 더 큰 교사 모델을 증류할 수 있습니다. 학생 모델이 평소처럼 응답을 생성하고, 교사 모델이 동일한 응답에 대해 토큰별 로그 확률을 제공합니다. KL 페널티가 학생을 교사의 분포 방향으로 유도합니다.

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

교사 모델은 OpenAI 호환 `/v1/completions` 엔드포인트(예: vLLM, SGLang)에서 서비스되어야 합니다. OPD는 PRM 채점과 함께 사용할 수 있으며, 두 가지 모두 비동기로 실행됩니다.

프로그래매틱 예시는 `examples/run_conversation_opd.py`, 즉시 사용 가능한 실행 스크립트는 `scripts/run_openclaw_tinker_opd.sh`를 참조하세요.

---

## 🧠 고급: 메타러닝 스케줄러 (v0.3)

RL 모드에서 가중치 핫스왑 단계는 에이전트를 수 분간 일시 정지시킵니다. 스케줄러(madmax 모드에서 기본 활성화)는 RL 업데이트를 사용자 비활성 창으로 연기하여 활성 사용 중에 에이전트가 중단되지 않도록 합니다.

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# 선택 사항: Google Calendar 통합
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

세 가지 조건이 업데이트 창을 트리거합니다 (하나만 충족하면 충분): 설정된 수면 시간, 시스템 키보드 유휴, 활성 Google Calendar 이벤트. 사용자가 업데이트 중에 돌아오면, 부분 배치가 저장되고 다음 창에서 재개됩니다.

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

- [OpenClaw](https://openclaw.ai) — 핵심 에이전트 프레임워크.
- [SkillRL](https://github.com/aiming-lab/SkillRL) — 스킬 강화 RL 프레임워크.
- [Tinker](https://www.thinkingmachines.ai/tinker/) — 온라인 RL 학습에 사용.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — RL 설계의 영감.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — 스킬 뱅크의 기반 제공.

---

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.
