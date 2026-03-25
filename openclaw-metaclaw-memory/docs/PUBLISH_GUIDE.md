# MetaClaw Memory 插件发布指南

> 这份文档是给项目维护者看的，说明要让用户能通过
> `openclaw plugins install @metaclaw/memory` 安装并使用本插件，
> 具体需要做哪些事情。

---

## 当前状态

插件代码已全部完成，TypeScript 编译通过，sidecar 全部端点已验证。
但从"代码完成"到"用户能装上"，中间还有一段发布流程要走。

---

## 核心问题：Python 依赖链

安装链路：

```
用户执行 openclaw plugins install @metaclaw/memory
  → npm 下载安装 TS 插件（包含 sidecar/ 目录）      ← 需要 npm 上有包
  → 用户执行 openclaw metaclaw setup
    → 创建 Python venv
    → pip install metaclaw-memory-sidecar           ← 需要能安装成功
      → 依赖 metaclaw 核心包                         ← 关键断点
```

**关键断点**：sidecar 的 Python 代码依赖 `metaclaw` 包，具体导入了：

```python
from metaclaw.config import MetaClawConfig                    # 154 行的 dataclass
from metaclaw.memory.manager import MemoryManager              # metaclaw/memory/ 下
from metaclaw.memory.models import MemoryType, MemoryUnit, ... # 共 18 个文件，~10000 行
from metaclaw.memory.consolidator import MemoryConsolidator
from metaclaw.memory.upgrade_worker import MemoryUpgradeWorker
```

好消息：`metaclaw/memory/` 模块是**完全自包含**的，不依赖 `metaclaw` 的其他模块
（不依赖 trainer、rollout、skill_manager 等）。唯一的外部依赖是 `metaclaw/config.py`
这一个文件（MetaClawConfig dataclass）。

---

## 方案选择

### 方案 A：将 memory 模块打包进 sidecar（推荐）

**做法**：把 `metaclaw/memory/` 和 `metaclaw/config.py` 复制到 sidecar 包内，
让 sidecar 完全自包含，不再依赖外部的 `metaclaw` 包。

```
sidecar/
├── metaclaw_memory_sidecar/
│   ├── server.py
│   ├── config.py
│   └── ...
├── metaclaw/                    ← 从主项目复制
│   ├── __init__.py
│   ├── config.py                ← MetaClawConfig (154 行)
│   └── memory/                  ← 整个 memory 子包 (~10000 行)
│       ├── __init__.py
│       ├── manager.py
│       ├── store.py
│       ├── models.py
│       └── ... (18 个文件)
└── pyproject.toml               ← 删除 "metaclaw" 依赖
```

**优点**：
- 用户不需要单独安装 metaclaw —— setup 一键完成
- npm 包自包含，离线也能装
- 不需要发布 metaclaw 到 PyPI
- sidecar/ 已经在 npm 的 `files` 字段里，会随 npm 包一起分发

**缺点**：
- metaclaw/memory 存在两份代码（主项目和 sidecar 内各一份）
- 主项目 memory 模块更新后，需要同步到 sidecar

**工作量**：约 30 分钟

### 方案 B：发布 metaclaw 到 PyPI

**做法**：给整个 metaclaw 项目写 pyproject.toml，发布到 PyPI。

**优点**：
- 干净，没有代码重复
- metaclaw 作为独立包可被其他项目复用

**缺点**：
- metaclaw 核心包包含训练、RL、API server 等大量模块，依赖链很重
  （torch、transformers、vllm 等）
- 用户只需要 memory 功能，却要装整个 metaclaw
- 发布到 PyPI 是个大决策，需要维护版本、处理向后兼容

**工作量**：1-2 小时 + 持续维护

### 方案 C：只发布 metaclaw-memory 子包到 PyPI

**做法**：把 `metaclaw/memory/` + `metaclaw/config.py` 作为独立的
`metaclaw-memory` 包发布到 PyPI。

**优点**：
- 轻量，只包含 memory 相关代码
- 没有 torch 等重依赖
- sidecar 的 pyproject.toml 依赖 `metaclaw-memory` 而非 `metaclaw`

**缺点**：
- 需要维护一个额外的 PyPI 包
- 需要处理版本同步

**工作量**：1 小时 + 持续维护

---

## 推荐方案：A（打包进 sidecar）

对于当前阶段（v0.1.0，首次发布），方案 A 是最务实的选择：
- 零外部依赖，用户体验最好
- 不需要任何 PyPI 发布
- 以后想切换到方案 B 或 C 随时可以

---

## 具体执行步骤

### 第一步：将 memory 模块打包进 sidecar

```bash
# 在 sidecar/ 目录下创建 metaclaw 包的副本
mkdir -p openclaw-metaclaw-memory/sidecar/metaclaw/memory
cp metaclaw/__init__.py  openclaw-metaclaw-memory/sidecar/metaclaw/
cp metaclaw/config.py    openclaw-metaclaw-memory/sidecar/metaclaw/
cp metaclaw/memory/*.py  openclaw-metaclaw-memory/sidecar/metaclaw/memory/
```

然后修改 `sidecar/pyproject.toml`，删除 `"metaclaw"` 依赖：

```toml
dependencies = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
    # 不再需要 "metaclaw" —— 已内嵌
]
```

### 第二步：修改 setup 命令，从本地安装 sidecar

当前 `src/commands/cli.ts` 中：
```typescript
execSync(`"${pip}" install --upgrade metaclaw-memory-sidecar`)  // ← 从 PyPI 装
```

改为：
```typescript
const sidecarDir = resolve(dirname(fileURLToPath(import.meta.url)), "../../sidecar")
execSync(`"${pip}" install --upgrade "${sidecarDir}"`)  // ← 从本地装
```

这样 setup 命令会直接从 npm 包内的 `sidecar/` 目录安装。

### 第三步：修改 sidecar.ts，优先使用 venv Python

当前 `src/sidecar.ts` 使用 `config.pythonPath`（系统 Python）。
应该优先使用 setup 创建的 venv：

```typescript
const venvPython = resolve(homedir(), ".openclaw/plugins/@metaclaw/memory/.venv/bin/python")
const python = existsSync(venvPython) ? venvPython : this.config.pythonPath
```

### 第四步：构建并验证

```bash
cd openclaw-metaclaw-memory
npm run build              # TypeScript 编译
npm pack --dry-run         # 检查打包内容（应包含 dist/ + sidecar/ + openclaw.plugin.json）
```

### 第五步：发布到 npm

```bash
# 需要 npm 账号 + @metaclaw scope 权限
npm login
npm publish --access public
```

发布后用户即可：
```bash
openclaw plugins install @metaclaw/memory
openclaw metaclaw setup     # 自动从本地 sidecar/ 目录安装 Python 环境
openclaw metaclaw status    # 验证
```

### 第六步：（可选）向 OpenClaw 社区提交

在 OpenClaw 的 GitHub 仓库提交 PR，将插件添加到
[Community Plugins](https://docs.openclaw.ai/plugins/community) 页面。

---

## 完整执行清单

| # | 任务 | 类型 | 状态 |
|---|------|------|------|
| 1 | 将 `metaclaw/memory/` + `config.py` 复制到 `sidecar/metaclaw/` | 代码 | ✅ |
| 2 | 修改 `sidecar/pyproject.toml` 删除 `metaclaw` 依赖 | 代码 | ✅ |
| 3 | 修改 `src/commands/cli.ts` setup 从本地安装 sidecar | 代码 | ✅ |
| 4 | 修改 `src/sidecar.ts` 优先使用 venv Python | 代码 | ✅ |
| 5 | 验证 sidecar 能独立启动（不依赖外部 metaclaw） | 测试 | ✅ |
| 6 | TypeScript 编译通过 | 测试 | ✅ |
| 7 | `npm pack --dry-run` 确认打包内容 | 测试 | ✅ |
| 8 | 注册 npm 账号 + @metaclaw scope | 发布 | ⬜ |
| 9 | `npm publish --access public` | 发布 | ⬜ |
| 10 | 在 OpenClaw 社区提交 PR | 推广 | ⬜ |

其中 #1-7 是我（AI）可以帮你执行的，#8-9 需要你自己操作 npm 账号，#10 需要你提交 PR。

---

## 发布后的用户体验

```bash
# 安装（一行命令）
openclaw plugins install @metaclaw/memory

# 初始化（一行命令 — 自动创建 venv，从本地安装 Python 依赖）
openclaw metaclaw setup

# 配置（在 openclaw.json 中加两行）
# "metaclaw-memory": { "enabled": true }
# "slots": { "memory": "metaclaw-memory" }

# 使用（全自动）
# - 每次对话自动注入相关记忆
# - 每次对话结束自动提取记忆
# - /remember, /recall 随时手动操作
```
