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
