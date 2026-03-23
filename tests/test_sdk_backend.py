import types

import pytest

from metaclaw.config import MetaClawConfig
from metaclaw.sdk_backend import (
    _backend_env_order,
    resolve_api_key,
    resolve_base_url,
    resolve_sdk_backend,
)


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


# ------------------------------------------------------------------ #
# Weaver backend tests                                                 #
# ------------------------------------------------------------------ #


def test_resolve_sdk_backend_explicit_weaver(monkeypatch):
    weaver_compat = types.SimpleNamespace(__name__="metaclaw.weaver_compat")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("weaver"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: weaver_compat if name == "metaclaw.weaver_compat" else None,
    )

    backend = resolve_sdk_backend(
        MetaClawConfig(
            backend="weaver",
            api_key="sk-weaver-test-123",
            base_url="https://weaver-console.nex-agi.cn",
        )
    )

    assert backend.key == "weaver"
    assert backend.label == "Weaver"
    assert backend.module is weaver_compat
    assert backend.api_key == "sk-weaver-test-123"
    assert backend.base_url == "https://weaver-console.nex-agi.cn"


def test_auto_detects_weaver_from_env(monkeypatch):
    weaver_compat = types.SimpleNamespace(__name__="metaclaw.weaver_compat")
    monkeypatch.setenv("WEAVER_API_KEY", "sk-from-env")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("weaver", "tinker"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: weaver_compat if name == "metaclaw.weaver_compat" else None,
    )

    backend = resolve_sdk_backend(MetaClawConfig(backend="auto"))

    assert backend.key == "weaver"
    assert backend.label == "Weaver"


def test_auto_detects_weaver_from_url(monkeypatch):
    weaver_compat = types.SimpleNamespace(__name__="metaclaw.weaver_compat")
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("weaver", "tinker"),
    )
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.import_module",
        lambda name: weaver_compat if name == "metaclaw.weaver_compat" else None,
    )

    backend = resolve_sdk_backend(
        MetaClawConfig(
            backend="auto",
            base_url="https://weaver-console.nex-agi.cn",
        )
    )

    assert backend.key == "weaver"


def test_explicit_weaver_requires_sdk(monkeypatch):
    monkeypatch.setattr(
        "metaclaw.sdk_backend.importlib.util.find_spec",
        _fake_find_spec_factory("tinker"),  # weaver NOT available
    )

    with pytest.raises(RuntimeError, match="nex-weaver"):
        resolve_sdk_backend(
            MetaClawConfig(
                backend="weaver",
                api_key="sk-weaver-123",
                base_url="https://weaver-console.nex-agi.cn",
            )
        )


def test_weaver_env_order():
    assert _backend_env_order("api_key", "weaver") == ("WEAVER_API_KEY", "TINKER_API_KEY")
    assert _backend_env_order("base_url", "weaver") == ("WEAVER_BASE_URL", "TINKER_BASE_URL")
