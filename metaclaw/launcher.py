"""
MetaClaw service launcher.

Orchestrates startup in two modes:
  skills_only — proxy + skill injection + auto skill summarization (no Tinker)
  rl          — full RL training stack (proxy + Tinker + PRM + skill evolution)

Also configures OpenClaw to point at the proxy.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import threading
import time
from pathlib import Path
from typing import Optional

from .config_store import ConfigStore

logger = logging.getLogger(__name__)

_PID_FILE = Path.home() / ".metaclaw" / "metaclaw.pid"


class MetaClawLauncher:
    """Start/stop MetaClaw services based on ConfigStore."""

    def __init__(self, config_store: ConfigStore):
        self.cs = config_store
        self._rollout_worker = None
        self._trainer_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def start(self):
        cfg = self.cs.to_metaclaw_config()
        mode = cfg.mode

        logger.info("[Launcher] Starting MetaClaw in %s mode …", mode)
        self._write_pid()
        self._setup_signal_handlers()

        # "madmax" mode = RL with scheduler enabled
        if mode == "madmax":
            cfg.scheduler_enabled = True
            await self._start_rl(cfg)
        elif mode == "skills_only":
            await self._start_skills_only(cfg)
        else:
            await self._start_rl(cfg)

    def stop(self):
        self._stop_event.set()
        if self._rollout_worker is not None:
            try:
                self._rollout_worker.stop()
            except Exception:
                pass
        if self._trainer_task is not None and not self._trainer_task.done():
            self._trainer_task.cancel()
        _PID_FILE.unlink(missing_ok=True)

    # ------------------------------------------------------------------ #
    # Skills-only mode                                                     #
    # ------------------------------------------------------------------ #

    async def _start_skills_only(self, cfg):
        from .prm_scorer import PRMScorer
        from .rollout import AsyncRolloutWorker
        from .skill_evolver import SkillEvolver
        from .skill_manager import SkillManager

        # Set evolver env vars (uses same LLM as the user's chat LLM)
        self._setup_evolver_env(cfg)

        skill_manager: Optional[SkillManager] = None
        if cfg.use_skills:
            Path(cfg.skills_dir).mkdir(parents=True, exist_ok=True)
            skill_manager = SkillManager(
                skills_dir=cfg.skills_dir,
                retrieval_mode=cfg.retrieval_mode,
                embedding_model_path=cfg.embedding_model_path,
                task_specific_top_k=cfg.task_specific_top_k,
            )
            logger.info("[Launcher] SkillManager loaded: %s skills", skill_manager.get_skill_count())

        skill_evolver: Optional[SkillEvolver] = None
        if cfg.enable_skill_evolution and skill_manager is not None:
            try:
                skill_evolver = SkillEvolver(
                    max_new_skills=cfg.max_new_skills,
                    history_path=cfg.skill_evolution_history_path,
                )
                logger.info("[Launcher] SkillEvolver ready (auto-summarize mode)")
            except Exception as e:
                logger.warning("[Launcher] SkillEvolver init failed: %s", e)

        # PRM is optional in skills_only mode
        prm_scorer = None
        if cfg.use_prm and (cfg.prm_provider == "bedrock" or (cfg.prm_url and cfg.prm_api_key)):
            prm_client = None
            if cfg.prm_provider == "bedrock":
                from .bedrock_client import BedrockChatClient
                prm_client = BedrockChatClient(
                    model_id=cfg.prm_model,
                    region=cfg.bedrock_region,
                )
            prm_scorer = PRMScorer(
                prm_url=cfg.prm_url,
                prm_model=cfg.prm_model,
                api_key=cfg.prm_api_key,
                prm_m=cfg.prm_m,
                temperature=cfg.prm_temperature,
                max_new_tokens=cfg.prm_max_new_tokens,
                llm_client=prm_client,
            )

        worker = AsyncRolloutWorker(
            config=cfg,
            sampling_client=None,
            skill_manager=skill_manager,
            prm_scorer=prm_scorer,
            skill_evolver=skill_evolver,
        )
        # In skills_only mode, submission is always enabled
        worker.resume_submission()
        worker.start()
        self._rollout_worker = worker

        logger.info("[Launcher] proxy ready at http://%s:%d", cfg.proxy_host, cfg.proxy_port)

        # Configure the chosen CLI agent to point at the MetaClaw proxy
        from .claw_adapter import configure_claw
        configure_claw(cfg)

        # Keep running until stopped
        while not self._stop_event.is_set():
            await asyncio.sleep(1.0)

    # ------------------------------------------------------------------ #
    # RL mode                                                              #
    # ------------------------------------------------------------------ #

    async def _start_rl(self, cfg):
        from .trainer import MetaClawTrainer

        # Set evolver env vars (may use dedicated evolver or fallback to llm)
        self._setup_evolver_env(cfg)

        # Seed both alias families so downstream SDKs and helper scripts can
        # resolve the same configured backend credentials.
        self._seed_rl_backend_env(cfg)

        # ------------------------------------------------------------------ #
        # Scheduler setup (optional — gated on scheduler_enabled config flag) #
        # ------------------------------------------------------------------ #
        trigger_event = asyncio.Event()
        pause_event   = asyncio.Event()
        scheduler = None

        if cfg.scheduler_enabled:
            from .idle_detector import IdleDetector, LastRequestTracker
            from .scheduler import SlowUpdateScheduler

            request_tracker = LastRequestTracker()
            idle_detector   = IdleDetector(fallback_tracker=request_tracker)

            calendar_client = None
            if cfg.scheduler_calendar_enabled and cfg.scheduler_calendar_credentials_path:
                try:
                    from .calendar_client import GoogleCalendarClient
                    calendar_client = GoogleCalendarClient(
                        credentials_path=cfg.scheduler_calendar_credentials_path,
                        token_path=cfg.scheduler_calendar_token_path,
                    )
                    calendar_client.authenticate()
                    logger.info("[Launcher] Google Calendar client authenticated")
                except ImportError:
                    logger.warning(
                        "[Launcher] Google Calendar dependencies not installed. "
                        "Install with: pip install metaclaw[scheduler]"
                    )
                except Exception as exc:
                    logger.warning("[Launcher] Calendar auth failed: %s — skipping calendar", exc)
                    calendar_client = None

            scheduler = SlowUpdateScheduler(
                config=cfg,
                trigger_event=trigger_event,
                pause_event=pause_event,
                idle_detector=idle_detector,
                calendar_client=calendar_client,
            )
            logger.info(
                "[Launcher] scheduler enabled — RL updates restricted to idle/sleep/calendar windows"
            )
        else:
            # No scheduler: set trigger immediately so the trainer runs continuously
            # (original v0.2 behaviour, fully backward compatible).
            trigger_event.set()

        trainer = MetaClawTrainer(
            cfg, trigger_event, pause_event, scheduler,
            last_request_tracker=request_tracker if cfg.scheduler_enabled else None,
        )

        # Configure the chosen CLI agent once the proxy is about to be ready
        await asyncio.sleep(3)
        from .claw_adapter import configure_claw
        configure_claw(cfg)

        tasks = [asyncio.create_task(trainer.run())]
        if scheduler is not None:
            tasks.append(asyncio.create_task(scheduler.run()))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            if scheduler is not None:
                scheduler.stop()
            _PID_FILE.unlink(missing_ok=True)

    # ------------------------------------------------------------------ #
    # Evolver env vars                                                     #
    # ------------------------------------------------------------------ #

    def _setup_evolver_env(self, cfg):
        """Set OPENAI_* env vars for SkillEvolver."""
        if cfg.evolver_api_base:
            os.environ.setdefault("OPENAI_BASE_URL", cfg.evolver_api_base)
        if cfg.evolver_api_key:
            os.environ.setdefault("OPENAI_API_KEY", cfg.evolver_api_key)
        if cfg.evolver_model_id:
            os.environ.setdefault("SKILL_EVOLVER_MODEL", cfg.evolver_model_id)

    def _seed_rl_backend_env(self, cfg):
        """Export configured RL backend credentials under both alias families."""
        api_key = cfg.configured_api_key()
        base_url = cfg.configured_base_url()
        if api_key:
            os.environ.setdefault("TINKER_API_KEY", api_key)
            os.environ.setdefault("MINT_API_KEY", api_key)
            os.environ.setdefault("WEAVER_API_KEY", api_key)
        if base_url:
            os.environ.setdefault("TINKER_BASE_URL", base_url)
            os.environ.setdefault("MINT_BASE_URL", base_url)
            os.environ.setdefault("WEAVER_BASE_URL", base_url)

    # ------------------------------------------------------------------ #
    # PID / signals                                                        #
    # ------------------------------------------------------------------ #

    def _write_pid(self):
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PID_FILE.write_text(str(os.getpid()))

    def _setup_signal_handlers(self):
        def _handler(signum, frame):
            logger.info("[Launcher] signal %s received — stopping …", signum)
            self.stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, _handler)
            except (OSError, ValueError):
                pass
