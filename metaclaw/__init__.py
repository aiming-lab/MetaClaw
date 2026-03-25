"""
MetaClaw — OpenClaw skill injection and RL training, one-click deployment.

Integrates:
  - OpenClaw online dialogue data collection (FastAPI proxy)
  - Skill injection and auto-summarization (skills_only mode)
  - Tinker cloud LoRA RL training (rl mode, optional)
  - Long-term memory system (memory module)

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

# Memory imports
from .memory.manager import MemoryManager
from .memory.candidate import generate_policy_candidates
from .memory.promotion import MemoryPromotionCriteria, should_promote
from .memory.replay import (
    MemoryReplayEvaluator,
    MemoryReplaySample,
    load_replay_samples,
    run_policy_candidate_replay,
)
from .memory.self_upgrade import MemorySelfUpgradeOrchestrator
from .memory.scope import derive_memory_scope
from .memory.store import MemoryStore
from .memory.consolidator import MemoryConsolidator
from .memory.upgrade_worker import MemoryUpgradeWorker

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
    "MemoryManager",
    "generate_policy_candidates",
    "MemoryPromotionCriteria",
    "MemoryReplayEvaluator",
    "MemoryReplaySample",
    "MemorySelfUpgradeOrchestrator",
    "MemoryUpgradeWorker",
    "derive_memory_scope",
    "load_replay_samples",
    "run_policy_candidate_replay",
    "should_promote",
    "MemoryStore",
    "MemoryConsolidator",
]
