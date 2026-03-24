"""
Data types that mirror the Tinker SDK surface used by data_formatter.py
and api_server.py.

Training path:  TensorData, ModelInput.from_ints(), Datum
Inference path: EncodedTextChunk, ModelInput(chunks=...), SampleSequence, SampleResponse
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import mlx.core as mx


# ------------------------------------------------------------------ #
# Training types (used by data_formatter.py)                         #
# ------------------------------------------------------------------ #

@dataclass
class TensorData:
    """Thin wrapper around an MLX array, convertible from PyTorch tensors."""

    array: mx.array

    @classmethod
    def from_torch(cls, tensor) -> "TensorData":
        import numpy as np
        arr = mx.array(tensor.detach().cpu().numpy())
        return cls(array=arr)

    def to_mlx(self) -> mx.array:
        return self.array

    def __len__(self) -> int:
        return self.array.shape[0]


@dataclass
class Datum:
    """One training example in the tinker-cookbook RL convention."""

    model_input: "ModelInput"
    loss_fn_inputs: Dict[str, TensorData] = field(default_factory=dict)


# ------------------------------------------------------------------ #
# Inference types (used by api_server.py forward_to_backend)         #
# ------------------------------------------------------------------ #

@dataclass
class EncodedTextChunk:
    """Mirrors tinker.EncodedTextChunk.

    api_server.py calls:
        chunk = sdk.EncodedTextChunk(tokens=list(prompt_ids), type="encoded_text")
    """
    tokens: List[int]
    type: str = "encoded_text"


@dataclass
class SampleSequence:
    """One generated sequence returned by SamplingClient.sample_async().

    api_server.py reads:
        seq = response.sequences[0]
        seq.tokens       -> list[int]
        seq.logprobs      -> list[float]
        seq.stop_reason   -> str
    """
    tokens: List[int]
    logprobs: List[float]
    stop_reason: str = "stop"


@dataclass
class SampleResponse:
    """Container returned by SamplingClient.sample_async().

    api_server.py reads:  response.sequences[0]
    """
    sequences: List[SampleSequence]


# ------------------------------------------------------------------ #
# ModelInput (dual-purpose: training + inference)                    #
# ------------------------------------------------------------------ #

@dataclass
class ModelInput:
    """Token sequence for model consumption.

    Training path (data_formatter.py):
        sdk.ModelInput.from_ints(all_tokens[:-1])
        -> uses .tokens

    Inference path (api_server.py):
        sdk.ModelInput(chunks=[chunk])
        -> uses .chunks[0].tokens
    """
    tokens: Optional[mx.array] = None
    chunks: Optional[List[EncodedTextChunk]] = None

    @classmethod
    def from_ints(cls, token_ids: List[int]) -> "ModelInput":
        return cls(tokens=mx.array(token_ids, dtype=mx.int32))

    def get_token_ids(self) -> List[int]:
        """Return plain list of ints regardless of how this was constructed."""
        if self.tokens is not None:
            return self.tokens.tolist()
        if self.chunks:
            return self.chunks[0].tokens
        return []

    def __len__(self) -> int:
        if self.tokens is not None:
            return self.tokens.shape[0]
        if self.chunks:
            return len(self.chunks[0].tokens)
        return 0
