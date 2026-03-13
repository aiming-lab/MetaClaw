"""
MetaClaw service launcher.

Orchestrates startup in two modes:
  skills_only — proxy + skill injection + auto skill summarization (no Tinker)
  rl          — full RL training stack (proxy + Tinker + PRM + skill evolution)

Also configures OpenClaw to point at the proxy.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
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

        if mode == "skills_only":
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
        if cfg.use_prm and cfg.prm_url and cfg.prm_api_key:
            prm_scorer = PRMScorer(
                prm_url=cfg.prm_url,
                prm_model=cfg.prm_model,
                api_key=cfg.prm_api_key,
                prm_m=cfg.prm_m,
                temperature=cfg.prm_temperature,
                max_new_tokens=cfg.prm_max_new_tokens,
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

        # Configure openclaw to point at the proxy
        self._configure_openclaw(cfg)

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

        trainer = MetaClawTrainer(cfg)
        self._trainer_task = asyncio.create_task(trainer.run())

        # Configure openclaw once the proxy is about to be ready
        await asyncio.sleep(3)
        self._configure_openclaw(cfg)

        try:
            await self._trainer_task
        except asyncio.CancelledError:
            pass
        finally:
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
        if base_url:
            os.environ.setdefault("TINKER_BASE_URL", base_url)
            os.environ.setdefault("MINT_BASE_URL", base_url)

    # ------------------------------------------------------------------ #
    # OpenClaw wiring                                                      #
    # ------------------------------------------------------------------ #

    def _configure_openclaw(self, cfg):
        """Auto-configure OpenClaw to use the MetaClaw proxy."""
        model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"
        provider_json = json.dumps({
            "api": "openai-completions",
            "baseUrl": f"http://127.0.0.1:{cfg.proxy_port}/v1",
            "apiKey": cfg.proxy_api_key or "metaclaw",
            "models": [{
                "id": model_id,
                "name": model_id,
                "reasoning": False,
                "input": ["text"],
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                "contextWindow": 32768,
                "maxTokens": 8192,
            }],
        })

        commands = [
            ["openclaw", "config", "set", "models.providers.metaclaw",
             "--json", provider_json],
            ["openclaw", "config", "set", "agents.defaults.model.primary",
             f"metaclaw/{model_id}"],
            ["openclaw", "config", "set", "agents.defaults.sandbox.mode", "off"],
            ["openclaw", "gateway", "restart"],
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode != 0:
                    logger.warning(
                        "[Launcher] openclaw command failed: %s\n  stderr: %s",
                        " ".join(cmd),
                        result.stderr.strip(),
                    )
                else:
                    logger.info("[Launcher] %s → ok", " ".join(cmd[:4]))
            except FileNotFoundError:
                logger.warning(
                    "[Launcher] 'openclaw' not found in PATH — skipping auto-config. "
                    "Run openclaw_model_*.sh manually."
                )
                break
            except Exception as e:
                logger.warning("[Launcher] openclaw config command error: %s", e)

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
