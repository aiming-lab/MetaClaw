#!/usr/bin/env python3
"""
rl_run.py — 运行 metaclaw-bench (RL mode)，每 N 个场景触发一次 RL 训练。

流程：
  1. 将 rl.yaml（环境变量替换后）写入 ~/.metaclaw/config.yaml
  2. 后台启动 PROXY_SCRIPT (metaclaw start)，等待就绪
  3. 执行 metaclaw-bench run --scene-per-train N
  4. 全部流程完成后终止 proxy 进程组
"""

import json
import os
import pty
import re
import select
import shutil
import signal
import socket
import sys
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path


# ===================== 核心配置（改这里就行）=====================
class cfg:
    # 日志文件路径（若已存在，自动追加 _1/_2 后缀）
    LOG_FILE = "/home/xkaiwen/workspace/metaclaw-test/benchmark/logs/rl_run/bench_run.log"

    # metaclaw-bench 可执行文件路径
    BENCH_BIN = "/home/xkaiwen/miniconda3/bin/metaclaw-bench"

    # run 命令参数
    BENCH_INPUT   = "/home/xkaiwen/workspace/metaclaw-test/benchmark/data/metaclaw-bench/all_tests_metaclaw.json"
    BENCH_OUTPUT  = "/home/xkaiwen/workspace/metaclaw-test/benchmark/results"
    BENCH_COUNT   = 3    # -n (retry)

    # 每多少个场景触发一次 RL 训练（设为 1 = 每个 day 训练一次）
    SCENE_PER_TRAIN = 5

    # 加载 API Key 的 shell 脚本（设为 None 则跳过）
    API_KEY_SCRIPT = "/home/xkaiwen/workspace/utils/apikey/metaclaw_cfg.sh"

    PROXY_SCRIPT = "/home/xkaiwen/workspace/metaclaw-test/benchmark/scripts/proxy_run.py"
    PROXY_CONFIG = "/home/xkaiwen/workspace/metaclaw-test/benchmark/scripts/config/rl.yaml"

    # 原始 skill 目录（每次运行前复制到临时目录，保证初始状态一致）
    ORIGINAL_SKILL_DIR = "/home/xkaiwen/workspace/metaclaw-test/memory_data/skills"
# =================================================================


def find_free_port() -> int:
    """让操作系统分配一个空闲端口并返回。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


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


def write_proxy_config(env: dict, temp_skill_dir: str, port: int) -> str:
    """读取 PROXY_CONFIG yaml，将 ${VAR} 替换为 env 中对应值，
    覆写 skills.dir 和 proxy.port，写入临时配置文件并返回其路径。"""
    import yaml as _yaml

    with open(cfg.PROXY_CONFIG, encoding="utf-8") as f:
        content = f.read()

    def replace(m):
        var = m.group(1)
        val = env.get(var, "")
        if not val:
            print(f"[config] 警告：环境变量 {var} 未设置，替换为空字符串")
        return val

    content = re.sub(r'\$\{(\w+)\}', replace, content)

    # 解析后覆写 skills.dir 和 proxy.port
    data = _yaml.safe_load(content) or {}
    data.setdefault("skills", {})["dir"] = temp_skill_dir
    data.setdefault("proxy", {})["port"] = port

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="metaclaw_cfg_",
        delete=False, encoding="utf-8",
    )
    _yaml.dump(data, tmp, default_flow_style=False, allow_unicode=True)
    tmp.close()
    print(f"[config] 临时配置已写入 {tmp.name} (port={port})")
    return tmp.name


def start_proxy(env: dict, config_path: str, port: int) -> subprocess.Popen:
    """后台启动 PROXY_SCRIPT（stdout/stderr 丢弃，proxy 有自己的日志），
    轮询 /healthz 确认就绪后返回进程对象。"""
    print(f"[proxy] 正在启动 proxy (RL mode, port={port})...")
    proxy_env = dict(env) if env else dict(os.environ)
    proxy_env["METACLAW_CONFIG_FILE"] = config_path
    proc = subprocess.Popen(
        [sys.executable, cfg.PROXY_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=proxy_env,
        start_new_session=True,
    )

    url = f"http://localhost:{port}/healthz"
    print("[proxy] 等待就绪...")
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"[proxy] 进程意外退出（退出码 {proc.returncode}）")
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    print("[proxy] 就绪，继续执行 benchmark...")
                    return proc
        except Exception:
            pass
        time.sleep(2)

    raise RuntimeError("[proxy] 等待超时（120s），未收到健康检查响应")


def stop_proxy(proc: subprocess.Popen):
    """向 proxy 进程组发送 SIGTERM，超时后强制 SIGKILL。"""
    if proc.poll() is not None:
        return
    print("[proxy] 正在停止 proxy...")
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.wait()
    print("[proxy] proxy 已停止")


def run_command(cmd: list, log_path: Path, env: dict = None) -> int:
    """执行命令，通过伪终端(pty)实时输出到终端和日志文件，返回退出码。"""
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

    # 第零步：分配空闲端口
    port = find_free_port()
    print(f"[port] 自动分配端口: {port}")

    # 第一步：将 ORIGINAL_SKILL_DIR 复制到临时目录，保证每次运行初始状态一致
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_skill_dir = str(Path(tempfile.gettempdir()) / f"metaclaw_skills_{ts}")
    shutil.copytree(cfg.ORIGINAL_SKILL_DIR, temp_skill_dir)
    print(f"[skills] 已复制初始 skill 目录到: {temp_skill_dir}")

    # 第二步：生成临时配置文件（skills.dir 指向临时目录，proxy.port 为动态端口）
    tmp_config_path = write_proxy_config(env or os.environ.copy(), temp_skill_dir, port)

    # 启动 proxy，等待就绪
    proxy_proc = start_proxy(env or os.environ.copy(), tmp_config_path, port)

    # 将动态端口注入 metaclaw-bench 的环境变量，供 openclaw 配置解析
    bench_env = dict(env) if env else dict(os.environ)
    bench_env["METACLAW_PROXY_PORT"] = str(port)

    start = datetime.now()
    try:
        # run（worker 强制为 1，启用 scene-per-train）
        run_cmd = [
            cfg.BENCH_BIN, "run",
            "-i", cfg.BENCH_INPUT,
            "-o", cfg.BENCH_OUTPUT,
            "-w", "1",
            "-n", str(cfg.BENCH_COUNT),
            "--scene-per-train", str(cfg.SCENE_PER_TRAIN),
        ]
        run_command(run_cmd, log_path, env=bench_env)

    finally:
        # 无论成功还是异常，都确保 proxy 被终止，并清理临时文件
        stop_proxy(proxy_proc)
        # 清理临时 skill 目录
        if os.path.isdir(temp_skill_dir):
            shutil.rmtree(temp_skill_dir)
            print(f"[skills] 已清理临时 skill 目录: {temp_skill_dir}")
        # 清理临时配置文件
        if os.path.isfile(tmp_config_path):
            os.unlink(tmp_config_path)
            print(f"[config] 已清理临时配置文件: {tmp_config_path}")

    end = datetime.now()
    append_timing(log_path, start, end)


if __name__ == "__main__":
    main()
