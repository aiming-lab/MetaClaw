# MetaClaw Memory × OpenClaw 插件 — 交接文档

> 本文档面向接手此项目剩余工作的同事，涵盖背景、目标、当前状态、
> 剩余工作及具体操作步骤。

---

## 一、背景

MetaClaw Memory 是我们自研的记忆系统，核心能力包括：
- 6 种结构化记忆类型（事实、偏好、技能、情景等）
- FTS5 + 向量嵌入的混合检索（4 种模式：keyword / embedding / hybrid / auto）
- 本地 SQLite 存储，零云依赖
- 自演化策略（candidate → replay → promotion 升级循环）
- 自动合并、衰减、去重

OpenClaw 是一个流行的 AI 开发框架，拥有成熟的插件生态。将 MetaClaw Memory
封装为 OpenClaw 插件，可以让任何 OpenClaw 用户直接使用我们的记忆系统。

**核心差异化**：相比已有的 Mem0、Supermemory、MemOS Cloud 等插件，
我们是唯一一个完全本地化、自带自演化能力的方案。

---

## 二、架构

```
┌──────────────────────┐         localhost:19823        ┌──────────────────────┐
│   OpenClaw Gateway   │  ←── HTTP (fetch) ──────────→  │  MetaClaw Sidecar    │
│                      │                                │  (FastAPI + uvicorn) │
│  ┌────────────────┐  │   /retrieve → 注入记忆到提示   │  ┌────────────────┐  │
│  │ TS Plugin      │──│──────────────────────────────→ │  │ MemoryManager  │  │
│  │  • auto-recall │  │   /ingest   → 提取记忆         │  │ MemoryStore    │  │
│  │  • auto-capture│  │   /search   → 搜索             │  │ UpgradeWorker  │  │
│  │  • AI tools    │  │   /store    → 存储             │  │ (background)   │  │
│  │  • CLI cmds    │  │   /health   → 健康检查          │  └────────────────┘  │
│  └────────────────┘  │                                │        ↕ SQLite+FTS5  │
└──────────────────────┘                                └──────────────────────┘
```

**为什么用 sidecar？** MetaClaw Memory 是 Python，OpenClaw 插件是 TypeScript。
我们用本地 HTTP sidecar（FastAPI + uvicorn）桥接两者，进程常驻保持连接/缓存热。

---

## 三、项目结构

```
openclaw-metaclaw-memory/
├── package.json                      # npm 包配置，name: @metaclaw/memory
├── openclaw.plugin.json              # OpenClaw 插件清单
├── tsconfig.json
├── .npmignore                        # npm 打包排除规则
├── src/                              # TypeScript 源码
│   ├── index.ts                      # 入口：注册 hooks/tools/CLI/service
│   ├── sidecar.ts                    # 启动/停止 Python sidecar
│   ├── client.ts                     # sidecar HTTP 客户端
│   ├── types.ts                      # 类型定义 + parseConfig
│   ├── config-schema.ts              # TypeBox 配置 schema
│   ├── hooks/
│   │   ├── auto-recall.ts            # before_prompt_build → 注入记忆
│   │   └── auto-capture.ts           # agent_end → 提取记忆
│   ├── tools/
│   │   ├── memory-search.ts          # AI tool: 搜索记忆
│   │   ├── memory-store.ts           # AI tool: 存储记忆
│   │   ├── memory-forget.ts          # AI tool: 删除记忆
│   │   └── memory-status.ts          # AI tool: 查看状态
│   └── commands/
│       ├── cli.ts                    # CLI: setup/status/search/wipe/upgrade
│       └── slash.ts                  # 斜杠命令: /remember, /recall, /memory-status
├── dist/                             # 编译输出（已构建）
└── sidecar/                          # Python sidecar（自包含）
    ├── pyproject.toml                # Python 包配置
    ├── .gitignore
    ├── metaclaw_memory_sidecar/      # FastAPI 服务
    │   ├── server.py                 # 10 个 API 端点
    │   ├── config.py
    │   └── __main__.py
    └── metaclaw/                     # 内嵌的 memory 模块（18 个文件，~10000 行）
        ├── __init__.py
        ├── config.py                 # MetaClawConfig dataclass
        └── memory/                   # 完整的记忆子系统
            ├── manager.py
            ├── store.py
            ├── models.py
            └── ... (15 个其他文件)
```

---

## 四、当前状态（已完成的工作）

| # | 任务 | 状态 |
|---|------|------|
| 1 | 调研 OpenClaw 插件 API（文档 + 3 个真实插件源码） | ✅ 完成 |
| 2 | 重写所有 TS 代码匹配真实 API（hooks/tools/CLI/service） | ✅ 完成 |
| 3 | 将 `metaclaw/memory/` 模块打包进 sidecar，消除 PyPI 依赖 | ✅ 完成 |
| 4 | 修改 setup 命令从本地安装 sidecar | ✅ 完成 |
| 5 | sidecar.ts 优先使用 venv Python | ✅ 完成 |
| 6 | TypeScript 零错误编译 | ✅ 完成 |
| 7 | sidecar 自包含测试（导入 + E2E health/store/search） | ✅ 完成 |
| 8 | npm pack 验证（67 文件，103.6 kB，无 __pycache__） | ✅ 完成 |
| 9 | 编写 OpenClaw 侧文档（OPENCLAW_PLUGIN_SPEC.md） | ✅ 完成 |
| 10 | 编写安装指南（QUICK_START.md, INTEGRATION_GUIDE.md） | ✅ 完成 |
| 11 | 编写发布指南（PUBLISH_GUIDE.md） | ✅ 完成 |

**底线：代码已全部完成、编译通过、本地验证通过。**

---

## 五、剩余工作

### 任务 1：发布到 npm（必须）

这是让用户能 `openclaw plugins install @metaclaw/memory` 的前提。

**具体步骤：**

```bash
# 1. 注册/登录 npm 账号
npm login

# 2. 确保 @metaclaw scope 可用
#    如果是首次使用，需要在 npmjs.com 上创建 @metaclaw 组织
#    或者用个人账号发布（需要修改 package.json 的 name）

# 3. 进入插件目录
cd openclaw-metaclaw-memory

# 4. 确认构建是最新的
npm run build

# 5. 最终检查打包内容
npm pack --dry-run
# 应该看到 dist/, sidecar/, openclaw.plugin.json，总共约 67 个文件

# 6. 发布
npm publish --access public
```

**注意事项：**
- `@metaclaw` 是一个 scoped 包，需要 `--access public` 才能公开
- 如果 `@metaclaw` scope 不可用，可以改名为 `openclaw-metaclaw-memory`
  （修改 package.json 的 `name` 字段）
- 版本号当前是 `0.1.0`，首次发布用这个即可

### 任务 2：向 OpenClaw 社区提交（推荐）

让插件出现在 OpenClaw 的 [Community Plugins](https://docs.openclaw.ai/plugins/community) 页面。

**具体步骤：**

1. Fork OpenClaw 的文档仓库
2. 在 community plugins 列表中添加条目：
   ```
   - **@metaclaw/memory** — Self-evolving local-first memory with 6 structured types,
     hybrid retrieval (FTS5 + embedding), and automatic self-upgrade cycles.
     Fully local, zero cloud dependency.
   ```
3. 提交 PR，附上 OPENCLAW_PLUGIN_SPEC.md 中的技术说明

**参考文档：** `OPENCLAW_PLUGIN_SPEC.md` 是专门为 OpenClaw 审核者准备的，
包含架构图、API 端点、数据流、安装流程等完整信息。

### 任务 3：后续维护（持续）

- **metaclaw/memory 模块同步**：当主项目的 `metaclaw/memory/` 目录有更新时，
  需要同步到 `sidecar/metaclaw/memory/`。建议后续考虑用 CI 脚本自动同步。
- **版本更新**：更新代码后需要递增 `package.json` 的 version 再 `npm publish`
- **Python 兼容性**：当前要求 Python 3.10+，如果用户环境有问题需要关注

---

## 六、安装验证流程

发布到 npm 后，用以下流程验证安装是否正常：

```bash
# 1. 安装插件
openclaw plugins install @metaclaw/memory

# 2. 初始化（创建 venv、安装 Python 依赖）
openclaw metaclaw setup

# 3. 检查状态
openclaw metaclaw status

# 4. 在 openclaw.json 中启用插件
# {
#   "plugins": {
#     "entries": {
#       "@metaclaw/memory": {
#         "enabled": true,
#         "config": {
#           "autoRecall": true,
#           "autoCapture": true
#         }
#       }
#     },
#     "slots": {
#       "memory": "metaclaw-memory"
#     }
#   }
# }

# 5. 启动 OpenClaw，进行一次对话，验证：
#    - 记忆是否自动注入到提示中
#    - 对话结束后记忆是否被提取
#    - /remember "test" 和 /recall "test" 是否正常

# 6. 验证 CLI 命令
openclaw metaclaw search "test"
openclaw metaclaw upgrade
```

---

## 七、关键文件速查

| 文件 | 说明 |
|------|------|
| `OPENCLAW_PLUGIN_SPEC.md` | 给 OpenClaw 审核者看的技术文档 |
| `docs/QUICK_START.md` | 给用户看的快速上手（英文） |
| `docs/INTEGRATION_GUIDE.md` | 给用户看的详细集成指南（中文） |
| `docs/PUBLISH_GUIDE.md` | 发布策略分析（方案选择已执行完毕） |
| `src/index.ts` | TS 插件入口，所有注册逻辑在这里 |
| `sidecar/metaclaw_memory_sidecar/server.py` | Python sidecar 的所有 API 端点 |
| `sidecar/metaclaw/memory/manager.py` | 记忆系统核心门面类 |

---

## 八、常见问题

**Q: 为什么不直接发布 metaclaw 到 PyPI？**
A: metaclaw 核心包包含训练、RL、API server 等重型依赖（torch/transformers/vllm），
用户只需要 memory 功能。所以我们把 memory 模块内嵌到了 sidecar 内。
详见 `docs/PUBLISH_GUIDE.md` 的方案分析。

**Q: sidecar 的 Python 依赖有哪些？**
A: 只有 `fastapi>=0.100` 和 `uvicorn[standard]>=0.20`。memory 模块本身使用
Python 标准库的 sqlite3 和 dataclasses，不需要额外的 ML 库。

**Q: 如果以后想改成从 PyPI 安装 sidecar 怎么办？**
A: 只需要：(1) 把 `sidecar/` 单独发布到 PyPI 为 `metaclaw-memory-sidecar`，
(2) 修改 `src/commands/cli.ts` 的 setup 命令，从 PyPI 安装而不是本地安装。
两处改动，约 10 行代码。
