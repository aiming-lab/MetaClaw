from pathlib import Path

from metaclaw.config_store import ConfigStore
from metaclaw.setup_wizard import SetupWizard, _PROVIDER_PRESETS


def test_setup_wizard_preserves_existing_proxy_settings(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    skills_dir = tmp_path / "skills"
    store = ConfigStore(config_file=config_path)
    store.save(
        {
            "mode": "skills_only",
            "llm": {
                "provider": "custom",
                "model_id": "old-model",
                "api_base": "https://old.example/v1",
                "api_key": "old-llm-key",
            },
            "proxy": {
                "port": 30000,
                "host": "127.0.0.1",
                "api_key": "proxy-key",
                "trusted_local": True,
            },
            "skills": {
                "enabled": True,
                "dir": str(skills_dir),
                "retrieval_mode": "template",
                "top_k": 6,
                "task_specific_top_k": 10,
                "auto_evolve": True,
            },
            "rl": {"enabled": False},
        }
    )

    monkeypatch.setattr("metaclaw.setup_wizard.ConfigStore", lambda: store)

    def fake_prompt_choice(msg, choices, default=""):
        if msg == "Operating mode":
            return "skills_only"
        if msg == "LLM provider":
            return "custom"
        raise AssertionError(f"Unexpected choice prompt: {msg}")

    def fake_prompt(msg, default="", hide=False):
        if msg == "API base URL":
            return "https://new.example/v1"
        if msg == "Model ID":
            return "new-model"
        if msg == "API key":
            return "new-llm-key"
        if msg == "Skills directory":
            return str(skills_dir)
        raise AssertionError(f"Unexpected text prompt: {msg}")

    def fake_prompt_bool(msg, default=False):
        if msg == "Enable skill injection":
            return True
        if msg == "Auto-summarize skills after each conversation":
            return True
        raise AssertionError(f"Unexpected bool prompt: {msg}")

    def fake_prompt_int(msg, default=0):
        if msg == "Proxy port":
            return 32000
        raise AssertionError(f"Unexpected int prompt: {msg}")

    monkeypatch.setattr("metaclaw.setup_wizard._prompt_choice", fake_prompt_choice)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt", fake_prompt)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_bool", fake_prompt_bool)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_int", fake_prompt_int)

    SetupWizard().run()

    saved = store.load()
    assert saved["proxy"]["port"] == 32000
    assert saved["proxy"]["host"] == "127.0.0.1"
    assert saved["proxy"]["api_key"] == "proxy-key"
    assert saved["proxy"]["trusted_local"] is True


def test_novita_preset_defaults():
    """Novita preset should use the OpenAI-compatible endpoint and kimi-k2.5."""
    preset = _PROVIDER_PRESETS["novita"]
    assert preset["api_base"] == "https://api.novita.ai/openai"
    assert preset["model_id"] == "moonshotai/kimi-k2.5"


def test_novita_provider_fresh_setup(monkeypatch, tmp_path: Path):
    """Fresh setup with novita provider should save the correct endpoint and model."""
    config_path = tmp_path / "config.yaml"
    skills_dir = tmp_path / "skills"
    store = ConfigStore(config_file=config_path)

    monkeypatch.setattr("metaclaw.setup_wizard.ConfigStore", lambda: store)

    def fake_prompt_choice(msg, choices, default=""):
        if "agent" in msg.lower():
            return "openclaw"
        if msg == "Operating mode":
            return "skills_only"
        if msg == "LLM provider":
            return "novita"
        raise AssertionError(f"Unexpected choice prompt: {msg}")

    def fake_prompt(msg, default="", hide=False):
        if msg == "Skills directory":
            return str(skills_dir)
        return default

    def fake_prompt_bool(msg, default=False):
        return default

    def fake_prompt_int(msg, default=0):
        return default

    monkeypatch.setattr("metaclaw.setup_wizard._prompt_choice", fake_prompt_choice)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt", fake_prompt)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_bool", fake_prompt_bool)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_int", fake_prompt_int)

    SetupWizard().run()

    saved = store.load()
    assert saved["llm"]["provider"] == "novita"
    assert saved["llm"]["model_id"] == "moonshotai/kimi-k2.5"
    assert saved["llm"]["api_base"] == "https://api.novita.ai/openai"


def test_minimax_preset_defaults_to_m27():
    """MiniMax preset should default to MiniMax-M2.7."""
    preset = _PROVIDER_PRESETS["minimax"]
    assert preset["model_id"] == "MiniMax-M2.7"
    assert preset["api_base"] == "https://api.minimax.io/v1"


def test_minimax_provider_fresh_setup(monkeypatch, tmp_path: Path):
    """Fresh setup with minimax provider should default to MiniMax-M2.7."""
    config_path = tmp_path / "config.yaml"
    skills_dir = tmp_path / "skills"
    store = ConfigStore(config_file=config_path)
    # No existing config — simulates a fresh setup

    monkeypatch.setattr("metaclaw.setup_wizard.ConfigStore", lambda: store)

    def fake_prompt_choice(msg, choices, default=""):
        if "agent" in msg.lower():
            return "openclaw"
        if msg == "Operating mode":
            return "skills_only"
        if msg == "LLM provider":
            return "minimax"
        raise AssertionError(f"Unexpected choice prompt: {msg}")

    def fake_prompt(msg, default="", hide=False):
        if msg == "Skills directory":
            return str(skills_dir)
        return default

    def fake_prompt_bool(msg, default=False):
        return default

    def fake_prompt_int(msg, default=0):
        return default

    monkeypatch.setattr("metaclaw.setup_wizard._prompt_choice", fake_prompt_choice)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt", fake_prompt)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_bool", fake_prompt_bool)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_int", fake_prompt_int)

    SetupWizard().run()

    saved = store.load()
    assert saved["llm"]["provider"] == "minimax"
    assert saved["llm"]["model_id"] == "MiniMax-M2.7"
    assert saved["llm"]["api_base"] == "https://api.minimax.io/v1"
