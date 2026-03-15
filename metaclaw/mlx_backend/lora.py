"""LoRA layer injection and weight I/O using mlx_lm's built-in tuner."""

from __future__ import annotations

import logging
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten

logger = logging.getLogger(__name__)


def inject_lora(
    model: nn.Module,
    rank: int = 16,
    alpha: float = 16.0,
    num_layers: int = -1,
) -> nn.Module:
    from mlx_lm.tuner.utils import linear_to_lora_layers

    lora_cfg = {"rank": rank, "alpha": alpha, "dropout": 0.0, "scale": alpha / rank}

    linear_to_lora_layers(
        model,
        num_layers=num_layers,
        config=lora_cfg,
    )

    n_train = sum(p.size for _, p in tree_flatten(model.trainable_parameters()))
    n_total = sum(p.size for _, p in tree_flatten(model.parameters()))
    pct = 100 * n_train / n_total if n_total > 0 else 0
    logger.info(
        "[MLX-LoRA] injected adapters (rank=%d alpha=%.1f): "
        "trainable=%d / %d params (%.2f%%)",
        rank, alpha, n_train, n_total, pct,
    )
    return model


def save_lora_weights(model: nn.Module, path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    out_file = path / "adapters.safetensors"

    trainable = dict(tree_flatten(model.trainable_parameters()))
    mx.save_safetensors(str(out_file), trainable)
    logger.info("[MLX-LoRA] saved %d tensors -> %s", len(trainable), out_file)
    return out_file


def load_lora_weights(model: nn.Module, path: str | Path) -> nn.Module:
    path = Path(path)
    adapter_file = path / "adapters.safetensors" if path.is_dir() else path

    model.load_weights(str(adapter_file), strict=False)
    logger.info("[MLX-LoRA] loaded adapters <- %s", adapter_file)
    return model
