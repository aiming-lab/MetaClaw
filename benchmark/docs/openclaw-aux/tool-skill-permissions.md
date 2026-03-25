# OpenClaw 工具与技能权限系统详解

> 分析来源：`src/agents/tool-policy.ts`、`src/agents/tool-policy-pipeline.ts`、`src/agents/pi-tools.policy.ts`、`src/config/types.tools.ts`、`src/config/types.agents.ts`、`src/agents/skills/config.ts`、`src/infra/exec-approvals.ts`

---

## 一、权限系统总览

OpenClaw 的工具权限由 **多层策略管道（Policy Pipeline）** 控制，每一层只能 **进一步收紧** 权限，不能放宽上游层的限制。策略从全局配置到 agent 级别再到运行时上下文逐级细化。

```
┌──────────────────────────────────────────────────┐
│  1. tools.profile         （基础 profile 展开）  │
│  2. tools.byProvider.profile  （provider profile）│
│  3. tools.allow / deny    （全局显式策略）        │
│  4. tools.byProvider.allow/deny （全局 provider） │
│  5. agents.X.tools.allow/deny （per-agent 策略）  │
│  6. agents.X.tools.byProvider  （agent+provider） │
│  7. group tools.allow/deny （渠道/群组级策略）    │
│  8. sandbox tools.allow/deny （沙箱策略）         │
│  9. subagent deny list    （子 agent 深度限制）   │
└──────────────────────────────────────────────────┘
         ↓ 每层只能进一步过滤 ↓
      最终可用工具列表
```

---

## 二、工具策略的核心概念

### 2.1 allow / deny / alsoAllow

```jsonc
{
  "tools": {
    "allow": ["exec", "read"],       // 白名单（只允许列出的工具）
    "alsoAllow": ["web_search"],     // 追加白名单（不替换，叠加到 profile/allow 之上）
    "deny": ["browser"]             // 黑名单（deny 优先于 allow）
  }
}
```

**判定逻辑**（`makeToolPolicyMatcher()`，位于 `pi-tools.policy.ts:13`）：

1. 若工具名匹配 `deny` 中的任何条目 → **拒绝**
2. 若 `allow` 为空 → **全部允许**（无限制）
3. 若工具名匹配 `allow` 中的任何条目 → **允许**
4. 特殊规则：若 `exec` 在 allow 中，则 `apply_patch` 自动允许
5. 通配符：`*` 在 allow 中表示全部允许，在 deny 中表示全部拒绝
6. 支持 glob 模式（如 `web_*`）

### 2.2 工具组（Tool Groups）

可在 allow/deny 中使用组名作为简写（定义于 `tool-policy.ts:15`）：

| 组名               | 包含的工具                                                                  |
| ------------------ | --------------------------------------------------------------------------- |
| `group:fs`         | `read`, `write`, `edit`, `apply_patch`                                      |
| `group:runtime`    | `exec`, `process`                                                           |
| `group:sessions`   | `sessions_list`, `sessions_history`, `sessions_send`, `sessions_spawn`, `subagents`, `session_status` |
| `group:memory`     | `memory_search`, `memory_get`                                               |
| `group:web`        | `web_search`, `web_fetch`                                                   |
| `group:ui`         | `browser`, `canvas`                                                         |
| `group:automation` | `cron`, `gateway`                                                           |
| `group:messaging`  | `message`                                                                   |
| `group:nodes`      | `nodes`                                                                     |
| `group:openclaw`   | 所有原生工具（不含插件）                                                    |
| `group:plugins`    | 所有已启用的插件工具                                                        |

### 2.3 Profile（预设策略模板）

通过 `tools.profile` 选择预设模板（定义于 `tool-policy.ts:65`）：

| Profile      | 允许的工具                                                          |
| ------------ | ------------------------------------------------------------------- |
| `minimal`    | 仅 `session_status`                                                 |
| `coding`     | `group:fs` + `group:runtime` + `group:sessions` + `group:memory` + `image` |
| `messaging`  | `group:messaging` + `sessions_list` + `sessions_history` + `sessions_send` + `session_status` |
| `full`       | 无限制（空策略 = 全部允许）                                         |

### 2.4 工具名别名

部分工具名支持别名（`tool-policy.ts:10`）：
- `bash` → `exec`
- `apply-patch` → `apply_patch`

---

## 三、全局配置（`openclaw.json` 中的 `tools` 字段）

### 3.1 完整结构

```jsonc
{
  "tools": {
    // --- 工具策略 ---
    "profile": "coding",                // 基础 profile
    "allow": ["exec", "read"],           // 全局白名单
    "alsoAllow": ["web_search"],         // 追加白名单（叠加到 profile 之上）
    "deny": ["browser"],                 // 全局黑名单

    // --- 按 provider/model 覆盖 ---
    "byProvider": {
      "openai": {
        "profile": "coding",
        "allow": ["group:fs"],
        "deny": ["exec"]
      },
      "anthropic/claude-opus-4-6": {     // provider/model 精确匹配
        "deny": ["browser"]
      }
    },

    // --- Exec 工具配置 ---
    "exec": {
      "host": "sandbox",                // sandbox | gateway | node
      "security": "allowlist",          // deny | allowlist | full
      "ask": "on-miss",                 // off | on-miss | always
      "safeBins": ["cat", "echo"],      // 无需白名单的安全命令
      "pathPrepend": ["/usr/local/bin"],
      "backgroundMs": 5000,
      "timeoutSec": 120
    },

    // --- 文件系统工具 ---
    "fs": {
      "workspaceOnly": true             // 限制 read/write/edit 只能访问 workspace 内文件
    },

    // --- Elevated 提权模式 ---
    "elevated": {
      "enabled": true,                  // 全局开关
      "allowFrom": {                    // 按 provider 的发送者白名单
        "telegram": ["alice", "bob"],
        "whatsapp": ["*"]               // * 表示任何人
      }
    },

    // --- 子 agent 策略 ---
    "subagents": {
      "model": "anthropic/claude-sonnet-4-6",
      "tools": {
        "allow": ["group:fs", "group:runtime"],
        "deny": ["gateway"]
      }
    },

    // --- 沙箱策略 ---
    "sandbox": {
      "tools": {
        "allow": ["exec", "read", "write", "edit"],
        "deny": ["browser", "canvas"]
      }
    },

    // --- 其他工具配置 ---
    "loopDetection": {
      "enabled": true,
      "warningThreshold": 10,
      "criticalThreshold": 20
    }
  }
}
```

### 3.2 byProvider 匹配规则

`byProvider` 的 key 支持两种格式（`pi-tools.policy.ts:148`）：

1. **仅 provider**: `"openai"` — 匹配该 provider 的所有模型
2. **provider/model**: `"anthropic/claude-opus-4-6"` — 精确匹配特定模型

匹配优先级：精确模型 ID > provider ID。

---

## 四、Per-Agent 配置

每个 agent 可在 `agents.list[]` 中设置独立的工具和技能权限：

```jsonc
{
  "agents": {
    "list": [
      {
        "id": "coder",
        "tools": {
          "profile": "coding",
          "allow": ["exec", "group:fs"],
          "alsoAllow": ["web_search"],
          "deny": ["browser"],
          "byProvider": {
            "google": { "deny": ["exec"] }
          },
          "elevated": {
            "enabled": false                // 禁用该 agent 的提权模式
          },
          "exec": {
            "security": "allowlist",
            "ask": "always"                 // 每次执行都需确认
          },
          "fs": {
            "workspaceOnly": true
          },
          "sandbox": {
            "tools": {
              "allow": ["exec", "read"],
              "deny": ["write"]
            }
          }
        },
        "skills": ["git", "python"]         // 技能白名单
      }
    ]
  }
}
```

### 4.1 Agent 策略与全局策略的关系

- Agent 的 `tools.profile` 会覆盖全局 `tools.profile`
- Agent 的 `tools.allow/deny` 作为管道中的独立步骤，只能进一步限制全局策略的结果
- Agent 的 `tools.elevated` 只能进一步限制全局 `tools.elevated`（两者都需 `enabled: true` 才能生效）
- `alsoAllow` 是追加式的，合并到 profile 的 allow 列表中

### 4.2 AgentToolsConfig 与 ToolsConfig 的差异

| 字段                 | 全局 ToolsConfig | Per-Agent AgentToolsConfig |
| -------------------- | :--------------: | :------------------------: |
| profile              | ✅               | ✅                         |
| allow / deny         | ✅               | ✅                         |
| alsoAllow            | ✅               | ✅                         |
| byProvider           | ✅               | ✅                         |
| elevated             | ✅               | ✅（只能更严格）           |
| exec                 | ✅               | ✅                         |
| fs                   | ✅               | ✅                         |
| sandbox.tools        | ✅               | ✅                         |
| loopDetection        | ✅               | ✅                         |
| subagents            | ✅               | ❌                         |
| web / media / links  | ✅               | ❌                         |
| message / sessions   | ✅               | ❌                         |
| agentToAgent         | ✅               | ❌                         |

---

## 五、策略管道执行流程

管道由 `buildDefaultToolPolicyPipelineSteps()` 构建（`tool-policy-pipeline.ts:17`），
由 `applyToolPolicyPipeline()` 执行（`tool-policy-pipeline.ts:65`）：

```
步骤 1: tools.profile (coding)
  → 展开 profile 为 allow 列表，合并 alsoAllow
步骤 2: tools.byProvider.profile (openai)
  → provider 级 profile 覆盖
步骤 3: tools.allow / tools.deny
  → 全局显式白名单/黑名单过滤
步骤 4: tools.byProvider.allow / deny
  → 全局 provider 级白名单/黑名单
步骤 5: agents.X.tools.allow / deny
  → per-agent 白名单/黑名单
步骤 6: agents.X.tools.byProvider.allow / deny
  → per-agent + provider 级过滤
步骤 7: group tools.allow / deny
  → 渠道/群组级策略（最终限制层）
```

每个步骤都会调用 `filterToolsByPolicy()` 过滤当前工具列表。每一步只能移除工具，不能添加。

### 5.1 插件工具白名单保护

如果 `allow` 列表中只包含插件工具（不包含任何核心工具），系统会 **自动剥离该白名单**，防止意外禁用所有核心工具。此时会发出警告，建议改用 `alsoAllow`（`tool-policy.ts:232`）。

---

## 六、Exec 命令审批系统

### 6.1 exec-approvals.json

独立于 `openclaw.json`，位于 `~/.openclaw/exec-approvals.json`：

```jsonc
{
  "version": 1,
  "socket": {
    "path": "~/.openclaw/exec-approvals.sock",
    "token": "..."
  },
  "defaults": {
    "security": "allowlist",
    "ask": "on-miss",
    "askFallback": "deny",
    "autoAllowSkills": false             // 技能注册的二进制文件是否自动放行
  },
  "agents": {
    "main": {
      "security": "allowlist",
      "ask": "on-miss",
      "allowlist": [
        { "id": "uuid", "pattern": "git *", "lastUsedAt": 1234567890 }
      ]
    },
    "*": { }                              // 通配符，适用于所有 agent
  }
}
```

### 6.2 Exec Security 模式

| 模式        | 含义                                        |
| ----------- | ------------------------------------------- |
| `deny`      | 默认，拒绝所有 exec 命令（除非 host 覆盖） |
| `allowlist` | 命令必须匹配白名单条目                      |
| `full`      | 所有命令直接允许，无需白名单检查            |

### 6.3 Exec Ask 模式

| 模式      | 含义                                  |
| --------- | ------------------------------------- |
| `off`     | 从不询问                              |
| `on-miss` | 默认，仅在命令不在白名单时询问        |
| `always`  | 每次执行都询问                        |

### 6.4 是否需要审批的判定逻辑

```typescript
// exec-approvals.ts
requiresExecApproval = (
  params.ask === "always" ||
  (params.ask === "on-miss" &&
    params.security === "allowlist" &&
    (!params.analysisOk || !params.allowlistSatisfied))
);
```

### 6.5 SafeBins

通过 `tools.exec.safeBins` 配置的二进制文件（如 `cat`, `echo`），在仅接收标准输入（无文件/路径参数）时可绕过白名单。

---

## 七、子 Agent（Subagent）权限限制

子 agent 的权限除了继承父级管道过滤外，还有额外的硬编码限制（`pi-tools.policy.ts:44`）。

### 7.1 所有子 agent 始终禁止的工具

```
gateway, agents_list, whatsapp_login, session_status,
cron, memory_search, memory_get, sessions_send
```

### 7.2 叶子子 agent 额外禁止的工具

当子 agent 深度 >= `maxSpawnDepth`（默认 1）时：

```
sessions_list, sessions_history, sessions_spawn
```

### 7.3 深度控制

`maxSpawnDepth` 通过 `agents.defaults.subagents.maxSpawnDepth` 配置（默认 1）。

- **深度 1 + maxSpawnDepth >= 2**（编排者子 agent）：保留 `sessions_spawn` 等工具，可管理子 agent
- **深度 >= maxSpawnDepth**（叶子子 agent）：禁止 spawn 和 session 管理工具

额外的 deny 可通过 `tools.subagents.tools.deny` 追加。

---

## 八、沙箱工具策略

沙箱有独立的默认白名单（来自 `sandbox/constants.ts`）：

**默认允许**：
```
exec, process, read, write, edit, apply_patch, image,
sessions_list, sessions_history, sessions_send, sessions_spawn,
subagents, session_status
```

**默认拒绝**：
```
browser, canvas, nodes, cron, gateway, [所有渠道 ID]
```

可通过以下方式覆盖：
- 全局：`tools.sandbox.tools.allow/deny`
- Per-agent：`agents.list[].tools.sandbox.tools.allow/deny`（完全替换全局设置，不合并）

---

## 九、渠道/群组级工具策略

通过 `channels.<channel>.groups` 配置，按群组和发送者进一步限制（`group-policy.ts`）：

```jsonc
{
  "channels": {
    "discord": {
      "groups": {
        "guild-id-123": {
          "tools": {
            "allow": ["read"],
            "deny": ["exec"]
          },
          "toolsBySender": {
            "alice": { "allow": ["*"] },         // alice 可用所有工具
            "*": { "deny": ["browser"] }          // 其他人禁用 browser
          }
        },
        "*": {                                    // 通配符，所有群组
          "tools": { "deny": ["exec"] }
        }
      }
    }
  }
}
```

`toolsBySender` 匹配字段包括：`senderId`、`senderE164`、`senderUsername`、`senderName`。第一个匹配的条目生效，然后尝试通配符 `*`。

群组策略是管道的最后一步，只能在上游允许的范围内进一步限制。

---

## 十、Owner-Only 工具

某些工具仅限 owner 使用（`tool-policy.ts:63`）：

```typescript
const OWNER_ONLY_TOOL_NAMES = new Set<string>(["whatsapp_login"]);
```

- 非 owner 发送者：工具从列表中完全移除（不仅是执行被阻止）
- 通过 `applyOwnerOnlyToolPolicy()` 在管道之外单独执行

---

## 十一、Elevated（提权）模式

通过 `/elevated` 指令触发，允许跳过沙箱直接在宿主机执行命令。

### 11.1 门控条件

1. 全局 `tools.elevated.enabled` 必须为 `true`（默认 true）
2. Agent 级 `agents.list[].tools.elevated.enabled` 必须为 `true`（默认 true）
3. 发送者必须在 `allowFrom` 白名单中

### 11.2 提权后的行为

- `host` 切换为 `"gateway"`（绕过沙箱）
- `security` 根据 `defaultLevel` 变为 `"full"` 或 `"ask"`
- `defaultLevel` 取值：`"off"` | `"on"`（→ ask）| `"ask"` | `"full"`（绕过审批）

---

## 十二、技能（Skills）权限系统

技能不是传统的"工具"——它们是 Markdown 文件（`SKILL.md`），通过注入上下文/指令扩展 agent 的能力。权限系统与工具白名单分离。

### 12.1 全局技能配置

```jsonc
{
  "skills": {
    "allowBundled": ["git", "python"],     // 内置技能白名单（省略则允许全部）
    "entries": {
      "my-skill": { "enabled": false },     // 禁用特定技能
      "openai-skill": {
        "enabled": true,
        "apiKey": "sk-..."
      }
    }
  }
}
```

### 12.2 Per-Agent 技能配置

```jsonc
{
  "agents": {
    "list": [
      {
        "id": "coder",
        "skills": ["git", "python"]        // 技能白名单
      }
    ]
  }
}
```

- `skills` 省略 → 允许所有符合条件的技能
- `skills: []`（空数组） → 禁用所有技能

### 12.3 技能资格评估流程

`shouldIncludeSkill()`（`skills/config.ts:70`）按以下顺序判断：

1. `skills.entries.<key>.enabled === false` → 排除
2. 内置技能不在 `skills.allowBundled` 中 → 排除
3. OS 不匹配 → 排除
4. `metadata.always === true` → 始终包含
5. 运行时 `requires` 检查（二进制文件是否存在、环境变量是否设置、配置路径是否有效）

Per-agent 的 `skills` 白名单在上述流程之后额外过滤（`filterSkillEntries()`，位于 `skills/workspace.ts`），是简单的名称匹配。

### 12.4 技能与 Exec 审批

`exec-approvals.json` 中的 `autoAllowSkills`（默认 `false`）：当设为 `true` 时，技能注册的二进制文件可绕过 exec 白名单，无需显式审批条目。

---

## 十三、常见配置示例

### 示例 1：最小权限 agent（只读）

```jsonc
{
  "agents": {
    "list": [{
      "id": "reader",
      "tools": {
        "profile": "minimal",
        "alsoAllow": ["read"]
      },
      "skills": []                         // 禁用所有技能
    }]
  }
}
```

### 示例 2：编码 agent + 按 provider 限制

```jsonc
{
  "agents": {
    "list": [{
      "id": "coder",
      "tools": {
        "profile": "coding",
        "alsoAllow": ["web_search"],
        "deny": ["browser"],
        "byProvider": {
          "openai": { "deny": ["exec"] }    // OpenAI 模型禁止执行命令
        },
        "exec": {
          "security": "allowlist",
          "ask": "on-miss"
        },
        "fs": { "workspaceOnly": true }
      },
      "skills": ["git", "python", "node"]
    }]
  }
}
```

### 示例 3：全局限制 + agent 例外

```jsonc
{
  "tools": {
    "deny": ["browser", "canvas"],          // 全局禁用 browser 和 canvas
    "exec": { "security": "allowlist" }
  },
  "agents": {
    "list": [{
      "id": "admin",
      "tools": {
        "profile": "full"                   // admin 使用 full profile
        // 注意：全局 deny 仍然生效！管道是逐层收紧的
        // 若需要 admin 使用 browser，需要移除全局 deny
      }
    }]
  }
}
```

> **注意**：管道是逐层收紧的，per-agent 的 profile/allow 无法覆盖全局 deny。若需要某个 agent 使用被全局禁止的工具，需调整全局策略。

---

## 十四、关键源码文件索引

| 文件                                         | 内容                                                  |
| -------------------------------------------- | ----------------------------------------------------- |
| `src/agents/tool-policy.ts`                  | 工具组、Profile、名称别名、`expandToolGroups`         |
| `src/agents/tool-policy-pipeline.ts`         | 策略管道构建与执行                                    |
| `src/agents/pi-tools.policy.ts`              | `filterToolsByPolicy`、子 agent 策略、group 策略解析  |
| `src/agents/pi-tools.ts`                     | `createOpenClawCodingTools` — 组装工具 + 应用完整管道 |
| `src/config/types.tools.ts`                  | `ToolsConfig`、`AgentToolsConfig`、`ExecToolConfig` 类型 |
| `src/config/types.agents.ts`                 | `AgentConfig`（含 `tools` 和 `skills` 字段）          |
| `src/agents/sandbox-tool-policy.ts`          | `pickSandboxToolPolicy`、`alsoAllow` 合并逻辑         |
| `src/agents/sandbox/constants.ts`            | 沙箱默认允许/拒绝列表                                 |
| `src/infra/exec-approvals.ts`                | `exec-approvals.json` Schema、`requiresExecApproval`  |
| `src/infra/exec-approvals-allowlist.ts`      | `evaluateExecAllowlist`、`isSafeBinUsage`             |
| `src/config/group-policy.ts`                 | 渠道群组级工具策略解析                                |
| `src/auto-reply/reply/reply-elevated.ts`     | Elevated 模式门控逻辑                                 |
| `src/agents/skills/config.ts`                | 技能资格评估：`shouldIncludeSkill`                    |
| `src/agents/skills/workspace.ts`             | `filterSkillEntries`（per-agent 技能过滤）            |
