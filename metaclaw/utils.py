from openai import OpenAI
from typing import Any
import os
import subprocess

_COMPRESSION_INSTRUCTION = (
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


def _get_llm_provider() -> str:
    """Detect whether to use Bedrock or OpenAI based on config/env."""
    try:
        from .config_store import ConfigStore
        cfg = ConfigStore().load()
        if isinstance(cfg, dict):
            prm_provider = cfg.get("rl", {}).get("prm_provider", "")
            if prm_provider == "bedrock":
                return "bedrock"
    except Exception:
        pass
    if os.environ.get("METACLAW_USE_BEDROCK", "").lower() in ("1", "true", "yes"):
        return "bedrock"
    return "openai"


def run_llm(messages):
    provider = _get_llm_provider()

    if provider == "bedrock":
        return _run_llm_bedrock(messages)
    return _run_llm_openai(messages)


def _run_llm_bedrock(messages):
    from .bedrock_client import BedrockChatClient

    model_id = os.environ.get("BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    client = BedrockChatClient(model_id=model_id, region=region)

    rewrite_messages = [{"role": "system", "content": _COMPRESSION_INSTRUCTION}, *messages]
    response = client.chat.completions.create(
        model=model_id,
        messages=rewrite_messages,
        max_completion_tokens=2500,
    )
    return response.choices[0].message.content


def _run_llm_openai(messages):
    prm_url = ""
    prm_api_key = ""
    prm_model = ""
    llm_url = ""
    llm_api_key = ""
    mode = "auto"
    try:
        from .config_store import ConfigStore

        cfg = ConfigStore().load()
        if isinstance(cfg, dict):
            mode = cfg.get("mode", "auto") or "auto"
            rl_cfg = cfg.get("rl", {}) or {}
            llm_cfg = cfg.get("llm", {}) or {}
            if isinstance(rl_cfg, dict):
                prm_url = str(rl_cfg.get("prm_url", "") or "")
                prm_api_key = str(rl_cfg.get("prm_api_key", "") or "")
                prm_model = str(rl_cfg.get("prm_model", "") or "")
            if isinstance(llm_cfg, dict):
                llm_url = str(llm_cfg.get("api_base", "") or "")
                llm_api_key = str(llm_cfg.get("api_key", "") or "")
    except Exception:
        pass

    # In skills_only mode: llm.* config values take priority over OPENAI_* env vars.
    # In other modes: rl.prm_* config values take priority (existing behaviour).
    if mode == "skills_only":
        api_key = llm_api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = llm_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    else:
        api_key = prm_api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = prm_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = prm_model or os.environ.get("PRM_MODEL", "gpt-5.2")
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    rewrite_messages = [{"role": "system", "content": _COMPRESSION_INSTRUCTION}, *messages]
    response = client.chat.completions.create(
        model=model_id,
        messages=rewrite_messages,
        max_completion_tokens=2500,
    )
    return response.choices[0].message.content


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
