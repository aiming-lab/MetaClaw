"""Unit tests for the MLX backend integration into sdk_backend.py.

Mirrors the patterns in test_sdk_backend.py. All tests mock external
modules so they run on any platform (no Apple Silicon required).

Requires: the modified metaclaw/sdk_backend.py with MLX support.
"""

from __future__ import annotations

import types
import pytest
from unittest.mock import MagicMock

from metaclaw.sdk_backend import (
    SDKBackend,
    _normalize_backend_name,
    infer_backend_key,
    resolve_api_key,
    resolve_base_url,
    resolve_sdk_backend,
)


# ------------------------------------------------------------------ #
# Helpers (same pattern as test_sdk_backend.py)                      #
# ------------------------------------------------------------------ #

def _fake_find_spec_factory(*available):
    """Return a find_spec that reports *available* modules as importable."""
    def _find_spec(name):
        return MagicMock() if name in available else None
    return _find_spec


def _cfg(**overrides):
    """Build a minimal config namespace with sensible defaults."""
    defaults = dict(
        backend="auto",
        api_key="",
        base_url="",
        tinker_api_key="",
        tinker_base_url="",
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ------------------------------------------------------------------ #
# Validation                                                         #
# ------------------------------------------------------------------ #

def test_mlx_is_valid_backend_name():
    assert _normalize_backend_name("mlx") == "mlx"


def test_mlx_is_case_insensitive():
    assert _normalize_backend_name("MLX") == "mlx"
    assert _normalize_backend_name(" Mlx ") == "mlx"


# ------------------------------------------------------------------ #
# Explicit backend="mlx"                                             #
# ------------------------------------------------------------------ #

def test_resolve_sdk_backend_explicit_mlx(monkeypatch):
    mlx_module = types.SimpleNamespace(__name__="metaclaw.mlx_backend")

    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mlx", "mlx_lm"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: mlx_module if name == "metaclaw.mlx_backend" else None,
    )

    backend = resolve_sdk_backend(_cfg(backend="mlx"))

    assert backend.key == "mlx"
    assert backend.label == "MLX"
    assert backend.import_name == "metaclaw.mlx_backend"
    assert backend.module is mlx_module
    assert backend.api_key == ""
    assert backend.base_url == ""
    assert backend.banner == "MLX local RL"


def test_explicit_mlx_ignores_api_key():
    """MLX is local — api_key should always resolve to empty."""
    assert resolve_api_key(_cfg(backend="mlx", api_key="sk-should-ignore"), "mlx") == ""


def test_explicit_mlx_passes_base_url_as_model_path():
    """base_url can carry the MLX model path when set explicitly."""
    url = resolve_base_url(
        _cfg(backend="mlx", base_url="mlx-community/Qwen2.5-7B-4bit"), "mlx"
    )
    assert url == "mlx-community/Qwen2.5-7B-4bit"


# ------------------------------------------------------------------ #
# Auto-detection                                                     #
# ------------------------------------------------------------------ #

def test_auto_does_not_select_mlx_without_signal(monkeypatch):
    """Without env or config signal, auto should NOT pick MLX."""
    monkeypatch.delenv("METACLAW_RL_BACKEND", raising=False)
    monkeypatch.delenv("MINT_API_KEY", raising=False)
    monkeypatch.delenv("MINT_BASE_URL", raising=False)
    monkeypatch.delenv("TINKER_API_KEY", raising=False)
    monkeypatch.delenv("TINKER_BASE_URL", raising=False)

    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mlx", "mlx_lm", "tinker"),
    )

    assert infer_backend_key(_cfg()) == "tinker"


def test_auto_selects_mlx_when_env_set(monkeypatch):
    """METACLAW_RL_BACKEND=mlx should trigger MLX selection in auto mode."""
    monkeypatch.setenv("METACLAW_RL_BACKEND", "mlx")
    monkeypatch.delenv("MINT_API_KEY", raising=False)
    monkeypatch.delenv("MINT_BASE_URL", raising=False)
    monkeypatch.delenv("TINKER_API_KEY", raising=False)
    monkeypatch.delenv("TINKER_BASE_URL", raising=False)

    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mlx", "mlx_lm"),
    )

    assert infer_backend_key(_cfg()) == "mlx"


def test_auto_skips_mlx_when_mlx_lm_missing(monkeypatch):
    """If mlx is importable but mlx_lm is not, auto should skip MLX."""
    monkeypatch.setenv("METACLAW_RL_BACKEND", "mlx")
    monkeypatch.delenv("MINT_API_KEY", raising=False)
    monkeypatch.delenv("MINT_BASE_URL", raising=False)
    monkeypatch.delenv("TINKER_API_KEY", raising=False)
    monkeypatch.delenv("TINKER_BASE_URL", raising=False)

    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mlx", "tinker"),  # mlx_lm missing
    )

    # Should fall through to tinker since _mlx_available() is False
    assert infer_backend_key(_cfg()) == "tinker"


# ------------------------------------------------------------------ #
# Error handling                                                     #
# ------------------------------------------------------------------ #

def test_explicit_mlx_missing_deps_raises(monkeypatch):
    """backend=mlx without mlx/mlx_lm installed should raise RuntimeError."""
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("tinker"),  # no mlx at all
    )

    with pytest.raises(RuntimeError, match="Apple Silicon"):
        resolve_sdk_backend(_cfg(backend="mlx"))


# ------------------------------------------------------------------ #
# Priority: explicit > mlx > mint > tinker                          #
# ------------------------------------------------------------------ #

def test_explicit_mint_wins_over_mlx_env(monkeypatch):
    """Explicit backend=mint should override METACLAW_RL_BACKEND=mlx."""
    monkeypatch.setenv("METACLAW_RL_BACKEND", "mlx")

    assert infer_backend_key(_cfg(backend="mint")) == "mint"


def test_explicit_tinker_wins_over_mlx_env(monkeypatch):
    """Explicit backend=tinker should override METACLAW_RL_BACKEND=mlx."""
    monkeypatch.setenv("METACLAW_RL_BACKEND", "mlx")

    assert infer_backend_key(_cfg(backend="tinker")) == "tinker"


# ------------------------------------------------------------------ #
# Existing backends still work                                       #
# ------------------------------------------------------------------ #

def test_tinker_still_resolves(monkeypatch):
    tinker_module = types.SimpleNamespace(__name__="tinker")
    monkeypatch.delenv("METACLAW_RL_BACKEND", raising=False)
    monkeypatch.delenv("MINT_API_KEY", raising=False)
    monkeypatch.delenv("MINT_BASE_URL", raising=False)

    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("tinker"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: tinker_module if name == "tinker" else None,
    )

    backend = resolve_sdk_backend(
        _cfg(backend="tinker", api_key="sk-tinker-123", base_url="https://api.tinker.example/v1")
    )

    assert backend.key == "tinker"
    assert backend.module is tinker_module
    assert backend.api_key == "sk-tinker-123"
    assert backend.banner == "Tinker cloud RL"


def test_mint_still_resolves(monkeypatch):
    mint_module = types.SimpleNamespace(__name__="mint")
    monkeypatch.delenv("METACLAW_RL_BACKEND", raising=False)

    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mint"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: mint_module if name == "mint" else None,
    )

    backend = resolve_sdk_backend(
        _cfg(backend="mint", api_key="sk-mint-123", base_url="https://mint.macaron.xin/")
    )

    assert backend.key == "mint"
    assert backend.module is mint_module
    assert backend.api_key == "sk-mint-123"
    assert backend.banner == "MinT cloud RL"
