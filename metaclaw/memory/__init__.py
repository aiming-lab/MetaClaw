"""
MetaClaw Memory Subsystem.

Self-evolving long-term memory with adaptive policy, replay-based evaluation,
and bounded self-upgrade — all backed by SQLite + FTS5.
"""

from .candidate import generate_policy_candidates
from .consolidator import MemoryConsolidator
from .manager import MemoryManager
from .models import MemoryQuery, MemoryStatus, MemoryType, MemoryUnit
from .promotion import MemoryPromotionCriteria, should_promote
from .replay import (
    MemoryReplayEvaluator,
    MemoryReplaySample,
    load_replay_samples,
    run_policy_candidate_replay,
)
from .scope import derive_memory_scope
from .self_upgrade import MemorySelfUpgradeOrchestrator
from .store import MemoryStore
from .telemetry import MemoryTelemetryStore
from .upgrade_worker import MemoryUpgradeWorker

__all__ = [
    "MemoryManager",
    "MemoryStore",
    "MemoryConsolidator",
    "MemoryQuery",
    "MemoryStatus",
    "MemoryType",
    "MemoryUnit",
    "MemoryTelemetryStore",
    "MemoryPromotionCriteria",
    "should_promote",
    "MemoryReplayEvaluator",
    "MemoryReplaySample",
    "load_replay_samples",
    "run_policy_candidate_replay",
    "MemorySelfUpgradeOrchestrator",
    "MemoryUpgradeWorker",
    "derive_memory_scope",
    "generate_policy_candidates",
]
