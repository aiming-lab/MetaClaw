"""
Unified configuration for MetaClaw training.

Dataclass-based config compatible with command-line overrides.
"""

from dataclasses import dataclass


@dataclass
class MetaClawConfig:
    # ------------------------------------------------------------------ #
    # Model                                                               #
    # ------------------------------------------------------------------ #
    model_name: str = "Qwen/Qwen3-4B"
    lora_rank: int = 32
    renderer_name: str = "qwen3"  # Tinker renderer: "qwen3", "llama3", "role_colon"

    # ------------------------------------------------------------------ #
    # Training                                                            #
    # ------------------------------------------------------------------ #
    learning_rate: float = 1e-4
    batch_size: int = 4           # Number of ConversationSamples per training step
    max_steps: int = 1000
    loss_fn: str = "importance_sampling"  # "ppo" | "importance_sampling" | "cispo"
    save_weights_timeout_s: float = 200.0  # timeout for sampling-client refresh
    backend: str = "auto"         # "auto" | "tinker" | "mint"
    api_key: str = ""             # neutral RL backend API key
    base_url: str = ""            # neutral RL backend base URL
    resume_from_ckpt: str = ""    # optional Tinker resume path, e.g. tinker://.../weights/step_0003
    tinker_api_key: str = ""      # legacy alias for api_key
    tinker_base_url: str = ""     # legacy alias for base_url

    # ------------------------------------------------------------------ #
    # Reward / PRM                                                        #
    # ------------------------------------------------------------------ #
    use_prm: bool = True
    # Provider: "openai" (any OpenAI-compatible URL) | "bedrock" (AWS Bedrock)
    prm_provider: str = "openai"
    # Any OpenAI-compatible base URL (ignored when prm_provider="bedrock"):
    prm_url: str = "https://api.openai.com/v1"
    prm_model: str = "gpt-5.2"  # judge model
    prm_api_key: str = ""                    # set via env var or directly (ignored for bedrock)
    prm_m: int = 3                           # majority-vote count
    prm_temperature: float = 0.6
    prm_max_new_tokens: int = 1024
    use_opd: bool = False                    # OPD (teacher logprobs) mode
    teacher_url: str = ""                    # Teacher model base URL (OpenAI-compatible /v1/completions)
    teacher_model: str = ""                  # Teacher model name
    teacher_api_key: str = ""                # Teacher model API key
    kl_penalty_coef: float = 1.0             # KL penalty coefficient for OPD

    # ------------------------------------------------------------------ #
    # Skills                                                              #
    # ------------------------------------------------------------------ #
    use_skills: bool = False
    skills_dir: str = "memory_data/skills"    # directory of individual *.md skill files
    retrieval_mode: str = "template"          # "template" | "embedding"
    embedding_model_path: str = "Qwen/Qwen3-Embedding-0.6B"
    skill_top_k: int = 6                      # General skills to inject
    task_specific_top_k: int = 10    # Task-specific skills cap; None means no cap
    enable_skill_evolution: bool = False
    skill_update_threshold: float = 0.4       # Evolve when success rate < threshold
    max_new_skills: int = 3

    # ------------------------------------------------------------------ #
    # Context window                                                       #
    # ------------------------------------------------------------------ #
    max_context_tokens: int = 20000
    # Hard cap on prompt token count sent to the upstream LLM.
    # In rl/madmax mode this must be ≤ (Tinker/MinT max_seq_len − max output
    # tokens) because the full prompt+response must fit the RL backend's
    # training sequence length.
    # Set to 0 to disable truncation entirely.  This is the recommended
    # setting for skills_only mode with large-context cloud models (MiniMax
    # M2.7, Kimi K2, etc.) — there is no RL backend, so there is no
    # sequence-length constraint and truncating arbitrarily loses context.

    context_window: int = 0
    # Context window advertised to the connected agent (e.g. the value
    # OpenClaw uses to decide when to compact the session).
    # 0 = auto: 200 000 for skills_only mode; 32 768 for rl/madmax mode
    # (where the RL backend's sequence-length budget limits usable context).
    # Set this explicitly to match your upstream model's actual context window
    # so OpenClaw compacts only when truly necessary.

    # ------------------------------------------------------------------ #
    # API Server                                                          #
    # ------------------------------------------------------------------ #
    proxy_port: int = 30000
    proxy_host: str = "0.0.0.0"
    tinker_sampling_url: str = "http://localhost:8080"  # Tinker sampling endpoint
    served_model_name: str = "qwen3-4b"
    proxy_api_key: str = ""                   # Optional bearer token check
    record_enabled: bool = True
    record_dir: str = "records/"

    # ------------------------------------------------------------------ #
    # Programmatic task rollout (Qwen3-native, no OpenClaw TUI needed)  #
    # ------------------------------------------------------------------ #
    # Directory containing task JSONL files in slime-compatible format:
    #   <openclaw_env_data_dir>/<split>.jsonl
    # Each line: {"task_id": "...", "instruction": "..."}
    # Leave empty ("") to skip programmatic rollout (passive proxy mode,
    # consistent with OpenClaw-RL's --disable-rollout-global-dataset).
    openclaw_env_data_dir: str = ""           # e.g. "/path/to/tasks"
    openclaw_env_split: str = "train"         # jsonl split name
    openclaw_env_concurrency: int = 4         # parallel episodes
    openclaw_env_max_steps: int = 15          # max turns per episode
    openclaw_env_python_path: str = ""        # unused (kept for compatibility)

    # ------------------------------------------------------------------ #
    # Operating mode                                                      #
    # ------------------------------------------------------------------ #
    # "madmax"        — v0.3: RL + scheduler (trains during idle/sleep windows)
    # "rl"          — v0.2: RL without scheduler (trains immediately on full batch)
    # "skills_only" — proxy + skill injection only (no Tinker, no RL)
    mode: str = "madmax"

    # Which CLI agent to auto-configure on startup.
    # "openclaw" | "copaw" | "ironclaw" | "picoclaw" | "zeroclaw" |
    # "nanoclaw" | "nemoclaw" | "hermes" | "none"
    # "none" skips auto-configuration (standalone / custom setup).
    claw_type: str = "openclaw"

    # Deprecated: kept for backward compatibility.
    # Setting configure_openclaw=False is equivalent to claw_type="none".
    configure_openclaw: bool = True

    # ------------------------------------------------------------------ #
    # Scheduler (meta-learning: gate slow RL updates to idle windows)     #
    # ------------------------------------------------------------------ #
    scheduler_enabled: bool = True
    scheduler_idle_threshold_minutes: int = 30
    scheduler_sleep_start: str = "23:00"   # HH:MM 24h local time
    scheduler_sleep_end: str = "07:00"
    scheduler_min_window_minutes: int = 15  # minimum window needed for one RL step
    scheduler_calendar_enabled: bool = False
    scheduler_calendar_credentials_path: str = ""
    scheduler_calendar_token_path: str = ""  # default set in config_store

    # ------------------------------------------------------------------ #
    # LLM for skills_only forwarding                                     #
    # ------------------------------------------------------------------ #
    llm_provider: str = "openai"  # "openai" | "bedrock" | "openrouter" (any OpenAI-compat URL)
    llm_api_base: str = ""      # e.g. https://api.moonshot.cn/v1 (ignored for bedrock)
    llm_api_key: str = ""       # bearer token for upstream LLM (ignored for bedrock)
    llm_model_id: str = ""      # model name to forward to (bedrock: inference profile ID)

    # ------------------------------------------------------------------ #
    # OpenRouter-specific (ignored for other providers)                    #
    # ------------------------------------------------------------------ #
    openrouter_app_name: str = "MetaClaw"     # X-Title header for attribution
    openrouter_app_url: str = ""              # HTTP-Referer header
    openrouter_route: str = "fallback"        # "fallback" | "price" | "throughput" | "latency"
    openrouter_fallback_models: str = ""      # comma-separated backup model IDs
    openrouter_data_policy: str = ""          # "deny" to avoid data-collecting providers

    # ------------------------------------------------------------------ #
    # LLM for skill evolution                                             #
    # ------------------------------------------------------------------ #
    # Provider: "openai" | "bedrock"
    evolver_provider: str = "openai"
    azure_openai_deployment: str = "o3"  # kept for backward compat
    evolver_api_base: str = ""           # leave empty to reuse llm_api_base
    evolver_api_key: str = ""            # leave empty to reuse llm_api_key
    evolver_model_id: str = "gpt-5.2"
    # AWS Bedrock region (used when prm_provider or evolver_provider = "bedrock")
    bedrock_region: str = "us-east-1"
    skill_evolution_history_path: str = "memory_data/skills/evolution_history.jsonl"

    def configured_backend(self) -> str:
        from .sdk_backend import configured_backend_name

        return configured_backend_name(self)

    def configured_api_key(self) -> str:
        from .sdk_backend import configured_api_key

        return configured_api_key(self)

    def configured_base_url(self) -> str:
        from .sdk_backend import configured_base_url

        return configured_base_url(self)

    def resolved_api_key(self) -> str:
        from .sdk_backend import resolve_api_key

        return resolve_api_key(self)

    def resolved_base_url(self) -> str:
        from .sdk_backend import resolve_base_url

        return resolve_base_url(self)

    def resolved_backend_key(self) -> str:
        from .sdk_backend import infer_backend_key

        return infer_backend_key(self)

    def training_backend_label(self) -> str:
        return "MinT" if self.resolved_backend_key() == "mint" else "Tinker"

    def training_backend_banner(self) -> str:
        return f"{self.training_backend_label()} cloud RL"

    # Backward-compatible accessors used by older code paths and configs.
    def resolved_tinker_api_key(self) -> str:
        return self.resolved_api_key()

    def resolved_tinker_base_url(self) -> str:
        return self.resolved_base_url()

    def training_backend_key(self) -> str:
        return self.resolved_backend_key()
