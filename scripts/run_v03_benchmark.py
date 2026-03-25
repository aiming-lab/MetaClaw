"""
MetaClaw v0.3 benchmark: full outer-loop training with scheduler.

- Scheduler sleep window starts 5 min from launch → RL updates auto-trigger
- PRM scoring via Bedrock Sonnet 4.6 (no API key needed)
- Skill evolution via Bedrock Sonnet 4.6
- Tinker LoRA training on Qwen3-8B
- wandb logging enabled
- Evaluation run after training completes
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark")


async def run_training():
    from metaclaw.config import MetaClawConfig
    from metaclaw.trainer import MetaClawTrainer
    from metaclaw.scheduler import SlowUpdateScheduler
    from metaclaw.idle_detector import IdleDetector, LastRequestTracker

    # Sleep window: starts 1 min from now, lasts 2 hours
    now = datetime.now()
    sleep_start = (now + timedelta(minutes=1)).strftime("%H:%M")
    sleep_end = (now + timedelta(hours=2, minutes=1)).strftime("%H:%M")
    logger.info("Sleep window: %s – %s (current time: %s)", sleep_start, sleep_end, now.strftime("%H:%M"))

    config = MetaClawConfig(
        # Mode
        mode="auto",

        # Model
        model_name="Qwen/Qwen3-8B",
        served_model_name="Qwen3-8B",
        lora_rank=32,
        renderer_name="qwen3",

        # Training
        learning_rate=1e-4,
        batch_size=2,
        max_steps=5,
        loss_fn="importance_sampling",

        # PRM — Bedrock Sonnet 4.6
        use_prm=True,
        prm_provider="bedrock",
        prm_model="us.anthropic.claude-sonnet-4-6",
        prm_m=3,

        # Skills + evolution — Bedrock Sonnet 4.6
        use_skills=True,
        skills_dir="memory_data/skills",
        retrieval_mode="template",
        skill_top_k=6,
        enable_skill_evolution=True,
        skill_update_threshold=0.4,
        max_new_skills=3,
        evolver_provider="bedrock",
        evolver_model_id="us.anthropic.claude-sonnet-4-6",

        # Proxy
        proxy_port=30000,
        proxy_host="0.0.0.0",

        # Programmatic rollout from train.jsonl
        openclaw_env_data_dir="examples",
        openclaw_env_split="train",
        openclaw_env_concurrency=4,
        openclaw_env_max_steps=15,

        # Scheduler — sleep window opens in 5 min
        scheduler_enabled=True,
        scheduler_sleep_start=sleep_start,
        scheduler_sleep_end=sleep_end,
        scheduler_idle_threshold_minutes=9999,  # rely on sleep window only

        # Bedrock region
        bedrock_region="us-east-1",
    )

    # Set up scheduler
    trigger_event = asyncio.Event()
    pause_event = asyncio.Event()
    request_tracker = LastRequestTracker()
    idle_detector = IdleDetector(fallback_tracker=request_tracker)

    scheduler = SlowUpdateScheduler(
        config=config,
        trigger_event=trigger_event,
        pause_event=pause_event,
        idle_detector=idle_detector,
    )

    trainer = MetaClawTrainer(
        config,
        trigger_event=trigger_event,
        pause_event=pause_event,
        scheduler=scheduler,
        last_request_tracker=request_tracker,
    )

    # Run scheduler + trainer concurrently.
    # trainer.run() exits after max_steps; scheduler.run() loops forever.
    # Use asyncio.wait with FIRST_COMPLETED so we proceed once training finishes.
    trainer_task = asyncio.create_task(trainer.run())
    scheduler_task = asyncio.create_task(scheduler.run())

    try:
        done, pending = await asyncio.wait(
            [trainer_task, scheduler_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # Propagate any exception from the trainer
        for t in done:
            t.result()
    finally:
        scheduler.stop()
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

    return trainer, config


async def run_evaluation(config):
    """Evaluate the trained model by running tasks and measuring PRM scores."""
    import tinker
    from transformers import AutoTokenizer
    from metaclaw.bedrock_client import BedrockChatClient
    from metaclaw.prm_scorer import PRMScorer

    logger.info("=" * 60)
    logger.info("  EVALUATION PHASE")
    logger.info("=" * 60)

    # Load tasks
    tasks_file = Path(config.openclaw_env_data_dir) / f"{config.openclaw_env_split}.jsonl"
    tasks = []
    for line in tasks_file.read_text().splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    logger.info("Loaded %d evaluation tasks", len(tasks))

    # Load tokenizer for Tinker ModelInput construction
    tokenizer = AutoTokenizer.from_pretrained(config.model_name, trust_remote_code=True)
    logger.info("Tokenizer loaded: %s", config.model_name)

    # Create Tinker sampling client from the latest checkpoint
    service_client = tinker.ServiceClient()
    training_client = await service_client.create_lora_training_client_async(
        base_model=config.model_name, rank=config.lora_rank,
    )
    sampling_client = await training_client.save_weights_and_get_sampling_client_async()
    logger.info("Sampling client ready for evaluation")

    # PRM scorer for evaluation
    bedrock_client = BedrockChatClient(
        model_id=config.prm_model,
        region=config.bedrock_region,
    )
    scorer = PRMScorer(
        prm_url="",
        prm_model=config.prm_model,
        prm_m=3,
        temperature=0.3,
        max_new_tokens=512,
        llm_client=bedrock_client,
    )

    # Evaluate on a subset of tasks
    eval_tasks = tasks[:20]  # first 20 tasks
    results = []

    for i, task in enumerate(eval_tasks):
        task_id = task.get("task_id", f"eval_{i}")
        instruction = task.get("instruction", "")

        # Build chat messages and tokenize for Tinker ModelInput
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": instruction},
        ]
        try:
            prompt_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
            prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
            chunk = tinker.EncodedTextChunk(tokens=list(prompt_ids), type="encoded_text")
            model_input = tinker.ModelInput(chunks=[chunk])

            sampling_params = tinker.SamplingParams(
                temperature=0.6, max_tokens=512, top_k=50, top_p=0.95,
            )
            sample_result = await sampling_client.sample_async(
                prompt=model_input,
                num_samples=1,
                sampling_params=sampling_params,
            )
            # Decode response tokens back to text
            seq = sample_result.sequences[0]
            response_text = tokenizer.decode(seq.tokens, skip_special_tokens=True)
        except Exception as e:
            logger.warning("Sampling failed for %s: %s", task_id, e)
            response_text = f"Error: {e}"

        # Score via PRM
        prm_result = await scorer.evaluate(
            response=response_text,
            instruction=instruction,
            session_id=task_id,
            turn_num=1,
        )

        results.append({
            "task_id": task_id,
            "score": prm_result["score"],
            "votes": prm_result["votes"],
            "instruction": instruction[:100],
            "response": response_text[:200],
        })

        logger.info(
            "  [%d/%d] %s → score=%s votes=%s",
            i + 1, len(eval_tasks), task_id,
            prm_result["score"], prm_result["votes"],
        )

    # Summary
    scores = [r["score"] for r in results]
    mean_score = sum(scores) / len(scores) if scores else 0
    success_rate = sum(1 for s in scores if s > 0) / len(scores) if scores else 0
    failure_rate = sum(1 for s in scores if s < 0) / len(scores) if scores else 0

    logger.info("=" * 60)
    logger.info("  EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info("  Tasks evaluated:  %d", len(results))
    logger.info("  Mean PRM score:   %.3f", mean_score)
    logger.info("  Success rate:     %.1f%% (score > 0)", success_rate * 100)
    logger.info("  Failure rate:     %.1f%% (score < 0)", failure_rate * 100)
    logger.info("  Neutral rate:     %.1f%% (score = 0)", (1 - success_rate - failure_rate) * 100)

    # Save results
    eval_file = Path("records/eval_results.jsonl")
    eval_file.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_file, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info("  Results saved to: %s", eval_file)

    # Log to wandb if available
    try:
        import wandb
        if wandb.run is not None:
            wandb.log({
                "eval/mean_score": mean_score,
                "eval/success_rate": success_rate,
                "eval/failure_rate": failure_rate,
                "eval/num_tasks": len(results),
            })
    except Exception:
        pass

    return {
        "mean_score": mean_score,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "num_tasks": len(results),
    }


async def main():
    logger.info("=" * 60)
    logger.info("  MetaClaw v0.3 Benchmark")
    logger.info("  batch_size=2  max_steps=5  mode=auto")
    logger.info("  PRM: Bedrock Sonnet 4.6  Evolver: Bedrock Sonnet 4.6")
    logger.info("=" * 60)

    trainer, config = await run_training()
    logger.info("Training complete. Starting evaluation...")

    eval_results = await run_evaluation(config)

    logger.info("=" * 60)
    logger.info("  BENCHMARK COMPLETE")
    logger.info("  Training: 5 steps, batch_size=2")
    logger.info("  Eval: mean_score=%.3f success=%.1f%%",
                eval_results["mean_score"], eval_results["success_rate"] * 100)
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
