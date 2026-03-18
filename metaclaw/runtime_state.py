from __future__ import annotations

from contextlib import contextmanager
import os
import tempfile
from pathlib import Path
from typing import Any


def _state_dir() -> Path:
    return Path.home() / ".metaclaw"


def pid_file_path() -> Path:
    return _state_dir() / "metaclaw.pid"


def daemon_start_lock_path() -> Path:
    return _state_dir() / "daemon_start.lock"


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return False


def _coerce_pid(value: Any) -> int | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def read_pid() -> int | None:
    try:
        pid = _coerce_pid(pid_file_path().read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return None
    if pid is None:
        pid_file_path().unlink(missing_ok=True)
        return None
    return pid


def write_pid(pid: int):
    path = pid_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(path, str(pid))


def clear_pid():
    pid_file_path().unlink(missing_ok=True)


def clear_pid_if_matches(pid: int):
    if read_pid() == pid:
        clear_pid()


def _write_text_atomic(path: Path, text: str):
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
@contextmanager
def daemon_start_lock():
    path = daemon_start_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    owner_pid = os.getpid()

    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                holder = _coerce_pid(path.read_text(encoding="utf-8").strip())
            except FileNotFoundError:
                continue

            if holder is None or not process_alive(holder):
                path.unlink(missing_ok=True)
                continue

            raise RuntimeError(holder)

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(str(owner_pid))
                handle.flush()
                os.fsync(handle.fileno())
            break
        except Exception:
            path.unlink(missing_ok=True)
            raise

    try:
        yield
    finally:
        try:
            holder = _coerce_pid(path.read_text(encoding="utf-8").strip())
        except FileNotFoundError:
            return
        except Exception:
            path.unlink(missing_ok=True)
            return

        if holder == owner_pid or holder is None:
            path.unlink(missing_ok=True)
