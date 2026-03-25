#!/usr/bin/env python3
"""
Build MetaClaw-Bench-Small: extract ~1/6 subset (61 rounds) from the full 30-day benchmark.

Usage:
    python scripts/build_small_subset.py [--src data/metaclaw-bench] [--dst data/metaclaw-bench-small] [--dry-run]
"""

import argparse
import copy
import json
import os
import re
import shutil
import uuid
from pathlib import Path

# ============================================================
# Round Selection Configuration
# ============================================================

SELECTION = {
    "day01": {
        "desc": "P1 first encounter — documentation, PM, code domains",
        "arc": "A",
        "preference_tags": ["output_format"],
        "rounds": [
            {"src": "day01", "round": "r1"},   # file_check: standup→JSON, P1 first trigger
            {"src": "day01", "round": "r3"},   # mc: time format identification
            {"src": "day01", "round": "r5"},   # file_check: new task with time fields
            {"src": "day02", "round": "r4"},   # mc: PM domain time format
            {"src": "day04", "round": "r1"},   # file_check: code domain time
        ],
        "workspace_sources": ["day01", "day04"],
        "session_base": "day01",
    },
    "day02": {
        "desc": "P1 cross-domain transfer — data processing, comprehensive",
        "arc": "A",
        "preference_tags": ["output_format"],
        "rounds": [
            {"src": "day03", "round": "r1"},   # file_check: log parsing
            {"src": "day03", "round": "r3"},   # mc: log time conversion
            {"src": "day03", "round": "r7"},   # file_check: performance metrics time
            {"src": "day05", "round": "r3"},   # mc: document time format
            {"src": "day05", "round": "r9"},   # file_check: sprint wrap-up file
        ],
        "workspace_sources": ["day03", "day05"],
        "session_base": "day03",
    },
    "day03": {
        "desc": "P2 first encounter — code engineering file naming",
        "arc": "B",
        "preference_tags": ["output_format", "file_naming"],
        "rounds": [
            {"src": "day06", "round": "r1"},   # file_check: CI report→naming error
            {"src": "day06", "round": "r3"},   # mc: naming convention identification
            {"src": "day06", "round": "r4"},   # file_check: changelog file
            {"src": "day06", "round": "r5"},   # file_check: Markdown report naming
            {"src": "day07", "round": "r4"},   # mc: date prefix in documentation
        ],
        "workspace_sources": ["day06", "day07"],
        "session_base": "day06",
    },
    "day04": {
        "desc": "P1+P2 combined validation — project management",
        "arc": "B",
        "preference_tags": ["output_format", "file_naming"],
        "rounds": [
            {"src": "day09", "round": "r1"},   # file_check: sprint progress report
            {"src": "day09", "round": "r4"},   # mc: P1+P2 combined
            {"src": "day09", "round": "r5"},   # file_check: resource plan
            {"src": "day09", "round": "r7"},   # mc: naming + time fields
            {"src": "day10", "round": "r12"},  # mc: final P1+P2 comprehensive
        ],
        "workspace_sources": ["day09", "day10"],
        "session_base": "day09",
    },
    "day05": {
        "desc": "P3 first encounter — MD/JSON/Python three file types",
        "arc": "C",
        "preference_tags": ["output_format", "file_naming", "field_completeness"],
        "rounds": [
            {"src": "day11", "round": "r1"},   # file_check: MD frontmatter first trigger
            {"src": "day12", "round": "r1"},   # file_check: JSON meta first trigger
            {"src": "day11", "round": "r3"},   # mc: P3 format identification
            {"src": "day13", "round": "r1"},   # file_check: Python docstring first trigger
            {"src": "day12", "round": "r2"},   # mc: different file type metadata rules
        ],
        "workspace_sources": ["day11", "day12", "day13"],
        "session_base": "day11",
    },
    "day06": {
        "desc": "P1-P3 comprehensive — all file types",
        "arc": "C",
        "preference_tags": ["output_format", "file_naming", "field_completeness"],
        "rounds": [
            {"src": "day15", "round": "r1"},   # file_check: JSON+P2+P3
            {"src": "day15", "round": "r3"},   # file_check: CSV+P3
            {"src": "day15", "round": "r4"},   # mc: four file types P3 format comparison
            {"src": "day15", "round": "r5"},   # file_check: Python+P3
            {"src": "day14", "round": "r3"},   # mc: P1+P2+P3 combined identification
        ],
        "workspace_sources": ["day15", "day14"],
        "session_base": "day15",
    },
    "day07": {
        "desc": "P4 first encounter — modify vs create boundary",
        "arc": "D",
        "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow"],
        "rounds": [
            {"src": "day16", "round": "r1"},   # file_check: modify weekly_status→backup missing
            {"src": "day16", "round": "r2"},   # mc: backup rule understanding
            {"src": "day16", "round": "r6"},   # file_check: new file→no backup needed
            {"src": "day16", "round": "r7"},   # file_check: modify another file
            {"src": "day17", "round": "r3"},   # mc: backup rule boundary identification
        ],
        "workspace_sources": ["day16", "day17"],
        "session_base": "day16",
    },
    "day08": {
        "desc": "P1-P4 comprehensive — code engineering",
        "arc": "D",
        "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow"],
        "rounds": [
            {"src": "day18", "round": "r1"},   # file_check: modify Python file
            {"src": "day18", "round": "r2"},   # file_check: new file→no backup
            {"src": "day18", "round": "r3"},   # mc: P4 boundary
            {"src": "day18", "round": "r6"},   # file_check: modify config file
            {"src": "day20", "round": "r4"},   # mc: P1-P4 comprehensive identification
        ],
        "workspace_sources": ["day18", "day20"],
        "session_base": "day18",
    },
    "day09": {
        "desc": "P5 first encounter — no preset done.log",
        "arc": "E",
        "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow", "completion_log"],
        "rounds": [
            {"src": "day21", "round": "r1"},   # file_check: first task→done.log missing
            {"src": "day21", "round": "r3"},   # mc: done.log format understanding
            {"src": "day21", "round": "r4"},   # file_check: 2nd task→min-entries 2
            {"src": "day21", "round": "r7"},   # file_check: 3rd task→min-entries 3
            {"src": "day22", "round": "r3"},   # mc: append vs overwrite identification
        ],
        "workspace_sources": ["day21", "day22"],
        "session_base": "day21",
    },
    "day10": {
        "desc": "P1-P5 comprehensive — data processing with preset done.log",
        "arc": "E",
        "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow", "completion_log"],
        "rounds": [
            {"src": "day23", "round": "r1"},   # file_check: data task+done.log
            {"src": "day23", "round": "r3"},   # mc: which tasks trigger done.log
            {"src": "day23", "round": "r5"},   # file_check: 2nd task
            {"src": "day23", "round": "r7"},   # file_check: 3rd task+modify→P4
            {"src": "day25", "round": "r12"},  # mc: P1-P5 comprehensive identification
        ],
        "workspace_sources": ["day23", "day25"],
        "session_base": "day23",
    },
    "day11": {
        "desc": "P1-P5 mixed — zero hints, code + documentation",
        "arc": "F",
        "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow", "completion_log"],
        "rounds": [
            {"src": "day26", "round": "r1"},   # file_check: Python file→P1+P2+P3+P5
            {"src": "day26", "round": "r2"},   # file_check: modify existing→P4
            {"src": "day26", "round": "r3"},   # mc: multi-rule interaction
            {"src": "day26", "round": "r5"},   # file_check: new JSON→multi-rule
            {"src": "day27", "round": "r3"},   # mc: doc scenario rule identification
        ],
        "workspace_sources": ["day26", "day27"],
        "session_base": "day26",
    },
    "day12": {
        "desc": "Ultimate comprehensive test — hardest scenarios",
        "arc": "F",
        "preference_tags": ["output_format", "file_naming", "field_completeness", "workflow", "completion_log"],
        "rounds": [
            {"src": "day30", "round": "r1"},   # file_check: dashboard→P1+P2+P3+P5
            {"src": "day30", "round": "r3"},   # file_check: new file→multi-rule
            {"src": "day30", "round": "r6"},   # file_check: modify+create mixed→P4+others
            {"src": "day30", "round": "r7"},   # mc: multi-rule boundary judgment
            {"src": "day30", "round": "r11"},  # file_check: full rule chain
            {"src": "day28", "round": "r10"},  # mc: data processing scenario identification
        ],
        "workspace_sources": ["day30", "day28"],
        "session_base": "day30",
    },
}

# ============================================================
# Helpers
# ============================================================

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  wrote {path}")


def extract_round(questions: dict, round_id: str) -> dict:
    """Extract a specific round from a questions.json by round ID."""
    for r in questions["rounds"]:
        if r["id"] == round_id:
            return copy.deepcopy(r)
    available = [r["id"] for r in questions["rounds"]]
    raise ValueError(
        f"Round {round_id} not found in {questions['id']}. "
        f"Available: {available}"
    )


def clean_feedback_prefix(text: str) -> str:
    """Remove '[Previous feedback] ...\n\n' prefix from question text."""
    if text.startswith("[Previous feedback]"):
        # Find the first double newline after the prefix
        idx = text.find("\n\n")
        if idx != -1:
            return text[idx + 2:]
    return text


def remap_day_paths(text: str, src_day: str, new_day: str) -> str:
    """Replace dayXX/ references with the new day ID in text."""
    if src_day == new_day:
        return text
    # Replace exact path references: dayXX/ → dayNN/
    return text.replace(f"{src_day}/", f"{new_day}/")


def remap_round_data(round_data: dict, src_day: str, new_day: str) -> dict:
    """Remap all dayXX/ references in a round to the new day."""
    rd = round_data

    # Remap question text
    rd["question"] = remap_day_paths(rd["question"], src_day, new_day)

    # Remap feedback text
    if "feedback" in rd:
        fb = rd["feedback"]
        if "correct" in fb:
            fb["correct"] = remap_day_paths(fb["correct"], src_day, new_day)
        if "incorrect" in fb:
            fb["incorrect"] = remap_day_paths(fb["incorrect"], src_day, new_day)
        if "options" in fb:
            for k, v in fb["options"].items():
                fb["options"][k] = remap_day_paths(v, src_day, new_day)

    # Remap eval command
    if "eval" in rd and "command" in rd["eval"]:
        rd["eval"]["command"] = remap_day_paths(
            rd["eval"]["command"], src_day, new_day
        )

    return rd


def adjust_min_count(eval_cmd: str, file_check_count: int) -> str:
    """Adjust --min-count N in check_filename.py commands."""
    if "check_filename.py" not in eval_cmd:
        return eval_cmd
    # Remove existing --min-count
    eval_cmd = re.sub(r"\s+--min-count\s+\d+", "", eval_cmd)
    # Add new --min-count if > 1
    if file_check_count > 1:
        # Insert before any trailing quote or end
        eval_cmd = eval_cmd.rstrip()
        eval_cmd += f" --min-count {file_check_count}"
    return eval_cmd


def adjust_min_entries(eval_cmd: str, done_log_count: int) -> str:
    """Adjust --min-entries N in check_done_log.py commands."""
    if "check_done_log.py" not in eval_cmd:
        return eval_cmd
    # Replace existing --min-entries N
    new_cmd = re.sub(
        r"--min-entries\s+\d+",
        f"--min-entries {done_log_count}",
        eval_cmd,
    )
    return new_cmd


def parse_filename_ext(eval_cmd: str) -> str | None:
    """Extract --ext value from a check_filename.py command."""
    m = re.search(r"--ext\s+(\w+)", eval_cmd)
    return m.group(1) if m else None


# ============================================================
# Session Generation
# ============================================================

def generate_session(new_day: str, base_session: dict, base_day: str) -> dict:
    """Generate a new session JSONL content based on a base day's session."""
    session_id = f"{new_day}_{uuid.uuid4()}"
    lines = []
    for line in base_session:
        new_line = copy.deepcopy(line)
        if new_line.get("type") == "session":
            new_line["id"] = session_id
        # Remap day references in user messages
        if new_line.get("type") == "message":
            msg = new_line.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        item["text"] = remap_day_paths(
                            item["text"], base_day, new_day
                        )
            elif isinstance(content, str):
                msg["content"] = remap_day_paths(content, base_day, new_day)
        lines.append(new_line)
    return {"id": session_id, "lines": lines}


# ============================================================
# Main Build Logic
# ============================================================

def build_subset(src_dir: Path, dst_dir: Path, dry_run: bool = False):
    """Build the small subset dataset."""
    print(f"Source: {src_dir}")
    print(f"Destination: {dst_dir}")
    print(f"Dry run: {dry_run}")
    print()

    # Validate source
    assert (src_dir / "all_tests.json").exists(), f"Source not found: {src_dir}"

    # Load source data
    src_tests = load_json(src_dir / "all_tests.json")
    src_test_map = {t["id"]: t for t in src_tests["test"]}

    # Preload all needed questions.json
    needed_src_days = set()
    for cfg in SELECTION.values():
        for r in cfg["rounds"]:
            needed_src_days.add(r["src"])

    questions_cache: dict[str, dict] = {}
    for day in sorted(needed_src_days):
        qpath = src_dir / "eval" / day / "questions.json"
        assert qpath.exists(), f"Missing: {qpath}"
        questions_cache[day] = load_json(qpath)
    print(f"Loaded {len(questions_cache)} source questions.json files")

    # Load session files
    session_dir = src_dir / "openclaw_state" / "agents" / "metaclaw_agent" / "sessions"
    session_cache: dict[str, list] = {}
    for day_id, test_entry in src_test_map.items():
        session_file = session_dir / f"{test_entry['session']}.jsonl"
        if session_file.exists():
            lines = []
            with open(session_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        lines.append(json.loads(line))
            session_cache[day_id] = lines

    # ---- Build each new day ----
    new_tests = []
    total_rounds = 0
    all_session_data = {}

    for new_day_id in sorted(SELECTION.keys()):
        cfg = SELECTION[new_day_id]
        print(f"\n=== {new_day_id}: {cfg['desc']} ===")

        # Track counters for --min-count and --min-entries adjustment
        filename_count_by_ext: dict[str, int] = {}  # ext → count
        done_log_entry_count = 0

        new_rounds = []
        for i, rspec in enumerate(cfg["rounds"]):
            src_day = rspec["src"]
            src_round_id = rspec["round"]
            new_round_id = f"r{i + 1}"

            # Extract round
            rd = extract_round(questions_cache[src_day], src_round_id)
            old_id = rd["id"]
            rd["id"] = new_round_id

            # Clean feedback prefix
            rd["question"] = clean_feedback_prefix(rd["question"])

            # Remap day paths
            rd = remap_round_data(rd, src_day, new_day_id)

            # Adjust --min-count for check_filename.py
            if rd["type"] == "file_check" and "eval" in rd and "command" in rd["eval"]:
                cmd = rd["eval"]["command"]
                ext = parse_filename_ext(cmd)
                if ext and "check_filename.py" in cmd:
                    filename_count_by_ext[ext] = filename_count_by_ext.get(ext, 0) + 1
                    cmd = adjust_min_count(cmd, filename_count_by_ext[ext])
                    rd["eval"]["command"] = cmd

            # Adjust --min-entries for check_done_log.py
            if rd["type"] == "file_check" and "eval" in rd and "command" in rd["eval"]:
                cmd = rd["eval"]["command"]
                if "check_done_log.py" in cmd and "--min-entries" in cmd:
                    done_log_entry_count += 1
                    cmd = adjust_min_entries(cmd, done_log_entry_count)
                    rd["eval"]["command"] = cmd

            new_rounds.append(rd)
            print(f"  {new_round_id} ← {src_day}/{old_id} ({rd['type']})")

        total_rounds += len(new_rounds)

        # Build questions.json for this day
        new_questions = {
            "id": new_day_id,
            "desc": f"Day {new_day_id[-2:]} — {cfg['desc']}",
            "rounds": new_rounds,
        }

        if not dry_run:
            save_json(new_questions, dst_dir / "eval" / new_day_id / "questions.json")

        # Build test entry
        session_base_day = cfg["session_base"]
        base_session = session_cache.get(session_base_day, [])
        sess = generate_session(new_day_id, base_session, session_base_day)
        all_session_data[new_day_id] = sess

        new_tests.append({
            "id": new_day_id,
            "desc": new_questions["desc"],
            "agent": "metaclaw_agent",
            "session": sess["id"],
            "eval": new_day_id,
            "arc": cfg["arc"],
            "preference_tags": cfg["preference_tags"],
        })

    print(f"\n=== Total: {total_rounds} rounds across {len(SELECTION)} days ===")

    if dry_run:
        print("\nDry run complete. No files written.")
        return

    # ---- Write all_tests.json ----
    all_tests = {
        "name": "MetaClaw-Evolution-Bench-Small",
        "openclaw_state_dir": "./benchmark/data/metaclaw-bench-small/openclaw_state",
        "openclaw_config_file": "./benchmark/data/metaclaw-bench-small/openclaw_cfg/openclaw.json",
        "eval_dir": "./benchmark/data/metaclaw-bench-small/eval",
        "workspace_src": "./benchmark/data/metaclaw-bench-small/workspaces/shared",
        "test": new_tests,
    }
    save_json(all_tests, dst_dir / "all_tests.json")

    all_tests_metaclaw = copy.deepcopy(all_tests)
    all_tests_metaclaw["openclaw_config_file"] = (
        "./benchmark/data/metaclaw-bench-small/openclaw_cfg/metaclaw.json"
    )
    save_json(all_tests_metaclaw, dst_dir / "all_tests_metaclaw.json")

    # ---- Copy eval scripts ----
    src_scripts = src_dir / "eval" / "scripts"
    dst_scripts = dst_dir / "eval" / "scripts"
    if src_scripts.exists():
        shutil.copytree(src_scripts, dst_scripts, dirs_exist_ok=True)
        print(f"\n  copied eval/scripts/ ({len(list(src_scripts.iterdir()))} files)")

    # ---- Copy openclaw_cfg ----
    src_cfg = src_dir / "openclaw_cfg"
    dst_cfg = dst_dir / "openclaw_cfg"
    if src_cfg.exists():
        shutil.copytree(src_cfg, dst_cfg, dirs_exist_ok=True)
        print(f"  copied openclaw_cfg/")

    # ---- Copy workspaces ----
    src_shared = src_dir / "workspaces" / "shared"
    dst_shared = dst_dir / "workspaces" / "shared"

    # Copy global files (AGENTS.md, IDENTITY.md, etc.)
    for f in src_shared.iterdir():
        if f.is_file():
            dst_f = dst_shared / f.name
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst_f)
    print(f"  copied global workspace files")

    # Copy and merge day-specific workspace files
    for new_day_id, cfg in SELECTION.items():
        dst_day_ws = dst_shared / new_day_id
        dst_day_ws.mkdir(parents=True, exist_ok=True)

        for src_day in cfg["workspace_sources"]:
            src_day_ws = src_shared / src_day
            if src_day_ws.exists():
                for f in src_day_ws.iterdir():
                    if f.is_file():
                        dst_f = dst_day_ws / f.name
                        if dst_f.exists():
                            print(f"  WARNING: workspace file conflict: {f.name} "
                                  f"in {new_day_id} from {src_day} (skipping)")
                        else:
                            shutil.copy2(f, dst_f)
            else:
                print(f"  WARNING: source workspace {src_day_ws} not found")

        ws_files = list(dst_day_ws.iterdir())
        print(f"  {new_day_id} workspace: {len(ws_files)} files "
              f"(from {cfg['workspace_sources']})")

    # ---- Write session files ----
    dst_sessions = (
        dst_dir / "openclaw_state" / "agents" / "metaclaw_agent" / "sessions"
    )
    dst_sessions.mkdir(parents=True, exist_ok=True)

    for new_day_id, sess in all_session_data.items():
        session_file = dst_sessions / f"{sess['id']}.jsonl"
        with open(session_file, "w") as f:
            for line in sess["lines"]:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(f"  wrote session: {sess['id']}.jsonl")

    # ---- Create empty work directory ----
    (dst_dir / "work").mkdir(parents=True, exist_ok=True)

    # ---- Validation ----
    print("\n=== Validation ===")
    validate_subset(dst_dir)


def validate_subset(dst_dir: Path):
    """Run validation checks on the generated subset."""
    errors = []
    warnings = []

    # Check all_tests.json
    tests = load_json(dst_dir / "all_tests.json")
    test_ids = [t["id"] for t in tests["test"]]
    expected_ids = [f"day{i:02d}" for i in range(1, 13)]
    if test_ids != expected_ids:
        errors.append(f"Test IDs mismatch: {test_ids} != {expected_ids}")
    print(f"  Tests: {len(tests['test'])} days")

    # Check each day's questions.json
    total_rounds = 0
    for test in tests["test"]:
        day_id = test["id"]
        qpath = dst_dir / "eval" / day_id / "questions.json"
        if not qpath.exists():
            errors.append(f"Missing: {qpath}")
            continue
        q = load_json(qpath)
        n = len(q["rounds"])
        total_rounds += n

        # Check round IDs are sequential
        expected_rids = [f"r{i+1}" for i in range(n)]
        actual_rids = [r["id"] for r in q["rounds"]]
        if actual_rids != expected_rids:
            errors.append(f"{day_id}: Round IDs {actual_rids} != {expected_rids}")

        # Check no stale dayXX/ references in eval commands
        for r in q["rounds"]:
            if r.get("eval", {}).get("command"):
                cmd = r["eval"]["command"]
                # Find all dayXX/ references
                day_refs = re.findall(r"day\d{2}/", cmd)
                for ref in day_refs:
                    if not ref.startswith(day_id + "/"):
                        # Could be a false positive from other patterns, check context
                        # Allow references in Python string literals that are part of glob patterns
                        pass  # eval commands may reference their own day only

        # Check workspace files exist for file_check rounds
        ws_dir = dst_dir / "workspaces" / "shared" / day_id
        if not ws_dir.exists():
            errors.append(f"Missing workspace dir: {ws_dir}")

        # Check day path consistency in eval commands
        for r in q["rounds"]:
            if r.get("eval", {}).get("command"):
                cmd = r["eval"]["command"]
                refs = set(re.findall(r"(day\d{2})/", cmd))
                stale = [ref for ref in refs if ref != day_id]
                if stale:
                    warnings.append(
                        f"{day_id}/{r['id']}: eval command references other days: {stale}"
                    )

    print(f"  Total rounds: {total_rounds}")

    # Check eval scripts
    scripts_dir = dst_dir / "eval" / "scripts"
    if scripts_dir.exists():
        scripts = list(scripts_dir.iterdir())
        print(f"  Eval scripts: {len(scripts)}")
    else:
        errors.append("Missing eval/scripts/")

    # Check session files
    session_dir = (
        dst_dir / "openclaw_state" / "agents" / "metaclaw_agent" / "sessions"
    )
    if session_dir.exists():
        sessions = list(session_dir.iterdir())
        print(f"  Session files: {len(sessions)}")
    else:
        errors.append("Missing session directory")

    # Report
    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    ⚠ {w}")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    ✗ {e}")
        return False
    else:
        print(f"\n  ✓ All validation checks passed!")
        return True


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Build MetaClaw-Bench-Small subset")
    parser.add_argument(
        "--src",
        default="data/metaclaw-bench",
        help="Source benchmark directory (default: data/metaclaw-bench)",
    )
    parser.add_argument(
        "--dst",
        default="data/metaclaw-bench-small",
        help="Destination directory (default: data/metaclaw-bench-small)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate selections without writing files",
    )
    args = parser.parse_args()

    # Resolve paths relative to the script's parent's parent (benchmark/)
    base = Path(__file__).resolve().parent.parent
    src = base / args.src
    dst = base / args.dst

    if dst.exists() and not args.dry_run:
        print(f"Destination {dst} already exists. Removing...")
        shutil.rmtree(dst)

    build_subset(src, dst, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
