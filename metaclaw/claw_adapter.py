"""
Claw adapter: auto-configures the active CLI agent to use the MetaClaw proxy.

Supported agents:
  openclaw  — runs `openclaw config set …` + `openclaw gateway restart`
  copaw     — patches ~/.copaw/config.json, triggers daemon hot-reload
  ironclaw  — patches ~/.ironclaw/.env, runs `ironclaw service restart`
  picoclaw  — patches ~/.picoclaw/config.json model_list, runs `picoclaw gateway restart`
  zeroclaw  — patches ~/.zeroclaw/config.toml, runs `zeroclaw service restart`
  none      — skip auto-configuration entirely

Add more claws by implementing a `_configure_<name>` function and registering
it in ``_ADAPTERS``.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .config import MetaClawConfig

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Dispatcher                                                          #
# ------------------------------------------------------------------ #

def configure_claw(cfg: "MetaClawConfig") -> None:
    """Dispatch to the appropriate claw adapter based on cfg.claw_type."""
    claw = getattr(cfg, "claw_type", "openclaw")

    # Backward-compat: configure_openclaw=False → treat as "none"
    configure_flag = getattr(cfg, "configure_openclaw", True)
    if not configure_flag:
        claw = "none"

    adapter = _ADAPTERS.get(claw)
    if adapter is None:
        logger.warning(
            "[ClawAdapter] Unknown claw_type=%r — skipping auto-configuration", claw
        )
        return
    adapter(cfg)


# ------------------------------------------------------------------ #
# OpenClaw adapter                                                    #
# ------------------------------------------------------------------ #

def _configure_openclaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure OpenClaw to use the MetaClaw proxy."""
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"
    provider_json = json.dumps({
        "api": "openai-completions",
        "baseUrl": f"http://127.0.0.1:{cfg.proxy_port}/v1",
        "apiKey": cfg.proxy_api_key or "metaclaw",
        "models": [{
            "id": model_id,
            "name": model_id,
            "reasoning": False,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 32768,
            "maxTokens": 8192,
        }],
    })

    commands = [
        ["openclaw", "config", "set", "models.providers.metaclaw",
         "--json", provider_json],
        ["openclaw", "config", "set", "agents.defaults.model.primary",
         f"metaclaw/{model_id}"],
        ["openclaw", "config", "set", "agents.defaults.sandbox.mode", "off"],
        ["openclaw", "gateway", "restart"],
    ]
    _run_commands("openclaw", commands)


# ------------------------------------------------------------------ #
# CoPaw adapter                                                       #
# ------------------------------------------------------------------ #

def _configure_copaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure CoPaw to use the MetaClaw proxy.

    Patches ~/.copaw/config.json to set the default model provider to
    the MetaClaw OpenAI-compatible endpoint.  CoPaw's ConfigWatcher will
    hot-reload the file automatically; we also attempt a daemon restart
    as a fallback for instant effect.
    """
    config_path = Path.home() / ".copaw" / "config.json"
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"

    # Load existing config or start fresh
    data: dict = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[ClawAdapter] Failed to read %s: %s", config_path, e)

    # Inject MetaClaw as the default model provider
    if not isinstance(data.get("models"), dict):
        data["models"] = {}
    data["models"]["default"] = {
        "provider": "openai_compatible",
        "model": model_id,
        "api_key": cfg.proxy_api_key or "metaclaw",
        "base_url": f"http://127.0.0.1:{cfg.proxy_port}/v1",
    }

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("[ClawAdapter] CoPaw config updated: %s", config_path)
    except Exception as e:
        logger.error("[ClawAdapter] Failed to write %s: %s", config_path, e)
        return

    # Hot-reload: CoPaw's ConfigWatcher picks up the file change automatically.
    # Also attempt `copaw daemon restart` for immediate effect (ignore if not running).
    _run_commands("copaw", [["copaw", "daemon", "restart"]], ignore_missing=True)


# ------------------------------------------------------------------ #
# IronClaw adapter                                                    #
# ------------------------------------------------------------------ #

def _configure_ironclaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure IronClaw to use the MetaClaw proxy.

    Patches ~/.ironclaw/.env to set LLM_BACKEND=openai_compatible and
    point LLM_BASE_URL at the MetaClaw proxy port.  Triggers a service
    restart so the new env vars take effect immediately.
    """
    env_path = Path.home() / ".ironclaw" / ".env"
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"

    new_vars = {
        "LLM_BACKEND": "openai_compatible",
        "LLM_BASE_URL": f"http://127.0.0.1:{cfg.proxy_port}/v1",
        "LLM_MODEL": model_id,
        "LLM_API_KEY": cfg.proxy_api_key or "metaclaw",
    }

    _patch_dotenv(env_path, new_vars)

    # IronClaw reads .env at startup, so a service restart is required.
    _run_commands(
        "ironclaw",
        [["ironclaw", "service", "restart"]],
        ignore_missing=True,
    )


def _patch_dotenv(env_path: Path, new_vars: dict[str, str]) -> None:
    """Update or insert KEY=VALUE lines in a .env file (preserves comments)."""
    lines: list[str] = []
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            logger.warning("[ClawAdapter] Failed to read %s: %s", env_path, e)

    updated: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in new_vars:
            new_lines.append(f"{key}={new_vars[key]}")
            updated.add(key)
        else:
            new_lines.append(line)

    # Append any keys that were not already in the file
    for key, val in new_vars.items():
        if key not in updated:
            new_lines.append(f"{key}={val}")

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        logger.info("[ClawAdapter] IronClaw .env updated: %s", env_path)
    except Exception as e:
        logger.error("[ClawAdapter] Failed to write %s: %s", env_path, e)


# ------------------------------------------------------------------ #
# PicoClaw adapter                                                     #
# ------------------------------------------------------------------ #

def _configure_picoclaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure PicoClaw to use the MetaClaw proxy.

    Injects a ``metaclaw`` entry into the ``model_list`` array in
    ``~/.picoclaw/config.json`` and sets it as the default model via
    ``agents.defaults.model_name``.
    """
    config_path = Path.home() / ".picoclaw" / "config.json"
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"

    data: dict = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[ClawAdapter] Failed to read %s: %s", config_path, e)

    # Build the MetaClaw model entry
    metaclaw_entry = {
        "model_name": "metaclaw",
        "model": f"openai/{model_id}",
        "api_key": cfg.proxy_api_key or "metaclaw",
        "api_base": f"http://127.0.0.1:{cfg.proxy_port}/v1",
    }

    # Ensure model_list exists and upsert the metaclaw entry
    model_list = data.get("model_list")
    if not isinstance(model_list, list):
        model_list = []
    # Remove any previous metaclaw entry
    model_list = [m for m in model_list if m.get("model_name") != "metaclaw"]
    model_list.append(metaclaw_entry)
    data["model_list"] = model_list

    # Set metaclaw as the active default model
    if not isinstance(data.get("agents"), dict):
        data["agents"] = {}
    if not isinstance(data["agents"].get("defaults"), dict):
        data["agents"]["defaults"] = {}
    data["agents"]["defaults"]["model_name"] = "metaclaw"

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("[ClawAdapter] PicoClaw config updated: %s", config_path)
    except Exception as e:
        logger.error("[ClawAdapter] Failed to write %s: %s", config_path, e)
        return

    _run_commands(
        "picoclaw",
        [["picoclaw", "gateway", "restart"]],
        ignore_missing=True,
    )


# ------------------------------------------------------------------ #
# ZeroClaw adapter                                                     #
# ------------------------------------------------------------------ #

def _configure_zeroclaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure ZeroClaw to use the MetaClaw proxy.

    Patches ``~/.zeroclaw/config.toml`` to set the provider to
    ``openai-compatible`` pointing at the MetaClaw proxy.  Falls back to
    a simple line-based patcher to avoid a hard dependency on a TOML
    write library.
    """
    config_path = Path.home() / ".zeroclaw" / "config.toml"
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"

    new_vars = {
        "provider": "openai-compatible",
        "model": model_id,
        "api_key": cfg.proxy_api_key or "metaclaw",
        "base_url": f"http://127.0.0.1:{cfg.proxy_port}/v1",
    }

    _patch_toml(config_path, new_vars)

    _run_commands(
        "zeroclaw",
        [["zeroclaw", "service", "restart"]],
        ignore_missing=True,
    )


def _patch_toml(toml_path: Path, new_vars: dict[str, str]) -> None:
    """Update or insert key = "value" lines in a TOML file.

    This is a minimal line-based patcher (no full TOML parser required).
    It handles simple ``key = "value"`` pairs at the top level.  Existing
    keys are updated in-place; missing keys are appended.
    """
    lines: list[str] = []
    if toml_path.exists():
        try:
            lines = toml_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            logger.warning("[ClawAdapter] Failed to read %s: %s", toml_path, e)

    updated: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in new_vars:
            new_lines.append(f'{key} = "{new_vars[key]}"')
            updated.add(key)
        else:
            new_lines.append(line)

    for key, val in new_vars.items():
        if key not in updated:
            new_lines.append(f'{key} = "{val}"')

    try:
        toml_path.parent.mkdir(parents=True, exist_ok=True)
        toml_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        logger.info("[ClawAdapter] ZeroClaw config.toml updated: %s", toml_path)
    except Exception as e:
        logger.error("[ClawAdapter] Failed to write %s: %s", toml_path, e)


# ------------------------------------------------------------------ #
# Noop adapter                                                        #
# ------------------------------------------------------------------ #

def _configure_none(cfg: "MetaClawConfig") -> None:
    logger.info("[ClawAdapter] claw_type=none — skipping auto-configuration")


# ------------------------------------------------------------------ #
# Registry                                                            #
# ------------------------------------------------------------------ #

_ADAPTERS: dict[str, Callable[["MetaClawConfig"], None]] = {
    "openclaw": _configure_openclaw,
    "copaw": _configure_copaw,
    "ironclaw": _configure_ironclaw,
    "picoclaw": _configure_picoclaw,
    "zeroclaw": _configure_zeroclaw,
    "none": _configure_none,
}

# Canonical list of supported claw types (for CLI choices / wizard).
CLAW_TYPES: list[str] = list(_ADAPTERS)


# ------------------------------------------------------------------ #
# Shared helper                                                       #
# ------------------------------------------------------------------ #

def _run_commands(
    agent_name: str,
    commands: list[list[str]],
    ignore_missing: bool = False,
) -> None:
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.warning(
                    "[ClawAdapter] %s command failed: %s\n  stderr: %s",
                    agent_name,
                    " ".join(cmd),
                    result.stderr.strip(),
                )
            else:
                logger.info("[ClawAdapter] %s → ok", " ".join(cmd[:4]))
        except FileNotFoundError:
            if ignore_missing:
                logger.debug(
                    "[ClawAdapter] '%s' not found in PATH — skipping restart step",
                    cmd[0],
                )
            else:
                logger.warning(
                    "[ClawAdapter] '%s' not found in PATH — skipping auto-config. "
                    "Configure %s manually.",
                    cmd[0],
                    agent_name,
                )
            break
        except Exception as e:
            logger.warning("[ClawAdapter] %s command error: %s", agent_name, e)
