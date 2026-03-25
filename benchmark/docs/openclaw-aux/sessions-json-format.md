# sessions.json 格式与解析机制

> 关键源码：`src/config/sessions/`（store.ts、types.ts、paths.ts、transcript.ts）

---

## 文件位置

### 默认路径

```
~/.openclaw/agents/<agentId>/sessions/sessions.json
```

### 路径解析优先级

1. `openclaw.json` 中 `session.store` 字段（支持 `{agentId}` 模板替换）
2. `OPENCLAW_STATE_DIR` 环境变量指定根目录
3. 默认：`~/.openclaw/agents/<agentId>/sessions/sessions.json`

**`{agentId}` 模板示例：**

```jsonc
// openclaw.json
{
  "session": {
    "store": "~/.openclaw/agents/{agentId}/sessions.json"
  }
}
```

启动时 `{agentId}` 被替换为实际 agent ID，路径随后经过 `path.resolve()` 转换为绝对路径。

---

## 文件整体结构

sessions.json 是一个**平铺的 JSON 对象**，key 为 sessionKey，value 为 SessionEntry：

```json
{
  "agent:main:+15551234567": {
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "updatedAt": 1704086400000,
    "sessionFile": "550e8400-e29b-41d4-a716-446655440000.jsonl",
    ...
  },
  "agent:main:discord:group:123456789": {
    "sessionId": "660e8400-e29b-41d4-a716-446655440001",
    ...
  },
  "global": {
    "sessionId": "770e8400-e29b-41d4-a716-446655440002",
    ...
  }
}
```

**没有顶层 version 字段**，就是一个裸的 `Record<string, SessionEntry>`。

### sessionKey 格式

sessionKey 由路由逻辑生成，常见格式：

| 场景           | sessionKey 示例                      |
| -------------- | ------------------------------------ |
| WhatsApp 私聊  | `agent:main:+15551234567`            |
| Discord 群组   | `agent:main:discord:group:123456789` |
| Telegram 私聊  | `agent:main:telegram:+15557654321`   |
| 全局单会话模式 | `global` 或 `main`                   |
| 沙箱子会话     | 父key + 随机后缀                     |

---

## SessionEntry 完整字段

```typescript
// src/config/sessions/types.ts
type SessionEntry = {
  // ── 必填 ──
  sessionId: string;         // UUID，唯一会话 ID
  updatedAt: number;         // 最后更新时间戳（毫秒）

  // ── 会话文件 ──
  sessionFile?: string;      // 消息历史 .jsonl 文件路径（相对于 sessions/ 目录）

  // ── 模型信息 ──
  model?: string;            // 如 "claude-sonnet-4-6"
  modelProvider?: string;    // 如 "anthropic"、"openai"
  providerOverride?: string; // 临时覆盖提供商
  modelOverride?: string;    // 临时覆盖模型

  // ── Token 统计 ──
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
  totalTokensFresh?: boolean; // token 统计是否来自最新一次运行
  contextTokens?: number;    // 模型上下文窗口大小

  // ── 行为模式 ──
  thinkingLevel?: string;    // "off" | "default" | "full"
  verboseLevel?: string;
  reasoningLevel?: string;
  elevatedLevel?: string;

  // ── 渠道路由信息 ──
  channel?: string;          // 主渠道，如 "whatsapp"、"telegram"、"discord"
  chatType?: "direct" | "group" | "channel";
  lastChannel?: string;      // 最后一条消息来自的渠道
  lastTo?: string;           // 最后消息目标（电话号、用户ID等）
  lastAccountId?: string;    // 最后使用的账户 ID
  lastThreadId?: string | number;

  // ── 群组信息 ──
  groupId?: string;
  subject?: string;          // 群组名称/主题
  groupChannel?: string;     // 群组内的频道名
  space?: string;            // 如 Slack workspace
  groupActivation?: "mention" | "always";
  groupActivationNeedsSystemIntro?: boolean;

  // ── 消息队列 ──
  queueMode?: "steer" | "followup" | "collect" | "steer-backlog" | "queue" | "interrupt";
  queueDebounceMs?: number;
  queueCap?: number;
  queueDrop?: "old" | "new" | "summarize";
  sendPolicy?: "allow" | "deny";

  // ── 子会话（沙箱） ──
  spawnedBy?: string;        // 父会话的 sessionKey
  spawnDepth?: number;       // 0=主会话，1=子，2=子子

  // ── 显示信息 ──
  label?: string;            // 用户自定义标签
  displayName?: string;      // 自动生成的显示名称

  // ── 状态标志 ──
  systemSent?: boolean;      // 系统提示已发送
  abortedLastRun?: boolean;  // 上次运行被中断

  // ── 认证 ──
  authProfileOverride?: string;
  authProfileOverrideSource?: "auto" | "user";

  // ── 压缩/记忆 ──
  compactionCount?: number;         // 被 compaction 的次数
  memoryFlushAt?: number;           // 记忆最后清空时间戳
  memoryFlushCompactionCount?: number;

  // ── 语音 ──
  ttsAuto?: string;

  // ── 来源信息 ──
  origin?: {
    label?: string;
    provider?: string;
    surface?: string;
    chatType?: string;
    from?: string;
    to?: string;
    accountId?: string;
    threadId?: string | number;
  };
  deliveryContext?: {
    channel?: string;
    to?: string;
    accountId?: string;
    threadId?: string | number;
  };

  // ── CLI 集成 ──
  claudeCliSessionId?: string;
  cliSessionIds?: Record<string, string>;

  // ── 心跳 ──
  lastHeartbeatText?: string;
  lastHeartbeatSentAt?: number;

  // ── 快照 ──
  skillsSnapshot?: object;
  systemPromptReport?: object;
};
```

---

## 解析流程（src/config/sessions/store.ts）

### loadSessionStore()

```
1. 检查内存缓存（45 秒 TTL，由 OPENCLAW_SESSION_CACHE_TTL_MS 控制）
   └─ 验证文件 mtime 是否变化（防并发修改）

2. 从磁盘读取文件
   └─ Windows 上最多重试 3 次（处理并发写入导致的空文件）

3. JSON.parse()

4. 字段迁移（旧版兼容）
   ├─ provider  → channel
   ├─ lastProvider → lastChannel
   └─ room → groupChannel

5. normalizeSessionStore()（规范化 deliveryContext 等传递字段）

6. 存入内存缓存（深拷贝）

7. 返回深拷贝（防止外部突变）
```

---

## 写入流程（src/config/sessions/store.ts）

### updateSessionStore()（推荐 API）

```
1. 获取文件锁（withSessionStoreLock，防并发）
2. 在锁内重新读取最新状态（skipCache: true）
3. 执行 mutator(store) 修改数据
4. saveSessionStoreUnlocked()
   ├─ 清除缓存
   ├─ normalizeSessionStore()
   ├─ 维护（若 maintenance.mode = "enforce"）
   │   ├─ pruneStaleEntries()：删除超过 pruneAfter（默认 30 天）的条目
   │   ├─ capEntryCount()：保留最近 maxEntries（默认 500）条
   │   └─ archiveSessionTranscripts()：归档被删除的 .jsonl 文件
   ├─ JSON.stringify(store, null, 2)
   └─ 原子写入（临时文件 + rename，Unix 模式 0o600）
```

### 写入特性

- **原子写入**：先写 `.tmp` 临时文件，再 `rename` 到目标路径，不会出现半写文件
- **文件权限**：Unix 下设置为 `0o600`（仅所有者可读写）
- **并发安全**：写操作通过文件锁串行化

---

## 消息历史：.jsonl 文件

**sessions.json 只存元数据，实际消息存在 .jsonl 文件中。**

```
~/.openclaw/agents/<agentId>/sessions/
├── sessions.json                          # 元数据索引
├── 550e8400-...-446655440000.jsonl        # Alice 的对话历史
├── 660e8400-...-446655440001.jsonl        # Discord 群的对话历史
└── archive/                               # 被维护清理后的归档
    └── 550e8400-...-446655440000.jsonl
```

**.jsonl 格式（每行一条 JSON）：**

```jsonl
{"type":"session","version":1,"id":"550e8400-...","timestamp":"2024-01-01T00:00:00.000Z","cwd":"/workspace"}
{"role":"user","content":[{"type":"text","text":"你好"}]}
{"role":"assistant","content":[{"type":"text","text":"你好！有什么可以帮你的？"}]}
{"role":"user","content":[{"type":"text","text":"帮我搜索一下"}]}
{"role":"assistant","content":[{"type":"tool_use","id":"call_1","name":"web_search","input":{"query":"..."}},{"type":"text","text":"我来搜索"}]}
{"role":"user","content":[{"type":"tool_result","tool_use_id":"call_1","content":"搜索结果..."}]}
```

---

## 如何手动编辑 sessions.json

### 注意事项

1. **编辑前停止 openclaw**，或确保当前 agent 未在运行（文件有写锁）
2. 编辑完成后文件必须是合法 JSON（不支持 JSON5 注释）
3. `sessionId` 字段一旦设置不要修改（.jsonl 文件名与其对应）
4. `updatedAt` 是毫秒时间戳，可以用 `Date.now()` 获取当前值

### 常见编辑操作

**重置某个会话（清除 token 统计）：**
```json
{
  "agent:main:+15551234567": {
    "sessionId": "原UUID不变",
    "updatedAt": 1704086400000,
    "inputTokens": 0,
    "outputTokens": 0,
    "totalTokens": 0,
    "totalTokensFresh": false
  }
}
```

**删除某个会话：**
直接删除对应的 key，对应的 .jsonl 文件不会自动删除（需手动清理或等待归档）。

**修改会话标签：**
```json
{
  "agent:main:+15551234567": {
    "...": "其他字段不变",
    "label": "我的自定义标签"
  }
}
```

**强制下次运行重新发送系统提示：**
```json
{
  "agent:main:+15551234567": {
    "...": "其他字段不变",
    "systemSent": false
  }
}
```

---

## session.store 相关 openclaw.json 配置

```jsonc
{
  "session": {
    // 存储路径，支持 {agentId} 替换和 ~ 展开
    "store": "~/.openclaw/agents/{agentId}/sessions.json",

    // 会话作用域
    "scope": "per-sender",   // 每个发送者独立会话（默认）
    // "scope": "global",    // 所有消息共用一个会话

    // 私聊作用域细分
    "dmScope": "main",       // "main" | "per-peer" | "per-channel-peer"

    // 会话重置
    "reset": {
      "mode": "idle",        // "idle"（空闲重置）| "daily"（每日重置）
      "idleMinutes": 60,     // 空闲超过 60 分钟重置
      "atHour": 2            // 每天 2:00 AM 重置（daily 模式）
    },

    // 维护策略
    "maintenance": {
      "mode": "warn",        // "warn"（只警告）| "enforce"（自动清理）
      "pruneAfter": "30d",   // 删除 30 天未活跃的 session
      "maxEntries": 500,     // 最多保留 500 条 session
      "rotateBytes": "10mb"  // sessions.json 超过 10MB 时轮转备份
    }
  }
}
```

---

## 关键源码文件

| 文件                                | 内容                                                 |
| ----------------------------------- | ---------------------------------------------------- |
| `src/config/sessions/types.ts`      | SessionEntry 完整类型定义、mergeSessionEntry()       |
| `src/config/sessions/store.ts`      | 读写、锁、缓存、维护（prune、cap、rotate）           |
| `src/config/sessions/paths.ts`      | resolveDefaultSessionStorePath()、resolveStorePath() |
| `src/config/sessions/transcript.ts` | .jsonl 文件操作，消息追加                            |
| `src/config/sessions/metadata.ts`   | deriveSessionMetaPatch()，元数据自动派生             |
| `src/config/types.base.ts`          | openclaw.json 里 SessionConfig 的类型定义            |

## 补充 QA

```
如果某个agent的~/.openclaw/agents/<agentId>/sessions里缺少sessions.json，下次以openclaw --agent agent-id --session session-id的形式指定该agent运行在其文件夹内存在的某个session里，可行吗 
```

```
完整追踪了代码后，答案如下：                          

可行。 下面是完整的执行路径：                                                                                                                                                
  
---                                                                                                                                                                          
逐步追踪                                                                                                                                                                   
                                                                                                                                                                            
1. loadSessionStore() 找不到 sessions.json 时（src/config/sessions/store.ts）

fs.readFileSync 抛异常，被 catch {} 静默捕获，返回空对象 {}，不报错。

2. resolveSessionKeyForRequest()（src/commands/agent/session.ts:42）

--agent agent-id
  → resolveExplicitAgentSessionKey({ agentId: "agent-id" })
  → sessionKey = "agent:agent-id:main"   ← agent 的主 session key
  → storePath = ~/.openclaw/agents/agent-id/sessions/sessions.json
  → sessionStore = {}  （文件不存在，返回空对象）

由于 explicitSessionKey 已经确定（非空），后面按 sessionId 在 store 中查找的逻辑块被跳过（第69行 !explicitSessionKey 条件为 false）。

3. resolveSession()（第143行）

const sessionId = opts.sessionId?.trim()   // ← 直接使用你提供的 UUID
const isNewSession = !fresh && !opts.sessionId  // = false（不视为新 session）

4. resolveSessionFilePath()（src/config/sessions/paths.ts:195）

由于 sessionEntry 是 undefined（store 为空，没有 sessionFile 字段可读），走 fallback：

resolveSessionTranscriptPathInDir(sessionId, sessionsDir)
// → ~/.openclaw/agents/agent-id/sessions/<uuid>.jsonl

如果该 .jsonl 文件存在 → Pi SDK 打开它，历史对话完整继续。

5. 运行结束后（agentCommand() 第613行）

if (sessionStore && sessionKey) {    // sessionKey = "agent:agent-id:main"，条件成立
  await updateSessionStoreAfterAgentRun(...)
  // → 自动创建 sessions.json，写入该 session 的元数据
}

---
结论

┌──────────────────────────────────┬──────────────────────────────┐
│               问题               │             结论             │
├──────────────────────────────────┼──────────────────────────────┤
│ sessions.json 缺失会报错吗？     │ 不会，返回空 {}              │
├──────────────────────────────────┼──────────────────────────────┤
│ 指定的 session UUID 会被使用吗？ │ 会，直接用于定位 .jsonl 文件 │
├──────────────────────────────────┼──────────────────────────────┤
│ 历史对话能恢复吗？               │ 能，只要 .jsonl 文件存在     │
├──────────────────────────────────┼──────────────────────────────┤
│ sessions.json 会被创建吗？       │ 会，运行结束后自动写入       │
└──────────────────────────────────┴──────────────────────────────┘

---
注意

正确的 CLI 语法是：

openclaw agent --agent <agent-id> --session-id <uuid>
#                ^^^^^ 子命令        ^^^^^^^^^^^ 注意是 --session-id 不是 --session

运行后 sessions.json 会被创建，session 注册在 "agent:<agent-id>:main" 这个 key 下。
```
