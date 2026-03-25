# openclaw.json 配置格式规范

> 分析来源：src/config/zod-schema*.ts、src/config/paths.ts、src/config/agent-dirs.ts、src/infra/home-dir.ts

## 文件位置

- 默认：`~/.openclaw/openclaw.json`
- 可通过 `OPENCLAW_CONFIG_PATH` 环境变量覆盖
- 格式：JSON5（支持注释、尾逗号）
- 验证：通过 Zod schema（`src/config/zod-schema.ts`）

---

## 路径字段：是否支持相对路径？

**结论：支持相对路径，但行为取决于具体字段。**

### 路径解析规则（src/config/paths.ts）

```
~/ 或 ~   → 展开为用户 home 目录（支持 OPENCLAW_HOME / HOME 环境变量覆盖）
相对路径   → path.resolve(input)，即相对于 process.cwd()（启动进程时的工作目录）
绝对路径   → 原样使用
```

### 各路径字段一览

| 字段路径                                      | 相对于        | 说明                                            |
| --------------------------------------------- | ------------- | ----------------------------------------------- |
| `agents.defaults.workspace`                   | process.cwd() | agent 运行时的工作目录                          |
| `agents.defaults.repoRoot`                    | process.cwd() | 仓库根目录（覆盖自动检测）                      |
| `agents.list[].workspace`                     | process.cwd() | 单个 agent 的工作目录                           |
| `agents.list[].agentDir`                      | process.cwd() | agent 数据目录（多 agent 模式必须唯一）         |
| `agents.defaults.identity.avatar`             | workspace     | **相对于 workspace**，或 HTTP(s) URL / data URI |
| `agents.list[].identity.avatar`               | workspace     | 同上                                            |
| `agents.defaults.memorySearch.extraPaths[]`   | workspace     | **相对于 workspace**                            |
| `agents.defaults.memorySearch.store.path`     | process.cwd() | 向量数据库路径                                  |
| `agents.defaults.sandbox.workspaceRoot`       | process.cwd() | 沙箱工作空间根目录                              |
| `agents.list[].sandbox.workspaceRoot`         | process.cwd() | 同上                                            |
| `memory.qmd.paths[].path`                     | process.cwd() | QMD 索引路径                                    |
| `session.store`                               | process.cwd() | 会话存储文件                                    |
| `logging.file`                                | process.cwd() | 日志文件                                        |
| `hooks.transformsDir`                         | process.cwd() | Webhook 转换脚本目录                            |
| `cron.store`                                  | process.cwd() | 定时任务存储                                    |
| `browser.executablePath`                      | process.cwd() | 浏览器可执行文件                                |
| `gateway.controlUi.root`                      | process.cwd() | 控制面板静态文件根目录                          |
| `gateway.tls.certPath` / `keyPath` / `caPath` | process.cwd() | TLS 证书文件                                    |
| `canvasHost.root`                             | process.cwd() | Canvas 根目录                                   |
| `plugins.load.paths[]`                        | process.cwd() | 插件加载目录                                    |
| `skills.load.extraDirs[]`                     | process.cwd() | 技能加载目录                                    |

> **注意**：`docker.binds[]` 中的路径为 `host:container` 格式，host 侧推荐使用绝对路径。

---

## 顶级字段总览

```
openclaw.json
├── $schema              # JSON Schema URI（供编辑器提示）
├── meta                 # 元数据（lastTouchedVersion、lastTouchedAt）
├── env                  # 环境变量（shellEnv、vars、自定义键值对）
├── wizard               # 向导信息（lastRunAt 等，通常自动维护）
├── diagnostics          # 诊断/遥测（OTEL、cacheTrace）
├── logging              # 日志（level、file、consoleLevel、redactSensitive）
├── update               # 自动更新（channel、checkOnStart）
├── browser              # 浏览器驱动（executablePath、headless、profiles）
├── ui                   # UI 外观（seamColor、assistant.name/avatar）
├── auth                 # 认证配置（profiles、order、cooldowns）
├── models               # LLM 提供商（mode、providers）
├── agents               # 代理配置（defaults、list）
├── tools                # 工具访问控制（allow、deny、exec、sandbox）
├── bindings             # 代理到渠道的路由绑定
├── broadcast            # 广播配置
├── audio                # 语音配置
├── media                # 媒体处理
├── messages             # 消息格式默认值
├── commands             # 命令配置
├── approvals            # 工具审批策略
├── session              # 会话管理（scope、store、reset）
├── cron                 # 定时任务（enabled、store、webhook）
├── hooks                # Webhooks（path、token、transformsDir、mappings）
├── web                  # Web 服务配置
├── channels             # 消息渠道（WhatsApp、Telegram、Discord、Slack 等 40+）
├── discovery            # 服务发现
├── canvasHost           # Canvas 主机
├── talk                 # 语音交互
├── gateway              # 网关服务器（port、auth、tls、controlUi）
├── memory               # 内存/记忆后端（backend、qmd）
├── skills               # 技能配置（allowBundled、load、limits）
└── plugins              # 插件配置（enabled、allow、deny、load.paths）
```

---

## agents 详细结构

```jsonc
{
  "agents": {
    "defaults": {
      "workspace": "~/my-workspace",          // 所有 agent 默认工作目录
      "repoRoot": "/optional/repo/root",      // 覆盖自动检测的仓库根
      "model": {
        "primary": "anthropic/claude-sonnet-4-5",
        "fallbacks": ["openai/gpt-4o"]
      },
      "maxConcurrent": 4,
      "heartbeat": { "enabled": true, "intervalSec": 30 },
      "memorySearch": {
        "provider": "gemini",
        "model": "gemini-embedding-001",
        "extraPaths": ["../team-docs"],       // 相对于 workspace
        "store": { "path": "~/.openclaw/memory/vectors.db" }
      },
      "sandbox": {
        "mode": "non-main",
        "workspaceRoot": "~/.openclaw/sandboxes",
        "docker": {
          "image": "openclaw-sandbox:bookworm-slim",
          "workdir": "/workspace"
        }
      },
      "identity": {
        "name": "Default Agent",
        "avatar": "avatar.png"                // 相对于 workspace
      }
    },
    "list": [
      {
        "id": "alice",
        "agentDir": "~/.openclaw/agents/alice",  // 必须唯一
        "workspace": "~/workspace-alice",
        "name": "Alice",
        "default": true,
        "model": { "primary": "anthropic/claude-opus-4-6" }
      }
    ]
  }
}
```

### 多 agent 模式限制
- 每个 agent 的 `agentDir` 必须唯一，否则启动时报错
- 若不配置 `agentDir`，默认为 `~/.openclaw/agents/{agentId}/agent`

---

## models 配置

```jsonc
{
  "models": {
    "mode": "allowlist",                      // allowlist | passthrough
    "providers": {
      "anthropic": {
        "apiKey": "${ANTHROPIC_API_KEY}",     // 支持环境变量替换
        "models": ["claude-sonnet-4-5", "claude-opus-4-6"]
      },
      "openai": {
        "baseUrl": "https://api.openai.com/v1",
        "apiKey": "${OPENAI_API_KEY}"
      },
      "openrouter": {
        "apiKey": "${OPENROUTER_API_KEY}"
      }
    }
  }
}
```

---

## gateway 配置

```jsonc
{
  "gateway": {
    "port": 8080,
    "mode": "production",
    "bind": "0.0.0.0",
    "controlUi": {
      "enabled": true,
      "basePath": "/",
      "root": "./ui/dist",                   // 相对于 process.cwd()
      "allowedOrigins": ["https://example.com"]
    },
    "auth": {
      "mode": "bearer",
      "token": "${GATEWAY_TOKEN}"
    },
    "tls": {
      "enabled": true,
      "certPath": "/etc/ssl/cert.pem",
      "keyPath": "/etc/ssl/key.pem"
    }
  }
}
```

---

## 环境变量替换

配置值中支持 `${VAR_NAME}` 语法：

```jsonc
{
  "models": {
    "providers": {
      "groq": { "apiKey": "${GROQ_API_KEY}" }
    }
  }
}
```

---

## 关键环境变量

| 环境变量                | 用途                                |
| ----------------------- | ----------------------------------- |
| `OPENCLAW_CONFIG_PATH`  | 覆盖配置文件路径                    |
| `OPENCLAW_STATE_DIR`    | 覆盖 `~/.openclaw` 状态目录         |
| `OPENCLAW_HOME`         | 覆盖用户 home 目录（影响 `~` 展开） |
| `OPENCLAW_GATEWAY_PORT` | 覆盖网关端口                        |
| `OPENCLAW_NIX_MODE`     | 设为 `1` 启用 Nix 特定行为          |
| `CLAWDBOT_STATE_DIR`    | 遗留兼容（同 OPENCLAW_STATE_DIR）   |
| `CLAWDBOT_CONFIG_PATH`  | 遗留兼容（同 OPENCLAW_CONFIG_PATH） |

---

## 关键源码文件

| 文件                                     | 内容                                       |
| ---------------------------------------- | ------------------------------------------ |
| `src/config/zod-schema.ts`               | 主 schema，OpenClawSchema 完整定义         |
| `src/config/zod-schema.agents.ts`        | agents / bindings schema                   |
| `src/config/zod-schema.agent-runtime.ts` | agent 运行时 schema（工具、沙箱等）        |
| `src/config/paths.ts`                    | 路径解析：resolveUserPath、resolveStateDir |
| `src/config/agent-dirs.ts`               | agent 目录解析，重复检测                   |
| `src/infra/home-dir.ts`                  | expandHomePrefix、home 目录查找逻辑        |
| `src/config/config.ts`                   | 配置加载主流程                             |
| `src/config/defaults.ts`                 | 各字段默认值应用                           |
| `docs/gateway/configuration-examples.md` | 官方配置示例                               |
