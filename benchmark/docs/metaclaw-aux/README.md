# MetaClaw 源码分析文档索引

## 文件列表

| 文件 | 内容 |
|------|------|
| [metaclaw-tinker-training.md](./metaclaw-tinker-training.md) | MetaClaw 使用 Tinker 远程训练 LoRA 的完整机制，包括训练方式、数据来源、上下文窗口、所有可调参数 |

## 分析摘要

MetaClaw 是一个基于 Tinker 云端 LoRA 训练的持续学习系统，核心特性：

- **无需本地 GPU**：训练完全卸载到 Tinker 云端
- **训练算法**：GRPO-style RL（默认）或在线策略蒸馏（OPD）
- **数据来源**：OpenClaw 对话流量（被动代理）或 JSONL 任务文件（程序化 rollout）
- **上下文窗口**：默认 20000 tokens（`max_context_tokens`），可调；受 Tinker 端 `max_seq_len` 约束
- **奖励信号**：LLM-as-judge（OpenAI-compatible API），多数投票
- **技能演化**：失败样本自动触发 SkillEvolver 生成新技能，MAML 风格 support/query 集分离

源码路径：`/home/xkaiwen/workspace/metaclaw-test/metaclaw/`
