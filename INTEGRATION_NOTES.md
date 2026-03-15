# MLX Backend Integration Notes

## Files to add
- `metaclaw/mlx_backend/__init__.py`
- `metaclaw/mlx_backend/data_types.py`
- `metaclaw/mlx_backend/params.py`
- `metaclaw/mlx_backend/lora.py`
- `metaclaw/mlx_backend/service_client.py`
- `tests/test_mlx_backend.py`

## Files to replace
- `metaclaw/sdk_backend.py` (full replacement with MLX support)

## Files to patch (small edits)

### metaclaw/setup_wizard.py
# In metaclaw/setup_wizard.py, update line ~156:
#
# BEFORE:
#     ["auto", "tinker", "mint"],
#
# AFTER:
#     ["auto", "tinker", "mint", "mlx"],
#
# This adds "mlx" to the interactive backend selection menu.


### metaclaw/config.py
# In metaclaw/config.py, add these fields to MetaClawConfig:
#
#     # MLX backend settings
#     mlx_model_path: str = ""          # local path or HF repo (e.g. mlx-community/Qwen2.5-7B-4bit)
#     mlx_output_dir: str = "./mlx_metaclaw_output"
#
# Update training_backend_label() around line 168:
#
# BEFORE:
#     def training_backend_label(self) -> str:
#         return "MinT" if self.resolved_backend_key() == "mint" else "Tinker"
#
# AFTER:
#     def training_backend_label(self) -> str:
#         key = self.resolved_backend_key()
#         if key == "mlx":
#             return "MLX"
#         return "MinT" if key == "mint" else "Tinker"
#
# Update training_backend_banner() around line 171:
#
# BEFORE:
#     def training_backend_banner(self) -> str:
#         return f"{self.training_backend_label()} cloud RL"
#
# AFTER:
#     def training_backend_banner(self) -> str:
#         label = self.training_backend_label()
#         suffix = "local RL" if self.resolved_backend_key() == "mlx" else "cloud RL"
#         return f"{label} {suffix}"


## Optional: pyproject.toml extras

```toml
[project.optional-dependencies]
mlx = ["mlx>=0.22.0", "mlx-lm>=0.21.0", "safetensors"]
```

## Usage

```bash
# Install with MLX extras
pip install -e ".[mlx]"

# Configure
metaclaw setup   # select backend → mlx

# Or via env
export METACLAW_RL_BACKEND=mlx
metaclaw start
```
