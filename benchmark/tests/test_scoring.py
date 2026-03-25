"""Tests for benchmark/src/scoring/ and benchmark/src/report/ modules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def questions_eval_dir(tmp_path: Path) -> Path:
    """Create an eval directory with questions.json (MetaClaw format with eval sub-object)."""
    eval_dir = tmp_path / "eval"
    scenario_dir = eval_dir / "s1"
    scenario_dir.mkdir(parents=True)

    questions = [
        {
            "id": "g1",
            "desc": "UI library",
            "rounds": [
                {
                    "id": "q1",
                    "type": "multi_choice",
                    "question": "Which UI library is used?",
                    "feedback": {
                        "correct": "Correct!",
                        "options": {
                            "A": "A wrong: not used.",
                            "B": "B correct: Ant Design is used.",
                            "C": "C wrong: not used.",
                            "D": "D wrong: not used.",
                        },
                    },
                    "eval": {
                        "options": {"A": "Material UI", "B": "Ant Design", "C": "Bootstrap", "D": "Chakra UI"},
                        "answer": "B",
                    },
                }
            ],
        },
        {
            "id": "g2",
            "desc": "Database",
            "rounds": [
                {
                    "id": "q2",
                    "type": "multi_choice",
                    "question": "Which database is used?",
                    "feedback": {
                        "correct": "Correct!",
                        "options": {
                            "A": "A wrong: not used.",
                            "B": "B wrong: not used.",
                            "C": "C correct: SQLite is used.",
                            "D": "D wrong: not used.",
                        },
                    },
                    "eval": {
                        "options": {"A": "PostgreSQL", "B": "MySQL", "C": "SQLite", "D": "MongoDB"},
                        "answer": "C",
                    },
                }
            ],
        },
        {
            "id": "g3",
            "desc": "File check",
            "rounds": [
                {
                    "id": "q3",
                    "type": "file_check",
                    "question": "Generate output.json.",
                    "feedback": {"correct": "File OK!", "incorrect": "File missing."},
                    "eval": {
                        "command": "cat output.json",
                        "expect_exit": 0,
                    },
                }
            ],
        },
    ]
    (scenario_dir / "questions.json").write_text(json.dumps(questions), encoding="utf-8")
    return eval_dir


@pytest.fixture()
def all_tests_file(tmp_path: Path, questions_eval_dir: Path) -> Path:
    """Create a minimal all_tests.json."""
    oc_state = tmp_path / "openclaw_state"
    oc_state.mkdir()
    (oc_state / "openclaw.json").write_text("{}", encoding="utf-8")

    data = {
        "name": "test-suite",
        "openclaw_state_dir": str(oc_state),
        "eval_dir": str(questions_eval_dir),
        "workspace_src": str(oc_state),  # dummy, not used by scoring
        "test": [
            {
                "id": "task1_s1",
                "agent": "agent1",
                "session": "sess-1",
                "eval": "s1",
            }
        ],
    }
    f = tmp_path / "all_tests.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


@pytest.fixture()
def results_dir(tmp_path: Path) -> Path:
    """Create a minimal results directory with infer_result.json files."""
    results = tmp_path / "results"

    # Correct answer (bbox matches)
    p1 = results / "task1_s1" / "g1" / "q1"
    p1.mkdir(parents=True)
    (p1 / "infer_result.json").write_text(
        json.dumps({
            "test_id": "task1_s1",
            "group_id": "g1",
            "round_id": "q1",
            "qa_id": "q1",
            "status": "success",
            "answer": r"The frontend uses Ant Design. \bbox{B}",
            "llm_log": {
                "messages": [
                    {"role": "assistant", "usage": {"input": 100, "output": 50, "cacheRead": 20}},
                ]
            },
        }),
        encoding="utf-8",
    )

    # Wrong answer (bbox does not match)
    p2 = results / "task1_s1" / "g2" / "q2"
    p2.mkdir(parents=True)
    (p2 / "infer_result.json").write_text(
        json.dumps({
            "test_id": "task1_s1",
            "group_id": "g2",
            "round_id": "q2",
            "qa_id": "q2",
            "status": "success",
            "answer": r"I think it uses PostgreSQL. \bbox{A}",
            "llm_log": {
                "messages": [
                    {"role": "assistant", "usage": {"input": 80, "output": 30, "cacheRead": 0}},
                ]
            },
        }),
        encoding="utf-8",
    )

    # file_check result with inline_score passed=True
    p3 = results / "task1_s1" / "g3" / "q3"
    p3.mkdir(parents=True)
    (p3 / "infer_result.json").write_text(
        json.dumps({
            "test_id": "task1_s1",
            "group_id": "g3",
            "round_id": "q3",
            "qa_id": "q3",
            "status": "success",
            "answer": "",
            "inline_score": {"passed": True, "exit_code": 0, "stdout": "OK", "stderr": ""},
            "llm_log": {"messages": []},
        }),
        encoding="utf-8",
    )

    return results


# ---------------------------------------------------------------------------
# _extract_bbox_answer tests
# ---------------------------------------------------------------------------


def test_extract_bbox_answer_found() -> None:
    from src.scoring.scoring_cmd import _extract_bbox_answer

    assert _extract_bbox_answer(r"Answer is \bbox{B}") == {"B"}
    assert _extract_bbox_answer(r"Answer is \bbox{b}") == {"B"}  # case-insensitive
    assert _extract_bbox_answer(r"\bbox{D} is my answer") == {"D"}


def test_extract_bbox_answer_not_found() -> None:
    from src.scoring.scoring_cmd import _extract_bbox_answer

    assert _extract_bbox_answer("No answer here") is None
    assert _extract_bbox_answer("") is None
    assert _extract_bbox_answer(r"\bbox{} empty") is None


def test_extract_bbox_answer_multiple_takes_first() -> None:
    from src.scoring.scoring_cmd import _extract_bbox_answer

    # re.search returns the first match
    result = _extract_bbox_answer(r"Maybe \bbox{A} or \bbox{C}")
    assert result == {"A"}


def test_extract_bbox_answer_multi_letter() -> None:
    from src.scoring.scoring_cmd import _extract_bbox_answer

    assert _extract_bbox_answer(r"\bbox{A,B,C}") == {"A", "B", "C"}
    assert _extract_bbox_answer(r"\bbox{F,H,I}") == {"F", "H", "I"}
    assert _extract_bbox_answer(r"\bbox{a,b}") == {"A", "B"}  # case-insensitive


def test_extract_bbox_answer_boxed_alias() -> None:
    from src.scoring.scoring_cmd import _extract_bbox_answer

    # \boxed{} is the standard LaTeX command agents commonly use instead of \bbox{}
    assert _extract_bbox_answer(r"\boxed{B}") == {"B"}
    assert _extract_bbox_answer(r"\boxed{A,C,D,E,F}") == {"A", "C", "D", "E", "F"}
    assert _extract_bbox_answer(r"The answer is \boxed{A,C,D,E,F}") == {"A", "C", "D", "E", "F"}
    assert _extract_bbox_answer(r"\boxed{a,b,c}") == {"A", "B", "C"}  # case-insensitive


# ---------------------------------------------------------------------------
# _find_correct_answer tests
# ---------------------------------------------------------------------------


def test_find_correct_answer(all_tests_file: Path, questions_eval_dir: Path) -> None:
    from src.scoring.scoring_cmd import _find_correct_answer

    all_tests = json.loads(all_tests_file.read_text(encoding="utf-8"))
    # Answer is now inside eval sub-object
    result, q_num, question_type = _find_correct_answer(all_tests, "task1_s1", "g1", "q1")
    assert result == "B"
    assert q_num == 4
    assert question_type == "multi_choice"


def test_find_correct_answer_file_check(all_tests_file: Path, questions_eval_dir: Path) -> None:
    from src.scoring.scoring_cmd import _find_correct_answer

    all_tests = json.loads(all_tests_file.read_text(encoding="utf-8"))
    result, q_num, question_type = _find_correct_answer(all_tests, "task1_s1", "g3", "q3")
    assert result is None
    assert q_num == 0
    assert question_type == "file_check"


def test_find_correct_answer_missing_test(all_tests_file: Path) -> None:
    from src.scoring.scoring_cmd import _find_correct_answer

    all_tests = json.loads(all_tests_file.read_text(encoding="utf-8"))
    result, _, question_type = _find_correct_answer(all_tests, "no_such_test", "g1", "q1")
    assert result is None
    assert question_type == "multi_choice"


def test_find_correct_answer_missing_group(all_tests_file: Path) -> None:
    from src.scoring.scoring_cmd import _find_correct_answer

    all_tests = json.loads(all_tests_file.read_text(encoding="utf-8"))
    result, _, question_type = _find_correct_answer(all_tests, "task1_s1", "g99", "q1")
    assert result is None
    assert question_type == "multi_choice"


# ---------------------------------------------------------------------------
# run_scoring tests
# ---------------------------------------------------------------------------


def test_run_scoring_writes_scoring_json(
    all_tests_file: Path, results_dir: Path
) -> None:
    from src.scoring.scoring_cmd import run_scoring

    run_scoring(input_path=str(all_tests_file), result_dir=str(results_dir))

    s1 = results_dir / "task1_s1" / "g1" / "q1" / "scoring.json"
    s2 = results_dir / "task1_s1" / "g2" / "q2" / "scoring.json"
    assert s1.exists()
    assert s2.exists()

    d1 = json.loads(s1.read_text(encoding="utf-8"))
    assert d1["extracted_answer"] == ["B"]
    assert d1["correct_answer"] == ["B"]
    assert d1["score"] == 1

    d2 = json.loads(s2.read_text(encoding="utf-8"))
    assert d2["extracted_answer"] == ["A"]
    assert d2["correct_answer"] == ["C"]
    assert d2["score"] == 0.5


def test_run_scoring_overwrites_existing(
    all_tests_file: Path, results_dir: Path
) -> None:
    from src.scoring.scoring_cmd import run_scoring

    # Pre-write a scoring.json with stale content
    scoring_path = results_dir / "task1_s1" / "g1" / "q1" / "scoring.json"
    scoring_path.write_text(json.dumps({"score": 99}), encoding="utf-8")

    run_scoring(input_path=str(all_tests_file), result_dir=str(results_dir))

    # Should have overwritten with the correct computed score
    d = json.loads(scoring_path.read_text(encoding="utf-8"))
    assert d["score"] != 99
    assert d["correct_answer"] == ["B"]


def test_run_scoring_no_infer_files(tmp_path: Path, all_tests_file: Path) -> None:
    from src.scoring.scoring_cmd import run_scoring

    empty_dir = tmp_path / "empty_results"
    empty_dir.mkdir()
    # Should not raise, just warn
    run_scoring(input_path=str(all_tests_file), result_dir=str(empty_dir))


# ---------------------------------------------------------------------------
# file_check scoring
# ---------------------------------------------------------------------------


def test_score_file_check_passed(all_tests_file: Path, results_dir: Path) -> None:
    from src.scoring.scoring_cmd import run_scoring

    run_scoring(input_path=str(all_tests_file), result_dir=str(results_dir))

    scoring_path = results_dir / "task1_s1" / "g3" / "q3" / "scoring.json"
    assert scoring_path.exists()
    d = json.loads(scoring_path.read_text(encoding="utf-8"))
    assert d["question_type"] == "file_check"
    assert d["score"] == 1.0
    assert d["metrics"]["passed"] is True
    assert d["extracted_answer"] is None
    assert d["correct_answer"] is None


def test_score_file_check_failed() -> None:
    from src.scoring.scoring_cmd import _score_file_check

    infer_result = {"inline_score": {"passed": False, "exit_code": 1, "stdout": "", "stderr": ""}}
    result = _score_file_check(infer_result)
    assert result["score"] == 0.0
    assert result["metrics"]["passed"] is False


def test_score_file_check_missing_inline_score() -> None:
    from src.scoring.scoring_cmd import _score_file_check

    # No inline_score at all → defaults to failed
    result = _score_file_check({})
    assert result["score"] == 0.0
    assert result["metrics"]["passed"] is False


# ---------------------------------------------------------------------------
# report: _extract_agent_tokens tests
# ---------------------------------------------------------------------------


def test_extract_agent_tokens() -> None:
    from src.report.report_cmd import _extract_agent_tokens

    infer_result = {
        "llm_log": {
            "messages": [
                {"role": "user", "content": "Q?"},
                {"role": "assistant", "usage": {"input": 100, "output": 50, "cacheRead": 20}},
                {"role": "user", "content": "Q2?"},
                {"role": "assistant", "usage": {"input": 200, "output": 80, "cacheRead": 0}},
            ]
        }
    }
    tokens = _extract_agent_tokens(infer_result)
    assert tokens["input"] == 300
    assert tokens["output"] == 130
    assert tokens["cache_read"] == 20
    assert tokens["total_input"] == 320   # 300 + 20


def test_extract_agent_tokens_no_log() -> None:
    from src.report.report_cmd import _extract_agent_tokens

    tokens = _extract_agent_tokens({})
    assert tokens == {"input": 0, "output": 0, "cache_read": 0, "total_input": 0}


# ---------------------------------------------------------------------------
# report: _load_compaction_tokens tests
# ---------------------------------------------------------------------------


def test_load_compaction_tokens(tmp_path: Path) -> None:
    from src.report.report_cmd import _load_compaction_tokens

    data = {
        "task1_scenario1": {
            "compaction_result": {
                "llm_calls": [
                    {"input_tokens": 1000, "output_tokens": 200, "cached_tokens": 50},
                    {"input_tokens": 500, "output_tokens": 100, "cached_tokens": 0},
                ]
            }
        }
    }
    p = tmp_path / "compaction_results.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    result = _load_compaction_tokens(p)
    assert result["task1_scenario1"]["input"] == 1500
    assert result["task1_scenario1"]["output"] == 300
    assert result["task1_scenario1"]["cache_read"] == 50
    assert result["task1_scenario1"]["total_input"] == 1550  # 1500 + 50


def test_load_compaction_tokens_missing_file(tmp_path: Path) -> None:
    from src.report.report_cmd import _load_compaction_tokens

    result = _load_compaction_tokens(tmp_path / "nonexistent.json")
    assert result == {}


# ---------------------------------------------------------------------------
# run_report tests
# ---------------------------------------------------------------------------


def test_run_report_generates_files(
    all_tests_file: Path, results_dir: Path, tmp_path: Path
) -> None:
    from src.scoring.scoring_cmd import run_scoring
    from src.report.report_cmd import run_report

    # First score the results
    run_scoring(input_path=str(all_tests_file), result_dir=str(results_dir))

    # Then generate report
    out_dir = tmp_path / "report_out"
    run_report(result_dir=str(results_dir), output_dir=str(out_dir))

    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()

    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    # 3 results: q1 (score=1.0), q2 (score=0.5), q3 file_check (score=1.0)
    assert report["summary"]["total_questions"] == 3
    assert report["summary"]["correct"] == 2.5
    assert abs(report["summary"]["accuracy"] - 2.5 / 3) < 0.001

    # Token aggregation (file_check result has empty llm_log)
    agent_tokens = report["summary"]["tokens"]["agent"]
    assert agent_tokens["input"] == 180        # 100 + 80 (q3 has no usage)
    assert agent_tokens["output"] == 80        # 50 + 30
    assert agent_tokens["cache_read"] == 20    # 20 + 0
    assert agent_tokens["total_input"] == 200  # 180 + 20


def test_run_report_no_scoring_files(tmp_path: Path) -> None:
    from src.report.report_cmd import run_report

    empty = tmp_path / "empty"
    empty.mkdir()
    # Should not raise, even without output_dir
    run_report(result_dir=str(empty))


def test_run_report_no_output_dir_only_prints(
    all_tests_file: Path, results_dir: Path
) -> None:
    """Test that report command without --output only prints, no files saved."""
    from src.scoring.scoring_cmd import run_scoring
    from src.report.report_cmd import run_report

    # First score the results
    run_scoring(input_path=str(all_tests_file), result_dir=str(results_dir))

    # Run report without output_dir (should only print)
    run_report(result_dir=str(results_dir), output_dir=None)

    # Verify no report files were created in results_dir
    assert not (results_dir / "report.json").exists()
    assert not (results_dir / "report.md").exists()


# ---------------------------------------------------------------------------
# run: _generate_combined_reports tests
# ---------------------------------------------------------------------------


def test_generate_combined_reports(tmp_path: Path) -> None:
    from src.run.run_cmd import _generate_combined_reports

    reports = [
        ("set-a", {"summary": {"total_questions": 10, "correct": 8, "accuracy": 0.8,
                                "tokens": {
                                    "agent": {"input": 1000, "output": 500, "cache_read": 100, "total_input": 1100},
                                    "compaction": {"input": 200, "output": 80, "cache_read": 0, "total_input": 200},
                                }}}),
        ("set-b", {"summary": {"total_questions": 5, "correct": 3, "accuracy": 0.6,
                                "tokens": {
                                    "agent": {"input": 600, "output": 300, "cache_read": 0, "total_input": 600},
                                    "compaction": {"input": 0, "output": 0, "cache_read": 0, "total_input": 0},
                                }}}),
    ]
    _generate_combined_reports(tmp_path, reports)

    md_path = tmp_path / "reports.md"
    assert md_path.exists()
    md = md_path.read_text(encoding="utf-8")
    assert "set-a" in md
    assert "set-b" in md
    assert "80.0%" in md
    assert "60.0%" in md
    # Headers distinguish agent and compaction
    assert "Agent Total In" in md
    assert "Comp Total In" in md
    assert "1,100" in md   # set-a agent total_input
    assert "200" in md     # set-a compaction total_input
    # input/cache_read breakdown should NOT appear as columns
    assert "Cache Read" not in md
    assert "Agent Input" not in md


# ---------------------------------------------------------------------------
# report: compaction token multiplier tests
# ---------------------------------------------------------------------------


def test_run_report_compaction_multiplied_by_groups(
    all_tests_file: Path, results_dir: Path, tmp_path: Path
) -> None:
    """Compaction tokens should be multiplied by the number of question groups."""
    from src.scoring.scoring_cmd import run_scoring
    from src.report.report_cmd import run_report

    # Create compaction_results.json with base tokens per scenario
    compaction_data = {
        "task1_s1": {
            "compaction_result": {
                "llm_calls": [
                    {"input_tokens": 1000, "output_tokens": 200, "cached_tokens": 50},
                ]
            }
        }
    }
    compaction_path = tmp_path / "compaction_results.json"
    compaction_path.write_text(json.dumps(compaction_data), encoding="utf-8")

    run_scoring(input_path=str(all_tests_file), result_dir=str(results_dir))

    out_dir = tmp_path / "report_out"
    run_report(
        result_dir=str(results_dir),
        compaction_path=str(compaction_path),
        output_dir=str(out_dir),
    )

    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

    # The results_dir has 3 groups (g1, g2, g3) under task1_s1, so compaction
    # tokens should be multiplied by 3.
    task_comp = report["by_task"]["task1_s1"]["tokens"]["compaction"]
    assert task_comp["input"] == 3000       # 1000 * 3 groups
    assert task_comp["output"] == 600       # 200 * 3
    assert task_comp["cache_read"] == 150   # 50 * 3
    assert task_comp["total_input"] == 3150  # (1000+50) * 3

    # compaction_groups metadata
    assert report["by_task"]["task1_s1"]["tokens"]["compaction_groups"] == 3

    # Summary compaction tokens should also reflect the multiplier
    summary_comp = report["summary"]["tokens"]["compaction"]
    assert summary_comp["input"] == 3000
    assert summary_comp["total_input"] == 3150


# ---------------------------------------------------------------------------
# run: auto-discover compaction_results.json tests
# ---------------------------------------------------------------------------


def test_run_cmd_auto_discovers_compaction(
    all_tests_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_run() auto-detects compaction_results.json next to all_tests.json."""
    # Place compaction_results.json next to all_tests.json
    compaction_data = {
        "task1_s1": {
            "compaction_result": {
                "llm_calls": [
                    {"input_tokens": 500, "output_tokens": 100, "cached_tokens": 0},
                ]
            }
        }
    }
    comp_path = all_tests_file.parent / "compaction_results.json"
    comp_path.write_text(json.dumps(compaction_data), encoding="utf-8")

    import src.run.run_cmd as run_mod

    captured: list[dict] = []

    # Stub out infer and scoring so the test doesn't need a live openclaw
    async def _mock_infer(*args, **kwargs):
        pass

    monkeypatch.setattr(run_mod, "_run_one_all_tests", _mock_infer)
    monkeypatch.setattr(run_mod, "run_scoring", lambda *a, **kw: None)

    def _mock_run_report(result_dir: str, compaction_path=None, output_dir=None):
        captured.append({"compaction_path": compaction_path})

    monkeypatch.setattr(run_mod, "run_report", _mock_run_report)

    from src.run.run_cmd import run_run

    out_dir = tmp_path / "run_out_fresh"
    run_run(input_arg=str(all_tests_file), output_arg=str(out_dir), workers=1, retry=0)

    assert len(captured) == 1
    assert captured[0]["compaction_path"] is not None
    assert "compaction_results.json" in captured[0]["compaction_path"]


def test_run_cmd_no_compaction_when_file_absent(
    all_tests_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_run() passes compaction_path=None when no compaction_results.json exists."""
    import src.run.run_cmd as run_mod

    captured: list[dict] = []

    async def _mock_infer(*args, **kwargs):
        pass

    monkeypatch.setattr(run_mod, "_run_one_all_tests", _mock_infer)
    monkeypatch.setattr(run_mod, "run_scoring", lambda *a, **kw: None)

    def _mock_run_report(result_dir: str, compaction_path=None, output_dir=None):
        captured.append({"compaction_path": compaction_path})

    monkeypatch.setattr(run_mod, "run_report", _mock_run_report)

    from src.run.run_cmd import run_run

    out_dir = tmp_path / "run_out_fresh2"
    run_run(input_arg=str(all_tests_file), output_arg=str(out_dir), workers=1, retry=0)

    assert len(captured) == 1
    assert captured[0]["compaction_path"] is None


# ---------------------------------------------------------------------------
# report: metrics extraction and aggregation tests
# ---------------------------------------------------------------------------


def test_extract_metrics_basic() -> None:
    """Test basic metrics extraction from scoring.json."""
    from src.report.report_cmd import _extract_metrics

    scoring = {
        "test_id": "t1",
        "metrics": {
            "iou": 0.5,
            "precision": 1.0,
            "recall": 0.6,
            "f1": 0.75,
            "exact_match": 0.0,
        }
    }
    result = _extract_metrics(scoring, "t1", "g1", "r1")
    assert result == {
        "iou": 0.5,
        "precision": 1.0,
        "recall": 0.6,
        "f1": 0.75,
        "exact_match": 0.0,
    }


def test_extract_metrics_bool_to_int() -> None:
    """Test that bool values are converted to 0/1."""
    from src.report.report_cmd import _extract_metrics

    scoring = {
        "test_id": "t1",
        "metrics": {
            "exact_match": True,
            "has_error": False,
        }
    }
    result = _extract_metrics(scoring, "t1", "g1", "r1")
    assert result == {"exact_match": 1.0, "has_error": 0.0}


def test_extract_metrics_skip_non_numeric() -> None:
    """Test that non-numeric types are skipped."""
    from src.report.report_cmd import _extract_metrics

    scoring = {
        "test_id": "t1",
        "metrics": {
            "score": 0.8,
            "label": "good",  # string - should be skipped
            "items": [1, 2, 3],  # list - should be skipped
        }
    }
    result = _extract_metrics(scoring, "t1", "g1", "r1")
    assert result == {"score": 0.8}


def test_extract_metrics_no_metrics_field() -> None:
    """Test that missing metrics field returns empty dict."""
    from src.report.report_cmd import _extract_metrics

    scoring = {"test_id": "t1", "score": 1.0}
    result = _extract_metrics(scoring, "t1", "g1", "r1")
    assert result == {}


def test_extract_metrics_with_int() -> None:
    """Test that int values are converted to float."""
    from src.report.report_cmd import _extract_metrics

    scoring = {
        "test_id": "t1",
        "metrics": {
            "count": 5,
            "ratio": 0.5,
        }
    }
    result = _extract_metrics(scoring, "t1", "g1", "r1")
    assert result == {"count": 5.0, "ratio": 0.5}


def test_run_report_with_metrics(tmp_path: Path) -> None:
    """Test that metrics are aggregated correctly in report."""
    from src.report.report_cmd import run_report

    # Create test results with metrics
    results = tmp_path / "results"

    # Task 1, Question 1 with metrics
    p1 = results / "task1" / "g1" / "q1"
    p1.mkdir(parents=True)
    (p1 / "infer_result.json").write_text(
        json.dumps({
            "test_id": "task1",
            "group_id": "g1",
            "round_id": "q1",
            "status": "success",
            "answer": "Answer",
            "llm_log": {"messages": []},
        }),
        encoding="utf-8",
    )
    (p1 / "scoring.json").write_text(
        json.dumps({
            "test_id": "task1",
            "group_id": "g1",
            "round_id": "q1",
            "score": 1.0,
            "metrics": {
                "iou": 0.8,
                "precision": 1.0,
                "recall": 0.8,
            }
        }),
        encoding="utf-8",
    )

    # Task 1, Question 2 with metrics
    p2 = results / "task1" / "g2" / "q2"
    p2.mkdir(parents=True)
    (p2 / "infer_result.json").write_text(
        json.dumps({
            "test_id": "task1",
            "group_id": "g2",
            "round_id": "q2",
            "status": "success",
            "answer": "Answer",
            "llm_log": {"messages": []},
        }),
        encoding="utf-8",
    )
    (p2 / "scoring.json").write_text(
        json.dumps({
            "test_id": "task1",
            "group_id": "g2",
            "round_id": "q2",
            "score": 0.5,
            "metrics": {
                "iou": 0.6,
                "precision": 0.75,
                "recall": 0.6,
            }
        }),
        encoding="utf-8",
    )

    out_dir = tmp_path / "report_out"
    run_report(result_dir=str(results), output_dir=str(out_dir))

    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

    # Check task-level metrics (average of 2 questions)
    task_metrics = report["by_task"]["task1"]["metrics"]
    assert abs(task_metrics["iou"] - 0.7) < 0.001  # (0.8 + 0.6) / 2
    assert abs(task_metrics["precision"] - 0.875) < 0.001  # (1.0 + 0.75) / 2
    assert abs(task_metrics["recall"] - 0.7) < 0.001  # (0.8 + 0.6) / 2

    # Check summary metrics (average of all questions)
    summary_metrics = report["summary"]["metrics"]
    assert abs(summary_metrics["iou"] - 0.7) < 0.001
    assert abs(summary_metrics["precision"] - 0.875) < 0.001
    assert abs(summary_metrics["recall"] - 0.7) < 0.001

    # Check markdown contains metrics
    md = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "iou" in md
    assert "precision" in md
    assert "recall" in md


def test_run_report_mixed_metrics(tmp_path: Path) -> None:
    """Test report with some results having metrics and some not."""
    from src.report.report_cmd import run_report

    results = tmp_path / "results"

    # Question with metrics
    p1 = results / "task1" / "g1" / "q1"
    p1.mkdir(parents=True)
    (p1 / "infer_result.json").write_text(
        json.dumps({"test_id": "task1", "llm_log": {"messages": []}}),
        encoding="utf-8",
    )
    (p1 / "scoring.json").write_text(
        json.dumps({
            "test_id": "task1",
            "group_id": "g1",
            "round_id": "q1",
            "score": 1.0,
            "metrics": {"f1": 0.9}
        }),
        encoding="utf-8",
    )

    # Question without metrics
    p2 = results / "task1" / "g2" / "q2"
    p2.mkdir(parents=True)
    (p2 / "infer_result.json").write_text(
        json.dumps({"test_id": "task1", "llm_log": {"messages": []}}),
        encoding="utf-8",
    )
    (p2 / "scoring.json").write_text(
        json.dumps({
            "test_id": "task1",
            "group_id": "g2",
            "round_id": "q2",
            "score": 0.5,
        }),
        encoding="utf-8",
    )

    out_dir = tmp_path / "report_out"
    run_report(result_dir=str(results), output_dir=str(out_dir))

    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

    # Task metrics should be average of only those questions with metrics
    # In this case, only q1 has f1, so task average = 0.9 / 2 = 0.45 (weighted by all questions)
    task_metrics = report["by_task"]["task1"]["metrics"]
    assert abs(task_metrics["f1"] - 0.45) < 0.001  # 0.9 / 2 questions

    # Summary should also reflect this
    summary_metrics = report["summary"]["metrics"]
    assert abs(summary_metrics["f1"] - 0.45) < 0.001
