# OpenClaw 多 Channel 机制详解

> 分析来源：`src/routing/resolve-route.ts`、`src/routing/session-key.ts`、`src/config/sessions/`、`src/auto-reply/dispatch.ts`、`src/auto-reply/reply/route-reply.ts`、`src/auto-reply/templating.ts`、`src/infra/outbound/deliver.ts`、`src/gateway/server-methods/send.ts`

---

## 一、核心结论（先看这里）

| 问题                                          | 结论                                                              |
| --------------------------------------------- | ----------------------------------------------------------------- |
| 同一 agent 能接收多个 channel 的消息吗？      | **能**，默认配置下所有 DM 进同一个 session                        |
| Agent 能"看到"消息来自哪个 channel 吗？       | 能，通过 system prompt 里注入的 OriginatingChannel 等模板变量     |
| Agent 回复能自动路由回原始 channel 吗？       | **能**，通过 OriginatingChannel + OriginatingTo 实现精确路由      |
| Agent 能主动向其他 channel/session 发消息吗？ | 能，用 `sessions_send` 工具跨 session 通信，或 Gateway `send` API |
| Group 消息和 DM 消息共享同一个 session 吗？   | **不**，Group 消息总是拥有独立 session key                        |

---

## 二、消息路由：从 Channel 到 Session

### 2.1 整体流程

```
各 Channel Plugin（WhatsApp/Telegram/Slack/Discord/...）
    ↓ 收到外部消息
标准化为 MsgContext（统一格式）
    ↓
resolveAgentRoute()  →  决定哪个 agentId 处理
    ↓
buildAgentPeerSessionKey()  →  决定进入哪个 session
    ↓
Session Transcript (.jsonl)  ←  记录消息（含 channel origin 元数据）
    ↓
Agent 处理，生成回复
    ↓
routeReply()  →  根据 OriginatingChannel/OriginatingTo 发回原始 channel
```

### 2.2 Agent 路由：binding 规则决定哪个 agent 接收

`resolveAgentRoute()`（`routing/resolve-route.ts`）按以下优先级匹配 `openclaw.json` 中的 `bindings`：

1. `peer` 精确匹配（DM 对端 ID 或 Group ID）
2. `parentPeer` 匹配（Thread 继承）
3. `guildId + roles`（Discord 角色路由）
4. `guildId`（Discord Guild）
5. `teamId`（MSTeams）
6. `accountId`（多账户）
7. `channel` 级兜底
8. 默认 agent

多个 match 字段是 **AND** 语义（全部满足才匹配）。

### 2.3 SessionKey 生成：决定是否共享 session

`buildAgentPeerSessionKey()`（`routing/session-key.ts`）决定消息进入哪个 session。

**SessionKey 格式示例**：

| 场景                           | SessionKey                                         |
| ------------------------------ | -------------------------------------------------- |
| DM（默认 dmScope=main）        | `agent:main:main`                                  |
| DM（dmScope=per-channel-peer） | `agent:main:telegram:direct:123456789`             |
| Telegram 群组                  | `agent:main:telegram:group:group_id_hash`          |
| Slack 频道                     | `agent:main:slack:channel:C1234567890`             |
| 多账户 WhatsApp                | `agent:main:whatsapp:account2:direct:peer_id`      |
| Telegram Topic                 | `agent:main:telegram:group:group_abc123:topic:123` |

**关键点**：
- Group/Channel 消息**总是**获得独立的 session key（基于 group ID）
- DM 消息是否共享 session，取决于 `session.dmScope` 配置
- Agent 可以在同一时刻维护多个活跃 session（不同 session key）

### 2.4 dmScope：控制 DM 的 session 隔离粒度

在 `openclaw.json` 中配置：

```json5
{
  "session": {
    "dmScope": "main"  // 默认值
  }
}
```

| dmScope 值                   | 行为                                                                         |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `"main"`（默认）             | 所有 DM 共享一个 session（`agent:main:main`），跨 channel 消息全进同一个对话 |
| `"per-peer"`                 | 每个 peer ID 独立 session，但同一个人从不同 channel 发来的消息仍共享         |
| `"per-channel-peer"`         | channel + peer ID 组合决定 session，Telegram 和 WhatsApp 的消息分开          |
| `"per-account-channel-peer"` | 最细粒度：account + channel + peer ID 全部独立                               |

---

## 三、MsgContext：消息携带的 Channel 元数据

所有 channel 的消息被标准化为统一的 `MsgContext` 对象（`auto-reply/templating.ts`），以 Handlebars 模板变量的形式注入给 agent。

### 3.1 Channel 相关的关键字段

**来源标识**：

| 字段                 | 含义                                     | 示例                               |
| -------------------- | ---------------------------------------- | ---------------------------------- |
| `OriginatingChannel` | 消息来源 channel，**回复路由依赖此字段** | `"telegram"`, `"slack"`            |
| `OriginatingTo`      | 回复目标地址                             | `"123456789"`, `"U123@team"`       |
| `Provider`           | Provider 标识                            | `"whatsapp"`, `"telegram"`         |
| `Surface`            | UI 表面标识                              | `"discord"`, `"slack"`             |
| `ChatType`           | 消息类型                                 | `"direct"`, `"group"`, `"channel"` |
| `AccountId`          | 多账户场景的账户 ID                      | `"personal"`, `"biz"`              |

**发送者信息**：

| 字段             | 含义                                |
| ---------------- | ----------------------------------- |
| `From`           | 发送者 ID（channel 特定格式）       |
| `SenderName`     | 显示名称                            |
| `SenderUsername` | 用户名（如 Telegram @handle）       |
| `SenderE164`     | E.164 格式电话号（WhatsApp/Signal） |
| `SenderId`       | 数字 ID（Telegram/Discord）         |

**Group/Channel 特定**：

| 字段              | 含义                                               |
| ----------------- | -------------------------------------------------- |
| `GroupSubject`    | Group 主题/名称                                    |
| `GroupChannel`    | Channel 名称（如 `#general`）                      |
| `GroupSpace`      | Workspace/Server（Slack Workspace、Discord Guild） |
| `MessageThreadId` | Thread/Topic ID                                    |
| `IsForum`         | Telegram 论坛 group 标记                           |

**回复上下文**：

| 字段            | 含义               |
| --------------- | ------------------ |
| `ReplyToId`     | 被回复的消息 ID    |
| `ReplyToBody`   | 被回复的原消息文本 |
| `ReplyToSender` | 被回复消息的发送者 |

### 3.2 Agent 如何"看到"这些信息

这些字段作为 Handlebars 模板变量注入到 `USER.md`、`AGENTS.md`、`SOUL.md` 等 workspace 文件中。例如：

```markdown
<!-- USER.md 中可以写 -->
当前用户通过 {{Provider}} 与你通信，消息类型为 {{ChatType}}。
{{#if GroupSubject}}当前在群组「{{GroupSubject}}」中。{{/if}}
```

---

## 四、回复路由：精确发回原始 Channel

### 4.1 核心机制

回复路由由 `routeReply()`（`auto-reply/reply/route-reply.ts`）实现，**必须使用 `OriginatingChannel` 和 `OriginatingTo`** 而不是 session store 中的 `lastChannel`。

原因：当同一个 session 接收来自多个 channel 的消息时，`lastChannel` 是最后一条消息的来源，使用它会导致回复发到错误的 channel。

```
消息来自 Telegram → OriginatingChannel=telegram, OriginatingTo=123456789
消息来自 Slack   → OriginatingChannel=slack,    OriginatingTo=U456

Agent 处理 Telegram 消息时 → 回复发到 Telegram:123456789 ✓
Agent 处理 Slack 消息时   → 回复发到 Slack:U456 ✓
```

### 4.2 底层发送：deliverOutboundPayloads

最底层的发送实现（`infra/outbound/deliver.ts`）支持以下 channel：

- `whatsapp`、`telegram`、`slack`、`discord`
- `signal`、`imessage`、`matrix`、`msteams`
- 及插件扩展的自定义 channel

---

## 五、Agent 主动向 Channel 发消息的工具

### 5.1 `sessions_send` 工具（跨 session 通信）

允许 agent 向另一个 session 发送消息并等待回复，用于 **agent 间通信** 或向其他对话注入消息。

**参数**：

```json
{
  "sessionKey": "agent:main:telegram:direct:123456789",
  "label": "my-worker-session",
  "message": "要发送的消息内容",
  "timeoutSeconds": 5
}
```

`sessionKey` 和 `label` 二选一。

**返回值**：

```json
{
  "status": "ok",
  "reply": "目标 agent 的回复文本",
  "sessionKey": "实际使用的 session key"
}
```

**注意**：这是同步工具，会等待目标 session 的 agent 处理并回复后才返回。

### 5.2 Gateway `send` API（底层发送 API）

通过 Gateway RPC 向任意 channel 发消息，不经过 session 系统：

```json
POST /gateway
{
  "method": "send",
  "params": {
    "to": "123456789",
    "message": "消息内容",
    "channel": "telegram",
    "accountId": "default",
    "sessionKey": "agent:main:main",
    "idempotencyKey": "unique-id"
  }
}
```

`sessionKey` 可选：如果提供，发出的消息会被 mirror 到对应 session 的 transcript 中，agent 后续能在上下文中看到这条消息。

### 5.3 工具权限

与消息相关工具的权限配置（`openclaw.json` 的 `tools` 字段）：

```json5
{
  "tools": {
    "allow": ["sessions_send", "sessions_list", "sessions_history"]
  }
}
```

---

## 六、Session Store 中存储的 Channel 信息

`sessions.json` 中每个 session entry 存储来自消息的 channel 元数据：

```json
{
  "agent:main:main": {
    "deliveryContext": {
      "channel": "telegram",
      "to": "123456789",
      "accountId": "default"
    },
    "origin": {
      "provider": "telegram",
      "from": "123456789",
      "chatType": "direct",
      "label": "Alice"
    },
    "lastChannel": "telegram",
    "lastTo": "123456789"
  },
  "agent:main:telegram:group:abc123": {
    "deliveryContext": {
      "channel": "telegram",
      "to": "-1001234567890",
      "accountId": "default"
    },
    "chatType": "group",
    "groupId": "-1001234567890",
    "subject": "Team Discussion"
  }
}
```

**注意**：`deliveryContext` 和 `lastChannel` 只记录**最后一条消息**的来源。在多 channel 共享的 session 中，这些字段会随每条新消息被覆盖，不能用于追溯历史消息的来源。

---

## 七、多 Channel 共享 Session 的完整示例

**配置**：`dmScope: "main"`（默认），所有 DM 进同一 session

**场景**：用户先后从 Telegram、Slack 向同一个 agent 发消息，同时还有一条来自 WhatsApp 群组的消息

```
Step 1: Telegram DM
  SessionKey → agent:main:main
  Transcript 追加：{ role: "user", content: "msg1", origin: { provider: "telegram" } }
  回复 → 发到 Telegram:123456789

Step 2: Slack DM（同一个 session）
  SessionKey → agent:main:main
  Agent 能看到完整历史（包含 Telegram 的 msg1 + 回复）
  Transcript 追加：{ role: "user", content: "msg2", origin: { provider: "slack" } }
  回复 → 发到 Slack:U456

Step 3: WhatsApp 群组消息（独立 session）
  SessionKey → agent:main:whatsapp:group:group789
  进入独立 session，不共享上面的历史
  回复 → 发到 WhatsApp group_789
```

**关键观察**：
1. DM 消息跨 channel 共享 session（默认行为）
2. Group/Channel 消息总是独立 session，即使来自同一个 channel
3. Agent 在共享 session 中能看到所有来源的消息历史
4. 回复总是精确路由回消息的原始 channel

---

## 八、Benchmark 设计相关含义

> 这一节说明上述机制对 SimpleMem_Claw benchmark 数据设计的影响

### 8.1 Session 里的消息是什么

在真实 openclaw 使用中，**session transcript 里存的是 user 和 agent 之间的对话**，而不是多个用户之间互相讨论的内容。Agent 不会自然地"看到"Alice 和 Bob 在 Slack 上的争论——除非有人把那段争论转发给 agent 作为 user 消息。

### 8.2 让 agent 接触多 channel 讨论内容的可行方案

**方案 A：Workspace 静态文件（当前 articla-quarrel 的思路）**

把各 channel 的对话记录以 `.md` 文件形式放入 workspace，作为 system prompt 的一部分在每次会话开始时注入。Agent 通过读取这些文件了解多方讨论内容，然后在 user 消息触发下回答问题。

- 优点：实现简单，context 长度可精确控制
- 限制：所有"历史讨论"是静态的，不会随对话轮次动态更新
- 注入上限：单文件 20,000 chars，全部文件合计 150,000 chars（约 75k token）

**方案 B：Session Transcript 多轮方案**

在 session transcript（`.jsonl`）里预先写入多轮 user/assistant 消息，模拟"agent 被逐步告知各轮讨论进展"的过程。每个 user 消息代表一个阶段的讨论更新，agent 需在积累的上下文中回答问题。

- 优点：能自然地模拟多轮因果依赖，context 可超过 workspace 注入上限
- 限制：`.jsonl` 不能直接手写（需要通过 SessionManager，详见 compact-command.md 的警告），实际操作通过 `openclaw agent --message` 命令逐轮注入

**方案 C：`openclaw agent --message` 逐轮注入**

通过命令行，以 user 身份分多次把讨论摘要/原文发给 agent，形成真实的多轮 session 历史，再提问。这是方案 B 的实际操作方式。

### 8.3 Workspace 文件注入上限的影响

workspace 文件注入上限（150k chars ≈ 75k token）远低于 benchmark 目标（300-500k token）。因此：

- **如果用方案 A**：必须主要靠 session transcript（`.jsonl` 里的多轮对话历史）来堆积 context，workspace 文件只用于放任务说明和少量背景资料
- **如果用方案 B/C**：session transcript 可以积累到模型的 context 上限（200k token），再配合 workspace 文件，总 context 可达目标范围

### 8.4 支持的 Channel 类型

作为背景材料文件的"channel"来源，可以模拟以下平台的对话格式：

- `whatsapp` / `telegram` — 即时消息格式（时间戳 + 发送者名 + 内容）
- `slack` / `discord` — 工作协同工具频道格式
- `email` — 邮件链格式（From/To/Date/Subject/Body）
- `matrix` / `msteams` — 企业 IM 格式
- GitHub Issues / PR 评论 — 代码协作平台格式

---

## 九、关键源码文件索引

| 功能                               | 文件路径                               |
| ---------------------------------- | -------------------------------------- |
| Agent 路由决策                     | `src/routing/resolve-route.ts`         |
| SessionKey 生成                    | `src/routing/session-key.ts`           |
| Session Key 解析（消息处理时）     | `src/config/sessions/session-key.ts`   |
| Session 元数据（origin、delivery） | `src/config/sessions/metadata.ts`      |
| 消息分发入口                       | `src/auto-reply/dispatch.ts`           |
| 回复路由                           | `src/auto-reply/reply/route-reply.ts`  |
| MsgContext 所有模板变量            | `src/auto-reply/templating.ts`         |
| 底层 Channel 发送                  | `src/infra/outbound/deliver.ts`        |
| Gateway send API                   | `src/gateway/server-methods/send.ts`   |
| sessions_send tool                 | `src/agents/openclaw-tools.ts`         |
| Session Store 读写                 | `src/config/sessions/store.ts`         |
| Delivery Info 提取                 | `src/config/sessions/delivery-info.ts` |
