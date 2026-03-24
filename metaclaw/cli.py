"""
MetaClaw CLI entry point.

Usage:
    metaclaw setup          — interactive first-time configuration wizard
    metaclaw start          — one-click start (proxy + optional RL training)
    metaclaw stop           — stop a running MetaClaw instance
    metaclaw status         — check whether MetaClaw is running
    metaclaw config KEY VAL — set a config value (e.g. rl.enabled true)
    metaclaw config show    — show current config
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import click
except ImportError:
    print("MetaClaw requires 'click'. Install it with: pip install click")
    sys.exit(1)

from .config_store import CONFIG_FILE, ConfigStore
from . import runtime_state


def _default_daemon_log_path() -> Path:
    return Path.home() / ".metaclaw" / "metaclaw.log"


def _effective_proxy_port(config_store: ConfigStore, override_port: int | None) -> int:
    if override_port:
        return override_port
    return int(config_store.get("proxy.port") or 30000)


def _is_process_alive(pid: int) -> bool:
    return runtime_state.process_alive(pid)


def _read_pid() -> int | None:
    return runtime_state.read_pid()


def _clear_pid():
    runtime_state.clear_pid()


def _clear_pid_if_matches(pid: int):
    runtime_state.clear_pid_if_matches(pid)


def _healthz_ready(port: int, timeout: float = 0.5) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=timeout) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8"))
            return payload.get("ok") is True
    except Exception:
        return False


def _ensure_daemon_not_running():
    pid = _read_pid()
    if pid is None:
        return

    if not _is_process_alive(pid):
        _clear_pid()
        return

    raise click.ClickException(
        f"MetaClaw is already running (PID={pid}). "
        "Use 'metaclaw status' to inspect it or 'metaclaw stop' before starting a new daemon."
    )


def _wait_for_daemon_ready(proc, port: int, log_path: Path, timeout_s: float = 15.0):
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        returncode = proc.poll()
        if returncode is not None:
            raise click.ClickException(
                f"MetaClaw daemon exited with code {returncode}. Check logs: {log_path}"
            )
        if _healthz_ready(port):
            return
        time.sleep(0.2)

    raise click.ClickException(
        "MetaClaw daemon did not become healthy in time. "
        f"Check logs: {log_path}"
    )


def _build_session_override_store(
    config_store: ConfigStore,
    mode: str | None,
    port: int | None,
) -> tuple[ConfigStore, Path | None]:
    if not mode and not port:
        return config_store, None

    from .config_store import ConfigStore as _CS
    import tempfile
    import yaml

    data = config_store.load()
    if mode:
        data["mode"] = mode
    if port:
        data.setdefault("proxy", {})["port"] = port

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    try:
        yaml.dump(data, tmp)
    finally:
        tmp.close()
    tmp_path = Path(tmp.name)
    return _CS(config_file=tmp_path), tmp_path


def _spawn_daemon_process(
    mode: str | None,
    port: int | None,
    log_file: str | None,
    effective_port: int,
) -> tuple[int, Path]:
    import os
    import signal
    import subprocess

    log_path = Path(log_file).expanduser() if log_file else _default_daemon_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with runtime_state.daemon_start_lock():
            _ensure_daemon_not_running()

            cmd = [sys.executable, "-m", "metaclaw", "start"]
            if mode:
                cmd.extend(["--mode", mode])
            if port:
                cmd.extend(["--port", str(port)])

            with log_path.open("ab") as log_handle:
                child_env = os.environ.copy()
                child_env["METACLAW_RUNTIME_KIND"] = "daemon"
                child_env["METACLAW_RUNTIME_LOG_PATH"] = str(log_path)
                popen_kwargs = {
                    "stdin": subprocess.DEVNULL,
                    "stdout": log_handle,
                    "stderr": subprocess.STDOUT,
                    "close_fds": True,
                    "env": child_env,
                }
                if os.name == "nt":
                    creationflags = (
                        getattr(subprocess, "DETACHED_PROCESS", 0)
                        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                    )
                    if creationflags:
                        popen_kwargs["creationflags"] = creationflags
                else:
                    popen_kwargs["start_new_session"] = True
                proc = subprocess.Popen(cmd, **popen_kwargs)

            try:
                _wait_for_daemon_ready(proc, effective_port, log_path)
            except Exception:
                try:
                    if proc.poll() is None:
                        if os.name == "nt":
                            proc.terminate()
                        else:
                            os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            if os.name == "nt":
                                proc.kill()
                            else:
                                os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait(timeout=5)
                except Exception:
                    pass

                _clear_pid_if_matches(proc.pid)
                raise

            return proc.pid, log_path
    except RuntimeError as exc:
        owner_pid = exc.args[0] if exc.args else "?"
        raise click.ClickException(
            f"Another 'metaclaw start --daemon' is already in progress (PID={owner_pid}). "
            "Wait for it to finish or stop that process before retrying."
        ) from None


@click.group()
def metaclaw():
    """MetaClaw — OpenClaw skill injection and RL training."""


@metaclaw.command()
def setup():
    """Interactive first-time configuration wizard."""
    from .setup_wizard import SetupWizard
    SetupWizard().run()


@metaclaw.command()
@click.option(
    "--mode",
    type=click.Choice(["madmax", "skills_only", "rl"]),
    default=None,
    help="Override operating mode for this session.",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Override proxy port for this session.",
)
@click.option(
    "--daemon",
    "-d",
    is_flag=True,
    default=False,
    help="Run MetaClaw in the background.",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help="Log file used with --daemon (default: ~/.metaclaw/metaclaw.log).",
)
def start(mode: str | None, port: int | None, daemon: bool, log_file: str | None):
    """Start MetaClaw (proxy + optional RL training)."""
    import asyncio
    from .log_color import setup_logging

    setup_logging()

    cs = ConfigStore()
    if not cs.exists():
        click.echo(
            "No config found. Run 'metaclaw setup' first.",
            err=True,
        )
        sys.exit(1)

    if daemon:
        pid, log_path = _spawn_daemon_process(
            mode,
            port,
            log_file,
            effective_port=_effective_proxy_port(cs, port),
        )
        click.echo(
            f"MetaClaw started in background (PID={pid}). Logs: {log_path}. "
            "Use 'metaclaw status' to check health and 'metaclaw stop' to stop it."
        )
        return

    cs, temp_config_path = _build_session_override_store(cs, mode, port)

    from .launcher import MetaClawLauncher
    launcher = MetaClawLauncher(cs)
    try:
        asyncio.run(launcher.start())
    except KeyboardInterrupt:
        click.echo("\nInterrupted — stopping MetaClaw.")
        launcher.stop()
    finally:
        if temp_config_path is not None:
            temp_config_path.unlink(missing_ok=True)


@metaclaw.command()
def stop():
    """Stop a running MetaClaw instance."""
    import os
    import signal
    from pathlib import Path

    pid_file = Path.home() / ".metaclaw" / "metaclaw.pid"
    if not pid_file.exists():
        click.echo("MetaClaw is not running (no PID file found).")
        return
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        click.echo(f"Sent SIGTERM to PID {pid}.")
    except ProcessLookupError:
        click.echo("Process not found — cleaning up stale PID file.")
        pid_file.unlink(missing_ok=True)
    except Exception as e:
        click.echo(f"Error stopping MetaClaw: {e}", err=True)


@metaclaw.command()
def status():
    """Check whether MetaClaw is running."""
    import os
    from pathlib import Path

    pid_file = Path.home() / ".metaclaw" / "metaclaw.pid"
    if not pid_file.exists():
        click.echo("MetaClaw: not running")
        return

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
    except (ProcessLookupError, ValueError):
        click.echo("MetaClaw: not running (stale PID file)")
        pid_file.unlink(missing_ok=True)
        return

    cs = ConfigStore()
    port = int(cs.get("proxy.port") or 30000)
    mode = str(cs.get("mode") or "?")

    healthy = _healthz_ready(port, timeout=2.0)
    if healthy:
        click.echo(f"MetaClaw: running  (PID={pid}, mode={mode}, proxy=:{port})")
    else:
        click.echo(f"MetaClaw: starting (PID={pid}, mode={mode}, proxy=:{port})")

    # Show scheduler state if available.
    state_file = Path.home() / ".metaclaw" / "scheduler_state.json"
    if state_file.exists():
        try:
            import json
            sched = json.loads(state_file.read_text())
            state_val = sched.get("state", "?")
            sleep_win = sched.get("sleep_window", "?")
            idle_min = sched.get("idle_threshold_minutes", "?")
            updated_at = sched.get("updated_at", "?")
            click.echo(
                f"scheduler:  state={state_val}  "
                f"sleep={sleep_win}  idle≥{idle_min}min  "
                f"(updated {updated_at})"
            )
        except Exception:
            pass


@metaclaw.command(name="config")
@click.argument("key_or_action")
@click.argument("value", required=False)
def config_cmd(key_or_action: str, value: str | None):
    """Get or set a config value.

    Examples:\n
      metaclaw config show\n
      metaclaw config rl.enabled true\n
      metaclaw config proxy.port 30001
    """
    cs = ConfigStore()
    if key_or_action == "show":
        if not cs.exists():
            click.echo("No config file found. Run 'metaclaw setup' first.")
            return
        click.echo(f"Config file: {CONFIG_FILE}\n")
        click.echo(cs.describe())
        return

    if value is None:
        # Get mode
        result = cs.get(key_or_action)
        if result is None:
            click.echo(f"{key_or_action}: (not set)")
        else:
            click.echo(f"{key_or_action}: {result}")
        return

    cs.set(key_or_action, value)
    click.echo(f"Set {key_or_action} = {cs.get(key_or_action)}")


@metaclaw.group()
def skills():
    """Skill management commands."""


@skills.command(name="log")
@click.option(
    "--n", default=10, show_default=True,
    help="Number of most recent evolution events to show.",
)
@click.option(
    "--full", is_flag=True, default=False,
    help="Show full skill content (default: names and descriptions only).",
)
@click.option(
    "--file", "history_file", default="",
    help="Path to evolution_history.jsonl (default: auto-detect from config).",
)
def skills_log(n: int, full: bool, history_file: str):
    """Show the skill evolution history.

    Reads evolution_history.jsonl and prints a readable summary of each
    evolution event: when it happened, which failures triggered it, and
    what new skills were generated.
    """
    import json
    from pathlib import Path

    # Resolve history file path
    if not history_file:
        cs = ConfigStore()
        cfg = cs.to_metaclaw_config()
        history_file = cfg.skill_evolution_history_path

    path = Path(history_file).expanduser()
    if not path.exists():
        click.echo(
            f"No evolution history found at: {path}\n"
            "Skills evolve automatically after sessions. "
            "Make sure skills.auto_evolve is enabled.",
            err=True,
        )
        return

    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    except Exception as exc:
        click.echo(f"Error reading history file: {exc}", err=True)
        return

    if not lines:
        click.echo("Evolution history file is empty — no evolutions have run yet.")
        return

    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    total = len(records)
    shown = records[-n:]  # most recent N

    click.echo(f"\n{'='*60}")
    click.echo(f"  Skill Evolution Log  ({total} total events, showing last {len(shown)})")
    click.echo(f"{'='*60}\n")

    for i, rec in enumerate(shown, start=total - len(shown) + 1):
        ts        = rec.get("timestamp", "unknown time")
        n_fail    = rec.get("num_failures_analyzed", "?")
        n_gen     = rec.get("num_skills_generated", "?")
        names     = rec.get("skill_names", [])
        skills_detail = rec.get("skills", [])
        failure_prompts = rec.get("failure_prompts", [])

        click.echo(f"[#{i}]  {ts}")
        click.echo(f"  Failures analyzed: {n_fail}   Skills generated: {n_gen}")

        if names:
            click.echo(f"  New skills: {', '.join(names)}")

        if full and skills_detail:
            for sk in skills_detail:
                click.echo(f"\n  ── {sk['name']} ({sk.get('category','general')})")
                click.echo(f"     {sk.get('description','')}")
                content = sk.get("content", "")
                if content:
                    # Indent content lines
                    for line in content.splitlines():
                        click.echo(f"     {line}")

        if full and failure_prompts:
            click.echo(f"\n  ── Failure context (last 300 chars each):")
            for j, fp in enumerate(failure_prompts, 1):
                excerpt = fp.replace("\n", " ").strip()
                click.echo(f"     [{j}] ...{excerpt}")

        click.echo()

    total_skills = sum(r.get("num_skills_generated", 0) for r in records)
    click.echo(f"Total skills ever generated: {total_skills}")
    click.echo(f"History file: {path}\n")


@metaclaw.group()
def scheduler():
    """Scheduler management commands."""


@scheduler.command(name="status")
def scheduler_status():
    """Show the current slow-update scheduler state."""
    import json
    from pathlib import Path

    state_file = Path.home() / ".metaclaw" / "scheduler_state.json"
    if not state_file.exists():
        click.echo("Scheduler not running or not enabled.")
        return
    try:
        data = json.loads(state_file.read_text())
        click.echo(f"state:              {data.get('state', '?')}")
        click.echo(f"sleep window:       {data.get('sleep_window', '?')}")
        click.echo(f"idle threshold:     {data.get('idle_threshold_minutes', '?')} min")
        click.echo(f"last updated:       {data.get('updated_at', '?')}")
    except Exception as exc:
        click.echo(f"Error reading scheduler state: {exc}", err=True)


@scheduler.command(name="next-window")
def scheduler_next_window():
    """Estimate when the next slow-update window will open.

    Reads live scheduler state and configuration to give an approximate
    time until the next eligible idle/sleep/calendar window.
    """
    import json
    from pathlib import Path

    state_file = Path.home() / ".metaclaw" / "scheduler_state.json"
    if not state_file.exists():
        click.echo("Scheduler not running or not enabled.")
        return

    try:
        data = json.loads(state_file.read_text())
    except Exception as exc:
        click.echo(f"Error reading scheduler state: {exc}", err=True)
        return

    state = data.get("state", "?")
    click.echo(f"Current state:   {state}")
    click.echo(f"Sleep window:    {data.get('sleep_window', '?')}")
    click.echo(f"Idle threshold:  {data.get('idle_threshold_minutes', '?')} min")

    if state in ("window_open", "updating"):
        click.echo("→ A window is OPEN right now — RL update may be in progress.")
    elif state == "pausing":
        click.echo("→ Pausing current update (user became active).")
    else:
        click.echo(
            "→ Waiting for next idle/sleep/calendar window.\n"
            "  The scheduler checks every 60 seconds.\n"
            "  Next window opens when: sleep hours begin, "
            "or idle exceeds threshold, or a calendar event starts."
        )
