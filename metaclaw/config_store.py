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
    "mode": "skills_only",
    "llm": {
        "provider": "custom",
        "model_id": "",
        "api_base": "",
        "api_key": "",
    },
    "proxy": {"port": 30000, "host": "0.0.0.0", "api_key": ""},
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
        "backend": "auto",
        "model": "",
        "api_key": "",
        "base_url": "",
        "tinker_api_key": "",
        "tinker_base_url": "",
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
        mode = data.get("mode", "skills_only")
        rl_enabled = bool(rl.get("enabled", False))

        # Evolver: prefer rl.evolver_*, fallback to llm.*
        evolver_api_base = rl.get("evolver_api_base") or llm.get("api_base", "")
        evolver_api_key = rl.get("evolver_api_key") or llm.get("api_key", "")
        evolver_model = rl.get("evolver_model") or llm.get("model_id") or "gpt-5.2"

        skills_dir = str(
            Path(skills.get("dir", str(CONFIG_DIR / "skills"))).expanduser()
        )
        rl_backend = str(rl.get("backend", "auto") or "auto")
        rl_api_key = str(rl.get("api_key") or rl.get("tinker_api_key", "") or "")
        rl_base_url = str(rl.get("base_url") or rl.get("tinker_base_url", "") or "")

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
            proxy_api_key=str(proxy.get("api_key", "") or ""),
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
            backend=rl_backend,
            model_name=rl.get("model") or llm.get("model_id") or "Qwen/Qwen3-4B",
            lora_rank=int(rl.get("lora_rank", 32)),
            batch_size=int(rl.get("batch_size", 4)),
            resume_from_ckpt=str(rl.get("resume_from_ckpt", "") or ""),
            api_key=rl_api_key,
            base_url=rl_base_url,
            tinker_api_key=str(rl.get("tinker_api_key", "") or ""),
            tinker_base_url=str(rl.get("tinker_base_url", "") or ""),
            # PRM (only meaningful in rl mode)
            use_prm=bool(rl.get("prm_url")) and rl_enabled,
            prm_url=rl.get("prm_url", "https://api.openai.com/v1"),
            prm_model=rl.get("prm_model", "gpt-5.2"),
            prm_api_key=rl.get("prm_api_key", ""),
            # Evolver
            evolver_api_base=evolver_api_base,
            evolver_api_key=evolver_api_key,
            evolver_model_id=evolver_model,
        )

    def describe(self) -> str:
        """Return a human-readable summary of the current config."""
        data = self.load()
        llm = data.get("llm", {})
        skills = data.get("skills", {})
        rl = data.get("rl", {})
        mode = data.get("mode", "skills_only")
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
                f"rl.backend:      {rl.get('backend', 'auto')}",
                f"rl.model:        {rl.get('model', '?')}",
                f"rl.base_url:     {rl.get('base_url') or rl.get('tinker_base_url', '')}",
                f"rl.prm_url:      {rl.get('prm_url', '?')}",
                f"rl.evolver_model:{rl.get('evolver_model', '?')}",
                f"rl.resume_ckpt:  {rl.get('resume_from_ckpt', '')}",
            ]
        return "\n".join(lines)
