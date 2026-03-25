# Plugin registerCommand 接口详解

`registerCommand` 是 Plugin API 中用于注册自定义斜杠命令的接口，注册后用户可在聊天中通过 `/命令名` 触发，命令处理完全在插件代码中执行，**不调用 AI 模型**。

---

## 一、接口签名

```typescript
api.registerCommand(command: OpenClawPluginCommandDefinition): void
```

### OpenClawPluginCommandDefinition

```typescript
type OpenClawPluginCommandDefinition = {
  name: string;          // 命令名（不含 /），如 "voice"、"phone"
  description: string;   // 说明文字，显示在 /help 和命令菜单中
  acceptsArgs?: boolean; // 是否接受参数，默认 false（见下方说明）
  requireAuth?: boolean; // 是否仅授权用户可用，默认 true
  handler: PluginCommandHandler;
};

type PluginCommandHandler = (ctx: PluginCommandContext) => PluginCommandResult | Promise<PluginCommandResult>;
```

---

## 二、命令名规则

- 必须以小写字母开头，只允许字母、数字、`-`、`_`
- 不区分大小写（`/Voice` 和 `/voice` 等价）
- **不能使用保留命令名**，以下均为保留名：

```
help, commands, status, whoami, context,
stop, restart, reset, new, compact,
config, debug, allowlist, activation,
skill, subagents, kill, steer, tell, model, models, queue,
send, bash, exec,
think, verbose, reasoning, elevated, usage
```

---

## 三、PluginCommandContext（handler 接收的上下文）

```typescript
type PluginCommandContext = {
  args?: string;               // 命令后面的参数字符串（已消毒，最长 4096 字节）
  commandBody: string;         // 完整命令原文（含 / 和参数）
  channel: string;             // 消息来源渠道名，如 "telegram"、"discord"、"whatsapp"
  channelId?: ChannelId;       // 渠道 ID（类型标识）
  senderId?: string;           // 发送者标识符
  from?: string;               // 渠道作用域的发送方 ID
  to?: string;                 // 渠道作用域的接收方 ID
  accountId?: string;          // 多账户渠道下的账户 ID
  messageThreadId?: number;    // 话题/线程 ID（Telegram 群组话题等）
  isAuthorizedSender: boolean; // 发送者是否在 allowlist 中
  config: OpenClawConfig;      // 当前全局配置
};
```

---

## 四、acceptsArgs 的行为细节

`acceptsArgs` 控制命令是否匹配带参数的输入：

| 用户输入 | `acceptsArgs: false`（默认） | `acceptsArgs: true` |
|---------|--------------------------|-------------------|
| `/voice` | ✅ 匹配，`ctx.args` 为 `undefined` | ✅ 匹配，`ctx.args` 为 `undefined` |
| `/voice status` | ❌ **不匹配**，消息传递给下一处理器或 AI | ✅ 匹配，`ctx.args` 为 `"status"` |

**关键**：`acceptsArgs: false` 时，带参数的输入会**落通**到 AI 代理处理，这是有意设计——允许命令名兼作普通对话触发词。

---

## 五、requireAuth 认证

```typescript
requireAuth?: boolean  // 默认 true
```

- `true`（默认）：仅 `ctx.isAuthorizedSender === true` 的用户可执行，否则返回 `"⚠️ This command requires authorization."`
- `false`：所有用户可执行，包括未授权用户

`isAuthorizedSender` 由 openclaw 的 allowlist 系统决定，不需要插件自行校验。

---

## 六、PluginCommandResult（返回值格式）

返回值类型为 `ReplyPayload`：

```typescript
type ReplyPayload = {
  text?: string;                          // 回复文本
  mediaUrl?: string;                      // 单个媒体 URL（图片/音频/视频）
  mediaUrls?: string[];                   // 多个媒体 URL
  audioAsVoice?: boolean;                 // true = 音频作为语音气泡发送（而非文件）
  replyToId?: string;                     // 回复特定消息 ID
  replyToCurrent?: boolean;               // 回复触发本命令的那条消息
  isError?: boolean;                      // 标记为错误响应
  channelData?: Record<string, unknown>;  // 渠道专属数据（如 LINE Flex Message）
};
```

**常用返回示例：**

```typescript
// 纯文字
return { text: "操作完成" };

// 错误提示
return { text: "参数错误，用法：/cmd <action>", isError: true };

// 带图片
return { text: "生成结果：", mediaUrl: "https://example.com/result.png" };

// 语音消息
return { mediaUrl: "file:///tmp/audio.mp3", audioAsVoice: true };

// LINE 富文本卡片
return {
  channelData: {
    line: { flexMessage: { altText: "卡片标题", contents: { type: "bubble", /* ... */ } } }
  }
};
```

---

## 七、命令处理优先级

插件命令在所有内置命令之前处理，处理管道顺序如下：

```
消息到达
    ↓
handlePluginCommand   ← 插件命令（最先匹配）
    ↓ 未匹配
handleBashCommand
handleActivationCommand
handleUsageCommand
handleHelpCommand
... 其他内置命令
    ↓ 全部未匹配
发送给 AI 代理
```

一旦插件命令匹配成功，返回结果后**立即终止**，不再调用 AI。

---

## 八、完整示例

### 最简示例

```typescript
export default (api) => {
  api.registerCommand({
    name: "ping",
    description: "测试连通性",
    handler: () => ({ text: "pong" }),
  });
};
```

### 带子命令的示例

```typescript
api.registerCommand({
  name: "note",
  description: "管理笔记：/note add <内容> | /note list | /note clear",
  acceptsArgs: true,
  handler: async (ctx) => {
    const tokens = (ctx.args ?? "").trim().split(/\s+/).filter(Boolean);
    const action = tokens[0]?.toLowerCase() ?? "list";

    switch (action) {
      case "add": {
        const content = tokens.slice(1).join(" ");
        if (!content) return { text: "用法：/note add <内容>" };
        await saveNote(content);
        return { text: `✅ 已保存：${content}` };
      }
      case "list": {
        const notes = await loadNotes();
        return { text: notes.length ? notes.join("\n") : "（暂无笔记）" };
      }
      case "clear": {
        await clearNotes();
        return { text: "✅ 已清空所有笔记" };
      }
      default:
        return { text: "未知操作，支持：add / list / clear" };
    }
  },
});
```

### 读取插件配置的示例

```typescript
api.registerCommand({
  name: "status",
  description: "查看插件运行状态",
  handler: (ctx) => {
    // api.pluginConfig 来自 plugins.entries.my-plugin.config
    const cfg = api.pluginConfig as { endpoint?: string } ?? {};
    return {
      text: [
        `渠道：${ctx.channel}`,
        `发送者：${ctx.senderId ?? "未知"}`,
        `授权状态：${ctx.isAuthorizedSender ? "✅" : "❌"}`,
        `API 端点：${cfg.endpoint ?? "（未配置）"}`,
      ].join("\n"),
    };
  },
});
```

### 渠道感知的示例

```typescript
api.registerCommand({
  name: "share",
  description: "分享内容（不同渠道格式不同）",
  acceptsArgs: true,
  handler: (ctx) => {
    const content = ctx.args ?? "";
    if (!content) return { text: "用法：/share <内容>" };

    // 针对不同渠道返回不同格式
    if (ctx.channel === "line") {
      return {
        channelData: {
          line: {
            flexMessage: {
              altText: content,
              contents: { type: "bubble", body: { type: "box", layout: "vertical",
                contents: [{ type: "text", text: content }] } },
            },
          },
        },
      };
    }

    // 其他渠道返回纯文本
    return { text: content };
  },
});
```

### 公开命令（无需授权）

```typescript
api.registerCommand({
  name: "about",
  description: "查看插件信息（所有人可用）",
  requireAuth: false,
  handler: () => ({
    text: "My Plugin v1.0.0 — 由 Acme Corp 开发",
  }),
});
```

---

## 九、registerCommand vs registerCli 对比

| 维度 | `registerCommand` | `registerCli` |
|-----|------------------|--------------|
| 触发方式 | 聊天中发送 `/命令名` | 终端执行 `openclaw 命令名` |
| 调用者 | 远程聊天用户 | 本地 CLI 用户 |
| handler 输入 | `PluginCommandContext`（含渠道、发送者信息） | Commander.js 程序对象 |
| 返回值 | `ReplyPayload`（发回聊天） | 直接打印到 stdout |
| 授权控制 | `requireAuth` + `isAuthorizedSender` | 本地执行，无额外认证 |
| 典型用途 | 聊天机器人命令、远程控制 | 开发调试、系统管理 |

---

## 十、注意事项

1. **命令名冲突**：注册重复命令名时，`registry.ts` 会记录 `error` 级别诊断并**跳过**注册，不会抛出异常，需检查启动日志。

2. **`acceptsArgs: false` 的落通行为**：用户输入 `/cmd arg` 时命令不匹配，消息会被送到 AI 处理，可能产生意外响应。如果命令确实不需要参数但想阻止落通，可设 `acceptsArgs: true` 并在 handler 中忽略 `ctx.args`。

3. **handler 异常处理**：`executePluginCommand` 会捕获 handler 抛出的所有异常，返回通用错误消息 `"⚠️ Command failed. Please try again later."`，内部错误细节不会暴露给用户。

4. **同步 handler**：handler 可以是同步函数（直接返回 `ReplyPayload`），也可以是 `async` 函数，两种均支持。

5. **args 安全**：`ctx.args` 已经过消毒（移除控制字符，最长 4096 字节），但 handler 内仍需对参数做业务层校验。
