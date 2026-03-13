"""
MetaClaw — OpenClaw skill injection and RL training, one-click deployment.

Integrates:
  - OpenClaw online dialogue data collection (FastAPI proxy)
  - Skill injection and auto-summarization (skills_only mode)
  - Tinker-compatible cloud LoRA RL training, including MinT (rl mode, optional)

Quick start:
    metaclaw setup    # configure LLM, skills, RL toggle
    metaclaw start    # one-click launch
"""

from .config import MetaClawConfig
from .config_store import ConfigStore
from .api_server import MetaClawAPIServer
from .rollout import AsyncRolloutWorker
from .prm_scorer import PRMScorer
from .skill_manager import SkillManager
from .skill_evolver import SkillEvolver
from .launcher import MetaClawLauncher

# RL-only imports (guarded to avoid hard dep on torch/tinker in skills_only mode)
try:
    from .data_formatter import ConversationSample, batch_to_datums, compute_advantages
    from .trainer import MetaClawTrainer
except ImportError:
    pass

__all__ = [
    "MetaClawConfig",
    "ConfigStore",
    "MetaClawAPIServer",
    "AsyncRolloutWorker",
    "PRMScorer",
    "SkillManager",
    "SkillEvolver",
    "MetaClawLauncher",
]
