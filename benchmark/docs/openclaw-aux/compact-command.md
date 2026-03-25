# /compact 命令：原理与 .jsonl 文件变化

> 关键源码：`src/auto-reply/reply/commands-compact.ts`、`src/agents/pi-embedded-runner/compact.ts`、`src/gateway/session-utils.fs.ts`

---

## 命令格式

```
/compact
/compact <自定义压缩指令>   # 例：/compact Focus on decisions made
```

仅授权用户可执行。

---

## .jsonl 文件结构前置说明

**Pi SDK 的 .jsonl 是 parentId 链/DAG，不是简单的平铺列表。**

> 来自 `src/gateway/server-methods/AGENTS.md`：
> "Pi session transcripts are a `parentId` chain/DAG; never append Pi `type: "message"` entries via raw JSONL writes (missing `parentId` can sever the leaf path and break compaction/history). Always write transcript messages via `SessionManager.appendMessage(...)` (or a wrapper that uses it)."

**手动直接写入 .jsonl 会破坏 parentId 链，导致 compaction/历史断裂。**

### 普通消息条目格式

消息条目没有顶层 `type` 字段，而是包在 `message` key 下：

```json
{"message":{"role":"user","content":"Hello"}}
{"message":{"role":"assistant","content":[{"type":"text","text":"Response"}],"api":"openai-responses","provider":"openclaw","model":"claude-sonnet-4-6","usage":{...},"stopReason":"stop","timestamp":1704086400000}}
```

---

## /compact 执行后 .jsonl 新增的内容

执行 `/compact` 后，Pi SDK 通过 `SessionManager.appendCompaction()` 向 .jsonl **追加一行** compaction 条目：

```json
{
  "type": "compaction",
  "id": "comp-1",
  "timestamp": "2026-02-07T00:00:00.000Z",
  "summary": "之前的对话内容摘要...",
  "firstKeptEntryId": "entry-uuid-xyz",
  "tokensBefore": 150000
}
```

### 各字段含义

| 字段 | 类型 | 含义 |
|------|------|------|
| `type` | `"compaction"` | 固定值，标识这是一条压缩记录 |
| `id` | string | 本次压缩的唯一 ID |
| `timestamp` | ISO 时间字符串 | 压缩发生的时间 |
| `summary` | string | 被压缩的旧消息的 AI 生成摘要文本 |
| `firstKeptEntryId` | string | 未被压缩、保留下来的第一条消息的 entryId |
| `tokensBefore` | number | 压缩前的 token 数量 |

---

## compact 前后的 .jsonl 对比

**compact 前：**
```jsonl
{"type":"session","version":1,"id":"550e8400-...","timestamp":"...","cwd":"..."}
{"message":{"role":"user","content":"消息1"}}
{"message":{"role":"assistant","content":[...]}}
{"message":{"role":"user","content":"消息2"}}
{"message":{"role":"assistant","content":[...]}}
... （大量历史消息）
{"message":{"role":"user","content":"消息N"}}
{"message":{"role":"assistant","content":[...]}}
```

**compact 后（旧消息被总结，新增 compaction 条目）：**
```jsonl
{"type":"session","version":1,"id":"550e8400-...","timestamp":"...","cwd":"..."}
{"message":{"role":"user","content":"消息1"}}
... （部分旧消息被 Pi SDK 移除，由 summary 代替）
{"type":"compaction","id":"comp-1","timestamp":"2026-02-07T00:00:00.000Z","summary":"...之前对话的摘要...","firstKeptEntryId":"entry-xyz","tokensBefore":150000}
{"message":{"role":"user","content":"消息N"}}    ← 最近的消息被保留
{"message":{"role":"assistant","content":[...]}}
```

**关键行为**：
- **旧消息不是物理删除**：Pi SDK 通过 DAG parentId 链管理哪些消息"有效"，compaction 条目中的 `firstKeptEntryId` 标记了保留点
- 实际上 .jsonl 仍然保留了原始行，但 Pi SDK 在加载时从 `firstKeptEntryId` 处开始读取历史，旧消息被跳过
- compaction 条目充当"历史分割线"，摘要替代了之前的对话内容

---

## compact 后 sessions.json 的变化

执行完成后，`incrementCompactionCount()` 更新 sessions.json：

```json
{
  "agent:main:+15551234567": {
    "compactionCount": 1,          // ← +1
    "totalTokens": 85000,          // ← 更新为压缩后的 token 数
    "totalTokensFresh": true,      // ← 标记为最新值
    "inputTokens": null,           // ← 清除（只保留总数）
    "outputTokens": null,          // ← 清除
    "updatedAt": 1704090000000
  }
}
```

多次 compact 后 `compactionCount` 累计递增（2、3、4...）。

---

## 执行流程

```
用户发送：/compact [自定义指令]
    ↓
handleCompactCommand()                     # commands-compact.ts
├─ 中止当前运行中的 agent（如有）
├─ 解析自定义指令
└─ compactEmbeddedPiSession()
       ↓
   compactEmbeddedPiSessionDirect()        # pi-embedded-runner/compact.ts
   ├─ 获取写锁（acquireSessionWriteLock）
   ├─ 修复 .jsonl 文件（repairSessionFileIfNeeded）
   ├─ 打开 SessionManager
   ├─ 创建 AgentSession（含模型、工具等）
   ├─ limitHistoryTurns()：按模型限制裁剪历史
   ├─ session.agent.replaceMessages()：设置待压缩消息
   ├─ session.compact(customInstructions)  # Pi SDK 核心调用
   │  ├─ generateSummary()：调用 LLM 生成摘要
   │  └─ SessionManager.appendCompaction()：写入 .jsonl
   ├─ 估算 tokensAfter
   ├─ 触发 after_compaction 钩子
   └─ 返回结果
       ↓
   incrementCompactionCount()              # 更新 sessions.json
       ↓
返回提示：⚙️ Compacted (150000 → 85000 tokens) • Context usage: 85K/200K
```

---

## 自动 compact（auto-compaction）

除手动 `/compact` 外，当 context 接近上限时 Pi SDK 会自动触发压缩，流程相同。
事件类型为 `auto_compaction_start` / `auto_compaction_end`，写入 .jsonl 的 compaction 条目格式完全一致。

---

## Web UI 中的渲染

`src/gateway/session-utils.fs.ts` 在读取 .jsonl 时，遇到 compaction 条目会合成一条特殊的系统消息：

```json
{
  "role": "system",
  "content": [{ "type": "text", "text": "Compaction" }],
  "timestamp": 1704086400000,
  "__openclaw": { "kind": "compaction", "id": "comp-1" }
}
```

Web UI 将其渲染为一条分割线，点击可展开查看摘要内容（见 `export-html/template.js`）。

---

## 关键源码文件

| 文件 | 内容 |
|------|------|
| `src/auto-reply/reply/commands-compact.ts` | `/compact` 命令入口，授权检查，调用 compact |
| `src/agents/pi-embedded-runner/compact.ts` | 核心 compact 逻辑，调用 Pi SDK |
| `src/auto-reply/reply/session-updates.ts` | `incrementCompactionCount()`，更新 sessions.json |
| `src/gateway/session-utils.fs.ts` | 读取 .jsonl，将 compaction 转为 UI 合成消息 |
| `src/gateway/server-methods/AGENTS.md` | **重要警告**：禁止直接写入 .jsonl，必须用 SessionManager |
| `src/agents/pi-embedded-runner/tool-result-truncation.ts` | `appendCompaction()` 调用位置 |
