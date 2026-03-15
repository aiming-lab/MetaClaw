"""
MLX-native LoRA training backend for MetaClaw.

Provides a local, zero-cloud alternative to the Tinker and MinT backends
using Apple MLX on Apple Silicon. No API key or network required.
"""

from .data_types import (
    Datum,
    EncodedTextChunk,
    ModelInput,
    SampleResponse,
    SampleSequence,
    TensorData,
)
from .params import AdamParams, SamplingParams
from .service_client import SamplingClient, SaveStateResult, ServiceClient, TrainingClient

__all__ = [
    "AdamParams",
    "Datum",
    "EncodedTextChunk",
    "ModelInput",
    "SampleResponse",
    "SampleSequence",
    "SamplingClient",
    "SamplingParams",
    "SaveStateResult",
    "ServiceClient",
    "TensorData",
    "TrainingClient",
]
