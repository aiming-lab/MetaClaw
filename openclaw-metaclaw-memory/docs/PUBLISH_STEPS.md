# MetaClaw Memory 插件发布到 OpenClaw 操作步骤

---

## 前置条件

- Node.js 18+
- npm 账号（在 https://www.npmjs.com 注册）
- 拥有 `@metaclaw` scope 的发布权限（见步骤一）

---

## 步骤一：创建 npm 组织

如果 `@metaclaw` 这个 scope 还没有在 npm 上注册：

1. 登录 https://www.npmjs.com
2. 点击头像 → Add Organization
3. 组织名填 `metaclaw`
4. 选择免费计划（公开包）

如果你不打算用 `@metaclaw` scope，可以把 `package.json` 中的 `name` 改为不带 scope 的名字，比如 `openclaw-metaclaw-memory`，跳过此步骤。

---

## 步骤二：登录 npm

```bash
npm login
```

按提示输入用户名、密码、邮箱、OTP（如果开了双因素认证）。

---

## 步骤三：构建

```bash
cd openclaw-metaclaw-memory
npm run build
```

确认 `dist/` 目录中生成了编译后的 `.js` 文件。

---

## 步骤四：检查打包内容

```bash
npm pack --dry-run
```

确认输出中包含以下内容：
- `dist/` — 编译后的 TypeScript
- `sidecar/` — Python sidecar（含内嵌的 metaclaw/memory 模块）
- `openclaw.plugin.json` — 插件清单
- `package.json`

总文件数约 67 个，包大小约 100 kB。

如果看到 `__pycache__` 或 `.pyc` 文件，说明打包配置有问题，需要检查 `.npmignore`。

---

## 步骤五：发布

```bash
npm publish --access public
```

`--access public` 是必须的，因为 scoped 包默认是私有的。

发布成功后会看到类似输出：
```
+ @metaclaw/memory@0.1.0
```

---

## 步骤六：验证安装

在一台干净的机器上（或新目录下）执行：

```bash
# 安装插件
openclaw plugins install @metaclaw/memory

# 初始化 Python 环境（自动创建 venv 并安装依赖）
openclaw metaclaw setup

# 检查是否正常运行
openclaw metaclaw status
```

---

## 步骤七：配置 OpenClaw

在项目的 `openclaw.json` 中添加：

```json
{
  "plugins": {
    "entries": {
      "@metaclaw/memory": {
        "enabled": true,
        "config": {
          "autoRecall": true,
          "autoCapture": true
        }
      }
    },
    "slots": {
      "memory": "metaclaw-memory"
    }
  }
}
```

启动 OpenClaw 后进行一次对话，确认：
- 对话中能看到记忆被注入（auto-recall 生效）
- 对话结束后记忆被提取（auto-capture 生效）
- `/remember 测试内容` 和 `/recall 测试` 命令正常工作

---

## 步骤八（可选）：提交到 OpenClaw 社区插件列表

1. Fork OpenClaw 的文档仓库
2. 在 Community Plugins 页面添加一条记录
3. 提交 PR

可以附上 `OPENCLAW_PLUGIN_SPEC.md` 作为技术说明供审核者参考。

---

## 后续版本更新

修改代码后：

```bash
# 1. 递增版本号
npm version patch   # 0.1.0 → 0.1.1

# 2. 重新构建
npm run build

# 3. 发布
npm publish --access public
```
