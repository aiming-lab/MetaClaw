"""Benchmark report command.

Collects all scoring.json files, aggregates accuracy and token usage,
generates report.json and report.md.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from src.utils import resolve_path


def _empty_tokens() -> dict:
    return {"input": 0, "output": 0, "cache_read": 0, "total_input": 0}


def _add_tokens(a: dict, b: dict) -> dict:
    inp = a["input"] + b.get("input", 0)
    cache = a["cache_read"] + b.get("cache_read", 0)
    return {
        "input": inp,
        "output": a["output"] + b.get("output", 0),
        "cache_read": cache,
        "total_input": inp + cache,
    }


def _extract_agent_tokens(infer_result: dict) -> dict:
    """Extract token usage from infer_result.json llm_log."""
    tokens = _empty_tokens()
    llm_log = infer_result.get("llm_log")
    if not llm_log or not isinstance(llm_log, dict):
        return tokens
    messages = llm_log.get("messages", [])
    for msg in messages:
        if msg.get("role") == "assistant":
            usage = msg.get("usage", {})
            tokens["input"] += usage.get("input", 0)
            tokens["output"] += usage.get("output", 0)
            tokens["cache_read"] += usage.get("cacheRead", 0)
    tokens["total_input"] = tokens["input"] + tokens["cache_read"]
    return tokens


def _extract_metrics(scoring: dict, test_id: str, group_id: str, round_id: str) -> dict[str, float]:
    """Extract numeric metrics from scoring.json.

    Converts bool to 0/1, keeps int/float, skips other types.
    Prints warning if any field fails.
    """
    metrics = scoring.get("metrics")
    if not metrics or not isinstance(metrics, dict):
        return {}

    result = {}
    for key, value in metrics.items():
        try:
            if isinstance(value, bool):
                result[key] = float(value)
            elif isinstance(value, (int, float)):
                result[key] = float(value)
            else:
                # Skip non-numeric types silently
                continue
        except Exception as e:
            print(f"[warn] Failed to extract metric '{key}' for {test_id}/{group_id}/{round_id}: {e}")

    return result


def _load_compaction_tokens(compaction_path: Path) -> dict[str, dict]:
    """Load compaction tokens per test_id from compaction_results.json.

    Returns dict: test_id -> {"input": ..., "output": ..., "cache_read": ...}
    """
    result = {}
    if not compaction_path or not compaction_path.exists():
        return result

    data = json.loads(compaction_path.read_text(encoding="utf-8"))
    for test_id, test_data in data.items():
        tokens = _empty_tokens()
        comp_result = test_data.get("compaction_result", {})
        for call in comp_result.get("llm_calls", []):
            tokens["input"] += call.get("input_tokens", 0)
            tokens["output"] += call.get("output_tokens", 0)
            tokens["cache_read"] += call.get("cached_tokens", 0)
        tokens["total_input"] = tokens["input"] + tokens["cache_read"]
        result[test_id] = tokens
    return result


def _render_markdown(report: dict) -> str:
    """Render report as markdown table."""
    lines = ["# Benchmark Report", ""]

    summary = report["summary"]
    tokens = summary.get("tokens", {})
    agent_tok = tokens.get("agent", {})
    comp_tok = tokens.get("compaction", {})
    lines += [
        "## Summary",
        "",
        f"- **Total questions**: {summary['total_questions']}",
        f"- **Correct**: {summary['correct']:.1f}",
        f"- **Accuracy**: {summary['accuracy']:.1%}",
        "",
        "### Token Usage",
        "",
        "| Type | Total Input | Output |",
        "|------|-------------|--------|",
        f"| agent | {agent_tok.get('total_input', 0):,} | {agent_tok.get('output', 0):,} |",
        f"| compaction | {comp_tok.get('total_input', 0):,} | {comp_tok.get('output', 0):,} |",
    ]

    # Add metrics if available
    metrics = summary.get("metrics", {})
    if metrics:
        lines += ["", "### Metrics (Average)", ""]
        for key in sorted(metrics.keys()):
            value = metrics[key]
            lines.append(f"- **{key}**: {value:.4f}")

    lines += ["", "## By Task", ""]

    # Collect all metric keys from all tasks
    all_metric_keys = set()
    for task_data in report["by_task"].values():
        all_metric_keys.update(task_data.get("metrics", {}).keys())

    # Build table header
    header = "| Task | Questions | Correct | Accuracy |"
    separator = "|------|-----------|---------|----------|"
    for key in sorted(all_metric_keys):
        header += f" {key} |"
        separator += "------|"
    lines.append(header)
    lines.append(separator)

    # Build table rows
    for task_id, task_data in sorted(report["by_task"].items()):
        q_count = len(task_data.get("questions", []))
        correct = sum(q["score"] for q in task_data.get("questions", []))
        acc = task_data["accuracy"]
        row = f"| {task_id} | {q_count} | {correct:.1f} | {acc:.1%} |"

        task_metrics = task_data.get("metrics", {})
        for key in sorted(all_metric_keys):
            if key in task_metrics:
                row += f" {task_metrics[key]:.4f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines) + "\n"


def run_report(
    result_dir: str,
    compaction_path: str | None = None,
    output_dir: str | None = None,
) -> None:
    """Generate report from scoring results.

    Args:
        result_dir: Directory containing scoring.json files
        compaction_path: Optional path to compaction_results.json
        output_dir: Output directory. If None, only print to terminal (no files saved)
    """
    result_root = resolve_path(result_dir)

    # Prepare output directory if specified
    if output_dir:
        out_root = resolve_path(output_dir)
        out_root.mkdir(parents=True, exist_ok=True)
    else:
        out_root = None

    # Load compaction tokens
    comp_tokens_by_test: dict[str, dict] = {}
    if compaction_path:
        comp_path = resolve_path(compaction_path)
        comp_tokens_by_test = _load_compaction_tokens(comp_path)

    # Collect all scoring.json files
    scoring_files = sorted(result_root.rglob("scoring.json"))
    if not scoring_files:
        print(f"[warn] No scoring.json found under {result_root}")
        return

    # Build by_task structure
    by_task: dict[str, dict] = {}

    for scoring_path in scoring_files:
        try:
            scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        test_id = scoring.get("test_id", "unknown")
        group_id = scoring.get("group_id", "unknown")
        round_id = scoring.get("round_id", "unknown")
        score = scoring.get("score", 0)

        if test_id not in by_task:
            by_task[test_id] = {
                "accuracy": 0.0,
                "tokens": {
                    "agent": _empty_tokens(),
                    "compaction": _empty_tokens(),
                },
                "questions": [],
                "metrics": {},  # Will hold sum of metrics
            }

        # Load corresponding infer_result.json for token usage
        infer_path = scoring_path.parent / "infer_result.json"
        agent_tokens = _empty_tokens()
        if infer_path.exists():
            try:
                infer_result = json.loads(infer_path.read_text(encoding="utf-8"))
                agent_tokens = _extract_agent_tokens(infer_result)
            except Exception:
                pass

        # Extract metrics
        metrics = _extract_metrics(scoring, test_id, group_id, round_id)

        by_task[test_id]["questions"].append({
            "group_id": group_id,
            "round_id": round_id,
            "score": score,
            "tokens": {"agent": agent_tokens},
            "metrics": metrics,
        })
        by_task[test_id]["tokens"]["agent"] = _add_tokens(
            by_task[test_id]["tokens"]["agent"], agent_tokens
        )

        # Accumulate metrics
        for key, value in metrics.items():
            if key not in by_task[test_id]["metrics"]:
                by_task[test_id]["metrics"][key] = 0.0
            by_task[test_id]["metrics"][key] += value

    # Fill compaction tokens and compute accuracy per task
    summary_tokens = {
        "agent": _empty_tokens(),
        "compaction": _empty_tokens(),
    }
    summary_metrics: dict[str, float] = {}
    total_questions = 0
    total_correct = 0

    for test_id, task_data in by_task.items():
        questions = task_data["questions"]
        correct = sum(q["score"] for q in questions)
        task_data["accuracy"] = correct / len(questions) if questions else 0.0

        # Compute average metrics for this task
        num_questions = len(questions)
        if num_questions > 0:
            for key in task_data["metrics"]:
                task_data["metrics"][key] /= num_questions

        # Compaction tokens for this test.
        # Compaction is run once per scenario to produce a compacted session.
        # However, each question *group* receives its own independent session copy,
        # so the compaction cost is effectively incurred once per group (rounds
        # within the same group share the session and do NOT re-compact).
        num_groups = len({q["group_id"] for q in questions})
        comp_tok_base = comp_tokens_by_test.get(test_id)
        if comp_tok_base is None:
            # Try matching with _compact_ suffix stripped
            base_id = test_id.split("_compact")[0]
            for k in comp_tokens_by_test:
                if test_id.startswith(k) or k.startswith(base_id):
                    comp_tok_base = comp_tokens_by_test[k]
                    break
        if comp_tok_base is None:
            comp_tok_base = _empty_tokens()
        # Scale by the number of groups
        comp_tok = {
            "input": comp_tok_base["input"] * num_groups,
            "output": comp_tok_base["output"] * num_groups,
            "cache_read": comp_tok_base["cache_read"] * num_groups,
            "total_input": comp_tok_base["total_input"] * num_groups,
        }
        task_data["tokens"]["compaction"] = comp_tok
        task_data["tokens"]["compaction_groups"] = num_groups

        summary_tokens["agent"] = _add_tokens(summary_tokens["agent"], task_data["tokens"]["agent"])
        summary_tokens["compaction"] = _add_tokens(summary_tokens["compaction"], comp_tok)

        # Accumulate metrics to summary
        for key, value in task_data["metrics"].items():
            if key not in summary_metrics:
                summary_metrics[key] = 0.0
            summary_metrics[key] += value * num_questions  # Weight by number of questions

        total_questions += len(questions)
        total_correct += correct

    # Compute average metrics across all questions
    if total_questions > 0:
        for key in summary_metrics:
            summary_metrics[key] /= total_questions

    report = {
        "summary": {
            "total_questions": total_questions,
            "correct": total_correct,
            "accuracy": total_correct / total_questions if total_questions else 0.0,
            "tokens": summary_tokens,
            "metrics": summary_metrics,
        },
        "by_task": by_task,
    }

    # Render markdown
    md = _render_markdown(report)

    # Save files if output directory specified
    if out_root:
        report_json_path = out_root / "report.json"
        report_json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Written: {report_json_path}")

        report_md_path = out_root / "report.md"
        report_md_path.write_text(md, encoding="utf-8")
        print(f"Written: {report_md_path}")

    # Always print to terminal
    print("\n" + md)
