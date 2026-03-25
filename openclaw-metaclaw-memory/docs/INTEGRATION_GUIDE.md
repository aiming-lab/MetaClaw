# MetaClaw Memory — OpenClaw 集成指南

本文档详细说明如何将 MetaClaw Memory 插件接入 OpenClaw，从安装到配置到验证，每一步都有具体操作。

---

## 目录

1. [前提条件](#1-前提条件)
2. [安装方式](#2-安装方式)
3. [配置 OpenClaw](#3-配置-openclaw)
4. [初始化 Python 环境](#4-初始化-python-环境)
5. [验证安装](#5-验证安装)
6. [工作原理](#6-工作原理)
7. [使用方式](#7-使用方式)
8. [高级配置](#8-高级配置)
9. [故障排查](#9-故障排查)
10. [卸载](#10-卸载)

---

## 1. 前提条件

| 依赖 | 最低版本 | 检查命令 |
|------|---------|---------|
| Node.js | 18+ | `node --version` |
| Python | 3.10+ | `python3 --version` |
| OpenClaw | 最新版 | `openclaw --version` |
| pip | 最新版 | `pip3 --version` |

---

## 2. 安装方式

### 方式 A：从 npm 安装（推荐，公开发布后可用）

```bash
openclaw plugins install @metaclaw/memory
```

### 方式 B：从本地目录安装（开发/测试用）

```bash
# 先构建
cd /path/to/openclaw-metaclaw-memory
npm install
npm run build

# 链接到 OpenClaw（开发模式）
openclaw plugins install -l /path/to/openclaw-metaclaw-memory

# 或者复制安装
openclaw plugins install /path/to/openclaw-metaclaw-memory
```

### 方式 C：从 tarball 安装

```bash
cd /path/to/openclaw-metaclaw-memory
npm pack                              # 生成 metaclaw-memory-0.1.0.tgz
openclaw plugins install ./metaclaw-memory-0.1.0.tgz
```

安装完成后，通过以下命令确认插件已被发现：

```bash
openclaw plugins list
# 应该看到 metaclaw-memory 在列表中
```

---

## 3. 配置 OpenClaw

编辑你的 OpenClaw 配置文件（通常在 `~/.openclaw/openclaw.json` 或项目目录下的 `openclaw.json`）：

### 最小配置（使用全部默认值）

```json
{
  "plugins": {
    "entries": {
      "metaclaw-memory": {
        "enabled": true
      }
    },
    "slots": {
      "memory": "metaclaw-memory"
    }
  }
}
```

> **重要**：`plugins.slots.memory` 设为 `"metaclaw-memory"` 会**替换** OpenClaw 内置的 `memory-core` 插件。
> 如果你想保留内置记忆功能，可以不设置 slots，仅通过 entries 启用——两者会并存。

### 完整配置（所有选项）

```json
{
  "plugins": {
    "entries": {
      "metaclaw-memory": {
        "enabled": true,
        "config": {
          "autoRecall": true,
          "autoCapture": true,
          "sidecarPort": 19823,
          "scope": "default",
          "retrievalMode": "hybrid",
          "maxInjectedTokens": 800,
          "maxInjectedUnits": 6,
          "memoryDir": "~/.metaclaw/memory",
          "autoUpgradeEnabled": false,
          "pythonPath": "python3",
          "debug": false
        }
      }
    },
    "slots": {
      "memory": "metaclaw-memory"
    }
  }
}
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `autoRecall` | boolean | `true` | 每次对话前自动注入相关记忆 |
| `autoCapture` | boolean | `true` | 对话结束后自动提取和保存记忆 |
| `sidecarPort` | number | `19823` | Python sidecar HTTP 端口 |
| `scope` | string | `"default"` | 记忆作用域（可按项目隔离） |
| `retrievalMode` | string | `"hybrid"` | 检索模式：`keyword`（关键词）/ `embedding`（向量）/ `hybrid`（混合） |
| `maxInjectedTokens` | number | `800` | 每次注入的最大 token 数 |
| `maxInjectedUnits` | number | `6` | 每次注入的最大记忆条数 |
| `memoryDir` | string | `~/.metaclaw/memory` | SQLite 数据库存储目录 |
| `autoUpgradeEnabled` | boolean | `false` | 启用后台自演化工作线程 |
| `pythonPath` | string | `"python3"` | Python 解释器路径 |
| `debug` | boolean | `false` | 详细日志 |

---

## 4. 初始化 Python 环境

安装插件后，需要初始化 Python sidecar 环境：

```bash
openclaw metaclaw setup
```

这个命令会自动：
1. 检测 Python 3.10+ 是否可用
2. 创建虚拟环境 (`~/.openclaw/plugins/@metaclaw/memory/.venv/`)
3. 安装 `metaclaw-memory-sidecar` 包及其依赖（FastAPI、uvicorn 等）
4. 创建记忆存储目录

> **注意**：`metaclaw-memory-sidecar` 包依赖 `metaclaw` 核心包。如果尚未发布到 PyPI，
> 需要先本地安装：`pip install -e /path/to/metaclaw-test`

---

## 5. 验证安装

### 步骤 1：检查插件状态

```bash
openclaw metaclaw status
```

预期输出：
```
Memory System Status
  Status:   ok
  Scope:    default
  Memories: 0

Statistics:
  active: 0
  total: 0
```

### 步骤 2：手动存储一条记忆

使用斜杠命令：
```
/remember 我喜欢使用 TypeScript 编写后端代码
```

或通过 CLI：
```bash
# 直接通过 sidecar API 测试
curl -X POST http://127.0.0.1:19823/store \
  -H "Content-Type: application/json" \
  -d '{"content": "用户偏好 TypeScript 后端开发", "memory_type": "preference"}'
```

### 步骤 3：搜索记忆

```
/recall TypeScript
```

或通过 CLI：
```bash
openclaw metaclaw search "TypeScript"
```

### 步骤 4：确认自动注入

开始一次新对话，输入任何提示。如果 `autoRecall` 已启用，相关记忆会自动注入到提示上下文中（用户不可见，但 LLM 可以看到）。

启用 `debug: true` 可以在日志中看到注入过程：
```
metaclaw-memory: sidecar started
metaclaw-memory: auto-recall injected 3 memories (rendered 412 tokens)
```

---

## 6. 工作原理

### 自动记忆注入（Auto-Recall）

```
用户消息 → before_prompt_build hook 触发
  → 插件提取用户最新 prompt
  → POST /retrieve { task_description: prompt }
  → Sidecar: retrieve_for_prompt() + render_for_prompt()
  → 返回渲染后的 Markdown 记忆上下文
  → 插件: return { prependContext: rendered_markdown }
  → LLM 看到: [记忆上下文] + [用户消息]
```

### 自动记忆提取（Auto-Capture）

```
对话结束 → agent_end hook 触发
  → 插件从 event.messages 中提取 user/assistant 对话轮次
  → POST /ingest { session_id, turns }
  → Sidecar: ingest_session_turns()
    → 自动创建 episodic 记忆（每轮对话）
    → 自动创建 working_summary（对话摘要）
    → 自动合并和去重
  → 记忆持久化到 SQLite + FTS5
```

### 插件生命周期

```
OpenClaw 启动
  → 加载 openclaw.plugin.json（验证 manifest）
  → 导入 dist/index.js
  → 调用 register(api)
    → registerService({ start: 启动 sidecar, stop: 关闭 sidecar })
    → 注册 hooks (before_prompt_build, agent_end)
    → 注册 4 个 AI tools
    → 注册 3 个斜杠命令
    → 注册 CLI 命令组

OpenClaw Gateway 启动时
  → service.start() 触发
  → 启动 Python sidecar 进程 (FastAPI + uvicorn)
  → 等待 /health 响应（最长 15 秒）
  → sidecar 常驻运行，保持 SQLite 连接和缓存

OpenClaw 关闭时
  → service.stop() 触发
  → SIGTERM → sidecar 进程优雅退出
```

---

## 7. 使用方式

### 7.1 斜杠命令（对话中使用）

| 命令 | 说明 | 示例 |
|------|------|------|
| `/remember <文本>` | 手动保存记忆 | `/remember 项目使用 PostgreSQL 数据库` |
| `/recall <查询>` | 搜索记忆 | `/recall 数据库配置` |
| `/memory-status` | 查看系统状态 | `/memory-status` |

### 7.2 AI 工具（LLM 自主调用）

LLM 在对话中可以自动调用以下工具：

| 工具名 | 说明 |
|--------|------|
| `metaclaw_memory_search` | 搜索长期记忆 |
| `metaclaw_memory_store` | 主动存储记忆 |
| `metaclaw_memory_forget` | 归档（软删除）指定记忆 |
| `metaclaw_memory_status` | 查看系统健康状态和统计 |

### 7.3 CLI 命令

```bash
openclaw metaclaw setup       # 初始化 Python 环境
openclaw metaclaw status      # 查看系统状态
openclaw metaclaw search <Q>  # 搜索记忆（支持 --limit）
openclaw metaclaw wipe --yes  # 清除所有记忆（不可逆）
openclaw metaclaw upgrade     # 触发自演化升级周期
```

### 7.4 6 种记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `episodic` | 对话片段 | "用户在讨论数据库迁移时提到了性能问题" |
| `semantic` | 事实知识 | "项目使用 PostgreSQL 14 + Redis 缓存" |
| `preference` | 用户偏好 | "偏好使用 TypeScript、函数式风格" |
| `project_state` | 项目状态 | "v2.0 正在开发中，预计下周发布" |
| `working_summary` | 工作摘要 | "本次对话讨论了 API 重构方案，决定采用 REST" |
| `procedural_observation` | 流程观察 | "每次部署前需要运行 lint 和 type check" |

---

## 8. 高级配置

### 8.1 按项目隔离记忆

为不同项目使用不同的 `scope`：

```json
{
  "plugins": {
    "entries": {
      "metaclaw-memory": {
        "enabled": true,
        "config": {
          "scope": "my-project-name"
        }
      }
    }
  }
}
```

### 8.2 启用自演化

MetaClaw 的独特功能——自演化策略管线：

```json
{
  "config": {
    "autoUpgradeEnabled": true
  }
}
```

启用后，后台工作线程会定期：
- 分析记忆使用模式
- 优化检索策略
- 合并冗余记忆
- 衰减过时记忆

### 8.3 调整检索模式

```json
{
  "config": {
    "retrievalMode": "keyword"
  }
}
```

| 模式 | 优点 | 适用场景 |
|------|------|---------|
| `keyword` | 快速，精确匹配 | 技术文档、代码相关 |
| `embedding` | 语义相似度 | 自然语言、概念匹配 |
| `hybrid` | 两者结合，效果最好 | 通用（推荐） |

### 8.4 控制注入量

如果发现记忆注入影响了 LLM 响应质量：

```json
{
  "config": {
    "maxInjectedUnits": 3,
    "maxInjectedTokens": 400
  }
}
```

### 8.5 使用独立 Python 环境

如果系统有多个 Python 版本：

```json
{
  "config": {
    "pythonPath": "/usr/local/bin/python3.12"
  }
}
```

### 8.6 自定义存储位置

```json
{
  "config": {
    "memoryDir": "~/my-project/.metaclaw-memory"
  }
}
```

### 8.7 更改 sidecar 端口

如果 19823 端口冲突：

```json
{
  "config": {
    "sidecarPort": 19900
  }
}
```

---

## 9. 故障排查

### 问题：sidecar 启动失败

**症状**：`openclaw metaclaw status` 报错 "Could not reach sidecar"

**排查步骤**：

```bash
# 1. 检查端口是否被占用
lsof -i :19823

# 2. 手动启动 sidecar 查看详细错误
cd /path/to/openclaw-metaclaw-memory/sidecar
PYTHONPATH=.:.. python -m metaclaw_memory_sidecar --port 19823 --log-level debug

# 3. 检查 Python 环境
python3 --version  # 需要 3.10+
python3 -c "import fastapi; print(fastapi.__version__)"
python3 -c "from metaclaw.memory.manager import MemoryManager; print('OK')"
```

### 问题：记忆没有被注入

**排查步骤**：

1. 确认 `autoRecall: true`（默认值）
2. 启用 `debug: true` 查看日志
3. 检查是否有记忆存在：`openclaw metaclaw status`
4. 手动测试检索：
   ```bash
   curl -X POST http://127.0.0.1:19823/retrieve \
     -H "Content-Type: application/json" \
     -d '{"task_description": "你的测试查询"}'
   ```

### 问题：记忆没有被保存

**排查步骤**：

1. 确认 `autoCapture: true`
2. 检查 sidecar 日志中是否有 ingest 错误
3. 手动测试存储：
   ```bash
   curl -X POST http://127.0.0.1:19823/store \
     -H "Content-Type: application/json" \
     -d '{"content": "测试记忆", "memory_type": "semantic"}'
   ```

### 问题：端口冲突

```bash
# 查找占用进程
lsof -i :19823

# 修改端口
# 在 openclaw.json 中设置 "sidecarPort": 19900
```

### 问题：SQLite 数据库损坏

```bash
# 备份并重建
cp ~/.metaclaw/memory/memory.db ~/.metaclaw/memory/memory.db.bak
openclaw metaclaw wipe --yes
# 重启 sidecar，数据库会自动重建
```

---

## 10. 卸载

```bash
# 1. 禁用插件
openclaw plugins disable metaclaw-memory

# 2. 完全卸载
openclaw plugins uninstall metaclaw-memory

# 3.（可选）删除记忆数据
rm -rf ~/.metaclaw/memory

# 4.（可选）删除 Python 虚拟环境
rm -rf ~/.openclaw/plugins/@metaclaw/memory/.venv
```

卸载后，OpenClaw 会自动回退到内置的 `memory-core` 插件。

---

## 附录：与其他记忆插件对比

| 功能 | memory-core (内置) | Supermemory | MemOS Cloud | **MetaClaw** |
|------|-------------------|-------------|-------------|--------------|
| 运行环境 | 本地内置 | 云端 | 云端 | **完全本地** |
| 云依赖 | 无 | 必需 | 必需 | **无** |
| 记忆类型 | 通用文本 | 2 种 | 通用 | **6 种结构化** |
| 检索方式 | FTS 全文搜索 | 语义向量 | 向量 | **4 种混合模式** |
| 自演化策略 | 无 | 无 | 无 | **有** |
| 记忆合并/去重 | 无 | 云端处理 | 无 | **本地自动** |
| 记忆衰减 | 无 | 无 | 无 | **有** |
| 自升级 | 无 | 无 | 无 | **有** |
| 隐私 | 本地 | 数据上云 | 数据上云 | **完全本地** |
| 费用 | 免费 | 付费 | 付费 | **免费** |
