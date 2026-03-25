"""
Spawn the Node WeChat bridge (weixin-agent-sdk) that talks to the MetaClaw proxy.

Requires: Node.js on PATH and ``npm install`` inside ``metaclaw/wechat_node/``.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .config import MetaClawConfig

logger = logging.getLogger(__name__)


def _package_bridge_dir() -> Path:
    return Path(__file__).resolve().parent / "wechat_node"


def resolve_wechat_bridge_dir(cfg: "MetaClawConfig") -> Path:
    raw = (cfg.wechat_bridge_dir or "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
        if p.is_dir():
            return p
        logger.warning("[WeChat] wechat.bridge_dir is not a directory: %s — using bundled bridge", raw)
    return _package_bridge_dir()


def wechat_bridge_dependency_issues(cfg: "MetaClawConfig") -> tuple[Path, list[str]]:
    """Return ``(bridge_dir, issues)``. Empty ``issues`` means Node bridge can be spawned."""
    root = resolve_wechat_bridge_dir(cfg)
    bridge_js = root / "bridge.mjs"
    sdk = root / "node_modules" / "weixin-agent-sdk"
    issues: list[str] = []
    if not bridge_js.is_file():
        issues.append(f"missing {bridge_js}")
    if not sdk.is_dir():
        issues.append(f"weixin-agent-sdk missing — cd {root} && npm install")
    return root, issues


def spawn_wechat_bridge(
    cfg: "MetaClawConfig",
    *,
    relogin: bool = False,
) -> Optional[subprocess.Popen]:
    """Start ``node bridge.mjs`` if dependencies are installed. Returns None on skip/failure.

    ``relogin=True`` forces a QR login for this run (switch account / refresh token); normal
    ``metaclaw start`` always tries the saved session first.
    """
    root, issues = wechat_bridge_dependency_issues(cfg)
    if issues:
        for line in issues:
            logger.warning("[WeChat] %s", line)
        return None
    bridge_js = root / "bridge.mjs"

    model_id = (cfg.llm_model_id or cfg.served_model_name or "metaclaw-model").strip()
    api_key = (cfg.api_key or "metaclaw").strip()
    base_url = f"http://127.0.0.1:{cfg.proxy_port}/v1"

    env = os.environ.copy()
    env["METACLAW_OPENAI_BASE"] = base_url
    env["METACLAW_MODEL"] = model_id
    env["METACLAW_API_KEY"] = api_key
    if relogin:
        env["METACLAW_WECHAT_FORCE_LOGIN"] = "1"

    try:
        proc = subprocess.Popen(
            ["node", str(bridge_js)],
            cwd=str(root),
            env=env,
            stdin=subprocess.DEVNULL,
            # Inherit stdout/stderr so the user sees the WeChat QR code in the same terminal.
        )
    except FileNotFoundError:
        logger.warning("[WeChat] 'node' not found on PATH — install Node.js to use WeChat bridge")
        return None
    except Exception as exc:
        logger.warning("[WeChat] failed to spawn bridge: %s", exc)
        return None

    if relogin:
        logger.info(
            "[WeChat] bridge started (pid=%s) → %s model=%s — relogin: scan QR in this terminal",
            proc.pid,
            base_url,
            model_id,
        )
    else:
        logger.info(
            "[WeChat] bridge started (pid=%s) → %s model=%s — reusing saved login if any (else QR here)",
            proc.pid,
            base_url,
            model_id,
        )
    return proc


def terminate_wechat_bridge(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    except Exception as exc:
        logger.debug("[WeChat] terminate: %s", exc)
