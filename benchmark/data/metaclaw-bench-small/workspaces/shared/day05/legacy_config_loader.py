import json
import os

CONFIG_DEFAULTS = {
    "host": "localhost",
    "port": 8080,
    "debug": False,
    "log_level": "INFO",
    "timeout": 30
}

def load_config(filepath):
    if not os.path.exists(filepath):
        return CONFIG_DEFAULTS.copy()
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    config = CONFIG_DEFAULTS.copy()
    config.update(data)
    return config

def get_config_value(config, key, default=None):
    return config.get(key, default)

def validate_config(config):
    required = ["host", "port"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")
    if not isinstance(config.get("port"), int):
        raise TypeError("Config 'port' must be an integer")
    return True