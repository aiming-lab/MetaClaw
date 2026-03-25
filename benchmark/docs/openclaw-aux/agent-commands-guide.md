# OpenClaw agent/agents 命令详解与外部项目配置指南

> 目标：在外部项目中批量创建和管理 agent，每个 agent 的所有内容集中在一个独立文件夹里（workspace + session + agentDir）。

---

## 一、核心路径体系

### 默认路径

| 用途           | 默认路径                                 | 说明                              |
| -------------- | ---------------------------------------- | --------------------------------- |
| 主配置文件     | `~/.openclaw/openclaw.json`              | JSON5 格式，支持注释              |
| State 根目录   | `~/.openclaw/`                           | 也可用 `OPENCLAW_STATE_DIR` 覆盖  |
| Workspace      | `~/.openclaw/workspace`                  | agent 的工作目录                  |
| Agent 状态目录 | `~/.openclaw/agents/<agentId>/agent/`    | 存 auth-profiles、model-catalog   |
| Sessions       | `~/.openclaw/agents/<agentId>/sessions/` | 会话历史，**自动按 agentId 隔离** |

### 环境变量

| 变量                   | 作用                                                                   |
| ---------------------- | ---------------------------------------------------------------------- |
| `OPENCLAW_CONFIG_PATH` | 覆盖配置文件路径                                                       |
| `OPENCLAW_STATE_DIR`   | 覆盖 state 根目录                                                      |
| `OPENCLAW_PROFILE`     | 若非 `"default"`，workspace 默认变为 `~/.openclaw/workspace-<profile>` |

---

## 二、`openclaw agents` 命令

### 2.1 子命令总览

```bash
# 列出所有已配置的 agent
openclaw agents list
openclaw agents list --bindings      # 同时显示路由规则
openclaw agents list --json          # JSON 输出

# 添加新 agent（交互式向导）
openclaw agents add work

# 添加新 agent（非交互式，适合脚本批量创建）
openclaw agents add myagent \
  --name "My Agent" \
  --workspace /path/to/workspace \
  --agentDir /path/to/agent-dir \
  --model "anthropic/claude-sonnet-4-6" \
  --bind "whatsapp:personal" \
  --non-interactive

# 设置 agent 身份
openclaw agents set-identity --agent main --name "OpenClaw" --emoji "🦞"
openclaw agents set-identity --workspace ~/.openclaw/workspace --from-identity  # 从 IDENTITY.md 读取
openclaw agents set-identity --agent main --avatar avatars/openclaw.png

# 删除 agent
openclaw agents delete work
```

### 2.2 `agents add` 参数说明

| 参数                       | 说明                                                   |
| -------------------------- | ------------------------------------------------------ |
| `<id>`                     | agent ID（位置参数，自动 normalize）                   |
| `--name <name>`            | 显示名称                                               |
| `--workspace <path>`       | workspace 路径（非交互模式必填）                       |
| `--agentDir <path>`        | agent 状态目录（默认 `~/.openclaw/agents/<id>/agent`） |
| `--model <provider/model>` | 模型标识                                               |
| `--bind <channel:account>` | 绑定规则，可多次使用                                   |
| `--non-interactive`        | 非交互模式（有 flag 时自动触发）                       |
| `--json`                   | JSON 输出                                              |

> **注意**：`main` 是保留 ID，不能作为新 agent 的 ID。

---

## 三、`openclaw agent` 命令（运行单轮）

```bash
# 基本用法
openclaw agent --agent <agentId> --message "你好"

# 指定 session
openclaw agent --agent ops --session-id 1234 --message "Summarize logs"

# 发送消息到指定号码并投递
openclaw agent --to +15555550123 --message "status update" --deliver

# 带 thinking 模式
openclaw agent --session-id 1234 --message "Summarize inbox" --thinking medium

# 带回复路由
openclaw agent --agent ops --message "Generate report" --deliver \
  --reply-channel slack --reply-to "#reports"
```

### 主要参数

| 参数                    | 说明                                     |
| ----------------------- | ---------------------------------------- |
| `--agent <id>`          | 目标 agent ID                            |
| `--message / -m <text>` | 输入消息                                 |
| `--to <E.164>`          | 手机号（通过 Gateway 发送）              |
| `--session-id <id>`     | 会话 ID                                  |
| `--thinking <level>`    | `off/minimal/low/medium/high/xhigh`      |
| `--verbose <level>`     | `off/on/full`                            |
| `--deliver`             | 投递结果到目标 channel                   |
| `--reply-channel <ch>`  | 回复 channel（如 slack）                 |
| `--reply-to <target>`   | 回复目标（如 "#reports"）                |
| `--local`               | 使用 embedded Pi agent（不经过 Gateway） |
| `--timeout <sec>`       | 超时秒数                                 |

---

## 四、配置文件格式（`openclaw.json`）

配置文件为 **JSON5** 格式（支持注释、尾逗号、单引号字符串）。

### 4.1 完整结构

```json5
{
  // agents 配置块
  agents: {
    // 全局 defaults，所有 agent 共享（可被 per-agent 覆盖）
    defaults: {
      workspace: "~/.openclaw/workspace",          // 默认 workspace
      model: { primary: "anthropic/claude-sonnet-4-6" },
      thinkingDefault: "off",                       // off/minimal/low/medium/high/xhigh
      verboseDefault: "off",                        // off/on/full
      timeoutSeconds: 600,
      bootstrapMaxChars: 20000,                     // 单文件注入上限
      bootstrapTotalMaxChars: 150000,               // 总注入上限
      skipBootstrap: false,                         // 跳过自动创建 bootstrap 文件
      maxConcurrent: 1,                             // 最大并发 agent 数
    },

    // agent 列表
    list: [
      {
        id: "home",
        default: true,            // 没有 binding 匹配时的 fallback agent
        name: "Home",
        workspace: "~/.openclaw/workspace-home",
        agentDir: "~/.openclaw/agents/home/agent",
        model: {
          primary: "anthropic/claude-sonnet-4-6",
          fallbacks: ["anthropic/claude-haiku-4-5"],
        },
        identity: {
          name: "Home Assistant",
          emoji: "🏠",
          theme: "cozy",
          avatar: "avatars/home.png",               // workspace-relative 路径、URL、data URI
        },
        skills: ["skill-a", "skill-b"],             // 技能白名单（omit = 全部，empty = 全禁）
        tools: {
          allow: ["read", "exec"],
          deny: ["write", "edit"],
        },
        sandbox: {
          mode: "off",                              // off/non-main/all
          scope: "agent",                           // session/agent/shared
          workspaceAccess: "rw",                    // none/ro/rw
          docker: {
            setupCommand: "apt-get install -y git",
          },
        },
        groupChat: {
          mentionPatterns: ["@home", "@HomeBot"],
        },
        subagents: {
          allowAgents: ["work"],                    // 可以 spawn 的子 agent
        },
        heartbeat: {
          every: "30m",
          target: "last",
        },
      },
      {
        id: "work",
        name: "Work",
        workspace: "~/.openclaw/workspace-work",
        agentDir: "~/.openclaw/agents/work/agent",
        model: "anthropic/claude-opus-4-6",         // 可以是字符串简写
      },
    ],
  },

  // 路由规则（最具体优先）
  bindings: [
    // 按 channel + account 路由
    { agentId: "home", match: { channel: "whatsapp", accountId: "personal" } },
    { agentId: "work", match: { channel: "whatsapp", accountId: "biz" } },

    // 按 DM 对端路由（精确到号码）
    {
      agentId: "work",
      match: {
        channel: "whatsapp",
        peer: { kind: "direct", id: "+15551234567" },
      },
    },

    // 按 WhatsApp 群组路由
    {
      agentId: "family",
      match: {
        channel: "whatsapp",
        peer: { kind: "group", id: "120363999999999999@g.us" },
      },
    },

    // 按 Slack workspace 路由
    { agentId: "work", match: { channel: "slack", teamId: "T12345" } },

    // 按 Discord guild + roles 路由
    {
      agentId: "admin",
      match: {
        channel: "discord",
        guildId: "123456789",
        roles: ["role-id-1"],
      },
    },

    // 整个 channel 路由（兜底）
    { agentId: "work", match: { channel: "telegram" } },
  ],
}
```

### 4.2 路由优先级（从高到低）

1. `peer` 精确匹配（DM/群组/channel ID）
2. `parentPeer` 匹配（线程继承）
3. `guildId + roles`（Discord 角色路由）
4. `guildId`（Discord guild 路由）
5. `teamId`（Slack workspace 路由）
6. `accountId` 匹配
7. channel 级兜底（`accountId: "*"` 或只有 `channel`）
8. 默认 agent（`default: true` → 列表第一个 → `main`）

多个 match 字段是 **AND** 语义（全部满足才匹配）。

---

## 五、针对"外部项目批量管理 agent"的方案

### 5.1 目录结构设计

将每个 agent 的所有内容集中在一个外部目录里：

```
/path/to/my-agents-project/
├── agents/
│   ├── agent-alpha/
│   │   ├── workspace/          # 该 agent 的 workspace（AGENTS.md、SOUL.md 等）
│   │   │   ├── AGENTS.md
│   │   │   ├── SOUL.md
│   │   │   ├── USER.md
│   │   │   ├── IDENTITY.md
│   │   │   └── memory/
│   │   └── agent-state/        # 该 agent 的 agentDir（auth、model catalog）
│   │       ├── auth-profiles.json
│   │       └── model-catalog.json
│   ├── agent-beta/
│   │   ├── workspace/
│   │   └── agent-state/
│   └── ...
├── openclaw.json               # 主配置文件（可通过 OPENCLAW_CONFIG_PATH 指定）
└── scripts/
    └── setup-agents.sh         # 批量注册脚本
```

> **Session 存储**：session 数据目前固定在 `~/.openclaw/agents/<agentId>/sessions/`，
> **无法**通过配置文件直接改变路径。如需迁移，只能手动复制。

### 5.2 `openclaw.json` 配置示例（引用外部路径）

```json5
{
  agents: {
    defaults: {
      thinkingDefault: "off",
      timeoutSeconds: 600,
      skipBootstrap: true,    // workspace 文件已手动准备，跳过自动生成
    },
    list: [
      {
        id: "alpha",
        name: "Agent Alpha",
        workspace: "/path/to/my-agents-project/agents/agent-alpha/workspace",
        agentDir: "/path/to/my-agents-project/agents/agent-alpha/agent-state",
      },
      {
        id: "beta",
        name: "Agent Beta",
        workspace: "/path/to/my-agents-project/agents/agent-beta/workspace",
        agentDir: "/path/to/my-agents-project/agents/agent-beta/agent-state",
      },
    ],
  },
}
```

使用 `OPENCLAW_CONFIG_PATH` 让 openclaw 使用外部配置：

```bash
export OPENCLAW_CONFIG_PATH=/path/to/my-agents-project/openclaw.json
openclaw agents list
```

### 5.3 批量创建 agent 脚本示例

```bash
#!/bin/bash
# setup-agents.sh
export OPENCLAW_CONFIG_PATH=/path/to/my-agents-project/openclaw.json

AGENTS_ROOT="/path/to/my-agents-project/agents"

# 定义 agent 列表
AGENTS=("alpha" "beta" "gamma")

for AGENT_ID in "${AGENTS[@]}"; do
  WORKSPACE="$AGENTS_ROOT/$AGENT_ID/workspace"
  AGENT_DIR="$AGENTS_ROOT/$AGENT_ID/agent-state"

  # 创建目录结构
  mkdir -p "$WORKSPACE/memory"
  mkdir -p "$AGENT_DIR"

  # 创建 workspace 文件（可按需自定义）
  cat > "$WORKSPACE/AGENTS.md" << EOF
# Agent $AGENT_ID 的操作规则
...
EOF

  cat > "$WORKSPACE/IDENTITY.md" << EOF
# identity
name: $AGENT_ID
emoji: 🤖
EOF

  # 注册到 openclaw 配置
  openclaw agents add "$AGENT_ID" \
    --name "$AGENT_ID" \
    --workspace "$WORKSPACE" \
    --agentDir "$AGENT_DIR" \
    --non-interactive
done
```

### 5.4 关键注意事项

1. **`agentDir` 不能复用**：每个 agent 必须有独立的 `agentDir`，否则会导致 auth/session 冲突。

2. **Sessions 路径固定**：session 历史存储在 `~/.openclaw/agents/<agentId>/sessions/`，这个路径**不可配置**，只能通过 `OPENCLAW_STATE_DIR` 统一移动 state 根目录。

3. **如需完全外置 sessions**，可以设置：
   ```bash
   export OPENCLAW_STATE_DIR=/path/to/my-agents-project/.openclaw-state
   ```
   这样所有 agent 的 sessions 会存在 `/path/to/my-agents-project/.openclaw-state/agents/<agentId>/sessions/`。

4. **`skipBootstrap: true`**：若 workspace 文件已预先准备好，设置此项防止 openclaw 自动覆盖。

5. **身份文件（IDENTITY.md）**：设置好 workspace 后，可用 `openclaw agents set-identity --workspace <path> --from-identity` 自动读取并更新配置。

---

## 六、Workspace 文件说明

每个 agent 的 workspace 包含以下标准文件（均为 Markdown，每次会话开始时注入）：

| 文件                   | 必须   | 用途                                       |
| ---------------------- | ------ | ------------------------------------------ |
| `AGENTS.md`            | 推荐   | 操作规则、记忆指导、行为规范               |
| `SOUL.md`              | 推荐   | 人格、语调、边界                           |
| `USER.md`              | 推荐   | 用户信息和称谓方式                         |
| `IDENTITY.md`          | 推荐   | agent 名称、emoji、theme、avatar           |
| `TOOLS.md`             | 可选   | 本地工具说明（仅参考，不控制权限）         |
| `HEARTBEAT.md`         | 可选   | 心跳运行检查清单（保持简短）               |
| `BOOT.md`              | 可选   | Gateway 重启时的启动检查清单               |
| `BOOTSTRAP.md`         | 一次性 | 首次运行仪式（完成后删除）                 |
| `MEMORY.md`            | 可选   | 精选长期记忆                               |
| `memory/YYYY-MM-DD.md` | 自动   | 每日记忆日志                               |
| `skills/`              | 可选   | workspace 专属技能（覆盖同名 shared 技能） |

**注入上限**：单文件 20000 chars（`bootstrapMaxChars`），全部文件合计 150000 chars（`bootstrapTotalMaxChars`）。

---

## 七、常用命令速查

```bash
# 查看所有 agent 及其路由
openclaw agents list --bindings

# 手动运行某个 agent 一次
openclaw agent --agent alpha --message "hello"

# 查看 agent 配置（配置文件中的内容）
OPENCLAW_CONFIG_PATH=./openclaw.json openclaw agents list --json

# 用 IDENTITY.md 同步身份
openclaw agents set-identity --workspace ./agents/alpha/workspace --from-identity

# 删除 agent（只删配置，不删文件）
openclaw agents delete alpha
```

---

## 八、源码关键文件索引

| 文件                                   | 用途                                   |
| -------------------------------------- | -------------------------------------- |
| `src/commands/agent.ts`                | `openclaw agent` 命令实现              |
| `src/commands/agents.commands.add.ts`  | `openclaw agents add` 实现             |
| `src/commands/agents.commands.list.ts` | `openclaw agents list` 实现            |
| `src/commands/agents.config.ts`        | agent 配置增删改查                     |
| `src/commands/agents.bindings.ts`      | binding 路由处理                       |
| `src/config/types.agents.ts`           | `AgentConfig`、`AgentBinding` 类型定义 |
| `src/config/types.agent-defaults.ts`   | `AgentDefaultsConfig` 完整类型         |
| `src/config/types.openclaw.ts`         | `OpenClawConfig` 顶层类型              |
| `src/agents/agent-scope.ts`            | agent 配置解析工具函数                 |
| `docs/concepts/multi-agent.md`         | 多 agent 路由概念文档                  |
| `docs/concepts/agent-workspace.md`     | workspace 文件结构文档                 |
