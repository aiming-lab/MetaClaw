"""Shared utilities for benchmark tools."""

from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    """Return the metaclaw-test project root directory.

    Checks the METACLAW_ROOT environment variable first.  Falls back to
    computing from this file's location: benchmark/src/utils.py is three
    levels below the project root.

      parent            → benchmark/src/
      parent.parent     → benchmark/
      parent.parent.parent → metaclaw-test/ (project root)
    """
    env_root = os.environ.get("METACLAW_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).parent.parent.parent


def resolve_path(p: str | Path, cwd: Path | None = None) -> Path:
    """Resolve a path relative to the project root.

    If *p* is already absolute, return it as-is.  Otherwise resolve it
    relative to *cwd* (defaults to the project root).
    """
    if cwd is None:
        cwd = get_project_root()
    path = Path(p)
    if path.is_absolute():
        return path
    return (cwd / path).resolve()
