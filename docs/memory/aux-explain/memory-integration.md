# Memory 模块集成点

## 系统集成拓扑

```
MetaClawConfig (memory.* 配置项)
       │
       ▼
MetaClawLauncher
  ├── 构建 MemoryManager.from_config(cfg)
  └── 启动 MemoryUpgradeWorker (后台 asyncio Task)
       │
       ▼
AsyncRolloutWorker (透传 memory_manager)
       │
       ▼
MetaClawAPIServer ─── 核心集成点
  ├── _inject_memory()    → retrieve_for_prompt() + render_for_prompt()
  ├── _ingest_memory()    → ingest_session_turns()
  └── /v1/memory/* REST   → 9 个管理端点
```

## 各组件集成详情

### 1. 配置层 (`config.py`)

20+ 个 `memory_*` 配置项, 涵盖:
- 开关: `memory_enabled`, `memory_auto_upgrade_enabled`
- 存储: `memory_dir`, `memory_store_path`
- 检索: `memory_retrieval_mode`, `memory_max_injected_units/tokens`
- 向量: `memory_use_embeddings`, `memory_embedding_mode/model`
- 策略: `memory_policy_path`, `memory_telemetry_path`
- 升级: `memory_auto_upgrade_interval_seconds`, `memory_auto_upgrade_require_review`

### 2. Launcher (`launcher.py`)

- `memory_enabled=True` 时构建 `MemoryManager`
- `memory_auto_upgrade_enabled=True` 时启动 `MemoryUpgradeWorker` 后台任务

### 3. API Server (`api_server.py`) — 主要集成点

**读路径 (注入)**:
- 每次 `/v1/chat/completions` 请求前调用 `_inject_memory()`
- 通过 `X-Memory-Scope` header 或 body 中 `memory_scope` 指定作用域
- 检索结果渲染后 prepend 到 system message

**写路径 (提取)**:
- 会话结束 (`session_done=True`) 时调用 `_ingest_memory_for_session()`
- 独立的 `_session_memory_turns` 缓冲区, 不受 skill evolution 影响

**REST API** (9 个端点):

| 端点 | 方法 | 功能 |
|------|------|------|
| `/v1/memory/stats` | GET | 存储统计 |
| `/v1/memory/search` | GET | 关键词搜索 |
| `/v1/memory/health` | GET | 健康状态 |
| `/v1/memory/summary` | GET | 池摘要 |
| `/v1/memory/{id}` | GET | 单条记忆 |
| `/v1/memory/action-plan` | POST | 操作计划 |
| `/v1/memory/maintenance` | POST | 触发维护 |
| `/v1/memory/feedback-analysis` | GET | 反馈分析 |
| `/v1/memory/operator-report` | GET | 运维报告 |

### 4. CLI (`cli.py`) — 18 个子命令

`metaclaw memory` 命令组: `status`, `stats`, `search`, `export`, `import`, `summary`, `diagnose`, `gc`, `ttl`, `expire`, `share`, `merge`, `history`, `analytics`, `tag`, `scopes`, `snapshot`, `rollback` 等。

### 5. Trainer (`trainer.py`)

- `setup()` 中构建 `MemoryManager`, 传递给 rollout worker
- 不直接操作记忆

### 6. Skill Manager / Skill Evolver

- 与 memory 完全独立, 无交叉依赖

### 7. OpenClaw 插件 (`openclaw-metaclaw-memory/`)

TypeScript npm 包 `@metaclaw/memory`, 通过 Python sidecar 进程桥接:
- `auto-recall` hook: 发送前注入记忆
- `auto-capture` hook: 会话后提取记忆
- slash commands: `memory-status`, `memory-search`, `memory-store`, `memory-forget`
- 内嵌 Python memory 模块副本, 实现独立分发
