"""Benchmark infer command.

Runs the openclaw agent for each question in each test scenario, saving
per-question results under the output directory.

Concurrency model
-----------------
MetaClaw bench requires serial test execution (per-test workspace isolation
via openclaw.json patching).  The ``workers`` parameter is accepted for API
compatibility but is always treated as 1, and a notice is printed if a
different value is passed.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from src.infer.prompts import (
    CONTINUE_REMINDER,
    FILE_CHECK_INCORRECT_SUFFIX,
    FORMAT_ERROR,
    missed_option,
    standalone_feedback,
    with_feedback,
    wrong_option,
)
from src.infer.query_reader import QueryReader, get_default_query_reader
from src.utils import get_project_root, resolve_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_all_tests_files(input_path: Path) -> list[Path]:
    """Return a list of all_tests.json files to process."""
    if input_path.is_file():
        if input_path.suffix.lower() == ".json":
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    json_content = json.load(f)
                if isinstance(json_content, list):
                    return [Path(p) for p in json_content]
                else:
                    return [input_path]
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load JSON file {input_path}: {e}")
                return [input_path]
        return [input_path]
    return sorted(input_path.rglob("all_tests.json"))


def _prepare_output_dir(output_arg: str, name: str | None = None) -> Path:
    """Prepare and return the actual output directory."""
    out = resolve_path(output_arg)
    if out.exists():
        short_id = str(uuid.uuid4())[:8]
        subdir_name = f"infer_{name}_{short_id}" if name else f"infer_{short_id}"
        out = out / subdir_name
    out.mkdir(parents=True, exist_ok=True)
    return out


def _replace_str_in_json(obj: Any, old: str, new: str) -> Any:
    """Recursively replace *old* with *new* in all string values of a JSON object."""
    if isinstance(obj, dict):
        return {k: _replace_str_in_json(v, old, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_str_in_json(v, old, new) for v in obj]
    if isinstance(obj, str) and old in obj:
        return obj.replace(old, new)
    return obj


def _prepare_work_copy(
    openclaw_state_dir: Path,
    project_root: Path,
    openclaw_config_src: Path | None = None,
) -> Path:
    """Copy openclaw_state into a sibling ``work/`` folder.

    Creates under ``<parent>/work/``:
      - ``openclaw_state_<uuid>/`` — isolated copy of openclaw_state

    If *openclaw_config_src* is provided it is copied into the work copy as
    ``openclaw.json``; otherwise ``openclaw.json`` is expected to already
    exist inside *openclaw_state_dir* (legacy layout).

    Rewrites agentDir paths in the copy's ``openclaw.json`` to point to the
    new location.  Does NOT copy or remap workspace directories; those are
    handled per-test by :func:`_copy_workspace_for_test` and
    :func:`_patch_agent_workspace`.

    Returns the path to the new openclaw_state copy.
    """
    work_dir = openclaw_state_dir.parent / "work"
    work_dir.mkdir(exist_ok=True)

    run_id = str(uuid.uuid4())
    work_copy = work_dir / f"openclaw_state_{run_id}"
    shutil.copytree(openclaw_state_dir, work_copy)

    if openclaw_config_src is not None:
        shutil.copy2(openclaw_config_src, work_copy / "openclaw.json")

    openclaw_json_path = work_copy / "openclaw.json"
    if openclaw_json_path.exists():
        config = json.loads(openclaw_json_path.read_text(encoding="utf-8"))

        # Remap openclaw_state paths (agentDir etc.)
        replacements: list[tuple[str, str]] = []
        replacements.append((
            str(openclaw_state_dir).replace("\\", "/"),
            str(work_copy).replace("\\", "/"),
        ))
        try:
            orig_rel = openclaw_state_dir.relative_to(project_root)
            new_rel = work_copy.relative_to(project_root)
            orig_rel_str = str(orig_rel).replace("\\", "/")
            new_rel_str = str(new_rel).replace("\\", "/")
            replacements.append(("./" + orig_rel_str, "./" + new_rel_str))
            replacements.append((
                "${METACLAW_ROOT}/" + orig_rel_str,
                str(work_copy).replace("\\", "/"),
            ))
        except ValueError:
            pass
        for old, new in replacements:
            config = _replace_str_in_json(config, old, new)

        # Resolve ${METACLAW_PROXY_PORT} placeholder (defaults to 30000)
        proxy_port = os.environ.get("METACLAW_PROXY_PORT", "30000")
        config = _replace_str_in_json(
            config, "${METACLAW_PROXY_PORT}", proxy_port
        )

        # Ensure sessions visibility so agent can read all sessions of same agent
        tools_cfg = config.setdefault("tools", {})
        sessions_cfg = tools_cfg.setdefault("sessions", {})
        sessions_cfg.setdefault("visibility", "agent")

        openclaw_json_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"Created work copy → {work_copy}")
    return work_copy


def _copy_workspace_for_test(
    workspace_src: Path,
    work_dir: Path,
    test_id: str,
) -> Path:
    """Copy a test-specific workspace to work_dir/workspace_<test_id>_<uuid>/.

    Copies two things from workspace_src:
    1. All root-level files and non-dayXX directories (identity files such as
       AGENTS.md, USER.md, SOUL.md, etc.).
    2. Only the dayXX subdirectory that matches test_id (e.g. "day01").

    Other dayXX directories are excluded so the agent cannot accidentally see
    content from other test days.
    """
    dest = work_dir / f"workspace_{test_id}_{str(uuid.uuid4())[:8]}"
    dest.mkdir(parents=True, exist_ok=False)

    day_pattern = re.compile(r"^day\d+$")

    for item in workspace_src.iterdir():
        if item.is_dir():
            if day_pattern.match(item.name):
                # Only copy the directory that matches this test
                if item.name == test_id:
                    shutil.copytree(item, dest / item.name)
            else:
                shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)

    return dest


def _copy_eval_scripts(eval_dir: Path, workspace_path: Path) -> None:
    """Copy eval/scripts/ into workspace/scripts/ if the scripts directory exists."""
    scripts_src = eval_dir / "scripts"
    if scripts_src.exists():
        scripts_dst = workspace_path / "scripts"
        shutil.copytree(scripts_src, scripts_dst, dirs_exist_ok=True)


def _patch_agent_workspace(
    openclaw_json_path: Path,
    agent_id: str,
    workspace_path: Path,
) -> None:
    """Update the named agent's workspace field in openclaw.json."""
    config = json.loads(openclaw_json_path.read_text(encoding="utf-8"))
    for agent_cfg in config.get("agents", {}).get("list", []):
        if agent_cfg.get("id") == agent_id:
            agent_cfg["workspace"] = str(workspace_path)
    openclaw_json_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _resolve_log_dir(work_openclaw_state_dir: Path, project_root: Path) -> Path:
    """Read logDir from the work copy's openclaw.json, expanding ${METACLAW_ROOT}."""
    fallback = project_root / "logs" / "llm_prompts"
    openclaw_json_path = work_openclaw_state_dir / "openclaw.json"
    if not openclaw_json_path.exists():
        return fallback
    try:
        config = json.loads(openclaw_json_path.read_text(encoding="utf-8"))
        log_dir_str: str | None = (
            config.get("plugins", {})
            .get("entries", {})
            .get("llm-prompt-logger", {})
            .get("config", {})
            .get("logDir")
        )
        if log_dir_str:
            log_dir_str = log_dir_str.replace("${METACLAW_ROOT}", str(project_root))
            return Path(log_dir_str)
    except Exception:
        pass
    return fallback


def _trim_llm_log_messages(log: Any) -> Any:
    """Trim a parsed llm_log so ``messages`` contains only the last user turn."""
    if not isinstance(log, dict):
        return log
    messages = log.get("messages")
    if not isinstance(messages, list) or not messages:
        return log

    last_user_idx: int | None = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx is None:
        return log

    trimmed = dict(log)
    trimmed["messages"] = messages[last_user_idx:]
    return trimmed


def _get_existing_log_files(log_dir: Path, session_id: str) -> set[Path]:
    """Return the set of log files that already exist for a session."""
    session_log_dir = log_dir / session_id
    if not session_log_dir.exists():
        return set()
    return set(session_log_dir.glob("*.json"))


def _read_newest_log_after(
    log_dir: Path, session_id: str, existing_files: set[Path]
) -> Any:
    """Return the content of the newest log file added after *existing_files*."""
    session_log_dir = log_dir / session_id
    if not session_log_dir.exists():
        return None
    all_files = set(session_log_dir.glob("*.json"))
    new_files = all_files - existing_files
    if new_files:
        newest = max(new_files, key=lambda p: p.stat().st_mtime)
    elif all_files:
        newest = max(all_files, key=lambda p: p.stat().st_mtime)
    else:
        return None
    try:
        return _trim_llm_log_messages(json.loads(newest.read_text(encoding="utf-8")))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Per-run gateway management
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    """Find an available TCP port on loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _start_work_gateway(
    work_openclaw_state_dir: Path,
    port: int,
) -> tuple[asyncio.subprocess.Process, Path]:
    """Start a dedicated openclaw gateway for the work-copy state dir.

    stdout and stderr are both redirected to ``gateway.log`` inside the work
    copy directory so the output is available if the process crashes.

    Returns ``(process, log_path)``.
    """
    config_path = work_openclaw_state_dir / "openclaw.json"
    log_path = work_openclaw_state_dir / "gateway.log"
    env = {
        **os.environ,
        "METACLAW_ROOT": str(get_project_root()),
        "OPENCLAW_STATE_DIR": str(work_openclaw_state_dir),
        "OPENCLAW_CONFIG_PATH": str(config_path),
        "OPENCLAW_GATEWAY_PORT": str(port),
    }
    # Open the log file; the child inherits a duplicate fd and keeps writing
    # to it after Python closes the parent's handle at the end of the with-block.
    with open(log_path, "w", encoding="utf-8") as log_fh:
        proc = await asyncio.create_subprocess_exec(
            "openclaw", "gateway", "run",
            "--port", str(port),
            "--allow-unconfigured",
            env=env,
            stdout=log_fh,
            stderr=log_fh,
        )
    return proc, log_path


def _read_gateway_log(log_path: Path, max_bytes: int = 8192) -> str:
    """Return the last *max_bytes* of the gateway log, or empty string on failure."""
    try:
        if not log_path.exists():
            return ""
        size = log_path.stat().st_size
        if size == 0:
            return ""
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            return f.read().strip()
    except Exception:
        return ""


async def _wait_for_gateway(port: int, timeout: float = 10.0) -> bool:
    """Poll until the gateway's TCP port accepts connections (or timeout)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port),
                timeout=0.5,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            await asyncio.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Async subprocess runner
# ---------------------------------------------------------------------------


async def _run_openclaw_agent(
    session_id: str,
    message: str,
    openclaw_config_path: Path,
    openclaw_state_dir: Path,
    project_root: Path,
    agent_id: str | None = None,
    gateway_port: int | None = None,
    timeout: float | None = None,
) -> tuple[int, str, str]:
    """Run ``openclaw agent`` and return (returncode, stdout, stderr)."""
    env = {
        **os.environ,
        "METACLAW_ROOT": str(project_root),
        "OPENCLAW_CONFIG_PATH": str(openclaw_config_path),
        "OPENCLAW_STATE_DIR": str(openclaw_state_dir),
    }
    if gateway_port is not None:
        env["OPENCLAW_GATEWAY_PORT"] = str(gateway_port)
    proc = await asyncio.create_subprocess_exec(
        "openclaw", "agent",
        "--session-id", session_id,
        "--message", message,
        cwd=str(project_root),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return -1, "", f"Timeout after {timeout}s"
    return proc.returncode, stdout_bytes.decode(), stderr_bytes.decode()


# ---------------------------------------------------------------------------
# Per-group session isolation
# ---------------------------------------------------------------------------


def _prepare_session(
    work_openclaw_state_dir: Path,
    agent_id: str,
    session_id: str,
) -> None:
    """Ensure the session transcript file exists in the work copy."""
    sessions_dir = work_openclaw_state_dir / "agents" / agent_id / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_path = sessions_dir / f"{session_id}.jsonl"
    if not session_path.exists():
        session_path.touch()


# ---------------------------------------------------------------------------
# Update executor
# ---------------------------------------------------------------------------


def _register_session_in_json(
    work_openclaw_state_dir: Path,
    agent_id: str,
    path_str: str,
    channel: str,
) -> None:
    """Register a new session in sessions.json."""
    sessions_dir = work_openclaw_state_dir / "agents" / agent_id / "sessions"
    sessions_json_path = sessions_dir / "sessions.json"

    try:
        if sessions_json_path.exists():
            with open(sessions_json_path, encoding="utf-8") as f:
                sessions_data = json.load(f)
        else:
            sessions_data = {}
    except Exception as e:
        print(f"  [warn] failed to read sessions.json: {e}")
        return

    session_id = path_str.replace(".jsonl", "")
    session_key = f"agent:{agent_id}:{session_id}"

    if session_key in sessions_data:
        print(f"  [info] session already registered: {session_key}")
        return

    sessions_data[session_key] = {
        "sessionId": session_id,
        "sessionFile": path_str,
        "channel": channel,
        "lastChannel": channel,
    }

    try:
        with open(sessions_json_path, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, indent=2, ensure_ascii=False)
        print(f"  [register] session in sessions.json: {session_key}")
    except Exception as e:
        print(f"  [warn] failed to write sessions.json: {e}")


def _execute_update(
    update: dict,
    agent_id: str,
    work_openclaw_state_dir: Path,
    eval_dir: Path,
    eval_name: str,
) -> None:
    """Execute a single update action from a round's ``update`` list."""
    update_type = update.get("type")
    action = update.get("action")
    path_str = update.get("path", "")
    source_str = update.get("source")
    param = update.get("param")
    channel = update.get("channel", "unknown")

    source_path: Path | None = None
    if source_str:
        source_path = eval_dir / eval_name / source_str
        if not source_path.exists():
            print(f"  [warn] update source not found: {source_path}")
            return
        if action == "new":
            if Path(source_str).name != Path(path_str).name:
                print(
                    f"  [warn] update source/path filename mismatch for new action: "
                    f"{Path(source_str).name} != {Path(path_str).name}"
                )
                return

    if update_type == "session":
        target_path = (
            work_openclaw_state_dir / "agents" / agent_id / "sessions" / path_str
        )
    elif update_type == "workspace":
        try:
            config = json.loads(
                (work_openclaw_state_dir / "openclaw.json").read_text(encoding="utf-8")
            )
        except Exception:
            print(f"  [warn] cannot read openclaw.json for workspace lookup")
            return
        workspace: str | None = None
        for agent_cfg in config.get("agents", {}).get("list", []):
            if agent_cfg.get("id") == agent_id:
                workspace = agent_cfg.get("workspace")
                break
        if not workspace:
            print(f"  [warn] workspace not found for agent {agent_id}")
            return
        target_path = Path(workspace) / path_str
    else:
        print(f"  [warn] unknown update type: {update_type!r}")
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if action == "new":
        if source_path is None:
            print(f"  [warn] update action 'new' requires source (path={path_str})")
            return
        shutil.copy2(source_path, target_path)
        print(f"  [update] new {update_type}: {path_str}")
        if update_type == "session" and channel:
            _register_session_in_json(work_openclaw_state_dir, agent_id, path_str, channel)
    elif action == "append":
        if source_path is None:
            print(f"  [warn] update action 'append' requires source (path={path_str})")
            return
        content = source_path.read_text(encoding="utf-8")
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(content)
        print(f"  [update] append {update_type}: {path_str}")
    elif action == "insert":
        if source_path is None:
            print(f"  [warn] update action 'insert' requires source (path={path_str})")
            return
        after = int(param.get("after", 0)) if isinstance(param, dict) else int(param or 0)
        existing_lines = (
            target_path.read_text(encoding="utf-8").splitlines(keepends=True)
            if target_path.exists()
            else []
        )
        insert_content = source_path.read_text(encoding="utf-8")
        new_content = (
            "".join(existing_lines[:after])
            + insert_content
            + "".join(existing_lines[after:])
        )
        target_path.write_text(new_content, encoding="utf-8")
        print(f"  [update] insert {update_type} after line {after}: {path_str}")
    elif action == "delete":
        if not target_path.exists():
            return
        lines_param: list = param.get("lines", []) if isinstance(param, dict) else []
        existing_lines = target_path.read_text(encoding="utf-8").splitlines(keepends=True)
        to_delete: set[int] = set()
        for line_spec in lines_param:
            if isinstance(line_spec, int):
                to_delete.add(line_spec - 1)
            elif isinstance(line_spec, str) and ":" in line_spec:
                parts = line_spec.split(":", 1)
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else len(existing_lines)
                to_delete.update(range(start, end))
        new_lines = [line for i, line in enumerate(existing_lines) if i not in to_delete]
        target_path.write_text("".join(new_lines), encoding="utf-8")
        print(f"  [update] delete lines {lines_param} from {update_type}: {path_str}")
    else:
        print(f"  [warn] unknown update action: {action!r}")


# ---------------------------------------------------------------------------
# Inline scoring
# ---------------------------------------------------------------------------


def _run_file_check(eval_cfg: dict, workspace: Path) -> dict:
    """Execute the file_check command and return a pass/fail result dict.

    Args:
        eval_cfg: The ``eval`` object from a file_check round record.
        workspace: The test's workspace directory (used as cwd).

    Returns:
        {"passed": bool, "exit_code": int, "stdout": str, "stderr": str}
    """
    command = eval_cfg.get("command", "")
    if not command:
        return {"passed": False, "exit_code": -1, "stdout": "", "stderr": "no command specified"}

    timeout = float(eval_cfg.get("timeout", 30))
    expect_exit = eval_cfg.get("expect_exit", 0)
    expect_stdout = eval_cfg.get("expect_stdout")
    expect_stdout_regex = eval_cfg.get("expect_stdout_regex", False)

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr

        passed = exit_code == expect_exit
        if passed and expect_stdout is not None:
            if expect_stdout_regex:
                passed = bool(re.search(expect_stdout, stdout))
            else:
                passed = expect_stdout in stdout

        return {"passed": passed, "exit_code": exit_code, "stdout": stdout, "stderr": stderr}

    except subprocess.TimeoutExpired:
        return {"passed": False, "exit_code": -1, "stdout": "", "stderr": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"passed": False, "exit_code": -1, "stdout": "", "stderr": str(e)}


def _compute_inline_score(
    round_record: dict,
    answer_text: str,
    workspace_path: Path,
) -> dict:
    """Compute inline score for a round immediately after agent response.

    For multi_choice: extracts \\bbox{} answer and compares to eval.answer.
    For file_check: executes eval.command in the workspace.

    Returns a dict with at minimum {"passed": bool}.
    """
    question_type = round_record.get("type", "multi_choice")
    eval_cfg = round_record.get("eval", {})

    if question_type == "file_check":
        return _run_file_check(eval_cfg, workspace_path)

    # multi_choice (default)
    match = re.search(r"\\(?:bbox|boxed)\{([^}]*)\}", answer_text or "")
    extracted: set[str] | None = None
    if match:
        letters = re.findall(r"[A-Za-z]", match.group(1))
        if letters:
            extracted = {l.upper() for l in letters}

    correct_raw = eval_cfg.get("answer", "")
    if isinstance(correct_raw, list):
        correct_set = {l.upper() for item in correct_raw for l in re.findall(r"[A-Za-z]", str(item))}
    elif isinstance(correct_raw, str):
        correct_set = {l.upper() for l in re.findall(r"[A-Za-z]", correct_raw)}
    else:
        correct_set = set()

    passed = extracted is not None and bool(correct_set) and extracted == correct_set
    return {
        "passed": passed,
        "type": "multi_choice",
        "format_valid": extracted is not None,
        "selected": sorted(extracted) if extracted is not None else [],
    }


def _build_multi_choice_feedback(
    agent_selected: set[str], round_record: dict, format_valid: bool = True
) -> str:
    """Generate feedback text for a multi_choice round.

    - Invalid format (no \\bbox{}) → format error message
    - Exact match → ``feedback.correct``
    - Otherwise → per-option explanations for missed and wrongly selected options,
      assembled from ``feedback.options``.
    """
    if not format_valid:
        return FORMAT_ERROR

    eval_cfg = round_record.get("eval", {})
    correct_raw = eval_cfg.get("answer", "")
    if isinstance(correct_raw, list):
        correct = {l.upper() for item in correct_raw for l in re.findall(r"[A-Za-z]", str(item))}
    elif isinstance(correct_raw, str):
        correct = {l.upper() for l in re.findall(r"[A-Za-z]", correct_raw)}
    else:
        correct = set()

    feedback_rec = round_record.get("feedback", {})
    if agent_selected == correct:
        return feedback_rec.get("correct", "")

    options_fb = feedback_rec.get("options", {})
    lines = []
    for opt in sorted(correct - agent_selected):      # missed: should have selected
        lines.append(missed_option(opt, options_fb.get(opt, "")))
    for opt in sorted(agent_selected - correct):      # wrong: should not have selected
        lines.append(wrong_option(opt, options_fb.get(opt, "")))
    lines.append(CONTINUE_REMINDER)
    return "\n".join(lines)


def _build_feedback_text(round_record: dict, inline_score: dict) -> str:
    """Build the feedback string for a round from its inline_score.

    Dispatches based on ``round_record["type"]``:
    - ``multi_choice``: calls :func:`_build_multi_choice_feedback`
    - ``file_check`` (and others): reads ``feedback.correct`` or ``feedback.incorrect``
    """
    question_type = round_record.get("type", "multi_choice")
    feedback_rec = round_record.get("feedback", {})

    if question_type == "multi_choice":
        selected = set(inline_score.get("selected", []))
        format_valid = inline_score.get("format_valid", True)
        return _build_multi_choice_feedback(selected, round_record, format_valid=format_valid)

    # file_check and other types: simple correct/incorrect branch
    passed = inline_score.get("passed", False)
    text = feedback_rec.get("correct" if passed else "incorrect", "")
    if not passed and text:
        text = f"{text}\n{FILE_CHECK_INCORRECT_SUFFIX}"
    return text


# ---------------------------------------------------------------------------
# Per-question and per-group runners
# ---------------------------------------------------------------------------


async def _run_question(
    test_id: str,
    group_id: str,
    round_id: str,
    query: str,
    session_id: str,
    openclaw_config_path: Path,
    openclaw_state_dir: Path,
    log_dir: Path,
    result_path: Path,
    project_root: Path,
    gateway_port: int | None = None,
    retry: int = 0,
    agent_id: str | None = None,
    question_type: str = "multi_choice",
) -> None:
    """Run a single round and write the result to *result_path*.

    If *result_path* already exists the agent call is skipped (breakpoint
    resume support).  Inline scoring is handled by the caller (_run_group).
    """
    if result_path.exists():
        print(f"  [skip] {test_id}/{group_id}/{round_id} (result already exists)")
        return

    result_path.parent.mkdir(parents=True, exist_ok=True)

    existing_logs = _get_existing_log_files(log_dir, session_id)
    started_at = time.time()
    last_error = ""

    status = "failed"
    answer = ""
    for attempt in range(retry + 1):
        rc, stdout, stderr = await _run_openclaw_agent(
            session_id=session_id,
            message=query,
            openclaw_config_path=openclaw_config_path,
            openclaw_state_dir=openclaw_state_dir,
            project_root=project_root,
            gateway_port=gateway_port,
        )
        if rc == 0:
            status = "success"
            answer = stdout
            break
        last_error = stderr or f"Exit code {rc}"
        if attempt < retry:
            print(f"  [retry {attempt + 1}/{retry}] {test_id}/{group_id}/{round_id}")

    finished_at = time.time()
    duration_ms = int((finished_at - started_at) * 1000)

    llm_log = _read_newest_log_after(log_dir, session_id, existing_logs)

    result: dict[str, Any] = {
        "test_id": test_id,
        "group_id": group_id,
        "round_id": round_id,
        "qa_id": round_id,  # kept for backwards compatibility
        "question_type": question_type,
        "question": query,
        "status": status,
        "run_metadata": {
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "retry_count": retry,
        },
        "llm_log": llm_log,
    }
    if status == "success":
        result["answer"] = answer
    else:
        result["error"] = last_error

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  [{status}] {test_id}/{group_id}/{round_id} ({duration_ms} ms)")


async def _run_group(
    test_id: str,
    group: dict,
    agent_id: str,
    original_session_id: str,
    work_openclaw_state_dir: Path,
    openclaw_config_path: Path,
    log_dir: Path,
    out_dir: Path,
    project_root: Path,
    retry: int,
    semaphore: asyncio.Semaphore,
    eval_dir: Path,
    eval_name: str,
    workspace_path: Path,
    gateway_port: int | None = None,
) -> None:
    """Run all rounds within a group serially.

    Implements:
    - Feedback injection: prepends "[上一步反馈] {text}" from the previous round
    - Inline scoring: scores each round immediately after the agent responds
    - Resume support: skips rounds that already have inline_score in their result
    - Standalone feedback: sends a final no-answer feedback message after the last round
    """
    async with semaphore:
        group_id = group["id"]
        _prepare_session(work_openclaw_state_dir, agent_id, original_session_id)

        rounds = group.get("rounds", [])
        if not rounds:
            return

        # prev_inline_score / prev_round_record: track state needed to build
        # feedback text for the *next* round (or standalone at the end).
        prev_inline_score: dict | None = None
        prev_round_record: dict | None = None

        for round_record in rounds:
            round_id = round_record["id"]
            question_type = round_record.get("type", "multi_choice")
            result_path = out_dir / test_id / group_id / round_id / "infer_result.json"

            # --- Resume check ---
            existing_inline_score: dict | None = None
            if result_path.exists():
                try:
                    existing_result = json.loads(result_path.read_text(encoding="utf-8"))
                    if "inline_score" in existing_result:
                        existing_inline_score = existing_result["inline_score"]
                except Exception:
                    pass

            if existing_inline_score is not None:
                # Fully resumed: track state for feedback chain and continue
                print(f"  [skip] {test_id}/{group_id}/{round_id} (inline_score exists)")
                prev_inline_score = existing_inline_score
                prev_round_record = round_record
                continue

            # --- Build query with optional feedback prefix ---
            question_text = round_record["question"]
            feedback_text: str | None = None
            if prev_inline_score is not None and prev_round_record is not None:
                candidate = _build_feedback_text(prev_round_record, prev_inline_score)
                if candidate:
                    feedback_text = candidate

            query = (
                with_feedback(feedback_text, question_text)
                if feedback_text
                else question_text
            )

            # --- Apply update actions before this round ---
            for upd in round_record.get("update", []):
                _execute_update(
                    update=upd,
                    agent_id=agent_id,
                    work_openclaw_state_dir=work_openclaw_state_dir,
                    eval_dir=eval_dir,
                    eval_name=eval_name,
                )

            # --- Run agent (skips internally if result already exists) ---
            await _run_question(
                test_id=test_id,
                group_id=group_id,
                round_id=round_id,
                query=query,
                session_id=original_session_id,
                openclaw_config_path=openclaw_config_path,
                openclaw_state_dir=work_openclaw_state_dir,
                log_dir=log_dir,
                result_path=result_path,
                project_root=project_root,
                gateway_port=gateway_port,
                retry=retry,
                question_type=question_type,
            )

            # --- Inline scoring ---
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except Exception:
                result = {}

            answer_text = result.get("answer", "")
            inline_score = _compute_inline_score(round_record, answer_text, workspace_path)

            result["inline_score"] = inline_score
            result_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            passed = inline_score.get("passed", False)
            print(f"  [inline_score] {test_id}/{group_id}/{round_id}: passed={passed}")

            prev_inline_score = inline_score
            prev_round_record = round_record

        # --- Standalone feedback after last round ---
        if prev_inline_score is None or prev_round_record is None:
            return

        feedback_marker = out_dir / test_id / group_id / "feedback_sent.marker"
        if feedback_marker.exists():
            return

        standalone_text = _build_feedback_text(prev_round_record, prev_inline_score)
        if not standalone_text:
            return

        print(f"  [feedback] sending standalone feedback for {test_id}/{group_id}")
        await _run_openclaw_agent(
            session_id=original_session_id,
            message=standalone_feedback(standalone_text),
            openclaw_config_path=openclaw_config_path,
            openclaw_state_dir=work_openclaw_state_dir,
            project_root=project_root,
            gateway_port=gateway_port,
        )
        feedback_marker.parent.mkdir(parents=True, exist_ok=True)
        feedback_marker.touch()


# ---------------------------------------------------------------------------
# Single-test runner (one isolated work copy + gateway per test)
# ---------------------------------------------------------------------------


async def _run_one_test(
    test: dict,
    workspace_src: Path,
    openclaw_state_dir: Path,
    openclaw_config_src: Path | None,
    eval_dir: Path,
    project_root: Path,
    out_dir: Path,
    retry: int,
    outer_semaphore: asyncio.Semaphore,
    query_reader: QueryReader,
) -> None:
    """Run all groups for one test scenario under its own work copy and gateway.

    Acquires *outer_semaphore* for the full duration so that at most
    ``workers`` tests run concurrently.  Groups within the test are always
    executed serially because they share the same session transcript and
    workspace state.
    """
    async with outer_semaphore:
        test_id  = test["id"]
        agent_id = test["agent"]
        session_id = test["session"]
        eval_name  = test["eval"]

        groups = query_reader.read_queries(eval_dir, eval_name)
        if not groups:
            print(f"[warn] No groups found for {test_id} (eval={eval_name})")
            return

        print(f"[plan] {test_id}: {len(groups)} group(s)")

        # Isolated work copy so this test never shares openclaw.json with others
        work_openclaw_state_dir = _prepare_work_copy(
            openclaw_state_dir, project_root, openclaw_config_src
        )
        work_dir = work_openclaw_state_dir.parent
        openclaw_json_path = work_openclaw_state_dir / "openclaw.json"

        # Per-test workspace (only the matching dayXX folder)
        workspace_copy = _copy_workspace_for_test(workspace_src, work_dir, test_id)
        _copy_eval_scripts(eval_dir, workspace_copy)
        _patch_agent_workspace(openclaw_json_path, agent_id, workspace_copy)

        log_dir = _resolve_log_dir(work_openclaw_state_dir, project_root)

        # Dedicated gateway for this work copy
        gateway_port = _find_free_port()
        gateway_proc, gateway_log = await _start_work_gateway(
            work_openclaw_state_dir, gateway_port
        )
        ready = await _wait_for_gateway(gateway_port)
        if not ready:
            if gateway_proc.returncode is None:
                gateway_proc.terminate()
                await gateway_proc.wait()
            output = _read_gateway_log(gateway_log)
            raise RuntimeError(
                f"[{test_id}] Gateway on port {gateway_port} did not become ready. "
                f"State dir: {work_openclaw_state_dir}"
                + (f"\nGateway output:\n{output}" if output else "")
            )
        print(f"[{test_id}] Gateway started on port {gateway_port}")

        # One semaphore per test: groups are always serial within a test
        group_semaphore = asyncio.Semaphore(1)
        try:
            for group in groups:
                await _run_group(
                    test_id=test_id,
                    group=group,
                    agent_id=agent_id,
                    original_session_id=session_id,
                    work_openclaw_state_dir=work_openclaw_state_dir,
                    openclaw_config_path=openclaw_json_path,
                    log_dir=log_dir,
                    out_dir=out_dir,
                    project_root=project_root,
                    retry=retry,
                    semaphore=group_semaphore,
                    eval_dir=eval_dir,
                    eval_name=eval_name,
                    workspace_path=workspace_copy,
                    gateway_port=gateway_port,
                )
        finally:
            if gateway_proc.returncode is None:
                gateway_proc.terminate()
                await gateway_proc.wait()
                print(f"[{test_id}] Gateway on port {gateway_port} stopped.")
            else:
                output = _read_gateway_log(gateway_log)
                raise RuntimeError(
                    f"[{test_id}] Gateway on port {gateway_port} crashed "
                    f"(exit={gateway_proc.returncode})."
                    + (f"\nGateway output:\n{output}" if output else "")
                )


# ---------------------------------------------------------------------------
# Single all_tests.json runner
# ---------------------------------------------------------------------------


def _trigger_memory_ingest(proxy_port: int = 30000) -> bool:
    """Call POST /v1/memory/ingest on the metaclaw proxy to flush all buffered sessions."""
    import urllib.request
    import urllib.error

    url = f"http://localhost:{proxy_port}/v1/memory/ingest"
    payload = json.dumps({}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            added = result.get("added", 0)
            buffered = result.get("buffered_turns", 0)
            sessions = result.get("sessions", [])
            sids = [s["session_id"][:20] for s in sessions]
            print(f"  [memory] ingest → added={added} from {buffered} turns, sessions={sids}")
            return True
    except urllib.error.HTTPError as e:
        print(f"  [memory] ERROR: ingest failed: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  [memory] ERROR: ingest failed: {e}")
        return False


def _trigger_train_step() -> bool:
    """Call ``metaclaw train-step`` as a subprocess and return True on success."""
    print("\n" + "=" * 60)
    print("[train-step] Triggering RL training step via 'metaclaw train-step' ...")
    print("=" * 60)
    proxy_port = os.environ.get("METACLAW_PROXY_PORT", "30000")
    try:
        result = subprocess.run(
            ["metaclaw", "train-step", "--port", proxy_port],
            capture_output=True,
            text=True,
            timeout=660,
        )
        if result.stdout:
            print(f"[train-step] {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"[train-step] WARNING: train-step exited with code {result.returncode}")
            if result.stderr:
                print(f"[train-step] stderr: {result.stderr.strip()}")
            return False
        return True
    except FileNotFoundError:
        print("[train-step] ERROR: 'metaclaw' command not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("[train-step] ERROR: train-step timed out (660s)")
        return False
    except Exception as e:
        print(f"[train-step] ERROR: {e}")
        return False


async def _run_one_all_tests(
    input_file: Path,
    out_dir: Path,
    workers: int,
    retry: int,
    query_reader: QueryReader,
    scene_per_train: int | None = None,
    memory: bool = False,
    memory_proxy_port: int = 30000,
) -> None:
    """Process all test scenarios in one all_tests.json.

    Tests run concurrently up to *workers* at a time.  Each test gets its own
    isolated openclaw_state copy and dedicated gateway so parallel tests never
    share mutable state.  Groups within each test are always executed serially
    (shared session transcript).

    When *scene_per_train* is set, ``metaclaw train-step`` is invoked after
    every N completed test scenes.

    When *memory* is True, ``POST /v1/memory/ingest`` is called on the
    metaclaw proxy after each test scene to trigger memory extraction.
    """
    project_root = get_project_root()
    all_tests = json.loads(input_file.read_text(encoding="utf-8"))

    # Validate and resolve workspace_src
    workspace_src_raw = all_tests.get("workspace_src")
    if not workspace_src_raw:
        raise ValueError("all_tests.json missing required field 'workspace_src'")
    workspace_src = resolve_path(
        workspace_src_raw.replace("${METACLAW_ROOT}", str(project_root))
    )
    if not workspace_src.exists():
        raise FileNotFoundError(f"workspace_src not found: {workspace_src}")

    openclaw_state_dir = resolve_path(all_tests["openclaw_state_dir"])
    if not openclaw_state_dir.exists():
        raise FileNotFoundError(f"openclaw_state_dir not found: {openclaw_state_dir}")

    openclaw_config_src: Path | None = None
    openclaw_config_file_raw = all_tests.get("openclaw_config_file")
    if openclaw_config_file_raw:
        openclaw_config_src = resolve_path(
            openclaw_config_file_raw.replace("${METACLAW_ROOT}", str(project_root))
        )
        if not openclaw_config_src.exists():
            raise FileNotFoundError(f"openclaw_config_file not found: {openclaw_config_src}")

    eval_dir = resolve_path(all_tests["eval_dir"])
    outer_semaphore = asyncio.Semaphore(workers)

    test_list = all_tests.get("test", [])

    _need_serial = (scene_per_train is not None and scene_per_train > 0) or memory
    if _need_serial:
        # Serial execution: needed for scene-per-train or memory ingest ordering.
        if workers != 1 and (scene_per_train is not None and scene_per_train > 0):
            print(
                f"[warn] --scene-per-train requires serial execution; "
                f"overriding workers from {workers} to 1"
            )
        if workers != 1 and memory:
            print(
                f"[warn] --memory requires serial execution; "
                f"overriding workers from {workers} to 1"
            )
        total_scenes = len(test_list)
        for i, test in enumerate(test_list, start=1):
            await _run_one_test(
                test=test,
                workspace_src=workspace_src,
                openclaw_state_dir=openclaw_state_dir,
                openclaw_config_src=openclaw_config_src,
                eval_dir=eval_dir,
                project_root=project_root,
                out_dir=out_dir,
                retry=retry,
                outer_semaphore=outer_semaphore,
                query_reader=query_reader,
            )
            # Skip memory ingest and RL training after the last scene
            # — no more scenes to benefit from the updated state.
            if i == total_scenes:
                break
            # Memory ingest after each test scene (except last)
            if memory:
                await asyncio.to_thread(_trigger_memory_ingest, memory_proxy_port)
            # RL training trigger (except last)
            if scene_per_train is not None and scene_per_train > 0 and i % scene_per_train == 0:
                await asyncio.to_thread(_trigger_train_step)
    else:
        # Original concurrent execution.
        tasks = [
            asyncio.create_task(
                _run_one_test(
                    test=test,
                    workspace_src=workspace_src,
                    openclaw_state_dir=openclaw_state_dir,
                    openclaw_config_src=openclaw_config_src,
                    eval_dir=eval_dir,
                    project_root=project_root,
                    out_dir=out_dir,
                    retry=retry,
                    outer_semaphore=outer_semaphore,
                    query_reader=query_reader,
                )
            )
            for test in test_list
        ]
        await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_infer(
    input_arg: str,
    output_arg: str,
    workers: int = 1,
    retry: int = 0,
    query_reader: QueryReader | None = None,
    scene_per_train: int | None = None,
    memory: bool = False,
    memory_proxy_port: int = 30000,
) -> None:
    """Run batch inference on all tests in all_tests.json (or directory).

    Args:
        input_arg: Path to all_tests.json or a directory containing them.
        output_arg: Output directory path.
        workers: Maximum number of tests that run concurrently (default: 1).
                 Each test gets its own isolated work copy and gateway.
                 Groups within a test are always executed serially.
        retry: Number of retries per failed question (default: 0).
        query_reader: Custom QueryReader (uses QuestionsJsonQueryReader by default).
        scene_per_train: If set, trigger ``metaclaw train-step`` every N scenes.
        memory: If True, trigger memory ingestion after each test scene.
        memory_proxy_port: MetaClaw proxy port for memory ingest calls.
    """
    if query_reader is None:
        query_reader = get_default_query_reader()

    input_path = resolve_path(input_arg)
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    all_tests_files = _find_all_tests_files(input_path)
    if not all_tests_files:
        raise FileNotFoundError(f"No all_tests.json found under: {input_path}")

    is_dir_input = input_path.is_dir()

    first = json.loads(all_tests_files[0].read_text(encoding="utf-8"))
    base_out = _prepare_output_dir(output_arg, first.get("name"))

    if scene_per_train is not None:
        print(f"\n[info] RL training enabled: train-step every {scene_per_train} scene(s)")
    if memory:
        print(f"\n[info] Memory ingestion enabled: ingest after each scene (proxy port {memory_proxy_port})")

    async def _main() -> None:
        for f in all_tests_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            name = data.get("name", f.stem)

            if is_dir_input:
                out_dir = base_out / name
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = base_out

            print(f"\n=== Processing {f} (name={name}) ===")
            print(f"Output: {out_dir}")
            await _run_one_all_tests(
                input_file=f,
                out_dir=out_dir,
                workers=workers,
                retry=retry,
                query_reader=query_reader,
                scene_per_train=scene_per_train,
                memory=memory,
                memory_proxy_port=memory_proxy_port,
            )

    asyncio.run(_main())
    print(f"\nInference complete. Results in: {base_out}")
