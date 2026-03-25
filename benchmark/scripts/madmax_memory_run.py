#!/usr/bin/env python3
"""
madmax_memory_run.py — 运行 metaclaw-bench (RL + skills + memory) 全量实验。

三大系统全开，融合所有脚本特性：
  - RL: 每 N 个场景触发一次训练 (scene-per-train)
  - skills: 复制初始 skill 目录到临时目录，保证每次运行一致
  - memory: 创建独立的 memory 存储目录，运行后收集统计并生成报告
  - 动态端口分配，支持并行运行

流程：
  1. 分配空闲端口
  2. 复制初始 skill 目录到临时目录
  3. 创建本次运行的独立 memory 目录
  4. 生成临时配置文件（skills.dir + memory.dir + proxy.port）
  5. 后台启动 proxy，等待就绪
  6. metaclaw-bench run（启用 scene-per-train + memory ingest）
  7. benchmark 结束后收集 memory 统计，生成报告
  8. 停止 proxy，清理临时文件
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
import urllib.error
from datetime import datetime
from pathlib import Path


# ===================== 核心配置（改这里就行）=====================
class cfg:
    # 日志文件路径（若已存在，自动追加 _1/_2 后缀）
    LOG_FILE = "/home/xkaiwen/workspace/metaclaw-test/benchmark/logs/madmax_memory_run/bench_run.log"

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
    PROXY_CONFIG = "/home/xkaiwen/workspace/metaclaw-test/benchmark/scripts/config/madmax.yaml"

    # 原始 skill 目录（每次运行前复制到临时目录，保证初始状态一致）
    ORIGINAL_SKILL_DIR = "/home/xkaiwen/workspace/metaclaw-test/memory_data/skills"

    # memory 存储基础路径（每次运行会在此下创建时间戳子目录）
    MEMORY_STORE_BASE = "/home/xkaiwen/workspace/metaclaw-test/benchmark/memory_runs"
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
    """source shell 脚本后，将 os.environ 以 JSON 写入临时文件读回。"""
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


def create_memory_run_dir() -> Path:
    """在 MEMORY_STORE_BASE 下创建以时间戳命名的子目录，并预置 policy.json。"""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(cfg.MEMORY_STORE_BASE) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"[memory] 本次运行 memory 存储目录: {run_dir}")

    policy = {
        "version": 1,
        "retrieval_mode": "hybrid",
        "max_injected_units": 10,
        "max_injected_tokens": 1500,
        "keyword_weight": 1.0,
        "metadata_weight": 0.6,
        "importance_weight": 0.7,
        "recency_weight": 0.1,
        "recent_bonus_hours": 168,
        "type_boosts": {
            "semantic": 1.3,
            "preference": 1.2,
            "project_state": 1.1,
            "procedural_observation": 1.1,
            "working_summary": 1.0,
            "episodic": 0.7,
        },
        "notes": ["bench-optimized: high importance, low recency, semantic-boosted"],
    }
    policy_path = run_dir / "policy.json"
    policy_path.write_text(
        json.dumps(policy, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[memory] 预置 policy.json: {policy_path}")
    return run_dir


def write_proxy_config(env: dict, temp_skill_dir: str, memory_dir: Path, port: int) -> str:
    """读取 PROXY_CONFIG yaml，将 ${VAR} 替换为 env 中对应值，
    覆写 skills.dir、memory.dir 和 proxy.port，写入临时配置文件并返回其路径。"""
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

    data = _yaml.safe_load(content) or {}
    data.setdefault("skills", {})["dir"] = temp_skill_dir
    data.setdefault("memory", {})["dir"] = str(memory_dir)
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
    """后台启动 PROXY_SCRIPT，轮询 /healthz 确认就绪后返回进程对象。"""
    print(f"[proxy] 正在启动 proxy (madmax: RL+skills+memory, port={port})...")
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
        cmd, stdout=slave_fd, stderr=slave_fd, env=env, close_fds=True,
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


# ------------------------------------------------------------------ #
# Memory 统计采集与报告生成                                             #
# ------------------------------------------------------------------ #

def _api_get(path: str, port: int) -> dict | None:
    url = f"http://localhost:{port}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[memory] 警告：请求 {path} 失败: {e}")
        return None


def collect_memory_stats(port: int) -> dict:
    """从运行中的 proxy 收集 memory 统计数据。"""
    print("[memory] 正在从 proxy 收集 memory 统计数据...")
    data = {}
    data["stats"] = _api_get("/v1/memory/stats", port) or {}
    data["summary"] = _api_get("/v1/memory/summary", port) or {}
    data["health"] = _api_get("/v1/memory/health", port) or {}
    data["operator_report"] = _api_get("/v1/memory/operator-report", port) or {}
    data["feedback_analysis"] = _api_get("/v1/memory/feedback-analysis", port) or {}
    print("[memory] 统计数据收集完成")
    return data


def write_memory_report(mem_data: dict, output_dir: str, elapsed_seconds: float):
    """将 memory 统计数据写入 memory_report.md / .json。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "memory_report.md"
    json_path = out / "memory_report.json"

    stats = mem_data.get("stats", {})

    lines = [
        "# Madmax (RL+Skills+Memory) Benchmark Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Benchmark duration: {elapsed_seconds:.1f}s ({elapsed_seconds / 60:.1f}min)",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Active memories | {stats.get('active', 0)} |",
        f"| Total memories | {stats.get('total', 0)} |",
        f"| Scope | {stats.get('scope_id', 'default')} |",
        "",
    ]

    active_by_type = stats.get("active_by_type", {})
    if active_by_type:
        lines += ["## Memory Type Distribution", "", "| Type | Count | Ratio |", "|------|-------|-------|"]
        total_active = stats.get("active", 1) or 1
        for mtype, count in sorted(active_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {mtype} | {count} | {count / total_active:.1%} |")
        lines.append("")

    for section_key, section_title in [
        ("health", "Health Check"), ("summary", "System Summary"),
        ("operator_report", "Operator Report"), ("feedback_analysis", "Feedback Analysis"),
    ]:
        section = mem_data.get(section_key, {})
        if section and isinstance(section, dict):
            lines += [f"## {section_title}", ""]
            for k, v in section.items():
                if isinstance(v, (str, int, float, bool)):
                    lines.append(f"- **{k}**: {v}")
                elif isinstance(v, dict):
                    lines.append(f"- **{k}**:")
                    for sk, sv in v.items():
                        lines.append(f"  - {sk}: {sv}")
                elif isinstance(v, list) and len(v) <= 20:
                    lines.append(f"- **{k}**:")
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(f"  - {json.dumps(item, ensure_ascii=False)[:200]}")
                        else:
                            lines.append(f"  - {item}")
            lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[memory] memory_report.md 已写入: {report_path}")

    json_path.write_text(json.dumps(mem_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[memory] memory_report.json 已写入: {json_path}")


# ------------------------------------------------------------------ #
# 主流程                                                               #
# ------------------------------------------------------------------ #

def main():
    os.system("clear")

    log_path = resolve_log_path(cfg.LOG_FILE)

    env = None
    if cfg.API_KEY_SCRIPT:
        env = load_env_from_shell(cfg.API_KEY_SCRIPT)

    # 分配空闲端口
    port = find_free_port()
    print(f"[port] 自动分配端口: {port}")

    # 将 ORIGINAL_SKILL_DIR 复制到临时目录，保证每次运行初始状态一致
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_skill_dir = str(Path(tempfile.gettempdir()) / f"metaclaw_skills_{ts}")
    shutil.copytree(cfg.ORIGINAL_SKILL_DIR, temp_skill_dir)
    print(f"[skills] 已复制初始 skill 目录到: {temp_skill_dir}")

    # 创建本次运行的独立 memory 目录
    memory_dir = create_memory_run_dir()

    # 生成临时配置文件（skills.dir + memory.dir + proxy.port）
    tmp_config_path = write_proxy_config(
        env or os.environ.copy(), temp_skill_dir, memory_dir, port
    )

    # 启动 proxy，等待就绪
    proxy_proc = start_proxy(env or os.environ.copy(), tmp_config_path, port)

    # 将动态端口注入 metaclaw-bench 的环境变量
    bench_env = dict(env) if env else dict(os.environ)
    bench_env["METACLAW_PROXY_PORT"] = str(port)

    start = datetime.now()
    end = start
    try:
        # run（worker=1，scene-per-train + memory ingest）
        run_cmd = [
            cfg.BENCH_BIN, "run",
            "-i", cfg.BENCH_INPUT,
            "-o", cfg.BENCH_OUTPUT,
            "-w", "1",
            "-n", str(cfg.BENCH_COUNT),
            "--scene-per-train", str(cfg.SCENE_PER_TRAIN),
            "--memory",
            "--memory-proxy-port", str(port),
        ]
        run_command(run_cmd, log_path, env=bench_env)

        end = datetime.now()
        elapsed = (end - start).total_seconds()

        # benchmark 完成后收集 memory 统计
        mem_data = collect_memory_stats(port)
        write_memory_report(mem_data, cfg.BENCH_OUTPUT, elapsed)

    finally:
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
