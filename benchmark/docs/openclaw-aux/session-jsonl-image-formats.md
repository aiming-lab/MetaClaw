# Session JSONL 图像消息格式完整参考

本文档基于 `@mariozechner/pi-ai` 的 TypeScript 类型定义和 openclaw 源码，列举 session JSONL 中所有可能出现的图像相关格式，供解析器开发参考。

---

## 一、JSONL 文件整体结构

每个 JSONL 文件由若干 JSON 行组成，每行一条 entry，第一行固定为文件头。

### 1.1 文件头（第一行）

```json
{"type":"session","version":3,"id":"my-session","timestamp":"2026-03-03T12:00:00.000Z","cwd":"/home/user/project"}
```

可选字段：
- `parentSession`：父会话文件路径（子会话分支时存在）

```json
{"type":"session","version":3,"id":"sub-session","timestamp":"...","cwd":"...","parentSession":"/path/to/parent.jsonl"}
```

### 1.2 消息 entry 的通用包装格式

**所有消息行**（无论什么 role）都被包装在以下结构中：

```json
{
  "type": "message",
  "id": "abc123",
  "parentId": "xyz789",
  "timestamp": "2026-03-03T12:00:01.000Z",
  "message": { <AgentMessage> }
}
```

| 字段 | 说明 |
|------|------|
| `type` | 固定为 `"message"` |
| `id` | entry 的唯一 ID（字符串，由 `generateId()` 生成） |
| `parentId` | 父 entry 的 ID，第一条为 `null` |
| `timestamp` | ISO 8601 字符串（注意：**非** Unix 毫秒数） |
| `message` | 实际消息对象，见下方各 role 格式 |

---

## 二、各 role 的完整类型定义

权威来源：`@mariozechner/pi-ai` `types.d.ts`

### 2.1 UserMessage

```typescript
interface UserMessage {
  role: "user";
  content: string | (TextContent | ImageContent)[];
  timestamp: number;  // Unix 毫秒数
}
```

**图像出现场景**：content 为数组，含一或多个 `ImageContent` block。

---

### 2.2 AssistantMessage

```typescript
interface AssistantMessage {
  role: "assistant";
  content: (TextContent | ThinkingContent | ToolCall)[];
  api: string;          // e.g. "openai-responses", "anthropic-messages", "google-generative-ai"
  provider: string;     // e.g. "openai", "anthropic", "google"
  model: string;        // e.g. "gpt-4o", "claude-opus-4-6"
  usage: Usage;
  stopReason: "stop" | "length" | "toolUse" | "error" | "aborted";
  errorMessage?: string;
  timestamp: number;
}
```

**关键**：AssistantMessage 的 content **不包含** `ImageContent`，图像不会出现在助手的直接输出中。

---

### 2.3 ToolResultMessage

```typescript
interface ToolResultMessage {
  role: "toolResult";
  toolCallId: string;   // 对应 ToolCall.id
  toolName: string;
  content: (TextContent | ImageContent)[];
  details?: any;
  isError: boolean;
  timestamp: number;
}
```

**图像出现场景**：工具（截图、图像生成等）返回图像时，content 数组中含 `ImageContent` block。

---

## 三、Content Block 类型定义（完整）

### TextContent

```typescript
interface TextContent {
  type: "text";
  text: string;
  textSignature?: string;  // 仅部分场景出现，可忽略
}
```

### ImageContent

```typescript
interface ImageContent {
  type: "image";
  data: string;      // base64 编码（标准 base64，不含 data URL 前缀）
  mimeType: string;  // "image/jpeg" | "image/png" | "image/gif" | "image/webp"
}
```

### ThinkingContent（仅出现在 AssistantMessage.content）

```typescript
interface ThinkingContent {
  type: "thinking";
  thinking: string;
  thinkingSignature?: string;  // 可能是 JSON 字符串、普通字符串或 undefined
}
```

### ToolCall（仅出现在 AssistantMessage.content）

```typescript
interface ToolCall {
  type: "toolCall";
  id: string;
  name: string;
  arguments: Record<string, any>;
  thoughtSignature?: string;
}
```

---

## 四、图像格式的所有特殊情况

### 4.1 标准图像 block（正常情况）

```json
{
  "type": "image",
  "data": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "mimeType": "image/jpeg"
}
```

### 4.2 已被压缩的图像

原始图像若超过以下限制，写入前会被自动压缩并**转换为 JPEG**：

| 限制 | 值 |
|------|----|
| 最大单边尺寸 | 2000px |
| 最大字节数 | 5MB（工具图像）/ 6MB（媒体理解） |

**因此**：读取到 `mimeType: "image/png"` 的图像，其 `data` 实际上可能已是 JPEG（mimeType 与实际数据不符）。
代码中有针对此情况的修正逻辑（`src/agents/tool-images.ts`），解析时应以 `data` 的 magic bytes 为准：

| Base64 前缀 | 实际格式 |
|-------------|---------|
| `/9j/` | `image/jpeg` |
| `iVBOR` | `image/png` |
| `R0lGOD` | `image/gif` |

### 4.3 图像处理失败后的替换 block

当 base64 验证失败或图像损坏时，`sanitizeContentBlocksImages()` 会将图像 block **替换为 text block**：

```json
{
  "type": "text",
  "text": "[session:history] omitted image payload: Base64 data contains invalid characters or malformed padding"
}
```

```json
{
  "type": "text",
  "text": "[tool:screenshot] omitted empty image payload"
}
```

格式规律：`[<label>] omitted image payload: <reason>` 或 `[<label>] omitted empty image payload`

### 4.4 `data` 字段的边缘情况

写入前经过 `validateAndNormalizeBase64()` 处理，理论上存入文件的 `data` 应为干净的标准 base64，但以下情况需注意：

| 情况 | 说明 |
|------|------|
| 含 `data:image/...;base64,` 前缀 | 理论上写入前会剥离，但历史数据或外部写入可能残留 |
| URL-safe base64（`-` 和 `_`） | 写入前会转换为标准 `+` 和 `/`，但需防御性处理 |
| 填充 `=` 不标准 | 验证失败会被替换为 text block，正常不应出现 |

---

## 五、完整 JSONL 示例

### 5.1 用户消息含图像（原生视觉路径）

```jsonl
{"type":"message","id":"m1","parentId":null,"timestamp":"2026-03-03T12:00:01.000Z","message":{"role":"user","content":[{"type":"text","text":"请分析这张截图"},{"type":"image","data":"iVBORw0KGgoAAAANS...","mimeType":"image/png"}],"timestamp":1740974401000}}
```

### 5.2 用户消息纯文本（媒体理解路径，图像已转为描述）

当走媒体理解路径时，图像本身不存入 JSONL，描述文字拼接在 text 中：

```jsonl
{"type":"message","id":"m1","parentId":null,"timestamp":"2026-03-03T12:00:01.000Z","message":{"role":"user","content":[{"type":"text","text":"请分析这张截图\n\n[Image: screenshot.png]\n图像内容：这是一张显示系统错误日志的截图，其中包含三条 ERROR 级别记录..."}],"timestamp":1740974401000}}
```

### 5.3 工具结果含图像

```jsonl
{"type":"message","id":"m3","parentId":"m2","timestamp":"2026-03-03T12:00:03.000Z","message":{"role":"toolResult","toolCallId":"call_abc123","toolName":"screenshot","content":[{"type":"text","text":"截图成功"},{"type":"image","data":"/9j/4AAQSkZJRg...","mimeType":"image/jpeg"}],"isError":false,"timestamp":1740974403000}}
```

### 5.4 助手消息（包含工具调用和 thinking）

```jsonl
{"type":"message","id":"m2","parentId":"m1","timestamp":"2026-03-03T12:00:02.000Z","message":{"role":"assistant","content":[{"type":"thinking","thinking":"需要截取屏幕来分析当前状态","thinkingSignature":"{\"id\":\"rs_abc\",\"type\":\"reasoning\"}"},{"type":"toolCall","id":"call_abc123","name":"screenshot","arguments":{"region":"full"}}],"api":"openai-responses","provider":"openai","model":"gpt-4o","usage":{"input":1200,"output":80,"cacheRead":0,"cacheWrite":0,"totalTokens":1280,"cost":{"input":0.003,"output":0.0008,"cacheRead":0,"cacheWrite":0,"total":0.0038}},"stopReason":"toolUse","timestamp":1740974402000}}
```

---

## 六、非消息 entry 类型（解析时需跳过）

JSONL 中还会出现以下非消息行，解析图像时应识别并跳过：

| `type` 值 | 说明 |
|-----------|------|
| `"session"` | 文件头（第一行） |
| `"thinking_level_change"` | thinking 级别切换 |
| `"model_change"` | 模型切换记录 |
| `"compaction"` | 上下文压缩记录 |
| `"branch_summary"` | 分支摘要 |
| `"custom"` | 扩展自定义数据（不参与 LLM 上下文） |
| `"custom_message"` | 扩展注入消息（**会**参与 LLM 上下文，content 可含 ImageContent） |
| `"label"` | 用户书签标记 |
| `"session_info"` | 会话元数据（如显示名） |

**`custom_message` 的 content 格式**（可能含图像）：

```typescript
interface CustomMessageEntry {
  type: "custom_message";
  customType: string;        // 扩展标识符
  content: string | (TextContent | ImageContent)[];
  details?: any;
  display: boolean;
}
```

---

## 七、解析器需处理的完整图像来源汇总

| 来源 | 出现位置 | 格式 |
|------|---------|------|
| 用户输入的本地图像 | `user.content[]` | `{type:"image", data, mimeType}` |
| 工具返回的图像（截图/生成等） | `toolResult.content[]` | `{type:"image", data, mimeType}` |
| `custom_message` 中的图像 | `custom_message.content[]` | `{type:"image", data, mimeType}` |
| 图像处理失败的降级结果 | 任意消息的 `content[]` | `{type:"text", text:"[...] omitted image payload: ..."}` |
| 媒体理解路径（图像转文字） | `user.content[0].text` 中拼接 | 纯文本，不含 `type:"image"` block |
