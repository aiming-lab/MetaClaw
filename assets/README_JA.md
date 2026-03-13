<div align="center">

<img src="new_logo.png" alt="MetaClaw" width="600">

<br/>

# エージェントと話すだけ — 学習し、*進化*する。

<p>
  <a href="https://github.com/aiming-lab/MetaClaw"><img src="https://img.shields.io/badge/github-MetaClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_完全非同期-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_GPU不要-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_スキル進化-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_ワンクリック展開-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md)

<br/>

[概要](#-概要) • [クイックスタート](#-クイックスタート) • [CLIリファレンス](#️-cliリファレンス) • [設定](#️-設定) • [スキル](#-スキル) • [RLモード](#-上級者向けrlモード) • [OPDモード](#-上級者向けopdモード) • [引用](#-引用)

</div>

---

<div align="center">

### コマンド2つ。それだけ。
</div>

```bash
metaclaw setup              # 初回設定ウィザード
metaclaw start              # スキル有効化、OpenClaw 接続 — チャット開始
metaclaw start --mode rl    # オプション：+ Tinker 互換バックエンドによるリアルタイム RL トレーニング
```

<div align="center">
<img src="metaclaw.gif" alt="MetaClaw demo" width="700">
</div>

---

## 🔥 ニュース

- **[2026/03/10]** **v0.2** — `metaclaw` CLI によるワンクリック展開。スキルはデフォルト有効、RL はオプトイン方式に。
- **[2026/03/09]** **MetaClaw** をリリース — エージェントと話すだけで自動進化。GPU デプロイ**不要**。**API** に接続するだけ。

---

## 🎥 デモ

https://github.com/user-attachments/assets/1c2919fc-5612-40f7-bb97-c74ab50619d5

---

## 📖 概要

**MetaClaw はライブ会話を継続的なトレーニングデータに自動変換します。**
いつも通りエージェントと話すだけで、MetaClaw が裏側で学習ループを処理します。

モデルを OpenAI 互換プロキシの背後に置き、OpenClaw 経由でインタラクションをインターセプト。各ターンで関連スキルを注入し、セッション終了後に新しいスキルを自動集約します。オプションで Tinker や MinT のような Tinker 互換クラウド RL バックエンドを有効化することで、サービスを中断せずウェイトをホットスワップできます。

GPU クラスタは不要です。MetaClaw は任意の OpenAI 互換 LLM API で動作し、[Tinker](https://www.thinkingmachines.ai/tinker/) や MinT のような Tinker 互換バックエンドに RL トレーニングを接続して、クラウドベースの LoRA ファインチューニングを実行できます。

## 🤖 主な機能

### **ワンクリック展開**
`metaclaw setup` で一度設定したら、`metaclaw start` でプロキシ起動・スキル注入・OpenClaw 接続まで自動化。手動シェルスクリプト不要。

### **2つの動作モード**

| モード | デフォルト | 内容 |
|--------|-----------|------|
| `skills_only` | ✅ | プロキシ → LLM API。スキル注入、セッション後に自動集約。GPU/Tinker 不要。 |
| `rl` | オフ | プロキシ → Tinker 互換クラウド RL。PRM スコアリングとスキル進化を含む完全トレーニングループ。 |

### **スキル注入**
各ターンで MetaClaw が最も関連性の高いスキル指示を取得し、エージェントのシステムプロンプトに注入。再トレーニング不要で即座に動作改善。

### **スキル自動集約**
会話が終わるたびに、使用中の同じ LLM がセッションを分析して新しいスキルを自動生成。手動キュレーション不要 — ライブラリは使用とともに成長します。

### **GPU クラスタ不要**
`skills_only` モードはネットワーク接続のみ必要。RL トレーニングは Tinker 互換クラウドバックエンドにオフロードされます。

### **2つの学習モード**
MetaClaw は以下の両方をサポートします：
- **RL（GRPO）**：暗黙のフィードバック信号から学習
- **オンポリシー蒸留（OPD）**：大きな教師モデルを学生にオンポリシーで蒸留

OPD モードでは、学生モデルが通常通り回答を生成し、教師モデルが同じ回答に対してトークンごとの対数確率を提供。教師の logprob が損失関数（例：`cispo`）に渡され、学生が教師の分布を学習します。教師は OpenAI 互換の `/v1/completions` エンドポイント（例：vLLM、SGLang）で提供する必要があります。

### **設計レベルでの非同期処理**
サービング、報酬モデリング、トレーニングは完全に分離。エージェントが応答し続ける間、スコアリングと最適化が並列で実行されます。

---

## 🚀 クイックスタート

### 1. インストール

```bash
pip install -e .            # skills_only モード（軽量）
pip install -e ".[rl]"      # + RL トレーニングサポート（torch、transformers、tinker）
pip install -e ".[evolve]"  # + OpenAI 互換 LLM によるスキル進化
```

`rl.backend=mint` を使う場合は、同じ環境に MinT 互換パッケージを別途インストールしてください。たとえば [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit) です。公式の MinT ドキュメントは [`mint-doc-alpha.macaron.im`](https://mint-doc-alpha.macaron.im/) にあります。MetaClaw はこの依存を標準パッケージには含めず、Tinker と MinT を明示的に選べるようにしています。

### 2. 設定

```bash
metaclaw setup
```

対話型ウィザードで LLM プロバイダー（Kimi、Qwen、またはカスタム）、API キー、RL の有効化を設定します。

MetaClaw の RL パスは `tinker` と `mint` を明示的に切り替えられます。推奨デフォルトは `auto` で、MinT 互換パッケージが入っていれば Mint 形式の credentials や base URL から引き続き MinT を自動判定します。つまり、同じ学習フローを設定だけで Tinker クラウドにも MinT デプロイにも向け替えられます。

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

以上です。MetaClaw がプロキシを起動し、OpenClaw を自動設定してゲートウェイを再起動します。OpenClaw を開いてチャットを開始 — 各ターンでスキルが注入され、終了後に自動的に新しいスキルとして集約されます。

---

## 🛠️ CLI リファレンス

```
metaclaw setup              # 初回インタラクティブ設定ウィザード
metaclaw start              # MetaClaw を起動（プロキシ + オプション RL）
metaclaw start --mode rl    # このセッションで RL モードを強制
metaclaw stop               # 実行中の MetaClaw インスタンスを停止
metaclaw status             # プロキシの状態と動作モードを確認
metaclaw config show        # 現在の設定を表示
metaclaw config KEY VALUE   # 設定値を変更
```

**よく使う設定キー：**

```bash
metaclaw config rl.enabled true           # RL トレーニングを有効化
metaclaw config rl.backend auto           # auto | tinker | mint
metaclaw config rl.api_key sk-...         # RL バックエンドのキーを設定
metaclaw config rl.base_url https://mint.macaron.xin/  # MinT などの任意 backend endpoint
metaclaw config skills.auto_evolve false  # スキル自動集約を無効化
metaclaw config proxy.port 31000          # プロキシポートを変更
```

---

## ⚙️ 設定

設定ファイルは `~/.metaclaw/config.yaml` に保存され、`metaclaw setup` によって作成されます。

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
```

---

## 💪 スキル

スキルは各ターンでエージェントのシステムプロンプトに注入される短い Markdown 形式の指示です。スキルディレクトリ（デフォルト `~/.metaclaw/skills/`）に個別の `SKILL.md` ファイルとして保存されます。

**スキル自動集約**は各会話後に実行されます。設定した LLM が何が起きたかを分析し、新しいスキルを自動生成。手動キュレーション不要 — ライブラリは使用とともに成長します。

内蔵スキルバンクをプリロードするには（コーディング、セキュリティ、エージェントタスクなど 40 以上のスキル）：

```bash
cp -r memory_data/skills/* ~/.metaclaw/skills/
```

---

## 🔬 上級者向け：RL モード

RL トレーニングを有効にして、Tinker または MinT 経由でライブ会話からモデルを継続的にファインチューニング：

```bash
metaclaw config rl.enabled true
metaclaw config rl.backend mint
metaclaw config rl.api_key sk-...
metaclaw config rl.base_url https://mint.macaron.xin/
metaclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
metaclaw config rl.prm_url https://api.openai.com/v1
metaclaw config rl.prm_api_key sk-...
metaclaw start
```

RL モードでは：
- 各会話ターンがトークン化されてトレーニングサンプルとして提出
- 審判 LLM（PRM）が非同期で回答にスコアを付与
- Tinker クラウドや MinT のような Tinker 互換バックエンドが LoRA ファインチューニングを実行。`batch_size` サンプルごとにウェイトをホットスワップ
- 専用エボルバー LLM が失敗したエピソードから新しいスキルを抽出

Tinker クラウドを使いたい場合は、`rl.backend` を `tinker` にするか、`auto` のままで MinT endpoint を設定しないでください。

**プログラム的なロールアウト**（OpenClaw TUI 不要）：`openclaw_env_data_dir` を JSONL タスクファイルのディレクトリに設定：

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

---

## 🔬 上級者向け：OPD モード

オンポリシー蒸留（OPD）を使用すると、学生モデルがオンポリシーでトレーニングしながら、より大きな教師モデルを蒸留できます。学生モデルが通常通り回答を生成し、教師モデルが同じ回答に対してトークンごとの対数確率を提供。KL ペナルティが学生を教師の分布へ誘導します。

```bash
metaclaw config opd.enabled true
metaclaw config opd.teacher_url http://localhost:8082/v1
metaclaw config opd.teacher_model Qwen/Qwen3-32B
metaclaw config opd.kl_penalty_coef 1.0
metaclaw start --mode rl
```

教師モデルは OpenAI 互換の `/v1/completions` エンドポイント（例：vLLM、SGLang）で提供する必要があります。OPD は PRM スコアリングと組み合わせることができ、両方が非同期で実行されます。

プログラム例は `examples/run_conversation_opd.py`、既製の起動スクリプトは `scripts/run_openclaw_tinker_opd.sh` を参照してください。

---

## 📚 引用

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

## 🙏 謝辞

MetaClaw は以下のオープンソースプロジェクトの上に構築されています：

- [OpenClaw](https://openclaw.ai) — コアエージェントフレームワーク。
- [SkillRL](https://github.com/aiming-lab/SkillRL) — スキル強化 RL フレームワーク。
- [Tinker](https://www.thinkingmachines.ai/tinker/) — オンライン RL トレーニングに使用。
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL) — RL 設計のインスピレーション。
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — スキルバンクの基盤を提供。

---

## 📄 ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) のもとで公開されています。
