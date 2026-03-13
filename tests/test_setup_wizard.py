from pathlib import Path

from metaclaw.config_store import ConfigStore
from metaclaw.setup_wizard import SetupWizard


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
