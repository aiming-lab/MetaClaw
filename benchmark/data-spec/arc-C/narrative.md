# Arc C — 叙事基准（Narrative）

> 本弧真相基准。subagent 造数据时必须读取本文件。

---

## 本弧核心偏好：P3 文件 Metadata 完整性

**精确规则**：见 `data-spec/preferences.md` P3 节。

**核心要求**：agent 生成的所有输出文件必须包含 metadata 块，按文件类型格式不同：

| 文件类型 | 格式 | 最少必填字段 |
|---------|------|------------|
| `.md` / `.txt` | 文件开头 YAML frontmatter | `created_at`（ISO 8601）、`author`、`status` |
| `.json` | 顶层 `meta` 对象 | `created_at`（ISO 8601）、`author`、`status` |
| `.py` | 文件开头模块级 docstring，含 `Meta:` 段 | `created_at`、`author`、`status` |
| `.csv` | 第一行 `# meta: created_at=... author=... status=...` | 同上 |

**P1、P2 仍然有效**：本弧所有输出文件需同时满足 P1（时间格式）、P2（命名规范）、P3（metadata）。

---

## 日期设定

| Day | 日期 | 星期 |
|-----|------|------|
| 11 | 2026-03-30 | 周一 |
| 12 | 2026-03-31 | 周二 |
| 13 | 2026-04-01 | 周三 |
| 14 | 2026-04-02 | 周四 |
| 15 | 2026-04-03 | 周五 |

---

## eval 脚本：check_metadata.py

**存放路径**：`eval/scripts/check_metadata.py`（arc-C 数据创建时一并创建）

**接口**：
```
python eval/scripts/check_metadata.py <filepath> [--type json|md|py|csv]
```

- 若未指定 `--type`，根据文件后缀自动判断
- Exit 0 + `OK`：metadata 完整
- Exit 1 + `FAIL: <说明>`：缺失或不合法

**完整实现**：

```python
#!/usr/bin/env python3
"""check_metadata.py — validate P3 metadata completeness."""
import argparse, json, re, sys

REQUIRED_FIELDS = ['created_at', 'author', 'status']
VALID_STATUSES = {'pending', 'in_progress', 'done'}
ISO_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$')


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_json(path):
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        fail(f"cannot parse JSON: {e}")
    meta = data.get('meta')
    if not meta or not isinstance(meta, dict):
        fail("missing top-level 'meta' object")
    for f in REQUIRED_FIELDS:
        if f not in meta:
            fail(f"meta.{f} is missing")
        if meta[f] is None or meta[f] == '':
            fail(f"meta.{f} is empty")
    if not ISO_PATTERN.match(str(meta.get('created_at', ''))):
        fail(f"meta.created_at is not valid ISO 8601 +08:00: {meta.get('created_at')!r}")
    if meta.get('status') not in VALID_STATUSES:
        fail(f"meta.status must be one of {VALID_STATUSES}, got {meta.get('status')!r}")
    print("OK")
    sys.exit(0)


def check_md(path):
    text = open(path, encoding='utf-8').read()
    if not text.startswith('---'):
        fail("missing YAML frontmatter (file must start with ---)")
    end = text.find('\n---', 3)
    if end == -1:
        fail("YAML frontmatter not closed with ---")
    fm = text[3:end]
    found = {}
    for line in fm.splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            found[k.strip()] = v.strip()
    for f in REQUIRED_FIELDS:
        if f not in found or not found[f]:
            fail(f"frontmatter missing or empty field: {f}")
    if not ISO_PATTERN.match(found.get('created_at', '')):
        fail(f"frontmatter created_at is not valid ISO 8601 +08:00: {found.get('created_at')!r}")
    if found.get('status') not in VALID_STATUSES:
        fail(f"frontmatter status must be one of {VALID_STATUSES}, got {found.get('status')!r}")
    print("OK")
    sys.exit(0)


def check_py(path):
    text = open(path, encoding='utf-8').read()
    # Look for module docstring containing Meta: section
    m = re.search(r'"""(.*?)"""', text, re.DOTALL)
    if not m:
        fail("missing module docstring")
    docstring = m.group(1)
    meta_section = re.search(r'Meta:(.*?)(?:\n\n|\Z)', docstring, re.DOTALL)
    if not meta_section:
        fail("module docstring missing 'Meta:' section")
    meta_text = meta_section.group(1)
    found = {}
    for line in meta_text.splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            found[k.strip().lower()] = v.strip()
    for f in REQUIRED_FIELDS:
        if f not in found or not found[f]:
            fail(f"Meta section missing or empty field: {f}")
    if not ISO_PATTERN.match(found.get('created_at', '')):
        fail(f"Meta created_at is not valid ISO 8601 +08:00: {found.get('created_at')!r}")
    print("OK")
    sys.exit(0)


def check_csv(path):
    first_line = open(path, encoding='utf-8').readline().strip()
    if not first_line.startswith('# meta:'):
        fail("first line must be '# meta: created_at=... author=... status=...'")
    meta_str = first_line[len('# meta:'):].strip()
    found = {}
    for part in meta_str.split():
        if '=' in part:
            k, _, v = part.partition('=')
            found[k.strip()] = v.strip()
    for f in REQUIRED_FIELDS:
        if f not in found or not found[f]:
            fail(f"meta comment missing field: {f}")
    if not ISO_PATTERN.match(found.get('created_at', '')):
        fail(f"meta created_at is not valid ISO 8601 +08:00: {found.get('created_at')!r}")
    print("OK")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath')
    parser.add_argument('--type', choices=['json', 'md', 'py', 'csv'], default=None)
    args = parser.parse_args()
    ftype = args.type or args.filepath.rsplit('.', 1)[-1].lower()
    dispatch = {'json': check_json, 'md': check_md, 'txt': check_md,
                'py': check_py, 'csv': check_csv}
    fn = dispatch.get(ftype)
    if not fn:
        fail(f"unsupported file type: {ftype}")
    fn(args.filepath)


if __name__ == '__main__':
    main()
```

---

## 各天领域与 P3 表现

| Day | 领域 | P3 触发场景 | P3 格式类型 |
|-----|------|------------|------------|
| 11 | 文档写作 | 周报、会议纪要（Markdown）| YAML frontmatter |
| 12 | 数据处理 | 分析报告、指标文件（JSON）| `meta` 对象 |
| 13 | 代码工程 | Python 工具脚本 | 模块 docstring Meta 段 |
| 14 | 项目管理 | P1+P2+P3 联合：PM 文档需满足三个规则 | 混合 |
| 15 | 综合 | 最复杂：多种文件类型，三个规则全部出现 | 混合 |

---

## 预期 P3 失败方式

- JSON 文件：有内容对象但缺少顶层 `meta` 字段
- Markdown 文件：直接从正文开始，没有 YAML frontmatter
- Python 文件：有 docstring 但没有 `Meta:` 段
- meta 字段不完整：有 `meta` 对象但缺少 `created_at` 或 `author` 或 `status`
- `status` 值非法：写了 "complete"、"finished" 而不是 "done"

---

## 语言约束

**所有数据内容必须用英文**：session JSONL 消息、workspace 文件内容、question/feedback 文本、multi_choice 选项。

---

## 造数据约束

1. question 中不得出现 "metadata"、"frontmatter"、"meta field" 等提示词
2. workspace 预置文件（参考材料）可以没有 metadata；只有 agent 生成的输出需要 metadata
3. `feedback.incorrect` 必须给出完整正确的 metadata 格式示例（这是训练信号）
4. P1、P2 规则同样适用：输出文件需同时满足命名规范和时间格式
