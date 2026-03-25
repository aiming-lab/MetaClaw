"""
MetaClaw CLI entry point.

Usage:
    metaclaw setup          — interactive first-time configuration wizard
    metaclaw start          — one-click start (proxy + optional RL training)
    metaclaw stop           — stop a running MetaClaw instance
    metaclaw status         — check whether MetaClaw is running
    metaclaw config KEY VAL — set a config value (e.g. rl.enabled true)
    metaclaw config show    — show current config
    metaclaw wechat-bridge   — run WeChat bridge (Node) to local proxy
    metaclaw wechat-relogin  — same bridge, but force QR (switch WeChat account)
    metaclaw wechat-check    — diagnose WeChat config / node / npm deps
"""

from __future__ import annotations

import sys

try:
    import click
except ImportError:
    print("MetaClaw requires 'click'. Install it with: pip install click")
    sys.exit(1)

from .config_store import CONFIG_FILE, ConfigStore


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
    type=click.Choice(["auto", "skills_only", "rl"]),
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
    "-c", "--config",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom config YAML file (default: ~/.metaclaw/config.yaml).",
)
def start(mode: str | None, port: int | None, config: str | None):
    """Start MetaClaw (proxy + optional RL training)."""
    import asyncio
    from pathlib import Path
    from .log_color import setup_logging

    setup_logging()

    if config:
        cs = ConfigStore(config_file=Path(config))
    else:
        cs = ConfigStore()
    if not cs.exists():
        click.echo(
            "No config found. Run 'metaclaw setup' first, or pass --config <path>.",
            err=True,
        )
        sys.exit(1)

    # Session-level overrides (don't persist)
    if mode or port:
        data = cs.load()
        if mode:
            data["mode"] = mode
        if port:
            data.setdefault("proxy", {})["port"] = port
        # Use an in-memory store for this session
        from .config_store import ConfigStore as _CS
        import tempfile, os, yaml
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        yaml.dump(data, tmp)
        tmp.close()
        cs = _CS(config_file=Path(tmp.name))

    from .launcher import MetaClawLauncher
    launcher = MetaClawLauncher(cs)
    try:
        asyncio.run(launcher.start())
    except KeyboardInterrupt:
        click.echo("\nInterrupted — stopping MetaClaw.")
        launcher.stop()


@metaclaw.command()
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    default=None,
    help="Config YAML whose proxy.port identifies the instance to stop.",
)
@click.option("--port", type=int, default=None, help="Proxy port of the instance to stop.")
def stop(config: str | None, port: int | None):
    """Stop a running MetaClaw instance."""
    import os
    import signal
    from pathlib import Path
    from .launcher import pid_file_for_port

    if port is None:
        if config:
            cs = ConfigStore(config_file=Path(config))
        else:
            cs = ConfigStore()
        port = cs.get("proxy.port") or 30000

    pid_file = pid_file_for_port(port)
    if not pid_file.exists():
        click.echo(f"MetaClaw is not running (no PID file for port {port}).")
        return
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        click.echo(f"Sent SIGTERM to PID {pid} (port {port}).")
    except ProcessLookupError:
        click.echo("Process not found — cleaning up stale PID file.")
        pid_file.unlink(missing_ok=True)
    except Exception as e:
        click.echo(f"Error stopping MetaClaw: {e}", err=True)


@metaclaw.command()
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    default=None,
    help="Config YAML whose proxy.port identifies the instance to query.",
)
@click.option("--port", type=int, default=None, help="Proxy port of the instance to query.")
def status(config: str | None, port: int | None):
    """Check whether MetaClaw is running."""
    import os
    from pathlib import Path
    from .launcher import pid_file_for_port

    if config:
        cs = ConfigStore(config_file=Path(config))
    else:
        cs = ConfigStore()
    if port is None:
        port = cs.get("proxy.port") or 30000

    pid_file = pid_file_for_port(port)
    if not pid_file.exists():
        click.echo(f"MetaClaw: not running (port {port})")
        return

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # check if process exists
    except (ProcessLookupError, ValueError):
        click.echo("MetaClaw: not running (stale PID file)")
        pid_file.unlink(missing_ok=True)
        return
    try:
        import urllib.request
        with urllib.request.urlopen(
            f"http://localhost:{port}/healthz", timeout=2
        ) as resp:
            healthy = resp.status == 200
    except Exception:
        healthy = False

    mode = cs.get("mode") or "?"
    if healthy:
        click.echo(f"MetaClaw: running  (PID={pid}, mode={mode}, proxy=:{port})")
    else:
        click.echo(f"MetaClaw: starting (PID={pid}, mode={mode}, proxy=:{port})")

    cfg = cs.to_metaclaw_config()
    if cfg.memory_enabled:
        from pathlib import Path as _P
        import json as _json

        policy_path = _P(cfg.memory_policy_path).expanduser()
        if policy_path.exists():
            try:
                policy = _json.loads(policy_path.read_text())
                click.echo(
                    "memory:     "
                    f"mode={policy.get('retrieval_mode', '?')}  "
                    f"units={policy.get('max_injected_units', '?')}  "
                    f"tokens={policy.get('max_injected_tokens', '?')}"
                )
            except Exception:
                click.echo(f"memory:     policy file unreadable ({policy_path})")

    # Show scheduler state if available.
    state_file = Path.home() / ".metaclaw" / "scheduler_state.json"
    if state_file.exists():
        try:
            import json
            sched = json.loads(state_file.read_text())
            state_val  = sched.get("state", "?")
            sleep_win  = sched.get("sleep_window", "?")
            idle_min   = sched.get("idle_threshold_minutes", "?")
            updated_at = sched.get("updated_at", "?")
            click.echo(
                f"scheduler:  state={state_val}  "
                f"sleep={sleep_win}  idle≥{idle_min}min  "
                f"(updated {updated_at})"
            )
        except Exception:
            pass


@metaclaw.command("wechat-bridge")
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    default=None,
    help="Config YAML (default: ~/.metaclaw/config.yaml).",
)
def wechat_bridge_cmd(config: str | None):
    """Run the WeChat personal bridge (Node + weixin-agent-sdk) against the local proxy.

    Reuses a saved session under ``~/.openclaw/openclaw-weixin`` when possible.
    To scan QR again (e.g. switch account), use ``metaclaw wechat-relogin``.

    Requires: Node.js, and ``npm install`` in the package ``wechat_node`` directory.
    Start ``metaclaw start`` first so /v1 is available.
    """
    from pathlib import Path

    from .log_color import setup_logging
    from .wechat_bridge import spawn_wechat_bridge

    setup_logging()
    if config:
        cs = ConfigStore(config_file=Path(config))
    else:
        cs = ConfigStore()
    if not cs.exists():
        click.echo("No config found. Run 'metaclaw setup' first.", err=True)
        sys.exit(1)
    cfg = cs.to_metaclaw_config()
    proc = spawn_wechat_bridge(cfg)
    if proc is None:
        sys.exit(1)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        click.echo("\nWeChat bridge stopped.")


@metaclaw.command("wechat-relogin")
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    default=None,
    help="Config YAML (default: ~/.metaclaw/config.yaml).",
)
def wechat_relogin_cmd(config: str | None):
    """Run the WeChat bridge and **force a QR login** for this run (new account / refresh).

    Same as ``wechat-bridge`` but ignores the saved session so you can scan again.
    Does not change config; ``metaclaw start`` still prefers the saved session afterward.
    """
    from pathlib import Path

    from .log_color import setup_logging
    from .wechat_bridge import spawn_wechat_bridge

    setup_logging()
    if config:
        cs = ConfigStore(config_file=Path(config))
    else:
        cs = ConfigStore()
    if not cs.exists():
        click.echo("No config found. Run 'metaclaw setup' first.", err=True)
        sys.exit(1)
    cfg = cs.to_metaclaw_config()
    proc = spawn_wechat_bridge(cfg, relogin=True)
    if proc is None:
        sys.exit(1)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        click.echo("\nWeChat bridge stopped.")


@metaclaw.command("wechat-check")
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    default=None,
    help="Config YAML (default: ~/.metaclaw/config.yaml).",
)
def wechat_check_cmd(config: str | None):
    """Print WeChat bridge diagnostics (config, paths, node, npm deps)."""
    import shutil
    from pathlib import Path

    from .wechat_bridge import wechat_bridge_dependency_issues

    if config:
        cs = ConfigStore(config_file=Path(config))
    else:
        cs = ConfigStore()
    if not cs.exists():
        click.echo("No config found. Run 'metaclaw setup' first.", err=True)
        sys.exit(1)
    cfg = cs.to_metaclaw_config()
    raw = cs.load().get("wechat", {})
    root, dep_issues = wechat_bridge_dependency_issues(cfg)
    bridge = root / "bridge.mjs"
    sdk = root / "node_modules" / "weixin-agent-sdk"
    node = shutil.which("node")

    click.echo(f"wechat.enabled (resolved): {cfg.wechat_enabled}")
    click.echo(f"wechat.enabled (raw in YAML): {raw.get('enabled', '(missing)')!r}")
    click.echo(f"bridge_dir: {root}")
    click.echo(f"bridge.mjs exists: {bridge.is_file()}")
    click.echo(f"weixin-agent-sdk installed: {sdk.is_dir()}")
    click.echo(f"node on PATH: {node or '(not found)'}")
    click.echo(f"proxy port: {cfg.proxy_port}")
    click.echo(f"METACLAW_MODEL would be: {cfg.llm_model_id or cfg.served_model_name or 'metaclaw-model'!r}")

    if not cfg.wechat_enabled:
        click.echo("\n→ Enable: metaclaw config wechat.enabled true", err=True)
    for line in dep_issues:
        click.echo(f"\n→ {line}", err=True)
    if not node:
        click.echo("\n→ Install Node.js and ensure `node` is on PATH", err=True)

    ok = cfg.wechat_enabled and not dep_issues and bool(node)
    sys.exit(0 if ok else 1)


@metaclaw.command(name="train-step")
@click.option(
    "--port",
    type=int,
    default=None,
    help="Override proxy port (default: read from config).",
)
@click.option(
    "--timeout",
    type=int,
    default=600,
    help="Timeout in seconds (default: 600).",
)
def train_step(port: int | None, timeout: int):
    """Trigger a single RL training step on the running MetaClaw instance.

    Sends a request to the running proxy's admin endpoint and waits for the
    training step to complete.  Requires MetaClaw to be running in RL/auto
    mode.  Useful for bench-driven experiments or manual control.
    """
    import json
    import urllib.request
    import urllib.error

    if port is None:
        cs = ConfigStore()
        port = cs.get("proxy.port") or 30000

    url = f"http://localhost:{port}/v1/admin/train_step"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        click.echo(f"Error ({e.code}): {body}", err=True)
        sys.exit(1)
    except urllib.error.URLError as e:
        click.echo(
            f"Cannot connect to MetaClaw at port {port}: {e.reason}\n"
            "Is MetaClaw running? Try: metaclaw status",
            err=True,
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    status = result.get("status", "unknown")
    if status == "ok":
        click.echo(
            f"Train step #{result.get('step', '?')} complete: "
            f"samples={result.get('samples', '?')} "
            f"mean_reward={result.get('mean_reward', '?')} "
            f"success_rate={result.get('success_rate', '?')}"
        )
    elif status == "skipped":
        click.echo(f"Skipped: {result.get('message', 'no samples')}")
    else:
        click.echo(f"Error: {result.get('message', 'unknown error')}", err=True)
        sys.exit(1)


@metaclaw.command(name="config")
@click.argument("key_or_action")
@click.argument("value", required=False)
def config_cmd(key_or_action: str, value: str | None):
    """Get or set a config value.

    Examples:\n
      metaclaw config show\n
      metaclaw config rl.enabled true\n
      metaclaw config proxy.port 30001\n
      metaclaw config wechat.enabled true\n
      metaclaw config wechat.bridge_dir /path/to/custom/wechat_node
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
@metaclaw.group()
def memory():
    """Memory management commands."""


@memory.command(name="status")
def memory_status():
    """Show the current memory policy and storage configuration."""
    import json
    from pathlib import Path

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    click.echo(f"enabled:            {cfg.memory_enabled}")
    click.echo(f"store:              {cfg.memory_store_path}")
    click.echo(f"default scope:      {cfg.memory_scope}")
    click.echo(f"configured mode:    {cfg.memory_retrieval_mode}")
    click.echo(f"embeddings enabled: {cfg.memory_use_embeddings}")
    click.echo(f"policy file:        {cfg.memory_policy_path}")
    click.echo(f"telemetry file:     {cfg.memory_telemetry_path}")
    click.echo(f"stale review hrs:   {cfg.memory_review_stale_after_hours}")
    upgrade_history_path = Path(cfg.memory_dir).expanduser() / "upgrade_history.jsonl"
    upgrade_worker_state_path = Path(cfg.memory_dir).expanduser() / "upgrade_worker_state.json"
    upgrade_alerts_path = Path(cfg.memory_dir).expanduser() / "upgrade_alerts.json"
    upgrade_alerts_history_path = Path(cfg.memory_dir).expanduser() / "upgrade_alerts_history.jsonl"

    policy_path = Path(cfg.memory_policy_path).expanduser()
    if not policy_path.exists():
        click.echo("policy state:       not initialized")
        return
    try:
        data = json.loads(policy_path.read_text())
    except Exception as exc:
        click.echo(f"policy state:       unreadable ({exc})", err=True)
        return

    click.echo(f"active mode:        {data.get('retrieval_mode', '?')}")
    click.echo(f"max units:          {data.get('max_injected_units', '?')}")
    click.echo(f"max tokens:         {data.get('max_injected_tokens', '?')}")
    click.echo(f"recent bonus hours: {data.get('recent_bonus_hours', '?')}")
    notes = data.get("notes", [])
    click.echo(f"notes:              {len(notes)}")
    for note in notes[-5:]:
        click.echo(f"  - {note}")

    telemetry_path = Path(cfg.memory_telemetry_path).expanduser()
    if telemetry_path.exists():
        try:
            lines = [line for line in telemetry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            click.echo(f"telemetry events:   {len(lines)}")
        except Exception:
            click.echo("telemetry events:   unreadable")
    if upgrade_history_path.exists():
        try:
            from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

            orchestrator = MemorySelfUpgradeOrchestrator(
                cfg,
                history_path=str(upgrade_history_path),
            )
            summary = orchestrator.summarize_history()
            review_summary = orchestrator.summarize_review_queue(
                stale_after_hours=cfg.memory_review_stale_after_hours
            )
            review_history = orchestrator.summarize_review_history()
            health = orchestrator.summarize_operational_health(
                stale_after_hours=cfg.memory_review_stale_after_hours
            )
            click.echo(f"upgrade decisions:  {summary['total']}")
            click.echo(f"promoted count:     {summary['promoted']}")
            click.echo(f"pending review:     {summary['pending_review']}")
            click.echo(f"stale review:       {review_summary['stale_count']}")
            click.echo(f"oldest review hrs:  {review_summary['oldest_age_hours']}")
            click.echo(f"recent decisions:   {summary['recent_total']}")
            click.echo(f"recent promoted:    {summary['recent_promoted']}")
            click.echo(f"recent approvals:   {review_history['recent_approved']}")
            click.echo(f"recent rejections:  {review_history['recent_rejected']}")
            click.echo(f"health level:       {health['level']}")
            click.echo(f"health reasons:     {', '.join(health['reasons']) or '-'}")
        except Exception:
            click.echo("upgrade decisions:  unreadable")
    if upgrade_worker_state_path.exists():
        try:
            worker_state = json.loads(upgrade_worker_state_path.read_text(encoding="utf-8"))
            click.echo(f"upgrade worker:     {worker_state.get('state', '?')}")
            click.echo(f"worker detail:      {worker_state.get('detail', '')}")
        except Exception:
            click.echo("upgrade worker:     unreadable")
    if upgrade_alerts_path.exists():
        try:
            payload = json.loads(upgrade_alerts_path.read_text(encoding="utf-8"))
            alerts = payload.get("alerts", [])
            click.echo(f"upgrade alerts:     {len(alerts)}")
            if alerts:
                first = alerts[0]
                click.echo(
                    "alert summary:      "
                    f"{first.get('code', '?')} level={first.get('level', '?')} "
                    f"pending={first.get('pending_count', '?')} stale={first.get('stale_count', '?')}"
                )
        except Exception:
            click.echo("upgrade alerts:     unreadable")
    if upgrade_alerts_history_path.exists():
        try:
            count = len(
                [line for line in upgrade_alerts_history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            )
            click.echo(f"alert history:      {count}")
        except Exception:
            click.echo("alert history:      unreadable")
    health_history_path = Path(cfg.memory_dir).expanduser() / "upgrade_health_history.jsonl"
    if health_history_path.exists():
        try:
            from .memory.upgrade_worker import MemoryUpgradeWorker

            worker = MemoryUpgradeWorker(cfg)
            health_summary = worker.summarize_health_history()
            click.echo(f"health snapshots:   {health_summary['total_snapshots']}")
            click.echo(f"health healthy:     {health_summary['healthy_rate']}")
            click.echo(f"health warning:     {health_summary['warning_rate']}")
            click.echo(f"health critical:    {health_summary['critical_rate']}")
        except Exception:
            click.echo("health snapshots:   unreadable")


@memory.command(name="rollback")
@click.option("--steps", default=1, show_default=True, type=int, help="How many policy revisions to roll back.")
def memory_rollback(steps: int):
    """Roll back the persisted memory policy to an earlier revision."""
    from .memory.policy_store import MemoryPolicyStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryPolicyStore(cfg.memory_policy_path)
    try:
        state = store.rollback(steps=steps)
    except Exception as exc:
        click.echo(f"Rollback failed: {exc}", err=True)
        raise SystemExit(1)

    click.echo("Rolled back memory policy.")
    click.echo(f"mode:               {state.retrieval_mode}")
    click.echo(f"max units:          {state.max_injected_units}")
    click.echo(f"max tokens:         {state.max_injected_tokens}")


@memory.command(name="stats")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--json-out", default="", help="Optional JSON output path.")
def memory_stats(scope: str, json_out: str):
    """Show detailed memory pool analytics."""
    import json as json_mod

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.metrics import summarize_memory_store
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    stats = summarize_memory_store(store, scope)

    click.echo(f"Scope:            {scope}")
    click.echo(f"Total memories:   {stats['total']}")
    click.echo(f"Active memories:  {stats['active']}")
    click.echo(f"Superseded:       {stats.get('superseded', 0)}")
    click.echo(f"Memory density:   {stats['memory_density']:.2%}")
    click.echo(f"Dominant type:    {stats.get('dominant_type', '-')}")
    click.echo(f"Type diversity:   {stats.get('type_count', 0)} types")
    click.echo()

    type_ratios = stats.get("type_ratios", {})
    if type_ratios:
        click.echo("Type distribution:")
        for t, ratio in sorted(type_ratios.items(), key=lambda x: -x[1]):
            count = stats.get("active_by_type", {}).get(t, 0)
            click.echo(f"  {t:30s} {count:4d} ({ratio:.1%})")

    if json_out:
        from pathlib import Path

        Path(json_out).write_text(json_mod.dumps(stats, indent=2), encoding="utf-8")
        click.echo(f"\nStats written to {json_out}")
    store.close()


@memory.command(name="search")
@click.argument("query")
@click.option("--scope", default="", help="Memory scope to search. Defaults to config scope.")
@click.option("--limit", "result_limit", default=10, show_default=True, type=int, help="Max results.")
@click.option("--json-out", default="", help="Optional JSON output path.")
def memory_search(query: str, scope: str, result_limit: int, json_out: str):
    """Search active memories by keyword query."""
    import json as json_mod

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    hits = store.search_keyword(scope, query, limit=result_limit)
    if not hits:
        click.echo("No matching memories found.")
        store.close()
        return
    click.echo(f"Found {len(hits)} matching memories:\n")
    results = []
    for i, hit in enumerate(hits, 1):
        click.echo(f"  [{i}] score={hit.score:.3f} type={hit.unit.memory_type.value}")
        click.echo(f"      id={hit.unit.memory_id}")
        content_preview = hit.unit.content[:200].replace("\n", " ")
        click.echo(f"      {content_preview}")
        if hit.matched_terms:
            click.echo(f"      matched: {', '.join(hit.matched_terms[:8])}")
        click.echo()
        results.append({
            "memory_id": hit.unit.memory_id,
            "score": round(hit.score, 4),
            "type": hit.unit.memory_type.value,
            "content": hit.unit.content[:500],
            "matched_terms": hit.matched_terms[:8],
            "importance": hit.unit.importance,
            "confidence": hit.unit.confidence,
        })
    if json_out:
        from pathlib import Path

        Path(json_out).write_text(json_mod.dumps(results, indent=2), encoding="utf-8")
        click.echo(f"Results written to {json_out}")
    store.close()


@memory.command(name="export")
@click.option("--scope", default="", help="Memory scope to export. Defaults to config scope.")
@click.option("--out", "out_path", required=True, help="Output JSONL path.")
@click.option("--include-superseded", is_flag=True, default=False, help="Include superseded memories.")
def memory_export(scope: str, out_path: str, include_superseded: bool):
    """Export active memories to JSONL for backup or migration."""
    import json as json_mod
    from pathlib import Path

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    if include_superseded:
        # Export all memories regardless of status.
        rows = store.conn.execute(
            "SELECT * FROM memories WHERE scope_id = ? ORDER BY updated_at DESC",
            (scope,),
        ).fetchall()
        units = [store._row_to_unit(row) for row in rows]
    else:
        units = store.list_active(scope, limit=10000)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for unit in units:
            record = {
                "memory_id": unit.memory_id,
                "scope_id": unit.scope_id,
                "memory_type": unit.memory_type.value,
                "content": unit.content,
                "summary": unit.summary,
                "source_session_id": unit.source_session_id,
                "source_turn_start": unit.source_turn_start,
                "source_turn_end": unit.source_turn_end,
                "entities": unit.entities,
                "topics": unit.topics,
                "importance": unit.importance,
                "confidence": unit.confidence,
                "access_count": unit.access_count,
                "reinforcement_score": unit.reinforcement_score,
                "status": unit.status.value,
                "supersedes": unit.supersedes,
                "superseded_by": unit.superseded_by,
                "created_at": unit.created_at,
                "updated_at": unit.updated_at,
                "last_accessed_at": unit.last_accessed_at,
            }
            f.write(json_mod.dumps(record, ensure_ascii=False) + "\n")

    click.echo(f"Exported {len(units)} memories to {out_path}")
    store.close()


@memory.command(name="import")
@click.option("--in", "in_path", required=True, help="Input JSONL path.")
@click.option("--scope", default="", help="Override scope for imported memories.")
def memory_import(in_path: str, scope: str):
    """Import memories from a JSONL backup."""
    import json as json_mod
    from pathlib import Path

    from .memory.models import MemoryType, MemoryUnit, MemoryStatus

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    imported = 0
    path = Path(in_path)
    if not path.exists():
        click.echo(f"File not found: {in_path}", err=True)
        store.close()
        raise SystemExit(1)

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json_mod.loads(line)
        except json_mod.JSONDecodeError:
            continue
        unit = MemoryUnit(
            memory_id=record["memory_id"],
            scope_id=scope or record.get("scope_id", cfg.memory_scope),
            memory_type=MemoryType(record["memory_type"]),
            content=record["content"],
            summary=record.get("summary", ""),
            source_session_id=record.get("source_session_id", ""),
            source_turn_start=record.get("source_turn_start", 0),
            source_turn_end=record.get("source_turn_end", 0),
            entities=record.get("entities", []),
            topics=record.get("topics", []),
            importance=record.get("importance", 0.5),
            confidence=record.get("confidence", 0.7),
            access_count=record.get("access_count", 0),
            reinforcement_score=record.get("reinforcement_score", 0.0),
            status=MemoryStatus(record.get("status", "active")),
            supersedes=record.get("supersedes", []),
            superseded_by=record.get("superseded_by", ""),
            created_at=record.get("created_at", ""),
            updated_at=record.get("updated_at", ""),
            last_accessed_at=record.get("last_accessed_at", ""),
        )
        store.add_memories([unit])
        imported += 1

    click.echo(f"Imported {imported} memories from {in_path}")
    store.close()


@memory.command(name="summary")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--per-type", default=3, help="Max memories to show per type.")
def memory_summary(scope: str, per_type: int):
    """Show a concise summary of the memory pool."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    summary = manager.get_pool_summary(scope_id=scope or None, max_per_type=per_type)
    manager.close()
    click.echo(summary)


@memory.command(name="diagnose")
@click.option("--scope", default="", help="Memory scope to diagnose. Defaults to config scope.")
def memory_diagnose(scope: str):
    """Run diagnostics on the memory subsystem and report issues."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.diagnose(scope_id=scope or None)
    manager.close()

    click.echo(f"Scope: {result['scope_id']}")
    click.echo(f"Store: {result['store']['active']} active, {result['store']['type_count']} types, dominant={result['store']['dominant_type']}")
    click.echo(f"Access: avg={result['access']['avg_access_count']}, never_accessed={result['access']['never_accessed']}")
    click.echo(f"Retrieval: {result['retrieval']['recent_events']} recent events, avg_retrieved={result['retrieval']['avg_retrieved']}, zero={result['retrieval']['zero_retrieval_count']}")
    click.echo(f"Policy: mode={result['policy']['retrieval_mode']}, units={result['policy']['max_injected_units']}, tokens={result['policy']['max_injected_tokens']}")
    if result['issues']:
        click.echo(f"Issues: {', '.join(result['issues'])}")
    else:
        click.echo("No issues detected.")


@memory.command(name="gc")
@click.option("--scope", default="", help="Memory scope to garbage-collect. Defaults to config scope.")
def memory_gc(scope: str):
    """Garbage-collect fully superseded memory chains."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    result = store.garbage_collect(scope)
    if result["removed"] == 0:
        click.echo("No orphaned superseded memories to clean up.")
    else:
        store.compact()
        click.echo(f"Removed {result['removed']} orphaned superseded memories.")
    store.close()


@memory.command(name="ttl")
@click.argument("memory_id")
@click.argument("expires_at")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_ttl(memory_id: str, expires_at: str, scope: str):
    """Set or clear a TTL on a memory. Pass empty string '' to clear."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    ok = store.set_ttl(memory_id, expires_at)
    if ok:
        if expires_at:
            click.echo(f"Set TTL on {memory_id}: expires at {expires_at}")
        else:
            click.echo(f"Cleared TTL on {memory_id}")
    else:
        click.echo(f"Memory {memory_id} not found.")
    store.close()


@memory.command(name="expire")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_expire(scope: str):
    """Archive all memories that have passed their TTL."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    count = store.expire_stale(scope)
    if count:
        click.echo(f"Archived {count} expired memor{'y' if count == 1 else 'ies'}.")
    else:
        click.echo("No expired memories to archive.")
    store.close()


@memory.command(name="share")
@click.argument("memory_id")
@click.argument("target_scope")
def memory_share(memory_id: str, target_scope: str):
    """Copy a memory to another scope for knowledge sharing."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    new_id = store.share_to_scope(memory_id, target_scope)
    if new_id:
        click.echo(f"Shared memory {memory_id} to scope '{target_scope}' as {new_id}")
    else:
        click.echo(f"Memory {memory_id} not found.")
    store.close()


@memory.command(name="export-json")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--output", "-o", default="", help="Output file path. Defaults to stdout.")
def memory_export_json(scope: str, output: str):
    """Export all active memories for a scope as JSON."""
    import json as _json
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    data = store.export_scope_json(scope)
    json_str = _json.dumps(data, indent=2, ensure_ascii=False)
    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Exported {len(data)} memories to {output}")
    else:
        click.echo(json_str)
    store.close()


@memory.command(name="merge")
@click.argument("id_a")
@click.argument("id_b")
@click.argument("content")
@click.option("--summary", default="", help="Summary for the merged memory.")
def memory_merge(id_a: str, id_b: str, content: str, summary: str):
    """Merge two memories into one, superseding both originals."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    new_id = store.merge_memories(id_a, id_b, content, summary)
    if new_id:
        click.echo(f"Merged {id_a[:8]} + {id_b[:8]} -> {new_id}")
    else:
        click.echo("One or both memory IDs not found.")
    store.close()


@memory.command(name="import-json")
@click.argument("input_path")
@click.option("--scope", default="", help="Target scope. If empty, uses original scope from data.")
def memory_import_json(input_path: str, scope: str):
    """Import memories from a JSON file (as produced by export-json)."""
    import json as _json
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    with open(input_path) as f:
        data = _json.load(f)
    target = scope or None
    count = store.import_memories_json(data, target_scope_id=target)
    click.echo(f"Imported {count} memories.")
    store.close()


@memory.command(name="type-ttl")
@click.argument("memory_type")
@click.argument("expires_at")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_type_ttl(memory_type: str, expires_at: str, scope: str):
    """Set TTL on all memories of a given type."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore
    from .memory.models import MemoryType as MT

    try:
        mt = MT(memory_type)
    except ValueError:
        click.echo(f"Invalid memory type: {memory_type}. Valid types: {[t.value for t in MT]}")
        return
    store = MemoryStore(cfg.memory_store_path)
    count = store.set_type_ttl(scope, mt, expires_at)
    click.echo(f"Set TTL on {count} {memory_type} memories (expires: {expires_at}).")
    store.close()


@memory.command(name="history")
@click.argument("memory_id")
def memory_history(memory_id: str):
    """Show version history for a memory (supersedes chain)."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    history = store.get_memory_history(memory_id)
    if not history:
        click.echo(f"No history found for {memory_id}.")
    else:
        for entry in history:
            status = entry["status"]
            marker = "*" if entry["memory_id"] == memory_id else " "
            click.echo(
                f" {marker} [{status}] {entry['memory_id'][:12]} "
                f"imp={entry['importance']:.2f} {entry['content'][:80]}"
            )
            if entry.get("superseded_by"):
                click.echo(f"     -> superseded by {entry['superseded_by'][:12]}")
    store.close()


@memory.command(name="analytics")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_analytics(scope: str):
    """Show comprehensive analytics for a scope."""
    import json as _json
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    analytics = store.get_scope_analytics(scope)
    click.echo(_json.dumps(analytics, indent=2))
    store.close()


@memory.command(name="tag")
@click.argument("memory_id")
@click.argument("tags", nargs=-1, required=True)
@click.option("--remove", is_flag=True, help="Remove tags instead of adding.")
def memory_tag(memory_id: str, tags: tuple, remove: bool):
    """Add or remove tags on a memory."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    tag_list = list(tags)
    if remove:
        ok = store.remove_tags(memory_id, tag_list)
        action = "Removed"
    else:
        ok = store.add_tags(memory_id, tag_list)
        action = "Added"
    if ok:
        click.echo(f"{action} tags {tag_list} on {memory_id[:12]}")
    else:
        click.echo(f"Memory {memory_id} not found.")
    store.close()


@memory.command(name="find-tag")
@click.argument("tag")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_find_tag(tag: str, scope: str):
    """Find memories with a given tag."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    units = store.search_by_tag(scope, tag)
    if not units:
        click.echo(f"No memories found with tag '{tag}'.")
    else:
        for u in units:
            click.echo(f"  {u.memory_id[:12]} [{u.memory_type.value}] {u.content[:80]}")
    store.close()


@memory.command(name="scopes")
def memory_scopes():
    """List all scopes in the memory store."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    scopes = store.list_scopes()
    if not scopes:
        click.echo("No scopes found.")
    else:
        for s in scopes:
            click.echo(f"  {s['scope_id']}: {s['active']} active / {s['total']} total")
    store.close()


@memory.command(name="snapshot")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--output", "-o", required=True, help="Output JSON file path.")
def memory_snapshot(scope: str, output: str):
    """Save a point-in-time snapshot of a scope for rollback."""
    import json as _json
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    snapshot = store.snapshot_scope(scope)
    with open(output, "w") as f:
        _json.dump(snapshot, f, indent=2, ensure_ascii=False)
    count = len(snapshot.get("memories", []))
    click.echo(f"Saved snapshot of {count} memories to {output}")
    store.close()


@memory.command(name="restore")
@click.argument("snapshot_path")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
def memory_restore(snapshot_path: str, yes: bool):
    """Restore a scope from a snapshot file (archives current state first)."""
    import json as _json
    if not yes:
        click.confirm("This will archive current memories and restore from snapshot. Continue?", abort=True)
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    with open(snapshot_path) as f:
        snapshot = _json.load(f)
    count = store.restore_snapshot(snapshot)
    click.echo(f"Restored {count} memories from snapshot.")
    store.close()


@memory.command(name="events")
@click.option("--scope", default="", help="Filter by scope. Shows all if empty.")
@click.option("--limit", default=20, help="Max events to show.")
def memory_events(scope: str, limit: int):
    """Show recent memory mutation events (audit log)."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    events = store.get_event_log(scope_id=scope, limit=limit)
    if not events:
        click.echo("No events recorded.")
    else:
        for e in events:
            click.echo(
                f"  {e['timestamp']} {e['event_type']:10s} {e['memory_id'][:12]} "
                f"{e['scope_id'] or '-':12s} {e['detail'][:60]}"
            )
    store.close()


@memory.command(name="similar")
@click.argument("memory_id")
@click.option("--limit", default=5, help="Max similar memories to show.")
def memory_similar(memory_id: str, limit: int):
    """Find memories similar to a given memory."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    results = store.find_similar(memory_id, limit)
    if not results:
        click.echo(f"No similar memories found for {memory_id[:12]}.")
    else:
        for unit, score in results:
            click.echo(
                f"  {score:.2f} {unit.memory_id[:12]} [{unit.memory_type.value}] {unit.content[:80]}"
            )
    store.close()


@memory.command(name="health")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_health(scope: str):
    """Show health score (0-100) for a memory scope."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    health = store.compute_health_score(scope)
    score = health.get("score", 0)
    count = health.get("active_count", 0)
    click.echo(f"Health Score: {score}/100 ({count} active memories)")
    components = health.get("components", {})
    for name, value in components.items():
        bar = "#" * int(value)
        click.echo(f"  {name:20s}: {value:5.1f}/25 {bar}")
    store.close()


@memory.command(name="duplicates")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--threshold", default=0.80, help="Similarity threshold (0-1).")
def memory_duplicates(scope: str, threshold: float):
    """Find near-duplicate memories in a scope."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    dups = store.find_duplicates(scope, threshold)
    if not dups:
        click.echo("No duplicates found.")
    else:
        click.echo(f"Found {len(dups)} near-duplicate pair(s):")
        for d in dups:
            click.echo(
                f"  {d['similarity']:.2f} {d['id_a'][:12]} vs {d['id_b'][:12]} [{d['type']}]"
            )
            click.echo(f"    A: {d['content_a'][:70]}")
            click.echo(f"    B: {d['content_b'][:70]}")
    store.close()


@memory.command(name="search-advanced")
@click.option("--scope", default="", help="Memory scope.")
@click.option("--keyword", default="", help="Keyword to search in content.")
@click.option("--type", "memory_type", default="", help="Filter by memory type.")
@click.option("--tag", default="", help="Filter by tag.")
@click.option("--min-importance", default=0.0, help="Minimum importance.")
@click.option("--limit", default=20, help="Max results.")
def memory_search_advanced(scope: str, keyword: str, memory_type: str, tag: str, min_importance: float, limit: int):
    """Search memories with combined criteria (keyword + type + tag + importance)."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    results = store.search_advanced(scope, keyword, memory_type, tag, min_importance, limit)
    if not results:
        click.echo("No matching memories found.")
    else:
        for u in results:
            tags_str = f" [{', '.join(u.tags)}]" if u.tags else ""
            click.echo(
                f"  {u.memory_id[:12]} [{u.memory_type.value}] imp={u.importance:.2f}{tags_str} {u.content[:80]}"
            )
    store.close()


@memory.command(name="compare-scopes")
@click.argument("scope_a")
@click.argument("scope_b")
def memory_compare_scopes(scope_a: str, scope_b: str):
    """Compare two scopes to find shared and unique memories."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    result = store.compare_scopes(scope_a, scope_b)
    click.echo(f"Scope '{scope_a}': {result['scope_a_count']} memories")
    click.echo(f"Scope '{scope_b}': {result['scope_b_count']} memories")
    click.echo(f"Shared: {result['shared_count']}")
    click.echo(f"Unique to '{scope_a}': {result['unique_to_a']}")
    click.echo(f"Unique to '{scope_b}': {result['unique_to_b']}")
    if result.get("shared_content"):
        click.echo("\nShared content samples:")
        for c in result["shared_content"]:
            click.echo(f"  - {c}")
    store.close()


@memory.command(name="rebalance")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_rebalance(scope: str):
    """Rebalance clustered importance values for better retrieval differentiation."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.rebalance_importance(scope_id=scope or None)
    manager.close()
    click.echo(f"Adjusted {result['adjusted']} memor{'y' if result['adjusted'] == 1 else 'ies'}.")


@memory.command(name="resolve-conflicts")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_resolve_conflicts(scope: str):
    """Auto-resolve conflicts by superseding older memories."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.auto_resolve_conflicts(scope_id=scope or None)
    manager.close()
    click.echo(
        f"Resolved {result['resolved']} of {result.get('total_conflicts', 0)} conflict(s)."
    )


@memory.command(name="trend")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=10, help="Max snapshots to show.")
def memory_trend(scope: str, limit: int):
    """Show memory pool trends over time."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore

    store = MemoryStore(cfg.memory_store_path)
    snapshots = store.get_stats_trend(scope, limit)
    if not snapshots:
        click.echo("No trend data available. Stats are recorded after each ingestion.")
    else:
        click.echo(f"{'Timestamp':<25s} {'Active':>7s} {'Total':>7s} {'Health':>7s}")
        click.echo("-" * 48)
        for s in snapshots:
            click.echo(
                f"{s.get('timestamp', '?'):<25s} {s.get('active', 0):>7d} "
                f"{s.get('total', 0):>7d} {s.get('health_score', 0):>7.1f}"
            )
    store.close()


@memory.command(name="consolidation-preview")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_consolidation_preview(scope: str):
    """Preview what consolidation would do without applying changes."""
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    scope = scope or cfg.memory_scope
    from .memory.store import MemoryStore
    from .memory.consolidator import MemoryConsolidator

    store = MemoryStore(cfg.memory_store_path)
    consolidator = MemoryConsolidator(store=store)
    preview = consolidator.dry_run(scope)
    click.echo(f"Consolidation preview for scope '{scope}':")
    click.echo(f"  Stale summaries to supersede: {preview['stale_summaries']}")
    click.echo(f"  Exact duplicates to merge:    {preview['exact_duplicates']}")
    click.echo(f"  Near-duplicates to merge:     {preview['near_duplicates']}")
    click.echo(f"  Memories to decay:             {preview['decay_candidates']}")
    click.echo(f"  Total actions:                 {preview['total_actions']}")
    store.close()


@memory.command(name="suggest-types")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=10, help="Max suggestions.")
def memory_suggest_types(scope: str, limit: int):
    """Suggest type corrections for potentially mistyped memories."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    suggestions = manager.suggest_type_corrections(scope_id=scope or None, limit=limit)
    manager.close()
    if not suggestions:
        click.echo("No type correction suggestions.")
        return
    for s in suggestions:
        click.echo(f"  {s['memory_id'][:12]}... {s['current_type']} -> {s['suggested_type']} ({s['content_preview']})")


@memory.command(name="cross-scope-duplicates")
@click.argument("scope_a")
@click.argument("scope_b")
def memory_cross_scope_duplicates(scope_a: str, scope_b: str):
    """Find near-duplicate memories across two scopes."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    dupes = manager.find_cross_scope_duplicates(scope_a, scope_b)
    manager.close()
    if not dupes:
        click.echo("No cross-scope duplicates found.")
        return
    click.echo(f"Found {len(dupes)} cross-scope duplicate(s):")
    for d in dupes:
        click.echo(f"  [{d['similarity']:.2f}] {d['id_a'][:12]}... <-> {d['id_b'][:12]}...")
        click.echo(f"    A: {d['preview_a']}")
        click.echo(f"    B: {d['preview_b']}")


@memory.command(name="urgency")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=10, help="Max results.")
def memory_urgency(scope: str, limit: int):
    """Show memories that need urgent attention (TTL proximity, unused high-importance, etc.)."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    results = manager.compute_urgency_scores(scope_id=scope or None, limit=limit)
    manager.close()
    if not results:
        click.echo("No urgent memories found.")
        return
    click.echo(f"Most urgent memories ({len(results)}):")
    for r in results:
        click.echo(f"  [{r['urgency']:5.1f}] {r['memory_id'][:12]}... ({r['type']}) {r['content_preview']}")


@memory.command(name="batch-get")
@click.argument("memory_ids", nargs=-1)
def memory_batch_get(memory_ids: tuple):
    """Retrieve multiple memories by their IDs."""
    from .memory.manager import MemoryManager

    if not memory_ids:
        click.echo("No memory IDs provided.")
        return
    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    units = manager.get_memories_by_ids(list(memory_ids))
    manager.close()
    if not units:
        click.echo("No memories found for the given IDs.")
        return
    click.echo(f"Found {len(units)} memories:")
    for u in units:
        click.echo(f"  [{u.memory_type.value}] {u.memory_id[:12]}... imp={u.importance:.2f} {u.content[:60]}")


@memory.command(name="impact")
@click.argument("memory_id")
def memory_impact(memory_id: str):
    """Analyze what depends on a memory and what would be affected by archiving it."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.analyze_memory_impact(memory_id)
    manager.close()
    if "error" in result:
        click.echo(f"Error: {result['error']}")
        return
    click.echo(f"Impact analysis for {memory_id[:16]}...")
    click.echo(f"  Content: {result['content_preview']}")
    click.echo(f"  Direct dependents: {len(result['direct_dependents'])}")
    click.echo(f"  Transitive dependents: {len(result['transitive_dependents'])}")
    click.echo(f"  Elaborations: {len(result['elaborations'])}")
    click.echo(f"  Contradictions: {len(result['contradictions'])}")
    click.echo(f"  Watchers: {len(result['watchers'])}")
    click.echo(f"  Safe to archive: {'Yes' if result['safe_to_archive'] else 'No'}")


@memory.command(name="dependency-cycles")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_dependency_cycles(scope: str):
    """Detect circular dependency chains in memory links."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    cycles = manager.detect_dependency_cycles(scope_id=scope or None)
    manager.close()
    if not cycles:
        click.echo("No dependency cycles detected.")
        return
    click.echo(f"Found {len(cycles)} dependency cycle(s):")
    for i, cycle in enumerate(cycles, 1):
        chain = " -> ".join(cid[:12] + "..." for cid in cycle)
        click.echo(f"  {i}. {chain}")


@memory.command(name="version-tree")
@click.argument("memory_id")
def memory_version_tree(memory_id: str):
    """Show the version tree (supersedes chain) for a memory."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    tree = manager.build_version_tree(memory_id)
    manager.close()
    click.echo(f"Version tree (chain length: {tree['chain_length']}):")
    click.echo(f"  Root: {tree['root_id'][:16]}...")
    click.echo(f"  Current: {tree['current_id'][:16]}...")
    for i, v in enumerate(tree["versions"]):
        marker = " <-- current" if v["memory_id"] == tree["current_id"] else ""
        click.echo(f"  {i+1}. [{v['status']}] {v['memory_id'][:12]}... imp={v['importance']:.2f} {v['content_preview']}{marker}")


@memory.command(name="dashboard")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_dashboard(scope: str, as_json: bool):
    """Comprehensive operational dashboard for a scope."""
    from .memory.manager import MemoryManager
    import json as json_mod

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_scope_dashboard(scope_id=scope or None)
    manager.close()
    if as_json:
        click.echo(json_mod.dumps(result, indent=2))
    else:
        o = result["overview"]
        click.echo(f"Dashboard: {result['scope_id']}")
        click.echo(f"  Active: {o['total_active']}  Health: {o['health_score']}  Topics: {o['topic_groups']}")
        a = result["access"]
        click.echo(f"  Access: hot={a['hot_count']} warm={a['warm_count']} cold={a['cold_count']} avg={a['avg_access']:.1f}")
        c = result["content"]
        click.echo(f"  Content: {c['total_tokens']} tokens, avg {c['avg_tokens']:.0f}/memory")
        g = result["graph"]
        click.echo(f"  Graph: {g['linked_memories']} linked, {g['total_links']} links, {g['connectivity']:.0%} connected")
        q = result["quota"]
        click.echo(f"  Quota: {q['utilization']:.0%} utilized{'  [OK]' if q['within_quota'] else '  [EXCEEDED]'}")
        click.echo(f"  Archival candidates: {result['top_archival_candidates']}  Urgent: {result['urgent_items']}")


@memory.command(name="normalize")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_normalize(scope: str):
    """Normalize content for all memories (strip whitespace, collapse spaces)."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.batch_normalize_content(scope_id=scope or None)
    manager.close()
    click.echo(f"Normalized {result['normalized']} of {result['total']} memories.")


@memory.command(name="priority-queue")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max items.")
def memory_priority_queue(scope: str, limit: int):
    """Show priority-ranked queue of memories needing attention."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    items = manager.get_priority_queue(scope_id=scope or None, limit=limit)
    manager.close()
    if not items:
        click.echo("No memories need attention.")
        return
    click.echo(f"Priority queue ({len(items)} items):")
    for item in items:
        reasons = ", ".join(set(item["reasons"]))
        click.echo(f"  [{item['priority']:5.1f}] {item['memory_id'][:12]}... ({item['type']}) [{reasons}]")


@memory.command(name="quality-gate")
@click.argument("content")
def memory_quality_gate(content: str):
    """Test content against quality gates before ingestion."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.apply_quality_gate(content)
    manager.close()
    status = "PASSED" if result["passed"] else "FAILED"
    click.echo(f"Quality gate: {status}")
    for g in result["gates"]:
        mark = "✓" if g["passed"] else "✗"
        details = "; ".join(g["details"]) if g["details"] else ""
        click.echo(f"  {mark} {g['gate']}: {details}")


@memory.command(name="freshness")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max results.")
def memory_freshness(scope: str, limit: int):
    """Show freshness scores for memories."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    results = manager.compute_freshness_scores(scope_id=scope or None, limit=limit)
    manager.close()
    if not results:
        click.echo("No memories found.")
        return
    click.echo(f"Freshness scores ({len(results)} shown):")
    for r in results:
        click.echo(f"  [{r['freshness']:5.1f}] {r['memory_id'][:12]}... ({r['type']}) imp={r['importance']:.2f} {r['content_preview']}")


@memory.command(name="inventory")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--type", "type_filter", default=None, help="Filter by memory type.")
@click.option("--min-importance", default=0.0, help="Minimum importance filter.")
@click.option("--sort", "sort_by", default="importance", help="Sort by: importance, access, created.")
@click.option("--limit", default=50, help="Max results.")
def memory_inventory(scope: str, type_filter: str, min_importance: float, sort_by: str, limit: int):
    """Browse memory inventory with filters and sorting."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_scope_inventory(
        scope_id=scope or None,
        type_filter=type_filter,
        min_importance=min_importance,
        sort_by=sort_by,
        limit=limit,
    )
    manager.close()
    click.echo(f"Inventory: {result['showing']}/{result['total_after_filter']} (of {result['total_before_filter']} total)")
    for item in result["items"]:
        tags = f" [{', '.join(item['tags'])}]" if item["tags"] else ""
        click.echo(f"  {item['memory_id'][:12]}... ({item['type']}) imp={item['importance']:.2f} acc={item['access_count']}{tags}")
        click.echo(f"    {item['content_preview'][:60]}")


@memory.command(name="maintenance-recommendations")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_maintenance_recommendations(scope: str):
    """Get maintenance recommendations based on scope state."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_maintenance_recommendations(scope_id=scope or None)
    manager.close()
    if not result["recommendations"]:
        click.echo("No maintenance actions recommended — scope is healthy.")
        return
    click.echo(f"Maintenance recommendations ({result['total_recommendations']}):")
    for r in result["recommendations"]:
        click.echo(f"  [{r['priority'].upper():6}] {r['action']}: {r['reason']}")


@memory.command(name="export-training")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--output", "output_path", default="", help="Output file path (JSONL).")
def memory_export_training(scope: str, output_path: str):
    """Export memories in ML training format (JSONL)."""
    from .memory.manager import MemoryManager
    import json as json_mod

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    records = manager.export_for_training(scope_id=scope or None)
    manager.close()
    if not records:
        click.echo("No memories to export.")
        return
    if output_path:
        with open(output_path, "w") as f:
            for r in records:
                f.write(json_mod.dumps(r) + "\n")
        click.echo(f"Exported {len(records)} records to {output_path}")
    else:
        for r in records:
            click.echo(json_mod.dumps(r))


@memory.command(name="auto-summarize")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max memories to summarize.")
def memory_auto_summarize(scope: str, limit: int):
    """Generate summaries for memories that don't have them."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    generated = manager.generate_auto_summaries(scope_id=scope or None, limit=limit)
    manager.close()
    if not generated:
        click.echo("All memories already have summaries.")
        return
    click.echo(f"Generated {len(generated)} summaries:")
    for g in generated:
        click.echo(f"  {g['memory_id'][:12]}... ({g['type']}): {g['summary'][:60]}")


@memory.command(name="recalculate-importance")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_recalculate_importance(scope: str):
    """Recalculate importance for all memories based on current signals."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.recalculate_importance(scope_id=scope or None)
    manager.close()
    click.echo(f"Evaluated {result['total_evaluated']} memories, updated {result['updated']}.")


@memory.command(name="type-balance")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_type_balance(scope: str):
    """Analyze memory type distribution and suggest rebalancing."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.analyze_type_balance(scope_id=scope or None)
    manager.close()
    click.echo(f"Type balance ({result['total']} memories):")
    for t, info in result["distribution"].items():
        bar = "#" * info["count"]
        click.echo(f"  {t:>25}: {info['count']:3d} ({info['ratio']:.0%}) {bar}")
    if result["suggestions"]:
        click.echo("Suggestions:")
        for s in result["suggestions"]:
            click.echo(f"  [{s['action']}] {s['reason']}")


@memory.command(name="health-comparison")
@click.argument("scope_a")
@click.argument("scope_b")
def memory_health_comparison(scope_a: str, scope_b: str):
    """Compare health scores between two scopes."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.compare_scope_health(scope_a, scope_b)
    manager.close()
    a = result["scope_a"]
    b = result["scope_b"]
    click.echo(f"Health comparison:")
    click.echo(f"  {a['name']}: health={a['health']} active={a['active']}")
    click.echo(f"  {b['name']}: health={b['health']} active={b['active']}")
    click.echo(f"  Healthier: {result['healthier_scope']} (delta={result['health_delta']})")


@memory.command(name="lifecycle")
@click.argument("memory_id")
def memory_lifecycle(memory_id: str):
    """Show the full lifecycle of a memory."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_memory_lifecycle(memory_id)
    manager.close()
    if "error" in result:
        click.echo(f"Error: {result['error']}")
        return
    s = result["current_state"]
    click.echo(f"Lifecycle for {memory_id[:16]}...")
    click.echo(f"  Status: {s['status']}  Type: {s['type']}  Importance: {s['importance']:.2f}")
    click.echo(f"  Created: {s['created_at']}  Updated: {s['updated_at']}")
    click.echo(f"  Access: {s['access_count']}  Tags: {s['tag_count']}  Topics: {s['topic_count']}")
    r = result["relationships"]
    click.echo(f"  Links: {r['link_count']}  Annotations: {r['annotation_count']}  Watchers: {r['watcher_count']}")
    click.echo(f"  Events: {result['event_count']}")


@memory.command(name="suggest-links")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--threshold", default=0.5, help="Minimum feature overlap.")
@click.option("--limit", default=20, help="Max suggestions.")
def memory_suggest_links(scope: str, threshold: float, limit: int):
    """Suggest links between memories with overlapping topics/entities."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    suggestions = manager.suggest_links(scope_id=scope or None, threshold=threshold, limit=limit)
    manager.close()
    if not suggestions:
        click.echo("No link suggestions found.")
        return
    click.echo(f"Link suggestions ({len(suggestions)}):")
    for s in suggestions:
        shared = ", ".join(s["shared_features"][:3])
        click.echo(f"  {s['memory_a'][:12]}... <-> {s['memory_b'][:12]}... ({s['similarity']:.0%}) [{shared}]")


@memory.command(name="scope-comparison")
@click.argument("scope_a")
@click.argument("scope_b")
def memory_scope_comparison(scope_a: str, scope_b: str):
    """Generate a detailed comparison report between two scopes."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.generate_detailed_scope_comparison(scope_a, scope_b)
    manager.close()
    a = result["scope_a"]
    b = result["scope_b"]
    click.echo(f"Scope comparison: {a['name']} vs {b['name']}")
    click.echo(f"  {a['name']}: {a['count']} memories, {a['topic_count']} topics, avg imp={a['avg_importance']:.2f}")
    click.echo(f"  {b['name']}: {b['count']} memories, {b['topic_count']} topics, avg imp={b['avg_importance']:.2f}")
    click.echo(f"  Topic overlap: {result['topic_overlap']:.0%}")
    if result["shared_topics"]:
        click.echo(f"  Shared topics: {', '.join(result['shared_topics'][:10])}")


@memory.command(name="expiry-forecast")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_expiry_forecast(scope: str):
    """Forecast upcoming memory expirations."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.forecast_expiry(scope_id=scope or None)
    manager.close()
    click.echo(f"Expiry forecast ({result['total']} memories, {result['with_ttl']} with TTL):")
    for window, count in result["forecast"].items():
        click.echo(f"  {window}: {count}")


@memory.command(name="type-overlap")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_type_overlap(scope: str):
    """Show topic overlap between memory types."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_type_overlap_matrix(scope_id=scope or None)
    manager.close()
    types = result["types"]
    if not types:
        click.echo("No memory types to analyze.")
        return
    click.echo("Type topic overlap matrix:")
    header = "            " + "  ".join(f"{t[:8]:>8}" for t in types)
    click.echo(header)
    for ta in types:
        row = f"{ta[:10]:>10}  " + "  ".join(f"{result['matrix'][ta][tb]:8.2f}" for tb in types)
        click.echo(row)


@memory.command(name="archive-recommendations")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max recommendations.")
def memory_archive_recommendations(scope: str, limit: int):
    """Recommend memories for archival based on multiple signals."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    recs = manager.recommend_archival(scope_id=scope or None, limit=limit)
    manager.close()
    if not recs:
        click.echo("No archival recommendations.")
        return
    click.echo(f"Archival recommendations ({len(recs)}):")
    for r in recs:
        reasons = ", ".join(r["reasons"])
        click.echo(f"  [{r['archival_score']:5.1f}] {r['memory_id'][:12]}... ({r['type']}) [{reasons}]")
        click.echo(f"    {r['content_preview'][:60]}")


@memory.command(name="content-density")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_content_density(scope: str):
    """Show content density statistics (token counts, value per token)."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_content_density_stats(scope_id=scope or None)
    manager.close()
    click.echo(f"Content density ({result['total']} memories, {result.get('total_tokens', 0)} total tokens):")
    click.echo(f"  Avg tokens: {result['avg_tokens']}")
    click.echo(f"  Min/Max: {result.get('min_tokens', 0)} / {result.get('max_tokens', 0)}")
    click.echo(f"  Avg value/token: {result['avg_value_per_token']:.4f}")
    for label, count in result.get("size_buckets", {}).items():
        click.echo(f"  {label}: {count}")


@memory.command(name="quota")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--max", "max_memories", default=1000, help="Max memories quota.")
def memory_quota(scope: str, max_memories: int):
    """Check scope memory quota utilization."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.check_scope_quota(scope_id=scope or None, max_memories=max_memories)
    manager.close()
    status = "WITHIN" if result["within_quota"] else "EXCEEDED"
    warning = " [WARNING: >90%]" if result["warning"] else ""
    click.echo(f"Quota: {result['current_count']}/{result['max_memories']} ({result['utilization']:.1%}) - {status}{warning}")
    click.echo(f"  Remaining: {result['remaining']}")


@memory.command(name="cascade-archive")
@click.argument("memory_id")
def memory_cascade_archive(memory_id: str):
    """Archive a memory and all its transitive dependents."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.cascade_archive(memory_id)
    manager.close()
    if "error" in result:
        click.echo(f"Error: {result['error']}")
        return
    click.echo(f"Cascade archive: {result['archived']} memories archived ({result['dependents_archived']} dependents).")


@memory.command(name="link-stats")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_link_stats(scope: str):
    """Show statistics about the memory link graph."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_link_graph_stats(scope_id=scope or None)
    manager.close()
    click.echo(f"Link graph stats ({result['total_memories']} memories):")
    click.echo(f"  Linked: {result['linked_memories']}  Unlinked: {result['unlinked_memories']}")
    click.echo(f"  Total links: {result['total_links']}")
    click.echo(f"  Connectivity: {result['connectivity_ratio']:.1%}")
    if result["most_connected"]:
        click.echo(f"  Most connected: {result['most_connected'][:16]}... ({result['max_connections']} connections)")
    if result["link_types"]:
        click.echo("  Link types:")
        for lt, count in result["link_types"].items():
            click.echo(f"    {lt}: {count}")


@memory.command(name="diff")
@click.argument("memory_id_a")
@click.argument("memory_id_b")
def memory_diff(memory_id_a: str, memory_id_b: str):
    """Compare two memories side by side."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.diff_memories(memory_id_a, memory_id_b)
    manager.close()
    if "error" in result:
        click.echo(f"Error: {result['error']}")
        return
    click.echo(f"Memory A ({result['memory_a']['type']}): {result['memory_a']['content'][:80]}")
    click.echo(f"Memory B ({result['memory_b']['type']}): {result['memory_b']['content'][:80]}")
    click.echo(f"Similarity: {result['content_diff']['similarity']:.1%}")
    click.echo(f"Type match: {result['type_match']}")
    click.echo(f"Importance delta: {result['importance_delta']:+.4f}")


@memory.command(name="clone-scope")
@click.argument("source_scope")
@click.argument("target_scope")
def memory_clone_scope(source_scope: str, target_scope: str):
    """Deep-clone a scope with fresh memory IDs."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.clone_scope(source_scope, target_scope)
    manager.close()
    click.echo(f"Cloned {result['cloned']} memories from '{source_scope}' to '{target_scope}'.")


@memory.command(name="access-frequency")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_access_frequency(scope: str):
    """Show hot/warm/cold memory access frequency analysis."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.analyze_access_frequency(scope_id=scope or None)
    manager.close()
    click.echo(f"Access frequency ({result['total']} memories, avg={result['avg_access']:.1f}):")
    click.echo(f"  Hot: {result['hot_count']}  Warm: {result['warm_count']}  Cold: {result['cold_count']}")
    if result["hot"]:
        click.echo("  Top hot memories:")
        for m in result["hot"][:5]:
            click.echo(f"    {m['memory_id'][:12]}... access={m['access_count']} {m['content_preview']}")


@memory.command(name="enrichments")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max suggestions.")
def memory_enrichments(scope: str, limit: int):
    """Show memories that need metadata enrichment."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    suggestions = manager.suggest_enrichments(scope_id=scope or None, limit=limit)
    manager.close()
    if not suggestions:
        click.echo("All memories are well-enriched.")
        return
    click.echo(f"Enrichment suggestions ({len(suggestions)} memories):")
    for s in suggestions:
        missing = ", ".join(s["missing_fields"])
        click.echo(f"  {s['memory_id'][:12]}... ({s['type']}) imp={s['importance']:.2f} completeness={s['completeness']:.0%}")
        click.echo(f"    Missing: {missing}")


@memory.command(name="search-regex")
@click.argument("pattern")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max results.")
def memory_search_regex(pattern: str, scope: str, limit: int):
    """Search memory content using a regular expression."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    results = manager.search_regex(pattern, scope_id=scope or None, limit=limit)
    manager.close()
    if not results:
        click.echo("No matches found.")
        return
    click.echo(f"Regex matches ({len(results)} found):")
    for r in results:
        click.echo(f"  {r['memory_id'][:12]}... ({r['type']}) matched: '{r['matched_text']}'")
        click.echo(f"    {r['content_preview']}")


@memory.command(name="merge-scopes")
@click.argument("source_scope")
@click.argument("target_scope")
def memory_merge_scopes(source_scope: str, target_scope: str):
    """Merge memories from source scope into target scope (preserves source)."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.merge_scopes(source_scope, target_scope)
    manager.close()
    click.echo(f"Merged '{source_scope}' into '{target_scope}': {result['copied']} copied, {result['skipped']} skipped.")


@memory.command(name="stats-delta")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_stats_delta(scope: str):
    """Show changes since last stats snapshot."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.compute_stats_delta(scope_id=scope or None)
    manager.close()
    if not result["has_previous"]:
        click.echo("No previous snapshot to compare against.")
        click.echo(f"Current active: {result['current'].get('active', 0)}")
        return
    click.echo("Stats delta (current vs last snapshot):")
    for key, delta in result["deltas"].items():
        sign = "+" if delta >= 0 else ""
        click.echo(f"  {key}: {sign}{delta}")


@memory.command(name="auto-tags")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=20, help="Max suggestions.")
def memory_auto_tags(scope: str, limit: int):
    """Suggest tags for untagged memories based on content analysis."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    suggestions = manager.suggest_auto_tags(scope_id=scope or None, limit=limit)
    manager.close()
    if not suggestions:
        click.echo("No tag suggestions (all memories already tagged or no patterns found).")
        return
    click.echo(f"Tag suggestions ({len(suggestions)} memories):")
    for s in suggestions:
        tags_str = ", ".join(s["suggested_tags"])
        click.echo(f"  {s['memory_id'][:12]}... ({s['type']}) -> [{tags_str}]")
        click.echo(f"    {s['content_preview'][:60]}")


@memory.command(name="link-graph")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_link_graph(scope: str, as_json: bool):
    """Export the memory link graph for visualization."""
    from .memory.manager import MemoryManager
    import json as json_mod

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    graph = manager.export_link_graph(scope_id=scope or None)
    manager.close()
    if as_json:
        click.echo(json_mod.dumps(graph, indent=2))
    else:
        click.echo(f"Link graph: {graph['node_count']} nodes, {graph['edge_count']} edges")
        for edge in graph["edges"][:20]:
            click.echo(f"  {edge['source'][:12]}... --[{edge['type']}]--> {edge['target'][:12]}...")


@memory.command(name="dedup-report")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--threshold", default=0.75, help="Similarity threshold.")
def memory_dedup_report(scope: str, threshold: float):
    """Generate a comprehensive deduplication report."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    report = manager.get_deduplication_report(scope_id=scope or None, threshold=threshold)
    manager.close()
    click.echo(f"Deduplication report (threshold={report['threshold']}):")
    click.echo(f"  Duplicate pairs: {report['total_duplicate_pairs']}")
    click.echo(f"  Duplicate clusters: {report['duplicate_clusters']}")
    click.echo(f"  Affected memories: {report['affected_memories']}")
    if report["clusters"]:
        click.echo("  Top clusters:")
        for c in report["clusters"][:5]:
            click.echo(f"    Cluster ({c['size']} members): {', '.join(m[:12] + '...' for m in c['members'][:3])}")


@memory.command(name="topic-groups")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--min-size", default=2, help="Minimum group size.")
def memory_topic_groups(scope: str, min_size: int):
    """Group memories by their dominant topic."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.group_by_topic(scope_id=scope or None, min_group_size=min_size)
    manager.close()
    click.echo(f"Topic groups ({result['total_groups']} groups, {result['total_grouped']} memories):")
    for topic, members in result["groups"].items():
        click.echo(f"  [{topic}] ({len(members)} memories)")
        for m in members[:3]:
            click.echo(f"    {m['memory_id'][:12]}... ({m['type']}) {m['content_preview'][:50]}")
        if len(members) > 3:
            click.echo(f"    ... and {len(members) - 3} more")


@memory.command(name="stale")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--days", default=30, help="Days of inactivity to consider stale.")
@click.option("--limit", default=20, help="Max results.")
def memory_stale(scope: str, days: int, limit: int):
    """Find memories that haven't been accessed recently."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    results = manager.find_stale_memories(scope_id=scope or None, stale_days=days, limit=limit)
    manager.close()
    if not results:
        click.echo("No stale memories found.")
        return
    click.echo(f"Stale memories ({len(results)} found, >{days} days inactive):")
    for r in results:
        pinned = " [PINNED]" if r["is_pinned"] else ""
        click.echo(f"  {r['memory_id'][:12]}... ({r['type']}) {r['days_inactive']:.0f}d stale={r['staleness_factor']:.1f}x{pinned}")
        click.echo(f"    {r['content_preview'][:60]}")


@memory.command(name="summary-report")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_summary_report(scope: str, as_json: bool):
    """Generate a comprehensive summary report for a scope."""
    from .memory.manager import MemoryManager
    import json as json_mod

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    report = manager.get_memory_summary_report(scope_id=scope or None)
    manager.close()
    if as_json:
        click.echo(json_mod.dumps(report, indent=2))
    else:
        click.echo(f"Memory Summary Report for scope: {report['scope_id']}")
        click.echo(f"  Generated: {report['generated_at']}")
        click.echo(f"  Active: {report['total_active']}  Superseded: {report['total_superseded']}")
        click.echo(f"  Health: {report['health_score']}")
        click.echo(f"  Topic groups: {report['topic_group_count']}")
        if report["top_topics"]:
            click.echo("  Top topics:")
            for t in report["top_topics"]:
                click.echo(f"    {t['topic']}: {t['count']} memories")


@memory.command(name="age-distribution")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_age_distribution(scope: str):
    """Show age distribution of active memories."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_age_distribution(scope_id=scope or None)
    manager.close()
    click.echo(f"Age distribution ({result['total']} memories):")
    for label, count in result["distribution"].items():
        bar = "#" * count
        click.echo(f"  {label:>12}: {count:3d} {bar}")


@memory.command(name="search-context")
@click.argument("query")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=5, help="Max results.")
def memory_search_context(query: str, scope: str, limit: int):
    """Search with highlighted matched terms in context."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    results = manager.search_with_context(query, scope_id=scope or None, limit=limit)
    manager.close()
    if not results:
        click.echo("No results found.")
        return
    for r in results:
        click.echo(f"  [{r['score']:.3f}] {r['memory_id'][:12]}... ({r['type']})")
        click.echo(f"    {r['snippet']}")


@memory.command(name="migrate-scope")
@click.argument("from_scope")
@click.argument("to_scope")
def memory_migrate_scope(from_scope: str, to_scope: str):
    """Migrate all active memories from one scope to another."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.migrate_scope(from_scope, to_scope)
    manager.close()
    click.echo(f"Migrated {result['migrated']} memories from '{from_scope}' to '{to_scope}'.")


@memory.command(name="importance-histogram")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_importance_histogram(scope: str):
    """Show importance distribution as a histogram."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_importance_histogram(scope_id=scope or None)
    manager.close()
    click.echo(f"Importance distribution ({result['total']} memories):")
    for label, count in sorted(result["histogram"].items()):
        bar = "#" * count
        click.echo(f"  {label}: {count:3d} {bar}")


@memory.command(name="maintenance")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_maintenance(scope: str):
    """Run a full maintenance cycle (expire, consolidate, retain, cleanup, gc, compact)."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.run_maintenance(scope_id=scope or None)
    manager.close()
    click.echo(f"Maintenance complete for scope '{result['scope_id']}':")
    click.echo(f"  Expired: {result['expired']}")
    click.echo(f"  Consolidation: {result['consolidation']}")
    click.echo(f"  Retention archived: {result['retention_archived']}")
    click.echo(f"  Orphans removed: {result['orphans_removed']}")
    click.echo(f"  GC removed: {result['gc_removed']}")


@memory.command(name="sample")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--count", default=5, help="Number of memories to sample.")
def memory_sample(scope: str, count: int):
    """Show a random sample of active memories."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    samples = manager.sample_memories(scope_id=scope or None, count=count)
    manager.close()
    if not samples:
        click.echo("No active memories found.")
        return
    for s in samples:
        click.echo(f"  [{s.memory_type.value}] {s.memory_id[:12]}... ({s.importance:.2f}) {s.content[:80]}")


@memory.command(name="api-status")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_api_status(scope: str, as_json: bool):
    """Show comprehensive API-ready status summary."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    status = manager.get_api_status(scope_id=scope or None)
    manager.close()
    if as_json:
        import json
        click.echo(json.dumps(status, indent=2))
    else:
        click.echo(f"Scope: {status['scope_id']}")
        click.echo(f"Schema: v{status['schema_version']}")
        click.echo(f"Active: {status['active_count']}")
        click.echo(f"Health: {status['health']['score']:.1f}/100")
        click.echo(f"DB: {status['db']['size_mb']} MB")
        click.echo(f"Integrity: {'OK' if status['integrity_valid'] else 'ISSUES'}")
        click.echo(f"Features: {status['features']['pinned']} pinned, {status['features']['with_ttl']} TTL, {status['features']['with_tags']} tagged")


@memory.command(name="validate")
def memory_validate():
    """Validate store integrity (orphaned links, dangling references)."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.validate_integrity()
    store.close()
    if result["valid"]:
        click.echo("Store integrity: OK")
    else:
        click.echo("Store integrity: ISSUES FOUND")
        for issue in result["issues"]:
            click.echo(f"  - {issue}")


@memory.command(name="cleanup-orphans")
def memory_cleanup_orphans():
    """Remove orphaned links, watches, and annotations."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.cleanup_orphans()
    store.close()
    click.echo(f"Removed {result['total_removed']} orphan(s): {result['removed_links']} links, {result['removed_watches']} watches, {result['removed_annotations']} annotations.")


@memory.command(name="export-csv")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--output", "output_path", default="", help="Output file path. Defaults to stdout.")
def memory_export_csv(scope: str, output_path: str):
    """Export active memories as CSV."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    csv_text = store.export_csv(scope or cfg.memory_scope)
    store.close()
    if output_path:
        with open(output_path, "w") as f:
            f.write(csv_text)
        click.echo(f"Exported to {output_path}.")
    else:
        click.echo(csv_text)


@memory.command(name="optimize-hints")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_optimize_hints(scope: str):
    """Show optimization suggestions for the memory store."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    hints = manager.get_optimization_hints(scope_id=scope or None)
    manager.close()
    for hint in hints:
        click.echo(f"  - {hint}")


@memory.command(name="db-size")
def memory_db_size():
    """Show memory database size and page statistics."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    info = store.get_db_size()
    store.close()
    click.echo(f"Database size: {info['size_mb']} MB ({info['size_bytes']} bytes)")
    click.echo(f"Pages: {info['page_count']} (size: {info['page_size']} bytes)")
    click.echo(f"Free pages: {info['freelist_pages']} ({info['freelist_ratio']:.1%})")


@memory.command(name="typed-retention")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_typed_retention(scope: str):
    """Apply per-type retention policies (archive old, low-value memories)."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.apply_typed_retention(scope_id=scope or None)
    manager.close()
    click.echo(f"Archived {result['archived']} memories via typed retention policy.")


@memory.command(name="backup")
@click.argument("backup_path")
def memory_backup(backup_path: str):
    """Create a full backup of the memory database."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.backup(backup_path)
    store.close()
    if result:
        click.echo(f"Backup created at {backup_path}.")
    else:
        click.echo("Backup failed.")


@memory.command(name="schema-version")
def memory_schema_version():
    """Show the current memory store schema version."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    version = store.get_schema_version()
    store.close()
    click.echo(f"Schema version: {version}")


@memory.command(name="watch")
@click.argument("memory_id")
@click.argument("watcher")
def memory_watch(memory_id: str, watcher: str):
    """Watch a memory for changes."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.add_watch(memory_id, watcher)
    store.close()
    if result:
        click.echo(f"Watching memory {memory_id} as '{watcher}'.")
    else:
        click.echo("Already watching this memory.")


@memory.command(name="unwatch")
@click.argument("memory_id")
@click.argument("watcher")
def memory_unwatch(memory_id: str, watcher: str):
    """Stop watching a memory."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.remove_watch(memory_id, watcher)
    store.close()
    click.echo("Unwatched." if result else "Not watching this memory.")


@memory.command(name="watchers")
@click.argument("memory_id")
def memory_watchers(memory_id: str):
    """Show watchers for a memory."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    watchers = store.get_watchers(memory_id)
    store.close()
    if not watchers:
        click.echo("No watchers.")
        return
    for w in watchers:
        click.echo(f"  {w}")


@memory.command(name="usage-report")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_usage_report(scope: str):
    """Generate comprehensive usage report for monitoring."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    report = manager.generate_usage_report(scope_id=scope or None)
    manager.close()
    click.echo(f"Scope: {report['scope_id']}")
    click.echo(f"Active memories: {report['total_active']}")
    click.echo(f"Health score: {report['health_score']:.1f}/100")
    click.echo(f"Avg importance: {report['avg_importance']:.2f}")
    click.echo(f"Access coverage: {report['access_coverage']:.0%}")
    click.echo(f"Pinned: {report['pinned_count']}, With TTL: {report['with_ttl']}")
    click.echo(f"Outgoing links: {report['total_outgoing_links']}")
    click.echo("Types:")
    for t, c in sorted(report["type_distribution"].items()):
        click.echo(f"  {t}: {c}")


@memory.command(name="auto-ttl")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_auto_ttl(scope: str):
    """Apply adaptive TTL to memories based on type and access patterns."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.apply_adaptive_ttl(scope_id=scope or None)
    manager.close()
    click.echo(f"Set adaptive TTL on {result['updated']} memories.")


@memory.command(name="clusters")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
def memory_clusters(scope: str):
    """Find connected clusters of memories via links."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    clusters = manager.find_memory_clusters(scope_id=scope or None)
    manager.close()
    if not clusters:
        click.echo("No connected clusters found.")
        return
    click.echo(f"Found {len(clusters)} cluster(s):")
    for i, cluster in enumerate(clusters, 1):
        click.echo(f"  Cluster {i} ({len(cluster)} memories): {', '.join(m[:12] + '...' for m in cluster[:5])}")


@memory.command(name="batch-archive")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--max-quality", type=float, default=None, help="Archive memories with quality score below this.")
@click.option("--type", "mem_type", default=None, help="Only archive this memory type.")
@click.option("--max-importance", type=float, default=None, help="Only archive memories with importance below this.")
@click.option("--min-age-days", type=int, default=None, help="Only archive memories older than this many days.")
def memory_batch_archive(scope: str, max_quality: float, mem_type: str, max_importance: float, min_age_days: int):
    """Archive memories matching criteria (AND logic). Pinned and summaries are excluded."""
    from .memory.manager import MemoryManager
    from .memory.models import MemoryType as MT

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    mt = None
    if mem_type:
        try:
            mt = MT(mem_type)
        except ValueError:
            click.echo(f"Unknown memory type: {mem_type}")
            manager.close()
            return
    result = manager.batch_archive_by_criteria(
        scope_id=scope or None,
        max_quality_score=max_quality,
        memory_type=mt,
        max_importance=max_importance,
        min_age_days=min_age_days,
    )
    manager.close()
    click.echo(f"Archived {result['archived']} memories in scope '{result['scope_id']}'.")


@memory.command(name="quality")
@click.option("--scope", default="", help="Memory scope. Defaults to config scope.")
@click.option("--limit", default=10, help="Number of lowest-quality memories to show.")
def memory_quality(scope: str, limit: int):
    """Show lowest-quality memories for review and cleanup."""
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    results = manager.get_lowest_quality_memories(scope_id=scope or None, limit=limit)
    manager.close()
    if not results:
        click.echo("No active memories found.")
        return
    click.echo(f"Lowest-quality memories (showing {len(results)}):")
    for r in results:
        click.echo(f"  [{r['score']:5.1f}] {r['memory_id'][:12]}... ({r['memory_type']}) {r['content_preview']}")


@memory.command(name="annotate")
@click.argument("memory_id")
@click.argument("content")
@click.option("--author", default="", help="Author of the annotation.")
def memory_annotate(memory_id: str, content: str, author: str):
    """Add an annotation to a memory."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    aid = store.add_annotation(memory_id, content, author)
    store.close()
    click.echo(f"Added annotation #{aid} to memory {memory_id}.")


@memory.command(name="annotations")
@click.argument("memory_id")
def memory_annotations(memory_id: str):
    """Show all annotations for a memory."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    annotations = store.get_annotations(memory_id)
    store.close()
    if not annotations:
        click.echo("No annotations found.")
        return
    for a in annotations:
        author = f" by {a['author']}" if a["author"] else ""
        click.echo(f"  #{a['annotation_id']}{author} ({a['created_at']}): {a['content']}")


@memory.command(name="link")
@click.argument("source_id")
@click.argument("target_id")
@click.option("--type", "link_type", default="related",
              type=click.Choice(["related", "depends_on", "elaborates", "contradicts"]),
              help="Type of relationship.")
def memory_link(source_id: str, target_id: str, link_type: str):
    """Create a link between two memories."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.add_link(source_id, target_id, link_type)
    store.close()
    if result:
        click.echo(f"Linked {source_id} --[{link_type}]--> {target_id}")
    else:
        click.echo("Link already exists.")


@memory.command(name="links")
@click.argument("memory_id")
def memory_links(memory_id: str):
    """Show all links for a memory."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    links = store.get_links(memory_id)
    store.close()
    if not links:
        click.echo("No links found.")
        return
    for lnk in links:
        arrow = "-->" if lnk["direction"] == "outgoing" else "<--"
        other = lnk["target_id"] if lnk["direction"] == "outgoing" else lnk["source_id"]
        click.echo(f"  {arrow} [{lnk['link_type']}] {other}")


@memory.command(name="grant-access")
@click.argument("scope")
@click.argument("principal")
@click.option("--permission", default="read", type=click.Choice(["read", "write", "admin"]),
              help="Permission level.")
def memory_grant_access(scope: str, principal: str, permission: str):
    """Grant a principal access to a memory scope."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    result = store.grant_access(scope, principal, permission)
    store.close()
    if result:
        click.echo(f"Granted {permission} access on scope '{scope}' to '{principal}'.")
    else:
        click.echo(f"Access already exists or invalid permission.")


@memory.command(name="revoke-access")
@click.argument("scope")
@click.argument("principal")
@click.option("--permission", default="", help="Specific permission to revoke. Omit to revoke all.")
def memory_revoke_access(scope: str, principal: str, permission: str):
    """Revoke a principal's access to a memory scope."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    count = store.revoke_access(scope, principal, permission or None)
    store.close()
    click.echo(f"Revoked {count} grant(s).")


@memory.command(name="scope-grants")
@click.argument("scope")
def memory_scope_grants(scope: str):
    """List all access grants for a memory scope."""
    from .memory.store import MemoryStore

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    store = MemoryStore(cfg.memory_store_path)
    grants = store.list_scope_grants(scope)
    store.close()
    if not grants:
        click.echo("No access grants found.")
        return
    for g in grants:
        click.echo(f"  {g['principal']}: {g['permission']} (since {g['created_at']})")


@memory.command(name="replay-report")
@click.option(
    "--records",
    "records_path",
    default="",
    help="Path to records JSONL. Defaults to <record_dir>/conversations.jsonl from config.",
)
@click.option("--scope", default="", help="Override replay default scope.")
@click.option("--json-out", default="", help="Optional path to write a JSON replay report.")
@click.option("--candidate-policy", default="", help="Optional candidate policy JSON path for baseline-vs-candidate replay.")
def memory_replay_report(records_path: str, scope: str, json_out: str, candidate_policy: str):
    """Run a lightweight offline replay report against the current memory system."""
    from .memory.manager import MemoryManager
    from .memory.promotion import MemoryPromotionCriteria, should_promote
    from .memory.replay import (
        MemoryReplayEvaluator,
        load_replay_samples,
        run_policy_candidate_replay,
        write_replay_report,
    )

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not records_path:
        from pathlib import Path

        records_path = str(Path(cfg.record_dir) / "conversations.jsonl")

    samples = load_replay_samples(records_path, default_scope=scope or cfg.memory_scope)
    if not samples:
        click.echo(f"No replay samples found at {records_path}")
        return

    if candidate_policy:
        baseline, candidate, comparison = run_policy_candidate_replay(
            cfg=cfg,
            samples=samples,
            candidate_policy_path=candidate_policy,
        )
    else:
        manager = MemoryManager.from_config(cfg)
        try:
            evaluator = MemoryReplayEvaluator()
            baseline = evaluator.evaluate(manager, samples)
            candidate = evaluator.evaluate(manager, samples)
            comparison = evaluator.compare(baseline, candidate)
        finally:
            manager.close()

    click.echo(f"samples:                    {candidate.sample_count}")
    click.echo(f"avg retrieved:              {candidate.avg_retrieved:.4f}")
    click.echo(f"avg query overlap:          {candidate.avg_query_overlap:.4f}")
    click.echo(f"avg continuation overlap:   {candidate.avg_continuation_overlap:.4f}")
    click.echo(f"avg response overlap:       {candidate.avg_response_overlap:.4f}")
    click.echo(f"avg specificity:            {candidate.avg_specificity:.4f}")
    click.echo(f"avg focus score:            {candidate.avg_focus_score:.4f}")
    click.echo(f"avg value density:          {candidate.avg_value_density:.4f}")
    click.echo(f"candidate beats baseline:   {comparison['candidate_beats_baseline']}")
    click.echo(
        f"promotion decision:         "
        f"{should_promote(comparison, MemoryPromotionCriteria(min_sample_count=1))}"
    )
    if json_out:
        write_replay_report(json_out, baseline, candidate, comparison)
        click.echo(f"json report:                {json_out}")


@memory.command(name="promote-candidate")
@click.option("--candidate-policy", required=True, help="Candidate policy JSON path.")
@click.option(
    "--records",
    "records_path",
    default="",
    help="Path to records JSONL. Defaults to <record_dir>/conversations.jsonl from config.",
)
@click.option("--report-out", default="", help="Optional replay report output path.")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
@click.option("--require-review", is_flag=True, default=False, help="Queue the candidate for human approval instead of auto-promoting.")
def memory_promote_candidate(candidate_policy: str, records_path: str, report_out: str, history_out: str, require_review: bool):
    """Evaluate a candidate memory policy and promote it if replay criteria pass."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not records_path:
        records_path = str(Path(cfg.record_dir) / "conversations.jsonl")
    if not report_out:
        report_out = str(Path(cfg.memory_dir) / "replay_report.json")
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")

    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    decision = orchestrator.evaluate_candidate(
        candidate_policy_path=candidate_policy,
        replay_records_path=records_path,
        report_path=report_out,
        criteria=None,
        require_review=require_review,
    )
    click.echo(f"promoted:                  {decision.promoted}")
    click.echo(f"reason:                    {decision.reason}")
    click.echo(f"candidate beats baseline:  {decision.comparison.get('candidate_beats_baseline')}")
    click.echo(f"report:                    {decision.report_path}")


@memory.command(name="generate-candidates")
@click.option("--out-dir", default="", help="Directory to write generated candidate policies.")
def memory_generate_candidates(out_dir: str):
    """Generate a bounded set of memory policy candidates from the current live policy."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    orchestrator = MemorySelfUpgradeOrchestrator(
        cfg,
        history_path=str(Path(cfg.memory_dir) / "upgrade_history.jsonl"),
    )
    if not out_dir:
        out_dir = orchestrator.default_candidate_dir()
    paths = orchestrator.generate_candidate_files(out_dir)
    click.echo(f"generated:                 {len(paths)}")
    click.echo(f"output dir:                {out_dir}")


@memory.command(name="evaluate-candidates")
@click.option("--candidate-dir", required=True, help="Directory containing candidate policy JSON files.")
@click.option(
    "--records",
    "records_path",
    default="",
    help="Path to records JSONL. Defaults to <record_dir>/conversations.jsonl from config.",
)
@click.option("--reports-dir", default="", help="Directory to write per-candidate replay reports.")
def memory_evaluate_candidates(candidate_dir: str, records_path: str, reports_dir: str):
    """Evaluate a directory of generated candidates through replay gating."""
    from pathlib import Path

    from .memory.promotion import MemoryPromotionCriteria
    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not records_path:
        records_path = str(Path(cfg.record_dir) / "conversations.jsonl")

    orchestrator = MemorySelfUpgradeOrchestrator(
        cfg,
        history_path=str(Path(cfg.memory_dir) / "upgrade_history.jsonl"),
    )
    if not reports_dir:
        reports_dir = orchestrator.default_reports_dir()
    decisions = orchestrator.evaluate_candidate_directory(
        candidate_dir=candidate_dir,
        replay_records_path=records_path,
        reports_dir=reports_dir,
        criteria=MemoryPromotionCriteria(min_sample_count=1),
    )
    promoted = sum(1 for decision in decisions if decision.promoted)
    click.echo(f"evaluated:                 {len(decisions)}")
    click.echo(f"promoted:                  {promoted}")
    click.echo(f"reports dir:               {reports_dir}")


@memory.command(name="auto-upgrade")
@click.option(
    "--records",
    "records_path",
    default="",
    help="Path to records JSONL. Defaults to <record_dir>/conversations.jsonl from config.",
)
@click.option("--candidate-dir", default="", help="Directory for generated candidate policies.")
@click.option("--reports-dir", default="", help="Directory for replay reports.")
@click.option("--require-review", is_flag=True, default=False, help="Queue replay-passing candidates for review instead of auto-promoting.")
def memory_auto_upgrade(records_path: str, candidate_dir: str, reports_dir: str, require_review: bool):
    """Run the full bounded self-upgrade cycle: generate, replay-evaluate, and promote or queue."""
    from pathlib import Path

    from .memory.promotion import MemoryPromotionCriteria
    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not records_path:
        records_path = str(Path(cfg.record_dir) / "conversations.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(
        cfg,
        history_path=str(Path(cfg.memory_dir) / "upgrade_history.jsonl"),
    )
    decisions = orchestrator.run_auto_upgrade_cycle(
        replay_records_path=records_path,
        candidate_dir=candidate_dir,
        reports_dir=reports_dir,
        criteria=MemoryPromotionCriteria(min_sample_count=1),
        require_review=require_review,
    )
    promoted = sum(1 for decision in decisions if decision.promoted)
    pending = sum(1 for decision in decisions if decision.reason == "pending_review")
    click.echo(f"candidates processed:      {len(decisions)}")
    click.echo(f"promoted:                  {promoted}")
    click.echo(f"pending review:            {pending}")


@memory.command(name="review-queue")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
def memory_review_queue(history_out: str):
    """Show candidates waiting for human review."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    queue = orchestrator.read_review_queue()
    summary = orchestrator.summarize_review_queue(
        stale_after_hours=cfg.memory_review_stale_after_hours
    )
    review_history = orchestrator.summarize_review_history()
    health = orchestrator.summarize_operational_health(
        stale_after_hours=cfg.memory_review_stale_after_hours
    )
    click.echo(f"pending review:            {len(queue)}")
    click.echo(f"stale review:              {summary['stale_count']}")
    click.echo(f"stale threshold hours:     {summary['stale_after_hours']}")
    click.echo(f"oldest review age hours:   {summary['oldest_age_hours']}")
    click.echo(f"health level:              {health['level']}")
    click.echo(f"health reasons:            {', '.join(health['reasons']) or '-'}")
    click.echo(f"review queued total:       {review_history['queued']}")
    click.echo(f"review approved total:     {review_history['approved']}")
    click.echo(f"review rejected total:     {review_history['rejected']}")
    click.echo(f"review resolved total:     {review_history['resolved_count']}")
    click.echo(f"avg review hours:          {review_history['avg_resolution_hours']}")
    click.echo(f"max review hours:          {review_history['max_resolution_hours']}")
    click.echo(f"pending estimate:          {review_history['pending_estimate']}")
    click.echo(f"backlog pressure hours:    {review_history['backlog_pressure_hours']}")
    click.echo(f"approval rate:             {review_history['approval_rate']}")
    click.echo(f"rejection rate:            {review_history['rejection_rate']}")
    click.echo(f"recent window hours:       {review_history['recent_window_hours']}")
    click.echo(f"recent review events:      {review_history['recent_total']}")
    click.echo(f"recent queued:             {review_history['recent_queued']}")
    click.echo(f"recent approved:           {review_history['recent_approved']}")
    click.echo(f"recent rejected:           {review_history['recent_rejected']}")
    click.echo(f"recent resolved:           {review_history['recent_resolved_count']}")
    click.echo(f"recent avg hours:          {review_history['recent_avg_resolution_hours']}")
    click.echo(f"recent approval rate:      {review_history['recent_approval_rate']}")
    click.echo(f"recent rejection rate:     {review_history['recent_rejection_rate']}")
    for item in queue[-10:]:
        click.echo(
            f"- {item.get('candidate_policy_path', '?')}  "
            f"reason={item.get('reason', '?')}  "
            f"queued_at={item.get('timestamp', '?')}"
        )


@memory.command(name="review-history")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
@click.option("--n", default=10, show_default=True, type=int, help="Number of recent review events to show.")
def memory_review_history(history_out: str, n: int):
    """Show the dedicated review-event history for memory upgrade candidates."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    summary = orchestrator.summarize_review_history()
    records = orchestrator.read_review_history(limit=n)
    click.echo(f"review events total:       {summary['total']}")
    click.echo(f"queued:                    {summary['queued']}")
    click.echo(f"approved:                  {summary['approved']}")
    click.echo(f"rejected:                  {summary['rejected']}")
    click.echo(f"resolved:                  {summary['resolved_count']}")
    click.echo(f"avg resolution hours:      {summary['avg_resolution_hours']}")
    click.echo(f"max resolution hours:      {summary['max_resolution_hours']}")
    click.echo(f"pending estimate:          {summary['pending_estimate']}")
    click.echo(f"backlog pressure hours:    {summary['backlog_pressure_hours']}")
    click.echo(f"approval rate:             {summary['approval_rate']}")
    click.echo(f"rejection rate:            {summary['rejection_rate']}")
    click.echo(f"recent window hours:       {summary['recent_window_hours']}")
    click.echo(f"recent review events:      {summary['recent_total']}")
    click.echo(f"recent queued:             {summary['recent_queued']}")
    click.echo(f"recent approved:           {summary['recent_approved']}")
    click.echo(f"recent rejected:           {summary['recent_rejected']}")
    click.echo(f"recent resolved:           {summary['recent_resolved_count']}")
    click.echo(f"recent avg hours:          {summary['recent_avg_resolution_hours']}")
    click.echo(f"recent approval rate:      {summary['recent_approval_rate']}")
    click.echo(f"recent rejection rate:     {summary['recent_rejection_rate']}")
    for item in records:
        click.echo(
            f"- {item.get('timestamp', '?')}  "
            f"event={item.get('event', '?')}  "
            f"candidate={item.get('candidate_policy_path', '?')}"
        )


@memory.command(name="alerts")
@click.option("--n", default=10, show_default=True, type=int, help="Number of recent alert snapshots to show.")
def memory_alerts(n: int):
    """Show current and recent memory upgrade alerts."""
    from pathlib import Path

    from .memory.upgrade_worker import MemoryUpgradeWorker

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    current_path = Path(cfg.memory_dir).expanduser() / "upgrade_alerts.json"
    worker = MemoryUpgradeWorker(cfg)

    if current_path.exists():
        try:
            import json

            current = json.loads(current_path.read_text(encoding="utf-8"))
            alerts = current.get("alerts", [])
            click.echo(f"current alerts:            {len(alerts)}")
            click.echo(f"current updated_at:        {current.get('updated_at', '?')}")
            for item in alerts:
                click.echo(
                    f"- code={item.get('code', '?')} level={item.get('level', '?')} "
                    f"pending={item.get('pending_count', '?')} stale={item.get('stale_count', '?')}"
                )
        except Exception as exc:
            click.echo(f"Current alerts unreadable: {exc}", err=True)
            raise SystemExit(1)
    else:
        click.echo("current alerts:            0")

    summary = worker.summarize_alert_history()
    records = worker.read_alert_history(limit=n)
    click.echo(f"alert history entries:     {len(records)}")
    click.echo(f"alert history total:       {summary['total_snapshots']}")
    click.echo(f"nonempty snapshots:        {summary['nonempty_snapshots']}")
    click.echo(f"warning alerts:            {summary['warning_count']}")
    click.echo(f"critical alerts:           {summary['critical_count']}")
    click.echo(f"blocked alerts:            {summary['blocked_count']}")
    click.echo(f"stale alerts:              {summary['stale_count']}")
    click.echo(f"nonempty rate:             {summary['nonempty_snapshot_rate']}")
    click.echo(f"blocked rate:              {summary['blocked_snapshot_rate']}")
    click.echo(f"stale rate:                {summary['stale_snapshot_rate']}")
    click.echo(f"recent window hours:       {summary['recent_window_hours']}")
    click.echo(f"recent snapshots:          {summary['recent_total_snapshots']}")
    click.echo(f"recent nonempty:           {summary['recent_nonempty_snapshots']}")
    click.echo(f"recent warnings:           {summary['recent_warning_count']}")
    click.echo(f"recent critical:           {summary['recent_critical_count']}")
    click.echo(f"recent blocked:            {summary['recent_blocked_count']}")
    click.echo(f"recent stale:              {summary['recent_stale_count']}")
    click.echo(f"recent nonempty rate:      {summary['recent_nonempty_snapshot_rate']}")
    click.echo(f"recent blocked rate:       {summary['recent_blocked_snapshot_rate']}")
    click.echo(f"recent stale rate:         {summary['recent_stale_snapshot_rate']}")
    for item in records[-n:]:
        alerts = item.get("alerts", [])
        first = alerts[0] if alerts else {}
        click.echo(
            f"- {item.get('updated_at', '?')}  alerts={len(alerts)}  "
            f"code={first.get('code', '-')}"
        )


@memory.command(name="health-history")
@click.option("--n", default=10, show_default=True, type=int, help="Number of recent health snapshots to show.")
def memory_health_history(n: int):
    """Show recent operational-health snapshots for the memory upgrade loop."""
    from .memory.upgrade_worker import MemoryUpgradeWorker

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    worker = MemoryUpgradeWorker(cfg)
    summary = worker.summarize_health_history()
    records = worker.read_health_history(limit=n)
    click.echo(f"health snapshots total:    {summary['total_snapshots']}")
    click.echo(f"healthy count:             {summary['healthy_count']}")
    click.echo(f"warning count:             {summary['warning_count']}")
    click.echo(f"critical count:            {summary['critical_count']}")
    click.echo(f"healthy rate:              {summary['healthy_rate']}")
    click.echo(f"warning rate:              {summary['warning_rate']}")
    click.echo(f"critical rate:             {summary['critical_rate']}")
    click.echo(f"recent window hours:       {summary['recent_window_hours']}")
    click.echo(f"recent snapshots:          {summary['recent_snapshots']}")
    click.echo(f"recent healthy rate:       {summary['recent_healthy_rate']}")
    click.echo(f"recent warning rate:       {summary['recent_warning_rate']}")
    click.echo(f"recent critical rate:      {summary['recent_critical_rate']}")
    for item in records:
        click.echo(
            f"- {item.get('updated_at', '?')}  "
            f"state={item.get('state', '?')}  "
            f"level={item.get('level', '?')}  "
            f"reasons={','.join(item.get('reasons', [])) or '-'}"
        )


@memory.command(name="upgrade-history")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
@click.option("--n", default=10, show_default=True, type=int, help="Number of recent decisions to show.")
def memory_upgrade_history(history_out: str, n: int):
    """Show recent self-upgrade decisions."""
    import json
    from pathlib import Path

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    summary = orchestrator.summarize_history()
    records = orchestrator.read_history(limit=n)
    if not records:
        click.echo("No upgrade history found.")
        return
    click.echo(f"history total:             {summary['total']}")
    click.echo(f"promoted:                  {summary['promoted']}")
    click.echo(f"pending review:            {summary['pending_review']}")
    click.echo(f"rejected:                  {summary['rejected']}")
    click.echo(f"approved review:           {summary['approved_review']}")
    click.echo(f"rejected review:           {summary['rejected_review']}")
    click.echo(f"recent window hours:       {summary['recent_window_hours']}")
    click.echo(f"recent total:              {summary['recent_total']}")
    click.echo(f"recent promoted:           {summary['recent_promoted']}")
    click.echo(f"recent pending review:     {summary['recent_pending_review']}")
    click.echo(f"recent rejected:           {summary['recent_rejected']}")
    click.echo(f"recent approved review:    {summary['recent_approved_review']}")
    click.echo(f"recent rejected review:    {summary['recent_rejected_review']}")
    click.echo(f"history entries shown:     {len(records)}")
    for item in records:
        click.echo(
            f"- {item.get('timestamp', '?')}  "
            f"reason={item.get('reason', '?')}  "
            f"promoted={item.get('promoted', False)}"
        )


@memory.command(name="candidates-status")
@click.option("--candidate-dir", default="", help="Directory containing candidate policy files.")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
def memory_candidates_status(candidate_dir: str, history_out: str):
    """Show candidate directory summary."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    if not candidate_dir:
        candidate_dir = orchestrator.default_candidate_dir()
    summary = orchestrator.summarize_candidate_directory(candidate_dir)
    click.echo(f"candidate count:           {summary['count']}")
    click.echo(f"candidate dir:             {candidate_dir}")
    for candidate_path in summary["candidate_files"]:
        click.echo(f"- {candidate_path}")

    cycle_summary = orchestrator.read_cycle_summary()
    if cycle_summary:
        click.echo(f"last cycle candidates:     {cycle_summary.get('num_candidates', 0)}")
        click.echo(f"last cycle promoted:       {cycle_summary.get('num_promoted', 0)}")
        click.echo(f"last cycle pending review: {cycle_summary.get('num_pending_review', 0)}")
        metric_summary = cycle_summary.get("metric_summary", {})
        if metric_summary:
            click.echo(f"best candidate score:      {metric_summary.get('best_score', 0.0)}")
            click.echo(f"best candidate reason:     {metric_summary.get('best_reason', '-')}")
            click.echo(f"avg query delta:           {metric_summary.get('avg_query_overlap_delta_avg', 0.0)}")
            click.echo(f"avg focus delta:           {metric_summary.get('avg_focus_score_delta_avg', 0.0)}")
            click.echo(f"avg density delta:         {metric_summary.get('avg_value_density_delta_avg', 0.0)}")
        cleanup = cycle_summary.get("cleanup", {})
        if cleanup:
            click.echo(f"last cleanup candidates:   {cleanup.get('removed_candidates', 0)}")
            click.echo(f"last cleanup reports:      {cleanup.get('removed_reports', 0)}")
    cycle_history = orchestrator.summarize_cycle_history()
    click.echo(f"cycle history total:       {cycle_history['total_cycles']}")
    click.echo(f"cycle history promoted:    {cycle_history['promoted_cycles']}")
    click.echo(f"cycle history pending:     {cycle_history['pending_review_cycles']}")
    click.echo(f"avg cycle candidates:      {cycle_history['avg_candidates']}")
    click.echo(f"avg best score:            {cycle_history['avg_best_score']}")
    click.echo(f"promoted cycle rate:       {cycle_history['promoted_cycle_rate']}")
    click.echo(f"pending cycle rate:        {cycle_history['pending_review_cycle_rate']}")
    click.echo(f"recent cycle window hrs:   {cycle_history['recent_window_hours']}")
    click.echo(f"recent cycles:             {cycle_history['recent_cycles']}")
    click.echo(f"recent promoted cycles:    {cycle_history['recent_promoted_cycles']}")
    click.echo(f"recent pending cycles:     {cycle_history['recent_pending_review_cycles']}")
    click.echo(f"recent avg candidates:     {cycle_history['recent_avg_candidates']}")
    click.echo(f"recent avg best score:     {cycle_history['recent_avg_best_score']}")
    click.echo(f"recent promoted rate:      {cycle_history['recent_promoted_cycle_rate']}")
    click.echo(f"recent pending rate:       {cycle_history['recent_pending_review_cycle_rate']}")


@memory.command(name="cycle-history")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
@click.option("--n", default=10, show_default=True, type=int, help="Number of recent cycle records to show.")
def memory_cycle_history(history_out: str, n: int):
    """Show aggregate and recent cycle-history summaries for self-upgrade runs."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    summary = orchestrator.summarize_cycle_history()
    records = orchestrator.read_cycle_history(limit=n)
    click.echo(f"cycle history total:       {summary['total_cycles']}")
    click.echo(f"promoted cycles:           {summary['promoted_cycles']}")
    click.echo(f"pending review cycles:     {summary['pending_review_cycles']}")
    click.echo(f"avg candidates:            {summary['avg_candidates']}")
    click.echo(f"avg best score:            {summary['avg_best_score']}")
    click.echo(f"promoted cycle rate:       {summary['promoted_cycle_rate']}")
    click.echo(f"pending cycle rate:        {summary['pending_review_cycle_rate']}")
    click.echo(f"recent window hours:       {summary['recent_window_hours']}")
    click.echo(f"recent cycles:             {summary['recent_cycles']}")
    click.echo(f"recent promoted cycles:    {summary['recent_promoted_cycles']}")
    click.echo(f"recent pending cycles:     {summary['recent_pending_review_cycles']}")
    click.echo(f"recent avg candidates:     {summary['recent_avg_candidates']}")
    click.echo(f"recent avg best score:     {summary['recent_avg_best_score']}")
    click.echo(f"recent promoted rate:      {summary['recent_promoted_cycle_rate']}")
    click.echo(f"recent pending rate:       {summary['recent_pending_review_cycle_rate']}")
    click.echo(f"cycle records shown:       {len(records)}")
    for item in records:
        click.echo(
            f"- {item.get('updated_at', '?')}  "
            f"candidates={item.get('num_candidates', 0)}  "
            f"promoted={item.get('num_promoted', 0)}  "
            f"pending={item.get('num_pending_review', 0)}"
        )


@memory.command(name="cleanup-artifacts")
@click.option("--candidate-dir", default="", help="Directory containing candidate policy files.")
@click.option("--reports-dir", default="", help="Directory containing replay reports.")
@click.option("--keep-candidates", default=24, show_default=True, type=int, help="How many candidate files to keep.")
@click.option("--keep-reports", default=48, show_default=True, type=int, help="How many report files to keep.")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
def memory_cleanup_artifacts(candidate_dir: str, reports_dir: str, keep_candidates: int, keep_reports: int, history_out: str):
    """Prune stale candidate and report artifacts while preserving active review items."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    result = orchestrator.cleanup_artifacts(
        candidate_dir=candidate_dir,
        reports_dir=reports_dir,
        keep_candidates=keep_candidates,
        keep_reports=keep_reports,
    )
    click.echo(f"removed candidates:        {result['removed_candidates']}")
    click.echo(f"removed reports:           {result['removed_reports']}")
    click.echo(f"kept candidates target:    {result['kept_candidates']}")
    click.echo(f"kept reports target:       {result['kept_reports']}")


@memory.command(name="approve-candidate")
@click.option("--candidate-policy", required=True, help="Candidate policy JSON path to approve.")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
def memory_approve_candidate(candidate_policy: str, history_out: str):
    """Approve a queued candidate and promote it to the live policy."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    approved = orchestrator.approve_review_candidate(candidate_policy)
    if not approved:
        click.echo("Candidate not found in review queue.", err=True)
        raise SystemExit(1)
    click.echo("Candidate approved and promoted.")


@memory.command(name="reject-candidate")
@click.option("--candidate-policy", required=True, help="Candidate policy JSON path to reject.")
@click.option("--history-out", default="", help="Optional promotion history JSONL path.")
def memory_reject_candidate(candidate_policy: str, history_out: str):
    """Reject a queued candidate and remove it from the review queue."""
    from pathlib import Path

    from .memory.self_upgrade import MemorySelfUpgradeOrchestrator

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    if not history_out:
        history_out = str(Path(cfg.memory_dir) / "upgrade_history.jsonl")
    orchestrator = MemorySelfUpgradeOrchestrator(cfg, history_path=history_out)
    rejected = orchestrator.reject_review_candidate(candidate_policy)
    if not rejected:
        click.echo("Candidate not found in review queue.", err=True)
        raise SystemExit(1)
    click.echo("Candidate rejected.")


@memory.command(name="bookmark")
@click.argument("memory_ids", nargs=-1, required=True)
def memory_bookmark(memory_ids: tuple):
    """Bookmark memories for quick access."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.bookmark_memories(list(memory_ids))
    click.echo(f"Bookmarked {result['tagged']} of {result['total']} memories")
    manager.close()


@memory.command(name="bookmarks")
@click.option("--scope", default=None, help="Scope to list bookmarks from.")
def memory_bookmarks(scope: str | None):
    """List all bookmarked memories."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    bookmarks = manager.get_bookmarks(scope_id=scope)
    if not bookmarks:
        click.echo("No bookmarked memories.")
    else:
        for bm in bookmarks:
            click.echo(f"  {bm['memory_id']} [{bm['type']}] {bm['content']}")
    manager.close()


@memory.command(name="snapshot-compare")
@click.option("--scope", default=None, help="Scope to compare.")
def memory_snapshot_compare(scope: str | None):
    """Compare current stats with most recent snapshot."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.compare_snapshots(scope_id=scope)
    if result.get("delta") is None:
        click.echo(result.get("message", "No comparison available"))
    else:
        click.echo(f"Scope: {result['scope_id']}")
        for key, val in result["delta"].items():
            sign = "+" if val > 0 else ""
            click.echo(f"  {key}: {sign}{val}")
    manager.close()


@memory.command(name="feedback-analysis")
@click.option("--scope", default=None, help="Scope to analyze.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_feedback_analysis(scope: str | None, as_json: bool):
    """Analyze retrieval feedback patterns."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.analyze_feedback_patterns(scope_id=scope)
    manager.close()
    if as_json:
        import json
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Feedback Analysis — Scope: {result['scope_id']}")
        click.echo(f"  Total feedback: {result['total_feedback']}")
        click.echo(f"  Positive: {result['positive']} ({result['positive_rate']:.0%})")
        click.echo(f"  Negative: {result['negative']}")
        click.echo(f"  Unique memories: {result['unique_memories_with_feedback']}")
        if result["most_boosted"]:
            click.echo("  Most boosted:")
            for m in result["most_boosted"][:3]:
                click.echo(f"    {m['memory_id'][:16]}: +{m['positive']} -{m['negative']}")
        if result["most_penalized"]:
            click.echo("  Most penalized:")
            for m in result["most_penalized"][:3]:
                click.echo(f"    {m['memory_id'][:16]}: +{m['positive']} -{m['negative']}")


@memory.command(name="operator-report")
@click.option("--scope", default=None, help="Scope to report on.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_operator_report(scope: str | None, as_json: bool):
    """Generate comprehensive operator diagnostic report."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    report = manager.generate_operator_report(scope_id=scope)
    manager.close()
    if as_json:
        import json
        click.echo(json.dumps(report, indent=2, default=str))
    else:
        click.echo(f"Operator Report — Scope: {report['scope_id']}")
        click.echo(f"Generated: {report.get('generated_at', '?')}")
        click.echo()
        # Health
        health = report.get("health", {})
        if "error" not in health:
            status = "PASS" if health.get("passed") else "FAIL"
            click.echo(f"Health: {status}")
            for name, check in health.get("checks", {}).items():
                c_status = "OK" if check.get("passed") else "ISSUE"
                click.echo(f"  {name}: {c_status}")
        else:
            click.echo(f"Health: ERROR — {health['error']}")
        click.echo()
        # Stats
        stats = report.get("stats", {})
        if "error" not in stats:
            click.echo(f"Active: {stats.get('active', '?')}")
            click.echo(f"Total: {stats.get('total', '?')}")
        click.echo()
        # Action plan
        plan = report.get("action_plan", {})
        if "error" not in plan:
            actions = plan.get("actions", [])
            click.echo(f"Action Plan: {len(actions)} recommendations")
            for a in actions[:5]:
                click.echo(f"  [{a.get('priority', '?')}] {a.get('action', '?')}: {a.get('description', '')[:80]}")
        click.echo()
        # Growth
        growth = report.get("growth_rate", {})
        if "error" not in growth:
            rate = growth.get("daily_rate", 0)
            click.echo(f"Growth rate: {rate:.1f}/day")
        # Capacity
        cap = report.get("capacity", {})
        if "error" not in cap:
            days = cap.get("days_until_quota", "N/A")
            click.echo(f"Days until quota: {days}")


@memory.command(name="archive-scope")
@click.argument("scope")
def memory_archive_scope(scope: str):
    """Archive all active memories in a scope (keeps pinned)."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.archive_scope(scope)
    click.echo(f"Archived {result['archived']} of {result['total_before']} memories in scope '{scope}'")
    if result["pinned_kept"]:
        click.echo(f"  {result['pinned_kept']} pinned memories kept active")
    manager.close()


@memory.command(name="bulk-pin")
@click.option("--scope", default=None, help="Scope to pin in.")
@click.option("--min-importance", default=0.9, type=float, help="Min importance threshold.")
@click.option("--min-access", default=10, type=int, help="Min access count threshold.")
def memory_bulk_pin(scope: str | None, min_importance: float, min_access: int):
    """Pin high-value memories (prevents archival/decay)."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.bulk_pin_by_criteria(scope_id=scope, min_importance=min_importance, min_access_count=min_access)
    click.echo(f"Pinned {result['pinned']} of {result['total']} memories")
    manager.close()


@memory.command(name="export-yaml")
@click.option("--scope", default=None, help="Scope to export.")
@click.option("--output", default=None, help="Output file path.")
def memory_export_yaml(scope: str | None, output: str | None):
    """Export scope memories as YAML."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    yaml_str = manager.export_scope_yaml(scope_id=scope)
    if output:
        with open(output, "w") as f:
            f.write(yaml_str)
        click.echo(f"Exported to {output}")
    else:
        click.echo(yaml_str)
    manager.close()


@memory.command(name="search-grouped")
@click.argument("query")
@click.option("--scope", default=None, help="Scope to search.")
@click.option("--group-by", default="type", type=click.Choice(["type", "topic"]), help="Group results by type or topic.")
@click.option("--limit", default=20, type=int, help="Max results.")
def memory_search_grouped(query: str, scope: str | None, group_by: str, limit: int):
    """Search memories with grouped results."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.search_grouped(query, scope_id=scope, group_by=group_by, limit=limit)
    click.echo(f"Query: {result['query']} — {result['total_results']} results grouped by {result['group_by']}\n")
    for group_name, group_data in result["groups"].items():
        click.echo(f"  [{group_name}] ({group_data['count']} results)")
        for r in group_data["results"][:5]:
            click.echo(f"    {r['memory_id']}: {r['content']} (score={r['score']})")
    manager.close()


@memory.command(name="health-check")
@click.option("--scope", default=None, help="Scope to check.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_health_check(scope: str | None, as_json: bool):
    """Run a comprehensive system health check."""
    import json as _json
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.run_system_health_check(scope_id=scope)
    if as_json:
        click.echo(_json.dumps(result, indent=2, default=str))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        click.echo(f"Health Check: {status} — {result['summary']}\n")
        for name, check in result["checks"].items():
            marker = "✓" if check.get("passed") else "✗"
            click.echo(f"  {marker} {name}: {check}")
        if result["issues"]:
            click.echo(f"\nIssues:")
            for issue in result["issues"]:
                click.echo(f"  - {issue}")
    manager.close()


@memory.command(name="action-plan")
@click.option("--scope", default=None, help="Scope to plan for.")
def memory_action_plan(scope: str | None):
    """Generate a prioritized operator action plan for a scope."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    plan = manager.generate_action_plan(scope_id=scope)
    click.echo(f"Scope: {plan['scope_id']} — {plan['total_actions']} recommended actions\n")
    for action in plan["actions"]:
        priority_marker = {"high": "!!!", "medium": "!!", "low": "!"}.get(action["priority"], "")
        click.echo(f"[{action['priority'].upper()}] {priority_marker} {action['action']} ({action['count']} items)")
        click.echo(f"  {action['description']}")
        click.echo(f"  Run: {action['command']}\n")
    if not plan["actions"]:
        click.echo("No actions needed — scope is in good shape!")
    manager.close()


@memory.command(name="auto-dedup")
@click.option("--scope", default=None, help="Scope to deduplicate.")
@click.option("--threshold", default=0.85, type=float, help="Similarity threshold (default: 0.85).")
@click.option("--dry-run", is_flag=True, help="Preview without archiving.")
def memory_auto_dedup(scope: str | None, threshold: float, dry_run: bool):
    """Find and resolve duplicate memories by archiving older copies."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.auto_deduplicate(scope_id=scope, threshold=threshold, dry_run=dry_run)
    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"{prefix}Found {result['duplicates_found']} duplicate pairs, archived {result['archived']}")
    for pair in result["pairs"][:10]:
        click.echo(f"  keep={pair['keep']} remove={pair['remove']} similarity={pair['similarity']:.2f}")
    manager.close()


@memory.command(name="capacity-forecast")
@click.option("--scope", default=None, help="Scope to forecast.")
@click.option("--quota", default=1000, type=int, help="Target quota (default: 1000).")
def memory_capacity_forecast(scope: str | None, quota: int):
    """Project when a scope will reach its capacity quota."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.forecast_capacity(scope_id=scope, quota=quota)
    click.echo(f"Scope: {result['scope_id']}")
    click.echo(f"Current: {result['current']} / {result['quota']} ({result['utilization_pct']}%)")
    click.echo(f"Growth rate: {result['rate_per_day']}/day")
    if result["days_until_full"] is not None:
        click.echo(f"Days until full: {result['days_until_full']}")
    else:
        click.echo("Days until full: N/A (no growth detected)")
    manager.close()


@memory.command(name="audit-trail")
@click.option("--scope", default=None, help="Scope to export.")
@click.option("--limit", default=100, type=int, help="Max events (default: 100).")
def memory_audit_trail(scope: str | None, limit: int):
    """Export memory event audit trail for compliance."""
    import json as _json
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    events = manager.export_audit_trail(scope_id=scope, limit=limit)
    click.echo(_json.dumps(events, indent=2, default=str))
    manager.close()


@memory.command(name="retention-analysis")
@click.option("--scope", default=None, help="Scope to analyze.")
def memory_retention_analysis(scope: str | None):
    """Analyze retention policy effectiveness."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.analyze_retention_effectiveness(scope_id=scope)
    click.echo(f"Scope: {result['scope_id']}")
    click.echo(f"Total: {result['total_memories']} (active={result['active']}, archived={result['archived']}, superseded={result['superseded']})")
    click.echo(f"Archive ratio: {result['archive_ratio']}")
    click.echo(f"Avg active importance: {result['avg_active_importance']}")
    click.echo(f"Avg archived importance: {result['avg_archived_importance']}")
    click.echo(f"Avg archived access count: {result['avg_archived_access_count']}")
    click.echo(f"Avg active age: {result['avg_active_age_days']} days")
    click.echo(f"Retention health: {result['retention_health']}")
    manager.close()


@memory.command(name="growth-rate")
@click.option("--scope", default=None, help="Scope to analyze.")
@click.option("--window", default=30, type=int, help="Window in days (default: 30).")
def memory_growth_rate(scope: str | None, window: int):
    """Show memory growth rate and projections."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.get_memory_growth_rate(scope_id=scope, window_days=window)
    click.echo(f"Scope: {result['scope_id']}")
    click.echo(f"Current active: {result['current_active']}")
    click.echo(f"Added in last {result['window_days']}d: {result['added_in_window']}")
    click.echo(f"Rate: {result['rate_per_day']}/day")
    click.echo(f"Projected 30d: +{result['projected_30d']}, 90d: +{result['projected_90d']}")
    manager.close()


@memory.command(name="compress")
@click.option("--scope", default=None, help="Scope to compress (default: configured scope).")
@click.option("--id", "memory_id", default=None, help="Compress a single memory by ID.")
def memory_compress(scope: str | None, memory_id: str | None):
    """Compress memory content by removing filler phrases and redundancy."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    if memory_id:
        result = manager.compress_content(memory_id)
        if result.get("changed"):
            click.echo(f"Compressed {memory_id}: {result['original_length']} -> {result['compressed_length']} chars ({result['reduction_pct']}% reduction)")
        else:
            click.echo(f"No change for {memory_id}")
    else:
        result = manager.batch_compress(scope_id=scope)
        click.echo(f"Compressed {result['compressed']} of {result['total']} memories, saved {result['chars_saved']} chars")
    manager.close()


@memory.command(name="auto-tag-types")
@click.option("--scope", default=None, help="Scope to tag (default: configured scope).")
def memory_auto_tag_types(scope: str | None):
    """Auto-tag memories based on their type (e.g., project_state -> 'infrastructure')."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.bulk_tag_by_type(scope_id=scope)
    click.echo(f"Tagged {result['tagged']} of {result['total']} memories")
    manager.close()


@memory.command(name="system-summary")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def memory_system_summary(as_json: bool):
    """Show comprehensive system-wide memory summary."""
    import json as _json
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    summary = manager.get_system_summary()
    if as_json:
        click.echo(_json.dumps(summary, indent=2, default=str))
    else:
        click.echo(f"Schema version: {summary['schema_version']}")
        click.echo(f"Scopes: {summary['scope_count']}")
        click.echo(f"Total active memories: {summary['total_active_memories']}")
        emb = summary["embedder"]
        click.echo(f"Embedder: {'enabled' if emb['enabled'] else 'disabled'} ({emb.get('mode', 'none')})")
        pol = summary["policy"]
        click.echo(f"Retrieval mode: {pol['retrieval_mode']}")
        click.echo(f"Max units: {pol['max_injected_units']}, Max tokens: {pol['max_injected_tokens']}")
        integrity = summary["integrity"]
        click.echo(f"Integrity: {'valid' if integrity.get('valid') else 'ISSUES FOUND'}")
        for scope in summary["scopes"]:
            click.echo(f"  {scope['scope_id']}: {scope['active']} active / {scope['total']} total")
    manager.close()


@memory.command(name="embedder-info")
def memory_embedder_info():
    """Show current embedder configuration."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    info = manager.get_embedder_info()
    for k, v in info.items():
        click.echo(f"{k}: {v}")
    manager.close()


@memory.command(name="re-embed")
@click.option("--scope", default=None, help="Scope to re-embed (default: configured scope).")
def memory_re_embed(scope: str | None):
    """Re-encode all active memories with the current embedder."""
    from .config import ConfigStore
    from .memory.manager import MemoryManager

    cs = ConfigStore()
    cfg = cs.to_metaclaw_config()
    manager = MemoryManager.from_config(cfg)
    result = manager.re_embed_scope(scope_id=scope)
    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
    else:
        click.echo(f"Re-embedded {result['re_embedded']} of {result['total']} memories in scope {result['scope_id']}")
    manager.close()


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
