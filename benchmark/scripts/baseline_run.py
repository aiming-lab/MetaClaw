#!/usr/bin/env python3
"""
baseline_run.py — 运行 metaclaw-bench run，实时输出到终端并写入日志。
替代 bench_with_tee.sh，解决 tee 阻塞终端打印的问题。
"""

import json
import os
import pty
import select
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


# ===================== 核心配置（改这里就行）=====================
class cfg:
    # 日志文件路径（若已存在，自动追加 _1/_2 后缀）
    LOG_FILE = "/home/xkaiwen/workspace/metaclaw-test/benchmark/logs/baseline_run/bench_run.log"

    # metaclaw-bench 可执行文件路径
    BENCH_BIN = "/home/xkaiwen/miniconda3/bin/metaclaw-bench"

    # run 命令参数
    BENCH_INPUT   = "/home/xkaiwen/workspace/metaclaw-test/benchmark/data/metaclaw-bench/all_tests.json"
    BENCH_OUTPUT  = "/home/xkaiwen/workspace/metaclaw-test/benchmark/results"
    BENCH_WORKERS = 15   # -w
    BENCH_COUNT   = 3    # -n

    # 加载 API Key 的 shell 脚本（设为 None 则跳过）
    API_KEY_SCRIPT = "/home/xkaiwen/workspace/utils/apikey/metaclaw_cfg.sh"
# =================================================================


def resolve_log_path(log_file: str) -> Path:
    """若目标路径已存在，依次尝试 _1/_2/... 后缀直到找到空位。"""
    p = Path(log_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        return p
    stem, suffix = p.stem, p.suffix
    n = 1
    while True:
        candidate = p.parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def load_env_from_shell(script_path: str) -> dict:
    """source shell 脚本后，将 os.environ 以 JSON 写入临时文件读回，
    完全隔离 shell 脚本自身的 stdout 输出，避免 JSON 解析污染。"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["bash", "-c",
             f"source {script_path} && "
             "python3 -c 'import os,json; json.dump(dict(os.environ),open(os.environ[\"__TMP_ENV\"],\"w\"))'"],
            env={**os.environ, "__TMP_ENV": tmp_path},
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"加载 env 脚本失败：{script_path}")
        with open(tmp_path) as f:
            return json.load(f)
    finally:
        os.unlink(tmp_path)


def run_command(cmd: list, log_path: Path, env: dict = None) -> int:
    """执行命令，通过伪终端(pty)实时输出到终端和日志文件，返回退出码。
    使用 pty 让子进程认为自己在写 TTY，保持行缓冲，数据产生即刷出。"""
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        cmd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)

    with open(log_path, "a", encoding="utf-8") as log_f:
        while True:
            try:
                r, _, _ = select.select([master_fd], [], [], 1.0)
                if r:
                    chunk = os.read(master_fd, 4096)
                    if not chunk:
                        break
                    text = chunk.decode("utf-8", errors="replace")
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    log_f.write(text)
                    log_f.flush()
                elif proc.poll() is not None:
                    break
            except OSError:
                break

    os.close(master_fd)
    proc.wait()
    return proc.returncode


def append_timing(log_path: Path, start: datetime, end: datetime):
    """将计时结果追加到日志并打印到终端。"""
    elapsed = (end - start).total_seconds()
    lines = [
        "",
        "----------------------------------------",
        "命令执行完成！",
        f"开始时间：{start.strftime('%Y-%m-%d %H:%M:%S')}",
        f"结束时间：{end.strftime('%Y-%m-%d %H:%M:%S')}",
        f"总耗时：{elapsed:.3f} 秒",
        "========================================",
        "",
    ]
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("----------------------------------------")
    print(f"命令执行完成！总耗时：{elapsed:.3f} 秒")
    print(f"全部信息已写入日志文件：{log_path}")


def main():
    os.system("clear")

    log_path = resolve_log_path(cfg.LOG_FILE)

    env = None
    if cfg.API_KEY_SCRIPT:
        env = load_env_from_shell(cfg.API_KEY_SCRIPT)

    start = datetime.now()

    # run
    run_cmd = [
        cfg.BENCH_BIN, "run",
        "-i", cfg.BENCH_INPUT,
        "-o", cfg.BENCH_OUTPUT,
        "-w", str(cfg.BENCH_WORKERS),
        "-n", str(cfg.BENCH_COUNT),
    ]
    run_command(run_cmd, log_path, env=env)

    end = datetime.now()

    append_timing(log_path, start, end)


if __name__ == "__main__":
    main()
