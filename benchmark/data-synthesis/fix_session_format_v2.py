#!/usr/bin/env python3
"""Fix openclaw session files (second pass) — applied after fix_session_format.py.

Changes applied to already-converted files:
  Line 1  (type=session)          : remove "cwd" field
  Line 2  (type=model_change)     : provider → "anthropic", modelId → "claude-sonnet-4-6"
  Line 4  (type=custom/model-snap): data.provider → "anthropic", data.modelId → "claude-sonnet-4-6"
  user messages                   : add "timestamp" (unix ms) inside message dict
  assistant messages              : add api/provider/model/usage inside message dict

Usage:
    python fix_session_format_v2.py            # fix in-place
    python fix_session_format_v2.py --dry-run  # preview only
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SESSIONS_DIR = (
    Path(__file__).parent.parent
    / "benchmark/data/metaclaw-bench/openclaw_state/agents/metaclaw_agent/sessions"
)

PROVIDER  = "anthropic"
MODEL_ID  = "claude-sonnet-4-6"
MODEL_API = "openai-completions"

ASSISTANT_EXTRA = {
    "api":      MODEL_API,
    "provider": PROVIDER,
    "model":    MODEL_ID,
    "usage":    {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
}

# ---------------------------------------------------------------------------
# Per-line fixers
# ---------------------------------------------------------------------------


def _fix_line(obj: dict) -> dict:
    """Return a (possibly modified) copy of obj with all corrections applied."""
    t = obj.get("type")

    if t == "session":
        obj = {k: v for k, v in obj.items() if k != "cwd"}

    elif t == "model_change":
        obj = {**obj, "provider": PROVIDER, "modelId": MODEL_ID}

    elif t == "custom" and obj.get("customType") == "model-snapshot":
        data = {**obj.get("data", {}), "provider": PROVIDER, "modelId": MODEL_ID}
        obj = {**obj, "data": data}

    elif t == "message":
        msg = dict(obj.get("message", {}))
        role = msg.get("role")

        if role == "user":
            # Add unix-ms timestamp inside message dict if missing
            if "timestamp" not in msg:
                outer_ts: str = obj.get("timestamp", "")
                try:
                    dt = datetime.strptime(outer_ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                        tzinfo=timezone.utc
                    )
                    msg["timestamp"] = int(dt.timestamp() * 1000)
                except ValueError:
                    pass  # leave without timestamp if parse fails

        elif role == "assistant":
            for key, val in ASSISTANT_EXTRA.items():
                msg.setdefault(key, val)

        obj = {**obj, "message": msg}

    return obj


# ---------------------------------------------------------------------------
# Per-file logic
# ---------------------------------------------------------------------------


def _needs_fix(lines: list[dict]) -> bool:
    """Quick check whether any line still needs patching."""
    for obj in lines:
        t = obj.get("type")
        if t == "session" and "cwd" in obj:
            return True
        if t == "model_change" and (
            obj.get("provider") != PROVIDER or obj.get("modelId") != MODEL_ID
        ):
            return True
        if t == "custom" and obj.get("customType") == "model-snapshot":
            d = obj.get("data", {})
            if d.get("provider") != PROVIDER or d.get("modelId") != MODEL_ID:
                return True
        if t == "message":
            msg = obj.get("message", {})
            role = msg.get("role")
            if role == "user" and "timestamp" not in msg:
                return True
            if role == "assistant" and any(k not in msg for k in ASSISTANT_EXTRA):
                return True
    return False


def fix_file(path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Fix one .jsonl file.  Returns (changed, status_message)."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return False, "skipped (empty)"

    raw_lines = [l for l in text.splitlines() if l.strip()]

    try:
        parsed = [json.loads(l) for l in raw_lines]
    except json.JSONDecodeError as e:
        return False, f"ERROR: invalid JSON — {e}"

    # Only process files already in openclaw format
    if not parsed or parsed[0].get("type") != "session":
        return False, "skipped (not in openclaw format — run fix_session_format.py first)"

    if not _needs_fix(parsed):
        return False, "skipped (already up to date)"

    fixed = [_fix_line(obj) for obj in parsed]
    new_content = "\n".join(
        json.dumps(obj, ensure_ascii=False) for obj in fixed
    ) + "\n"

    if dry_run:
        print(f"\n--- {path.name} ---")
        for obj in fixed:
            print(f"  {json.dumps(obj, ensure_ascii=False)}")
        return True, "dry-run ok"

    path.write_text(new_content, encoding="utf-8")
    return True, f"fixed ({len(fixed)} lines)"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if not SESSIONS_DIR.exists():
        print(f"ERROR: sessions directory not found:\n  {SESSIONS_DIR}")
        sys.exit(1)

    files = sorted(SESSIONS_DIR.glob("*.jsonl"))
    if not files:
        print("No .jsonl files found.")
        return

    mode = "DRY RUN — " if dry_run else ""
    print(f"{mode}Processing {len(files)} session files in:")
    print(f"  {SESSIONS_DIR}\n")

    changed = skipped = errors = 0
    for f in files:
        ok, msg = fix_file(f, dry_run=dry_run)
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
        print(f"  [{tag}]  {f.name}: {msg}")

    print(f"\nDone.  fixed={changed}  skipped={skipped}  errors={errors}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
