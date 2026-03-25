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
    skill_evolution_every_n_turns: int = 10  # Every N conversation turns (main turns), run skill evolution on those turns (RL and skills_only)
    skill_update_threshold: float = 0.4       # Evolve when success rate < threshold (trainer batch evolution)
    max_new_skills: int = 3

    # ------------------------------------------------------------------ #
    # Memory                                                              #
    # ------------------------------------------------------------------ #
    memory_enabled: bool = False
    memory_dir: str = "memory_data/store"
    memory_store_path: str = "memory_data/store/memory.db"
    memory_scope: str = "default"
    memory_retrieval_mode: str = "keyword"   # "keyword" | "hybrid" | "embedding"
    memory_use_embeddings: bool = False
    memory_embedding_mode: str = "hashing"  # "hashing" | "semantic"
    memory_embedding_model: str = "all-MiniLM-L6-v2"  # sentence-transformers model name
    memory_embedding_model_path: str = "Qwen/Qwen3-Embedding-0.6B"
    memory_policy_path: str = "memory_data/store/policy.json"
    memory_telemetry_path: str = "memory_data/store/telemetry.jsonl"
    memory_auto_upgrade_enabled: bool = False
    memory_auto_upgrade_interval_seconds: int = 900
    memory_auto_upgrade_require_review: bool = True
    memory_review_stale_after_hours: int = 72
    memory_max_injected_units: int = 6
    memory_max_injected_tokens: int = 800
    memory_auto_extract: bool = True
    memory_auto_consolidate: bool = True
    memory_ignore_turn_type: bool = False   # buffer all turns (incl. side) for memory
    memory_manual_trigger: bool = False     # disable auto-ingest on session_done; use POST /v1/memory/ingest instead

    # ------------------------------------------------------------------ #
    # Skill-Memory Synergy (only active when both are enabled)            #
    # ------------------------------------------------------------------ #
    synergy_enabled: bool = True              # enable coordinated injection
    synergy_token_budget: int = 1200          # combined token cap for skill + memory
    synergy_skill_ratio: float = 0.35         # initial skill share (memory gets 1 - ratio)
    synergy_dedup_threshold: float = 0.5      # Jaccard overlap to drop a procedural memory

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
    # "auto"        — v0.3: RL + scheduler (trains during idle/sleep windows)
    # "rl"          — v0.2: RL without scheduler (trains immediately on full batch)
    # "skills_only" — proxy + skill injection only (no Tinker, no RL)
    mode: str = "auto"
    # When True (RL/auto mode only), the trainer does NOT run its own
    # collection loop.  Instead it waits for ``metaclaw train-step`` CLI
    # invocations (or admin API calls) to trigger individual RL updates.
    manual_train_trigger: bool = False

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

    # ------------------------------------------------------------------ #
    # WeChat personal (Node weixin-agent-sdk bridge → proxy)             #
    # ------------------------------------------------------------------ #
    wechat_enabled: bool = False
    wechat_bridge_dir: str = ""             # optional override; default: package wechat_node/
