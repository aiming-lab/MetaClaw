"""
Runtime backend selection for RL SDK clients.

MetaClaw can talk to:
  - ``tinker`` directly
  - ``mint`` via the MindLab compatibility package
  - ``weaver`` via the metaclaw.weaver_compat adapter
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from .config import MetaClawConfig

_VALID_BACKENDS = {"auto", "tinker", "mint", "weaver"}
_BACKEND_LABELS = {"tinker": "Tinker", "mint": "MinT", "weaver": "Weaver"}


@dataclass(frozen=True)
class SDKBackend:
    key: str
    label: str
    import_name: str
    module: Any
    api_key: str
    base_url: str

    @property
    def banner(self) -> str:
        return f"{self.label} cloud RL"


def _first_non_empty(*values: str) -> str:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return ""


def _first_env(*names: str) -> str:
    return _first_non_empty(*(os.environ.get(name, "") for name in names))


def _normalize_backend_name(value: str | None) -> str:
    normalized = (value or "auto").strip().lower()
    if normalized not in _VALID_BACKENDS:
        raise ValueError(
            f"Invalid RL backend {value!r}; expected one of {sorted(_VALID_BACKENDS)}"
        )
    return normalized


def configured_backend_name(config: "MetaClawConfig") -> str:
    return _normalize_backend_name(getattr(config, "backend", "auto"))


def configured_api_key(config: "MetaClawConfig") -> str:
    return _first_non_empty(
        getattr(config, "api_key", ""),
        getattr(config, "tinker_api_key", ""),
    )


def configured_base_url(config: "MetaClawConfig") -> str:
    return _first_non_empty(
        getattr(config, "base_url", ""),
        getattr(config, "tinker_base_url", ""),
    )


def _backend_env_order(kind: str, backend_key: str) -> tuple[str, ...]:
    if kind not in {"api_key", "base_url"}:
        raise ValueError(f"Unknown backend env kind: {kind}")
    suffix = "API_KEY" if kind == "api_key" else "BASE_URL"
    if backend_key == "weaver":
        return (f"WEAVER_{suffix}", f"TINKER_{suffix}")
    if backend_key == "mint":
        return (f"MINT_{suffix}", f"TINKER_{suffix}")
    return (f"TINKER_{suffix}", f"MINT_{suffix}")


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _looks_like_mint_api_key(value: str) -> bool:
    return value.strip().startswith("sk-mint-")


def _looks_like_mint_base_url(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    return "mint" in urlparse(candidate).netloc.lower()


def _has_weaver_signal(config: "MetaClawConfig") -> bool:
    if _first_env("WEAVER_API_KEY", "WEAVER_BASE_URL"):
        return True

    url_candidates = (
        configured_base_url(config),
        os.environ.get("TINKER_BASE_URL", ""),
    )
    return any(
        "weaver" in urlparse(u.strip()).netloc.lower()
        for u in url_candidates
        if u.strip()
    )


def _has_mint_signal(config: "MetaClawConfig") -> bool:
    if _first_env("MINT_API_KEY", "MINT_BASE_URL"):
        return True

    key_candidates = (
        configured_api_key(config),
        os.environ.get("TINKER_API_KEY", ""),
    )
    if any(_looks_like_mint_api_key(value) for value in key_candidates):
        return True

    url_candidates = (
        configured_base_url(config),
        os.environ.get("TINKER_BASE_URL", ""),
    )
    return any(_looks_like_mint_base_url(value) for value in url_candidates)


def infer_backend_key(config: "MetaClawConfig") -> str:
    configured = configured_backend_name(config)
    if configured in {"tinker", "mint", "weaver"}:
        return configured
    if _has_weaver_signal(config) and _module_available("weaver"):
        return "weaver"
    if _has_mint_signal(config) and _module_available("mint"):
        return "mint"
    return "tinker"


def resolve_api_key(config: "MetaClawConfig", backend_key: str | None = None) -> str:
    configured = configured_api_key(config)
    if configured:
        return configured
    key = backend_key or infer_backend_key(config)
    return _first_env(*_backend_env_order("api_key", key))


def resolve_base_url(config: "MetaClawConfig", backend_key: str | None = None) -> str:
    configured = configured_base_url(config)
    if configured:
        return configured
    key = backend_key or infer_backend_key(config)
    return _first_env(*_backend_env_order("base_url", key))


def _import_backend_module(backend_key: str, configured_backend: str):
    if backend_key == "weaver":
        if configured_backend == "weaver" and not _module_available("weaver"):
            raise RuntimeError(
                "rl.backend=weaver requires the nex-weaver SDK. "
                "Install 'nex-weaver' in this environment or switch rl.backend to auto/tinker."
            )
        return importlib.import_module("metaclaw.weaver_compat")
    if backend_key == "mint" and configured_backend == "mint" and not _module_available("mint"):
        raise RuntimeError(
            "rl.backend=mint requires the MinT compatibility package. "
            "Install 'mindlab-toolkit' in this environment or switch rl.backend to auto/tinker."
        )
    return importlib.import_module(backend_key)


def resolve_sdk_backend(config: "MetaClawConfig") -> SDKBackend:
    configured = configured_backend_name(config)
    key = infer_backend_key(config)
    module = _import_backend_module(key, configured)
    return SDKBackend(
        key=key,
        label=_BACKEND_LABELS[key],
        import_name=key,
        module=module,
        api_key=resolve_api_key(config, key),
        base_url=resolve_base_url(config, key),
    )
