# OpenClaw Channel 消息格式转换机制

## 概述

OpenClaw 支持多种即时通讯 channel（Slack、Telegram、Discord、Signal、iMessage、WhatsApp 等）。当用户从任意 channel 发送消息时，OpenClaw 会将原始消息转化为结构化的 `MsgContext` 对象，再经过多个处理阶段，最终以特定格式传递给 AI agent。本文档详细描述这一转换流程。

---

## 核心数据结构：MsgContext

**文件**：`src/auto-reply/templating.ts`

`MsgContext` 是贯穿整个消息处理流程的核心类型，携带所有消息元数据。关键字段如下：

| 字段 | 说明 |
|------|------|
| `Body` | **带 envelope 的完整消息**，包含 channel 标签、发送者、时间戳前缀。用于 session 上下文及模板变量 `{{Body}}` |
| `BodyForAgent` | **干净的原始用户文本**（无 envelope/历史/发送者标签）。优先用于构造实际 agent prompt |
| `RawBody` | `CommandBody` 的遗留别名，不含结构化上下文 |
| `CommandBody` | 用于指令检测的文本 |
| `BodyForCommands` | 指令解析时优先使用（若设置） |
| `InboundHistory` | 结构化的群组历史消息列表（sender + body + timestamp） |
| `SenderName` | 发送者显示名称 |
| `SenderId` | 发送者 ID |
| `SenderUsername` | 发送者用户名（不含 @ 前缀） |
| `SenderE164` | 发送者手机号（E.164 格式，如 +8613800138000） |
| `ConversationLabel` | 会话的人类可读标签（频道名、群组名、用户名等） |
| `GroupSubject` | 群组/频道主题名 |
| `GroupChannel` | 频道型群组标签（如 #general、#support） |
| `GroupSpace` | 所属 workspace/guild（如 Discord guild ID） |
| `ChatType` | 会话类型："direct" / "group" / "channel" |
| `Provider` / `Surface` | channel 标识符（如 "slack"、"telegram"、"discord"） |
| `OriginatingChannel` | 消息来源 channel，用于路由回复 |
| `ReplyToBody` / `ReplyToSender` | 被回复消息的内容和发送者 |
| `ForwardedFrom` / `ForwardedFromType` | 转发消息的来源信息 |
| `ThreadStarterBody` | 线程/话题的首条消息 |
| `Timestamp` | 消息时间戳（毫秒） |
| `MediaPath` / `MediaPaths` / `MediaType` | 媒体附件信息 |
| `WasMentioned` | 在群组中 bot 是否被 @ 提及 |
| `CommandAuthorized` | 发送者是否有权执行控制命令 |

---

## Envelope 格式：Body 字段的构造

**文件**：`src/auto-reply/envelope.ts`

### 核心函数 `formatAgentEnvelope`

这是 envelope 格式化的底层函数，生成带方括号前缀的消息字符串：

```
[{channel} {from} {+elapsed}? {timestamp}?] {body}
```

**示例**：
```
[Slack #general +5m Thu Jan 15 10:30:00 PST 2024] Alice: hello
[Telegram group:12345 Wed Jan 14 15:00:00 UTC 2024] Bob: hi there
[Discord #dev-chat Mon Jan 13 08:00:00 PST 2024] Charlie: 请帮我看下这个
```

- `channel`：channel 名称字符串（如 "Slack"、"Telegram"、"Discord"）
- `from`：会话标签（直接消息用发送者名，群组用频道/群名）
- `+elapsed`：距上次回复的间隔时长（如 "+5m"，可通过配置关闭）
- `timestamp`：格式化时间戳（支持 local/UTC/IANA 时区，可通过配置关闭）

Header 中的特殊字符会被转义（`[` → `(`，`]` → `)`，多余空白压缩）。

### 高层函数 `formatInboundEnvelope`

**文件**：`src/auto-reply/envelope.ts:190`

在 `formatAgentEnvelope` 基础上增加群组消息的发送者前缀：

- **群组消息**：在 body 前插入 `{senderName}: {body}`，然后调用 `formatAgentEnvelope`
- **直接消息**：直接调用 `formatAgentEnvelope`，body 不加前缀

```
// 群组：[Slack #general Thu Jan 15 10:30:00] Alice: hello
// 直接消息：[Slack Alice Thu Jan 15 10:30:00] hello
```

### 发送者标签解析 `resolveSenderLabel`

**文件**：`src/channels/sender-label.ts`

从 `{name, username, tag, e164, id}` 组合中生成最终显示名称：

- 优先级：`name > username > tag`（显示部分）
- ID 部分：`e164 > id`
- 若 display 与 id 均存在且不同：`{display} ({id})`

---

## 各 Channel 的消息处理详情

### Slack

**文件**：`src/slack/monitor/message-handler/prepare.ts`

1. **接收**：`SlackMessageEvent`（含 `text`、`user`、`channel`、`ts`、`files` 等字段）
2. **解析发送者**：调用 `ctx.resolveUserName(userId)` 从 Slack API 获取 display name / real name
3. **构造 `rawBody`**：`message.text + attachmentContent?.text + mediaPlaceholder`
4. **追加消息 ID**：
   ```
   rawBody + "\n[slack message id: {ts} channel: {channelId} thread_ts: {thread_ts}?]"
   ```
5. **构造 envelope（Body）**：
   ```
   [Slack {#channelName or senderName} {+elapsed}? {timestamp}?] {senderName}: {rawBodyWithId}
   ```
6. **MsgContext 关键赋值**：
   - `Body` = 完整 envelope（含历史拼接）
   - `BodyForAgent` = 原始 `rawBody`（不含 ID 后缀和 envelope）
   - `GroupSubject` = `#channelName`
   - `ChatType` = "direct"（私信）/ "channel"（频道）
   - `Surface` = "slack"

**线程处理**：
若消息是线程回复（`isThreadReply`），会额外获取线程首条消息（`threadStarterBody`）及线程历史（`threadHistoryBody`），并设置 `IsFirstThreadTurn` 标记。

### Telegram

**文件**：`src/telegram/bot-message-context.ts`

1. **接收**：Grammy bot 的 `message` 对象
2. **解析文本**：`expandTextLinks(msg.text, entities)` 展开链接文本
3. **处理 sticker**：若有缓存描述则替换为 `[Sticker {emoji} from "{setName}"] {description}`
4. **处理位置**：`formatLocationText(locationData)` 追加到 body
5. **处理回复/转发**：
   - 回复：`\n\n[Replying to {sender} id:{id}]\n{body}\n[/Replying]`（或 `[Quoting...]`）
   - 转发：`[Forwarded from {origin} at {isoTime}]\n{body}`
6. **构造 envelope（Body）**：
   ```
   [Telegram {groupLabel or senderName} {timestamp}?] {senderName}: {forwardPrefix}{bodyText}{replySuffix}
   ```
7. **MsgContext 关键赋值**：
   - `Body` = 完整 envelope
   - `BodyForAgent` = `bodyText`（纯净文本，含展开链接和位置，不含 envelope）
   - `GroupSubject` = 群组标题
   - `IsForum` = 是否是论坛型超级群组
   - `Surface` = "telegram"

**群组历史**：
若 `historyLimit > 0`，会将之前的消息拼接在 `combinedBody` 前（每条用独立 envelope 格式化）。

### Discord

**文件**：`src/discord/monitor/message-handler.process.ts`

1. **接收**：Discord Message 对象（含 guild/channel/member 信息）
2. **解析文本**：`resolveDiscordMessageText(message, {includeForwarded: true/false})`
3. **解析发送者**：
   - 普通用户：`author.username` + member displayname
   - PluralKit 代理：使用 PluralKit API 获取成员名称和 tag
4. **群组标签**：`buildGuildLabel()` 和 `buildDirectLabel()`
5. **线程处理**：若在线程中，获取父频道信息，构造 `threadLabel`
6. **构造 envelope（Body）**：
   ```
   [Discord {#channelName or @username} {timestamp}?] {senderLabel}: {text}
   ```
7. **MsgContext 关键赋值**：
   - `GroupChannel` = `#channelName`（频道名）
   - `GroupSpace` = guild ID 或 slug
   - `SenderTag` = Discord tag（如 "username#1234"）
   - `Surface` = "discord"

**自动线程**：
Discord 支持 `autoThread` 配置，会自动为每个用户消息创建子线程，此时 `From` 和路由目标会重写为子线程。

### Signal

**文件**：`src/signal/monitor/event-handler.ts`

1. **接收**：Signal RPC 的消息事件（含 envelope、dataMessage 等）
2. **构造 envelope（Body）**：
   ```
   [Signal {groupName or senderDisplay} {timestamp}?] {senderName}: {bodyText}
   ```
3. **MsgContext 关键赋值**：
   - `GroupSubject` = 群组名称
   - `SenderId` = sender UUID 或 E164
   - `Surface` = "signal"

### iMessage

**文件**：`src/imessage/monitor/inbound-processing.ts`

1. **接收**：BlueBubbles API 的通知（含 `chat_name`、`participants` 等）
2. **处理回复**：提取 `replyContext.body` 和 `replyContext.sender`
3. **构造 envelope（Body）**：
   ```
   [iMessage {groupName or senderName} {timestamp}?] {senderName}: {bodyText}{replySuffix}
   ```
4. **MsgContext 关键赋值**：
   - `GroupMembers` = 群组成员列表（逗号分隔）
   - `GroupSubject` = `chat_name`
   - `Surface` = "imessage"

### WhatsApp / Line / Matrix 等扩展 channel

这些 channel 通过插件扩展机制实现（`extensions/` 目录），核心接口相同：
- 通过 plugin-sdk 的 `ChannelPlugin` 接口注册
- 在运行时通过 gateway 接收消息
- 消息处理由各自的 runtime 实现，最终也构造 `MsgContext` 并调用相同的分发管道

---

## 消息分发管道

### 第一阶段：finalizeInboundContext

**文件**：`src/auto-reply/reply/inbound-context.ts`

对 `MsgContext` 进行标准化：
1. 规范化换行符（`\r\n` → `\n`）
2. 确定 `BodyForAgent`：优先使用显式设置值，否则按优先级降级：`CommandBody → RawBody → Body`
3. 自动补全 `ConversationLabel`（若未显式设置）
4. 规范化 media type 字段
5. 将 `CommandAuthorized` 默认设为 false（安全默认）

### 第二阶段：get-reply-directives（指令处理）

**文件**：`src/auto-reply/reply/get-reply-directives.ts`

```
promptSource = sessionCtx.BodyForAgent ?? sessionCtx.BodyStripped ?? sessionCtx.Body
```

从 prompt 中提取并剥离内联指令（如 `/think:`、`/verbose:`、`/model:`），处理完后将 `BodyForAgent`、`Body`、`BodyStripped` 均更新为指令剥离后的干净文本。

### 第三阶段：get-reply-run（构造最终 agent prompt）

**文件**：`src/auto-reply/reply/get-reply-run.ts`

```typescript
baseBody = sessionCtx.BodyStripped ?? sessionCtx.Body  // 通常为 BodyForAgent（干净文本）
inboundUserContext = buildInboundUserContextPrefix(sessionCtx)
baseBodyForPrompt = [inboundUserContext, baseBody].join("\n\n")
```

最终发送给 agent 的内容结构：

**System prompt 追加**（可信元数据，`buildInboundMetaSystemPrompt`）：
```
## Inbound Context (trusted metadata)
```json
{
  "schema": "openclaw.inbound_meta.v1",
  "message_id": "12345",
  "sender_id": "U123ABC",
  "chat_id": "channel:C456",
  "channel": "slack",
  "surface": "slack",
  "chat_type": "channel",
  "flags": { "is_group_chat": true, "was_mentioned": true, "history_count": 3 }
}
```

**User prompt**（`buildInboundUserContextPrefix` + 干净文本）：
```
Conversation info (untrusted metadata):
```json
{ "conversation_label": "#general", "group_subject": "#general", "was_mentioned": true }
```

Sender (untrusted metadata):
```json
{ "label": "Alice", "name": "Alice" }
```

Chat history since last reply (untrusted, for context):
```json
[
  { "sender": "Bob", "timestamp_ms": 1705320000000, "body": "有人在吗" },
  { "sender": "Alice", "timestamp_ms": 1705320060000, "body": "在的" }
]
```

hello
```

---

## Body vs BodyForAgent 的双轨机制

这是理解 OpenClaw 消息格式的关键：

| 字段 | 内容 | 用途 |
|------|------|------|
| `Body` | `[Slack #general Alice Thu Jan 15 10:30:00] Alice: hello\n[slack message id: 12345 channel: C123]` | 模板变量 `{{Body}}`；遗留 fallback；部分子系统 |
| `BodyForAgent` | `hello` | 最终传递给 agent 的干净文本 |
| `RawBody` / `CommandBody` | `hello` | 指令检测和解析 |

**为什么要分开？**
`Body`（envelope 格式）是早期设计遗留，它将所有元数据（channel、发送者、时间戳）混入消息文本。现代设计（`BodyForAgent` + 结构化 JSON 上下文）将元数据与用户内容分离：
- 可信元数据（message_id、sender_id）走 system prompt
- 不可信元数据（群名、发件人名称、历史消息）走 user prompt 中的结构化 JSON block
- 用户实际文本保持干净

这防止了 prompt injection 攻击（攻击者伪造 envelope header 或 message_id 标签）。

---

## 时间戳格式与时区

**文件**：`src/auto-reply/envelope.ts`、`src/infra/format-time/`

Envelope 中的时间戳格式可通过配置控制：

```yaml
agents:
  defaults:
    envelopeTimezone: "local"    # local（默认）| utc | user | Asia/Shanghai
    envelopeTimestamp: "on"      # on（默认）| off
    envelopeElapsed: "on"        # on（默认）| off
    userTimezone: "Asia/Shanghai" # 当 envelopeTimezone=user 时使用
```

时间戳格式示例：
- `local`：`Thu Jan 15 10:30:00 PST 2024`
- `utc`：`Thu Jan 15 18:30:00 UTC 2024`
- IANA：`Thu Jan 15 10:30:00 CST 2024`（Asia/Shanghai）

Elapsed（间隔时长）仅在有上一条消息时间戳时显示，例如 `+5m` 表示距上次回复 5 分钟。

---

## 群组历史（Pending History）

**文件**：`src/auto-reply/reply/history.ts`

在群组中，当 bot 未被 @mention 时，消息会被缓存到内存 map（`groupHistories`）。当 bot 被提及时，之前缓存的消息会通过两种方式提供给 agent：

1. **结构化方式**（现代）：`InboundHistory` 字段 → `buildInboundUserContextPrefix` 中的 JSON block
2. **Envelope 方式**（遗留）：将每条历史用 `formatInboundEnvelope` 格式化后拼接到 `combinedBody` 前

每条历史消息的 envelope 格式：
```
[Slack #general {timestamp}] {senderName}: {body} [id:{messageId} channel:{channelId}]
```

---

## 会话标识

**文件**：`src/routing/session-key.ts`、`src/routing/resolve-route.ts`

每条消息关联到一个 sessionKey，格式如：
- Slack DM：`slack:U123ABC`
- Slack 频道：`slack:channel:C456DEF`
- Slack 线程：`slack:channel:C456DEF:thread:1705320000.123456`
- Telegram 直接消息：`telegram:987654321`
- Telegram 群组：`telegram:group:-100123456789`
- Discord DM：`discord:user:123456789`
- Discord 频道：`discord:channel:987654321`

Session JSONL 文件（`<session-uuid>.jsonl`）存储于 `~/.openclaw/sessions/` 下，以 sessionKey 映射。

---

## 安全设计原则

1. **envelope header 不可信**：`[Slack #general Alex]` 等格式不作为受信任的系统指令
2. **可信/不可信分离**：message_id 等可信元数据走 system prompt，发送者名、群名走 user-role 的 JSON block
3. **Header 注入防护**：`sanitizeEnvelopeHeaderPart` 会移除换行符、转义方括号，防止构造伪造 envelope header
4. **命令权限分离**：`CommandAuthorized` 默认 false，需显式授权（基于 allowlist）才能执行控制命令

---

## 快速参考：各 Channel 的 envelope 格式

| Channel | DM 格式 | 群组格式 |
|---------|---------|---------|
| Slack | `[Slack {senderName} {ts}] {body}` | `[Slack #{channel} {ts}] {sender}: {body}\n[slack message id: ...]` |
| Telegram | `[Telegram {senderName} {ts}] {body}` | `[Telegram {groupName} {ts}] {sender}: {body}` |
| Discord | `[Discord {username} {ts}] {body}` | `[Discord #{channel} {ts}] {sender}: {body}` |
| Signal | `[Signal {senderDisplay} {ts}] {body}` | `[Signal {groupName} {ts}] {sender}: {body}` |
| iMessage | `[iMessage {senderName} {ts}] {body}` | `[iMessage {chatName} {ts}] {sender}: {body}` |
