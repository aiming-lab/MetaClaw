"""Benchmark clean command — remove work/ isolation directories."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.utils import resolve_path


def run_clean(path_arg: str) -> None:
    """Recursively find and remove all ``work/`` directories under *path_arg*.

    These directories are created by ``infer`` for per-run session and
    workspace isolation.  Cleaning them frees disk space and lets the next
    ``infer`` run start with a pristine copy of the original data.

    Args:
        path_arg: Root path to search (relative paths resolved from project root).
    """
    root = resolve_path(path_arg)
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")

    for pattern in ["work", "llm_prompts", "memory_runs"]:
        # Collect all directory name patterns, sorted so parents come before children.
        # We skip children that fall under an already-removed parent to avoid errors.
        candidates = sorted(p for p in root.rglob(pattern) if p.is_dir())
        removed: list[Path] = []

        for d in candidates:
            # Skip if an ancestor was already removed.
            if any(d.is_relative_to(r) for r in removed):
                continue
            shutil.rmtree(d)
            removed.append(d)
            print(f"Removed: {d}")

        if not removed:
            print(f"No {pattern}/ directories found under: {root}")
        else:
            n = len(removed)
            print(f"\nCleaned {n} {pattern}/ director{'y' if n == 1 else 'ies'}.")
