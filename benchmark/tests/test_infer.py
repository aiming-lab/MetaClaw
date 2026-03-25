"""Tests for benchmark/src/infer/ module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def eval_dir(tmp_path: Path) -> Path:
    """Create a minimal eval directory with questions.json."""
    e = tmp_path / "eval"
    scenario_dir = e / "scenario1"
    scenario_dir.mkdir(parents=True)

    questions = {
        "id": "scenario1",
        "desc": "test",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "What is the capital of France?",
                "feedback": {"correct": "Correct!", "incorrect": "Wrong."},
                "eval": {
                    "options": {"A": "Paris", "B": "London"},
                    "answer": ["A"],
                },
            }
        ],
    }
    (scenario_dir / "questions.json").write_text(
        json.dumps(questions), encoding="utf-8"
    )
    return e


@pytest.fixture()
def all_tests_file(tmp_path: Path, eval_dir: Path) -> Path:
    """Create a minimal all_tests.json with workspace_src."""
    oc_state = tmp_path / "openclaw_state"
    sessions = oc_state / "agents" / "agent1" / "sessions"
    sessions.mkdir(parents=True)
    agent_dir = oc_state / "agents" / "agent1" / "agent"
    agent_dir.mkdir(parents=True)
    (oc_state / "openclaw.json").write_text(
        json.dumps({"agents": {"list": [{"id": "agent1"}]}}),
        encoding="utf-8",
    )

    workspace_src = tmp_path / "workspaces" / "shared"
    workspace_src.mkdir(parents=True)
    for fname in ["AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"]:
        (workspace_src / fname).write_text(f"# {fname}", encoding="utf-8")

    data: dict = {
        "name": "my-tests",
        "openclaw_state_dir": str(oc_state),
        "eval_dir": str(eval_dir),
        "workspace_src": str(workspace_src),
        "test": [
            {
                "id": "scenario1",
                "desc": "Test scenario 1",
                "agent": "agent1",
                "session": "session-uuid-1",
                "eval": "scenario1",
            }
        ],
    }
    f = tmp_path / "all_tests.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# QueryReader tests
# ---------------------------------------------------------------------------


def test_eval_flow_query_reader_basic(tmp_path: Path) -> None:
    from src.infer.query_reader import EvalFlowQueryReader

    e = tmp_path / "eval"
    (e / "s1").mkdir(parents=True)
    flow = {
        "qa_annotations": [
            {"qa_id": "q1", "question": "What is the capital of France?"},
            {"qa_id": "q2", "question": "Who wrote Hamlet?"},
        ]
    }
    (e / "s1" / "eval_flow.json").write_text(json.dumps(flow), encoding="utf-8")

    reader = EvalFlowQueryReader()
    groups = reader.read_queries(e, "s1")
    assert len(groups) == 2
    assert groups[0]["id"] == "g1"
    assert groups[0]["rounds"][0]["id"] == "q1"
    assert "What is the capital" in groups[0]["rounds"][0]["question"]
    # new format: no options/answer at top level
    assert "options" not in groups[0]["rounds"][0]
    assert "answer" not in groups[0]["rounds"][0]


def test_eval_flow_query_reader_missing_file(tmp_path: Path) -> None:
    from src.infer.query_reader import EvalFlowQueryReader

    reader = EvalFlowQueryReader()
    groups = reader.read_queries(tmp_path / "nonexistent", "s1")
    assert groups == []


def test_get_default_query_reader() -> None:
    from src.infer.query_reader import QuestionsJsonQueryReader, get_default_query_reader

    reader = get_default_query_reader()
    assert isinstance(reader, QuestionsJsonQueryReader)


def test_questions_json_query_reader_reads_eval_and_feedback(tmp_path: Path) -> None:
    from src.infer.query_reader import QuestionsJsonQueryReader

    scenario_dir = tmp_path / "s1"
    scenario_dir.mkdir()
    questions = {
        "id": "s1",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "Q1?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {"correct": "Good!", "incorrect": "Nope."},
            },
            {
                "id": "r2",
                "type": "file_check",
                "question": "Q2?",
                "eval": {"command": "ls output.txt", "expect_exit": 0},
                "feedback": {"correct": "File OK!", "incorrect": "File missing."},
            },
        ],
    }
    (scenario_dir / "questions.json").write_text(json.dumps(questions), encoding="utf-8")

    reader = QuestionsJsonQueryReader()
    groups = reader.read_queries(tmp_path, "s1")
    assert len(groups) == 1
    rounds = groups[0]["rounds"]
    assert len(rounds) == 2

    r1 = rounds[0]
    assert r1["id"] == "r1"
    assert r1["type"] == "multi_choice"
    assert r1["eval"] == {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]}
    assert r1["feedback"] == {"correct": "Good!", "incorrect": "Nope."}

    r2 = rounds[1]
    assert r2["type"] == "file_check"
    assert r2["eval"]["command"] == "ls output.txt"
    assert r2["feedback"]["correct"] == "File OK!"


def test_questions_json_falls_back_to_eval_flow(tmp_path: Path) -> None:
    from src.infer.query_reader import QuestionsJsonQueryReader

    scenario_dir = tmp_path / "s1"
    scenario_dir.mkdir()
    flow = {"qa_annotations": [{"qa_id": "q1", "question": "Fallback Q?"}]}
    (scenario_dir / "eval_flow.json").write_text(json.dumps(flow), encoding="utf-8")

    reader = QuestionsJsonQueryReader()
    groups = reader.read_queries(tmp_path, "s1")
    assert len(groups) == 1
    assert groups[0]["rounds"][0]["id"] == "q1"


def test_questions_json_reads_update_field(tmp_path: Path) -> None:
    from src.infer.query_reader import QuestionsJsonQueryReader

    scenario_dir = tmp_path / "s1"
    scenario_dir.mkdir()
    questions = {
        "id": "s1",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "Q1?",
                "eval": {"options": {"A": "Y", "B": "N"}, "answer": ["A"]},
                "feedback": {"correct": "OK", "incorrect": "No"},
                "update": [
                    {"type": "workspace", "action": "new", "path": "f.txt", "source": "f.txt"}
                ],
            },
            {
                "id": "r2",
                "type": "multi_choice",
                "question": "Q2?",
                "eval": {"options": {"A": "Y", "B": "N"}, "answer": ["A"]},
                "feedback": {"correct": "OK", "incorrect": "No"},
                # no update
            },
        ],
    }
    (scenario_dir / "questions.json").write_text(json.dumps(questions), encoding="utf-8")

    reader = QuestionsJsonQueryReader()
    groups = reader.read_queries(tmp_path, "s1")
    rounds = groups[0]["rounds"]
    assert "update" in rounds[0]
    assert "update" not in rounds[1]


# ---------------------------------------------------------------------------
# _find_all_tests_files
# ---------------------------------------------------------------------------


def test_find_all_tests_files_single(all_tests_file: Path) -> None:
    from src.infer.infer_cmd import _find_all_tests_files

    result = _find_all_tests_files(all_tests_file)
    assert result == [all_tests_file]


def test_find_all_tests_files_directory(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _find_all_tests_files

    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "all_tests.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a" / "b" / "all_tests.json").write_text("{}", encoding="utf-8")

    result = _find_all_tests_files(tmp_path)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# _prepare_output_dir
# ---------------------------------------------------------------------------


def test_prepare_output_dir_new_dir(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_output_dir

    new_dir = tmp_path / "brand_new"
    with patch("src.infer.infer_cmd.resolve_path", return_value=new_dir):
        out = _prepare_output_dir(str(new_dir))
    assert out == new_dir
    assert out.exists()


def test_prepare_output_dir_existing_dir(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_output_dir

    existing = tmp_path / "existing"
    existing.mkdir()

    with patch("src.infer.infer_cmd.resolve_path", return_value=existing):
        out = _prepare_output_dir(str(existing), name="mytest")

    assert out.parent == existing
    assert out.name.startswith("infer_mytest_")
    assert out.exists()


# ---------------------------------------------------------------------------
# _prepare_work_copy (no workspace copy in new design)
# ---------------------------------------------------------------------------


def test_prepare_work_copy_creates_sibling_work_dir(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_work_copy

    state_dir = tmp_path / "openclaw_state"
    state_dir.mkdir()
    (state_dir / "agents" / "a1" / "sessions").mkdir(parents=True)
    (state_dir / "agents" / "a1" / "sessions" / "sess.jsonl").write_text("{}")
    (state_dir / "openclaw.json").write_text('{"agents": {}}', encoding="utf-8")

    work_copy = _prepare_work_copy(state_dir, tmp_path)

    assert (tmp_path / "work").exists()
    assert work_copy.parent == tmp_path / "work"
    assert work_copy.name.startswith("openclaw_state_")
    assert (work_copy / "openclaw.json").exists()
    assert state_dir.exists()


def test_prepare_work_copy_rewrites_agentdir_paths(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_work_copy

    state_dir = tmp_path / "openclaw_state"
    state_dir.mkdir(parents=True)
    (state_dir / "agents" / "a1" / "agent").mkdir(parents=True)

    orig_rel = "./" + str(state_dir.relative_to(tmp_path)).replace("\\", "/")
    openclaw_json = {
        "agents": {
            "list": [
                {
                    "id": "a1",
                    "workspace": "${BENCHMARK_WORKSPACE_DIR}",
                    "agentDir": orig_rel + "/agents/a1/agent",
                }
            ]
        }
    }
    (state_dir / "openclaw.json").write_text(json.dumps(openclaw_json), encoding="utf-8")

    work_copy = _prepare_work_copy(state_dir, tmp_path)
    config = json.loads((work_copy / "openclaw.json").read_text())
    agent = config["agents"]["list"][0]

    new_rel = "./" + str(work_copy.relative_to(tmp_path)).replace("\\", "/")
    # agentDir should be rewritten to work_copy
    assert new_rel in agent["agentDir"]
    assert orig_rel not in agent["agentDir"]

    # workspace is NOT touched by _prepare_work_copy (per-test patching)
    assert agent["workspace"] == "${BENCHMARK_WORKSPACE_DIR}"


def test_prepare_work_copy_unique_per_call(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_work_copy

    state_dir = tmp_path / "openclaw_state"
    state_dir.mkdir()
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")

    copy1 = _prepare_work_copy(state_dir, tmp_path)
    copy2 = _prepare_work_copy(state_dir, tmp_path)

    assert copy1 != copy2
    assert copy1.exists()
    assert copy2.exists()


# ---------------------------------------------------------------------------
# _copy_workspace_for_test and _patch_agent_workspace
# ---------------------------------------------------------------------------


def test_copy_workspace_for_test(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _copy_workspace_for_test

    workspace_src = tmp_path / "workspaces" / "shared"
    workspace_src.mkdir(parents=True)
    (workspace_src / "AGENTS.md").write_text("# agents", encoding="utf-8")
    (workspace_src / "day01").mkdir()
    (workspace_src / "day01" / "README.md").write_text("Day 1", encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    dest = _copy_workspace_for_test(workspace_src, work_dir, "day01")

    assert dest.name.startswith("workspace_day01_")
    assert dest.parent == work_dir
    assert (dest / "AGENTS.md").exists()
    assert (dest / "day01" / "README.md").exists()
    # Original untouched
    assert (workspace_src / "AGENTS.md").exists()


def test_copy_workspace_for_test_excludes_other_days(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _copy_workspace_for_test

    workspace_src = tmp_path / "workspaces" / "shared"
    workspace_src.mkdir(parents=True)
    (workspace_src / "AGENTS.md").write_text("# agents", encoding="utf-8")
    # Create three day directories; only day02 should be copied
    for day in ["day01", "day02", "day03"]:
        (workspace_src / day).mkdir()
        (workspace_src / day / "README.md").write_text(f"Day {day}", encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    dest = _copy_workspace_for_test(workspace_src, work_dir, "day02")

    # Target day is present
    assert (dest / "day02" / "README.md").exists()
    # Other day directories must NOT be copied
    assert not (dest / "day01").exists()
    assert not (dest / "day03").exists()
    # Identity files are present
    assert (dest / "AGENTS.md").exists()


def test_patch_agent_workspace(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _patch_agent_workspace

    oc_json = tmp_path / "openclaw.json"
    config = {
        "agents": {
            "list": [
                {"id": "agent1", "workspace": "${BENCHMARK_WORKSPACE_DIR}"},
                {"id": "agent2", "workspace": "/some/other/path"},
            ]
        }
    }
    oc_json.write_text(json.dumps(config), encoding="utf-8")

    new_ws = tmp_path / "work" / "workspace_day01_abc"
    _patch_agent_workspace(oc_json, "agent1", new_ws)

    updated = json.loads(oc_json.read_text())
    agents = {a["id"]: a for a in updated["agents"]["list"]}
    assert agents["agent1"]["workspace"] == str(new_ws)
    assert agents["agent2"]["workspace"] == "/some/other/path"


def test_copy_eval_scripts(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _copy_eval_scripts

    eval_dir = tmp_path / "eval"
    scripts_src = eval_dir / "scripts"
    scripts_src.mkdir(parents=True)
    (scripts_src / "check_meeting.py").write_text("print('OK')", encoding="utf-8")

    workspace = tmp_path / "workspace_day01"
    workspace.mkdir()

    _copy_eval_scripts(eval_dir, workspace)

    assert (workspace / "scripts" / "check_meeting.py").exists()


def test_copy_eval_scripts_no_scripts_dir(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _copy_eval_scripts

    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Should not raise even if eval/scripts/ doesn't exist
    _copy_eval_scripts(eval_dir, workspace)
    assert not (workspace / "scripts").exists()


# ---------------------------------------------------------------------------
# _run_file_check
# ---------------------------------------------------------------------------


def test_run_file_check_pass(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    (tmp_path / "output.txt").write_text("hello", encoding="utf-8")
    result = _run_file_check(
        {"command": "cat output.txt", "expect_exit": 0},
        tmp_path,
    )
    assert result["passed"] is True
    assert result["exit_code"] == 0


def test_run_file_check_fail_wrong_exit(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    result = _run_file_check(
        {"command": "ls nonexistent_file_xyz", "expect_exit": 0},
        tmp_path,
    )
    assert result["passed"] is False


def test_run_file_check_expect_stdout(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    (tmp_path / "check.py").write_text("print('OK')", encoding="utf-8")
    result = _run_file_check(
        {"command": "python check.py", "expect_exit": 0, "expect_stdout": "OK"},
        tmp_path,
    )
    assert result["passed"] is True


def test_run_file_check_expect_stdout_missing(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    (tmp_path / "check.py").write_text("print('FAIL')", encoding="utf-8")
    result = _run_file_check(
        {"command": "python check.py", "expect_exit": 0, "expect_stdout": "OK"},
        tmp_path,
    )
    assert result["passed"] is False


def test_run_file_check_expect_stdout_regex(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    (tmp_path / "check.py").write_text("print('Result: 42')", encoding="utf-8")
    result = _run_file_check(
        {
            "command": "python check.py",
            "expect_exit": 0,
            "expect_stdout": r"Result: \d+",
            "expect_stdout_regex": True,
        },
        tmp_path,
    )
    assert result["passed"] is True


def test_run_file_check_no_command(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    result = _run_file_check({}, tmp_path)
    assert result["passed"] is False
    assert "no command" in result["stderr"]


def test_run_file_check_timeout(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_file_check

    result = _run_file_check(
        {"command": "sleep 10", "expect_exit": 0, "timeout": 0.1},
        tmp_path,
    )
    assert result["passed"] is False
    assert "Timeout" in result["stderr"]


# ---------------------------------------------------------------------------
# _compute_inline_score
# ---------------------------------------------------------------------------


def test_compute_inline_score_multi_choice_pass(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _compute_inline_score

    round_record = {
        "type": "multi_choice",
        "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
    }
    result = _compute_inline_score(round_record, r"I choose \bbox{A}", tmp_path)
    assert result["passed"] is True


def test_compute_inline_score_multi_choice_fail(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _compute_inline_score

    round_record = {
        "type": "multi_choice",
        "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
    }
    result = _compute_inline_score(round_record, r"\bbox{B}", tmp_path)
    assert result["passed"] is False


def test_compute_inline_score_no_bbox(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _compute_inline_score

    round_record = {
        "type": "multi_choice",
        "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
    }
    result = _compute_inline_score(round_record, "I pick A (no bbox)", tmp_path)
    assert result["passed"] is False


def test_compute_inline_score_file_check_pass(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _compute_inline_score

    (tmp_path / "output.txt").write_text("done", encoding="utf-8")
    round_record = {
        "type": "file_check",
        "eval": {"command": "cat output.txt", "expect_exit": 0},
    }
    result = _compute_inline_score(round_record, "", tmp_path)
    assert result["passed"] is True


# ---------------------------------------------------------------------------
# _get_existing_log_files
# ---------------------------------------------------------------------------


def test_get_existing_log_files(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _get_existing_log_files

    session_dir = tmp_path / "sess1"
    session_dir.mkdir()
    f1 = session_dir / "a.json"
    f2 = session_dir / "b.json"
    f1.write_text("{}")
    f2.write_text("{}")

    result = _get_existing_log_files(tmp_path, "sess1")
    assert f1 in result
    assert f2 in result


def test_get_existing_log_files_missing_dir(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _get_existing_log_files

    result = _get_existing_log_files(tmp_path, "no-such-session")
    assert result == set()


# ---------------------------------------------------------------------------
# _trim_llm_log_messages
# ---------------------------------------------------------------------------


def test_trim_llm_log_messages_keeps_last_user_and_after() -> None:
    from src.infer.infer_cmd import _trim_llm_log_messages

    log = {
        "stage": "agent_end",
        "messages": [
            {"role": "compactionSummary"},
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "last question"},
            {"role": "assistant", "content": "last answer"},
        ],
    }
    result = _trim_llm_log_messages(log)
    assert len(result["messages"]) == 2
    assert result["messages"][0]["content"] == "last question"
    assert result["stage"] == "agent_end"


# ---------------------------------------------------------------------------
# _prepare_session
# ---------------------------------------------------------------------------


def test_prepare_session_creates_empty_when_missing(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_session

    _prepare_session(tmp_path, "a1", "main")
    session_file = tmp_path / "agents" / "a1" / "sessions" / "main.jsonl"
    assert session_file.exists()
    assert session_file.read_text(encoding="utf-8") == ""


def test_prepare_session_existing_file_untouched(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _prepare_session

    sessions_dir = tmp_path / "agents" / "a1" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "main.jsonl").write_text('{"msg":"existing"}\n', encoding="utf-8")

    _prepare_session(tmp_path, "a1", "main")
    assert (sessions_dir / "main.jsonl").read_text(encoding="utf-8") == '{"msg":"existing"}\n'


# ---------------------------------------------------------------------------
# _resolve_log_dir
# ---------------------------------------------------------------------------


def test_resolve_log_dir_reads_from_openclaw_json(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _resolve_log_dir

    state_dir = tmp_path / "openclaw_state"
    state_dir.mkdir()
    config = {
        "plugins": {
            "entries": {
                "llm-prompt-logger": {
                    "config": {"logDir": "${METACLAW_ROOT}/logs/llm_prompts"}
                }
            }
        }
    }
    (state_dir / "openclaw.json").write_text(json.dumps(config), encoding="utf-8")
    result = _resolve_log_dir(state_dir, tmp_path)
    assert result == tmp_path / "logs" / "llm_prompts"


def test_resolve_log_dir_fallback(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _resolve_log_dir

    state_dir = tmp_path / "openclaw_state"
    state_dir.mkdir()
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")
    result = _resolve_log_dir(state_dir, tmp_path)
    assert result == tmp_path / "logs" / "llm_prompts"


# ---------------------------------------------------------------------------
# _run_question
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_question_success(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_question

    result_path = tmp_path / "t1" / "g1" / "q1" / "infer_result.json"
    log_dir = tmp_path / "logs"

    with patch("src.infer.infer_cmd._run_openclaw_agent", new=AsyncMock(return_value=(0, "Paris", ""))):
        await _run_question(
            test_id="t1",
            group_id="g1",
            round_id="q1",
            query="Capital of France?",
            agent_id="agent1",
            session_id="sess-123",
            openclaw_config_path=tmp_path / "openclaw.json",
            openclaw_state_dir=tmp_path / "state",
            log_dir=log_dir,
            result_path=result_path,
            project_root=tmp_path,
            retry=0,
        )

    assert result_path.exists()
    result = json.loads(result_path.read_text())
    assert result["status"] == "success"
    assert result["answer"] == "Paris"
    assert result["qa_id"] == "q1"


@pytest.mark.asyncio
async def test_run_question_skips_existing(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _run_question

    result_path = tmp_path / "t1" / "g1" / "q1" / "infer_result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(json.dumps({"status": "success", "answer": "existing"}))

    with patch("src.infer.infer_cmd._run_openclaw_agent", new=AsyncMock()) as mock:
        await _run_question(
            test_id="t1", group_id="g1", round_id="q1", query="Q?",
            agent_id="agent1", session_id="sess-123",
            openclaw_config_path=tmp_path / "openclaw.json",
            openclaw_state_dir=tmp_path / "state",
            log_dir=tmp_path / "logs", result_path=result_path,
            project_root=tmp_path,
        )
    mock.assert_not_called()
    assert json.loads(result_path.read_text())["answer"] == "existing"


# ---------------------------------------------------------------------------
# _run_group: feedback injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_group_feedback_injection(tmp_path: Path) -> None:
    """_run_group prepends [上一步反馈] to subsequent rounds."""
    from src.infer.infer_cmd import _run_group

    state_dir = tmp_path / "state"
    sessions_dir = state_dir / "agents" / "a1" / "sessions"
    sessions_dir.mkdir(parents=True)
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    out_dir = tmp_path / "results"
    eval_dir = tmp_path / "eval"
    (eval_dir / "s1").mkdir(parents=True)

    queries_sent: list[str] = []

    async def _mock_agent(session_id, message, **kwargs):
        queries_sent.append(message)
        return 0, r"\bbox{A}", ""

    group = {
        "id": "g1",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "First question?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {
                    "correct": "Well done!",
                    "options": {"A": "A correct.", "B": "B wrong."},
                },
            },
            {
                "id": "r2",
                "type": "multi_choice",
                "question": "Second question?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {
                    "correct": "Perfect!",
                    "options": {"A": "A correct.", "B": "B wrong."},
                },
            },
        ],
    }

    semaphore = __import__("asyncio").Semaphore(1)

    with patch("src.infer.infer_cmd._run_openclaw_agent", new=_mock_agent):
        await _run_group(
            test_id="t1",
            group=group,
            agent_id="a1",
            original_session_id="main",
            work_openclaw_state_dir=state_dir,
            openclaw_config_path=state_dir / "openclaw.json",
            log_dir=tmp_path / "logs",
            out_dir=out_dir,
            project_root=tmp_path,
            retry=0,
            semaphore=semaphore,
            eval_dir=eval_dir,
            eval_name="s1",
            workspace_path=workspace,
        )

    # First round: no feedback prefix
    assert queries_sent[0] == "First question?"
    # Second round: feedback from r1 (correct) prepended via [Previous Feedback]
    assert "[Previous Feedback] Well done!" in queries_sent[1]
    assert "Second question?" in queries_sent[1]
    # Third call: standalone feedback message
    assert len(queries_sent) == 3
    assert "[Previous Feedback] Perfect!" in queries_sent[2]


@pytest.mark.asyncio
async def test_run_group_incorrect_feedback(tmp_path: Path) -> None:
    """When answer is wrong, incorrect feedback is used."""
    from src.infer.infer_cmd import _run_group

    state_dir = tmp_path / "state"
    (state_dir / "agents" / "a1" / "sessions").mkdir(parents=True)
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out_dir = tmp_path / "results"
    eval_dir = tmp_path / "eval"
    (eval_dir / "s1").mkdir(parents=True)

    queries_sent: list[str] = []

    async def _mock_agent(session_id, message, **kwargs):
        queries_sent.append(message)
        return 0, r"\bbox{B}", ""  # wrong answer (correct is A)

    group = {
        "id": "g1",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "Q1?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {
                    "correct": "Correct!",
                    "options": {
                        "A": "A correct: Yes is right.",
                        "B": "B wrong: No is incorrect.",
                    },
                },
            },
            {
                "id": "r2",
                "type": "multi_choice",
                "question": "Q2?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {
                    "correct": "C",
                    "options": {"A": "A ok", "B": "B not ok"},
                },
            },
        ],
    }

    semaphore = __import__("asyncio").Semaphore(1)
    with patch("src.infer.infer_cmd._run_openclaw_agent", new=_mock_agent):
        await _run_group(
            test_id="t1", group=group, agent_id="a1", original_session_id="main",
            work_openclaw_state_dir=state_dir,
            openclaw_config_path=state_dir / "openclaw.json",
            log_dir=tmp_path / "logs", out_dir=out_dir, project_root=tmp_path,
            retry=0, semaphore=semaphore, eval_dir=eval_dir, eval_name="s1",
            workspace_path=workspace,
        )

    # Agent selected B but correct is A → per-option feedback for r1:
    # missed A, wrongly selected B
    assert "You missed option A" in queries_sent[1]
    assert "A correct: Yes is right." in queries_sent[1]
    assert "You incorrectly selected option B" in queries_sent[1]
    assert "B wrong: No is incorrect." in queries_sent[1]


@pytest.mark.asyncio
async def test_run_group_writes_inline_score(tmp_path: Path) -> None:
    """_run_group writes inline_score to infer_result.json."""
    from src.infer.infer_cmd import _run_group

    state_dir = tmp_path / "state"
    (state_dir / "agents" / "a1" / "sessions").mkdir(parents=True)
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out_dir = tmp_path / "results"
    eval_dir = tmp_path / "eval"
    (eval_dir / "s1").mkdir(parents=True)

    group = {
        "id": "g1",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "Q?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {"correct": "C", "options": {"A": "A ok", "B": "B not ok"}},
            }
        ],
    }

    semaphore = __import__("asyncio").Semaphore(1)
    with patch(
        "src.infer.infer_cmd._run_openclaw_agent",
        new=AsyncMock(return_value=(0, r"\bbox{A}", "")),
    ):
        await _run_group(
            test_id="t1", group=group, agent_id="a1", original_session_id="main",
            work_openclaw_state_dir=state_dir,
            openclaw_config_path=state_dir / "openclaw.json",
            log_dir=tmp_path / "logs", out_dir=out_dir, project_root=tmp_path,
            retry=0, semaphore=semaphore, eval_dir=eval_dir, eval_name="s1",
            workspace_path=workspace,
        )

    result_path = out_dir / "t1" / "g1" / "r1" / "infer_result.json"
    assert result_path.exists()
    result = json.loads(result_path.read_text())
    assert "inline_score" in result
    assert result["inline_score"]["passed"] is True


@pytest.mark.asyncio
async def test_run_group_resume_skips_inline_score_rounds(tmp_path: Path) -> None:
    """Rounds with existing inline_score are skipped entirely."""
    from src.infer.infer_cmd import _run_group

    state_dir = tmp_path / "state"
    (state_dir / "agents" / "a1" / "sessions").mkdir(parents=True)
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out_dir = tmp_path / "results"
    eval_dir = tmp_path / "eval"
    (eval_dir / "s1").mkdir(parents=True)

    # Pre-write an infer_result with inline_score
    result_path = out_dir / "t1" / "g1" / "r1" / "infer_result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps({
            "status": "success",
            "answer": r"\bbox{A}",
            "inline_score": {"passed": True},
        })
    )

    group = {
        "id": "g1",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "Q?",
                "eval": {"options": {"A": "Yes", "B": "No"}, "answer": ["A"]},
                "feedback": {"correct": "C", "options": {"A": "A ok", "B": "B not ok"}},
            }
        ],
    }

    semaphore = __import__("asyncio").Semaphore(1)
    with patch("src.infer.infer_cmd._run_openclaw_agent", new=AsyncMock()) as mock:
        await _run_group(
            test_id="t1", group=group, agent_id="a1", original_session_id="main",
            work_openclaw_state_dir=state_dir,
            openclaw_config_path=state_dir / "openclaw.json",
            log_dir=tmp_path / "logs", out_dir=out_dir, project_root=tmp_path,
            retry=0, semaphore=semaphore, eval_dir=eval_dir, eval_name="s1",
            workspace_path=workspace,
        )

    # Agent should not be called for resumed round (only standalone feedback may be sent)
    # At most 1 call for standalone feedback
    assert mock.call_count <= 1


# ---------------------------------------------------------------------------
# _execute_update tests
# ---------------------------------------------------------------------------


def test_execute_update_workspace_new(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _execute_update

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    workspace_dir = tmp_path / "ws" / "a1"
    workspace_dir.mkdir(parents=True)
    config = {"agents": {"list": [{"id": "a1", "workspace": str(workspace_dir)}]}}
    (state_dir / "openclaw.json").write_text(json.dumps(config), encoding="utf-8")

    eval_dir = tmp_path / "eval"
    (eval_dir / "s1").mkdir(parents=True)
    (eval_dir / "s1" / "notes.txt").write_text("new content", encoding="utf-8")

    _execute_update(
        update={"type": "workspace", "action": "new", "path": "notes.txt", "source": "notes.txt"},
        agent_id="a1",
        work_openclaw_state_dir=state_dir,
        eval_dir=eval_dir,
        eval_name="s1",
    )

    assert (workspace_dir / "notes.txt").read_text(encoding="utf-8") == "new content"


def test_execute_update_session_append(tmp_path: Path) -> None:
    from src.infer.infer_cmd import _execute_update

    state_dir = tmp_path / "state"
    sessions_dir = state_dir / "agents" / "a1" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "sess.jsonl").write_text('{"msg":"existing"}\n', encoding="utf-8")

    eval_dir = tmp_path / "eval"
    (eval_dir / "s1").mkdir(parents=True)
    (eval_dir / "s1" / "sess.jsonl").write_text('{"msg":"appended"}\n', encoding="utf-8")
    (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")

    _execute_update(
        update={"type": "session", "action": "append", "path": "sess.jsonl", "source": "sess.jsonl"},
        agent_id="a1",
        work_openclaw_state_dir=state_dir,
        eval_dir=eval_dir,
        eval_name="s1",
    )

    content = (sessions_dir / "sess.jsonl").read_text(encoding="utf-8")
    assert '{"msg":"existing"}' in content
    assert '{"msg":"appended"}' in content


# ---------------------------------------------------------------------------
# run_clean tests
# ---------------------------------------------------------------------------


def test_run_clean_removes_work_dirs(tmp_path: Path) -> None:
    from src.clean.clean_cmd import run_clean

    (tmp_path / "data" / "work" / "openclaw_state_abc").mkdir(parents=True)
    (tmp_path / "data" / "work" / "workspaces_abc" / "a1").mkdir(parents=True)
    (tmp_path / "other" / "work" / "openclaw_state_xyz").mkdir(parents=True)
    (tmp_path / "data" / "eval").mkdir(parents=True)

    run_clean(str(tmp_path))

    assert not (tmp_path / "data" / "work").exists()
    assert not (tmp_path / "other" / "work").exists()
    assert (tmp_path / "data" / "eval").exists()
