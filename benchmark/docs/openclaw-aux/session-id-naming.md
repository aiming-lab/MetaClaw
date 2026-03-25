# Session ID 命名规则与自定义用法

openclaw 默认使用 UUID 作为 session ID，但完全支持自定义可读 ID。

---

## 格式规则

正则（来自 `src/config/sessions/paths.ts`）：

```
/^[a-z0-9][a-z0-9._-]{0,127}$/i
```

- 首字符：字母或数字
- 后续字符：字母、数字、`.`、`_`、`-`
- 总长度：1~128 字符，不区分大小写

## CLI 用法

```bash
openclaw agent --agent ops --session-id 1234 --message "Summarize logs"
```

对应的记录文件路径：

```
~/.openclaw/agents/ops/sessions/1234.jsonl
```

## 优先级逻辑

```
用户传入的 --session-id  >  复用已有 session  >  自动生成 UUID
```

## 合法 ID 示例

| ID | 是否合法 |
|----|---------|
| `1234` | ✅ |
| `my-session` | ✅ |
| `ops.daily_2026` | ✅ |
| `_invalid` | ❌ 不能以 `_` 开头 |
| `a/b` | ❌ 不允许 `/` |
