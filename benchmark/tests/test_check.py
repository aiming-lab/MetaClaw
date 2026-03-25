"""Tests for the check command (MetaClaw bench checkers)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.check.check_cmd import run_check
from src.check import (
    AllTestsStructureChecker,
    BasicIntegrityChecker,
    IdConsistencyChecker,
    FileFormatChecker,
    DirectoryStructureChecker,
    WorkspaceIntegrityChecker,
    SessionFormatChecker,
    QuestionsIntegrityChecker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def metaclaw_data(tmp_path: Path):
    """Create a minimal valid MetaClaw benchmark data structure."""
    base_dir = tmp_path / "metaclaw-bench"
    base_dir.mkdir()

    agent_id = "metaclaw_agent"
    session_id = "day01_aaaaaaaa-0000-0000-0000-000000000001"

    # openclaw_state
    sessions_dir = base_dir / "openclaw_state" / "agents" / agent_id / "sessions"
    sessions_dir.mkdir(parents=True)
    session_file = sessions_dir / f"{session_id}.jsonl"
    session_file.write_text(
        json.dumps({"role": "user", "content": "Hello, today is Monday."}) + "\n"
        + json.dumps({"role": "assistant", "content": "Understood, ready to help."}) + "\n",
        encoding="utf-8",
    )

    # eval
    eval_dir = base_dir / "eval" / "day01"
    eval_dir.mkdir(parents=True)
    questions = {
        "id": "day01",
        "desc": "Day 1 test",
        "rounds": [
            {
                "id": "r1",
                "type": "multi_choice",
                "question": "Which format?",
                "feedback": {
                    "correct": "Good!",
                    "options": {
                        "A": "A correct: ISO 8601 is the standard.",
                        "B": "B wrong: Unix timestamp is not ISO 8601.",
                    },
                },
                "eval": {
                    "options": {"A": "ISO 8601", "B": "Unix timestamp"},
                    "answer": ["A"],
                },
            },
            {
                "id": "r2",
                "type": "file_check",
                "question": "Save the file.",
                "feedback": {"correct": "File OK!", "incorrect": "File missing."},
                "eval": {"command": "ls tasks/day01/output.json", "expect_exit": 0},
            },
        ],
    }
    (eval_dir / "questions.json").write_text(
        json.dumps(questions), encoding="utf-8"
    )

    # workspace_src
    ws_dir = base_dir / "workspaces" / "shared"
    ws_dir.mkdir(parents=True)
    for fname in ["AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"]:
        (ws_dir / fname).write_text(f"# {fname}\nContent.", encoding="utf-8")
    (ws_dir / "day01").mkdir()

    # all_tests.json
    all_tests = {
        "name": "MetaClaw-Evolution-Bench",
        "openclaw_state_dir": str(base_dir / "openclaw_state"),
        "eval_dir": str(base_dir / "eval"),
        "workspace_src": str(ws_dir),
        "test": [
            {
                "id": "day01",
                "desc": "Day 1 - intro",
                "agent": agent_id,
                "session": session_id,
                "eval": "day01",
                "arc": "A",
                "preference_tags": ["output_format"],
            }
        ],
    }
    all_tests_file = base_dir / "all_tests.json"
    all_tests_file.write_text(json.dumps(all_tests), encoding="utf-8")

    return base_dir, all_tests_file


# ---------------------------------------------------------------------------
# AllTestsStructureChecker
# ---------------------------------------------------------------------------


def test_all_tests_structure_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = AllTestsStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed
    assert len(result.errors) == 0


def test_all_tests_structure_missing_workspace_src(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    del test_data["workspace_src"]
    checker = AllTestsStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("workspace_src" in e for e in result.errors)


def test_all_tests_structure_missing_test_field(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    del test_data["test"][0]["desc"]
    checker = AllTestsStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("desc" in e for e in result.errors)


def test_all_tests_structure_multiple_agents_error(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    # Add a second test with different agent
    second_test = dict(test_data["test"][0])
    second_test["id"] = "day02"
    second_test["agent"] = "another_agent"
    second_test["session"] = "day02_unique-session-id-002"
    test_data["test"].append(second_test)
    checker = AllTestsStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("multiple" in e for e in result.errors)


def test_all_tests_structure_duplicate_test_id(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    test_data["test"].append(test_data["test"][0].copy())
    checker = AllTestsStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("duplicate" in e for e in result.errors)


# ---------------------------------------------------------------------------
# BasicIntegrityChecker
# ---------------------------------------------------------------------------


def test_basic_integrity_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = BasicIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed
    assert len(result.errors) == 0


def test_basic_integrity_missing_session_file(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    session_id = test_data["test"][0]["session"]
    agent_id = test_data["test"][0]["agent"]
    session_file = (
        base_dir / "openclaw_state" / "agents" / agent_id / "sessions"
        / f"{session_id}.jsonl"
    )
    session_file.unlink()
    checker = BasicIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("session file" in e for e in result.errors)


def test_basic_integrity_missing_questions_json(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    (base_dir / "eval" / "day01" / "questions.json").unlink()
    checker = BasicIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("questions.json" in e for e in result.errors)


def test_basic_integrity_questions_missing_required_field(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    del q["rounds"][0]["feedback"]
    q_path.write_text(json.dumps(q))
    checker = BasicIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("feedback" in e for e in result.errors)


# ---------------------------------------------------------------------------
# IdConsistencyChecker
# ---------------------------------------------------------------------------


def test_id_consistency_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = IdConsistencyChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed


# ---------------------------------------------------------------------------
# FileFormatChecker
# ---------------------------------------------------------------------------


def test_file_format_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = FileFormatChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed


def test_file_format_invalid_jsonl(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    session_id = test_data["test"][0]["session"]
    agent_id = test_data["test"][0]["agent"]
    session_file = (
        base_dir / "openclaw_state" / "agents" / agent_id / "sessions"
        / f"{session_id}.jsonl"
    )
    with open(session_file, "a") as f:
        f.write("not valid json\n")
    checker = FileFormatChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("invalid JSON" in e for e in result.errors)


# ---------------------------------------------------------------------------
# DirectoryStructureChecker
# ---------------------------------------------------------------------------


def test_directory_structure_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = DirectoryStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed


def test_directory_structure_missing_eval_dir(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    import shutil
    shutil.rmtree(base_dir / "eval" / "day01")
    checker = DirectoryStructureChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("eval directory" in e for e in result.errors)


# ---------------------------------------------------------------------------
# WorkspaceIntegrityChecker
# ---------------------------------------------------------------------------


def test_workspace_integrity_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = WorkspaceIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed


def test_workspace_integrity_missing_identity_file(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    (base_dir / "workspaces" / "shared" / "SOUL.md").unlink()
    checker = WorkspaceIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("SOUL.md" in e for e in result.errors)


def test_workspace_integrity_missing_workspace_src_field(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    del test_data["workspace_src"]
    checker = WorkspaceIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("workspace_src" in e for e in result.errors)


# ---------------------------------------------------------------------------
# SessionFormatChecker
# ---------------------------------------------------------------------------


def test_session_format_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = SessionFormatChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed


def test_session_format_wrong_first_role(metaclaw_data):
    """Simple-format file with assistant as first role must fail."""
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    session_id = test_data["test"][0]["session"]
    agent_id = test_data["test"][0]["agent"]
    session_file = (
        base_dir / "openclaw_state" / "agents" / agent_id / "sessions"
        / f"{session_id}.jsonl"
    )
    session_file.write_text(
        json.dumps({"role": "assistant", "content": "Hi"}) + "\n",
        encoding="utf-8",
    )
    checker = SessionFormatChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("role='user'" in e for e in result.errors)


def test_session_format_openclaw_format_valid(metaclaw_data):
    """New openclaw format (4 metadata + message lines) must pass."""
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    session_id = test_data["test"][0]["session"]
    agent_id = test_data["test"][0]["agent"]
    session_file = (
        base_dir / "openclaw_state" / "agents" / agent_id / "sessions"
        / f"{session_id}.jsonl"
    )
    session_file.write_text(
        json.dumps({"type": "session", "version": 3, "id": session_id,
                    "timestamp": "2026-03-16T01:00:00.000Z", "cwd": "/ws"}) + "\n"
        + json.dumps({"type": "model_change", "id": "aabb1122", "parentId": None,
                      "timestamp": "2026-03-16T01:00:00.010Z",
                      "provider": "metaclaw-benchmark", "modelId": "${BENCHMARK_MODEL}"}) + "\n"
        + json.dumps({"type": "thinking_level_change", "id": "ccdd3344",
                      "parentId": "aabb1122", "timestamp": "2026-03-16T01:00:00.020Z",
                      "thinkingLevel": "low"}) + "\n"
        + json.dumps({"type": "custom", "customType": "model-snapshot",
                      "data": {"timestamp": 1773622800030, "provider": "metaclaw-benchmark",
                               "modelApi": "openai-completions",
                               "modelId": "${BENCHMARK_MODEL}"},
                      "id": "eeff5566", "parentId": "ccdd3344",
                      "timestamp": "2026-03-16T01:00:00.030Z"}) + "\n"
        + json.dumps({"type": "message", "id": "msg00001", "parentId": "eeff5566",
                      "timestamp": "2026-03-16T01:02:00.000Z",
                      "message": {"role": "user",
                                  "content": [{"type": "text", "text": "Hello!"}]}}) + "\n"
        + json.dumps({"type": "message", "id": "msg00002", "parentId": "msg00001",
                      "timestamp": "2026-03-16T01:02:30.000Z",
                      "message": {"role": "assistant",
                                  "content": [{"type": "text", "text": "Hi!"}]}}) + "\n",
        encoding="utf-8",
    )
    checker = SessionFormatChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed
    assert len(result.errors) == 0


def test_session_format_openclaw_format_wrong_first_message_role(metaclaw_data):
    """New openclaw format: first message with role=assistant must fail."""
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    session_id = test_data["test"][0]["session"]
    agent_id = test_data["test"][0]["agent"]
    session_file = (
        base_dir / "openclaw_state" / "agents" / agent_id / "sessions"
        / f"{session_id}.jsonl"
    )
    session_file.write_text(
        json.dumps({"type": "session", "version": 3, "id": session_id,
                    "timestamp": "2026-03-16T01:00:00.000Z", "cwd": "/ws"}) + "\n"
        + json.dumps({"type": "model_change", "id": "aabb1122", "parentId": None,
                      "timestamp": "2026-03-16T01:00:00.010Z"}) + "\n"
        + json.dumps({"type": "thinking_level_change", "id": "ccdd3344",
                      "parentId": "aabb1122", "timestamp": "2026-03-16T01:00:00.020Z",
                      "thinkingLevel": "low"}) + "\n"
        + json.dumps({"type": "custom", "customType": "model-snapshot", "data": {},
                      "id": "eeff5566", "parentId": "ccdd3344",
                      "timestamp": "2026-03-16T01:00:00.030Z"}) + "\n"
        + json.dumps({"type": "message", "id": "msg00001", "parentId": "eeff5566",
                      "timestamp": "2026-03-16T01:02:00.000Z",
                      "message": {"role": "assistant",
                                  "content": [{"type": "text", "text": "Hi!"}]}}) + "\n",
        encoding="utf-8",
    )
    checker = SessionFormatChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("role='user'" in e for e in result.errors)


# ---------------------------------------------------------------------------
# QuestionsIntegrityChecker
# ---------------------------------------------------------------------------


def test_questions_integrity_valid(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert result.passed


def test_questions_integrity_invalid_type(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    q["rounds"][0]["type"] = "unknown_type"
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("invalid type" in e for e in result.errors)


def test_questions_integrity_empty_feedback(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    q["rounds"][0]["feedback"]["correct"] = ""
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("feedback.correct" in e for e in result.errors)


def test_questions_integrity_multi_choice_too_few_options(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    q["rounds"][0]["eval"]["options"] = {"A": "only one"}
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("at least 2" in e for e in result.errors)


def test_questions_integrity_file_check_missing_command(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    del q["rounds"][1]["eval"]["command"]
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("eval.command" in e for e in result.errors)


def test_questions_integrity_duplicate_round_id(metaclaw_data):
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    q["rounds"][1]["id"] = q["rounds"][0]["id"]  # duplicate
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("duplicate round id" in e for e in result.errors)


def test_questions_integrity_multi_choice_missing_options_feedback(metaclaw_data):
    """feedback.options missing on multi_choice round → FAILED."""
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    # Remove the options key from feedback on r1 (multi_choice)
    del q["rounds"][0]["feedback"]["options"]
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("feedback.options" in e for e in result.errors)


def test_questions_integrity_multi_choice_options_key_mismatch(metaclaw_data):
    """feedback.options keys differ from eval.options keys → FAILED."""
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    # feedback.options has key C, but eval.options only has A and B
    q["rounds"][0]["feedback"]["options"]["C"] = "Extra option."
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("do not match" in e for e in result.errors)


def test_questions_integrity_multi_choice_empty_option_feedback(metaclaw_data):
    """feedback.options[X] is empty string → FAILED."""
    base_dir, all_tests_file = metaclaw_data
    test_data = json.loads(all_tests_file.read_text())
    q_path = base_dir / "eval" / "day01" / "questions.json"
    q = json.loads(q_path.read_text())
    q["rounds"][0]["feedback"]["options"]["A"] = ""
    q_path.write_text(json.dumps(q))
    checker = QuestionsIntegrityChecker(base_dir, test_data)
    result = checker.check(test_data)
    assert not result.passed
    assert any("feedback.options['A']" in e for e in result.errors)


# ---------------------------------------------------------------------------
# run_check integration
# ---------------------------------------------------------------------------


def test_run_check_integration(metaclaw_data, capsys):
    base_dir, all_tests_file = metaclaw_data
    run_check(str(all_tests_file))
    captured = capsys.readouterr()
    assert "Running Data Integrity Checks" in captured.out
    assert "Summary" in captured.out
