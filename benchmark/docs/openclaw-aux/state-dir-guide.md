# OpenClaw State 根目录详解：结构、文件格式与自定义指南

> 目标：完全控制 state 根目录位置，实现外部项目的完整自托管和隔离管理。

---

## 一、State 根目录概述

OpenClaw 的"state 根目录"存放所有**运行时可变数据**：

- 主配置文件（`openclaw.json`）
- OAuth / API Key 凭证（`credentials/`）
- 每个 agent 的认证、模型注册表（`agents/<id>/agent/`）
- 会话历史（`agents/<id>/sessions/`）
- 沙箱工作区（`sandboxes/`，可选）

注意：workspace 文件（AGENTS.md 等）**不在** state 根目录里，workspace 是独立的、可自由指定路径的目录。

---

## 二、控制 State 根目录的环境变量

### 2.1 完整环境变量清单

| 变量                   | 优先级         | 说明                                                                     | 示例值                      |
| ---------------------- | -------------- | ------------------------------------------------------------------------ | --------------------------- |
| `OPENCLAW_STATE_DIR`   | **最高**       | 覆盖整个 state 根目录                                                    | `/my/project/.state`        |
| `CLAWDBOT_STATE_DIR`   | 等同于上       | 历史别名，已废弃但仍支持                                                 | —                           |
| `OPENCLAW_CONFIG_PATH` | 独立           | 单独指定配置文件路径（不受 STATE_DIR 影响）                              | `/my/project/openclaw.json` |
| `CLAWDBOT_CONFIG_PATH` | 等同于上       | 历史别名                                                                 | —                           |
| `OPENCLAW_OAUTH_DIR`   | 独立           | 单独指定 OAuth 凭证目录（覆盖 `<stateDir>/credentials`）                 | `/my/project/creds`         |
| `OPENCLAW_AGENT_DIR`   | 独立           | 覆盖**主 agent**（main）的 agentDir（单 agent 模式）                     | `/my/project/agent-state`   |
| `PI_CODING_AGENT_DIR`  | 等同于上       | 同 `OPENCLAW_AGENT_DIR`，旧名称，仍支持                                  | —                           |
| `OPENCLAW_PROFILE`     | 影响 workspace | 非 `"default"` 时，默认 workspace 变为 `~/.openclaw/workspace-<profile>` | `"work"`                    |

### 2.2 变量优先级与生效逻辑

```
配置文件路径解析：
  OPENCLAW_CONFIG_PATH（如有）
  → <OPENCLAW_STATE_DIR>/openclaw.json（如有）
  → ~/.openclaw/openclaw.json（默认）

OAuth 目录解析：
  OPENCLAW_OAUTH_DIR（如有）
  → <stateDir>/credentials（默认）

主 agent 状态目录解析（agent-paths.ts）：
  OPENCLAW_AGENT_DIR / PI_CODING_AGENT_DIR（如有）
  → <stateDir>/agents/main/agent（默认）
```

---

## 三、State 根目录完整结构

```
<stateDir>/                                 ← OPENCLAW_STATE_DIR 指向这里
│
├── openclaw.json                           # 主配置文件（JSON5）★ 必须
│
├── credentials/                            # OAuth 凭证目录（也可用 OPENCLAW_OAUTH_DIR 覆盖）
│   └── oauth.json                          # 历史 OAuth 凭证（已基本迁移到 auth-profiles.json）
│
├── agents/                                 # 所有 agent 的状态目录
│   ├── main/                               # 默认 agent（id="main"）
│   │   ├── agent/                          # agentDir（认证、模型注册表）
│   │   │   ├── auth-profiles.json          # ★ 认证配置（API Key / OAuth）
│   │   │   └── model-catalog.json          # 模型注册表（自动生成）
│   │   └── sessions/                       # 会话存储
│   │       ├── sessions.json               # 会话索引（所有 session 元数据）
│   │       ├── <sessionId>.jsonl           # 单个会话的对话记录
│   │       └── <sessionId>-topic-<n>.jsonl # 带 topic 的会话记录
│   │
│   ├── work/                               # 自定义 agent（id="work"）
│   │   ├── agent/
│   │   │   └── auth-profiles.json
│   │   └── sessions/
│   │       ├── sessions.json
│   │       └── *.jsonl
│   │
│   └── <agentId>/                          # 每个 agent 对应一个子目录
│       └── ...
│
├── workspace                               # 默认 workspace（可选，如果 agents.defaults.workspace 未设置）
├── workspace-work                          # 未在配置文件中明确设置 workspace 时的自动 fallback
├── workspace-<agentId>                     # 按 agentId 命名的自动 fallback workspace
│
├── skills/                                 # 全局共享技能（由 openclaw 管理）
│   └── <skill-name>/
│       └── ...
│
└── sandboxes/                              # 沙箱工作区（sandbox 模式下自动创建）
    └── <agentId>-<sessionId>/
        └── ...
```

### 注意：workspace 和 state 的关系

- **workspace** 是 agent 的"工作目录"，存放 AGENTS.md、SOUL.md 等引导文件
- **state 根目录**存放运行时数据（凭证、会话、模型注册表）
- 两者是**完全独立**的目录，分开设置，分开备份
- workspace 默认在 `<stateDir>/workspace`，但**强烈建议**在配置文件里明确设置为外部路径

---

## 四、关键文件格式规范

### 4.1 `auth-profiles.json`（★ 最重要）

**路径**：`<stateDir>/agents/<agentId>/agent/auth-profiles.json`

**用途**：存储该 agent 的所有 API 认证信息，也是跨平台共享凭证的核心文件。

**格式**：

```json
{
  "version": 1,
  "profiles": {
    "<provider>:<profileId>": {
      "type": "api_key" | "oauth" | "token",
      "provider": "<provider>",
      ...
    }
  },
  "order": {
    "<provider>": ["<profileId1>", "<profileId2>"]
  },
  "lastGood": {
    "<provider>": "<profileId>"
  },
  "usageStats": {
    "<provider>:<profileId>": {
      "lastUsed": 1704000000000,
      "cooldownUntil": null,
      "disabledUntil": null,
      "errorCount": 0
    }
  }
}
```

**三种凭证类型详解**：

#### `type: "api_key"` — API Key 认证

```json
{
  "version": 1,
  "profiles": {
    "anthropic:default": {
      "type": "api_key",
      "provider": "anthropic",
      "key": "sk-ant-api03-xxxxxx",
      "email": "user@example.com"
    },
    "openai:default": {
      "type": "api_key",
      "provider": "openai",
      "key": "sk-proj-xxxxxx"
    },
    "anthropic:work-account": {
      "type": "api_key",
      "provider": "anthropic",
      "key": "sk-ant-api03-yyyyyy",
      "email": "work@company.com"
    }
  }
}
```

- `key`：API Key 字符串
- `email`：可选，账号邮箱（用于显示）
- `metadata`：可选，`Record<string, string>`，provider 特定元数据

#### `type: "token"` — 静态 Bearer Token

```json
{
  "version": 1,
  "profiles": {
    "huggingface:default": {
      "type": "token",
      "provider": "huggingface",
      "token": "hf_xxxxxxxxxxxxxxxxxxxxxx",
      "expires": 1735689600000
    }
  }
}
```

- `token`：Bearer Token 字符串
- `expires`：可选，过期时间（毫秒时间戳，无法自动续期）

#### `type: "oauth"` — OAuth 凭证

```json
{
  "version": 1,
  "profiles": {
    "anthropic:claude-cli": {
      "type": "oauth",
      "provider": "anthropic",
      "clientId": "xxxxxx",
      "access": "oauth-access-token",
      "refresh": "oauth-refresh-token",
      "expires": 1704086400000,
      "email": "user@example.com",
      "accountId": "acc_xxx",
      "projectId": "proj_xxx"
    }
  }
}
```

- `access`：访问令牌（自动刷新）
- `refresh`：刷新令牌
- `expires`：访问令牌过期时间（ms）
- `clientId`：可选，OAuth client ID
- `enterpriseUrl`：可选，企业 URL
- `projectId`：可选，项目 ID
- `accountId`：可选，账号 ID

**预定义的 profileId 常量**（来自源码）：

| Profile ID               | 用途                            |
| ------------------------ | ------------------------------- |
| `anthropic:claude-cli`   | 从 Claude CLI 同步的 OAuth 凭证 |
| `openai-codex:codex-cli` | 从 Codex CLI 同步的凭证         |
| `anthropic:default`      | 默认 Anthropic API Key          |

**轮询顺序控制（`order` 字段）**：

```json
{
  "version": 1,
  "profiles": {
    "anthropic:key1": { "type": "api_key", "provider": "anthropic", "key": "sk-ant-1" },
    "anthropic:key2": { "type": "api_key", "provider": "anthropic", "key": "sk-ant-2" }
  },
  "order": {
    "anthropic": ["anthropic:key1", "anthropic:key2"]
  }
}
```

若 `order` 不设置，则按 profiles 键的默认顺序轮询。

---

### 4.2 `sessions.json`（会话索引）

**路径**：`<stateDir>/agents/<agentId>/sessions/sessions.json`

**用途**：记录该 agent 所有会话的元数据（最后更新时间、token 用量、会话文件路径等）。

**格式**：

```json
{
  "version": 1,
  "sessions": {
    "agent:main:+15551234567": {
      "sessionId": "550e8400-e29b-41d4-a716-446655440000",
      "updatedAt": 1704086400000,
      "sessionFile": "550e8400-e29b-41d4-a716-446655440000.jsonl",
      "model": "claude-sonnet-4-6",
      "modelProvider": "anthropic",
      "inputTokens": 15000,
      "outputTokens": 3000,
      "totalTokens": 18000,
      "totalTokensFresh": true,
      "contextTokens": 200000,
      "thinkingLevel": "off",
      "verboseLevel": "off",
      "lastChannel": "whatsapp",
      "lastTo": "+15551234567",
      "lastAccountId": "personal",
      "compactionCount": 2
    }
  }
}
```

**Session Key 格式**：`agent:<agentId>:<senderKey>`
- DM（直接对话）：`agent:main:+15551234567`（主要会话键）
- 群组：`agent:main:whatsapp:group:12345@g.us`
- 主会话（main session）：`agent:main:main`

**注意**：sessions.json 是**自动维护**的，通常不需要手动创建或编辑。初始状态可以是空文件或 `{"version":1,"sessions":{}}`。

---

### 4.3 `<sessionId>.jsonl`（会话记录）

**路径**：`<stateDir>/agents/<agentId>/sessions/<sessionId>.jsonl`

**用途**：存储单个会话的完整对话历史（Pi SDK 格式，JSONL 每行一条记录）。

这个文件由 Pi SDK（底层 AI 库）自动管理，**不需要手动创建**。

---

### 4.4 `model-catalog.json`（模型注册表）

**路径**：`<stateDir>/agents/<agentId>/agent/model-catalog.json`

**用途**：缓存该 agent 可用的模型列表（从各 provider 动态发现并缓存）。

这个文件由 openclaw **自动生成和更新**，不需要手动维护。首次运行时会自动创建。

---

### 4.5 `credentials/oauth.json`（历史 OAuth 文件）

**路径**：`<stateDir>/credentials/oauth.json`（或 `OPENCLAW_OAUTH_DIR/oauth.json`）

**用途**：历史 OAuth 凭证存储。新版本已迁移到 `auth-profiles.json`，但首次加载时会自动合并。

**格式**：

```json
{
  "anthropic": {
    "access": "...",
    "refresh": "...",
    "expires": 1704086400000,
    "email": "user@example.com"
  }
}
```

新项目可**不创建**此文件，直接使用 `auth-profiles.json`。

---

## 五、针对外部项目的完整目录设计

### 5.1 推荐目录结构

```
/my/agents-project/
│
├── .state/                                 # ← OPENCLAW_STATE_DIR 指向这里
│   ├── openclaw.json                       # 主配置（JSON5）
│   ├── credentials/                        # OAuth 凭证（可选，新项目可忽略）
│   │   └── oauth.json
│   └── agents/
│       ├── alpha/
│       │   ├── agent/
│       │   │   └── auth-profiles.json      # ★ Alpha agent 的认证信息
│       │   └── sessions/
│       │       └── sessions.json           # 初始化为空，运行时自动填充
│       ├── beta/
│       │   ├── agent/
│       │   │   └── auth-profiles.json
│       │   └── sessions/
│       │       └── sessions.json
│       └── ...
│
├── workspaces/                             # 各 agent 的 workspace（与 state 分开）
│   ├── alpha/
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   ├── USER.md
│   │   ├── IDENTITY.md
│   │   └── memory/
│   ├── beta/
│   │   └── ...
│   └── ...
│
└── openclaw.json → .state/openclaw.json    # 可 symlink 到 state 里
```

### 5.2 最简化初始文件准备脚本

```bash
#!/bin/bash
# init-state.sh - 初始化外部 state 目录
set -e

PROJECT_ROOT="/my/agents-project"
STATE_DIR="$PROJECT_ROOT/.state"
AGENTS=("alpha" "beta" "gamma")

# 1. 创建 state 目录结构
mkdir -p "$STATE_DIR/credentials"

for AGENT_ID in "${AGENTS[@]}"; do
  mkdir -p "$STATE_DIR/agents/$AGENT_ID/agent"
  mkdir -p "$STATE_DIR/agents/$AGENT_ID/sessions"

  # 创建空的 auth-profiles.json（必须）
  if [ ! -f "$STATE_DIR/agents/$AGENT_ID/agent/auth-profiles.json" ]; then
    cat > "$STATE_DIR/agents/$AGENT_ID/agent/auth-profiles.json" << EOF
{
  "version": 1,
  "profiles": {}
}
EOF
  fi

  # 创建空的 sessions.json（可选，运行时自动创建，但提前创建更清晰）
  if [ ! -f "$STATE_DIR/agents/$AGENT_ID/sessions/sessions.json" ]; then
    cat > "$STATE_DIR/agents/$AGENT_ID/sessions/sessions.json" << EOF
{
  "version": 1,
  "sessions": {}
}
EOF
  fi
done

# 2. 创建主配置文件
cat > "$STATE_DIR/openclaw.json" << 'EOF'
{
  agents: {
    defaults: {
      skipBootstrap: true,
      thinkingDefault: "off",
      timeoutSeconds: 600,
    },
    list: [
      {
        id: "alpha",
        name: "Alpha",
        workspace: "/my/agents-project/workspaces/alpha",
        agentDir: "/my/agents-project/.state/agents/alpha/agent",
      },
      {
        id: "beta",
        name: "Beta",
        workspace: "/my/agents-project/workspaces/beta",
        agentDir: "/my/agents-project/.state/agents/beta/agent",
      },
    ],
  },
}
EOF

echo "State 目录初始化完成：$STATE_DIR"
```

### 5.3 注入 API Key 到 auth-profiles.json

```bash
#!/bin/bash
# set-apikey.sh - 为指定 agent 设置 Anthropic API Key
AGENT_ID="$1"
API_KEY="$2"
STATE_DIR="/my/agents-project/.state"
AUTH_FILE="$STATE_DIR/agents/$AGENT_ID/agent/auth-profiles.json"

# 使用 python3 安全地更新 JSON（或用 jq）
python3 - << PYEOF
import json, sys

with open("$AUTH_FILE", "r") as f:
    store = json.load(f)

store.setdefault("profiles", {})
store["profiles"]["anthropic:default"] = {
    "type": "api_key",
    "provider": "anthropic",
    "key": "$API_KEY"
}

with open("$AUTH_FILE", "w") as f:
    json.dump(store, f, indent=2)

print(f"API Key 已写入 $AUTH_FILE")
PYEOF
```

---

## 六、启动 openclaw 时的环境变量设置

### 6.1 推荐的启动方式

```bash
# 方式 A：仅设置 STATE_DIR（配置文件在 state 目录里）
export OPENCLAW_STATE_DIR=/my/agents-project/.state
openclaw start  # 自动读取 /my/agents-project/.state/openclaw.json

# 方式 B：STATE_DIR + 独立配置文件路径（更灵活）
export OPENCLAW_STATE_DIR=/my/agents-project/.state
export OPENCLAW_CONFIG_PATH=/my/agents-project/configs/openclaw.json
openclaw start

# 方式 C：仅指定配置文件（session 仍在 ~/.openclaw/ 下）
export OPENCLAW_CONFIG_PATH=/my/agents-project/openclaw.json
openclaw start

# 方式 D：完全隔离（推荐外部项目使用）
OPENCLAW_STATE_DIR=/my/agents-project/.state openclaw agents list
```

### 6.2 多项目并存时的隔离

每个外部项目可以使用不同的 `OPENCLAW_STATE_DIR`，完全互不干扰：

```bash
# 项目 A 的封装脚本
alias oc-a='OPENCLAW_STATE_DIR=/projects/a/.state openclaw'

# 项目 B 的封装脚本
alias oc-b='OPENCLAW_STATE_DIR=/projects/b/.state openclaw'

oc-a agents list   # 只看项目 A 的 agents
oc-b agents list   # 只看项目 B 的 agents
```

---

## 七、路径解析优先级总结

### agentDir 解析（从高到低）

1. `agents.list[].agentDir`（配置文件中明确设置）
2. `OPENCLAW_AGENT_DIR` / `PI_CODING_AGENT_DIR`（仅对 main agent 生效）
3. `<stateDir>/agents/<agentId>/agent`（默认，随 STATE_DIR 变化）

### workspace 解析（从高到低）

1. `agents.list[].workspace`（per-agent 明确设置）
2. `agents.defaults.workspace`（全局 default，用于 default agent）
3. `<stateDir>/workspace`（单 agent 模式默认）
4. `<stateDir>/workspace-<agentId>`（非 default agent 的自动 fallback）

### sessions 路径（**固定规则**，不可单独覆盖）

```
<stateDir>/agents/<agentId>/sessions/
```

只能通过 `OPENCLAW_STATE_DIR` 整体移动，不能单独为某个 agent 改变 sessions 路径。

---

## 八、Workspace 内部隐藏状态文件

Workspace 目录内（非 state 目录）还会生成一个隐藏的状态文件：

```
<workspaceDir>/
└── .openclaw/
    └── workspace-state.json          # 记录 bootstrap 初始化状态
```

**格式**：

```json
{
  "version": 1,
  "bootstrapSeededAt": "2024-01-01T00:00:00.000Z",
  "onboardingCompletedAt": "2024-01-01T00:00:00.000Z"
}
```

- `bootstrapSeededAt`：BOOTSTRAP.md 首次生成时间
- `onboardingCompletedAt`：onboarding 完成标记（此后不再重新生成 BOOTSTRAP.md）

如果 `skipBootstrap: true`，这个文件不影响行为。手动管理 workspace 时可以忽略或删除它。

---

## 九、凭证共享策略

### 9.1 多个 agent 共享同一套 API Key

有两种方式：

**方式一**：每个 agent 的 `auth-profiles.json` 写相同的 Key（最简单，但 Key 分散）

**方式二**：指向同一个 `agentDir`（**不推荐**，会导致 auth/session 冲突）

**方式三（推荐）**：只配置 main agent 的 Key，其他 agent 自动 fallback

```
源码逻辑（auth-profiles/store.ts）：
如果某 agent 的 auth-profiles.json 为空（profiles 为空对象），
则自动从 main agent 的 auth-profiles.json 继承凭证。
```

所以，只要 main agent（`<stateDir>/agents/main/agent/auth-profiles.json`）配置了 Key，其他 agent 在 Key 为空时会自动继承。

### 9.2 为不同 agent 配置不同的 API 账号

在各 agent 自己的 `auth-profiles.json` 里写不同的 Key 即可：

```json5
// agents/agent-a/agent/auth-profiles.json（使用账号 1）
{
  "version": 1,
  "profiles": {
    "anthropic:default": { "type": "api_key", "provider": "anthropic", "key": "sk-ant-1" }
  }
}

// agents/agent-b/agent/auth-profiles.json（使用账号 2）
{
  "version": 1,
  "profiles": {
    "anthropic:default": { "type": "api_key", "provider": "anthropic", "key": "sk-ant-2" }
  }
}
```

---

## 十、快速检验清单

使用 `openclaw doctor` 和 `openclaw agents list` 验证配置是否正确：

```bash
# 验证当前 state 目录配置
OPENCLAW_STATE_DIR=/my/project/.state openclaw agents list --bindings

# 检查配置文件路径
OPENCLAW_STATE_DIR=/my/project/.state openclaw config get

# 验证 agent 可以正常运行
OPENCLAW_STATE_DIR=/my/project/.state openclaw agent --agent alpha --message "ping" --local

# 诊断问题
OPENCLAW_STATE_DIR=/my/project/.state openclaw doctor
```

**最小可运行 state 目录清单**：

- [ ] `<stateDir>/openclaw.json` — 主配置（JSON5）
- [ ] `<stateDir>/agents/<agentId>/agent/auth-profiles.json` — 每个 agent 的认证
- [ ] workspace 目录中至少有 `AGENTS.md`（可以是空文件）
- [ ] `agents.list[].agentDir` 在配置文件中明确指向正确路径

sessions 目录会在首次运行时自动创建，无需提前手动创建。

---

## 十一、源码关键文件索引

| 文件                                    | 关键内容                                                                     |
| --------------------------------------- | ---------------------------------------------------------------------------- |
| `src/config/paths.ts`                   | `resolveStateDir()`、`resolveConfigPath()`、`resolveOAuthDir()`              |
| `src/agents/agent-paths.ts`             | `resolveOpenClawAgentDir()`（主 agent dir 解析）                             |
| `src/agents/agent-scope.ts`             | `resolveAgentDir()`、`resolveAgentWorkspaceDir()`                            |
| `src/config/sessions/paths.ts`          | `resolveSessionTranscriptsDirForAgent()`、`resolveDefaultSessionStorePath()` |
| `src/agents/auth-profiles/types.ts`     | `AuthProfileStore`、`AuthProfileCredential` 类型定义                         |
| `src/agents/auth-profiles/store.ts`     | 认证 store 加载、保存、main agent 继承逻辑                                   |
| `src/agents/auth-profiles/constants.ts` | 文件名常量（`AUTH_PROFILE_FILENAME = "auth-profiles.json"`）                 |
| `src/agents/workspace.ts`               | `ensureAgentWorkspace()`、workspace bootstrap 文件枚举                       |
| `src/config/sessions/types.ts`          | `SessionEntry` 完整类型（sessions.json 条目结构）                            |
