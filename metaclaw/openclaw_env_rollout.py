"""
Programmatic rollout: task JSONL → Qwen3-native agent loop → Tinker proxy.

Architecture (mirrors OpenClaw-RL, passive proxy + external task driver):

    task JSONL  (<data_dir>/<split>.jsonl)
        ↓
    Qwen3 agent loop  (this file)
        ↓  HTTP POST  X-Session-Id + X-Turn-Type: main
    proxy (localhost:30000)
        ↓  SamplingClient.sample_async
    Tinker / Qwen3
        ↓  parse <tool_call>
    subprocess (real openclaw CLI)
        ↓  stdout / stderr observation
    loop back

Each LLM call produces one ConversationSample in the proxy's output queue.
The MetaClawTrainer drains that queue to get training batches.

Data format  (<data_dir>/<split>.jsonl, one JSON object per line):
    {"task_id": "add_webhook_1", "instruction": "Register the webhook URL ..."}

Reward: fully delegated to the PRM in the proxy (no env.evaluate()).
        rollout_loop logs reward=0 for all episodes (proxy handles real rewards).

Tool call format: Qwen25/Qwen3 XML  (<tool_call>…</tool_call>)
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


# ── Tool call parsing (Qwen25/Qwen3 format) ──────────────────────────────────

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _parse_tool_call(text: str) -> Optional[str]:
    """Extract the `command` argument from a Qwen3 <tool_call> response."""
    m = _TOOL_CALL_RE.search(text)
    if not m:
        return None
    try:
        payload = json.loads(m.group(1))
        return payload.get("arguments", {}).get("command")
    except json.JSONDecodeError:
        logger.warning("[EnvRollout] bad tool-call JSON: %r", m.group(1)[:200])
        return None


def _strip_thinking(text: str) -> str:
    """Remove <think>…</think> blocks for display."""
    return _THINK_RE.sub("", text).strip()


# ── Tool schema ───────────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a CLI command and observe the output. "
                "When the task is fully complete, call run_command with command=\"done\"."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "The exact CLI command to run, e.g. "
                            "'openclaw status', "
                            "'openclaw agents add --name bot1 --model gpt-4o', "
                            "'done'"
                        ),
                    }
                },
                "required": ["command"],
            },
        },
    }
]

SYSTEM_PROMPT = """\
You are an expert CLI agent controlling an OpenClaw installation.
Your goal is to complete the given task by issuing CLI commands via the run_command tool.

Guidelines:
- Issue ONE command at a time and carefully read the output before proceeding.
- Use 'openclaw status' or similar read commands to inspect state before making changes.
- Handle errors: if a command fails, diagnose from the output and retry differently.
- When the task is fully complete, call run_command with command="done".
- Do NOT ask clarifying questions — act based on the task description alone.
"""

_SYSTEM_PROMPT_CACHE_PATH = Path(__file__).resolve().parents[1] / "records" / "system_prompt_cache.json"


def _get_rollout_system_prompt() -> str:
    """Use cached prompt if available, otherwise fallback to default."""
    try:
        if _SYSTEM_PROMPT_CACHE_PATH.exists():
            payload = json.loads(_SYSTEM_PROMPT_CACHE_PATH.read_text(encoding="utf-8"))
            cached = payload.get("compressed_system_prompt")
            if isinstance(cached, str) and cached.strip():
                return cached.strip()
    except Exception as e:
        logger.warning("[EnvRollout] failed to read system prompt cache: %s", e)
    return SYSTEM_PROMPT


# ── Command execution ─────────────────────────────────────────────────────────

async def _exec_command(cmd: str, timeout: float = 30.0) -> str:
    """Run a shell command and return combined stdout + stderr."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
        return output.strip() or "(no output)"
    except asyncio.TimeoutError:
        return f"Error: command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


# ── Single episode ────────────────────────────────────────────────────────────

async def run_task_episode(
    task_id: str,
    task_instruction: str,
    proxy_url: str,
    model_id: str = "Qwen3-4B-Instruct-2507",
    max_steps: int = 15,
    temperature: float = 0.6,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """
    Run one complete task episode.

    Sends HTTP requests to the proxy (training data collection side-effect).
    Command execution uses subprocess — no cli-agent-env dependency.
    Reward is always 0 here; real rewards come from PRM scoring in the proxy.
    """
    session_id = f"env-{task_id[:24]}-{uuid.uuid4().hex[:6]}"
    rollout_system_prompt = _get_rollout_system_prompt()

    messages: list[dict] = [
        {"role": "system", "content": rollout_system_prompt},
        {"role": "user", "content": f"{task_instruction}"},
    ]

    step = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        for step in range(max_steps):
            # ── Call proxy (Qwen3 via Tinker) ─────────────────────────────
            try:
                resp = await client.post(
                    f"{proxy_url}/v1/chat/completions",
                    json={
                        "model": model_id,
                        "messages": messages,
                        "tools": TOOLS,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    headers={
                        "X-Session-Id": session_id,
                        "X-Turn-Type": "main",
                    },
                )
                resp.raise_for_status()
                output = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503:
                    logger.info("[EnvRollout] %s: proxy paused, retrying in 3s …", task_id)
                    await asyncio.sleep(3.0)
                    continue
                logger.error("[EnvRollout] %s step=%d HTTP %d", task_id, step, e.response.status_code)
                break
            except Exception as e:
                logger.error("[EnvRollout] %s step=%d error: %s", task_id, step, e)
                break

            choice = output.get("choices", [{}])[0]
            content: str = choice.get("message", {}).get("content") or ""
            command = _parse_tool_call(content)
            brief = _strip_thinking(content)[:120]

            logger.info(
                f"{_YELLOW}[EnvRollout] {task_id} step={step} "
                f"cmd={command!r} response={brief!r}{_RESET}"
            )

            # ── No tool call ───────────────────────────────────────────────
            if command is None:
                logger.info("[EnvRollout] %s: no tool call → closing session", task_id)
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "No command issued. Closing session."})
                break

            cmd = command.strip()

            # ── Agent signals task complete ────────────────────────────────
            if cmd.lower() == "done":
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "Task complete."})
                break

            # ── Execute command via subprocess ─────────────────────────────
            cmd_output = await _exec_command(cmd)
            logger.info("[EnvRollout] %s cmd_output: %s", task_id, cmd_output[:200])

            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"Output:\n{cmd_output}"})

        # ── Close session (scores last real turn via PRM) ──────────────────
        try:
            await client.post(
                f"{proxy_url}/v1/chat/completions",
                json={
                    "model": model_id,
                    "messages": messages,
                    "tools": TOOLS,
                    "temperature": temperature,
                    "max_tokens": 64,
                },
                headers={
                    "X-Session-Id": session_id,
                    "X-Turn-Type": "main",
                    "X-Session-Done": "true",
                },
            )
        except Exception as e:
            logger.warning("[EnvRollout] %s session-close failed: %s", task_id, e)

    logger.info(
        f"{_GREEN}[EnvRollout] {task_id} done | steps={step}{_RESET}"
    )
    # Reward is 0 here — actual reward is PRM-scored inside the proxy.
    return {"task_id": task_id, "reward": 0.0, "steps": step, "success": True}


# ── Task listing ──────────────────────────────────────────────────────────────

def load_tasks(data_dir: str, split: str = "train") -> list[dict]:
    """
    Load tasks from a JSONL file.

    Expects:  <data_dir>/<split>.jsonl
    Each line: {"task_id": "...", "instruction": "..."}

    This format is consistent with slime's Dataset (used in OpenClaw-RL).
    No cli-agent-env dependency.
    """
    split_file = Path(data_dir) / f"{split}.jsonl"
    if not split_file.exists():
        raise FileNotFoundError(
            f"Task JSONL not found: {split_file}\n"
            f"Expected format: one JSON object per line with 'task_id' and 'instruction' fields."
        )
    tasks = []
    for line in split_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tasks.append(json.loads(line))
        except json.JSONDecodeError as e:
            logger.warning("[EnvRollout] skipping bad JSON line: %s", e)
    if not tasks:
        raise ValueError(f"No tasks found in {split_file}")
    return tasks


# ── Continuous rollout loop ───────────────────────────────────────────────────

async def rollout_loop(
    proxy_url: str,
    data_dir: str,
    split: str = "train",
    concurrency: int = 4,
    max_steps_per_episode: int = 15,
    temperature: float = 0.6,
    model_id: str = "Qwen3-4B-Instruct-2507",
) -> None:
    """
    Continuously run task episodes in parallel, feeding training data to the proxy.

    Reads tasks from <data_dir>/<split>.jsonl (standard slime JSONL format).
    Runs `concurrency` episodes at a time; when a batch finishes, samples new
    tasks and starts again.  Runs forever until cancelled.

    The proxy collects each LLM call as a ConversationSample and puts it in
    the rollout worker's output queue.  The trainer drains that queue.
    Reward = 0 in the rollout; actual reward comes from PRM inside the proxy.
    """
    tasks = load_tasks(data_dir, split)
    logger.info(
        "[EnvRollout] %d tasks loaded from %s/%s.jsonl | concurrency=%d",
        len(tasks), data_dir, split, concurrency,
    )

    episode_count = 0
    while True:
        batch = random.choices(tasks, k=concurrency)
        logger.info(
            "[EnvRollout] launching %d episodes: %s …",
            concurrency, [t.get("task_id", "?") for t in batch[:3]],
        )

        results = await asyncio.gather(
            *[
                run_task_episode(
                    task_id=t.get("task_id", f"task_{i}"),
                    task_instruction=t.get("instruction", ""),
                    proxy_url=proxy_url,
                    model_id=model_id,
                    max_steps=max_steps_per_episode,
                    temperature=temperature,
                )
                for i, t in enumerate(batch)
            ],
            return_exceptions=True,
        )

        episode_count += concurrency
        for r in results:
            if isinstance(r, Exception):
                logger.warning("[EnvRollout] episode error: %s", r)

        logger.info(
            f"{_GREEN}[EnvRollout] episodes=%d{_RESET}",
            episode_count,
        )
