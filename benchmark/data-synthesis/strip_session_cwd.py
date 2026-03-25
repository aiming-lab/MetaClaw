#!/usr/bin/env python3
"""Recursively find all .jsonl files under a directory and remove the "cwd"
field from the first line (if it is an openclaw session header with type="session").

Usage:
    python strip_session_cwd.py <root_dir>            # fix in-place
    python strip_session_cwd.py <root_dir> --dry-run  # preview only
    python strip_session_cwd.py                        # defaults to cwd
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def strip_cwd_from_file(path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Remove 'cwd' from the first line of *path* if it is a session header.

    Returns (changed, status_message).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"ERROR: cannot read file — {e}"

    lines = text.splitlines(keepends=True)
    if not lines:
        return False, "skipped (empty)"

    first = lines[0].rstrip("\n")
    if not first.strip():
        return False, "skipped (blank first line)"

    try:
        obj = json.loads(first)
    except json.JSONDecodeError as e:
        return False, f"skipped (first line not valid JSON: {e})"

    if obj.get("type") != "session":
        return False, "skipped (first line is not a session header)"

    if "cwd" not in obj:
        return False, "skipped (no cwd field)"

    del obj["cwd"]
    new_first = json.dumps(obj, ensure_ascii=False) + "\n"

    if dry_run:
        return True, f"dry-run: would remove cwd → {new_first.rstrip()}"

    lines[0] = new_first
    path.write_text("".join(lines), encoding="utf-8")
    return True, "removed cwd"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry_run = "--dry-run" in sys.argv

    root = Path(args[0]) if args else Path.cwd()
    if not root.exists():
        print(f"ERROR: directory not found: {root}")
        sys.exit(1)

    files = sorted(root.rglob("*.jsonl"))
    if not files:
        print(f"No .jsonl files found under: {root}")
        return

    mode = "DRY RUN — " if dry_run else ""
    print(f"{mode}Scanning {len(files)} .jsonl file(s) under:")
    print(f"  {root}\n")

    changed = skipped = errors = 0
    for f in files:
        ok, msg = strip_cwd_from_file(f, dry_run=dry_run)
        if "ERROR" in msg:
            tag = "ERR "
            errors += 1
        elif ok:
            tag = "FIXED" if not dry_run else "DRY  "
            if not dry_run:
                changed += 1
        else:
            tag = "SKIP "
            skipped += 1
        print(f"  [{tag}]  {f.relative_to(root)}: {msg}")

    print(f"\nDone.  fixed={changed}  skipped={skipped}  errors={errors}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
