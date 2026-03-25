# Arc B — 叙事基准（Narrative）

> 本弧真相基准。subagent 造数据时必须读取本文件。

---

## 本弧核心偏好：P2 文件命名规范

**精确规则**：见 `data-spec/preferences.md` P2 节。

**核心要求**：所有 agent 生成的输出文件命名格式为 `YYYYMMDD_<描述>.<ext>`，描述部分 snake_case，全小写。

**合法示例**：`20260323_sprint8_report.json`、`20260324_api_changelog.md`、`20260325_metrics_summary.csv`

**非法示例**：`report.json`、`SprintReport.json`、`sprint-report-2026-03-23.json`、`sprint_report_20260323.json`（日期不在最前面）、`20260323-sprint-report.json`（用了连字符而非下划线）

**验证 regex**：`^\d{8}_[a-z][a-z0-9_]*\.[a-z0-9]+$`

**P1 仍然有效**：本弧所有涉及时间字段的文件，同样需要符合 P1 规则（ISO 8601 +08:00）。

---

## 日期设定

| Day | 日期 | 星期 |
|-----|------|------|
| 06 | 2026-03-23 | 周一 |
| 07 | 2026-03-24 | 周二 |
| 08 | 2026-03-25 | 周三 |
| 09 | 2026-03-26 | 周四 |
| 10 | 2026-03-27 | 周五 |

---

## eval 脚本：check_filename.py

**存放路径**：`eval/scripts/check_filename.py`（arc-B 数据创建时一并创建）

**接口**：
```
# 模式一：目录扫描
python eval/scripts/check_filename.py --dir <directory> --ext <ext> [--min-count N]

# 模式二：单文件检查
python eval/scripts/check_filename.py <filepath>
```

- 模式一：扫描目录，检查是否存在 N 个（默认 1）符合 P2 命名模式且后缀为 ext 的文件
- 模式二：检查指定文件的 basename 是否符合 P2 命名模式
- Exit 0 + stdout `OK`：通过
- Exit 1 + stdout `FAIL: <说明>`：不通过

**完整实现**（subagent 按此创建脚本）：

```python
#!/usr/bin/env python3
"""check_filename.py — validate P2 file naming convention."""
import argparse, os, re, sys

PATTERN = re.compile(r'^\d{8}_[a-z][a-z0-9_]*\.[a-z0-9]+$')


def check_file(path):
    basename = os.path.basename(path)
    if PATTERN.match(basename):
        print("OK")
        sys.exit(0)
    else:
        print(f"FAIL: '{basename}' does not match YYYYMMDD_snake_case.ext pattern")
        sys.exit(1)


def check_dir(directory, ext, min_count):
    if not os.path.isdir(directory):
        print(f"FAIL: directory not found: {directory}")
        sys.exit(1)
    ext_lower = ext.lstrip('.').lower()
    matches = [
        f for f in os.listdir(directory)
        if PATTERN.match(f) and f.rsplit('.', 1)[-1].lower() == ext_lower
    ]
    if len(matches) >= min_count:
        print(f"OK ({len(matches)} matching file(s): {', '.join(sorted(matches))})")
        sys.exit(0)
    else:
        print(f"FAIL: expected >= {min_count} P2-compliant .{ext_lower} file(s) in {directory}, found {len(matches)}")
        sys.exit(1)


def main():
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('--'):
        check_file(sys.argv[1])
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True)
    parser.add_argument('--ext', required=True)
    parser.add_argument('--min-count', type=int, default=1)
    args = parser.parse_args()
    check_dir(args.dir, args.ext, args.min_count)


if __name__ == '__main__':
    main()
```

---

## 各天领域与 P2 表现

| Day | 领域 | P2 触发场景 | 延续 P1 的字段 |
|-----|------|------------|--------------|
| 06 | 代码工程 | 构建报告、测试结果、变更记录文件 | 时间字段（created_at 等）|
| 07 | 文档写作 | 周报、邮件草稿、会议纪要 | 会议时间、截止日期 |
| 08 | 数据处理 | 分析报告、数据摘要、指标导出 | 数据时间戳、报告生成时间 |
| 09 | 项目管理 | P1+P2 联合：PM 文档（时间字段 + 命名规范均需正确）| 全部时间字段 |
| 10 | 综合（sprint 收尾）| P1+P2 最复杂场景，多类型文件 | 全部时间字段 |

---

## 预期 P2 失败方式

- 直接使用语义名称：`test_report.json`、`changelog.md`、`metrics.csv`
- 日期格式错误：`2026-03-23_report.json`（连字符）、`report_20260323.json`（日期不在最前）
- 大写或驼峰：`SprintReport.json`、`TestResults.json`
- 连字符替代下划线：`20260323-sprint-report.json`

---

## 语言约束

**所有数据内容必须用英文**：session JSONL 消息、workspace 文件内容、question/feedback 文本、multi_choice 选项。

---

## 造数据约束

1. 任务描述（question）中不得出现 `YYYYMMDD`、"underscore"、"snake_case"、"naming convention" 等提示词
2. 任务描述只说"保存到 dayXX/ 目录下"，不指定文件名
3. `feedback.incorrect` 必须给出正确命名示例（如 `20260323_test_report.json`），这是最重要的训练信号
4. 同一天的 workspace 预置文件（只读参考材料）可以用普通名称，只有 agent 生成的输出文件需要遵循 P2
5. P1 规则同样适用：含时间字段的文件需同时满足 P1 和 P2
