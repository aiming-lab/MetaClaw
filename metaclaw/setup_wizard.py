"""
Interactive first-time setup wizard for MetaClaw.
"""

from __future__ import annotations

from pathlib import Path

from .config_store import CONFIG_DIR, ConfigStore

_API_KEY_PROVIDERS = {
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
        "api_base": "https://api.minimax.chat/v1",
        "model_id": "",
    },
    "novita": {
        "api_base": "https://api.novita.ai/v3/openai",
        "model_id": "",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "model_id": "",
    },
    "volcengine": {
        "api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "model_id": "doubao-seed-2-0-pro-260215",
    },
    "custom": {
        "api_base": "",
        "model_id": "",
    },
}

_OAUTH_TOKEN_PROVIDERS = {
    "anthropic": {
        "model_id": "claude-sonnet-4-6",
        "cli_binary": "claude",
        "env_var": "CLAUDE_CODE_OAUTH_TOKEN",
        "hint": "Claude Code CLI (npm install -g @anthropic-ai/claude-code)",
    },
    "openai-codex": {
        "model_id": "codex-mini",
        "cli_binary": "codex",
        "env_var": "CODEX_OAUTH_TOKEN",
        "hint": "OpenAI Codex CLI (npm install -g @openai/codex)",
    },
    "gemini": {
        "model_id": "gemini-2.5-pro",
        "cli_binary": "gemini",
        "env_var": "GEMINI_OAUTH_TOKEN",
        "hint": "Gemini CLI (npm install -g @anthropic-ai/gemini-cli)",
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

        # ---- Operating mode ----
        current_mode = existing.get("mode", "auto")
        mode = _prompt_choice(
            "Operating mode",
            ["auto", "skills_only", "rl"],
            default=current_mode,
        )

        # ---- LLM auth method ----
        print("\n--- LLM Configuration ---")
        current_llm = existing.get("llm", {})
        current_auth_method = current_llm.get("auth_method", "api_key")

        auth_method = _prompt_choice(
            "Auth method",
            ["oauth_token", "api_key"],
            default=current_auth_method,
        )

        provider = ""
        api_base = ""
        api_key = ""
        model_id = ""
        oauth_token = ""

        if auth_method == "oauth_token":
            # ── OAuth token path: CLI subprocess ──────────────
            print("\n  OAuth token providers use CLI tools (Claude Code, Codex, Gemini).")
            print("  MetaClaw will forward requests via the CLI subprocess.\n")

            current_provider = current_llm.get("provider", "anthropic")
            if current_provider not in _OAUTH_TOKEN_PROVIDERS:
                current_provider = "anthropic"

            provider = _prompt_choice(
                "Provider",
                list(_OAUTH_TOKEN_PROVIDERS.keys()),
                default=current_provider,
            )
            preset = _OAUTH_TOKEN_PROVIDERS[provider]
            print(f"  CLI: {preset['hint']}")

            model_id = _prompt(
                "Model ID",
                default=current_llm.get("model_id") or preset["model_id"],
            )

            # Check for existing stored token
            from .auth_store import AuthStore
            store = AuthStore()
            profile = store.get_best_profile(provider)
            if profile:
                cred_preview = profile.credential[:12] + "..." + profile.credential[-4:]
                print(f"\n  Existing token found: {profile.profile_id} ({cred_preview})")
                update_token = _prompt_bool("Update token", default=False)
            else:
                print(f"\n  No {provider} token found.")
                update_token = True

            if update_token:
                import getpass
                env_var = preset["env_var"]
                print(f"\n  Paste your {provider} OAuth token ({env_var} value).")
                print("  Accepts full JSON or just the access token string.\n")
                try:
                    oauth_token = getpass.getpass("  Token: ")
                except (EOFError, KeyboardInterrupt):
                    print("\n  Skipped.")
                    oauth_token = ""

                if oauth_token.strip():
                    try:
                        profile = store.paste_oauth_token(provider, oauth_token)
                        cred_preview = profile.credential[:12] + "..." + profile.credential[-4:]
                        print(f"  Stored: {profile.profile_id} ({cred_preview})")
                    except ValueError as e:
                        print(f"  Error: {e}")
                        print("  You can set it later: metaclaw config llm.oauth_token <token>")

        else:
            # ── API key path: direct API call ─────────────────
            current_provider = current_llm.get("provider", "custom")
            if current_provider not in _API_KEY_PROVIDERS:
                current_provider = "custom"

            provider = _prompt_choice(
                "Provider",
                list(_API_KEY_PROVIDERS.keys()),
                default=current_provider,
            )
            preset = _API_KEY_PROVIDERS[provider]

            if provider == "custom":
                api_base = _prompt(
                    "API base URL",
                    default=current_llm.get("api_base") or preset["api_base"],
                )
            else:
                api_base = preset["api_base"]
                print(f"  API base: {api_base}")

            model_id = _prompt(
                "Model ID",
                default=current_llm.get("model_id") or preset["model_id"],
            )
            api_key = _prompt(
                "API key",
                default=current_llm.get("api_key", ""),
                hide=True,
            )

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
        rl_enabled = mode in ("rl", "auto")

        if rl_enabled:
            print("\n--- RL Training Configuration ---")
            rl_model = _prompt(
                "Base model for RL training",
                default=rl_config.get("model") or model_id,
            )
            tinker_api_key = _prompt(
                "Tinker API key",
                default=rl_config.get("tinker_api_key", ""),
                hide=True,
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
                "model": rl_model,
                "tinker_api_key": tinker_api_key,
                "prm_url": prm_url,
                "prm_model": prm_model,
                "prm_api_key": prm_api_key,
                "lora_rank": lora_rank,
                "batch_size": rl_config.get("batch_size", 4),
                "resume_from_ckpt": resume_from_ckpt,
                "evolver_api_base": evolver_api_base,
                "evolver_api_key": evolver_api_key,
                "evolver_model": evolver_model,
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


        # ---- OpenClaw Compatibility (advanced) ----
        current_oc = existing.get("openclaw_compat", {})
        show_oc = _prompt_bool(
            "Configure OpenClaw compatibility settings (advanced)",
            default=False,
        )
        if show_oc:
            print("\n--- OpenClaw Compatibility ---")
            print(
                "MetaClaw integrates with OpenClaw v2026.4.10+ via context-engine lifecycle\n"
                "and can suppress built-in Active Memory to avoid duplicate injections."
            )
            oc_context_engine = _prompt_bool(
                "Enable context-engine integration (memory via assemble/compact lifecycle)",
                default=current_oc.get("context_engine_enabled", True),
            )
            oc_active_memory = _prompt_bool(
                "Suppress OpenClaw built-in Active Memory",
                default=current_oc.get("active_memory_compat", True),
            )
            oc_proxy_synergy = _prompt_bool(
                "Force proxy-side synergy (memory+skills) even with context-engine active",
                default=current_oc.get("prefer_proxy_synergy", False),
            )
            oc_min_version = _prompt(
                "Minimum OpenClaw version",
                default=current_oc.get("min_version", "2026.4.10"),
            )
            openclaw_compat_config = {
                "context_engine_enabled": oc_context_engine,
                "active_memory_compat": oc_active_memory,
                "prefer_proxy_synergy": oc_proxy_synergy,
                "min_version": oc_min_version,
            }
        else:
            openclaw_compat_config = current_oc or {
                "context_engine_enabled": True,
                "active_memory_compat": True,
                "prefer_proxy_synergy": False,
                "min_version": "2026.4.10",
            }

        # ---- Write config ----
        data = {
            "mode": mode,
            "llm": {
                "provider": provider,
                "auth_method": auth_method,
                "model_id": model_id,
                "api_base": api_base,
                "api_key": api_key,
            },
            "proxy": {"port": proxy_port, "host": "0.0.0.0"},
            "skills": {
                "enabled": skills_enabled,
                "dir": skills_dir,
                "retrieval_mode": current_skills.get("retrieval_mode", "template"),
                "top_k": current_skills.get("top_k", 6),
                "task_specific_top_k": current_skills.get("task_specific_top_k", 10),
                "auto_evolve": auto_evolve,
                "evolution_every_n_turns": current_skills.get("evolution_every_n_turns", 10),
            },
            "rl": rl_config,
            "scheduler": scheduler_config,
            "openclaw_compat": openclaw_compat_config,
        }

        cs.save(data)
        Path(skills_dir).expanduser().mkdir(parents=True, exist_ok=True)

        print(f"\nConfig saved to: {cs.config_file}")
        print("\nRun 'metaclaw start' to launch MetaClaw.")
        print("=" * 60 + "\n")
