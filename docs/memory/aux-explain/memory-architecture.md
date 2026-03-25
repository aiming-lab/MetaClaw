# Memory 模块架构总览

## 定位

MetaClaw 的长期记忆子系统，为 LLM 对话提供跨会话的事实/偏好/项目状态记忆能力。基于 SQLite + FTS5 构建，支持自适应检索策略和受控自升级。

## 分层架构

```
┌─────────────────────────────────────────────────────┐
│  upgrade_worker.py   — 异步后台自升级循环             │
├─────────────────────────────────────────────────────┤
│  self_upgrade.py     — 升级编排 (候选生成→评估→晋升)   │
├──────────┬──────────┬───────────────────────────────┤
│ candidate│ promotion│ replay.py — 离线回放评估        │
├──────────┴──────────┴───────────────────────────────┤
│  manager.py          — 门面层 (2400+ 行)             │
├──────┬──────────┬────────────┬───────────────────────┤
│ retriever │ consolidator │ policy_optimizer          │
├──────┴──────────┴────────────┴───────────────────────┤
│  store.py  — SQLite 持久化 (1787 行, schema v6)       │
├──────────┬──────────┬────────────────────────────────┤
│ models.py│embeddings│ policy.py / policy_store.py    │
├──────────┴──────────┴────────────────────────────────┤
│  scope.py · metrics.py · telemetry.py — 基础工具      │
└─────────────────────────────────────────────────────┘
```

## 文件清单 (18 个)

| 文件 | 职责 | 行数级别 |
|------|------|----------|
| `models.py` | 核心数据结构: `MemoryUnit`, `MemoryQuery`, `MemoryType`, `MemoryStatus` | 小 |
| `store.py` | SQLite + FTS5 持久层, CRUD/搜索/图/ACL/快照/GC | 大 (~1800) |
| `manager.py` | 门面 API, 编排所有子系统, LRU 缓存, 事件总线 | 大 (~2400) |
| `retriever.py` | 三模式检索: keyword / embedding / hybrid / auto | 中 |
| `consolidator.py` | 去重/合并/实体交叉增强/重要度衰减 | 中 |
| `embeddings.py` | `HashingEmbedder` (无依赖) + `SentenceTransformerEmbedder` | 小 |
| `policy.py` | 运行时检索策略 (`MemoryPolicy`), 内置 profile | 小 |
| `policy_store.py` | JSON 持久化 + 修订历史 + 回滚 | 小 |
| `policy_optimizer.py` | 基于遥测的自动策略调优 | 中 |
| `candidate.py` | 网格搜索 + 权重扰动生成候选策略 | 小 |
| `promotion.py` | 晋升门控: 8 维指标阈值判定 | 小 |
| `replay.py` | 离线会话回放评估 + 对比报告 | 中 |
| `self_upgrade.py` | 升级编排: 生成→评估→晋升/人工审核 | 中 |
| `upgrade_worker.py` | asyncio 后台 worker, 定期触发升级循环 | 小 |
| `scope.py` | 作用域推导: user/workspace/session 组合 | 小 |
| `metrics.py` | 存储统计汇总 (密度/类型分布/主导类型) | 小 |
| `telemetry.py` | JSONL 追加式遥测日志 | 小 |
| `__init__.py` | 公共 API 导出 (15 个符号) | 小 |

## 核心数据模型

### MemoryUnit (21 字段)

- **身份**: `memory_id`, `scope_id`, `memory_type`
- **内容**: `content`, `summary`
- **来源**: `source_session_id`, `source_turn_start`, `source_turn_end`
- **元数据**: `entities`, `topics`, `tags`
- **评分**: `importance`, `confidence`, `reinforcement_score`, `access_count`
- **生命周期**: `status`, `supersedes`, `superseded_by`, `expires_at`
- **向量**: `embedding`
- **时间戳**: `created_at`, `updated_at`, `last_accessed_at`

### MemoryType (6 种)

| 类型 | 用途 |
|------|------|
| `EPISODIC` | 会话事件片段 |
| `SEMANTIC` | 事实性知识 |
| `PREFERENCE` | 用户偏好 |
| `PROJECT_STATE` | 项目状态信息 |
| `WORKING_SUMMARY` | 滚动摘要 |
| `PROCEDURAL_OBSERVATION` | 过程性观察 |

## 关键设计决策

1. **SQLite 单文件存储** — 零外部依赖, FTS5 加速关键词搜索
2. **三模式检索** — keyword (FTS5/IDF), embedding (cosine), hybrid (加权融合)
3. **策略与代码分离** — 自适应调整的是策略参数, 不是代码
4. **有界自升级** — 候选策略必须在离线回放中击败基线才能晋升
5. **人工审核门控** — 默认开启 `require_review`, 支持 approve/reject 工作流
6. **作用域隔离** — 多租户 ACL, 跨作用域共享需显式授权
