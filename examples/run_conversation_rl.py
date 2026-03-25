"""
End-to-end example: conversation RL with Tinker + OpenClaw + Skills.

Run:
    python examples/metaclaw/run_conversation_rl.py

Prerequisites:
  - Tinker API key set (TINKER_API_KEY env var)
  - PRM inference service (if use_prm=True; set use_prm=False to skip)
  - For skill evolution: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT set

Data collection (two modes):

  1. Passive mode (openclaw_env_data_dir="", consistent with OpenClaw-RL):
     Configure OpenClaw to use the proxy (run openclaw_model_qwen.sh),
     then use OpenClaw normally.  The proxy collects training data automatically.

  2. Programmatic mode (openclaw_env_data_dir set):
     Provide a JSONL file at <openclaw_env_data_dir>/<split>.jsonl.
     Each line: {"task_id": "...", "instruction": "..."}
     A Qwen3-native agent loop drives tasks automatically via subprocess.
"""

import asyncio
import logging
import sys
import os

# Make sure SkillRL root is importable when running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from metaclaw.config import MetaClawConfig
from metaclaw.trainer import MetaClawTrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    config = MetaClawConfig(
        # Model
        model_name="moonshotai/Kimi-K2.5",
        served_model_name="Kimi-K2.5",
        lora_rank=32,
        renderer_name="kimi",

        # Training
        learning_rate=1e-4,
        batch_size=8,
        max_steps=500,
        loss_fn="importance_sampling",

        # PRM reward — point at any OpenAI-compatible judge API
        use_prm=True,
        prm_url="https://openai-api.shenmishajing.workers.dev/v1",
        prm_model="gpt-5.2",
        prm_api_key=os.environ.get("OPENAI_API_KEY", "aB7cD9eF2gH5iJ8kL1mN4oP6qR3sT0uV"),
        prm_m=3,

        # Skills
        use_skills=True,
        skills_dir="memory_data/skills",
        retrieval_mode="template",
        skill_top_k=6,

        # Skill evolution (requires Azure OpenAI env vars)
        enable_skill_evolution=False,
        skill_update_threshold=0.4,
        max_new_skills=3,

        # Proxy server
        proxy_port=30000,
        proxy_host="0.0.0.0",

        # Programmatic task rollout (optional).
        # Set to a directory containing <split>.jsonl task files, e.g.:
        #   openclaw_env_data_dir="/path/to/tasks"
        # where /path/to/tasks/train.jsonl has lines like:
        #   {"task_id": "add_webhook_1", "instruction": "Register the webhook URL ..."}
        #
        # Leave empty ("") for passive proxy mode (like OpenClaw-RL):
        #   run openclaw_model_qwen.sh to point OpenClaw at the proxy,
        #   then use OpenClaw normally.
        openclaw_env_data_dir="examples/metaclaw",  # set to task JSONL dir to enable
        openclaw_env_split="train",
        openclaw_env_concurrency=4,           # parallel task episodes
        openclaw_env_max_steps=15,            # max turns per episode
    )

    trainer = MetaClawTrainer(config)
    await trainer.run()


if __name__ == "__main__":
    asyncio.run(main())
