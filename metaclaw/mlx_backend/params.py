"""Optimizer and sampling parameter dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AdamParams:
    """Adam optimizer hyperparameters.

    trainer.py calls:  sdk.AdamParams(learning_rate=config.learning_rate)
    """
    learning_rate: float = 1e-4
    beta1: float = 0.9
    beta2: float = 0.999
    eps: float = 1e-8
    weight_decay: float = 0.0


@dataclass
class SamplingParams:
    """Generation parameters for SamplingClient.

    api_server.py calls:
        sdk.SamplingParams(temperature=..., max_tokens=..., top_k=50, top_p=0.95, stop=...)
    """
    temperature: float = 0.6
    top_p: float = 0.9
    max_tokens: int = 2048
    repetition_penalty: float = 1.0
    top_k: int = 50
    stop: Optional[List[str]] = None
