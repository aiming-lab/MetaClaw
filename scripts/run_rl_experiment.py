"""
Full RL training experiment with Tinker + Azure OpenAI PRM + Skills + Memory.

Uses:
  - Tinker cloud LoRA on Qwen/Qwen3-8B
  - Azure OpenAI gpt-5.1 as PRM judge + Skill Evolver
  - Memory system for long-term learning
  - Programmatic task rollout from examples/train.jsonl
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metaclaw.config import MetaClawConfig
from metaclaw.trainer import MetaClawTrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rl_experiment")

# Azure OpenAI credentials
AZURE_API_BASE = "https://huaxi-mlg4x1rk-eastus2.services.ai.azure.com/openai/v1"
AZURE_API_KEY = os.environ.get("AZURE_API_KEY", "")
AZURE_MODEL = "gpt-5.1"

# Tinker API key
os.environ["TINKER_API_KEY"] = "tml-QVQstrwSADCF2MlYeHzXaXchZJoc1HIiNeXBjr0Ox0xljEoJKQa8YFmw1iLcRfqLCAAAA"

# Evolver env vars
os.environ["OPENAI_API_KEY"] = AZURE_API_KEY
os.environ["OPENAI_BASE_URL"] = AZURE_API_BASE
os.environ["SKILL_EVOLVER_MODEL"] = AZURE_MODEL

# Disable wandb unless explicitly configured
os.environ.setdefault("WANDB_DISABLED", "true")


async def main():
    logger.info("=" * 60)
    logger.info("  MetaClaw RL Training Experiment")
    logger.info("  Model: Qwen/Qwen3-8B (Tinker LoRA, rank=32)")
    logger.info("  PRM: Azure OpenAI gpt-5.1")
    logger.info("  batch_size=2  max_steps=3")
    logger.info("=" * 60)

    config = MetaClawConfig(
        # Mode
        mode="rl",

        # Model
        model_name="Qwen/Qwen3-8B",
        served_model_name="Qwen3-8B",
        lora_rank=32,
        renderer_name="qwen3",

        # Training
        learning_rate=1e-4,
        batch_size=2,        # Small batch for quick experiment
        max_steps=3,         # 3 training steps to validate pipeline
        loss_fn="importance_sampling",

        # PRM reward — Azure OpenAI gpt-5.1
        use_prm=True,
        prm_provider="openai",
        prm_url=AZURE_API_BASE,
        prm_model=AZURE_MODEL,
        prm_api_key=AZURE_API_KEY,
        prm_m=3,
        prm_temperature=0.6,
        prm_max_new_tokens=1024,

        # Skills
        use_skills=True,
        skills_dir=os.path.expanduser("~/.metaclaw/skills"),
        retrieval_mode="template",
        skill_top_k=6,
        task_specific_top_k=10,

        # Skill evolution — Azure OpenAI gpt-5.1
        enable_skill_evolution=True,
        skill_update_threshold=0.4,
        max_new_skills=3,
        evolver_provider="openai",
        evolver_api_base=AZURE_API_BASE,
        evolver_api_key=AZURE_API_KEY,
        evolver_model_id=AZURE_MODEL,

        # Memory
        memory_enabled=True,
        memory_dir=os.path.expanduser("~/.metaclaw/memory"),
        memory_store_path=os.path.expanduser("~/.metaclaw/memory/memory.db"),
        memory_scope="default",
        memory_retrieval_mode="keyword",
        memory_auto_extract=True,
        memory_auto_consolidate=True,

        # Proxy server
        proxy_port=30000,
        proxy_host="0.0.0.0",

        # Programmatic task rollout from train.jsonl
        openclaw_env_data_dir="examples",
        openclaw_env_split="train",
        openclaw_env_concurrency=2,    # 2 parallel episodes
        openclaw_env_max_steps=10,     # max 10 turns per episode

        # No scheduler — run continuously
        scheduler_enabled=False,
    )

    trainer = MetaClawTrainer(config)
    try:
        await trainer.run()
        logger.info("=" * 60)
        logger.info("  RL TRAINING COMPLETE")
        logger.info("=" * 60)

        # Print skill evolution summary
        if trainer.skill_evolver:
            logger.info("Skill evolution summary: %s",
                        trainer.skill_evolver.get_update_summary())

        # Print memory stats
        if trainer.memory_manager:
            stats = trainer.memory_manager.get_scope_stats()
            logger.info("Memory stats: %s", stats)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Training failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
