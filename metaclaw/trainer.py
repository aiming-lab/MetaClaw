"""
Main training loop for MetaClaw.

Uses Tinker cloud LoRA training instead of Megatron + SGLang.

Training clock cycle (interleaved for throughput):
  1. Resume rollout worker → collect batch from API server
  2. Pause rollout worker
  3. Compute advantages (GRPO-style)
  4. Convert to Tinker Datums
  5. forward_backward_async → optim_step_async (back-to-back before await)
  6. save_weights_and_get_sampling_client → push to rollout worker
  7. Resume rollout worker
  8. Optionally evolve skills
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
from typing import Optional

from .config import MetaClawConfig
from .data_formatter import ConversationSample, batch_to_datums, compute_advantages
from .openclaw_env_rollout import rollout_loop
from .prm_scorer import PRMScorer
from .rollout import AsyncRolloutWorker, _drain_output_queue
from .skill_evolver import SkillEvolver
from .skill_manager import SkillManager

logger = logging.getLogger(__name__)

_GREEN = "\033[32m"
_RESET = "\033[0m"


class MetaClawTrainer:
    """
    End-to-end RL trainer using Tinker LoRA + OpenClaw-style data collection.

    Parameters
    ----------
    config:
        MetaClawConfig instance.
    trigger_event:
        asyncio.Event set by SlowUpdateScheduler when a valid idle/sleep/calendar
        window is open.  When None (or scheduler disabled), an already-set event
        is used so the trainer runs continuously (original behaviour).
    pause_event:
        asyncio.Event set by SlowUpdateScheduler when the user becomes active and
        the trainer should stop collecting and wait for the next window.
    scheduler:
        SlowUpdateScheduler instance for two-way state callbacks.  None when the
        scheduler is disabled.
    """

    def __init__(
        self,
        config: MetaClawConfig,
        trigger_event: Optional[asyncio.Event] = None,
        pause_event: Optional[asyncio.Event] = None,
        scheduler=None,
        last_request_tracker=None,
    ):
        self.config = config
        self._last_request_tracker = last_request_tracker
        self.training_client = None
        self.sampling_client = None
        self.rollout_worker: Optional[AsyncRolloutWorker] = None
        self.skill_manager: Optional[SkillManager] = None
        self.prm_scorer: Optional[PRMScorer] = None
        self.skill_evolver: Optional[SkillEvolver] = None
        self.memory_manager = None
        self._wandb = None

        # Scheduler integration
        self._scheduler = scheduler
        # When scheduler is disabled, use an already-set event so the loop
        # runs immediately without waiting.
        if trigger_event is None:
            self._trigger_event = asyncio.Event()
            self._trigger_event.set()
        else:
            self._trigger_event = trigger_event
        self._pause_event = pause_event or asyncio.Event()

        # Samples carried over from an interrupted collection window.
        # Prepended to the next batch only if their skill_generation still matches.
        self._pending_batch: list[ConversationSample] = []
        # Tracks the skill generation active when the current batch started.
        # Initialised to 0; updated from skill_manager.generation after setup().
        self._current_skill_generation: int = 0
        # Step counter for externally triggered train steps (bench-driven / CLI).
        self._external_step_counter: int = 0
    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    async def setup(self):
        """Initialise Tinker clients, SkillManager, PRMScorer, and rollout worker."""
        from .log_color import setup_logging
        setup_logging()

        import tinker

        # Optional Weights & Biases logging.
        # Enable by setting WANDB_DISABLED to anything except "true"/"1"/"yes"/"on".
        wandb_disabled = os.environ.get("WANDB_DISABLED", "").strip().lower() in {
            "1", "true", "yes", "on",
        }
        if not wandb_disabled:
            try:
                os.environ.setdefault("WANDB_SILENT", "true")
                wandb = importlib.import_module("wandb")
                wandb_project = os.environ.get("WANDB_PROJECT", "metaclaw")
                wandb_run_name = os.environ.get("WANDB_RUN_NAME", "")
                init_kwargs: dict = {"project": wandb_project}
                if wandb_run_name:
                    init_kwargs["name"] = wandb_run_name
                try:
                    init_kwargs["settings"] = wandb.Settings(silent=True)
                except Exception:
                    pass
                self._wandb = wandb.init(**init_kwargs)
                logger.info("[Trainer] wandb enabled: project=%s", wandb_project)
            except Exception as e:
                logger.warning("[Trainer] wandb init failed; continuing without wandb: %s", e)

        # 1. Tinker service + LoRA training client
        logger.info("[Trainer] connecting to Tinker service …")
        service_client = tinker.ServiceClient()
        self.training_client = await service_client.create_lora_training_client_async(
            base_model=self.config.model_name,
            rank=self.config.lora_rank,
        )
        if self.config.resume_from_ckpt:
            logger.info("[Trainer] resuming training client from ckpt: %s", self.config.resume_from_ckpt)
            try:
                await self.training_client.load_state_async(self.config.resume_from_ckpt)
                logger.info("[Trainer] load_state done")
            except AttributeError as e:
                raise RuntimeError(
                    f"[Trainer] load_state failed: missing async API on training_client ({e})"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"[Trainer] load_state failed from resume_from_ckpt={self.config.resume_from_ckpt}: {e}"
                ) from e

        # 2. Initial sampling client (checkpoint = base weights)
        self.sampling_client = (
            await self.training_client.save_weights_and_get_sampling_client_async()
        )
        logger.info("[Trainer] initial sampling client ready")

        # 3. SkillManager
        if self.config.use_skills:
            self.skill_manager = SkillManager(
                skills_dir=self.config.skills_dir,
                retrieval_mode=self.config.retrieval_mode,
                embedding_model_path=self.config.embedding_model_path,
                task_specific_top_k=self.config.task_specific_top_k
            )
            logger.info("[Trainer] SkillManager ready: %s", self.skill_manager.get_skill_count())

        # 4. PRMScorer
        if self.config.use_prm:
            prm_client = None
            if self.config.prm_provider == "bedrock":
                from .bedrock_client import BedrockChatClient
                prm_client = BedrockChatClient(
                    model_id=self.config.prm_model,
                    region=self.config.bedrock_region,
                )
                logger.info("[Trainer] PRMScorer using Bedrock: model=%s region=%s",
                            self.config.prm_model, self.config.bedrock_region)
            self.prm_scorer = PRMScorer(
                prm_url=self.config.prm_url,
                prm_model=self.config.prm_model,
                api_key=self.config.prm_api_key,
                prm_m=self.config.prm_m,
                temperature=self.config.prm_temperature,
                max_new_tokens=self.config.prm_max_new_tokens,
                llm_client=prm_client,
            )
            logger.info("[Trainer] PRMScorer ready: provider=%s model=%s m=%d",
                        self.config.prm_provider, self.config.prm_model, self.config.prm_m)

        # 5. SkillEvolver
        if self.config.enable_skill_evolution:
            evolver_client = None
            if self.config.evolver_provider == "bedrock":
                from .bedrock_client import BedrockChatClient
                evolver_client = BedrockChatClient(
                    model_id=self.config.evolver_model_id,
                    region=self.config.bedrock_region,
                )
                logger.info("[Trainer] SkillEvolver using Bedrock: model=%s",
                            self.config.evolver_model_id)
            else:
                # Set evolver env vars from config (fallback to llm.* if evolver.* not set)
                evolver_base = self.config.evolver_api_base or self.config.llm_api_base
                evolver_key = self.config.evolver_api_key or self.config.llm_api_key
                if evolver_base:
                    os.environ.setdefault("OPENAI_BASE_URL", evolver_base)
                if evolver_key:
                    os.environ.setdefault("OPENAI_API_KEY", evolver_key)
                if self.config.evolver_model_id:
                    os.environ.setdefault("SKILL_EVOLVER_MODEL", self.config.evolver_model_id)
            self.skill_evolver = SkillEvolver(
                max_new_skills=self.config.max_new_skills,
                history_path=self.config.skill_evolution_history_path,
                llm_client=evolver_client,
            )
            logger.info("[Trainer] SkillEvolver ready: provider=%s", self.config.evolver_provider)

        # 6. MemoryManager (optional)
        if self.config.memory_enabled:
            from .memory.manager import MemoryManager

            self.memory_manager = MemoryManager.from_config(self.config)
            logger.info("[Trainer] MemoryManager ready: store=%s", self.config.memory_store_path)

        # 7. Rollout worker (owns MetaClawAPIServer)
        self.rollout_worker = AsyncRolloutWorker(
            config=self.config,
            sampling_client=self.sampling_client,
            skill_manager=self.skill_manager,
            memory_manager=self.memory_manager,
            prm_scorer=self.prm_scorer,
            skill_evolver=self.skill_evolver,
            last_request_tracker=self._last_request_tracker,
        )
        logger.info("[Trainer] rollout worker configured on %s:%d",
                    self.config.proxy_host, self.config.proxy_port)

        # Sync skill generation baseline so the trainer knows which samples are fresh.
        if self.skill_manager is not None:
            self._current_skill_generation = self.skill_manager.generation

    # ------------------------------------------------------------------ #
    # Training step                                                        #
    # ------------------------------------------------------------------ #

    async def _train_on_batch(self, batch: list[ConversationSample], step_idx: int):
        """Run one GRPO-style RL update on *batch*."""
        import tinker

        # Compute advantages (centre-normalise within batch)
        advantages = compute_advantages(batch)
        kl_coef = self.config.kl_penalty_coef if self.config.use_opd else 0.0
        data_D = batch_to_datums(batch, advantages, kl_penalty_coef=kl_coef)

        if not data_D:
            logger.warning("[Trainer] empty data batch — skipping step")
            return

        # forward+backward must complete before optimizer step
        logger.info("[Trainer] forward_backward_async starting (datums=%d) …", len(data_D))
        await self.training_client.forward_backward_async(
            data_D, loss_fn=self.config.loss_fn
        )
        logger.info("[Trainer] forward_backward_async done")

        logger.info("[Trainer] optim_step_async starting …")
        await self.training_client.optim_step_async(
            tinker.AdamParams(learning_rate=self.config.learning_rate)
        )
        logger.info("[Trainer] optim_step_async done")

        # Sync new weights to rollout worker
        logger.info("[Trainer] save_weights_and_get_sampling_client_async starting …")
        try:
            self.sampling_client = await asyncio.wait_for(
                self.training_client.save_weights_and_get_sampling_client_async(
                    name="openclaw_lora"
                ),
                timeout=self.config.save_weights_timeout_s,
            )
        except asyncio.TimeoutError:
            logger.error(
                "[Trainer] save_weights timed out after %.1fs; keep previous sampling client",
                self.config.save_weights_timeout_s,
            )
            return
        except Exception as e:
            logger.error("[Trainer] save_weights failed: %s", e, exc_info=True)
            return

        logger.info("[Trainer] weights saved, sampling client updated")
        if step_idx % 5 == 0:
            ckpt_name = f"step_{step_idx:04d}"
            try:
                save_future = self.training_client.save_state_async(name=ckpt_name)
                result = await save_future
                logger.info("[Trainer] save_state done, name=%s resume_path=%s", ckpt_name, result.path)
            except Exception as e:
                logger.warning("[Trainer] save_state failed (name=%s): %s", ckpt_name, e)
        self.rollout_worker.update_sampling_client(self.sampling_client)

        rewards = [s.reward for s in batch]
        mean_r = sum(rewards) / len(rewards)
        success_rate = sum(1 for r in rewards if r > 0) / len(rewards)
        logger.info(
            f"{_GREEN}[Trainer] step complete | batch=%d mean_reward=%.3f "
            f"success_rate=%.2f{_RESET}",
            len(batch), mean_r, success_rate,
        )
        if self._wandb is not None:
            self._wandb.log(
                {
                    "train/step": step_idx,
                    "train/mean_reward": mean_r,
                    "train/success_rate": success_rate,
                    "train/batch_size": len(batch),
                },
                step=step_idx,
            )
    # ------------------------------------------------------------------ #
    # Skill evolution                                                      #
    # ------------------------------------------------------------------ #

    async def _maybe_evolve_skills(self, batch: list[ConversationSample]):
        """Trigger skill evolution if success rate is below threshold.

        After evolution, if new skills were added (skill_manager.generation bumped),
        the RL sample buffer is cleared so pre-evolution samples are not reused
        for gradient updates.  This enforces the MAML support/query set separation:
        samples that caused skill evolution (support set) are never fed into the
        RL outer loop (query set).
        """
        if not self.skill_evolver or not self.skill_manager:
            return
        if not self.skill_evolver.should_evolve(batch, self.config.skill_update_threshold):
            return

        old_generation = self.skill_manager.generation
        failed = [s for s in batch if s.reward <= 0]
        logger.info("[SkillEvolver] evolving skills from %d failures …", len(failed))
        new_skills = await self.skill_evolver.evolve(failed, self.skill_manager.skills)

        if not new_skills:
            return

        added_total = 0
        for skill in new_skills:
            category = skill.get("category", "general")
            added = self.skill_manager.add_skills([skill], category=category)
            added_total += added

        if added_total > 0:
            logger.info("[SkillEvolver] skill evolution added %d new skills", added_total)

        new_generation = self.skill_manager.generation
        if new_generation > old_generation:
            # Skill generation bumped — discard all pre-evolution samples to
            # prevent stale reward signals from entering the RL update.
            self._current_skill_generation = new_generation
            discarded_pending = len(self._pending_batch)
            self._pending_batch.clear()
            discarded_queue = self.rollout_worker.clear_output_queue()
            logger.info(
                "[Trainer] skill_generation %d→%d: discarded %d pending + %d queued samples "
                "(MAML support/query separation; next RL batch will use post-evolution data)",
                old_generation, new_generation,
                discarded_pending, discarded_queue,
            )

    # ------------------------------------------------------------------ #
    # External trigger (bench-driven mode / manual CLI)                    #
    # ------------------------------------------------------------------ #

    async def train_step_external(self) -> dict:
        """Execute a single RL training step using samples already in the
        output queue.  Called by ``metaclaw train-step`` CLI or the admin
        HTTP endpoint.

        Returns a dict with training metrics or an error description.
        """
        if self.training_client is None:
            return {"status": "error", "message": "trainer not initialised (no Tinker client)"}

        # Drain all available samples from the output queue.
        groups = self.rollout_worker.get_completed_groups()
        batch: list[ConversationSample] = []
        for _group_id, group in groups:
            fresh = [
                s for s in group
                if s.skill_generation >= self._current_skill_generation
            ]
            batch.extend(fresh)

        if not batch:
            return {"status": "skipped", "message": "no samples in queue", "samples": 0}

        self._external_step_counter += 1
        step_idx = self._external_step_counter

        try:
            await self._train_on_batch(batch, step_idx=step_idx)
        except Exception as exc:
            logger.error("[Trainer] train_step_external failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

        # Skill evolution (same logic as the normal training loop)
        await self._maybe_evolve_skills(batch)

        rewards = [s.reward for s in batch]
        mean_r = sum(rewards) / len(rewards)
        success_rate = sum(1 for r in rewards if r > 0) / len(rewards)
        result = {
            "status": "ok",
            "step": step_idx,
            "samples": len(batch),
            "mean_reward": round(mean_r, 4),
            "success_rate": round(success_rate, 4),
        }
        logger.info("[Trainer] train_step_external complete: %s", result)
        return result

    async def serve_manual_trigger(self):
        """Set up the full RL stack (Tinker + proxy + skills) but do NOT
        enter the autonomous training loop.  Instead, keep the proxy alive
        and wait for external ``train_step_external()`` calls via
        ``metaclaw train-step`` or the admin HTTP endpoint.

        This is the entry point used when ``manual_train_trigger=True``.
        """
        await self.setup()

        self.rollout_worker.start()
        self.rollout_worker.resume_submission()
        logger.info(
            "[Trainer] bench-driven mode: proxy serving at http://%s:%d — "
            "waiting for external train-step triggers",
            self.config.proxy_host, self.config.proxy_port,
        )

        # Optionally start programmatic task rollout (same as in run()).
        _env_rollout_task = None
        if self.config.openclaw_env_data_dir:
            proxy_url = f"http://localhost:{self.config.proxy_port}"
            _env_rollout_task = asyncio.create_task(
                rollout_loop(
                    proxy_url=proxy_url,
                    data_dir=self.config.openclaw_env_data_dir,
                    split=self.config.openclaw_env_split,
                    concurrency=self.config.openclaw_env_concurrency,
                    max_steps_per_episode=self.config.openclaw_env_max_steps,
                    temperature=0.6,
                    model_id=self.config.served_model_name,
                )
            )

        # Keep alive until externally cancelled.
        try:
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        finally:
            if _env_rollout_task is not None:
                _env_rollout_task.cancel()
            self.rollout_worker.stop()
            logger.info("[Trainer] bench-driven mode stopped")

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #

    async def _drain_with_pause_check(
        self, batch_size: int
    ) -> list[list[ConversationSample]]:
        """Collect batch_size sample groups, aborting early if pause_event fires.

        Also filters out samples whose skill_generation no longer matches
        self._current_skill_generation to avoid using stale pre-evolution data.
        """
        data: list[list[ConversationSample]] = []
        completed_groups: dict[int, list[ConversationSample]] = {}
        import time as _time
        start = _time.time()
        last_progress = start

        while len(data) < batch_size:
            if self._pause_event.is_set():
                logger.info("[Trainer] pause_event received — stopping batch collection early")
                break

            completed = self.rollout_worker.get_completed_groups()
            if completed:
                last_progress = _time.time()
                for group_id, group in completed:
                    # Filter out samples from a superseded skill generation.
                    fresh = [
                        s for s in group
                        if s.skill_generation >= self._current_skill_generation
                    ]
                    if fresh:
                        completed_groups[group_id] = fresh

            for group_id in sorted(list(completed_groups.keys())):
                if len(data) >= batch_size:
                    break
                data.append(completed_groups.pop(group_id))

            if _time.time() - last_progress > 30:
                logger.info(
                    "[Trainer] waiting for samples: %d/%d, queue=%d",
                    len(data), batch_size, self.rollout_worker.get_queue_size(),
                )
                last_progress = _time.time()

            if len(data) < batch_size and not self._pause_event.is_set():
                await asyncio.sleep(0.1)

        return data

    async def run(self):
        """Full training loop: setup → start worker → collect → train → [evolve] → repeat.

        When a SlowUpdateScheduler is active (scheduler_enabled=True), the loop
        waits for trigger_event before each step and aborts collection if
        pause_event fires (e.g. user became active again).  When the scheduler
        is disabled, both events are pre-set so the loop runs continuously,
        preserving the original behaviour.
        """
        await self.setup()

        external_trigger_mode = (
            self._scheduler is not None and self.config.scheduler_enabled
        )

        # Start rollout worker (starts proxy server in background thread)
        self.rollout_worker.start()
        # Accept inference and queue samples from the start. Only pause during drain+train.
        # Without this, when scheduler is on we stay at _trigger_event.wait() and never
        # reach resume_submission() below, so inference would get 503 until first window.
        self.rollout_worker.resume_submission()
        logger.info(
            "[Trainer] proxy server starting at http://%s:%d",
            self.config.proxy_host, self.config.proxy_port,
        )

        # Optionally start the programmatic task rollout loop as a background task.
        # Set openclaw_env_data_dir to a directory containing <split>.jsonl task files.
        # Leave empty to use passive proxy mode (like OpenClaw-RL).
        _env_rollout_task = None
        if self.config.openclaw_env_data_dir:
            proxy_url = f"http://localhost:{self.config.proxy_port}"
            _env_rollout_task = asyncio.create_task(
                rollout_loop(
                    proxy_url=proxy_url,
                    data_dir=self.config.openclaw_env_data_dir,
                    split=self.config.openclaw_env_split,
                    concurrency=self.config.openclaw_env_concurrency,
                    max_steps_per_episode=self.config.openclaw_env_max_steps,
                    temperature=0.6,
                    model_id=self.config.served_model_name,
                )
            )
            logger.info(
                "[Trainer] task rollout started: data_dir=%s split=%s concurrency=%d",
                self.config.openclaw_env_data_dir,
                self.config.openclaw_env_split,
                self.config.openclaw_env_concurrency,
            )

        step = 0
        while step < self.config.max_steps:
            # Wait for scheduler permission before each step.
            # When external_trigger_mode is False the event is always set,
            # so this is a no-op and the loop runs continuously.
            if external_trigger_mode:
                logger.info(
                    "[Trainer] step %d/%d — waiting for scheduler window …",
                    step + 1, self.config.max_steps,
                )
                await self._trigger_event.wait()
                if self._scheduler is not None:
                    self._scheduler.notify_trainer_started()

            logger.info("[Trainer] step %d/%d — waiting for batch (size=%d) …",
                        step + 1, self.config.max_steps, self.config.batch_size)

            # Resume collection → drain batch (with pause support) → pause
            self.rollout_worker.resume_submission()

            # Prepend any samples carried over from an interrupted window.
            # Only keep samples whose skill_generation still matches.
            carried = [
                s for s in self._pending_batch
                if s.skill_generation >= self._current_skill_generation
            ]
            self._pending_batch.clear()

            groups = await self._drain_with_pause_check(self.config.batch_size)
            batch = carried + [s for group in groups for s in group]

            self.rollout_worker.pause_submission()

            # Handle mid-collection pause: user became active before batch was full.
            if self._pause_event.is_set():
                self._pending_batch.extend(batch)
                self._pause_event.clear()
                self._trigger_event.clear()
                if self._scheduler is not None:
                    self._scheduler.notify_trainer_finished()
                logger.info(
                    "[Trainer] paused by scheduler — saved %d samples for next window",
                    len(self._pending_batch),
                )
                continue

            if not batch:
                logger.warning("[Trainer] empty batch after drain — skipping step")
                if self._scheduler is not None:
                    self._scheduler.notify_trainer_finished()
                continue

            try:
                await self._train_on_batch(batch, step_idx=step + 1)
            finally:
                self.rollout_worker.resume_submission()

            if self._scheduler is not None:
                self._scheduler.notify_trainer_finished()

            step += 1

        logger.info("[Trainer] training complete (%d steps)", self.config.max_steps)
        if self._wandb is not None:
            self._wandb.finish()
        if _env_rollout_task is not None:
            _env_rollout_task.cancel()
        self.rollout_worker.stop()

        if self.skill_evolver:
            logger.info("[Trainer] skill evolution summary: %s",
                        self.skill_evolver.get_update_summary())
