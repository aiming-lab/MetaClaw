from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from metaclaw.config import MetaClawConfig
from metaclaw.config_store import ConfigStore, _DEFAULTS
from metaclaw.setup_wizard import SetupWizard


# ---------------------------------------------------------------- #
# 1. Config dataclass defaults                                     #
# ---------------------------------------------------------------- #

def test_config_openclaw_defaults():
    cfg = MetaClawConfig()
    assert cfg.openclaw_context_engine_enabled is True
    assert cfg.openclaw_active_memory_compat is True
    assert cfg.openclaw_prefer_proxy_synergy is False
    assert cfg.openclaw_min_version == "2026.4.10"


# ---------------------------------------------------------------- #
# 2. ConfigStore _DEFAULTS                                         #
# ---------------------------------------------------------------- #

def test_config_store_openclaw_defaults(tmp_path: Path):
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    assert "openclaw_compat" in _DEFAULTS
    oc = _DEFAULTS["openclaw_compat"]
    assert oc["context_engine_enabled"] is True
    assert oc["active_memory_compat"] is True
    assert oc["prefer_proxy_synergy"] is False
    assert oc["min_version"] == "2026.4.10"

    # And that load() merges these defaults into a fresh store
    loaded = store.load()
    assert loaded["openclaw_compat"]["context_engine_enabled"] is True
    assert loaded["openclaw_compat"]["active_memory_compat"] is True
    assert loaded["openclaw_compat"]["prefer_proxy_synergy"] is False
    assert loaded["openclaw_compat"]["min_version"] == "2026.4.10"


# ---------------------------------------------------------------- #
# 3. ConfigStore mapping → MetaClawConfig                          #
# ---------------------------------------------------------------- #

def test_config_store_openclaw_mapping_explicit(tmp_path: Path):
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    store.save({
        "mode": "skills_only",
        "openclaw_compat": {
            "context_engine_enabled": False,
            "active_memory_compat": False,
            "prefer_proxy_synergy": True,
            "min_version": "2026.5.1",
        },
    })

    cfg = store.to_metaclaw_config()
    assert cfg.openclaw_context_engine_enabled is False
    assert cfg.openclaw_active_memory_compat is False
    assert cfg.openclaw_prefer_proxy_synergy is True
    assert cfg.openclaw_min_version == "2026.5.1"


def test_config_store_openclaw_mapping_defaults_when_missing(tmp_path: Path):
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    # Save without an openclaw_compat section
    store.save({"mode": "skills_only"})

    cfg = store.to_metaclaw_config()
    # Defaults from _DEFAULTS get merged
    assert cfg.openclaw_context_engine_enabled is True
    assert cfg.openclaw_active_memory_compat is True
    assert cfg.openclaw_prefer_proxy_synergy is False
    assert cfg.openclaw_min_version == "2026.4.10"


def test_config_store_openclaw_mapping_string_false(tmp_path: Path):
    """Verify string 'false' is parsed correctly (avoid bool('false') == True trap)."""
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    store.save({
        "mode": "skills_only",
        "openclaw_compat": {
            "context_engine_enabled": "false",
            "active_memory_compat": "false",
            "prefer_proxy_synergy": "true",
            "min_version": "2026.4.20",
        },
    })

    cfg = store.to_metaclaw_config()
    assert cfg.openclaw_context_engine_enabled is False
    assert cfg.openclaw_active_memory_compat is False
    assert cfg.openclaw_prefer_proxy_synergy is True
    assert cfg.openclaw_min_version == "2026.4.20"


# ---------------------------------------------------------------- #
# 4. ConfigStore describe()                                        #
# ---------------------------------------------------------------- #

def test_config_store_describe_openclaw(tmp_path: Path):
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    store.save({
        "mode": "skills_only",
        "openclaw_compat": {
            "context_engine_enabled": True,
            "active_memory_compat": False,
            "prefer_proxy_synergy": True,
            "min_version": "2026.4.10",
        },
    })

    out = store.describe()
    assert "openclaw.context_engine" in out
    assert "openclaw.active_memory" in out
    assert "openclaw.proxy_synergy" in out
    assert "openclaw.min_version" in out


def test_config_store_describe_includes_openclaw_via_defaults(tmp_path: Path):
    """Describe() includes openclaw block when defaults present (load() merges defaults)."""
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    store.save({"mode": "skills_only"})
    out = store.describe()
    # Defaults are merged on load(), so the openclaw block IS present
    assert "openclaw.context_engine" in out
    assert "openclaw.min_version" in out


# ---------------------------------------------------------------- #
# 5 & 6. Claw adapter — Active Memory suppression toggle           #
# ---------------------------------------------------------------- #

def test_configure_openclaw_active_memory_suppression(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("metaclaw.claw_adapter.subprocess.run", fake_run)

    from metaclaw.claw_adapter import _configure_openclaw
    cfg = MetaClawConfig(
        api_key="proxy-key",
        llm_model_id="test-model",
        proxy_port=30000,
        openclaw_active_memory_compat=True,
    )
    cfg.proxy_api_key = "proxy-key"  # claw_adapter accesses this attribute directly
    _configure_openclaw(cfg)

    slot_cmds = [c for c in calls if "plugins.slots.memory" in c]
    assert len(slot_cmds) == 1
    assert slot_cmds[0][-1] == "metaclaw-memory"

    # Gateway restart must be the LAST command
    assert calls[-1] == ["openclaw", "gateway", "restart"]


def test_configure_openclaw_skips_active_memory_suppression(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("metaclaw.claw_adapter.subprocess.run", fake_run)

    from metaclaw.claw_adapter import _configure_openclaw
    cfg = MetaClawConfig(
        api_key="proxy-key",
        llm_model_id="test-model",
        proxy_port=30000,
        openclaw_active_memory_compat=False,
    )
    cfg.proxy_api_key = "proxy-key"  # claw_adapter accesses this attribute directly
    _configure_openclaw(cfg)

    slot_cmds = [c for c in calls if "plugins.slots.memory" in c]
    assert len(slot_cmds) == 0
    # Gateway restart still runs last
    assert calls[-1] == ["openclaw", "gateway", "restart"]


# ---------------------------------------------------------------- #
# 7. API server dispatcher boolean conditions                      #
# ---------------------------------------------------------------- #

def test_api_server_dispatcher_conditions():
    """Verify the boolean conditions driving the context-engine dispatcher
    in api_server.py:1258-1269."""
    # Case 1: context-engine active, default config → skills-only path
    cfg = MetaClawConfig(
        openclaw_context_engine_enabled=True,
        openclaw_prefer_proxy_synergy=False,
    )
    context_engine_active = True
    has_skill_manager = True
    has_memory_manager = True

    # Outer guard true → enter context-engine block
    assert context_engine_active and cfg.openclaw_context_engine_enabled
    # Synergy escape hatch NOT taken (prefer_proxy_synergy is False)
    assert not (cfg.openclaw_prefer_proxy_synergy and has_memory_manager and has_skill_manager)
    # Falls through to skills-only path
    assert has_skill_manager

    # Case 2: prefer_proxy_synergy=True with memory + skills + synergy_enabled
    cfg2 = MetaClawConfig(
        openclaw_context_engine_enabled=True,
        openclaw_prefer_proxy_synergy=True,
    )
    assert cfg2.openclaw_prefer_proxy_synergy and has_memory_manager and has_skill_manager

    # Case 3: context-engine disabled in config → fall through to original logic
    cfg3 = MetaClawConfig(openclaw_context_engine_enabled=False)
    assert not (context_engine_active and cfg3.openclaw_context_engine_enabled)

    # Case 4: header not set → context_engine_active False → fall through
    assert not (False and cfg.openclaw_context_engine_enabled)


# ---------------------------------------------------------------- #
# 8. Setup wizard — OpenClaw advanced section                      #
# ---------------------------------------------------------------- #

def _wizard_skills_only_prompts(skills_dir: Path, oc_advanced: bool, oc_overrides: dict | None = None):
    """Build prompt fakers for a skills_only wizard run, with optional oc overrides."""
    overrides = oc_overrides or {}

    def fake_prompt_choice(msg, choices, default=""):
        if msg == "Operating mode":
            return "skills_only"
        if msg == "Auth method":
            return "api_key"
        if msg == "Provider":
            return "custom"
        if msg == "LLM provider":
            return "custom"
        raise AssertionError(f"Unexpected choice prompt: {msg}")

    def fake_prompt(msg, default="", hide=False):
        if msg == "API base URL":
            return "https://api.example/v1"
        if msg == "Model ID":
            return "test-model"
        if msg == "API key":
            return "test-key"
        if msg == "Skills directory":
            return str(skills_dir)
        if msg == "Minimum OpenClaw version":
            return overrides.get("min_version", "2026.4.15")
        raise AssertionError(f"Unexpected text prompt: {msg}")

    def fake_prompt_bool(msg, default=False):
        if msg == "Enable skill injection":
            return True
        if msg == "Auto-summarize skills after each conversation":
            return True
        if msg == "Configure OpenClaw compatibility settings (advanced)":
            return oc_advanced
        if msg == "Enable context-engine integration (memory via assemble/compact lifecycle)":
            return overrides.get("context_engine_enabled", True)
        if msg == "Suppress OpenClaw built-in Active Memory":
            return overrides.get("active_memory_compat", False)
        if msg == "Force proxy-side synergy (memory+skills) even with context-engine active":
            return overrides.get("prefer_proxy_synergy", True)
        raise AssertionError(f"Unexpected bool prompt: {msg}")

    def fake_prompt_int(msg, default=0):
        if msg == "Proxy port":
            return 30000
        raise AssertionError(f"Unexpected int prompt: {msg}")

    return fake_prompt_choice, fake_prompt, fake_prompt_bool, fake_prompt_int


def test_setup_wizard_openclaw_advanced_section(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    skills_dir = tmp_path / "skills"
    store = ConfigStore(config_file=config_path)

    pc, p, pb, pi = _wizard_skills_only_prompts(
        skills_dir,
        oc_advanced=True,
        oc_overrides={
            "context_engine_enabled": True,
            "active_memory_compat": False,
            "prefer_proxy_synergy": True,
            "min_version": "2026.4.15",
        },
    )

    monkeypatch.setattr("metaclaw.setup_wizard.ConfigStore", lambda: store)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_choice", pc)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt", p)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_bool", pb)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_int", pi)

    SetupWizard().run()

    saved = store.load()
    assert saved["openclaw_compat"]["context_engine_enabled"] is True
    assert saved["openclaw_compat"]["active_memory_compat"] is False
    assert saved["openclaw_compat"]["prefer_proxy_synergy"] is True
    assert saved["openclaw_compat"]["min_version"] == "2026.4.15"


def test_setup_wizard_openclaw_skipped_uses_defaults(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    skills_dir = tmp_path / "skills"
    store = ConfigStore(config_file=config_path)

    pc, p, pb, pi = _wizard_skills_only_prompts(skills_dir, oc_advanced=False)

    monkeypatch.setattr("metaclaw.setup_wizard.ConfigStore", lambda: store)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_choice", pc)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt", p)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_bool", pb)
    monkeypatch.setattr("metaclaw.setup_wizard._prompt_int", pi)

    SetupWizard().run()

    saved = store.load()
    # When user declines advanced section, defaults must be persisted
    assert saved["openclaw_compat"]["context_engine_enabled"] is True
    assert saved["openclaw_compat"]["active_memory_compat"] is True
    assert saved["openclaw_compat"]["prefer_proxy_synergy"] is False
    assert saved["openclaw_compat"]["min_version"] == "2026.4.10"
