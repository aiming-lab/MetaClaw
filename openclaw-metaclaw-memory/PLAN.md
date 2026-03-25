# MetaClaw Memory — OpenClaw Plugin Integration Plan

## 调研结论

通过深入阅读 OpenClaw 官方文档 (docs.openclaw.ai) 和现有插件源码（memory-core、supermemory、MemOS Cloud），确认了以下关键信息：

### OpenClaw 插件 API（实际）

1. **入口格式**：`export default { id, name, kind, configSchema, register(api) }`
2. **工具注册**：`api.registerTool({ name, label, description, parameters, execute(toolCallId, params) }, { name })`
3. **生命周期钩子**：`api.on("before_agent_start", handler)`, `api.on("agent_end", handler)`
4. **斜杠命令**：`api.registerCommand({ name, description, acceptsArgs, requireAuth, handler })`
5. **CLI 命令**：`api.registerCli(({ program }) => { ... }, { commands: [...] })`
6. **后台服务**：`api.registerService({ id, start, stop })`
7. **配置获取**：`api.pluginConfig`
8. **日志**：`api.logger`
9. **Memory Slot**：`kind: "memory"` 声明后可在 `plugins.slots.memory` 中选择
10. **Parameters**：使用 TypeBox (`@sinclair/typebox`) 定义参数类型

### 上下文注入（核心机制）

- `before_agent_start` hook 返回 `{ prependContext: "..." }` 注入记忆上下文
- `agent_end` hook 接收 `event.messages[]` 和 `event.success`
- 不需要 `api.prependContext()` — 直接通过 hook 返回值注入

### 竞品分析（已确认）

| 插件 | 类型 | 云依赖 | 自演化 | 检索模式 |
|------|------|--------|--------|----------|
| memory-core | 内置 | 无 | 无 | SQLite+FTS |
| supermemory | 第三方 | 必需 | 无 | 云端向量 |
| MemOS Cloud | 第三方 | 必需 | 无 | 云端 |
| **MetaClaw** | **第三方** | **无** | **是** | **4 种混合** |

## 需要修改的文件

### Python Sidecar — 无需改动 ✅
所有 12 个端点已通过 E2E 测试，保持不变。

### TypeScript 插件 — 全面重写

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `openclaw.plugin.json` | 重写 | 添加 `id`, `kind: "memory"`, 标准 JSON Schema |
| `package.json` | 更新 | 添加 `openclaw.extensions`, TypeBox 依赖 |
| `tsconfig.json` | 微调 | 可能无需改动 |
| `src/index.ts` | 重写 | `export default { register(api) }` 模式 |
| `src/types.ts` | 更新 | 对齐实际 API 类型 |
| `src/client.ts` | 无改动 | HTTP 客户端逻辑不变 |
| `src/sidecar.ts` | 微调 | 集成 `registerService` |
| `src/hooks/auto-recall.ts` | 重写 | `api.on("before_agent_start")` |
| `src/hooks/auto-capture.ts` | 重写 | `api.on("agent_end")` |
| `src/tools/memory-search.ts` | 重写 | TypeBox params + `execute()` |
| `src/tools/memory-store.ts` | 重写 | TypeBox params + `execute()` |
| `src/tools/memory-forget.ts` | 重写 | TypeBox params + `execute()` |
| `src/tools/memory-status.ts` | 重写 | TypeBox params + `execute()` |
| `src/commands/setup.ts` | 重写 | `registerCli` 模式 |
| `src/commands/status.ts` | 拆分 | CLI + 斜杠命令 |
| `src/commands/search.ts` | 拆分 | CLI + 斜杠命令 |
| `src/commands/wipe.ts` | 重写 | `registerCli` 模式 |
| `src/commands/upgrade.ts` | 重写 | `registerCli` 模式 |

## 任务拆解与执行计划

### Task 1: 更新 manifest 和 package.json ✅
- `openclaw.plugin.json` → 标准格式 (`id`, `kind: "memory"`, `configSchema` 完整 JSON Schema + `uiHints`)
- `package.json` → 添加 `openclaw.extensions`, `@sinclair/typebox` 依赖, `peerDependencies`

### Task 2: 重写入口 `src/index.ts` ✅
- 改为 `export default { id, name, kind, configSchema, register(api) }`
- 使用 `api.pluginConfig` 获取配置 (通过 `parseConfig()`)
- 使用 `api.registerService` 管理 sidecar 生命周期
- 使用 `api.logger` 替代 console
- lazy client getter 模式

### Task 3: 重写 Hooks ✅
- `auto-recall.ts`: `api.on("before_agent_start", ...)` → 返回 `{ prependContext }`
- `auto-capture.ts`: `api.on("agent_end", ...)` → 从 `event.messages` 提取对话

### Task 4: 重写 Tools ✅
- 所有 4 个工具使用 TypeBox `Type.Object()` 定义参数
- 使用 `execute(toolCallId, params)` 替代 `handler`
- 返回 `{ content: [{ type: "text", text: "..." }] }`
- 工具名前缀改为 `metaclaw_memory_*`

### Task 5: 重写 Commands ✅
- 斜杠命令（`/remember`, `/recall`, `/memory-status`）→ `api.registerCommand()`
- CLI 命令（`openclaw metaclaw setup/status/search/wipe/upgrade`）→ `api.registerCli()`
- 删除旧的 5 个命令文件，合并为 `cli.ts` + `slash.ts`

### Task 6: 更新 sidecar.ts + types.ts ✅
- `sidecar.ts` 通过 `registerService({ start, stop })` 集成（在 index.ts 中）
- `types.ts` 添加 `parseConfig()` + `defaultConfig`
- 新增 `config-schema.ts` (TypeBox schema)

### Task 7: 构建验证 ✅
- TypeScript 编译零错误
- 打包结构正确（dist/ 包含所有文件）
- clean rebuild 验证通过

### Task 8: 文档更新 ✅
- README 反映新的 API（memory slot, slash commands, CLI）
- 安装说明更新（`openclaw metaclaw` 命令）
- 发布指南添加
- 竞品对比表更新（包含 memory-core）

## 分支策略

在当前 `memory-upgrade` 分支上执行：
- `openclaw-metaclaw-memory/` 目录仍是 untracked 状态
- 没有 git 历史需要保护
- 修改完成后一次性提交

## 发布路径

1. 本地开发完成 → 编译通过
2. npm 发布为 `@metaclaw/memory`
3. 用户安装：`openclaw plugins install @metaclaw/memory`
4. 配置：`plugins.slots.memory = "metaclaw-memory"` 或 entries 启用
5. 初始化：`openclaw metaclaw setup`
