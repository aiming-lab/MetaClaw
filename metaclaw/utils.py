from typing import Any, Optional, TYPE_CHECKING
import os
import subprocess

if TYPE_CHECKING:
    from .config import MetaClawConfig

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


def _get_llm_provider(config: Optional["MetaClawConfig"] = None) -> str:
    """Detect whether to use Bedrock or OpenAI based on config/env."""
    if config is not None:
        if getattr(config, "mode", "") == "skills_only":
            if getattr(config, "llm_provider", "") == "bedrock":
                return "bedrock"
            return "openai"
        if getattr(config, "prm_provider", "") == "bedrock":
            return "bedrock"
        return "openai"

    try:
        from .config_store import ConfigStore

        cfg = ConfigStore().load()
        if isinstance(cfg, dict):
            mode = str(cfg.get("mode", "") or "")
            if mode == "skills_only":
                llm_provider = str((cfg.get("llm", {}) or {}).get("provider", "") or "")
                if llm_provider == "bedrock":
                    return "bedrock"
            else:
                prm_provider = str((cfg.get("rl", {}) or {}).get("prm_provider", "") or "")
                if prm_provider == "bedrock":
                    return "bedrock"
    except Exception:
        pass
    if os.environ.get("METACLAW_USE_BEDROCK", "").lower() in ("1", "true", "yes"):
        return "bedrock"
    return "openai"


def run_llm(messages, config: Optional["MetaClawConfig"] = None):
    provider = _get_llm_provider(config)

    if provider == "bedrock":
        return _run_llm_bedrock(messages, config)
    return _run_llm_openai(messages, config)


def _run_llm_bedrock(messages, config: Optional["MetaClawConfig"] = None):
    from .bedrock_client import BedrockChatClient

    if config is not None and getattr(config, "mode", "") == "skills_only":
        model_id = config.llm_model_id or os.environ.get(
            "BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6"
        )
    else:
        model_id = getattr(config, "prm_model", "") or os.environ.get(
            "BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6"
        )
    region = getattr(config, "bedrock_region", "") or os.environ.get("BEDROCK_REGION", "us-east-1")
    client = BedrockChatClient(model_id=model_id, region=region)

    rewrite_messages = [{"role": "system", "content": _COMPRESSION_INSTRUCTION}, *messages]
    response = client.chat.completions.create(
        model=model_id,
        messages=rewrite_messages,
        max_completion_tokens=2500,
    )
    return response.choices[0].message.content


def _run_llm_openai(messages, config: Optional["MetaClawConfig"] = None):
    try:
        from openai import OpenAI  # optional dep — install with: pip install metaclaw[evolve]
    except ImportError as e:
        raise ImportError(
            "The openai provider requires the 'openai' package. "
            "Install it with: pip install metaclaw[evolve]"
        ) from e
    api_base = ""
    api_key = ""
    model_id = ""

    if config is not None:
        if getattr(config, "mode", "") == "skills_only":
            api_base = getattr(config, "llm_api_base", "") or ""
            api_key = getattr(config, "llm_api_key", "") or ""
            model_id = getattr(config, "llm_model_id", "") or ""
        else:
            api_base = getattr(config, "prm_url", "") or ""
            api_key = getattr(config, "prm_api_key", "") or ""
            model_id = getattr(config, "prm_model", "") or ""
    else:
        try:
            from .config_store import ConfigStore

            cfg = ConfigStore().load()
            if isinstance(cfg, dict):
                mode = str(cfg.get("mode", "") or "")
                if mode == "skills_only":
                    llm_cfg = cfg.get("llm", {}) or {}
                    if isinstance(llm_cfg, dict):
                        api_base = str(llm_cfg.get("api_base", "") or "")
                        api_key = str(llm_cfg.get("api_key", "") or "")
                        model_id = str(llm_cfg.get("model_id", "") or "")
                else:
                    rl_cfg = cfg.get("rl", {}) or {}
                    if isinstance(rl_cfg, dict):
                        api_base = str(rl_cfg.get("prm_url", "") or "")
                        api_key = str(rl_cfg.get("prm_api_key", "") or "")
                        model_id = str(rl_cfg.get("prm_model", "") or "")
        except Exception:
            pass

    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    base_url = api_base or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = model_id or os.environ.get("PRM_MODEL", "gpt-5.2")
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
