import json
import os
from pathlib import Path
from types import SimpleNamespace

from metaclaw.config import MetaClawConfig
from metaclaw.config_store import ConfigStore
from metaclaw.launcher import MetaClawLauncher


def test_seed_rl_backend_env_sets_both_alias_families(monkeypatch):
    launcher = MetaClawLauncher(ConfigStore())
    for name in ("TINKER_API_KEY", "MINT_API_KEY", "TINKER_BASE_URL", "MINT_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    launcher._seed_rl_backend_env(
        MetaClawConfig(
            api_key="sk-test-123",
            base_url="https://mint.macaron.xin/",
        )
    )

    assert os.environ["TINKER_API_KEY"] == "sk-test-123"
    assert os.environ["MINT_API_KEY"] == "sk-test-123"
    assert os.environ["TINKER_BASE_URL"] == "https://mint.macaron.xin/"
    assert os.environ["MINT_BASE_URL"] == "https://mint.macaron.xin/"


def test_seed_rl_backend_env_preserves_existing_values(monkeypatch):
    launcher = MetaClawLauncher(ConfigStore())
    monkeypatch.setenv("TINKER_API_KEY", "existing-key")
    monkeypatch.setenv("MINT_BASE_URL", "https://existing.example/v1")
    monkeypatch.delenv("MINT_API_KEY", raising=False)
    monkeypatch.delenv("TINKER_BASE_URL", raising=False)

    launcher._seed_rl_backend_env(
        MetaClawConfig(
            api_key="new-key",
            base_url="https://new.example/v1",
        )
    )

    assert os.environ["TINKER_API_KEY"] == "existing-key"
    assert os.environ["MINT_API_KEY"] == "new-key"
    assert os.environ["MINT_BASE_URL"] == "https://existing.example/v1"
    assert os.environ["TINKER_BASE_URL"] == "https://new.example/v1"


def test_configure_openclaw_uses_proxy_api_key_not_rl_api_key(monkeypatch):
    launcher = MetaClawLauncher(ConfigStore())
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("metaclaw.launcher.subprocess.run", fake_run)

    launcher._configure_openclaw(
        MetaClawConfig(
            api_key="rl-backend-key",
            proxy_api_key="proxy-key",
            llm_model_id="test-model",
            served_model_name="served-model",
            proxy_port=31000,
        )
    )

    provider_cmd = calls[0]
    provider_json = json.loads(provider_cmd[-1])
    assert provider_json["apiKey"] == "proxy-key"


def test_config_store_prefers_neutral_rl_keys(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    store = ConfigStore(config_file=config_path)
    store.save(
        {
            "mode": "rl",
            "proxy": {"port": 31000, "api_key": "proxy-key"},
            "llm": {"model_id": "served-model"},
            "rl": {
                "enabled": True,
                "backend": "mint",
                "api_key": "neutral-key",
                "base_url": "https://mint.macaron.xin/",
                "tinker_api_key": "legacy-key",
                "tinker_base_url": "https://legacy.example/v1",
            },
        }
    )

    cfg = store.to_metaclaw_config()

    assert cfg.backend == "mint"
    assert cfg.api_key == "neutral-key"
    assert cfg.base_url == "https://mint.macaron.xin/"
    assert cfg.proxy_api_key == "proxy-key"
