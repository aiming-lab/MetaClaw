#!/usr/bin/env python3
"""Fix openclaw session JSONL files from simple {"role","content"} format to the
full openclaw format with 4 metadata header lines + typed message records.

Correct format (per reference):
  Line 1: {"type":"session","version":3,"id":"<session_id>","timestamp":"...","cwd":"..."}
  Line 2: {"type":"model_change","id":"<8hex>","parentId":null,"timestamp":"...","provider":"...","modelId":"..."}
  Line 3: {"type":"thinking_level_change","id":"<8hex>","parentId":"<id2>","timestamp":"...","thinkingLevel":"low"}
  Line 4: {"type":"custom","customType":"model-snapshot","data":{...},"id":"<8hex>","parentId":"<id3>","timestamp":"..."}
  Line N: {"type":"message","id":"<8hex>","parentId":"<prev>","timestamp":"...","message":{"role":"...","content":[{"type":"text","text":"..."}]}}

Usage:
    python fix_session_format.py            # fix all files in-place
    python fix_session_format.py --dry-run  # preview without writing
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SESSIONS_DIR = (
    Path(__file__).parent.parent
    / "benchmark/data/metaclaw-bench/openclaw_state/agents/metaclaw_agent/sessions"
)

# ---------------------------------------------------------------------------
# Day → calendar date mapping  (Mon–Fri, skipping weekends)
# Arc A (1-5):  2026-03-16 to 03-20
# Arc B (6-10): 2026-03-23 to 03-27
# Arc C (11-15):2026-03-30 to 04-03
# Arc D (16-20):2026-04-06 to 04-10
# Arc E (21-25):2026-04-13 to 04-17
# Arc F (26-30):2026-04-20 to 04-24
# ---------------------------------------------------------------------------

DAY_DATES: dict[int, str] = {
    1:  "2026-03-16",  2:  "2026-03-17",  3:  "2026-03-18",
    4:  "2026-03-19",  5:  "2026-03-20",
    6:  "2026-03-23",  7:  "2026-03-24",  8:  "2026-03-25",
    9:  "2026-03-26",  10: "2026-03-27",
    11: "2026-03-30",  12: "2026-03-31",  13: "2026-04-01",
    14: "2026-04-02",  15: "2026-04-03",
    16: "2026-04-06",  17: "2026-04-07",  18: "2026-04-08",
    19: "2026-04-09",  20: "2026-04-10",
    21: "2026-04-13",  22: "2026-04-14",  23: "2026-04-15",
    24: "2026-04-16",  25: "2026-04-17",
    26: "2026-04-20",  27: "2026-04-21",  28: "2026-04-22",
    29: "2026-04-23",  30: "2026-04-24",
}

# ---------------------------------------------------------------------------
# Model config — matches openclaw.json benchmark provider
# ---------------------------------------------------------------------------

PROVIDER   = "metaclaw-benchmark"
MODEL_ID   = "${BENCHMARK_MODEL}"
MODEL_API  = "openai-completions"

# cwd root in session header (per-day subdir appended at build time)
WORKSPACE_ROOT = "${METACLAW_ROOT}/benchmark/data/metaclaw-bench/workspaces/shared"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _short_id() -> str:
    """Return a fresh random 8-char hex ID."""
    return uuid.uuid4().hex[:8]


def _iso_ts(base: datetime, offset_ms: int = 0) -> str:
    """ISO 8601 UTC timestamp with milliseconds."""
    dt = base + timedelta(milliseconds=offset_ms)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _unix_ms(base: datetime, offset_ms: int = 0) -> int:
    dt = base + timedelta(milliseconds=offset_ms)
    return int(dt.timestamp() * 1000)


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------


def build_session_lines(
    session_id: str,
    day_num: int,
    messages: list[dict],
) -> list[str]:
    """Return JSONL lines for the correctly formatted session file."""
    date_str = DAY_DATES[day_num]
    # Session starts at 09:00:00 CST (UTC+8) → 01:00:00 UTC
    local_dt = datetime.strptime(
        f"{date_str}T09:00:00", "%Y-%m-%dT%H:%M:%S"
    ).replace(tzinfo=timezone(timedelta(hours=8)))
    base_utc = local_dt.astimezone(timezone.utc)

    id1 = _short_id()
    id2 = _short_id()
    id3 = _short_id()
    cwd = f"{WORKSPACE_ROOT}/day{day_num:02d}"

    lines: list[str] = []

    # ---- Line 1: session header ----
    lines.append(json.dumps({
        "type":      "session",
        "version":   3,
        "id":        session_id,
        "timestamp": _iso_ts(base_utc, 0),
        "cwd":       cwd,
    }, ensure_ascii=False))

    # ---- Line 2: model_change ----
    lines.append(json.dumps({
        "type":      "model_change",
        "id":        id1,
        "parentId":  None,
        "timestamp": _iso_ts(base_utc, 10),
        "provider":  PROVIDER,
        "modelId":   MODEL_ID,
    }, ensure_ascii=False))

    # ---- Line 3: thinking_level_change ----
    lines.append(json.dumps({
        "type":         "thinking_level_change",
        "id":           id2,
        "parentId":     id1,
        "timestamp":    _iso_ts(base_utc, 20),
        "thinkingLevel": "low",
    }, ensure_ascii=False))

    # ---- Line 4: model-snapshot ----
    lines.append(json.dumps({
        "type":       "custom",
        "customType": "model-snapshot",
        "data": {
            "timestamp": _unix_ms(base_utc, 30),
            "provider":  PROVIDER,
            "modelApi":  MODEL_API,
            "modelId":   MODEL_ID,
        },
        "id":        id3,
        "parentId":  id2,
        "timestamp": _iso_ts(base_utc, 30),
    }, ensure_ascii=False))

    # ---- Message lines ----
    # First message at 09:02:00 (2 min after session init), +30 s per turn.
    prev_id     = id3
    offset_ms   = 2 * 60 * 1000

    for msg in messages:
        mid  = _short_id()
        role = msg["role"]

        # Normalise content: current files store plain strings
        raw = msg["content"]
        if isinstance(raw, str):
            text = raw
        elif isinstance(raw, list):
            # Already-wrapped content — extract text fields
            text = " ".join(
                item.get("text", "") for item in raw if isinstance(item, dict)
            )
        else:
            text = str(raw)

        lines.append(json.dumps({
            "type":      "message",
            "id":        mid,
            "parentId":  prev_id,
            "timestamp": _iso_ts(base_utc, offset_ms),
            "message": {
                "role":    role,
                "content": [{"type": "text", "text": text}],
            },
        }, ensure_ascii=False))

        prev_id   = mid
        offset_ms += 30_000   # 30 s per turn

    return lines


# ---------------------------------------------------------------------------
# Per-file logic
# ---------------------------------------------------------------------------


def _already_converted(lines: list[str]) -> bool:
    if not lines:
        return False
    try:
        return json.loads(lines[0]).get("type") == "session"
    except Exception:
        return False


def fix_file(path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Fix one .jsonl file.  Returns (was_changed, status_message)."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return False, "skipped (empty file)"

    raw_lines = [l for l in text.splitlines() if l.strip()]

    if _already_converted(raw_lines):
        return False, "skipped (already in correct format)"

    # Parse existing simple messages
    messages: list[dict] = []
    for line in raw_lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            return False, f"ERROR: invalid JSON — {e}"
        if "role" not in obj:
            return False, f"ERROR: unexpected line (no 'role'): {line[:80]}"
        messages.append(obj)

    if not messages:
        return False, "skipped (no messages after parsing)"

    # Extract day number from filename: day01_<uuid>.jsonl → 1
    m = re.match(r"day(\d+)_", path.name)
    if not m:
        return False, "skipped (filename doesn't match day[N]_*.jsonl)"

    day_num = int(m.group(1))
    if day_num not in DAY_DATES:
        return False, f"ERROR: day {day_num} not in DAY_DATES mapping"

    session_id = path.stem   # full stem = session id (no .jsonl)
    new_lines  = build_session_lines(session_id, day_num, messages)
    new_content = "\n".join(new_lines) + "\n"

    if dry_run:
        print(f"\n--- {path.name} (day{day_num:02d}, {len(messages)} msgs) ---")
        for l in new_lines:
            print(f"  {l}")
        return True, "dry-run ok"

    path.write_text(new_content, encoding="utf-8")
    return True, f"fixed ({len(messages)} msg → {len(new_lines)} lines)"


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
