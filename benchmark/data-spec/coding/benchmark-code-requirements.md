# Benchmark 代码改造需求文档

> 目标：在现有 `benchmark/src` 代码基础上，支持 MetaClaw Evolution Benchmark 的数据格式，
> 主要新增：per-scenario workspace 隔离、feedback 注入机制、`file_check` 类型的内联评分。
>
> **关键路径**（绝对路径）：
> - 代码目录：`/home/xkaiwen/workspace/metaclaw-test/benchmark/src/`
> - 本文档：`/home/xkaiwen/workspace/metaclaw-test/data-spec/benchmark-code-requirements.md`
> - 数据格式定义：`/home/xkaiwen/workspace/metaclaw-test/data-spec/data-structure.md`
> - 测试数据目录（尚未创建）：`/home/xkaiwen/workspace/metaclaw-test/benchmark/data/metaclaw-bench/`

---

## 现有架构概述

```
run_cmd.py
  ├─ infer_cmd._run_one_all_tests()       # 一个 all_tests.json 的完整流程
  │    ├─ _prepare_work_copy()            # 复制 openclaw_state + workspace（全局一次）
  │    ├─ _run_group()                    # 串行执行一组 rounds
  │    │    ├─ _format_query()            # 拼接问题文本
  │    │    ├─ _run_question()            # 调用 openclaw agent CLI，保存 infer_result.json
  │    │    └─ _execute_update()          # 执行 round.update 操作
  │    └─ gateway 管理
  ├─ scoring_cmd.run_scoring()            # 遍历 infer_result.json，写 scoring.json
  └─ report_cmd.run_report()              # 汇总 scoring.json，生成 report.json/md
```

**关键现状问题**：
1. `_prepare_work_copy` 对整次 run 只创建一份 workspace 副本，30 个 scenario 共用
2. 无 feedback 注入：`_run_group` 不知道上一轮是否答对，不修改下一轮的 query
3. `file_check` 类型完全未实现（query_reader、infer、scoring 均只处理 multi_choice）

---

## 改动清单

### 1. `query_reader.py`

**位置**：`src/infer/query_reader.py`

#### 1.1 扩展 `RoundRecord`

新增字段（均可选，保持向后兼容）：

```python
class RoundRecord(TypedDict, total=False):
    id: str
    type: str
    question: str
    update: list
    feedback: dict       # {"correct": str, "incorrect": str}
    eval: dict           # {"options": ..., "answer": ...} 或 {"command": str, ...}
```

`options` 和 `answer` 从 RoundRecord 删除，scoring 和 query 逻辑全部从 `eval` 子对象读取。

#### 1.2 `QuestionsJsonQueryReader.read_queries`

读取每个 round 时，额外透传 `feedback` 和 `eval` 字段（如果存在）：

```python
if "eval" in r:
    rec["eval"] = r["eval"]
if "feedback" in r:
    rec["feedback"] = r["feedback"]
```

---

### 2. `infer_cmd.py`

**位置**：`src/infer/infer_cmd.py`

#### 2.1 新增：per-scenario workspace 副本

**问题**：当前 `_prepare_work_copy` 对全部 scenario 只创建一份 workspace 副本。MetaClaw bench 中每个 scenario 运行后 agent 会写文件到 workspace，后续 scenario 不应看到前者的写入。

**方案**：在 `_run_one_all_tests` 中，将 workspace 副本的创建从"全局一次"改为"per-test"。

具体做法：`_prepare_work_copy` 只复制 openclaw_state，不复制 workspace；workspace 由调用方按 test 创建。在 `_run_one_all_tests` 的 test 遍历循环内，为每个 test 单独复制 workspace，并将路径写入该次 run 的 `openclaw.json`（agent 的 `workspace` 字段）。

`all_tests.json` 新增字段 `workspace_src`（见数据结构文档）。处理逻辑：
1. 读取 `all_tests["workspace_src"]` 作为源目录（展开 `${SIMPLEMEM_ROOT}`）
2. 对每个 test 创建副本：`work_dir/workspace_<test_id>_<run_id>/`
3. 在该 test 运行前，将 `openclaw.json` 中该 agent 的 `workspace` 字段更新为副本路径

`workspace_src` 为必填字段，不存在则报错退出。

#### 2.2 新增：inline `file_check` 执行

新增函数 `_run_file_check(eval_cfg: dict, workspace: Path, timeout: float = 30.0) -> dict`：

- 在 `workspace` 目录下执行 `eval_cfg["command"]`（shell 命令）
- 对比 `eval_cfg.get("expect_exit", 0)` 和实际 exit code
- 若 `eval_cfg.get("expect_stdout")` 存在，检查 stdout 是否包含该字符串（`expect_stdout_regex=True` 时用正则）
- 返回：`{"passed": bool, "exit_code": int, "stdout": str, "stderr": str}`
- 执行超时（默认 30s，可由 `eval_cfg.get("timeout", 30)` 覆盖）后 `passed=False`

**执行环境要求**：在 workspace 目录下运行，`cwd=workspace`；不需要额外的网络隔离（沙箱），依赖调用方保证。

#### 2.3 修改：`_run_group` — feedback 注入 + inline scoring

这是最核心的改动。`_run_group` 现在需要：

1. 维护一个 `prev_round_passed: bool | None = None`（第一轮为 None）
2. 对每轮 round，**先拼接 feedback**（如果 `prev_round_passed is not None` 且本轮 round 有前一轮的 feedback 文本）：
   ```
   query = "[上一步反馈] {feedback_text}\n\n{question_text}"
   ```
   其中 `feedback_text` 取自**上一轮**的 `round_record["feedback"]["correct" or "incorrect"]`
3. 运行 `_run_question`
4. **立即做 inline scoring**，得到 `passed: bool`：
   - `multi_choice`：从 stdout 提取 `\bbox{}` 与 `round_record["eval"]["answer"]` 对比
   - `file_check`：调用 `_run_file_check(round_record["eval"], workspace_path)`
   - inline scoring 仅用于确定 feedback 模板；**不写 scoring.json**，scoring.json 仍由后续 `scoring_cmd` 负责
5. 将 inline scoring 结果写入 `infer_result.json` 的新字段 `"inline_score": {"passed": bool, ...}`
6. 更新 `prev_round_passed = passed`，供下轮使用
7. **最后一轮结束后**，如果该轮有 `feedback` 字段且值非空，发送一条无需回复的 standalone feedback 消息：
   - 消息内容：`"[上一步反馈] {feedback_text}"`（取最后一轮的 feedback），仅作反馈不发送问题
   - 调用 `_run_openclaw_agent` 发送，返回值不计入结果（忽略答案，不保存 infer_result.json）

**`_run_group` 新增参数**：`workspace_path: Path`（当前 test 的 workspace 副本路径，用于 `file_check` 执行）

**Feedback 文本来源规则**：
- Round `r_k` 执行完毕后，`prev_round_passed` 确定
- Round `r_{k+1}` 的 query 开头加：`r_k["feedback"]["correct"]` 或 `r_k["feedback"]["incorrect"]`
- 若 `r_k` 没有 `feedback` 字段，或对应 correct/incorrect 值为空字符串，则不注入
- 最后一轮的 feedback standalone 消息同理，空字符串则跳过

#### 2.4 修改：`_run_question` — 保存 inline_score

`infer_result.json` 增加 `inline_score` 字段（可选）。`_run_question` 签名不变；`_run_group` 在 `_run_question` 返回后读取 result_path、追加 `inline_score` 字段再写回文件。

#### 2.5 修改：`_run_one_all_tests` — 传递 workspace_path

在遍历 test 的循环中，为每个 test 准备 workspace 副本，将路径传入 `_run_group`。

**并发限制**：per-test workspace 方案通过直接 patch `openclaw.json` 的 `workspace` 字段实现，多个 test 并发时会竞争同一文件。`workers` 参数强制固定为 1，在 `_run_one_all_tests` 入口忽略传入值并打印提示。MetaClaw bench 本身需要串行执行，此限制符合实际使用。

---

### 3. `scoring_cmd.py`

**位置**：`src/scoring/scoring_cmd.py`

#### 3.0 `_find_correct_answer`：从 `eval` 子对象读取

`multi_choice` 的 `options` 和 `answer` 统一从 `round_rec["eval"]` 读取：
- `answer`：`round_rec["eval"]["answer"]`
- `q_num`：`len(round_rec["eval"].get("options", {}))`

旧的 `round_rec.get("answer")` / `round_rec.get("options")` 读取路径全部删除。

#### 3.1 `_score_round`：新增 `file_check` 分支

`file_check` 的 scoring 在 inference 阶段已完成（`inline_score.passed`）。scoring_cmd 只需读取：

```python
def _score_file_check(infer_result: dict) -> dict:
    inline = infer_result.get("inline_score", {})
    passed = inline.get("passed", False)
    return {
        "extracted_answer": None,
        "correct_answer": None,
        "score": 1.0 if passed else 0.0,
        "metrics": {"passed": passed},
    }
```

在 `_score_one` 中，传入完整 `infer_result` 而不仅仅是 `answer_text`，以便 `file_check` 分支能读取 `inline_score`。

#### 3.2 `_find_correct_answer`：`file_check` 类型处理

`file_check` 没有 `answer` 字段，`q_num=0`，函数应识别 `type=file_check` 并返回 `(None, 0, "file_check")`，不报错。

#### 3.3 `_score_one`：传入完整 infer_result

将 `infer_result` 传递给 `_score_round`，让 `file_check` 分支可以读取 `inline_score`：

```python
scored = _score_round(question_type, answer_text, correct_raw, q_num, infer_result=result)
```

`_score_round` 签名增加可选参数 `infer_result: dict | None = None`。

---

### 4. `report_cmd.py`

**不需要修改**。现有报告逻辑读取 `scoring.json` 的 `score` 字段（0/1 float），`file_check` 返回的格式完全兼容。`metrics` 只有 `passed` 一个 bool 字段，`_extract_metrics` 已处理 bool→0/1 转换。

---

## 数据流总结（改造后）

```
all_tests.json (含 workspace_src)
  └─ _run_one_all_tests
       ├─ _prepare_work_copy(openclaw_state)          # 全局一次，不含 workspace
       └─ for each test:
            ├─ copy workspace_src → workspace_<test_id>/   # per-test workspace
            ├─ patch openclaw.json[agent.workspace]
            └─ _run_group(workspace_path=...)
                 ├─ round r1:  query = question
                 │              _run_question → infer_result.json
                 │              inline_score → write back to infer_result.json
                 │              prev_passed = inline_score.passed
                 │
                 ├─ round r2:  query = "[上一步反馈] {r1.feedback[prev_passed]}\n\n{question}"
                 │              _run_question → infer_result.json
                 │              inline_score → write back
                 │              ...
                 │
                 └─ after last round:
                      send standalone feedback message (no result saved)

  └─ scoring_cmd:
       multi_choice → extract \bbox{} → compare answer  (unchanged)
       file_check   → read inline_score.passed from infer_result.json

  └─ report_cmd: unchanged
```

---

## 新增/修改文件汇总

| 文件 | 改动性质 |
|------|---------|
| `src/infer/query_reader.py` | 修改：RoundRecord 删除 options/answer，新增 feedback/eval；read_queries 透传新字段 |
| `src/infer/infer_cmd.py` | 修改：删除 `_format_query`，per-test workspace 副本，feedback 注入，file_check inline 执行，workers 固定为 1 |
| `src/scoring/scoring_cmd.py` | 修改：答案从 eval 子对象读取，新增 file_check 分支 |
| `src/check/` | 修改：删除 7 个旧 checker，保留并适配 4 个，新增 4 个（见第 5 节）|
| `src/report/report_cmd.py` | 不改 |
| `src/run/run_cmd.py` | 不改 |
| `pyproject.toml` | 修改：入口点改为 metaclaw-bench |
| `docs/CLI.md` | 全量重写 |
| `tests/test_check.py` | 修改：删除旧 checker 测试，新增新 checker 测试 |
| `tests/test_infer.py` | 修改：新增 feedback 注入、file_check、workspace 副本测试 |
| `tests/test_scoring.py` | 修改：新增 file_check 分支测试，旧 options 顶层读取测试删除 |

---

## 注意事项

1. **断点续跑与 inline_score**：若 `infer_result.json` 已存在且含 `inline_score` 字段，则跳过该轮（agent 调用和命令执行均不重复），直接从 `inline_score.passed` 读取结果继续构建 feedback。若 `infer_result.json` 存在但缺少 `inline_score`（上次中断在 agent 调用之后、inline scoring 之前），则补跑 inline scoring。

2. **最后一轮 standalone feedback 的发送时机**：必须在 `_run_group` 的最后一轮 inline scoring 完成后再发送，以确定用哪个 feedback 模板。

3. **Workspace 副本路径**：`_run_group` 需要知道当前 test 的 workspace 路径用于 `file_check` 执行。该路径来自 `openclaw.json` patch 后的 `agent.workspace`，或由 `_run_one_all_tests` 直接传入。

4. **`eval/scripts/` 路径**：`file_check` 的 `command` 字段路径相对于 workspace 根目录。预置脚本（来自 `eval/scripts/`）应在运行前通过 workspace 副本初始化阶段复制进去（可在 `_run_one_all_tests` 中，每次创建 workspace 副本时自动将 `eval_dir/scripts/` 内容复制到 `workspace/scripts/`）。

---

### 5. check 命令改造

**位置**：`src/check/`

MetaClaw bench 的数据结构与原 CALMB-New 完全不同。现有 11 个 checker 中，多数检查 CALMB 特有格式（6 行 session 结构、固定 assistant 模板、复杂 update 链等），对 MetaClaw bench 均不适用。

### 5.1 废弃的 checker（直接删除）

| 文件 | 原因 |
|------|------|
| `main_session_structure.py` | CALMB 专有的 6 行 session 格式，MetaClaw 不适用 |
| `user_message.py` | 检查 CALMB 特定 user 消息模板，不适用 |
| `assistant_reply.py` | 检查 CALMB 特定 assistant 回复模板，不适用 |
| `deep_structure.py` | 检查 timestamp 链、parentId 等 CALMB 内部格式，不适用 |
| `update_session.py` | MetaClaw bench 不使用 update 字段 |
| `session_registration.py` | MetaClaw 不使用 sessions.json 注册机制 |
| `cross_reference.py` | 原有逻辑检查 update source/path 交叉引用，不适用 |

### 5.2 保留并适配的 checker

| 文件 | 改动 |
|------|------|
| `basic_integrity.py` | 改为检查 MetaClaw all_tests.json 必需字段（新增 `workspace_src`，移除对 history_sessions/update 的检查） |
| `id_consistency.py` | 简化：只验证 test 内 agent/session/eval 字段互相一致；移除 sessions.json key 格式检查 |
| `file_format.py` | 保留，补充对 questions.json 的 JSON 有效性检查 |
| `directory_structure.py` | 改为检查 MetaClaw 目录结构：`workspace_src/`、`eval/dayXX/`、`openclaw_state/agents/<agent>/sessions/` |

### 5.3 新增 checker

**`questions_integrity.py` — QuestionsIntegrityChecker**

验证每个 `eval/dayXX/questions.json` 的内容正确性：

- 顶层必须有 `id`、`rounds` 字段，`rounds` 非空
- 每个 round 必须有：`id`、`type`、`question`、`feedback`、`eval`
- `type` 只能是 `multi_choice` 或 `file_check`
- `feedback.correct` 和 `feedback.incorrect` 均为非空字符串
- `type=multi_choice` 时：`eval.options` 为 dict 且至少 2 项，`eval.answer` 为字符串或数组且所有选项字母均在 `eval.options` 的 key 中
- `type=file_check` 时：`eval.command` 为非空字符串，`eval.expect_exit` 若存在则为整数
- round id 在同一 questions.json 内唯一
- round 数量：< 5 给 warning，> 20 给 warning

**`workspace_integrity.py` — WorkspaceIntegrityChecker**

验证 workspace 目录结构。此 checker 需要从 `all_tests_data`（而非 `base_dir`）中读取 `workspace_src` 字段，并展开 `${SIMPLEMEM_ROOT}` 环境变量（或用 `get_project_root()` 替换）：

- `workspace_src` 目录存在
- 包含必需身份文件：`AGENTS.md`、`IDENTITY.md`、`SOUL.md`、`TOOLS.md`、`USER.md`
- 对应每个 test（test.id 即 dayXX），`workspace_src/<test.id>/` 目录存在（warning 如不存在）

为此，`BaseChecker.__init__` 可增加可选参数 `all_tests_data: dict | None = None`，或在 `check_cmd.py` 中将 `all_tests_data` 传给需要它的 checker。

**`session_format.py` — SessionFormatChecker**

验证 session 初始文件格式：

- session 文件存在且是合法 JSONL
- 行数在 2–4 之间（1-2 轮对话 = 2-4 行；太多说明把任务写进了初始 session，给 warning）
- 第一行 role 为 `user`
- 若有第二行，role 为 `assistant`

**`all_tests_structure.py` — AllTestsStructureChecker**

验证 all_tests.json 顶层和 test 数组结构：

- 必需顶层字段：`name`、`openclaw_state_dir`、`eval_dir`、`workspace_src`、`test`
- `test` 数组非空，每项必有：`id`、`desc`、`agent`、`session`、`eval`
- 所有 test 共用同一个 `agent` id（不同则报 error）
- `arc` 和 `preference_tags` 缺失时给 warning（非必填但建议填写）
- test id 唯一性检查

### 5.4 check 命令最终 checker 列表（共 8 项）

```python
checkers = [
    AllTestsStructureChecker(base_dir),      # 新增
    BasicIntegrityChecker(base_dir),          # 适配
    IdConsistencyChecker(base_dir),           # 适配
    FileFormatChecker(base_dir),              # 保留
    DirectoryStructureChecker(base_dir),      # 适配
    WorkspaceIntegrityChecker(base_dir),      # 新增
    SessionFormatChecker(base_dir),           # 新增
    QuestionsIntegrityChecker(base_dir),      # 新增
]
```

---

### 6. CLI 入口点重命名

**位置**：`pyproject.toml`、`docs/CLI.md`

将 CLI 入口点从 `simplemem-benchmark` 改为 `metaclaw-bench`：

```toml
# pyproject.toml
[project.scripts]
metaclaw-bench = "src.cli:main"
```

`docs/CLI.md` 中所有命令示例中的 `simplemem-benchmark` 替换为 `metaclaw-bench`，标题和描述同步更新为 MetaClaw Benchmark。

`python -m benchmark.src.cli` 的调用方式保持不变（无需改动）。

---

### 7. 代码整洁与全量同步要求

**这是一次较大的项目重构，要求执行 agent 在改动完成后做以下检查**，避免堆积技术债：

### 7.1 代码结构审查

- 删除废弃的 checker 文件后，检查 `check/__init__.py` 和 `check_cmd.py` 的 import 是否同步清理
- `infer_cmd.py` 改动后检查函数职责是否清晰：workspace 相关逻辑（创建副本、patch config、scripts 复制）提取成独立函数，不要堆在 `_run_one_all_tests` 里
- `scoring_cmd.py` 新增 `file_check` 分支后，检查 `_score_round` 的参数签名是否仍然简洁
- **删除 `_format_query`**：`question` 字段已是完整输入，该函数无存在意义，直接内联为 `query = round_record["question"]`，相关 options 拼接和答题格式提示模板全部删除

### 7.2 tests 同步

`tests/` 目录下的测试文件需同步更新：

- `test_check.py`：删除对废弃 checker 的测试，新增对 8 个新 checker 的基础测试（valid data pass、key field missing fail）
- `test_infer.py`：新增对 feedback 注入逻辑的测试（`prev_round_passed` 正确拼接 feedback 文本）；新增对 `_run_file_check` 的单元测试（mock subprocess，验证 pass/fail 判断）；新增对 per-test workspace 副本逻辑的测试
- `test_scoring.py`：新增对 `file_check` 分支的测试（有 `inline_score.passed=True/False` 时 score=1/0）
- `test_ratio.py`：不需要改动

### 7.3 `docs/CLI.md` 全量更新

- 标题改为 `MetaClaw Benchmark CLI`
- 入口点改为 `metaclaw-bench`
- check 命令的"检查项目"章节改为描述新的 8 项 checker，删除旧的 11 项描述
- infer 命令文档：更新 `questions.json` 格式示例，去掉 options 字段，加上 `feedback` 和 `eval` 字段示例
- scoring 命令文档：补充 `file_check` 的 `scoring.json` 输出格式示例
- 删除 CALMB 特定的描述（"6 行标准"等）
