"""
Interactive first-time setup wizard for MetaClaw.
"""

from __future__ import annotations

import os
from pathlib import Path

from .claw_adapter import CLAW_TYPES
from .config_store import CONFIG_DIR, ConfigStore

_PROVIDER_PRESETS = {
    "kimi": {
        "api_base": "https://api.moonshot.cn/v1",
        "model_id": "moonshotai/Kimi-K2.5",
    },
    "qwen": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen-plus",
    },
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "model_id": "gpt-4o",
    },
    "minimax": {
        "api_base": "https://api.minimax.io/v1",
        "model_id": "MiniMax-M2.5",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "model_id": "google/gemini-2.5-pro",
    },
    "bedrock": {
        "api_base": "",
        "model_id": "us.anthropic.claude-sonnet-4-6",
    },
    "custom": {
        "api_base": "",
        "model_id": "",
    },
}


def _prompt(msg: str, default: str = "", hide: bool = False) -> str:
    import getpass
    if default:
        display_default = "***" if hide else default
        full_msg = f"{msg} [{display_default}]: "
    else:
        full_msg = f"{msg}: "
    try:
        if hide:
            val = getpass.getpass(full_msg)
        else:
            val = input(full_msg)
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return val.strip() or default


def _prompt_bool(msg: str, default: bool = False) -> bool:
    default_str = "Y/n" if default else "y/N"
    val = _prompt(f"{msg} ({default_str})")
    if not val:
        return default
    return val.lower() in {"y", "yes", "true", "1"}


def _prompt_int(msg: str, default: int = 0) -> int:
    while True:
        val = _prompt(msg, str(default))
        try:
            return int(val)
        except ValueError:
            print(f"  Please enter an integer (got: {val!r})")


def _prompt_choice(msg: str, choices: list[str], default: str = "") -> str:
    choices_str = "/".join(
        f"[{c}]" if c == default else c for c in choices
    )
    while True:
        val = _prompt(f"{msg} ({choices_str})", default)
        if val in choices:
            return val
        print(f"  Invalid choice. Pick one of: {choices}")


class SetupWizard:
    """Interactive configuration wizard."""

    def run(self):
        print("\n" + "=" * 60)
        print("  MetaClaw Setup")
        print("=" * 60)
        print("\nThis wizard will create ~/.metaclaw/config.yaml")
        print("You can re-run 'metaclaw setup' at any time to reconfigure.\n")

        cs = ConfigStore()
        existing = cs.load() if cs.exists() else {}

        # ---- CLI agent (claw type) ----
        print("\n--- CLI Agent ---")
        print(
            "MetaClaw will auto-configure the chosen agent to route its LLM\n"
            "calls through the MetaClaw proxy (skills + RL training)."
        )
        current_claw = existing.get("claw_type", "openclaw")
        claw_type = _prompt_choice(
            "CLI agent to configure",
            CLAW_TYPES,
            default=current_claw,
        )

        # ---- Operating mode ----
        current_mode = existing.get("mode", "madmax")
        mode = _prompt_choice(
            "Operating mode",
            ["madmax", "skills_only", "rl"],
            default=current_mode,
        )

        # ---- LLM provider ----
        print("\n--- LLM Configuration ---")
        current_llm = existing.get("llm", {})
        current_provider = current_llm.get("provider", "custom")
        provider = _prompt_choice(
            "LLM provider",
            ["kimi", "qwen", "openai", "minimax", "openrouter", "bedrock", "custom"],
            default=current_provider,
        )
        preset = _PROVIDER_PRESETS[provider]
        openrouter_config: dict = existing.get("openrouter", {})
        if provider == "bedrock":
            api_base = ""
            api_key = ""
            model_id = _prompt(
                "Bedrock model ID (inference profile)",
                default=current_llm.get("model_id") or preset["model_id"],
            )
            bedrock_region = _prompt(
                "AWS region",
                default=current_llm.get("bedrock_region", "us-east-1"),
            )
        else:
            bedrock_region = ""
            api_base = _prompt(
                "API base URL",
                default=current_llm.get("api_base") or preset["api_base"],
            )
            model_id = _prompt(
                "Model ID",
                default=current_llm.get("model_id") or preset["model_id"],
            )
            api_key = _prompt(
                "API key",
                default=current_llm.get("api_key", ""),
                hide=True,
            )

        # OpenRouter-specific options
        if provider == "openrouter":
            print("\n--- OpenRouter Options ---")
            or_route = _prompt_choice(
                "Routing strategy",
                ["fallback", "price", "throughput", "latency"],
                default=openrouter_config.get("route", "fallback"),
            )
            or_fallback = _prompt(
                "Fallback models (comma-separated, optional)",
                default=openrouter_config.get("fallback_models", ""),
            )
            or_data_policy = _prompt_choice(
                "Data collection policy",
                ["allow", "deny"],
                default="deny" if openrouter_config.get("data_policy") == "deny" else "allow",
            )
            openrouter_config = {
                "app_name": "MetaClaw",
                "route": or_route,
                "fallback_models": or_fallback,
                "data_policy": "" if or_data_policy == "allow" else "deny",
            }
        else:
            openrouter_config = {}

        # ---- Skills ----
        print("\n--- Skills Configuration ---")
        current_skills = existing.get("skills", {})
        skills_enabled = _prompt_bool(
            "Enable skill injection", default=current_skills.get("enabled", True)
        )
        default_skills_dir = str(CONFIG_DIR / "skills")
        skills_dir = _prompt(
            "Skills directory",
            default=current_skills.get("dir", default_skills_dir),
        )
        auto_evolve = _prompt_bool(
            "Auto-summarize skills after each conversation",
            default=current_skills.get("auto_evolve", True),
        )

        # ---- Proxy port ----
        print("\n--- Proxy Configuration ---")
        current_proxy = existing.get("proxy", {})
        proxy_port = _prompt_int("Proxy port", default=current_proxy.get("port", 30000))

        # ---- RL config (only if mode uses RL) ----
        rl_config: dict = existing.get("rl", {})
        rl_enabled = mode in ("rl", "madmax")

        if rl_enabled:
            print("\n--- RL Training Configuration ---")
            backend = _prompt_choice(
                "RL backend",
                ["auto", "tinker", "mint"],
                default=str(rl_config.get("backend", "auto") or "auto"),
            )
            rl_model = _prompt(
                "Base model for RL training",
                default=rl_config.get("model") or model_id,
            )
            backend_api_key = _prompt(
                "RL backend API key",
                default=(
                    rl_config.get("api_key")
                    or rl_config.get("tinker_api_key", "")
                ),
                hide=True,
            )
            backend_base_url = _prompt(
                "RL backend base URL (optional)",
                default=(
                    rl_config.get("base_url")
                    or rl_config.get("tinker_base_url")
                    or os.environ.get("TINKER_BASE_URL", "")
                    or os.environ.get("MINT_BASE_URL", "")
                ),
            )
            prm_url = _prompt(
                "PRM (reward model) URL",
                default=rl_config.get("prm_url", "https://api.openai.com/v1"),
            )
            prm_model = _prompt(
                "PRM model ID",
                default=rl_config.get("prm_model", "gpt-5.2"),
            )
            prm_api_key = _prompt(
                "PRM API key",
                default=rl_config.get("prm_api_key", ""),
                hide=True,
            )
            lora_rank = _prompt_int("LoRA rank", default=rl_config.get("lora_rank", 32))
            resume_from_ckpt = _prompt(
                "Resume from checkpoint path (optional)",
                default=rl_config.get("resume_from_ckpt", ""),
            )

            use_custom_evolver = _prompt_bool(
                "Use a separate model for skill evolution (default: same as LLM above)",
                default=bool(rl_config.get("evolver_api_base")),
            )
            if use_custom_evolver:
                evolver_api_base = _prompt(
                    "Evolver API base URL",
                    default=rl_config.get("evolver_api_base", ""),
                )
                evolver_api_key = _prompt(
                    "Evolver API key",
                    default=rl_config.get("evolver_api_key", ""),
                    hide=True,
                )
                evolver_model = _prompt(
                    "Evolver model ID",
                    default=rl_config.get("evolver_model", "gpt-5.2"),
                )
            else:
                evolver_api_base = ""
                evolver_api_key = ""
                evolver_model = ""

            rl_config = {
                "enabled": True,
                "backend": backend,
                "model": rl_model,
                "api_key": backend_api_key,
                "base_url": backend_base_url,
                "prm_provider": rl_config.get("prm_provider", "openai"),
                "prm_url": prm_url,
                "prm_model": prm_model,
                "prm_api_key": prm_api_key,
                "evolver_provider": rl_config.get("evolver_provider", "openai"),
                "evolver_api_base": evolver_api_base,
                "evolver_api_key": evolver_api_key,
                "evolver_model": evolver_model,
                "lora_rank": lora_rank,
                "batch_size": rl_config.get("batch_size", 4),
                "resume_from_ckpt": resume_from_ckpt,
            }
        else:
            rl_config = dict(rl_config)
            rl_config["enabled"] = False

        # ---- Scheduler (only meaningful in RL mode) ----
        current_sched = existing.get("scheduler", {})
        current_sched_cal = current_sched.get("calendar", {})
        scheduler_config: dict = {"enabled": False, "calendar": {"enabled": False}}

        if rl_enabled:
            print("\n--- Scheduler Configuration ---")
            print(
                "The scheduler lets MetaClaw run slow RL weight updates only when\n"
                "you are away from your computer (sleeping, idle, or in a meeting).\n"
                "This avoids interrupting your OpenClaw sessions."
            )
            sched_enabled = _prompt_bool(
                "Enable smart update scheduler",
                default=bool(current_sched.get("enabled", False)),
            )

            if sched_enabled:
                sleep_start = _prompt(
                    "Sleep start time (HH:MM, 24h)",
                    default=current_sched.get("sleep_start", "23:00"),
                )
                sleep_end = _prompt(
                    "Sleep end time   (HH:MM, 24h)",
                    default=current_sched.get("sleep_end", "07:00"),
                )
                idle_mins = _prompt_int(
                    "Idle threshold (minutes before RL may start)",
                    default=current_sched.get("idle_threshold_minutes", 30),
                )
                min_window = _prompt_int(
                    "Minimum window required for one RL step (minutes)",
                    default=current_sched.get("min_window_minutes", 15),
                )

                use_calendar = _prompt_bool(
                    "Use Google Calendar to detect meeting times (optional)",
                    default=bool(current_sched_cal.get("enabled", False)),
                )
                cal_config: dict = {"enabled": False}
                if use_calendar:
                    creds_path = _prompt(
                        "Path to Google Calendar client_secrets.json",
                        default=current_sched_cal.get("credentials_path", ""),
                    )
                    token_path = str(CONFIG_DIR / "calendar_token.json")
                    cal_config = {
                        "enabled": True,
                        "credentials_path": creds_path,
                        "token_path": token_path,
                    }
                    if creds_path:
                        print("\nAuthenticating with Google Calendar…")
                        try:
                            from .calendar_client import GoogleCalendarClient
                            gcal = GoogleCalendarClient(creds_path, token_path)
                            gcal.authenticate()
                            print("Google Calendar authenticated successfully.")
                        except ImportError:
                            print(
                                "  [!] Google Calendar packages not installed.\n"
                                "      Run: pip install metaclaw[scheduler]\n"
                                "      Then re-run 'metaclaw setup' to authenticate."
                            )
                        except Exception as exc:
                            print(
                                f"  [!] Calendar auth failed: {exc}\n"
                                "      You can retry by re-running 'metaclaw setup'."
                            )

                scheduler_config = {
                    "enabled": True,
                    "sleep_start": sleep_start,
                    "sleep_end": sleep_end,
                    "idle_threshold_minutes": idle_mins,
                    "min_window_minutes": min_window,
                    "calendar": cal_config,
                }
            else:
                scheduler_config = {"enabled": False, "calendar": {"enabled": False}}

        # ---- Write config ----
        proxy_config = dict(current_proxy)
        proxy_config["port"] = proxy_port
        proxy_config.setdefault("host", "0.0.0.0")
        data = {
            "claw_type": claw_type,
            "mode": mode,
            "llm": {
                "provider": provider,
                "model_id": model_id,
                "api_base": api_base,
                "api_key": api_key,
                "bedrock_region": bedrock_region,
            },
            "openrouter": openrouter_config,
            "proxy": proxy_config,
            "skills": {
                "enabled": skills_enabled,
                "dir": skills_dir,
                "retrieval_mode": current_skills.get("retrieval_mode", "template"),
                "top_k": current_skills.get("top_k", 6),
                "task_specific_top_k": current_skills.get("task_specific_top_k", 10),
                "auto_evolve": auto_evolve,
            },
            "rl": rl_config,
            "scheduler": scheduler_config,
        }

        cs.save(data)
        Path(skills_dir).expanduser().mkdir(parents=True, exist_ok=True)

        print(f"\nConfig saved to: {cs.config_file}")
        print("\nRun 'metaclaw start' to launch MetaClaw.")
        print("=" * 60 + "\n")
