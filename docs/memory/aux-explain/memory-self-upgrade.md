# Memory 自升级机制

## 概述

Memory 模块的自升级系统通过离线回放评估自动优化检索策略参数, 实现"改策略不改代码"的安全自适应。

## 升级流水线

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  候选生成     │ →  │  离线回放评估  │ →  │  晋升/审核    │
│ candidate.py │    │  replay.py   │    │ promotion.py │
└──────────────┘    └──────────────┘    └──────────────┘
       ↑                                       │
       │            ┌──────────────┐           ↓
       └────────────│ self_upgrade │←──────────┘
                    └──────────────┘
                           ↑
                    ┌──────────────┐
                    │upgrade_worker│  (asyncio 定时循环)
                    └──────────────┘
```

## 1. 候选策略生成 (`candidate.py`)

**两阶段生成**:
- Phase 1 — 网格搜索: `retrieval_mode` × `max_injected_units` × `max_injected_tokens` 的邻域组合
- Phase 2 — 权重扰动: 对 keyword/metadata/importance/recency 权重做 ±0.1~0.2 偏移

所有候选通过 `(mode, units, tokens, kw, meta, imp, rec)` 元组去重。

## 2. 离线回放评估 (`replay.py`)

**流程**: 对历史会话 JSONL 重放, 分别用基线和候选策略检索, 对比 8 维指标:

| 指标 | 权重 | 含义 |
|------|------|------|
| query_overlap | 20% | 检索结果与查询的词项重叠 |
| continuation_overlap | 15% | 与后续对话的相关度 |
| response_overlap | 15% | 与实际回复的匹配度 |
| focus_score | 15% | 检索精度 (precision) |
| grounding | 10% | 实体/主题元数据对齐 |
| coverage | 10% | 回复关键词覆盖率 |
| value_density | 10% | 信息密度 |
| specificity | 5% | 唯一性和长尾占比 |

综合分数还会被 zero-retrieval 率惩罚。

## 3. 晋升判定 (`promotion.py`)

`should_promote()` 检查:
- 所有指标 delta 达到 `MemoryPromotionCriteria` 阈值
- `candidate_beats_baseline` 标志为 True
- zero-retrieval 增量不超过上限 (默认 2)
- 最低样本数 (默认 10)

## 4. 编排器 (`self_upgrade.py`)

`MemorySelfUpgradeOrchestrator` 完整流程:
1. `generate_candidate_files()` — 写入候选策略 JSON
2. `evaluate_candidate_directory()` — 逐个回放评估, 选最优
3. 若 `require_review=True` → 加入人工审核队列
4. 若 `require_review=False` → 直接 `_promote_candidate()` 复制到 live 策略
5. `cleanup_artifacts()` — 清理旧候选和报告文件

**人工审核**: `approve_review_candidate()` / `reject_review_candidate()`, 审核队列有 72h 过期告警。

## 5. 后台 Worker (`upgrade_worker.py`)

- 默认每 900s 检查一次
- 检查回放数据文件是否有更新 (mtime)
- 先执行 `run_maintenance()` (TTL 过期 + 合并)
- 再执行 `run_auto_upgrade_cycle()`
- 持久化 worker 状态、告警和健康快照

## 6. 遥测驱动优化 (`policy_optimizer.py`)

在自升级循环之外, 还有基于遥测的增量调优:
- 记忆池 < 5 条: 不操作 (安全底线)
- ≥ 25 条: 切换到 hybrid 模式
- ≥ 80 条: 提高注入预算
- 检索持续饱和/空返回: 调整 `max_injected_units`
- 类型分布偏斜: 调整对应权重
