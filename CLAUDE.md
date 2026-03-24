# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MetaClaw is an agent that meta-learns and evolves in the wild. It places your model behind a proxy that intercepts interactions from personal agents (OpenClaw, CoPaw, IronClaw, etc.), injects relevant skills at each turn, and meta-learns from accumulated experience. The system supports three operating modes:
- `skills_only`: Lightweight proxy with skill injection (no GPU required)
- `rl`: Skills + RL training with GRPO algorithm
- `madmax`: Skills + RL + smart scheduler (default mode)

## Key Architecture Components

- **API Server** (`api_server.py`): Main proxy server that intercepts LLM requests and injects skills
- **CLI** (`cli.py`): Command-line interface for setup, start, stop, and configuration
- **Configuration** (`config.py`, `config_store.py`): Dataclass-based config system with YAML storage
- **Skill Management** (`skill_manager.py`, `skill_evolver.py`): Handles skill retrieval and evolution
- **Claw Adapters** (`claw_adapter.py`): Integration with various personal agents (OpenClaw, CoPaw, etc.)
- **Training System** (`trainer.py`, `sdk_backend.py`): RL training with support for Tinker, MinT, and MLX backends
- **Scheduler** (`scheduler.py`): Manages RL training during idle/sleep windows to avoid interrupting active use

## MLX Backend Integration

The repository includes MLX backend support for Apple Silicon Macs, allowing local RL training without cloud GPUs. Key MLX files are located in `metaclaw/mlx_backend/`:
- `__init__.py` - Package initialization
- `data_types.py` - MLX-specific data structures
- `params.py` - MLX training parameters
- `lora.py` - LoRA implementation for MLX
- `service_client.py` - MLX implementation of the service client interface

To use MLX backend, configurations in `metaclaw/config.py` may need updates:
- Add `mlx_model_path` and `mlx_output_dir` settings to MetaClawConfig class
- Update `training_backend_label()` and `training_backend_banner()` methods to handle "mlx" backend
- Add "mlx" to the backend selection list in the setup wizard

## Common Commands

```bash
# One-time setup
metaclaw setup

# Start MetaClaw (default: madmax mode)
metaclaw start

# Start in background
metaclaw start --daemon

# Start with specific mode
metaclaw start --mode rl          # RL mode only
metaclaw start --mode skills_only # Skills only mode

# Stop running instance
metaclaw stop

# Check status
metaclaw status

# View configuration
metaclaw config show

# Set configuration values
metaclaw config KEY VALUE

# Skill management
metaclaw skills log --n 10        # Show recent skill evolutions

# Scheduler management
metaclaw scheduler status         # Show scheduler state
```

## Installation & Dependencies

```bash
# Basic installation (skills_only mode)
pip install -e .

# With RL support
pip install -e ".[rl]"

# With full setup (RL + evolution + scheduler)
pip install -e ".[rl,evolve,scheduler]"

# With MLX support (Apple Silicon)
pip install -e ".[mlx]"
```

## Configuration Structure

- Main config file: `~/.metaclaw/config.yaml`
- Skills directory: `~/.metaclaw/skills/`
- Recordings: `records/` directory
- MLX output: Configurable via `mlx_output_dir` setting

## Key Configuration Options

- `mode`: "madmax" (default), "rl", or "skills_only"
- `claw_type`: "openclaw", "copaw", "ironclaw", "nanoclaw", "nemoclaw", or "none"
- `rl.backend`: "auto", "tinker", "mint", or "mlx"
- `skills.enabled`: Enable/disable skill injection
- `rl.enabled`: Enable/disable RL training
- `scheduler.enabled`: Control meta-learning scheduler

## Development Workflow

- Use `metaclaw setup` for initial configuration
- Develop with `metaclaw start` for immediate testing
- Monitor logs and state with `metaclaw status`
- The daemon mode runs in background with logs at `~/.metaclaw/metaclaw.log`