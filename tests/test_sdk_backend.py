import types

import pytest

from metaclaw.config import MetaClawConfig
from metaclaw.sdk_backend import resolve_api_key, resolve_base_url, resolve_sdk_backend


def _fake_find_spec_factory(*available_names):
    available = set(available_names)
    return lambda name: object() if name in available else None


def test_resolve_sdk_backend_explicit_mint(monkeypatch):
    mint_module = types.SimpleNamespace(__name__="mint")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mint"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: mint_module if name == "mint" else None,
    )

    backend = resolve_sdk_backend(
        MetaClawConfig(
            backend="mint",
            api_key="sk-mint-123",
            base_url="https://mint.macaron.xin/",
        )
    )

    assert backend.key == "mint"
    assert backend.label == "MinT"
    assert backend.module is mint_module
    assert backend.api_key == "sk-mint-123"
    assert backend.base_url == "https://mint.macaron.xin/"


def test_resolve_sdk_backend_explicit_tinker(monkeypatch):
    tinker_module = types.SimpleNamespace(__name__="tinker")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("tinker"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: tinker_module if name == "tinker" else None,
    )

    backend = resolve_sdk_backend(
        MetaClawConfig(
            backend="tinker",
            api_key="sk-tinker-123",
            base_url="https://api.tinker.example/v1",
        )
    )

    assert backend.key == "tinker"
    assert backend.label == "Tinker"
    assert backend.module is tinker_module


def test_auto_prefers_mint_when_signaled_and_importable(monkeypatch):
    mint_module = types.SimpleNamespace(__name__="mint")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("mint", "tinker"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: mint_module if name == "mint" else None,
    )

    backend = resolve_sdk_backend(
        MetaClawConfig(
            backend="auto",
            api_key="sk-mint-123",
            base_url="https://mint.macaron.xin/",
        )
    )

    assert backend.key == "mint"


def test_auto_falls_back_to_tinker_when_mint_missing(monkeypatch):
    tinker_module = types.SimpleNamespace(__name__="tinker")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("tinker"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: tinker_module if name == "tinker" else None,
    )

    backend = resolve_sdk_backend(
        MetaClawConfig(
            backend="auto",
            api_key="sk-mint-123",
            base_url="https://mint.macaron.xin/",
        )
    )

    assert backend.key == "tinker"
    assert backend.module is tinker_module


def test_neutral_rl_keys_override_legacy_aliases():
    cfg = MetaClawConfig(
        api_key="neutral-key",
        base_url="https://neutral.example/v1",
        tinker_api_key="legacy-key",
        tinker_base_url="https://legacy.example/v1",
    )

    assert resolve_api_key(cfg, "mint") == "neutral-key"
    assert resolve_base_url(cfg, "mint") == "https://neutral.example/v1"


def test_legacy_aliases_still_resolve_when_neutral_absent():
    cfg = MetaClawConfig(
        tinker_api_key="legacy-key",
        tinker_base_url="https://legacy.example/v1",
    )

    assert resolve_api_key(cfg, "tinker") == "legacy-key"
    assert resolve_base_url(cfg, "tinker") == "https://legacy.example/v1"


def test_explicit_mint_requires_compat_package(monkeypatch):
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("tinker"),
    )

    with pytest.raises(RuntimeError, match="mindlab-toolkit"):
        resolve_sdk_backend(
            MetaClawConfig(
                backend="mint",
                api_key="sk-mint-123",
                base_url="https://mint.macaron.xin/",
            )
        )
