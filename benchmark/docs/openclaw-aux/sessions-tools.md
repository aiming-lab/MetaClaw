# group:sessions 工具集详解

`group:sessions` 是 openclaw 原生提供的会话管理工具组，包含 6 个工具，供 AI 代理在运行时管理自身及子代理的会话。

---

## 工具一览

| 工具名 | 功能简述 |
|--------|---------|
| `sessions_list` | 列出当前代理的所有会话 |
| `sessions_history` | 读取指定会话的历史消息 |
| `sessions_send` | 向会话发送消息（A2A 通信） |
| `sessions_spawn` | 创建并运行子代理（one-shot 任务） |
| `session_status` | 查询/切换当前会话的状态和模型 |
| `subagents` | 列出、终止或引导子代理 |

---

## 一、`sessions_list`

列出当前代理的所有会话，可按类型、活跃时间和消息数过滤。

### 输入参数

```typescript
{
  kinds?: SessionKind[];     // 过滤类型（见下方枚举），省略则返回全部
  limit?: number;            // 最多返回条数（默认 50，最大 200）
  activeMinutes?: number;    // 仅返回最近 N 分钟有活动的会话
  messageLimit?: number;     // 每个会话额外附带最后 N 条消息（默认 0，最大 10）
}
```

**SessionKind 枚举值：**

```
"default" | "child" | "ephemeral" | "webhook" |
"telegram" | "discord" | "whatsapp" | "line" |
"facebook" | "instagram" | "wechat" | "slack" |
"email" | "matrix" | "api"
```

### 返回值

```typescript
{
  count: number;
  sessions: SessionListRow[];
}
```

**SessionListRow 结构：**

```typescript
type SessionListRow = {
  key: string;              // 会话唯一键，如 "ops/sessions/1234"
  kind: SessionKind;        // 会话类型
  channel: string;          // 来源渠道名，如 "telegram"、"discord"、"default"
  label?: string;           // 用户可读标签
  displayName?: string;     // 显示名称
  deliveryContext?: any;    // 渠道投递上下文
  updatedAt?: string;       // 最后更新时间（ISO 8601）
  sessionId?: string;       // 会话内部 ID
  model?: string;           // 当前使用的模型
  contextTokens?: number;   // 当前上下文 token 数
  totalTokens?: number;     // 历史累计 token 数
  thinkingLevel?: number;   // thinking 级别（0/1/2）
  verboseLevel?: number;    // verbose 级别
  systemSent?: boolean;     // 是否已发送 system prompt
  abortedLastRun?: boolean; // 上次运行是否被中断
  sendPolicy?: string;      // 消息投递策略
  lastChannel?: string;     // 最后一次消息的渠道
  lastTo?: string;          // 最后消息的接收方
  lastAccountId?: string;   // 最后消息的账户 ID
  transcriptPath?: string;  // JSONL 文件路径
  messages?: unknown[];     // 最后 N 条消息（仅 messageLimit > 0 时存在）
};
```

---

## 二、`sessions_history`

读取指定会话的历史消息内容，含工具调用结果。

### 输入参数

```typescript
{
  sessionKey: string;      // 会话键（来自 sessions_list 的 key 字段）
  limit?: number;          // 最多返回最后 N 条消息（默认 50，最大 200）
  includeTools?: boolean;  // 是否包含工具调用和工具结果消息（默认 true）
}
```

### 返回值

```typescript
{
  sessionKey: string;
  messages: HistoryMessage[];   // 见下方格式
  truncated: boolean;           // 是否触发了 80KB 字节上限截断
  droppedMessages: number;      // 因截断丢弃的消息条数
  contentTruncated: boolean;    // 是否有消息体内容被截断（超过 4000 字符）
  bytes: number;                // 本次返回内容的字节数
}
```

**HistoryMessage 格式（消息内容按 role 不同）：**

```typescript
// user / assistant 消息
{ role: "user" | "assistant"; content: string; timestamp: number }

// toolCall 消息（当 includeTools: true 时）
{ role: "toolCall"; name: string; arguments: any; id: string; timestamp: number }

// toolResult 消息（当 includeTools: true 时）
{ role: "toolResult"; toolName: string; content: ContentBlock[]; isError: boolean; timestamp: number }
```

**重要行为限制：**

| 限制 | 值 | 说明 |
|------|----|------|
| 字节上限 | 80KB | 超出则从最早消息开始丢弃，直到总量满足上限 |
| 文本截断 | 4000 字符 | 单条消息 content 超过此长度时截断并附加 `[truncated]` |
| 图像处理 | 数据剥离 | `ImageContent` 的 `data` 字段被替换为 `{omitted: true, bytes: <原始字节数>}`，`mimeType` 保留 |

---

## 三、`sessions_send`

向指定会话发送消息，等待代理处理后返回回复（A2A 异步通信）。

### 输入参数

```typescript
{
  sessionKey?: string;      // 目标会话键；与 label/agentId 三选一
  label?: string;           // 按会话标签查找目标
  agentId?: string;         // 按 agentId 查找目标（取该代理默认会话）
  message: string;          // 发送的消息内容（纯文本）
  timeoutSeconds?: number;  // 等待超时秒数（默认 300，0 表示不等待直接返回）
}
```

### 返回值

```typescript
{
  runId: string;             // 本次运行的唯一 ID
  status: "ok" | "accepted" | "timeout" | "error" | "forbidden";
  reply?: string;            // 代理的回复文本（status 为 "ok" 时存在）
  sessionKey: string;        // 实际处理的会话键
  delivery?: DeliveryResult; // 投递元数据
}
```

**status 含义：**

| status | 含义 |
|--------|------|
| `"ok"` | 代理已处理完成，`reply` 含回复内容 |
| `"accepted"` | `timeoutSeconds: 0` 时，消息已入队但未等待结果 |
| `"timeout"` | 等待超时，代理未在规定时间内完成 |
| `"error"` | 发送失败（会话不存在、代理不可用等） |
| `"forbidden"` | 当前代理没有权限向目标会话发送消息 |

---

## 四、`sessions_spawn`

创建一个子代理并执行一次性任务，任务完成后可选自动清理。

### 输入参数

```typescript
{
  task: string;                 // 子代理要执行的任务描述
  label?: string;               // 为子会话指定可读标签
  agentId?: string;             // 指定子代理使用的 agent 配置 ID（默认同当前代理）
  model?: string;               // 覆盖子代理使用的模型
  thinking?: 0 | 1 | 2;        // thinking 级别（0=关闭, 1=普通, 2=深度）
  runTimeoutSeconds?: number;   // 任务执行超时秒数
  cleanup?: boolean;            // 任务完成后是否删除子会话（默认 false）
}
```

### 返回值

```typescript
type SpawnSubagentResult = {
  status: "accepted" | "forbidden" | "error";
  childSessionKey?: string;  // 子会话键（status 为 "accepted" 时存在）
  runId?: string;            // 运行 ID
  error?: string;            // 错误信息（status 为 "error" 时存在）
}
```

**注意：** `sessions_spawn` 是 fire-and-forget 风格——任务提交后立即返回（`status: "accepted"`），不等待子代理完成。若需要等待结果，使用 `sessions_send` 代替。

---

## 五、`session_status`

查询当前会话的运行状态，或临时切换本次会话使用的模型。

### 输入参数

```typescript
{
  sessionKey?: string;  // 目标会话键（省略则使用当前会话）
  model?: string;       // 临时切换模型（仅本次会话生效）
}
```

### 返回值

工具返回两部分内容：

**content（展示给 AI 的文本卡片）：**

```
[text] 当前模型: gpt-4o
上下文: 12,340 tokens
会话键: ops/sessions/my-session
Thinking: 关闭 | Verbose: 0
...
```

**details（结构化数据）：**

```typescript
{
  ok: boolean;
  sessionKey: string;
  changedModel: boolean;   // 是否在本次调用中切换了模型
  statusText: string;      // 同 content 中的文本内容
}
```

---

## 六、`subagents`

列出当前正在运行的子代理，或向子代理发送终止/引导指令。

### 输入参数

```typescript
{
  action?: "list" | "kill" | "steer";  // 操作类型（默认 "list"）
  target?: string;       // 目标子代理的 sessionKey 或 runId（kill/steer 时必填）
  message?: string;      // 引导消息（action 为 "steer" 时必填）
  recentMinutes?: number; // list 时仅返回最近 N 分钟活跃的子代理（默认 60）
}
```

### 返回值（按 action 不同）

**`action: "list"`**

```typescript
{
  count: number;
  subagents: SubagentInfo[];
}

type SubagentInfo = {
  sessionKey: string;
  runId: string;
  label?: string;
  startedAt: string;   // ISO 8601
  status: "running" | "idle" | "done";
  model?: string;
}
```

**`action: "kill"`**

```typescript
{
  ok: boolean;
  sessionKey: string;
  cascade: boolean;    // 是否级联终止了该子代理的子代理
  message: string;     // 操作结果描述
}
```

**`action: "steer"`**

```typescript
{
  ok: boolean;
  sessionKey: string;
  message: string;     // 操作结果描述
}
```

**注意：** `kill` 操作会级联终止目标子代理下所有子孙代理，不可撤销。

---

## 七、工具使用场景对照

| 场景 | 推荐工具 |
|------|---------|
| 查看当前有哪些活跃会话 | `sessions_list` + `activeMinutes` |
| 读取某个渠道用户的历史对话 | `sessions_history` |
| 请另一个代理执行任务并等待结果 | `sessions_send` |
| 异步派发子任务（不等结果） | `sessions_spawn` |
| 临时切换模型后继续对话 | `session_status` + `model` |
| 取消失控的子代理 | `subagents` + `action: "kill"` |
| 向运行中的子代理追加指示 | `subagents` + `action: "steer"` |

---

## 八、权限说明

`group:sessions` 工具组受 tool policy 控制。代理配置中可按需开启：

```jsonc
{
  "tools": {
    "groups": ["sessions"]
  }
}
```

部分操作（如 `sessions_send` 跨代理通信、`subagents kill`）还受 allowlist 和代理间权限策略约束，未授权操作会返回 `status: "forbidden"`。
