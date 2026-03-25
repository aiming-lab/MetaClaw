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

from .config import MetaClawConfig
from .config_store import ConfigStore

logger = logging.getLogger(__name__)

_PID_DIR = Path.home() / ".metaclaw"


def pid_file_for_port(port: int) -> Path:
    """Return the PID file path for the given proxy port."""
    return _PID_DIR / f"metaclaw_{port}.pid"


class MetaClawLauncher:
    """Start/stop MetaClaw services based on ConfigStore."""

    def __init__(self, config_store: ConfigStore):
        self.cs = config_store
        self._rollout_worker = None
        self._trainer_task: Optional[asyncio.Task] = None
        self._memory_upgrade_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()
        self._pid_file: Optional[Path] = None
        self._wechat_proc: Optional[subprocess.Popen] = None

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def start(self):
        cfg = self.cs.to_metaclaw_config()
        mode = cfg.mode

        logger.info("[Launcher] Starting MetaClaw in %s mode …", mode)
        self._pid_file = pid_file_for_port(cfg.proxy_port)
        self._write_pid()
        self._setup_signal_handlers()

        # "auto" mode = RL with scheduler enabled
        if mode == "auto":
            cfg.scheduler_enabled = True
            await self._start_rl(cfg)
        elif mode == "skills_only":
            await self._start_skills_only(cfg)
        else:
            await self._start_rl(cfg)

    def stop(self):
        from .wechat_bridge import terminate_wechat_bridge

        self._stop_event.set()
        terminate_wechat_bridge(self._wechat_proc)
        self._wechat_proc = None
        if self._rollout_worker is not None:
            try:
                self._rollout_worker.stop()
            except Exception:
                pass
        if self._memory_upgrade_task is not None and not self._memory_upgrade_task.done():
            self._memory_upgrade_task.cancel()
        if self._trainer_task is not None and not self._trainer_task.done():
            self._trainer_task.cancel()
        if self._pid_file is not None:
            self._pid_file.unlink(missing_ok=True)

    # ------------------------------------------------------------------ #
    # Skills-only mode                                                     #
    # ------------------------------------------------------------------ #

    async def _start_skills_only(self, cfg):
        from .memory.manager import MemoryManager
        from .memory.upgrade_worker import MemoryUpgradeWorker
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

        memory_manager = None
        if cfg.memory_enabled:
            logger.info(
                "[Launcher] Memory paths: dir=%s store=%s policy=%s telemetry=%s",
                cfg.memory_dir, cfg.memory_store_path,
                cfg.memory_policy_path, cfg.memory_telemetry_path,
            )
            try:
                memory_manager = MemoryManager.from_config(cfg)
                logger.info("[Launcher] MemoryManager ready: store=%s", cfg.memory_store_path)
            except Exception as e:
                logger.warning("[Launcher] MemoryManager init failed: %s", e)

        worker = AsyncRolloutWorker(
            config=cfg,
            sampling_client=None,
            skill_manager=skill_manager,
            prm_scorer=prm_scorer,
            skill_evolver=skill_evolver,
            memory_manager=memory_manager,
        )
        # In skills_only mode, submission is always enabled
        worker.resume_submission()
        worker.start()
        self._rollout_worker = worker

        upgrade_worker = None
        if cfg.memory_enabled and cfg.memory_auto_upgrade_enabled:
            upgrade_worker = MemoryUpgradeWorker(config=cfg)
            self._memory_upgrade_task = asyncio.create_task(upgrade_worker.run())
            logger.info("[Launcher] MemoryUpgradeWorker started (skills_only)")

        logger.info("[Launcher] proxy ready at http://%s:%d", cfg.proxy_host, cfg.proxy_port)

        # WeChat bridge in parallel with OpenClaw CLI (configure can take ~30s).
        asyncio.create_task(self._start_wechat_bridge_when_ready(cfg))

        # Configure openclaw to point at the proxy
        self._configure_openclaw(cfg)

        # Keep running until stopped
        while not self._stop_event.is_set():
            await asyncio.sleep(1.0)

        if upgrade_worker is not None:
            upgrade_worker.stop()

    # ------------------------------------------------------------------ #
    # RL mode                                                              #
    # ------------------------------------------------------------------ #

    async def _start_rl(self, cfg):
        from .memory.upgrade_worker import MemoryUpgradeWorker
        from .trainer import MetaClawTrainer

        # Set evolver env vars (may use dedicated evolver or fallback to llm)
        self._setup_evolver_env(cfg)

        # Set Tinker API key if provided
        data = self.cs.load()
        tinker_key = data.get("rl", {}).get("tinker_api_key", "")
        if tinker_key:
            os.environ.setdefault("TINKER_API_KEY", tinker_key)

        # ------------------------------------------------------------------ #
        # Scheduler setup (optional — gated on scheduler_enabled config flag) #
        # ------------------------------------------------------------------ #
        trigger_event = asyncio.Event()
        pause_event   = asyncio.Event()
        scheduler = None
        request_tracker = None

        if cfg.scheduler_enabled and not cfg.manual_train_trigger:
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
            last_request_tracker=request_tracker,
        )

        # ------------------------------------------------------------------ #
        # Manual-trigger mode: setup + serve, no autonomous training loop     #
        # ------------------------------------------------------------------ #
        if cfg.manual_train_trigger:
            logger.info(
                "[Launcher] manual_train_trigger=True — RL steps via "
                "'metaclaw train-step' or POST /v1/admin/train_step"
            )
            # Wire the trainer reference into the API server so the admin
            # endpoint can schedule train_step_external() on this event loop.
            main_loop = asyncio.get_running_loop()

            # serve_manual_trigger() calls setup() internally, which creates
            # the rollout worker + API server.  After setup we inject the
            # trainer ref.  Use a small wrapper to do this post-setup.
            async def _serve_with_trainer_ref():
                await trainer.setup()
                trainer.rollout_worker._server.set_trainer(trainer, main_loop)
                trainer.rollout_worker.start()
                trainer.rollout_worker.resume_submission()
                logger.info(
                    "[Launcher] proxy ready at http://%s:%d",
                    cfg.proxy_host, cfg.proxy_port,
                )
                asyncio.create_task(self._start_wechat_bridge_when_ready(cfg))
                # Configure openclaw to point at the proxy
                self._configure_openclaw(cfg)
                try:
                    while not self._stop_event.is_set():
                        await asyncio.sleep(1.0)
                except asyncio.CancelledError:
                    pass
                finally:
                    trainer.rollout_worker.stop()

            try:
                await _serve_with_trainer_ref()
            finally:
                if self._pid_file is not None:
                    self._pid_file.unlink(missing_ok=True)
            return

        # ------------------------------------------------------------------ #
        # Normal RL mode: autonomous training loop                            #
        # ------------------------------------------------------------------ #

        # Configure openclaw once the proxy is about to be ready
        await asyncio.sleep(3)
        asyncio.create_task(self._start_wechat_bridge_when_ready(cfg))
        self._configure_openclaw(cfg)

        tasks = [asyncio.create_task(trainer.run())]
        if scheduler is not None:
            tasks.append(asyncio.create_task(scheduler.run()))

        if cfg.memory_enabled and cfg.memory_auto_upgrade_enabled:
            upgrade_worker = MemoryUpgradeWorker(
                config=cfg,
                window_check=scheduler.is_window_open if scheduler is not None else None,
            )
            self._memory_upgrade_task = asyncio.create_task(upgrade_worker.run())
            tasks.append(self._memory_upgrade_task)
            logger.info("[Launcher] MemoryUpgradeWorker started (rl)")
        else:
            upgrade_worker = None

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            if upgrade_worker is not None:
                upgrade_worker.stop()
            if scheduler is not None:
                scheduler.stop()
            if self._pid_file is not None:
                self._pid_file.unlink(missing_ok=True)

    # ------------------------------------------------------------------ #
    # Evolver env vars                                                     #
    # ------------------------------------------------------------------ #

    def _setup_evolver_env(self, cfg):
        """Set OPENAI_* env vars for SkillEvolver.

        In skills_only mode the config.yaml values take priority over any
        pre-existing OPENAI_* env vars (force-assign).  In other modes the
        existing env vars win (setdefault), preserving previous behaviour.
        """
        force = cfg.mode == "skills_only"
        _set = (lambda k, v: os.environ.__setitem__(k, v)) if force else os.environ.setdefault
        if cfg.evolver_api_base:
            _set("OPENAI_BASE_URL", cfg.evolver_api_base)
        if cfg.evolver_api_key:
            _set("OPENAI_API_KEY", cfg.evolver_api_key)
        if cfg.evolver_model_id:
            os.environ.setdefault("SKILL_EVOLVER_MODEL", cfg.evolver_model_id)

    # ------------------------------------------------------------------ #
    # WeChat (Node bridge)                                                 #
    # ------------------------------------------------------------------ #

    async def _start_wechat_bridge_when_ready(self, cfg: MetaClawConfig) -> None:
        """Wait for proxy /healthz, then spawn weixin-agent-sdk → MetaClaw proxy."""
        if not cfg.wechat_enabled:
            return

        logger.info(
            "[Launcher] WeChat enabled — waiting for http://127.0.0.1:%d/healthz …",
            cfg.proxy_port,
        )
        import httpx
        from .wechat_bridge import spawn_wechat_bridge

        url = f"http://127.0.0.1:{cfg.proxy_port}/healthz"
        deadline = time.monotonic() + 120.0
        while time.monotonic() < deadline:
            if self._stop_event.is_set():
                return
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    r = await client.get(url)
                    if r.status_code == 200:
                        self._wechat_proc = spawn_wechat_bridge(cfg)
                        if self._wechat_proc is None:
                            logger.error(
                                "[Launcher] WeChat bridge did not start — run: metaclaw wechat-check"
                            )
                        return
            except Exception:
                pass
            await asyncio.sleep(1.0)
        logger.warning("[Launcher] WeChat bridge skipped: proxy /healthz not ready in 120s")

    # ------------------------------------------------------------------ #
    # OpenClaw wiring                                                      #
    # ------------------------------------------------------------------ #

    def _configure_openclaw(self, cfg):
        """Auto-configure OpenClaw to use the MetaClaw proxy."""
        model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"
        provider_json = json.dumps({
            "api": "openai-completions",
            "baseUrl": f"http://127.0.0.1:{cfg.proxy_port}/v1",
            "apiKey": cfg.api_key or "metaclaw",
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
        self._pid_file.parent.mkdir(parents=True, exist_ok=True)
        self._pid_file.write_text(str(os.getpid()))

    def _setup_signal_handlers(self):
        def _handler(signum, frame):
            logger.info("[Launcher] signal %s received — stopping …", signum)
            self.stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, _handler)
            except (OSError, ValueError):
                pass
