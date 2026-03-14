"""
MetaClaw — OpenClaw skill injection and RL training, one-click deployment.

Integrates:
  - OpenClaw online dialogue data collection (FastAPI proxy)
  - Skill injection and auto-summarization (skills_only mode)
  - Tinker-compatible cloud LoRA RL training (rl mode, optional)

Quick start:
    metaclaw setup    # configure LLM, skills, RL toggle
    metaclaw start    # one-click launch
"""

from __future__ import annotations

import importlib

from .config import MetaClawConfig
from .config_store import ConfigStore

__all__ = [
    "MetaClawConfig",
    "ConfigStore",
    "MetaClawAPIServer",
    "AsyncRolloutWorker",
    "PRMScorer",
    "SkillManager",
    "SkillEvolver",
    "MetaClawLauncher",
    "ConversationSample",
    "batch_to_datums",
    "compute_advantages",
    "MetaClawTrainer",
]


_LAZY_IMPORTS = {
    "MetaClawAPIServer": (".api_server", "MetaClawAPIServer"),
    "AsyncRolloutWorker": (".rollout", "AsyncRolloutWorker"),
    "PRMScorer": (".prm_scorer", "PRMScorer"),
    "SkillManager": (".skill_manager", "SkillManager"),
    "SkillEvolver": (".skill_evolver", "SkillEvolver"),
    "MetaClawLauncher": (".launcher", "MetaClawLauncher"),
    "ConversationSample": (".data_formatter", "ConversationSample"),
    "batch_to_datums": (".data_formatter", "batch_to_datums"),
    "compute_advantages": (".data_formatter", "compute_advantages"),
    "MetaClawTrainer": (".trainer", "MetaClawTrainer"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_name, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_name, __name__)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
