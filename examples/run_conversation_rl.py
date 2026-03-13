"""
End-to-end RL smoke test for a Tinker-compatible backend such as MinT.

Run:
    python examples/run_conversation_rl.py

Required env:
  - METACLAW_RL_API_KEY or TINKER_API_KEY or MINT_API_KEY
  - Optional METACLAW_RL_BASE_URL or TINKER_BASE_URL or MINT_BASE_URL

Useful overrides:
  - METACLAW_RL_BACKEND=mint
  - METACLAW_RL_MODEL=Qwen/Qwen3-4B-Instruct-2507
  - METACLAW_MAX_STEPS=1
  - METACLAW_ENV_CONCURRENCY=1
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Make sure the repo root is importable when running from outside the repo.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metaclaw.config import MetaClawConfig
from metaclaw.trainer import MetaClawTrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


async def main():
    example_dir = REPO_ROOT / "examples"
    skills_dir = REPO_ROOT / "memory_data" / "skills"
    model_name = _first_env(
        "METACLAW_RL_MODEL",
        "TINKER_MODEL",
        "MINT_MODEL",
        default="Qwen/Qwen3-4B-Instruct-2507",
    )
    served_model_name = os.environ.get("METACLAW_SERVED_MODEL", model_name).strip() or model_name
    backend_api_key = _first_env("METACLAW_RL_API_KEY", "TINKER_API_KEY", "MINT_API_KEY")
    backend_base_url = _first_env("METACLAW_RL_BASE_URL", "TINKER_BASE_URL", "MINT_BASE_URL")
    backend = _first_env(
        "METACLAW_RL_BACKEND",
        default=("mint" if "mint" in backend_base_url.lower() else "auto"),
    ).lower()

    if not backend_api_key:
        raise RuntimeError(
            "Set METACLAW_RL_API_KEY, TINKER_API_KEY, or MINT_API_KEY before running this example."
        )

    logging.getLogger(__name__).info(
        "[ExampleRL] backend=%s model=%s served_model=%s data_dir=%s split=%s",
        backend,
        model_name,
        served_model_name,
        example_dir.name,
        "train",
    )

    config = MetaClawConfig(
        # Model
        model_name=model_name,
        served_model_name=served_model_name,
        lora_rank=int(os.environ.get("METACLAW_LORA_RANK", "16")),
        renderer_name=os.environ.get("METACLAW_RENDERER", "qwen3"),

        # Training
        learning_rate=float(os.environ.get("METACLAW_LR", "1e-4")),
        batch_size=int(os.environ.get("METACLAW_BATCH_SIZE", "1")),
        max_steps=int(os.environ.get("METACLAW_MAX_STEPS", "1")),
        loss_fn=os.environ.get("METACLAW_LOSS_FN", "importance_sampling"),
        backend=backend,
        api_key=backend_api_key,
        base_url=backend_base_url,
        proxy_api_key=os.environ.get("METACLAW_PROXY_API_KEY", "").strip(),

        # PRM reward is disabled by default for backend smoke tests.
        use_prm=False,

        # Skills
        use_skills=True,
        skills_dir=str(skills_dir),
        retrieval_mode="template",
        skill_top_k=6,

        # Skill evolution is disabled for smoke tests.
        enable_skill_evolution=False,
        skill_update_threshold=0.4,
        max_new_skills=3,

        # Proxy server
        proxy_port=int(os.environ.get("METACLAW_PROXY_PORT", "30000")),
        proxy_host=os.environ.get("METACLAW_PROXY_HOST", "0.0.0.0"),

        # Programmatic rollout: examples/train.jsonl
        openclaw_env_data_dir=str(example_dir),
        openclaw_env_split=os.environ.get("METACLAW_DATA_SPLIT", "train"),
        openclaw_env_concurrency=int(os.environ.get("METACLAW_ENV_CONCURRENCY", "1")),
        openclaw_env_max_steps=int(os.environ.get("METACLAW_ENV_MAX_STEPS", "2")),
    )

    trainer = MetaClawTrainer(config)
    await trainer.run()


if __name__ == "__main__":
    asyncio.run(main())
