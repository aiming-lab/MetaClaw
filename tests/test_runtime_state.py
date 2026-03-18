from metaclaw import runtime_state


def test_read_pid_clears_non_positive_pid(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    pid_path = runtime_state.pid_file_path()
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("0", encoding="utf-8")

    assert runtime_state.read_pid() is None
    assert not pid_path.exists()


def test_process_alive_treats_permission_error_as_live(monkeypatch):
    def fake_kill(pid, sig):
        raise PermissionError

    monkeypatch.setattr("os.kill", fake_kill)

    assert runtime_state.process_alive(12345) is True


def test_clear_pid_if_matches_only_clears_matching_pid(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    pid_path = runtime_state.pid_file_path()
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("12345", encoding="utf-8")

    runtime_state.clear_pid_if_matches(12345)

    assert not pid_path.exists()


def test_daemon_start_lock_reclaims_stale_holder(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    lock_path = runtime_state.daemon_start_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("99999", encoding="utf-8")
    monkeypatch.setattr("os.getpid", lambda: 12345)
    monkeypatch.setattr(runtime_state, "process_alive", lambda pid: pid == 12345)

    with runtime_state.daemon_start_lock():
        assert lock_path.exists()
        assert lock_path.read_text(encoding="utf-8").strip() == "12345"

    assert not lock_path.exists()


def test_daemon_start_lock_rejects_live_holder(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    lock_path = runtime_state.daemon_start_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("54321", encoding="utf-8")
    monkeypatch.setattr(runtime_state, "process_alive", lambda pid: pid == 54321)

    try:
        with runtime_state.daemon_start_lock():
            raise AssertionError("lock acquisition should have failed")
    except RuntimeError as exc:
        assert exc.args == (54321,)
    else:
        raise AssertionError("expected RuntimeError for live daemon start lock holder")
