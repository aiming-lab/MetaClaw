"""Sidecar configuration with env-var loading and MetaClawConfig conversion."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

from metaclaw.config import MetaClawConfig


@dataclass
class SidecarConfig:
    port: int = 19823
    host: str = "127.0.0.1"
    memory_dir: str = "~/.metaclaw/memory"
    memory_scope: str = "default"
    retrieval_mode: str = "keyword"  # keyword / hybrid / embedding
    max_injected_units: int = 6
    max_injected_tokens: int = 800
    use_embeddings: bool = False
    embedding_mode: str = "hashing"
    embedding_model: str = "all-MiniLM-L6-v2"
    auto_upgrade_enabled: bool = False
    auto_upgrade_interval: int = 900
    auto_consolidate: bool = True
    python_path: str = "python3"
    log_level: str = "info"

    def to_metaclaw_config(self) -> MetaClawConfig:
        """Convert sidecar settings into a MetaClawConfig for the memory subsystem."""
        mem_dir = str(Path(self.memory_dir).expanduser())
        store_path = str(Path(mem_dir) / "memory.db")
        policy_path = str(Path(mem_dir) / "policy.json")
        telemetry_path = str(Path(mem_dir) / "telemetry.jsonl")

        return MetaClawConfig(
            memory_enabled=True,
            memory_dir=mem_dir,
            memory_store_path=store_path,
            memory_scope=self.memory_scope,
            memory_retrieval_mode=self.retrieval_mode,
            memory_use_embeddings=self.use_embeddings,
            memory_embedding_mode=self.embedding_mode,
            memory_embedding_model=self.embedding_model,
            memory_policy_path=policy_path,
            memory_telemetry_path=telemetry_path,
            memory_auto_upgrade_enabled=self.auto_upgrade_enabled,
            memory_auto_upgrade_interval_seconds=self.auto_upgrade_interval,
            memory_max_injected_units=self.max_injected_units,
            memory_max_injected_tokens=self.max_injected_tokens,
            memory_auto_consolidate=self.auto_consolidate,
        )

    @classmethod
    def from_env(cls) -> "SidecarConfig":
        """Build config from METACLAW_SIDECAR_* environment variables."""
        kwargs: dict = {}
        for f in fields(cls):
            env_key = f"METACLAW_SIDECAR_{f.name.upper()}"
            val = os.environ.get(env_key)
            if val is None:
                continue
            if f.type == "bool":
                kwargs[f.name] = val.lower() in ("1", "true", "yes")
            elif f.type == "int":
                kwargs[f.name] = int(val)
            else:
                kwargs[f.name] = val
        return cls(**kwargs)
