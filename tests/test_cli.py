import os
import signal
import subprocess

import click
from click.testing import CliRunner

from metaclaw import cli


def test_start_daemon_spawns_detached_child(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    class FakeConfigStore:
        def exists(self):
            return True

        def get(self, key):
            assert key == "proxy.port"
            return 30000

    class FakeProcess:
        pid = 43210

        def poll(self):
            return None

    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(cli, "ConfigStore", FakeConfigStore)
    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr(cli, "_wait_for_daemon_ready", lambda proc, port, log_path: None)

    runner = CliRunner()
    result = runner.invoke(cli.metaclaw, ["start", "--daemon"])

    assert result.exit_code == 0
    assert "MetaClaw started in background (PID=43210)." in result.output
    assert "metaclaw status" in result.output
    assert "metaclaw stop" in result.output
    assert captured["cmd"] == [cli.sys.executable, "-m", "metaclaw", "start"]
    assert captured["kwargs"]["stdin"] == subprocess.DEVNULL
    assert captured["kwargs"]["stderr"] == subprocess.STDOUT
    assert captured["kwargs"]["close_fds"] is True
    assert captured["kwargs"]["stdout"].name.endswith("metaclaw.log")
    assert captured["kwargs"]["env"]["METACLAW_RUNTIME_KIND"] == "daemon"
    assert captured["kwargs"]["env"]["METACLAW_RUNTIME_LOG_PATH"].endswith("metaclaw.log")
    if os.name == "nt":
        assert captured["kwargs"]["creationflags"] != 0
    else:
        assert captured["kwargs"]["start_new_session"] is True


def test_start_daemon_propagates_mode_port_and_log_file_without_parent_override_file(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))

    class FakeConfigStore:
        def exists(self):
            return True

    class FakeProcess:
        pid = 43211

        def poll(self):
            return None

    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeProcess()

    monkeypatch.setattr(cli, "ConfigStore", FakeConfigStore)
    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr(cli, "_wait_for_daemon_ready", lambda proc, port, log_path: None)
    monkeypatch.setattr(
        cli,
        "_build_session_override_store",
        lambda config_store, mode, port: (_ for _ in ()).throw(
            AssertionError("daemon path should not build an override config file")
        ),
    )

    runner = CliRunner()
    log_path = tmp_path / "custom.log"
    result = runner.invoke(
        cli.metaclaw,
        [
            "start",
            "--daemon",
            "--mode",
            "skills_only",
            "--port",
            "31001",
            "--log-file",
            str(log_path),
        ],
    )

    assert result.exit_code == 0
    assert captured["cmd"] == [
        cli.sys.executable,
        "-m",
        "metaclaw",
        "start",
        "--mode",
        "skills_only",
        "--port",
        "31001",
    ]
    assert str(log_path) in result.output


def test_wait_for_daemon_ready_returns_after_health_check(monkeypatch, tmp_path):
    class FakeProcess:
        def poll(self):
            return None

    checks = iter([False, True])
    monkeypatch.setattr(cli, "_healthz_ready", lambda port, timeout=0.5: next(checks))
    monkeypatch.setattr("time.sleep", lambda _: None)

    cli._wait_for_daemon_ready(FakeProcess(), 30000, tmp_path / "metaclaw.log", timeout_s=1.0)


def test_wait_for_daemon_ready_raises_when_process_exits(monkeypatch, tmp_path):
    class FakeProcess:
        def poll(self):
            return 23

    monkeypatch.setattr(cli, "_healthz_ready", lambda port, timeout=0.5: False)

    try:
        cli._wait_for_daemon_ready(FakeProcess(), 30000, tmp_path / "metaclaw.log", timeout_s=0.2)
    except click.ClickException as exc:
        assert "exited with code 23" in str(exc)
        assert "metaclaw.log" in str(exc)
    else:
        raise AssertionError("expected ClickException when daemon exits early")


def test_spawn_daemon_process_terminates_child_and_cleans_runtime_files_on_timeout(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))

    class FakeProcess:
        pid = 43212

        def __init__(self):
            self._alive = True
            self.terminated = False
            self.waits = []

        def poll(self):
            return None if self._alive else 0

        def wait(self, timeout=None):
            self.waits.append(timeout)
            self._alive = False
            return 0

    proc = FakeProcess()
    cleared = []

    monkeypatch.setattr(cli, "_ensure_daemon_not_running", lambda: None)
    monkeypatch.setattr(
        "metaclaw.runtime_state.daemon_start_lock",
        lambda: __import__("contextlib").nullcontext(),
    )
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda cmd, **kwargs: proc,
    )
    monkeypatch.setattr(
        cli,
        "_wait_for_daemon_ready",
        lambda proc_, port, log_path: (_ for _ in ()).throw(click.ClickException("timeout")),
    )
    monkeypatch.setattr(cli, "_clear_pid_if_matches", lambda pid: cleared.append(pid))
    killpg_calls = []
    monkeypatch.setattr("os.killpg", lambda pid, sig: killpg_calls.append((pid, sig)))

    try:
        cli._spawn_daemon_process(None, None, None, effective_port=30000)
    except click.ClickException as exc:
        assert "timeout" in str(exc)
    else:
        raise AssertionError("expected ClickException when daemon startup times out")

    assert killpg_calls == [(43212, signal.SIGTERM)]
    assert proc.waits == [5]
    assert cleared == [43212]


def test_start_cleans_up_temp_override_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    class FakeConfigStore:
        def exists(self):
            return True

    temp_config = tmp_path / "session-override.yaml"
    temp_config.write_text("mode: skills_only\n", encoding="utf-8")

    class FakeLauncher:
        def __init__(self, config_store):
            self.config_store = config_store

        async def start(self):
            return None

        def stop(self):
            return None

    monkeypatch.setattr(cli, "ConfigStore", FakeConfigStore)
    monkeypatch.setattr(cli, "_build_session_override_store", lambda cs, mode, port: (cs, temp_config))
    monkeypatch.setattr("metaclaw.launcher.MetaClawLauncher", FakeLauncher)

    runner = CliRunner()
    result = runner.invoke(cli.metaclaw, ["start", "--mode", "skills_only"])

    assert result.exit_code == 0
    assert not temp_config.exists()


def test_ensure_daemon_not_running_rejects_live_pid(monkeypatch):
    monkeypatch.setattr(cli, "_read_pid", lambda: 12345)
    monkeypatch.setattr(cli, "_is_process_alive", lambda pid: True)

    try:
        cli._ensure_daemon_not_running()
    except click.ClickException as exc:
        assert "already running" in str(exc)
        assert "12345" in str(exc)
    else:
        raise AssertionError("expected ClickException when an active daemon already exists")


def test_ensure_daemon_not_running_clears_stale_pid(monkeypatch):
    cleared = []

    monkeypatch.setattr(cli, "_read_pid", lambda: 12345)
    monkeypatch.setattr(cli, "_is_process_alive", lambda pid: False)
    monkeypatch.setattr(cli, "_clear_pid", lambda: cleared.append(True))

    cli._ensure_daemon_not_running()

    assert cleared == [True]


def test_status_uses_configured_mode_and_port(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".metaclaw"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "metaclaw.pid").write_text("54321", encoding="utf-8")

    calls = []
    monkeypatch.setattr("os.kill", lambda pid, sig: calls.append((pid, sig)))
    monkeypatch.setattr(cli, "_healthz_ready", lambda port, timeout=2.0: True)

    class FakeConfigStore:
        def get(self, key):
            if key == "proxy.port":
                return 31001
            if key == "mode":
                return "skills_only"
            raise AssertionError(f"unexpected key: {key}")

    monkeypatch.setattr(cli, "ConfigStore", FakeConfigStore)

    runner = CliRunner()
    result = runner.invoke(cli.metaclaw, ["status"])

    assert result.exit_code == 0
    assert "PID=54321" in result.output
    assert "mode=skills_only" in result.output
    assert "proxy=:31001" in result.output
    assert calls == [(54321, 0)]


def test_stop_removes_pid_file_after_signal(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".metaclaw"
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = state_dir / "metaclaw.pid"
    pid_path.write_text("54321", encoding="utf-8")
    calls = []

    monkeypatch.setattr("os.kill", lambda pid, sig: calls.append((pid, sig)))

    runner = CliRunner()
    result = runner.invoke(cli.metaclaw, ["stop"])

    assert result.exit_code == 0
    assert calls == [(54321, signal.SIGTERM)]
    assert "Sent SIGTERM to PID 54321." in result.output
    assert not pid_path.exists()


def test_stop_cleans_pid_file_when_pid_is_stale(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".metaclaw"
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = state_dir / "metaclaw.pid"
    pid_path.write_text("54321", encoding="utf-8")

    def fake_kill(pid, sig):
        raise ProcessLookupError

    monkeypatch.setattr("os.kill", fake_kill)

    runner = CliRunner()
    result = runner.invoke(cli.metaclaw, ["stop"])

    assert result.exit_code == 0
    assert not pid_path.exists()
    assert "cleaning up stale PID file" in result.output


def test_start_daemon_rejects_concurrent_start_lock(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    class FakeConfigStore:
        def exists(self):
            return True

        def get(self, key):
            assert key == "proxy.port"
            return 30000

    @__import__("contextlib").contextmanager
    def fake_lock():
        raise RuntimeError(98765)
        yield

    monkeypatch.setattr(cli, "ConfigStore", FakeConfigStore)
    monkeypatch.setattr("metaclaw.runtime_state.daemon_start_lock", fake_lock)

    runner = CliRunner()
    result = runner.invoke(cli.metaclaw, ["start", "--daemon"])

    assert result.exit_code != 0
    assert "already in progress" in result.output
    assert "98765" in result.output
