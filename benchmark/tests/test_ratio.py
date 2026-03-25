"""Tests for benchmark/src/report/ratio_cmd.py and compact summary append."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# ratio_cmd: compute_ratio tests
# ---------------------------------------------------------------------------


def _make_report(by_task: dict) -> dict:
    """Build a minimal report dict with by_task."""
    return {"summary": {}, "by_task": by_task}


def _make_questions(pairs: list[tuple[str, str, int]]) -> list[dict]:
    """Build questions list from (group_id, round_id, total_input) triples."""
    return [
        {
            "group_id": g,
            "round_id": r,
            "score": 1,
            "tokens": {"agent": {"input": ti, "output": 0, "cache_read": 0, "total_input": ti}},
        }
        for g, r, ti in pairs
    ]


def test_compute_ratio_basic() -> None:
    from src.report.ratio_cmd import compute_ratio

    base = _make_report({
        "task1": {
            "accuracy": 1.0,
            "questions": _make_questions([("g1", "r1", 1000), ("g2", "r1", 2000)]),
            "tokens": {},
        },
    })
    comp = _make_report({
        "task1_compact_openclaw": {
            "accuracy": 1.0,
            "questions": _make_questions([("g1", "r1", 500), ("g2", "r1", 800)]),
            "tokens": {},
        },
    })

    result = compute_ratio(base, comp)
    assert result["summary"] == pytest.approx((0.5 + 0.6) / 2)
    assert result["by_task"]["task1_compact_openclaw"]["g1_r1"] == pytest.approx(0.5)
    assert result["by_task"]["task1_compact_openclaw"]["g2_r1"] == pytest.approx(0.6)


def test_compute_ratio_missing_question_skipped() -> None:
    from src.report.ratio_cmd import compute_ratio

    base = _make_report({
        "task1": {
            "accuracy": 1.0,
            "questions": _make_questions([("g1", "r1", 1000)]),
            "tokens": {},
        },
    })
    comp = _make_report({
        "task1_compact_openclaw": {
            "accuracy": 1.0,
            "questions": _make_questions([("g1", "r1", 500), ("g99", "r1", 100)]),
            "tokens": {},
        },
    })

    result = compute_ratio(base, comp)
    # g99 has no base match, should be skipped
    assert "g99_r1" not in result["by_task"].get("task1_compact_openclaw", {})
    assert result["summary"] == pytest.approx(0.5)


def test_compute_ratio_no_match() -> None:
    from src.report.ratio_cmd import compute_ratio

    base = _make_report({"taskA": {"accuracy": 1.0, "questions": [], "tokens": {}}})
    comp = _make_report({"taskB": {"accuracy": 1.0, "questions": [], "tokens": {}}})

    result = compute_ratio(base, comp)
    assert result["summary"] is None
    assert result["by_task"] == {}


# ---------------------------------------------------------------------------
# ratio_cmd: run_report_ratio tests
# ---------------------------------------------------------------------------


def test_run_report_ratio_writes_file(tmp_path: Path) -> None:
    from src.report.ratio_cmd import run_report_ratio

    base = _make_report({
        "t1": {"accuracy": 1.0, "questions": _make_questions([("g1", "r1", 1000)]), "tokens": {}},
    })
    comp = _make_report({
        "t1": {"accuracy": 1.0, "questions": _make_questions([("g1", "r1", 400)]), "tokens": {}},
    })

    base_path = tmp_path / "base" / "report.json"
    base_path.parent.mkdir()
    base_path.write_text(json.dumps(base), encoding="utf-8")

    comp_path = tmp_path / "comp" / "report.json"
    comp_path.parent.mkdir()
    comp_path.write_text(json.dumps(comp), encoding="utf-8")

    out = tmp_path / "out"
    result = run_report_ratio(str(base_path), [str(comp_path)], str(out))

    assert (out / "ratio_report.json").exists()
    assert len(result["compaction_ratios"]) == 1
    assert result["compaction_ratios"][0]["summary"] == pytest.approx(0.6)


def test_run_report_ratio_dir_input(tmp_path: Path) -> None:
    from src.report.ratio_cmd import run_report_ratio

    base = _make_report({
        "t1": {"accuracy": 1.0, "questions": _make_questions([("g1", "r1", 100)]), "tokens": {}},
    })
    comp = _make_report({
        "t1": {"accuracy": 1.0, "questions": _make_questions([("g1", "r1", 60)]), "tokens": {}},
    })

    base_path = tmp_path / "base" / "report.json"
    base_path.parent.mkdir()
    base_path.write_text(json.dumps(base), encoding="utf-8")

    # Put comp report.json in a subdirectory; pass the parent as directory
    comp_dir = tmp_path / "comps"
    comp_sub = comp_dir / "run1"
    comp_sub.mkdir(parents=True)
    (comp_sub / "report.json").write_text(json.dumps(comp), encoding="utf-8")

    out = tmp_path / "out"
    result = run_report_ratio(str(base_path), [str(comp_dir)], str(out))
    assert result["compaction_ratios"][0]["summary"] == pytest.approx(0.4)


def test_run_report_ratio_no_output_dir_only_prints(tmp_path: Path) -> None:
    """Test that report-ratio command without --output only prints, no files saved."""
    from src.report.ratio_cmd import run_report_ratio

    base = _make_report({
        "t1": {"accuracy": 1.0, "questions": _make_questions([("g1", "r1", 1000)]), "tokens": {}},
    })
    comp = _make_report({
        "t1": {"accuracy": 1.0, "questions": _make_questions([("g1", "r1", 400)]), "tokens": {}},
    })

    base_path = tmp_path / "base" / "report.json"
    base_path.parent.mkdir()
    base_path.write_text(json.dumps(base), encoding="utf-8")

    comp_path = tmp_path / "comp" / "report.json"
    comp_path.parent.mkdir()
    comp_path.write_text(json.dumps(comp), encoding="utf-8")

    # Run without output_dir (should only print)
    result = run_report_ratio(str(base_path), [str(comp_path)], output_dir=None)

    # Verify result is computed correctly
    assert len(result["compaction_ratios"]) == 1
    assert result["compaction_ratios"][0]["summary"] == pytest.approx(0.6)

    # Verify no ratio_report.json was created anywhere
    assert not (base_path.parent / "ratio_report.json").exists()
    assert not (comp_path.parent / "ratio_report.json").exists()
    assert not (tmp_path / "ratio_report.json").exists()


# ---------------------------------------------------------------------------
# _generate_combined_reports with ratio_results tests
# ---------------------------------------------------------------------------


def test_combined_reports_includes_ratio(tmp_path: Path) -> None:
    from src.run.run_cmd import _generate_combined_reports

    reports = [
        ("base", {"summary": {"total_questions": 10, "correct": 8, "accuracy": 0.8,
                               "tokens": {"agent": {"total_input": 1000, "output": 100},
                                          "compaction": {"total_input": 0, "output": 0}}}}),
        ("comp", {"summary": {"total_questions": 10, "correct": 7, "accuracy": 0.7,
                               "tokens": {"agent": {"total_input": 500, "output": 80},
                                          "compaction": {"total_input": 200, "output": 40}}}}),
    ]
    ratio_results = [
        ("comp", "base", {
            "compaction_ratios": [{"summary": 0.45, "by_task": {}}],
        }),
    ]
    _generate_combined_reports(tmp_path, reports, ratio_results)

    md = (tmp_path / "reports.md").read_text(encoding="utf-8")
    assert "Compaction Ratios" in md
    assert "0.4500" in md
    assert "comp" in md
    assert "base" in md
