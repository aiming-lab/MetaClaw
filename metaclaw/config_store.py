"""
User-facing configuration store for MetaClaw.

Reads/writes ~/.metaclaw/config.yaml and bridges to MetaClawConfig.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import MetaClawConfig

CONFIG_DIR = Path.home() / ".metaclaw"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

_DEFAULTS: dict = {
    "mode": "madmax",
    "llm": {
        "provider": "custom",
        "model_id": "",
        "api_base": "",
        "api_key": "",
    },
    "proxy": {"port": 30000, "host": "0.0.0.0"},
    "skills": {
        "enabled": True,
        "dir": str(Path.home() / ".metaclaw" / "skills"),
        "retrieval_mode": "template",
        "top_k": 6,
        "task_specific_top_k": 10,
        "auto_evolve": True,
    },
    "rl": {
        "enabled": False,
        "model": "",
        "tinker_api_key": "",
        "prm_url": "https://api.openai.com/v1",
        "prm_model": "gpt-5.2",
        "prm_api_key": "",
        "lora_rank": 32,
        "batch_size": 4,
        "resume_from_ckpt": "",
        "evolver_api_base": "",
        "evolver_api_key": "",
        "evolver_model": "gpt-5.2",
    },
    "scheduler": {
        "enabled": False,
        "idle_threshold_minutes": 30,
        "sleep_start": "23:00",
        "sleep_end": "07:00",
        "min_window_minutes": 15,
        "calendar": {
            "enabled": False,
            "credentials_path": "",
            "token_path": str(Path.home() / ".metaclaw" / "calendar_token.json"),
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _coerce(value: Any) -> Any:
    """Auto-coerce string values to bool/int/float where obvious."""
    if not isinstance(value, str):
        return value
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


class ConfigStore:
    """Read/write ~/.metaclaw/config.yaml."""

    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = config_file

    def exists(self) -> bool:
        return self.config_file.exists()

    def load(self) -> dict:
        if not self.config_file.exists():
            return _deep_merge({}, _DEFAULTS)
        try:
            import yaml
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return _deep_merge(_DEFAULTS, data)
        except Exception:
            return _deep_merge({}, _DEFAULTS)

    def save(self, data: dict):
        import yaml
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def get(self, dotpath: str) -> Any:
        data = self.load()
        for k in dotpath.split("."):
            if not isinstance(data, dict):
                return None
            data = data.get(k)
        return data

    def set(self, dotpath: str, value: Any):
        data = self.load()
        keys = dotpath.split(".")
        d = data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = _coerce(value)
        self.save(data)

    # ------------------------------------------------------------------ #
    # Bridge to MetaClawConfig                                            #
    # ------------------------------------------------------------------ #

    def to_metaclaw_config(self) -> MetaClawConfig:
        data = self.load()
        llm = data.get("llm", {})
        proxy = data.get("proxy", {})
        skills = data.get("skills", {})
        rl = data.get("rl", {})
        sched = data.get("scheduler", {})
        sched_cal = sched.get("calendar", {})
        mode = data.get("mode", "madmax")
        rl_enabled = mode in ("rl", "madmax") or bool(rl.get("enabled", False))

        # Evolver: prefer rl.evolver_*, fallback to llm.*
        evolver_api_base = rl.get("evolver_api_base") or llm.get("api_base", "")
        evolver_api_key = rl.get("evolver_api_key") or llm.get("api_key", "")
        evolver_model = rl.get("evolver_model") or llm.get("model_id") or "gpt-5.2"

        skills_dir = str(
            Path(skills.get("dir", str(CONFIG_DIR / "skills"))).expanduser()
        )

        return MetaClawConfig(
            # Mode
            mode=mode,
            # LLM for skills_only forwarding
            llm_api_base=llm.get("api_base", ""),
            llm_api_key=llm.get("api_key", ""),
            llm_model_id=llm.get("model_id", ""),
            # Proxy
            proxy_port=proxy.get("port", 30000),
            proxy_host=proxy.get("host", "0.0.0.0"),
            served_model_name=llm.get("model_id") or "metaclaw-model",
            # Skills
            use_skills=bool(skills.get("enabled", True)),
            skills_dir=skills_dir,
            retrieval_mode=skills.get("retrieval_mode", "template"),
            skill_top_k=int(skills.get("top_k", 6)),
            task_specific_top_k=int(skills.get("task_specific_top_k", 10)),
            enable_skill_evolution=bool(skills.get("auto_evolve", True)),
            skill_evolution_history_path=str(Path(skills_dir) / "evolution_history.jsonl"),
            # RL training
            model_name=rl.get("model") or llm.get("model_id") or "Qwen/Qwen3-4B",
            lora_rank=int(rl.get("lora_rank", 32)),
            batch_size=int(rl.get("batch_size", 4)),
            resume_from_ckpt=str(rl.get("resume_from_ckpt", "") or ""),
            # PRM (only meaningful in rl mode)
            use_prm=bool(rl.get("prm_url")) and rl_enabled,
            prm_url=rl.get("prm_url", "https://api.openai.com/v1"),
            prm_model=rl.get("prm_model", "gpt-5.2"),
            prm_api_key=rl.get("prm_api_key", ""),
            # Evolver
            evolver_api_base=evolver_api_base,
            evolver_api_key=evolver_api_key,
            evolver_model_id=evolver_model,
            # Scheduler — madmax mode forces scheduler on
            scheduler_enabled=mode == "madmax" or bool(sched.get("enabled", False)),
            scheduler_idle_threshold_minutes=int(sched.get("idle_threshold_minutes", 30)),
            scheduler_sleep_start=str(sched.get("sleep_start", "23:00")),
            scheduler_sleep_end=str(sched.get("sleep_end", "07:00")),
            scheduler_min_window_minutes=int(sched.get("min_window_minutes", 15)),
            scheduler_calendar_enabled=bool(sched_cal.get("enabled", False)),
            scheduler_calendar_credentials_path=str(sched_cal.get("credentials_path", "")),
            scheduler_calendar_token_path=str(
                sched_cal.get("token_path", "")
                or str(Path.home() / ".metaclaw" / "calendar_token.json")
            ),
        )

    def describe(self) -> str:
        """Return a human-readable summary of the current config."""
        data = self.load()
        llm = data.get("llm", {})
        skills = data.get("skills", {})
        rl = data.get("rl", {})
        mode = data.get("mode", "madmax")
        lines = [
            f"mode:            {mode}",
            f"llm.provider:    {llm.get('provider', '?')}",
            f"llm.model_id:    {llm.get('model_id', '?')}",
            f"llm.api_base:    {llm.get('api_base', '?')}",
            f"proxy.port:      {data.get('proxy', {}).get('port', 30000)}",
            f"skills.enabled:  {skills.get('enabled', True)}",
            f"skills.dir:      {skills.get('dir', '?')}",
            f"skills.evolve:   {skills.get('auto_evolve', True)}",
            f"rl.enabled:      {rl.get('enabled', False)}",
        ]
        if rl.get("enabled"):
            lines += [
                f"rl.model:        {rl.get('model', '?')}",
                f"rl.prm_url:      {rl.get('prm_url', '?')}",
                f"rl.evolver_model:{rl.get('evolver_model', '?')}",
                f"rl.resume_ckpt:  {rl.get('resume_from_ckpt', '')}",
            ]
        return "\n".join(lines)
