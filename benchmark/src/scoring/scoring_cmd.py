"""Benchmark scoring command.

For each infer_result.json found under the result directory, extracts the
model's answer or reads inline_score (for file_check), and writes scoring.json
to the same directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.utils import resolve_path


def _extract_bbox_answer(text: str) -> set[str] | None:
    r"""Extract letters from \bbox{...} or \boxed{...} pattern in text.

    Supports single letter (\bbox{B}) and multi-letter (\bbox{A,B,C}).
    Also accepts the standard LaTeX \boxed{} command as an alias.
    Returns a set of uppercase letters, or None if no match found.
    """
    match = re.search(r"\\(?:bbox|boxed)\{([^}]*)\}", text)
    if match:
        letters = re.findall(r"[A-Za-z]", match.group(1))
        if letters:
            return {l.upper() for l in letters}
    return None


def _normalize_answer(answer: Any) -> set[str]:
    """Normalize a raw answer value (str or list) to a set of uppercase letters."""
    if isinstance(answer, list):
        result: set[str] = set()
        for item in answer:
            result.update(re.findall(r"[A-Za-z]", str(item)))
        return {l.upper() for l in result}
    if isinstance(answer, str):
        letters = re.findall(r"[A-Za-z]", answer)
        return {l.upper() for l in letters}
    return set()


def _find_correct_answer(
    all_tests: dict,
    test_id: str,
    group_id: str,
    round_id: str,
) -> tuple[Any, int, str]:
    """Find the correct answer for a given test/group/round from questions.json.

    Reads answer and options from the ``eval`` sub-object of each round.

    Returns:
        (answer, q_num, question_type)
        For file_check: (None, 0, "file_check")
        For multi_choice: (answer_raw, len(options), "multi_choice")
    """
    test_entry = next(
        (t for t in all_tests.get("test", []) if t["id"] == test_id), None
    )
    if not test_entry:
        return None, 0, "multi_choice"

    eval_dir = resolve_path(all_tests["eval_dir"])
    eval_name = test_entry["eval"]
    questions_path = eval_dir / eval_name / "questions.json"
    if not questions_path.exists():
        return None, 0, "multi_choice"

    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    if isinstance(questions, dict):
        questions = [questions]

    for group in questions:
        if group["id"] == group_id:
            for round_rec in group.get("rounds", []):
                if round_rec["id"] == round_id:
                    question_type = round_rec.get("type", "multi_choice")
                    if question_type == "file_check":
                        return None, 0, "file_check"
                    eval_cfg = round_rec.get("eval", {})
                    answer = eval_cfg.get("answer", "")
                    q_num = len(eval_cfg.get("options", {}))
                    return answer, q_num, question_type
    return None, 0, "multi_choice"


def calculate_multichoice_metrics(
    answer: set, ground: set, q_num: int
) -> tuple[float, dict]:
    """Calculate multi-choice answer metrics.

    Returns:
        (score, metrics_dict)
    """
    if answer is None or not ground:
        return 0, {}

    tp = len(answer & ground)
    fp = len(answer - ground)
    fn = len(ground - answer)

    exact_match = 1.0 if answer == ground else 0.0

    union = len(answer | ground)
    iou = tp / union if union != 0 else 0.0

    precision_denominator = tp + fp
    precision = (
        tp / precision_denominator
        if precision_denominator != 0
        else (1.0 if ground == set() else 0.0)
    )

    recall_denominator = tp + fn
    recall = tp / recall_denominator if recall_denominator != 0 else 1.0

    f1_denominator = precision + recall
    f1 = 2 * precision * recall / f1_denominator if f1_denominator != 0 else 0.0

    score = 1 - (fp + fn) / q_num

    metrics = {
        "iou": iou,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match": exact_match,
    }
    return score, metrics


def _score_multi_choice(
    answer_text: str,
    correct_raw: Any,
    q_num: int,
) -> dict[str, Any]:
    """Score a multi_choice round."""
    extracted_set = _extract_bbox_answer(answer_text) if answer_text else None
    correct_set = _normalize_answer(correct_raw) if correct_raw is not None else None
    score, metrics = calculate_multichoice_metrics(extracted_set, correct_set, q_num)
    return {
        "extracted_answer": sorted(extracted_set) if extracted_set is not None else None,
        "correct_answer": sorted(correct_set) if correct_set is not None else None,
        "score": score,
        "metrics": metrics,
    }


def _score_file_check(infer_result: dict) -> dict[str, Any]:
    """Score a file_check round by reading inline_score from infer_result."""
    inline = infer_result.get("inline_score", {})
    passed = inline.get("passed", False)
    return {
        "extracted_answer": None,
        "correct_answer": None,
        "score": 1.0 if passed else 0.0,
        "metrics": {"passed": passed},
    }


def _score_round(
    question_type: str,
    answer_text: str,
    correct_raw: Any,
    q_num: int,
    infer_result: dict | None = None,
) -> dict[str, Any]:
    """Dispatch scoring to the appropriate scorer based on question_type."""
    if question_type == "multi_choice":
        return _score_multi_choice(answer_text, correct_raw, q_num)

    if question_type == "file_check":
        return _score_file_check(infer_result or {})

    return {
        "extracted_answer": None,
        "correct_answer": None,
        "score": 0.0,
        "metrics": {},
    }


def _score_one(
    infer_result_path: Path,
    all_tests: dict,
) -> dict[str, Any] | None:
    """Score one infer_result.json and return scoring record."""
    try:
        result = json.loads(infer_result_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    parts = infer_result_path.parts
    round_id = parts[-2]
    group_id = parts[-3]
    test_id = parts[-4]

    test_id = result.get("test_id", test_id)
    group_id = result.get("group_id", group_id)
    round_id = result.get("round_id", result.get("qa_id", round_id))

    answer_text = result.get("answer", "")

    correct_raw, q_num, question_type = _find_correct_answer(
        all_tests, test_id, group_id, round_id
    )
    question_type = result.get("question_type", question_type)

    scored = _score_round(question_type, answer_text, correct_raw, q_num, infer_result=result)

    return {
        "test_id": test_id,
        "group_id": group_id,
        "round_id": round_id,
        "question_type": question_type,
        **scored,
    }


def run_scoring(input_path: str, result_dir: str) -> None:
    """Run scoring on all infer_result.json files.

    Args:
        input_path: Path to all_tests.json
        result_dir: Directory to recursively search for infer_result.json files
    """
    input_file = resolve_path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    all_tests = json.loads(input_file.read_text(encoding="utf-8"))
    result_root = resolve_path(result_dir)

    infer_files = sorted(result_root.rglob("infer_result.json"))
    if not infer_files:
        print(f"[warn] No infer_result.json found under {result_root}")
        return

    scored = 0
    total = 0
    for infer_path in infer_files:
        total += 1
        scoring_path = infer_path.parent / "scoring.json"

        record = _score_one(infer_path, all_tests)
        if record is None:
            print(f"  [fail] could not score {infer_path.relative_to(result_root)}")
            continue

        scoring_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        s = record["score"]
        ex = ",".join(record["extracted_answer"]) if record["extracted_answer"] else "?"
        cor = ",".join(record["correct_answer"]) if record["correct_answer"] else "?"
        print(
            f"  [{'✓' if s else '✗'}] {record['test_id']}/{record['group_id']}/{record['round_id']}: "
            f"{ex} vs {cor} → {s}"
        )
        scored += 1

    print(f"\nScoring complete: {scored}/{total} processed. Results in: {result_root}")
