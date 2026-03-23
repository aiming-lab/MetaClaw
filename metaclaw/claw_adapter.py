"""
Claw adapter: auto-configures the active CLI agent to use the MetaClaw proxy.

Supported agents:
  openclaw  — runs `openclaw config set …` + `openclaw gateway restart`
  copaw     — patches ~/.copaw/config.json, triggers daemon hot-reload
  ironclaw  — patches ~/.ironclaw/.env, runs `ironclaw service restart`
  picoclaw  — patches ~/.picoclaw/config.json model_list, runs `picoclaw gateway restart`
  zeroclaw  — patches ~/.zeroclaw/config.toml, runs `zeroclaw service restart`
  nanoclaw  — patches nanoclaw's .env (ANTHROPIC_BASE_URL), restarts via launchd/systemd
  nemoclaw  — registers metaclaw provider in OpenShell, sets inference route
  hermes    — patches ~/.hermes/config.yaml custom_providers, runs `hermes gateway restart`
  none      — skip auto-configuration entirely

Add more claws by implementing a `_configure_<name>` function and registering
it in ``_ADAPTERS``.
"""

from __future__ import annotations

import datetime
import json
import logging
import platform
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
    """Auto-configure OpenClaw to use the MetaClaw proxy.

    Uses the ``anthropic-messages`` API format so that OpenClaw's plugin hook
    system (``before_prompt_build``) correctly populates ``event.rawMessage``.
    This is required for memory plugins such as Hindsight, mem0, and
    memory-lancedb to perform auto-recall.  MetaClaw exposes a full
    Anthropic-compatible ``/v1/messages`` endpoint, so tool calls, streaming,
    and all other agent features continue to work unchanged.
    """
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"

    # Resolve the context window to advertise to OpenClaw.
    # cfg.context_window == 0 means "auto": use a large window in skills_only
    # mode (no RL backend → no sequence-length constraint) and a conservative
    # window in rl/madmax mode (must fit Tinker/MinT training budget).
    _explicit_cw = getattr(cfg, "context_window", 0)
    if _explicit_cw > 0:
        context_window = _explicit_cw
    elif getattr(cfg, "mode", "madmax") == "skills_only":
        context_window = 200000
    else:
        context_window = 32768

    # Use anthropic-messages API format — OpenClaw appends /v1/messages to
    # baseUrl, so the base must not include the /v1 path segment.
    provider_json = json.dumps({
        "api": "anthropic-messages",
        "baseUrl": f"http://127.0.0.1:{cfg.proxy_port}",
        "apiKey": cfg.proxy_api_key or "metaclaw",
        "models": [{
            "id": model_id,
            "name": model_id,
            "reasoning": False,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": context_window,
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


def _patch_dotenv(env_path: Path, new_vars: dict[str, str], label: str = "IronClaw") -> None:
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
        logger.info("[ClawAdapter] %s .env updated: %s", label, env_path)
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
# NanoClaw adapter                                                    #
# ------------------------------------------------------------------ #

def _configure_nanoclaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure NanoClaw to route API calls through MetaClaw proxy.

    NanoClaw uses an Anthropic-compatible credential proxy (credential-proxy.ts)
    that forwards container API calls to ANTHROPIC_BASE_URL.  MetaClaw exposes
    a /v1/messages Anthropic-compatible endpoint, so we point ANTHROPIC_BASE_URL
    at the MetaClaw proxy and restart the service.

    Config file location is discovered in priority order:
      1. WorkingDirectory from ~/Library/LaunchAgents/com.nanoclaw.plist (macOS)
      2. WorkingDirectory from ~/.config/systemd/user/nanoclaw.service (Linux)
      3. Common install locations: ~/nanoclaw, ~/code/nanoclaw, ~/.nanoclaw
    """
    env_path = _find_nanoclaw_env()
    if env_path is None:
        logger.warning(
            "[ClawAdapter] Could not locate nanoclaw .env — "
            "set ANTHROPIC_BASE_URL=http://127.0.0.1:%d and "
            "ANTHROPIC_API_KEY=%s in nanoclaw's .env manually.",
            cfg.proxy_port,
            cfg.proxy_api_key or "metaclaw",
        )
        return

    new_vars = {
        "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{cfg.proxy_port}",
        "ANTHROPIC_API_KEY": cfg.proxy_api_key or "metaclaw",
    }
    _patch_dotenv(env_path, new_vars, label="NanoClaw")

    # Restart nanoclaw via launchd (macOS) or systemd --user (Linux)
    if platform.system() == "Darwin":
        import os
        uid = os.getuid()
        _run_commands(
            "nanoclaw",
            [["launchctl", "kickstart", "-k", f"gui/{uid}/com.nanoclaw"]],
            ignore_missing=True,
        )
    else:
        _run_commands(
            "nanoclaw",
            [["systemctl", "--user", "restart", "nanoclaw"]],
            ignore_missing=True,
        )


def _find_nanoclaw_env() -> Path | None:
    """Locate nanoclaw's project-root .env file by probing known locations."""
    home = Path.home()

    # 1. macOS launchd plist → WorkingDirectory
    plist_path = home / "Library" / "LaunchAgents" / "com.nanoclaw.plist"
    if plist_path.exists():
        try:
            import plistlib
            with open(plist_path, "rb") as f:
                plist = plistlib.load(f)
            work_dir = plist.get("WorkingDirectory")
            if work_dir:
                candidate = Path(work_dir) / ".env"
                if candidate.parent.is_dir():
                    return candidate
        except Exception as e:
            logger.debug("[ClawAdapter] failed to parse nanoclaw plist: %s", e)

    # 2. Linux systemd service → WorkingDirectory=
    service_path = home / ".config" / "systemd" / "user" / "nanoclaw.service"
    if service_path.exists():
        try:
            for line in service_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("WorkingDirectory="):
                    work_dir = stripped.split("=", 1)[1].strip()
                    candidate = Path(work_dir) / ".env"
                    if candidate.parent.is_dir():
                        return candidate
        except Exception as e:
            logger.debug("[ClawAdapter] failed to parse nanoclaw service file: %s", e)

    # 3. Common install locations (check for existing .env or at least the dir)
    for candidate in [
        home / "nanoclaw" / ".env",
        home / "code" / "nanoclaw" / ".env",
        home / ".nanoclaw" / ".env",
    ]:
        if candidate.exists() or candidate.parent.is_dir():
            return candidate

    return None


# ------------------------------------------------------------------ #
# NemoClaw adapter                                                    #
# ------------------------------------------------------------------ #

def _configure_nemoclaw(cfg: "MetaClawConfig") -> None:
    """Auto-configure NemoClaw to route inference through MetaClaw proxy.

    NemoClaw runs OpenClaw inside an OpenShell sandbox with a pluggable
    inference provider.  We register (or update) a 'metaclaw' OpenAI-compatible
    provider via the openshell CLI and set it as the active inference route.
    The config is also persisted to ~/.nemoclaw/config.json so that
    `openclaw nemoclaw status` reflects the current state.
    """
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"
    api_key = cfg.proxy_api_key or "metaclaw"
    base_url = f"http://127.0.0.1:{cfg.proxy_port}/v1"

    # Step 1: Register (or update) the metaclaw provider in OpenShell
    create_cmd = [
        "openshell", "provider", "create",
        "--name", "metaclaw",
        "--type", "openai",
        "--credential", f"OPENAI_API_KEY={api_key}",
        "--config", f"OPENAI_BASE_URL={base_url}",
    ]
    try:
        result = subprocess.run(
            create_cmd, capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            stderr = result.stderr or ""
            if "AlreadyExists" in stderr or "already exists" in stderr.lower():
                logger.info("[ClawAdapter] openshell provider 'metaclaw' exists — updating")
                _run_commands("nemoclaw", [[
                    "openshell", "provider", "update", "metaclaw",
                    "--credential", f"OPENAI_API_KEY={api_key}",
                    "--config", f"OPENAI_BASE_URL={base_url}",
                ]])
            else:
                logger.warning(
                    "[ClawAdapter] openshell provider create failed: %s",
                    stderr.strip(),
                )
                return
        else:
            logger.info("[ClawAdapter] openshell provider create metaclaw → ok")
    except FileNotFoundError:
        logger.warning(
            "[ClawAdapter] 'openshell' not found in PATH — configure NemoClaw manually."
        )
        return
    except Exception as e:
        logger.warning("[ClawAdapter] openshell provider create error: %s", e)
        return

    # Step 2: Set inference route to the metaclaw provider
    _run_commands("nemoclaw", [[
        "openshell", "inference", "set",
        "--provider", "metaclaw",
        "--model", model_id,
    ]])

    # Step 3: Persist ~/.nemoclaw/config.json
    _write_nemoclaw_config(base_url, model_id, api_key)

    # Step 4: Restart openclaw gateway inside the sandbox (best-effort)
    _run_commands("nemoclaw", [["openclaw", "gateway", "restart"]], ignore_missing=True)


def _write_nemoclaw_config(endpoint_url: str, model: str, api_key: str) -> None:
    """Write ~/.nemoclaw/config.json to record MetaClaw as the active provider."""
    config_path = Path.home() / ".nemoclaw" / "config.json"
    data = {
        "endpointType": "custom",
        "endpointUrl": endpoint_url,
        "ncpPartner": None,
        "model": model,
        "profile": "ncp",
        "credentialEnv": "OPENAI_API_KEY",
        "onboardedAt": datetime.datetime.utcnow().isoformat() + "Z",
    }
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("[ClawAdapter] NemoClaw config updated: %s", config_path)
    except Exception as e:
        logger.error("[ClawAdapter] Failed to write %s: %s", config_path, e)


# ------------------------------------------------------------------ #
# Hermes adapter                                                      #
# ------------------------------------------------------------------ #

def _configure_hermes(cfg: "MetaClawConfig") -> None:
    """Auto-configure Hermes Agent to use the MetaClaw proxy.

    Injects a ``metaclaw`` entry into ``~/.hermes/config.yaml``
    ``custom_providers`` list and sets it as the active model provider via
    ``model.provider``.  Attempts a gateway restart so the change takes
    effect immediately without manual intervention.

    Config file location respects the ``HERMES_HOME`` environment variable
    (defaults to ``~/.hermes``).
    """
    try:
        import yaml as _yaml
    except ImportError:
        logger.warning(
            "[ClawAdapter] PyYAML not available — configure Hermes manually. "
            "Add a custom provider with base_url=http://127.0.0.1:%d/v1 "
            "in ~/.hermes/config.yaml.",
            cfg.proxy_port,
        )
        return

    import os as _os
    hermes_home = Path(_os.getenv("HERMES_HOME", "") or Path.home() / ".hermes")
    config_path = hermes_home / "config.yaml"
    model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"
    base_url = f"http://127.0.0.1:{cfg.proxy_port}/v1"
    api_key = cfg.proxy_api_key or "metaclaw"

    # Resolve context window (same logic as _configure_openclaw).
    _explicit_cw = getattr(cfg, "context_window", 0)
    if _explicit_cw > 0:
        context_window = _explicit_cw
    elif getattr(cfg, "mode", "madmax") == "skills_only":
        context_window = 200000
    else:
        context_window = 32768

    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as fh:
                data = _yaml.safe_load(fh) or {}
        except Exception as e:
            logger.warning("[ClawAdapter] Failed to read %s: %s", config_path, e)

    # Upsert the metaclaw entry in custom_providers (deduplicate by name).
    providers = data.get("custom_providers")
    if not isinstance(providers, list):
        providers = []
    providers = [p for p in providers if not (isinstance(p, dict) and p.get("name") == "metaclaw")]
    providers.append({
        "name": "metaclaw",
        "base_url": base_url,
        "api_key": api_key,
        "models": {model_id: {"context_length": context_window}},
    })
    data["custom_providers"] = providers

    # Set metaclaw as the active provider and model.
    model_cfg = data.get("model")
    if not isinstance(model_cfg, dict):
        model_cfg = {}
    model_cfg["provider"] = "custom:metaclaw"
    model_cfg["default"] = model_id
    data["model"] = model_cfg

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as fh:
            _yaml.dump(data, fh, default_flow_style=False, sort_keys=False)
        logger.info("[ClawAdapter] Hermes config updated: %s", config_path)
    except Exception as e:
        logger.error("[ClawAdapter] Failed to write %s: %s", config_path, e)
        return

    # Restart the Hermes gateway if it is running so the new provider takes
    # effect immediately (best-effort; ignored if hermes is not in PATH).
    _run_commands("hermes", [["hermes", "gateway", "restart"]], ignore_missing=True)


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
    "nanoclaw": _configure_nanoclaw,
    "nemoclaw": _configure_nemoclaw,
    "hermes": _configure_hermes,
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
