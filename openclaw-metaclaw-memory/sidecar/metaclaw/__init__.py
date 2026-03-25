"""
MetaClaw — bundled subset for the OpenClaw memory sidecar.

Only includes the memory subsystem and MetaClawConfig.
The full MetaClaw package (training, RL, skills, etc.) is NOT included here.
"""

from .config import MetaClawConfig
from .memory.manager import MemoryManager
from .memory.store import MemoryStore
from .memory.consolidator import MemoryConsolidator
from .memory.upgrade_worker import MemoryUpgradeWorker

__all__ = [
    "MetaClawConfig",
    "MemoryManager",
    "MemoryStore",
    "MemoryConsolidator",
    "MemoryUpgradeWorker",
]
