"""Benchmark report-ratio command.

Computes compaction ratios by comparing compaction report.json files against
a baseline report.json.  Matching is done at the finest granularity
(task → group_id + round_id) so that per-question input-token ratios are
preserved and the summary is a true mean of per-question ratios.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from src.utils import resolve_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_report_jsons(paths: list[str]) -> list[Path]:
    """Expand a list of paths (files or directories) into report.json Paths."""
    result: list[Path] = []
    for p_str in paths:
        p = resolve_path(p_str)
        if p.is_file():
            result.append(p)
        elif p.is_dir():
            result.extend(sorted(p.rglob("report.json")))
        else:
            print(f"[warn] Skipping non-existent path: {p}")
    return result


def _build_base_index(report: dict) -> dict[str, dict[str, float]]:
    """Build a lookup: task_id → { 'gX_rY': total_input, ... }."""
    index: dict[str, dict[str, float]] = {}
    for task_id, task_data in report.get("by_task", {}).items():
        per_q: dict[str, float] = {}
        for q in task_data.get("questions", []):
            key = f"{q['group_id']}_{q['round_id']}"
            ti = q.get("tokens", {}).get("agent", {}).get("total_input", 0)
            per_q[key] = ti
        index[task_id] = per_q
    return index


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def compute_ratio(base_report: dict, comp_report: dict) -> dict:
    """Compute per-question compaction ratios.

    Returns dict with ``summary`` (mean ratio) and ``by_task`` breakdown.
    Ratio = 1 - comp_total_input / base_total_input (higher is better, means more savings).
    Questions missing from either side are silently skipped.
    """
    base_idx = _build_base_index(base_report)
    all_ratios: list[float] = []
    by_task: dict[str, dict[str, float]] = {}

    for task_id, task_data in comp_report.get("by_task", {}).items():
        # Strip _compact_xxx suffix to match base task_id
        base_task_id = task_id.split("_compact")[0] if "_compact" in task_id else task_id
        base_qs = base_idx.get(base_task_id, {})
        if not base_qs:
            continue

        task_ratios: dict[str, float] = {}
        for q in task_data.get("questions", []):
            key = f"{q['group_id']}_{q['round_id']}"
            base_ti = base_qs.get(key)
            if base_ti is None or base_ti == 0:
                continue
            comp_ti = q.get("tokens", {}).get("agent", {}).get("total_input", 0)
            ratio = 1 - comp_ti / base_ti
            task_ratios[key] = ratio
            all_ratios.append(ratio)

        if task_ratios:
            by_task[task_id] = task_ratios

    return {
        "summary": mean(all_ratios) if all_ratios else None,
        "by_task": by_task,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_report_ratio(
    base_path: str,
    compaction_paths: list[str],
    output_dir: str | None = None,
) -> dict:
    """Compute compaction ratios and write ratio_report.json.

    Args:
        base_path: Path to the baseline report.json.
        compaction_paths: List of paths to compaction report.json files or
            directories containing them.
        output_dir: Output directory. If None, only print to terminal (no files saved)

    Returns:
        The full ratio report dict.
    """
    base_file = resolve_path(base_path)
    if not base_file.exists():
        raise FileNotFoundError(f"Base report not found: {base_file}")
    base_report = json.loads(base_file.read_text(encoding="utf-8"))

    comp_files = _collect_report_jsons(compaction_paths)
    if not comp_files:
        print("[warn] No compaction report.json files found")
        return {}

    ratios_list: list[dict] = []
    for cf in comp_files:
        comp_report = json.loads(cf.read_text(encoding="utf-8"))
        ratio_data = compute_ratio(base_report, comp_report)
        ratios_list.append({
            "compaction_report": str(cf),
            **ratio_data,
        })

    result = {
        "base_report": str(base_file),
        "compaction_ratios": ratios_list,
    }

    # Save file if output directory specified
    if output_dir:
        out = resolve_path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        out_file = out / "ratio_report.json"
        out_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Written: {out_file}")

    # Always print to terminal
    print("\nRatio Report:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return result
