<div align="center">

<img src="new_logo2.png" alt="MetaClaw" width="600">

<br/>

# エージェントと話すだけ,学習し、*進化*する。

<p>脳の学習メカニズムに着想を得て。あなたの 🦞 を日常の会話からメタ学習・進化させます。GPU不要。Kimi、Qwen、Claude、MiniMax など対応。</p>

<img src="metaclaw_mainfig_v2.png" alt="MetaClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_完全非同期-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_GPU不要-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_スキル進化-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_ワンクリック展開-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇷🇺 Русский](./README_RU.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇦🇪 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[概要](#-概要) • [クイックスタート](#-クイックスタート) • [設定](#️-設定) • [スキルモード](#-スキルモード) • [RL モード](#-rl-モード) • [MadMax モード](#-madmax-モードデフォルト) • [引用](#-引用)

</div>

---

<div align="center">

### コマンド2つ。それだけ。
</div>

```bash
metaclaw setup              # 初回設定ウィザード
metaclaw start              # デフォルト: madmax モード — スキル + スケジュール RL トレーニング
metaclaw start --daemon     # バックグラウンドで実行、ログ -> ~/.metaclaw/metaclaw.log
metaclaw start --daemon --log-file /tmp/metaclaw.log  # カスタムログパス
metaclaw start --mode rl    # スケジューラなし RL（バッチが満たされ次第即時トレーニング）
metaclaw start --mode skills_only  # スキルのみ、RL なし（Tinker 不要）
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 ニュース

- **[2026/03/16]** **v0.3.2** マルチ Claw サポート：IronClaw・PicoClaw・ZeroClaw・CoPaw・NanoClaw・NemoClaw が OpenClaw に加えて利用可能に。NanoClaw は新規 `/v1/messages` Anthropic 互換エンドポイント経由で、NemoClaw は OpenShell 推論ルーティング経由で接続。OpenRouter を LLM プラットフォームとして追加。
- **[2026/03/13]** **v0.3.1** MinT バックエンドサポート：RL トレーニングが Tinker と MinT の両方で動作。`rl.backend`（auto/tinker/mint）で設定可能。
- **[2026/03/13]** **v0.3** 継続的メタ学習サポート：RL 重み更新を睡眠時間・アイドル時間・Google Calendar 会議中にのみ実行。サポート/クエリセット分離を追加し、古い報酬信号によるモデル更新の汚染を防止。
- **[2026/03/11]** **v0.2** `metaclaw` CLI によるワンクリック展開。スキルはデフォルト有効、RL はオプトイン方式に。
- **[2026/03/09]** **MetaClaw** をリリース。エージェントと話すだけで自動進化。GPU デプロイ**不要**。**API** に接続するだけ。

---

## 🎥 デモ

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 概要

**MetaClaw は、実環境でメタ学習し進化し続けるエージェントです。**
いつも通りエージェントと話すだけで、MetaClaw はすべてのライブ会話を学習シグナルに変換し、オフライン学習だけに頼るのではなく、実際のデプロイを通じてエージェントを継続的に改善します。

内部では、モデルを OpenAI 互換プロキシの背後に配置し（NanoClaw などの Anthropic ネイティブエージェントには `/v1/messages` 互換エンドポイントも提供）、OpenClaw・NanoClaw・NemoClaw などの対応エージェント経由でインタラクションをインターセプト。各ターンで関連スキルを注入し、蓄積された経験からメタ学習します。セッション終了後にスキルが自動集約され、RL 有効時にはメタ学習スケジューラがウェイト更新をアイドル時間帯に延期し、アクティブ利用中のエージェント中断を防ぎます。

GPU クラスタは不要です。MetaClaw は任意の OpenAI 互換 LLM API で動作し、クラウドベースの LoRA トレーニングには Tinker 互換バックエンドを利用します。[Tinker](https://www.thinkingmachines.ai/tinker/) が標準の参照パスで、必要に応じて MinT を別途互換パッケージ経由で有効化できます。

## 🤖 主な機能

### **ワンクリック展開**
`metaclaw setup` で一度設定したら、`metaclaw start` でプロキシ起動・スキル注入・OpenClaw 接続まで自動化。手動シェルスクリプト不要。

### **3つの動作モード**

| モード | デフォルト | 内容 |
|--------|-----------|------|
| `skills_only` | | プロキシで LLM API を中継。スキル注入、セッション後に自動集約。GPU/Tinker 不要。 |
| `rl` | | スキル + RL トレーニング（GRPO）。バッチが満たされ次第即時トレーニング。OPD（教師蒸留）もオプションで利用可能。 |
| `madmax` | ✅ | スキル + RL + スマートスケジューラ。RL 重み更新は睡眠/アイドル/会議ウィンドウでのみ実行。 |

### **設計レベルでの非同期処理**
サービング、報酬モデリング、トレーニングは完全に分離。エージェントが応答し続ける間、スコアリングと最適化が並列で実行されます。

---

## 🚀 クイックスタート

### 1. インストール

```bash
pip install -e .                        # skills_only モード（軽量）
pip install -e ".[rl]"                  # + RL トレーニングサポート（torch、transformers、tinker）
pip install -e ".[evolve]"              # + OpenAI 互換 LLM によるスキル進化
pip install -e ".[scheduler]"           # + Google Calendar スケジューラ統合
pip install -e ".[rl,evolve,scheduler]" # 推奨：完全 RL + スケジューラセットアップ
```

`rl.backend=mint` を使う場合は、同じ環境に MinT 互換パッケージを別途インストールしてください。たとえば [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit) です。MetaClaw はこの依存をデフォルトパッケージに含めず、RL 利用者が Tinker と MinT を明示的に選べるようにしています。

### 2. 設定

```bash
metaclaw setup
```

対話型ウィザードで LLM プロバイダー（Kimi、Qwen、MiniMax、またはカスタム）、API キー、RL の有効化を設定します。

MetaClaw の RL パスは `tinker` と `mint` を明示的に切り替えられます。推奨デフォルトは `auto` で、MinT パッケージが入っていれば Mint 形式の credentials や base URL から MinT を推定できます。

**Tinker**（デフォルト）:

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

互換性のため、旧来の `rl.tinker_api_key` と `rl.tinker_base_url` も引き続き利用できます。

### 3. 起動

```bash
metaclaw start
```

以上です。MetaClaw がプロキシを起動し、OpenClaw を自動設定してゲートウェイを再起動します。OpenClaw を開いてチャットを開始すると、各ターンでスキルが注入され、終了後に自動的に新しいスキルとして集約されます。

---

## ⚙️ 設定

設定ファイルは `~/.metaclaw/config.yaml` に保存され、`metaclaw setup` によって作成されます。

**CLI コマンド：**

```
metaclaw setup                  # 初回インタラクティブ設定ウィザード
metaclaw start                  # MetaClaw を起動（デフォルト: madmax モード）
metaclaw start --daemon         # MetaClaw をバックグラウンドで起動
metaclaw start --daemon --log-file /tmp/metaclaw.log  # カスタムログパス
metaclaw start --mode rl        # このセッションで RL モードを強制（スケジューラなし）
metaclaw start --mode skills_only  # このセッションでスキルのみモードを強制
metaclaw stop                   # 実行中の MetaClaw インスタンスを停止
metaclaw status                 # プロキシの状態、動作モード、スケジューラ状態を確認
metaclaw config show            # 現在の設定を表示
metaclaw config KEY VALUE       # 設定値を変更
```

`--daemon` で MetaClaw を起動すると、ローカルプロキシが正常に動作するまでコマンドは待機します。`metaclaw status` で準備状況を確認し、`metaclaw stop` でバックグラウンドプロセスを停止できます。

<details>
<summary><b>完全な設定リファレンス（クリックで展開）</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # ローカル MetaClaw プロキシ用の任意 bearer token

skills:
  enabled: true
  dir: ~/.metaclaw/skills   # スキルライブラリのディレクトリ
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # タスク固有スキルの上限（デフォルト 10）
  auto_evolve: true         # 各セッション後にスキルを自動集約

rl:
  enabled: false            # true にすると RL トレーニングを有効化
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # 任意の backend endpoint。例: MinT 用 https://mint.macaron.xin/
  tinker_api_key: ""        # api_key の互換エイリアス
  tinker_base_url: ""       # base_url の互換エイリアス
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # トレーニングを再開するチェックポイントパス（オプション）
  evolver_api_base: ""      # 空の場合は llm.api_base を再利用
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # true にすると OPD（教師蒸留）を有効化
  teacher_url: ""           # 教師モデルのベース URL（OpenAI 互換 /v1/completions）
  teacher_model: ""         # 教師モデル名（例：Qwen/Qwen3-32B）
  teacher_api_key: ""       # 教師モデルの API キー
  kl_penalty_coef: 1.0      # OPD の KL ペナルティ係数

max_context_tokens: 20000   # 切り捨て前のプロンプトトークン上限

scheduler:                  # v0.3：メタ学習スケジューラ（madmax モードで自動有効化）
  enabled: false            # madmax モードでは自動有効化。rl モードでは手動設定
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

## 💪 スキルモード

**`metaclaw start --mode skills_only`**

最も軽量なモードです。GPU も RL バックエンドも不要。MetaClaw が LLM をプロキシの背後に配置し、各ターンで関連スキルを注入、会話終了後に新しいスキルを自動集約します。

スキルは `~/.metaclaw/skills/` に個別の `SKILL.md` ファイルとして保存される短い Markdown 指示です。ライブラリは使用とともに自動的に成長します。

内蔵スキルバンクをプリロードするには（コーディング、セキュリティ、エージェントタスクなど 40 以上のスキル）：

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 RL モード

**`metaclaw start --mode rl`**

スキルモードのすべてに加え、ライブ会話からの継続的な RL ファインチューニングを実行します。各会話ターンがトークン化されてトレーニングサンプルとして提出されます。審判 LLM（PRM）が非同期で回答にスコアを付与し、Tinker 互換バックエンド（Tinker クラウドまたは MinT）が LoRA ファインチューニングとウェイトのホットスワップを実行します。

**Tinker**（デフォルト）:

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

専用エボルバー LLM が失敗したエピソードから新しいスキルを抽出し、スキルライブラリにフィードバックします。

**プログラム的なロールアウト**（OpenClaw TUI 不要）：`openclaw_env_data_dir` を JSONL タスクファイルのディレクトリに設定：

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### オンポリシー蒸留（OPD）

OPD は RL モードのオプション機能です。より大きな教師モデルを学生にオンポリシーで蒸留します。学生モデルが通常通り回答を生成し、教師モデルが同じ回答に対してトークンごとの対数確率を提供。KL ペナルティが学生を教師の分布へ誘導します。

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
```

教師モデルは OpenAI 互換の `/v1/completions` エンドポイント（例：vLLM、SGLang）で提供する必要があります。OPD は PRM スコアリングと組み合わせることができ、両方が非同期で実行されます。`examples/run_conversation_opd.py` と `scripts/run_openclaw_tinker_opd.sh` を参照してください。

---

## 🧠 MadMax モード（デフォルト）

**`metaclaw start`**

RL モードのすべてに加え、メタ学習スケジューラがウェイト更新をユーザーの非アクティブウィンドウに延期し、アクティブな使用中にエージェントが中断されないようにします。これがデフォルトモードです。

RL ウェイトのホットスワップステップでエージェントが数分間一時停止します。RL モードのようにバッチが満たされ次第即時トレーニングするのではなく、MadMax は適切なウィンドウを待ちます。

3つの条件が更新ウィンドウをトリガーします（いずれか1つで十分）：

- **睡眠時間**：設定可能な開始/終了時刻（例：23:00 から 07:00）
- **キーボードアイドル**：N 分間のアイドル後にトリガー
- **Google Calendar イベント**：会議を検出して更新を実行

```bash
metaclaw config scheduler.sleep_start "23:00"
metaclaw config scheduler.sleep_end   "07:00"
metaclaw config scheduler.idle_threshold_minutes 30

# オプション：Google Calendar 統合
pip install -e ".[scheduler]"
metaclaw config scheduler.calendar.enabled true
metaclaw config scheduler.calendar.credentials_path ~/.metaclaw/client_secrets.json
```

ユーザーが更新中に戻った場合、部分バッチは保存され、次のウィンドウで再開されます。

各 `ConversationSample` には `skill_generation` バージョンがタグ付けされます。スキル進化がジェネレーションをインクリメントすると、RL バッファがフラッシュされ、進化後のサンプルのみが勾配更新に使用されます（MAML サポート/クエリセット分離）。

---

## 📚 引用

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

## 🙏 謝辞

MetaClaw は以下のオープンソースプロジェクトの上に構築されています：

- [OpenClaw](https://openclaw.ai), コアエージェントフレームワーク。
- [SkillRL](https://github.com/aiming-lab/SkillRL), スキル強化 RL フレームワーク。
- [Tinker](https://www.thinkingmachines.ai/tinker/), オンライン RL トレーニングに使用。
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit), オンライン RL トレーニングの代替バックエンド。
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL), RL 設計のインスピレーション。
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills), スキルバンクの基盤を提供。
- [NanoClaw](https://github.com/qwibitai/nanoclaw), qwibitai 製のパーソナル Claude エージェント。`/v1/messages` 互換エンドポイント経由で接続。
- [NemoClaw](https://github.com/NVIDIA/NemoClaw), NVIDIA の OpenShell 推論エージェントプラグイン。

---

## 📄 ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) のもとで公開されています。
