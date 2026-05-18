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
        # Legacy bridge proc removed — WeChat now handled by official openclaw-weixin plugin

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
        self._stop_event.set()
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

        # Configure openclaw to point at the proxy (also installs openclaw-weixin if enabled)
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
                # Configure openclaw to point at the proxy (also installs openclaw-weixin if enabled)
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
            _set("SKILL_EVOLVER_MODEL", cfg.evolver_model_id)
        elif not os.environ.get("SKILL_EVOLVER_MODEL"):
            logger.warning(
                "[Launcher] No evolver model configured (rl.evolver_model and llm.model_id "
                "are both empty). Skill evolution will be disabled. Set rl.evolver_model "
                "or llm.model_id in config.yaml to enable it."
            )
            if cfg.enable_skill_evolution:
                cfg.enable_skill_evolution = False

    # ------------------------------------------------------------------ #
    # OpenClaw wiring                                                      #
    # ------------------------------------------------------------------ #

    def _configure_openclaw(self, cfg):
        """Auto-configure OpenClaw to use the MetaClaw proxy."""
        model_id = cfg.llm_model_id or cfg.served_model_name or "metaclaw-model"

        # Skip if already configured — avoid unnecessary gateway restarts
        try:
            cur = subprocess.run(
                ["openclaw", "config", "get", "agents.defaults.model.primary"],
                capture_output=True, text=True, timeout=10,
            )
            if cur.returncode == 0 and f"metaclaw/{model_id}" in cur.stdout:
                logger.info("[Launcher] openclaw already configured for metaclaw — skipping auto-config")
                return
        except Exception:
            pass

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

        # Install official WeChat plugin if enabled and not already installed.
        # npx install restarts the gateway itself, so track whether we need our own restart.
        weixin_just_installed = False
        if cfg.wechat_enabled:
            weixin_just_installed = self._ensure_openclaw_weixin_plugin()

        commands = [
            ["openclaw", "config", "set", "models.providers.metaclaw",
             "--json", provider_json],
            ["openclaw", "config", "set", "agents.defaults.model.primary",
             f"metaclaw/{model_id}"],
            ["openclaw", "config", "set", "agents.defaults.sandbox.mode", "off"],
        ]
        # Skip gateway restart if npx install already restarted it.
        if not weixin_just_installed:
            commands.append(["openclaw", "gateway", "restart"])

        for cmd in commands:
            cmd_timeout = 90 if "gateway" in cmd else 15
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=cmd_timeout,
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

    def _ensure_openclaw_weixin_plugin(self) -> bool:
        """Install the official @tencent-weixin/openclaw-weixin plugin if not present.

        Returns True if the plugin was just installed (npx install ran and restarted the gateway).
        """
        install_dir = Path.home() / ".openclaw" / "extensions" / "openclaw-weixin"
        files_exist = (install_dir / "package.json").exists()
        config_ok = self._openclaw_weixin_registered()

        if files_exist and config_ok:
            logger.info("[Launcher] openclaw-weixin plugin already installed")
            self._ensure_openclaw_weixin_allow()
            return False

        if files_exist and not config_ok:
            logger.info("[Launcher] openclaw-weixin files present but not registered in openclaw.json — re-running install")

        logger.info("[Launcher] Installing official WeChat plugin (openclaw-weixin)…")
        try:
            proc = subprocess.Popen(
                ["npx", "-y", "@tencent-weixin/openclaw-weixin-cli@latest", "install"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            # Stream output but only show QR code and key status lines, translated to English
            import re
            _qr_pass = re.compile(
                r"▄|█|▀|二维码|QR|扫码|scan|连接成功|connected|等待连接|waiting"
                r"|https://liteapp\.weixin\.qq\.com",
                re.IGNORECASE,
            )
            _zh_en = {
                "正在启动微信扫码登录...": "Starting WeChat QR login...",
                "使用微信扫描以下二维码，以完成连接：": "Scan the QR code below with WeChat to connect:",
                "如果二维码未能成功展示，请用浏览器打开以下链接扫码：": "If the QR code doesn't display, open this link in a browser:",
                "等待连接结果...": "Waiting for connection...",
                "与微信连接成功！": "WeChat connected successfully!",
            }
            for line in proc.stdout:
                if _qr_pass.search(line):
                    for zh, en in _zh_en.items():
                        if zh in line:
                            line = line.replace(zh, en)
                            break
                    print(line, end="", flush=True)
            proc.wait(timeout=300)
            if proc.returncode == 0:
                logger.info("[Launcher] openclaw-weixin plugin installed ✓")
                self._ensure_openclaw_weixin_allow()
                return True
            else:
                logger.warning(
                    "[Launcher] openclaw-weixin install failed (exit %d)",
                    proc.returncode,
                )
        except FileNotFoundError:
            logger.warning(
                "[Launcher] npx not found — install Node.js ≥ 18 to enable WeChat. "
                "Or run manually: npx -y @tencent-weixin/openclaw-weixin-cli@latest install"
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.warning("[Launcher] openclaw-weixin install timed out (300s)")
        except Exception as e:
            logger.warning("[Launcher] openclaw-weixin install error: %s", e)
        return False

    @staticmethod
    def _openclaw_weixin_registered() -> bool:
        """Check if openclaw-weixin is registered in openclaw.json (entries)."""
        import json as _json

        oc_config = Path.home() / ".openclaw" / "openclaw.json"
        if not oc_config.exists():
            return False
        try:
            data = _json.loads(oc_config.read_text(encoding="utf-8"))
            plugins = data.get("plugins", {})
            return "openclaw-weixin" in plugins.get("entries", {})
        except Exception:
            return False

    @staticmethod
    def _ensure_openclaw_weixin_allow():
        """Ensure openclaw-weixin has full provenance in openclaw.json (allow + load.paths)."""
        import json as _json

        oc_config = Path.home() / ".openclaw" / "openclaw.json"
        install_path = str(Path.home() / ".openclaw" / "extensions" / "openclaw-weixin")
        if not oc_config.exists():
            return
        try:
            data = _json.loads(oc_config.read_text(encoding="utf-8"))
            plugins = data.setdefault("plugins", {})
            changed = False

            # plugins.allow
            allow = plugins.setdefault("allow", [])
            if "openclaw-weixin" not in allow:
                allow.append("openclaw-weixin")
                changed = True

            # plugins.load.paths — gives the gateway "load-path provenance"
            load = plugins.setdefault("load", {})
            paths = load.setdefault("paths", [])
            if install_path not in paths:
                paths.append(install_path)
                changed = True

            if changed:
                oc_config.write_text(_json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                logger.info("[Launcher] patched openclaw.json: openclaw-weixin allow + load.paths")
        except Exception as e:
            logger.debug("[Launcher] could not patch plugins config: %s", e)

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
