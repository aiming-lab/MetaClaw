"""
Weaver compatibility layer.

Provides the same module-level interface as ``tinker`` / ``mint`` so that
``sdk_backend.py`` can ``import metaclaw.weaver_compat`` and assign it as
``self._sdk``.  Upper-layer code (trainer, api_server, data_formatter) keeps
calling ``self._sdk.ServiceClient``, ``self._sdk.EncodedTextChunk``, etc.
without any change.

Key differences from Tinker/MinT that this adapter handles:

* Weaver uses synchronous methods with ``wait=True/False`` instead of
  native ``*_async()`` coroutines.  We wrap them with
  ``asyncio.to_thread()``.
* The chunk class is ``ModelInputChunk`` (not ``EncodedTextChunk``).
* ``TensorData`` offers ``from_array()`` instead of ``from_torch()``.
* ``ServiceClient`` needs an explicit ``connect()`` + heartbeat.
* Sampling responses are plain ``dict`` objects — we wrap them in
  ``types.SimpleNamespace`` for attribute access.
"""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Any, Sequence

import weaver
import weaver.types

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Loss functions that Weaver supports                                  #
# ------------------------------------------------------------------ #
_SUPPORTED_LOSS_FNS = frozenset({
    "cross_entropy",
    "importance_sampling",
    "truncated_importance_sampling",
    "forward_logprob",
})

# ------------------------------------------------------------------ #
# Type re-exports (same names that Tinker / MinT expose)               #
# ------------------------------------------------------------------ #

# Tinker calls this ``EncodedTextChunk``; Weaver calls it ``ModelInputChunk``.
EncodedTextChunk = weaver.types.ModelInputChunk

ModelInput = weaver.types.ModelInput
SamplingParams = weaver.types.SamplingParams
AdamParams = weaver.types.AdamParams
Datum = weaver.types.Datum


# ------------------------------------------------------------------ #
# TensorData: add from_torch() alias                                   #
# ------------------------------------------------------------------ #

class TensorData(weaver.types.TensorData):
    """TensorData subclass that adds the ``from_torch()`` class method
    expected by MetaClaw's data_formatter."""

    @classmethod
    def from_torch(cls, tensor):
        """Create a TensorData from a PyTorch tensor.

        Delegates to the Weaver SDK's ``from_array()`` which accepts any
        array-like object (including PyTorch tensors).
        """
        return cls.from_array(tensor)


# ------------------------------------------------------------------ #
# SamplingClient wrapper                                               #
# ------------------------------------------------------------------ #

class _SamplingClientWrapper:
    """Wraps a Weaver ``SamplingClient`` to expose ``sample_async()``
    and converts dict responses to attribute-access objects."""

    def __init__(self, inner, service_client: weaver.ServiceClient):
        self._inner = inner
        # Keep the connected ServiceClient alive so it is not garbage-collected
        # while this sampling client still references it internally.
        self._service = service_client

    async def sample_async(
        self,
        prompt,
        num_samples: int = 1,
        sampling_params=None,
        include_prompt_logprobs: bool = False,
        topk_prompt_logprobs: int = 0,
        **kwargs,
    ):
        kw: dict[str, Any] = dict(
            prompt=prompt,
            num_samples=num_samples,
            include_prompt_logprobs=include_prompt_logprobs,
            topk_prompt_logprobs=topk_prompt_logprobs,
        )
        if sampling_params is not None:
            kw["sampling_params"] = sampling_params
        kw.update(kwargs)

        result = await asyncio.to_thread(self._inner.sample, **kw, wait=True)
        return _dict_to_namespace(result)


def _dict_to_namespace(obj):
    """Recursively convert dicts/lists to SimpleNamespace so that
    ``response.sequences[0].tokens`` works the same as with Tinker."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _dict_to_namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_dict_to_namespace(item) for item in obj]
    return obj


# ------------------------------------------------------------------ #
# TrainingClient wrapper                                               #
# ------------------------------------------------------------------ #

class _TrainingClientWrapper:
    """Wraps a Weaver ``TrainingClient`` to expose the ``*_async()``
    interface that MetaClaw's trainer.py expects."""

    def __init__(self, inner, service_client: weaver.ServiceClient):
        self._inner = inner
        self._service = service_client

    async def forward_backward_async(
        self,
        datums: Sequence,
        loss_fn: str,
        **kwargs,
    ):
        if loss_fn not in _SUPPORTED_LOSS_FNS:
            logger.warning(
                "[weaver_compat] loss_fn=%r is not supported by Weaver. "
                "Supported: %s. The request will be sent as-is but may fail.",
                loss_fn,
                sorted(_SUPPORTED_LOSS_FNS),
            )
        return await asyncio.to_thread(
            self._inner.forward_backward, datums, loss_fn, wait=True, **kwargs,
        )

    async def optim_step_async(self, adam_params, **kwargs):
        return await asyncio.to_thread(
            self._inner.optim_step, adam_params, wait=True, **kwargs,
        )

    async def save_weights_and_get_sampling_client_async(
        self, name: str | None = None, **kwargs,
    ):
        sc = await asyncio.to_thread(
            self._inner.save_weights_and_get_sampling_client,
            name=name, wait=True, **kwargs,
        )
        return _SamplingClientWrapper(sc, self._service)

    async def save_state_async(self, name: str | None = None, **kwargs):
        return await asyncio.to_thread(
            self._inner.save_state, name=name, wait=True, **kwargs,
        )

    async def load_state_async(self, path, **kwargs):
        return await asyncio.to_thread(
            self._inner.load_state, path, wait=True, **kwargs,
        )


# ------------------------------------------------------------------ #
# ServiceClient wrapper                                                #
# ------------------------------------------------------------------ #

class ServiceClient:
    """Wraps a Weaver ``ServiceClient`` to expose the Tinker-style
    constructor + ``create_lora_training_client_async()`` interface."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        kw: dict[str, Any] = {}
        if base_url is not None:
            kw["base_url"] = base_url
        if api_key is not None:
            kw["api_key"] = api_key
        self._inner = weaver.ServiceClient(**kw)
        self._inner.connect()

    async def create_lora_training_client_async(
        self,
        base_model: str,
        rank: int = 32,
        **kwargs,
    ):
        from weaver.types import LoraConfig

        tc = await asyncio.to_thread(
            self._inner.create_model,
            base_model=base_model,
            lora_config=LoraConfig(rank=rank),
            **kwargs,
        )
        return _TrainingClientWrapper(tc, self._inner)

    def close(self):
        """Cleanly shut down the underlying Weaver session."""
        try:
            self._inner.close()
        except Exception:
            pass
