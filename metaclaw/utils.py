from openai import OpenAI
from typing import Any
import os
import subprocess

def _fallback_content(messages) -> str:
    for message in reversed(messages):
        content = message.get("content", "") if isinstance(message, dict) else ""
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def run_llm(messages):
    # Prefer MetaClaw PRM config so RL mode can reuse configured judge endpoint.
    prm_url = ""
    prm_api_key = ""
    prm_model = ""
    try:
        from .config_store import ConfigStore

        cfg = ConfigStore().load()
        rl_cfg = cfg.get("rl", {}) if isinstance(cfg, dict) else {}
        if isinstance(rl_cfg, dict):
            prm_url = str(rl_cfg.get("prm_url", "") or "")
            prm_api_key = str(rl_cfg.get("prm_api_key", "") or "")
            prm_model = str(rl_cfg.get("prm_model", "") or "")
    except Exception:
        # Keep runtime resilient: fall back to environment variables/defaults.
        pass

    api_key = prm_api_key or os.environ.get("OPENAI_API_KEY", "")
    base_url = prm_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = prm_model or os.environ.get("PRM_MODEL", "gpt-5.2")
    fallback = _fallback_content(messages)
    if not api_key and base_url.rstrip("/") == "https://api.openai.com/v1":
        return fallback

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    compression_instruction = (
        "You are compressing an OpenClaw system prompt. "
        "Rewrite it to be under 2000 tokens while preserving behavior. "
        "Keep all critical policy and routing rules: "
        "(1) tool names and their intended usage constraints, "
        "(2) safety and non-delegable prohibitions, "
        "(3) skills-selection rules, "
        "(4) memory recall requirements, "
        "(5) update/config restrictions, "
        "(6) reply-tag/messaging rules, "
        "(7) heartbeat handling rules. "
        "Remove duplicated prose, repeated examples, and decorative language. "
        "Prefer compact bullet sections with short imperative statements. "
        "Do not invent or weaken any rule. "
        "Output only the rewritten system prompt text."
    )
    rewrite_messages = [{"role": "system", "content": compression_instruction}, *messages]

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=rewrite_messages,
            max_completion_tokens=2500,
        )
    except Exception:
        return fallback
    return response.choices[0].message.content or fallback


def run_turn(message: str) -> str:
    """Run one OpenClaw agent turn with a user message."""
    cmd = [
        "pnpm", "openclaw", "agent",
        "--message", message,
        "--agent", "main",
    ]
    result = subprocess.run(
        cmd,
        cwd=os.environ.get("OPENCLAW_PATH", ""),
        capture_output=True,
        text=True,
    )
    return result.stdout
