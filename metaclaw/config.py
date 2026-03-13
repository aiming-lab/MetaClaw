"""
Unified configuration for MetaClaw training.

Dataclass-based config compatible with command-line overrides.
"""

from dataclasses import dataclass, field


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
    resume_from_ckpt: str = ""    # optional Tinker resume path, e.g. tinker://.../weights/step_0003

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
    max_context_tokens: int = 20000            # hard cap on prompt token count; must match
                                              # Tinker's max_seq_len minus headroom for response

    # ------------------------------------------------------------------ #
    # API Server                                                          #
    # ------------------------------------------------------------------ #
    proxy_port: int = 30000
    proxy_host: str = "0.0.0.0"
    tinker_sampling_url: str = "http://localhost:8080"  # Tinker sampling endpoint
    served_model_name: str = "qwen3-4b"
    api_key: str = ""                         # Optional bearer token check
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
    # LLM for skills_only forwarding (OpenAI-compatible)                 #
    # ------------------------------------------------------------------ #
    llm_api_base: str = ""      # e.g. https://api.moonshot.cn/v1
    llm_api_key: str = ""       # bearer token for upstream LLM
    llm_model_id: str = ""      # model name to forward to

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
