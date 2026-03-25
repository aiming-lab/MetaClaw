# OpenClaw Plugin 与 Hook 系统

OpenClaw 提供三个层次的扩展接口，从轻量到重量依次为：

| 扩展类型 | 适用场景 | 接口复杂度 |
|---------|---------|----------|
| **Internal Hooks** | 响应命令/生命周期事件，执行副作用 | 低，写一个 TS 函数 |
| **Plugin System** | 注册新工具、命令、拦截 LLM 流程 | 中，导出模块对象 |
| **Webhook Hooks** | 外部 HTTP 请求触发 Agent 行为 | 低，配置文件驱动 |

---

## 一、Internal Hooks（内部事件 Hook）

### 1.1 概念

Hook 是响应特定事件自动执行的 TypeScript 函数，运行在 Gateway 进程内部。典型用途：
- `/new` 时自动保存会话摘要到 memory
- 每次命令记录审计日志
- Gateway 启动时执行初始化脚本

### 1.2 目录结构

Hook 自动从以下目录扫描（优先级从高到低）：

```
~/.openclaw/hooks/<hook-name>/     # 用户安装，跨 workspace 共享
<workspace>/hooks/<hook-name>/     # per-agent，最高优先级
<openclaw>/dist/hooks/bundled/     # 内置，随 openclaw 发布
```

每个 Hook 目录固定结构：

```
my-hook/
├── HOOK.md        # 元数据和文档（必须）
└── handler.ts     # 处理函数（必须，或 index.ts）
```

### 1.3 HOOK.md 格式

```markdown
---
name: my-hook
description: "Hook 的简短描述"
metadata:
  openclaw:
    emoji: "🎯"
    events: ["command:new", "command:reset"]   # 订阅的事件列表
    requires:
      bins: ["jq"]                             # 需要的系统命令
      env: ["MY_API_KEY"]                      # 需要的环境变量
      config: ["workspace.dir"]                # 需要的配置字段
      os: ["linux", "darwin"]                  # 支持的操作系统
    always: false                              # true = 无论是否 enabled 都执行
    install:
      - id: bundled
        kind: bundled
        label: "Bundled with OpenClaw"
---

# My Hook

详细说明...
```

### 1.4 支持的事件类型（完整列表）

**结论：`command` 通配符只能捕获 `/new`、`/reset`、`/stop` 三个命令，不存在 `command:compact` 等其他命令事件。**

Internal Hook 系统的事件根类型为 `"command" | "session" | "agent" | "gateway"`，目前实际触发的事件如下：

| 事件键（HOOK.md 中填写） | `event.type` | `event.action` | 触发条件 |
|------------------------|-------------|---------------|---------|
| `command:new` | `"command"` | `"new"` | 用户发送 `/new` |
| `command:reset` | `"command"` | `"reset"` | 用户发送 `/reset` |
| `command:stop` | `"command"` | `"stop"` | 用户发送 `/stop` |
| `command` | `"command"` | 以上任意 | 通配，捕获全部 command 事件 |
| `agent:bootstrap` | `"agent"` | `"bootstrap"` | Agent 启动、构建系统提示前 |
| `gateway:startup` | `"gateway"` | `"startup"` | Gateway 启动完成后（延迟 250ms） |
| `session` | `"session"` | — | 目前无实际触发点（预留） |

> `/compact`、`/clear`、`/help` 等其他斜杠命令**不触发** Internal Hook 事件，它们的扩展入口在 Plugin System 的 `registerCommand` 接口。

### 1.5 各事件的 event 对象格式

所有事件共享基础结构：

```typescript
interface InternalHookEvent {
  type: "command" | "session" | "agent" | "gateway";
  action: string;               // 具体动作名称
  sessionKey: string;           // 关联的 session key
  context: Record<string, unknown>;  // 事件专属上下文（见下方各事件说明）
  timestamp: Date;
  messages: string[];           // 向用户推送消息，直接 push 字符串即可
}
```

#### command:new / command:reset

```typescript
// event.context 字段：
{
  cfg: OpenClawConfig,               // 全局配置
  sessionEntry: SessionEntry,        // 新 session（reset 后的）
  previousSessionEntry: SessionEntry,// reset 前的旧 session（含 sessionFile 路径）
  commandSource: string,             // 触发来源，如 "telegram"、"gateway:sessions.reset"
  senderId: string | undefined,      // 消息发送者 ID
}
```

#### command:stop

```typescript
// event.context 字段：
{
  sessionEntry: SessionEntry | undefined,  // 被停止的 session
  sessionId: string | undefined,
  commandSource: string,                   // 触发来源通道名称
  senderId: string | undefined,
}
```

#### agent:bootstrap

```typescript
// event.context 字段：
{
  workspaceDir: string,                   // agent workspace 目录
  bootstrapFiles: WorkspaceBootstrapFile[], // 启动文件列表（可直接修改此数组以注入文件）
  cfg: OpenClawConfig | undefined,
  sessionKey: string | undefined,
  sessionId: string | undefined,
  agentId: string | undefined,
}
// 注意：handler 可直接向 bootstrapFiles 数组 push 新文件项来注入额外上下文
```

#### gateway:startup

```typescript
// event.context 字段：
{
  cfg: OpenClawConfig,       // 网关配置
  deps: CliDeps,             // CLI 依赖对象
  workspaceDir: string,      // 默认 workspace 目录
}
```

### 1.6 handler.ts 接口

```typescript
import type { HookHandler } from "../../src/hooks/hooks.js";

const handler: HookHandler = async (event) => {
  if (event.type !== "command" || event.action !== "new") return;

  const ctx = event.context;
  const prevSession = ctx.previousSessionEntry as { sessionFile?: string; sessionId?: string };

  // 读取上一个 session 的文件路径
  console.log("上一个 session 文件:", prevSession.sessionFile);

  // 向用户推送一条提示
  event.messages.push("✅ 已处理 /new 命令");
};

export default handler;
```

### 1.5 配置文件（config.json）

Hook 需要在配置中启用：

```jsonc
{
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "session-memory": {
          "enabled": true,
          "messages": 25    // hook 自定义配置字段（由 hook 自行读取）
        },
        "my-hook": {
          "enabled": true,
          "env": { "EXTRA_VAR": "value" }
        }
      }
    }
  }
}
```

### 1.6 CLI 管理命令

```bash
openclaw hooks list              # 列出所有已发现的 hook
openclaw hooks enable my-hook   # 启用
openclaw hooks disable my-hook  # 禁用
openclaw hooks info my-hook     # 查看详情（含 requirements 检查）
openclaw hooks check             # 检查所有 hook 的资格
```

### 1.7 内置 Hook 一览

| Hook | 事件 | 功能 |
|------|------|------|
| `session-memory` | `command:new` | 保存会话摘要到 `<workspace>/memory/YYYY-MM-DD-slug.md` |
| `command-logger` | `command` | 记录所有命令到 `~/.openclaw/logs/commands.log` |
| `bootstrap-extra-files` | `agent:bootstrap` | 注入额外文件到 bootstrap 上下文 |
| `boot-md` | `gateway:startup` | 启动时执行 `BOOT.md` |

### 1.8 Hook Pack（npm 包形式分发）

多个 Hook 可打包为 npm 包：

```jsonc
// package.json
{
  "name": "@acme/my-hooks",
  "version": "0.1.0",
  "openclaw": {
    "hooks": ["./hooks/session-logger", "./hooks/alert-hook"]
  }
}
```

安装：

```bash
openclaw hooks install @acme/my-hooks
openclaw hooks install ./path/to/local-hooks-pack
```

---

## 二、Plugin System（插件系统）

### 2.1 概念

Plugin 是 TypeScript 模块，通过 `OpenClawPluginApi` 注册扩展能力：
- 自定义 Agent **工具**（Tool）
- 自定义 **CLI 命令**
- 自定义 **Gateway HTTP 路由**
- 拦截 **LLM 请求/响应流程**（Plugin Hooks）
- 注册后台**服务**
- 注册新**通道**（Channel）

### 2.2 发现路径（优先级从高到低）

```
<workspace>/.openclaw/extensions/*.ts
<workspace>/.openclaw/extensions/*/index.ts
~/.openclaw/extensions/*.ts
~/.openclaw/extensions/*/index.ts
plugins.load.paths（配置文件指定的额外路径）
<openclaw>/extensions/*（内置，默认禁用）
```

每个插件目录需包含 `openclaw.plugin.json` 清单文件。

### 2.3 插件模块格式

插件导出一个对象或函数：

```typescript
// ~/.openclaw/extensions/my-plugin.ts
import type { OpenClawPluginDefinition } from "openclaw/plugins";

const plugin: OpenClawPluginDefinition = {
  id: "my-plugin",
  name: "My Plugin",
  version: "1.0.0",
  description: "示例插件",

  register: async (api) => {
    // 在此调用 api.registerXxx() 和 api.on() 注册扩展
  },
};

export default plugin;
```

或简写函数形式：

```typescript
export default async (api) => {
  api.registerTool(myTool);
};
```

### 2.4 OpenClawPluginApi 完整接口

```typescript
interface OpenClawPluginApi {
  id: string;
  name: string;
  config: OpenClawConfig;           // 全局配置
  pluginConfig?: Record<string, unknown>;  // 插件专属配置（来自 plugins.entries.my-plugin.config）
  runtime: PluginRuntime;
  logger: PluginLogger;             // { debug, info, warn, error }

  // --- 注册接口 ---
  registerTool(
    tool: AnyAgentTool | OpenClawPluginToolFactory,
    opts?: { name?: string; names?: string[]; optional?: boolean }
  ): void;

  registerHook(
    events: string | string[],      // 内部 hook 事件名
    handler: InternalHookHandler,
    opts?: { entry?: HookEntry; name?: string }
  ): void;

  registerHttpHandler(handler: (req, res) => Promise<boolean> | boolean): void;
  registerHttpRoute(params: { path: string; handler: (req, res) => void }): void;
  registerChannel(registration: ChannelPlugin): void;
  registerGatewayMethod(method: string, handler: GatewayRequestHandler): void;
  registerCli(registrar: (program: Command) => void, opts?: { commands?: string[] }): void;
  registerService(service: { id: string; start(ctx): void; stop?(ctx): void }): void;
  registerProvider(provider: ProviderPlugin): void;
  registerCommand(command: OpenClawPluginCommandDefinition): void;

  // --- Plugin Hook 接口（新式，推荐）---
  on<K extends PluginHookName>(
    hookName: K,
    handler: PluginHookHandlerMap[K],
    opts?: { priority?: number }   // priority 越高越先执行
  ): void;

  resolvePath(input: string): string;  // 解析相对于插件目录的路径
}
```

### 2.5 Plugin Hooks（20 个生命周期 Hook）

通过 `api.on(hookName, handler)` 注册，分三类执行模式。

---

#### 修改型（顺序执行，按 priority 从高到低，可返回修改结果）

**1. `before_model_resolve`** — LLM 调用前，模型解析阶段（此时 session 消息尚未准备）

```typescript
// event
{ prompt: string }
// ctx: PluginHookAgentContext
{ agentId?: string; sessionKey?: string; sessionId?: string; workspaceDir?: string; messageProvider?: string }
// 返回值（可选）
{ modelOverride?: string; providerOverride?: string }
```

**2. `before_prompt_build`** — 系统提示构建前（session 消息已准备好）

```typescript
// event
{ prompt: string; messages: unknown[] }  // messages 为本轮上下文消息快照
// ctx: PluginHookAgentContext
// 返回值（可选）
{ systemPrompt?: string; prependContext?: string }
```

**3. `before_agent_start`** — 兼容旧版，合并 1+2（新代码推荐分别使用上两个）

```typescript
// event
{ prompt: string; messages?: unknown[] }
// 返回值（可选）
{ modelOverride?: string; providerOverride?: string; systemPrompt?: string; prependContext?: string }
```

**4. `message_sending`** — 回复消息发出前（可修改内容或取消）

```typescript
// event
{ to: string; content: string; metadata?: Record<string, unknown> }
// ctx: PluginHookMessageContext
{ channelId: string; accountId?: string; conversationId?: string }
// 返回值（可选）
{ content?: string; cancel?: boolean }
```

**5. `before_tool_call`** — 工具调用前（可修改参数或阻止调用）

```typescript
// event
{ toolName: string; params: Record<string, unknown> }
// ctx: PluginHookToolContext
{ agentId?: string; sessionKey?: string; toolName: string }
// 返回值（可选）
{ params?: Record<string, unknown>; block?: boolean; blockReason?: string }
```

---

#### 同步型（**不能** async，阻塞执行，可修改将写入 JSONL 的消息）

**6. `tool_result_persist`** — toolResult 消息写入 session 前

```typescript
// event
{
  toolName?: string;
  toolCallId?: string;
  message: AgentMessage;    // 即将写入的 toolResult 消息对象
  isSynthetic?: boolean;    // 是否为 guard/repair 步骤合成的结果
}
// ctx: PluginHookToolResultPersistContext
{ agentId?: string; sessionKey?: string; toolName?: string; toolCallId?: string }
// 返回值（可选，同步）
{ message?: AgentMessage }  // 返回修改后的消息；不返回则写入原消息
```

**7. `before_message_write`** — 任意消息写入 JSONL 前（含 user/assistant/toolResult）

```typescript
// event
{ message: AgentMessage; sessionKey?: string; agentId?: string }
// ctx
{ agentId?: string; sessionKey?: string }
// 返回值（可选，同步）
{ block?: boolean; message?: AgentMessage }
// block: true 时该消息不写入文件
```

---

#### 观察型（异步并行，fire-and-forget，返回 void）

**8. `llm_input`** — LLM 请求发出前

```typescript
// event
{
  runId: string;
  sessionId: string;
  provider: string;           // e.g. "anthropic"
  model: string;              // e.g. "claude-opus-4-6"
  systemPrompt?: string;
  prompt: string;             // 用户本轮输入
  historyMessages: unknown[]; // 本轮发送给 LLM 的完整消息列表
  imagesCount: number;
}
// ctx: PluginHookAgentContext
```

**9. `llm_output`** — LLM 响应返回后

```typescript
// event
{
  runId: string;
  sessionId: string;
  provider: string;
  model: string;
  assistantTexts: string[];   // LLM 生成的所有文本段落
  lastAssistant?: unknown;    // 最后一条 assistant 消息对象
  usage?: {
    input?: number; output?: number;
    cacheRead?: number; cacheWrite?: number;
    total?: number;
  };
}
// ctx: PluginHookAgentContext
```

**10. `agent_end`** — Agent 本轮运行结束

```typescript
// event
{
  messages: unknown[];  // 完整消息快照
  success: boolean;
  error?: string;
  durationMs?: number;
}
// ctx: PluginHookAgentContext
```

**11. `before_compaction`** — 上下文压缩（/compact）触发前

```typescript
// event
{
  messageCount: number;     // 压缩前总消息数
  compactingCount?: number; // 实际送入压缩 LLM 的消息数（经 history-limit 截断后）
  tokenCount?: number;
  messages?: unknown[];
  sessionFile?: string;     // JSONL 文件路径，压缩前消息已落盘，可异步读取
}
// ctx: PluginHookAgentContext
```

**12. `after_compaction`** — 上下文压缩完成后

```typescript
// event
{
  messageCount: number;     // 压缩后消息数
  tokenCount?: number;
  compactedCount: number;   // 被压缩掉的消息数
  sessionFile?: string;     // 压缩前所有消息仍保留在磁盘，可异步读取
}
// ctx: PluginHookAgentContext
```

**13. `before_reset`** — `/new` 或 `/reset` 清空 session 前（fire-and-forget，不阻塞命令执行）

```typescript
// event
{
  sessionFile?: string;   // 旧 session 的 JSONL 文件路径
  messages?: unknown[];   // 旧 session 的消息
  reason?: string;        // "new" 或 "reset"
}
// ctx: PluginHookAgentContext
```

**14. `message_received`** — 外部消息到达时

```typescript
// event
{ from: string; content: string; timestamp?: number; metadata?: Record<string, unknown> }
// ctx: PluginHookMessageContext
{ channelId: string; accountId?: string; conversationId?: string }
```

**15. `message_sent`** — 回复消息发送成功或失败后

```typescript
// event
{ to: string; content: string; success: boolean; error?: string }
// ctx: PluginHookMessageContext
```

**16. `after_tool_call`** — 工具执行完毕后

```typescript
// event
{
  toolName: string;
  params: Record<string, unknown>;
  result?: unknown;     // 工具返回结果
  error?: string;       // 工具抛出的错误
  durationMs?: number;
}
// ctx: PluginHookToolContext
{ agentId?: string; sessionKey?: string; toolName: string }
```

**17. `session_start`** — Session 启动时

```typescript
// event
{ sessionId: string; resumedFrom?: string }  // resumedFrom: 从哪个旧 session 恢复
// ctx: PluginHookSessionContext
{ agentId?: string; sessionId: string }
```

**18. `session_end`** — Session 结束时

```typescript
// event
{ sessionId: string; messageCount: number; durationMs?: number }
// ctx: PluginHookSessionContext
```

**19. `gateway_start`** — Gateway 启动完成时

```typescript
// event
{ port: number }
// ctx: PluginHookGatewayContext
{ port?: number }
```

**20. `gateway_stop`** — Gateway 停止时

```typescript
// event
{ reason?: string }
// ctx: PluginHookGatewayContext
```

### 2.6 完整插件示例

```typescript
// ~/.openclaw/extensions/audit-plugin.ts
export default async (api) => {

  // 1. 拦截工具调用，记录审计日志
  api.on("before_tool_call", async (event, ctx) => {
    console.log(`[audit] tool=${event.toolName} session=${ctx.sessionKey}`);
    // 阻止危险操作示例：
    if (event.toolName === "bash" && String(event.params.command).includes("rm -rf")) {
      return { block: true, blockReason: "危险命令被审计插件拦截" };
    }
  });

  // 2. 动态切换模型
  api.on("before_model_resolve", async (event, ctx) => {
    if (event.prompt.startsWith("[fast]")) {
      return { modelOverride: "gpt-4o-mini" };
    }
  });

  // 3. 在系统提示中注入上下文
  api.on("before_prompt_build", async (event, ctx) => {
    const today = new Date().toISOString().split("T")[0];
    return { prependContext: `Today is ${today}.` };
  });

  // 4. 过滤发出的消息
  api.on("message_sending", async (event, ctx) => {
    if (event.content.includes("INTERNAL")) {
      return { cancel: true };
    }
  });

  // 5. 阻止某些消息写入 JSONL
  api.on("before_message_write", (event, ctx) => {
    // 同步执行，不能 async
    if (event.message.role === "toolResult" && /* 某条件 */ false) {
      return { block: true };
    }
  });

  // 6. 注册自定义工具
  api.registerTool({
    name: "audit_log",
    description: "写入审计日志",
    parameters: { type: "object", properties: { message: { type: "string" } } },
    execute: async (toolCallId, params) => {
      return { content: [{ type: "text", text: `Logged: ${params.message}` }], details: null };
    },
  });

  // 7. 注册内部 hook（响应命令事件）
  api.registerHook("command:new", async (event) => {
    event.messages.push("✨ 审计插件：新 session 开始");
  });
};
```

### 2.7 配置文件

```jsonc
{
  "plugins": {
    "enabled": true,
    "load": {
      "paths": ["/path/to/extra/plugins"]
    },
    "entries": {
      "my-plugin": {
        "enabled": true,
        "config": {
          "apiKey": "xxx",
          "logLevel": "debug"
        }
      }
    },
    "slots": {
      "memory": "memory-lancedb"   // 替换内置 memory 插件
    }
  }
}
```

### 2.8 CLI 管理命令

```bash
openclaw plugins list                           # 列出已加载插件
openclaw plugins install @openclaw/voice-call  # 安装官方插件（仅 npm registry）
openclaw plugins enable my-plugin              # 启用
openclaw plugins disable my-plugin             # 禁用
```

---

## 三、Webhook Hooks（外部 HTTP 触发）

### 3.1 概念

外部系统（GitHub、Gmail、自定义脚本等）通过 HTTP POST 请求触发 OpenClaw Agent。

### 3.2 配置文件

```jsonc
{
  "hooks": {
    "enabled": true,
    "path": "/hooks",              // HTTP 路径前缀，默认 /hooks
    "token": "my-secret-token",   // Bearer Token 认证
    "defaultSessionKey": "agent:main:main",
    "allowRequestSessionKey": true,
    "maxBodyBytes": 262144,        // 256KB
    "mappings": [
      {
        "id": "github-push",
        "match": {
          "path": "/hooks/github",    // 匹配请求路径
          "source": "github"          // 匹配来源标识
        },
        "action": "agent",            // "agent"=调用Agent | "wake"=唤醒Agent
        "agentId": "ops",
        "messageTemplate": "New push to {{repository.name}}: {{head_commit.message}}",
        "thinking": "low",
        "timeoutSeconds": 60
      },
      {
        "id": "custom-transform",
        "match": { "path": "/hooks/custom" },
        "action": "agent",
        "transform": {
          "module": "./transforms/custom.ts",   // 相对 workspace 路径
          "export": "default"
        }
      }
    ]
  }
}
```

### 3.3 Transform 函数

用于在 webhook payload 转换为 Agent 消息前做自定义处理：

```typescript
// workspace/transforms/custom.ts
export default async function transform(payload: unknown): Promise<{ message: string }> {
  const data = payload as Record<string, unknown>;
  return {
    message: `收到事件：${JSON.stringify(data)}`,
  };
}
```

---

## 四、三种扩展方式对比

| 特性 | Internal Hook | Plugin | Webhook Hook |
|-----|--------------|--------|-------------|
| 执行环境 | Gateway 进程内 | Gateway 进程内 | 外部 HTTP 触发 |
| 编写语言 | TypeScript | TypeScript | TypeScript（transform） |
| 注册方式 | 目录发现 | 目录发现 | 配置文件 |
| 拦截 LLM 流程 | ❌ | ✅ | ❌ |
| 修改工具调用 | ❌ | ✅ | ❌ |
| 自定义工具 | ❌ | ✅ | ❌ |
| 响应命令事件 | ✅ | ✅（`registerHook`） | ❌ |
| 响应外部请求 | ❌ | ✅（`registerHttpRoute`） | ✅ |
| 配置复杂度 | 低 | 中 | 低 |
