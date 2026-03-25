# Memory 在 API 代理内部的工作流程

## MetaClaw 的代理本质

MetaClaw 以 OpenAI 兼容的 API 代理运行。外部客户端 (如 OpenClaw/Claude Code) 只需将 `base_url` 指向 MetaClaw，像调用普通 LLM 一样发请求。MetaClaw 在内部拦截请求，**编辑 prompt 后再转发给真正的 LLM**，对客户端完全透明。

Memory 模块正是在这个"拦截→编辑→转发"的过程中工作的。

## 整体流程图

```
客户端 (OpenClaw / Claude Code / 任意 OpenAI 兼容客户端)
    │
    │  POST /v1/chat/completions
    │  (标准 OpenAI 格式, 附加 session_id / memory_scope)
    ▼
┌─────────────────────────────────────────────────┐
│  MetaClaw API Server  (FastAPI, async)           │
│                                                  │
│  ① 解析请求 → 确定 session_id, memory_scope      │
│                                                  │
│  ② 【读路径】_inject_memory()                     │
│     ├─ 从 user messages 提取 task description     │
│     ├─ 用 base_scope 从 SQLite 检索相关记忆        │
│     ├─ render_for_prompt() 渲染为文本              │
│     └─ prepend 到 system message                  │
│                                                  │
│  ③ _inject_skills() (注入技能, 与 memory 独立)     │
│                                                  │
│  ④ 转发修改后的 messages → 真正的 LLM              │
│                                                  │
│  ⑤ 接收 LLM 响应, 流式返回给客户端                 │
│                                                  │
│  ⑥ 【写路径】缓冲 turn (prompt + response)         │
│     └─ 写入 _session_memory_turns[session_id]     │
│                                                  │
│  ⑦ 会话结束 (session_done=True) 时:               │
│     └─ _ingest_memory_for_session()               │
│        ├─ 从 turns 提取 MemoryUnit                │
│        ├─ 去重 + 冲突检测                          │
│        ├─ 写入 SQLite                             │
│        └─ 触发合并 + 策略刷新                      │
└─────────────────────────────────────────────────┘
```

## 详细步骤

### Step 1: 请求解析与作用域确定

客户端发送标准 `/v1/chat/completions` 请求时，可以通过以下方式指定记忆作用域：

```
# HTTP Header
X-Memory-Scope: user:alice|workspace:proj-x

# 或 request body 字段
{ "memory_scope": "user:alice|workspace:proj-x", ... }
```

作用域确定优先级：
1. 同一 session 内缓存的 scope（保持一致性）
2. 显式指定的 `memory_scope` / `user_id` + `workspace_id`
3. MemoryManager 的默认 `scope_id`

**关键设计**: 检索和写入都使用 `base_scope`（剥离 `|session:xxx` 后缀），确保记忆**跨会话共享**。

### Step 2: 读路径 — 记忆注入 (`_inject_memory`)

仅在 `turn_type == "main"` 时触发（非 skill evolution / teacher 等内部轮次）。

```python
# 1. 提取任务描述 — 取最后一条 user message
task_desc = user_msgs[-1]["content"][:500]

# 2. 检索 — 在线程池中执行 (避免阻塞 async 事件循环)
memories = await asyncio.to_thread(
    self.memory_manager.retrieve_for_prompt, task_desc, scope_id=base_scope
)

# 3. 渲染为文本块
memory_text = self.memory_manager.render_for_prompt(memories)

# 4. 注入到 system message
#    - 如果已有 system message → 追加到末尾
#    - 如果没有 → 插入一条新的 system message
messages[0]["content"] += "\n\n" + memory_text
```

**检索内部流程**:
- `MemoryRetriever` 根据策略选择模式 (keyword/embedding/hybrid/auto)
- keyword 模式: FTS5 全文搜索 + IDF 排序
- hybrid 模式: IDF 关键词分 + cosine 向量分 + importance + recency + reinforcement 加权融合
- 结果按 `MemoryPolicy` 参数裁剪 (默认 top 6 条, 最多 800 tokens)
- LRU 缓存 (16 条) 避免重复检索

**渲染格式** (注入到 prompt 中的样子):

```
## Long-term Memory

### Working Summary
[PINNED] 用户偏好 Python 异步编程...  (importance: 0.99)

### Project State
当前项目使用 FastAPI + SQLite...  (importance: 0.7, 2h ago)

### Preference
用户喜欢简洁的代码风格...  (importance: 0.6, 1d ago)
```

### Step 3: 转发给 LLM

修改后的 messages（包含注入的记忆文本）转发给配置的 LLM provider（如 Azure OpenAI）。客户端完全无感知。

### Step 4: 响应返回 + Turn 缓冲

LLM 响应流式返回给客户端的同时:

```python
turn_entry = {"prompt_text": prompt_text, "response_text": response_text}

# 独立的 memory buffer (不受 skill evolution 清空影响)
self._session_memory_turns[session_id].append(turn_entry)
```

**关键设计**: memory 有独立的 turn 缓冲区 `_session_memory_turns`，与 skill evolution 的 `_session_turns` 分离。这解决了之前 skill evolution 触发时会清空 memory turns 的 bug。

### Step 5: 会话结束 — 记忆提取 (`_ingest_memory_for_session`)

当客户端发送 `session_done=True` 时触发:

```python
memory_turns = self._session_memory_turns.pop(session_id, [])
# 异步任务, 不阻塞响应返回
self._safe_create_task(
    self._ingest_memory_for_session(session_id, memory_turns, scope)
)
```

**提取内部流程**:
1. `ingest_session_turns()` 对每个 turn 执行模式匹配提取:
   - 从 response 侧提取事实 → `SEMANTIC`
   - 识别 "I prefer/like/want" → `PREFERENCE`
   - 识别项目状态描述 → `PROJECT_STATE`
   - 识别过程性观察 → `PROCEDURAL_OBSERVATION`
   - 构建多轮上下文的滚动摘要 → `WORKING_SUMMARY`
2. 对提取的 MemoryUnit 去重（与已有记忆 Jaccard 比较）
3. 冲突检测（同 scope/type 的矛盾内容）
4. 写入 SQLite + 记录遥测事件
5. 触发 `MemoryConsolidator` 合并
6. 刷新 `MemoryPolicy`（基于最新统计）

## 两条路径对比

| | 读路径 (注入) | 写路径 (提取) |
|---|---|---|
| **触发时机** | 每次 main turn 请求前 | 会话结束 (session_done) |
| **作用域** | base_scope (跨会话) | base_scope (跨会话) |
| **执行方式** | `asyncio.to_thread` (同步→线程) | `_safe_create_task` (后台异步) |
| **阻塞请求** | 是 (必须等检索完成才转发) | 否 (fire-and-forget) |
| **对客户端** | 透明 (只是 prompt 变了) | 透明 (响应已返回) |

## 作用域机制 — 为什么跨会话有效

```
会话 A: scope = "user:alice|workspace:proj|session:abc123"
                                    ↓ base_scope()
存储/检索: scope = "user:alice|workspace:proj"
                                    ↑ base_scope()
会话 B: scope = "user:alice|workspace:proj|session:def456"
```

`base_scope()` 剥离 session 后缀，使不同会话共享同一个记忆池。

## 与 Skill 系统的关系

Memory 和 Skill 在代理内部是**并行注入**的两个独立模块:

```python
# api_server.py 第 926-930 行
if turn_type == "main":
    if self.memory_manager:
        messages = await self._inject_memory(messages, ...)   # 先注入记忆
    if self.skill_manager:
        messages = self._inject_skills(messages)               # 再注入技能
```

- Memory: 注入的是"这个用户/项目的历史上下文"
- Skill: 注入的是"你可以使用这些能力/工具"
- 两者互不干扰，各有独立的 turn 缓冲和生命周期

## 后台维护

除了请求级的读写路径，还有后台 `MemoryUpgradeWorker` (asyncio Task):
- 定期执行 TTL 过期 + 合并
- 触发自升级循环 (候选策略生成→回放评估→晋升)
- 对客户端完全不可见
