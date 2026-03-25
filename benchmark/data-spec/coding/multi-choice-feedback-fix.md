# 代码需求：multi_choice per-option feedback 支持

> **前提**：`benchmark-code-requirements.md` 中的全部重构已完成。本文档是增量修复，仅涉及 multi_choice 相关逻辑。

---

## 背景与问题

原有设计中，所有 eval 类型的 `feedback` 均为 `{correct: str, incorrect: str}` 两字段。

multi_choice 的实际语义更复杂：每道题有 5–10 个选项，agent 可能漏选正确项或错选错误项，每种情况都需要针对具体选项的解释。原有 `incorrect` 单字符串无法区分"你漏选了 A（因为 A 是正确的）"和"你错选了 B（因为 B 是错误的）"，训练信号质量差。

---

## 新的 multi_choice feedback 数据结构

```json
"feedback": {
  "correct": "完全正确！",
  "options": {
    "A": "A 正确：这是标准 ISO 8601 格式，含时区偏移。",
    "B": "B 错误：Unix 时间戳是整数，不是 ISO 8601。",
    "C": "C 正确：时区偏移是必须的，不能省略。",
    "D": "D 错误：ISO 8601 要求日期与时间用 T 分隔，不用空格。"
  }
}
```

- `feedback.correct`：仅在精确匹配时使用
- `feedback.options`：每个选项一条解释，key 与 `eval.options` 完全一致
- **file_check 的 `feedback` 结构不变**（仍为 `{correct, incorrect}`）

---

## 需要修改的文件

### 1. `src/infer/infer_cmd.py`

**变更：`_run_group` 中的 inline scoring + feedback 生成逻辑**

当前：
```python
# 伪代码，可能与实际实现略有差异
if inline_score:
    feedback_text = round_record['feedback']['correct']
else:
    feedback_text = round_record['feedback']['incorrect']
```

修改后：multi_choice 和 file_check 的 feedback 生成需分支处理。

新增辅助函数（可放在同文件或 utils 中）：

```python
def _build_multi_choice_feedback(agent_selected: set[str], round_record: dict) -> str:
    """
    生成 multi_choice 的 feedback_text。
    - 精确匹配 → round_record['feedback']['correct']
    - 否则 → 漏选 + 错选的 per-option 解释，按选项字母顺序拼接
    """
    correct = set(round_record['eval']['answer'])
    if agent_selected == correct:
        return round_record['feedback']['correct']

    options_fb = round_record['feedback'].get('options', {})
    lines = []
    for opt in sorted(correct - agent_selected):       # 漏选
        lines.append(f"你漏选了 {opt}：{options_fb.get(opt, '')}")
    for opt in sorted(agent_selected - correct):       # 错选
        lines.append(f"你错选了 {opt}：{options_fb.get(opt, '')}")
    return "\n".join(lines)
```

在 `_run_group` 中调用（替换原有 correct/incorrect 分支）：

```python
rtype = round_record.get('type')
if rtype == 'multi_choice':
    agent_selected = _extract_multi_choice_answer(response_text)   # 已有提取函数
    passed = agent_selected == set(round_record['eval']['answer'])
    feedback_text = _build_multi_choice_feedback(agent_selected, round_record)
elif rtype == 'file_check':
    passed = _run_file_check(round_record, workspace_dir)          # 已有
    feedback_text = round_record['feedback']['correct' if passed else 'incorrect']
```

注意：
- `_extract_multi_choice_answer` 是已有的选项提取函数（`\bbox{X}` 解析），不需修改
- `passed` 仍写入 `infer_result.json` 的 `inline_score` 字段，行为不变

---

### 2. `src/scoring/scoring_cmd.py`

**变更：`_score_multi_choice`**

当前该函数仅返回 `bool`（pass/fail）。为与 infer 端解耦，scoring_cmd 仍独立读取 `infer_result.json` 中的 `inline_score` 字段计算得分，**不需要重新解析 feedback**。

`_score_multi_choice` 函数签名和返回值**不变**，此文件改动最小，仅需确认：
- 读取的是 `inline_score` 字段（由 infer 端写入），而非重新调用 `\bbox` 解析
- 如果目前直接重新解析回复文本，可保持原逻辑（精确匹配 → pass），不受 feedback 结构影响

---

### 3. `src/check/questions_integrity.py`（`QuestionsIntegrityChecker`）

**变更：multi_choice feedback 校验**

当前校验 `feedback.correct` 和 `feedback.incorrect` 两个字段。

修改后，对 multi_choice 类型：
- 必须有 `feedback.correct`（非空字符串）
- 必须有 `feedback.options`（dict，非空）
- `feedback.options` 的 key 集合必须与 `eval.options` 的 key 集合完全一致
- `feedback.options` 每个 value 必须为非空字符串
- **不检查 `feedback.incorrect`**（multi_choice 无此字段）

对 file_check 类型：
- 保持原有校验：`feedback.correct` 和 `feedback.incorrect` 均为非空字符串

---

### 4. `tests/test_scoring.py` 和 `tests/test_check.py`

**变更：更新 fixture 和测试用例**

`test_scoring.py`：
- multi_choice round 的 fixture 数据中，`feedback` 改为新结构（`{correct, options}`）
- 确保现有 multi_choice 评分测试仍通过

`test_check.py`：
- `metaclaw_data` fixture 中的 multi_choice round，`feedback` 改为新结构
- 新增测试：
  - `test_questions_integrity_multi_choice_missing_options_feedback`：`feedback.options` 缺失 → FAILED
  - `test_questions_integrity_multi_choice_options_key_mismatch`：`feedback.options` key 与 `eval.options` 不一致 → FAILED
  - `test_questions_integrity_multi_choice_empty_option_feedback`：某个 `feedback.options[X]` 为空字符串 → FAILED

---

## 不需要修改的文件

- `src/run/run_cmd.py`：pipeline 编排，不涉及 feedback 结构
- `src/check/` 中除 `questions_integrity.py` 外的其他 checker
- `src/check/base.py`、`src/utils.py`、`src/cli.py`

---

## 实现验证

完成后运行：

```bash
conda activate smem
cd /home/xkaiwen/workspace/metaclaw-test/benchmark
python -m pytest tests/ -v
```

预期：所有测试通过，无 regression。
