"""
MLX-native ServiceClient, TrainingClient, and SamplingClient.

Implements the same async interface as the ``tinker`` SDK so MetaClaw's
trainer.py and api_server.py can use it as a drop-in local backend.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_unflatten

from .data_types import Datum, ModelInput, SampleResponse, SampleSequence
from .lora import inject_lora, load_lora_weights, save_lora_weights
from .params import AdamParams, SamplingParams

logger = logging.getLogger(__name__)


@dataclass
class SaveStateResult:
    path: str


class SamplingClient:
    """Wraps an MLX model + tokenizer for inference.

    Supports the sample_async() interface that api_server.py calls:
        response = await self.sampling_client.sample_async(
            prompt=model_input,
            num_samples=1,
            sampling_params=sampling_params,
            include_prompt_logprobs=False,
            top_k_prompt_logprobs=0,
        )
        seq = response.sequences[0]
        seq.tokens / seq.logprobs / seq.stop_reason
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        adapter_path: Optional[Path] = None,
    ):
        self._model = model
        self._tokenizer = tokenizer
        self._adapter_path = adapter_path

    @property
    def model(self) -> nn.Module:
        return self._model

    @property
    def tokenizer(self) -> Any:
        return self._tokenizer

    @property
    def adapter_path(self) -> Optional[Path]:
        return self._adapter_path

    async def sample_async(
        self,
        prompt: ModelInput,
        num_samples: int = 1,
        sampling_params: Optional[SamplingParams] = None,
        include_prompt_logprobs: bool = False,
        top_k_prompt_logprobs: int = 0,
    ) -> SampleResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sample_sync, prompt, num_samples, sampling_params
        )

    def _sample_sync(
        self,
        prompt: ModelInput,
        num_samples: int,
        sampling_params: Optional[SamplingParams],
    ) -> SampleResponse:
        from mlx_lm.generate import generate_step
        from mlx_lm.sample_utils import make_sampler

        sp = sampling_params or SamplingParams()
        prompt_ids = prompt.get_token_ids()
        prompt_arr = mx.array(prompt_ids, dtype=mx.int32)

        sampler = make_sampler(temp=sp.temperature, top_p=sp.top_p)

        stop_strings = set(sp.stop or [])
        eos_token_id = getattr(self._tokenizer, "eos_token_id", None)

        stop_token_ids = set()
        if eos_token_id is not None:
            stop_token_ids.add(eos_token_id)
        for s in stop_strings:
            ids = self._tokenizer.encode(s, add_special_tokens=False)
            if len(ids) == 1:
                stop_token_ids.add(ids[0])

        generated_tokens: List[int] = []
        generated_logprobs: List[float] = []

        for step_out, _ in zip(
            generate_step(
                prompt_arr,
                self._model,
                sampler=sampler,
            ),
            range(sp.max_tokens),
        ):
            token, logprob_val = step_out
            token_id = token.item() if hasattr(token, "item") else int(token)

            if token_id in stop_token_ids:
                break

            generated_tokens.append(token_id)

            # logprob_val may be a scalar, a 1-d vocab array, or a dict
            if isinstance(logprob_val, dict):
                lp = float(logprob_val.get("logprob", 0.0))
            elif hasattr(logprob_val, "shape") and logprob_val.ndim > 0:
                lp = float(logprob_val[token_id].item() if hasattr(logprob_val[token_id], "item") else logprob_val[token_id])
            elif hasattr(logprob_val, "item"):
                lp = float(logprob_val.item())
            else:
                lp = float(logprob_val)
            generated_logprobs.append(lp)

            if stop_strings:
                partial = self._tokenizer.decode(generated_tokens)
                if any(s in partial for s in stop_strings):
                    break

        stop_reason = "stop"
        if len(generated_tokens) >= sp.max_tokens:
            stop_reason = "length"

        seq = SampleSequence(
            tokens=generated_tokens,
            logprobs=generated_logprobs,
            stop_reason=stop_reason,
        )
        return SampleResponse(sequences=[seq])


class TrainingClient:
    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        rank: int,
        base_model_name: str,
        output_dir: Path,
    ):
        self._model = model
        self._tokenizer = tokenizer
        self._rank = rank
        self._base_model_name = base_model_name
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._optimizer: Optional[optim.Adam] = None
        self._grads: Optional[list] = None
        self._step_count = 0
        self._last_loss: float = 0.0

    async def forward_backward_async(
        self, data: List[Datum], loss_fn: str = "policy_gradient"
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._forward_backward_sync, data, loss_fn)

    def _forward_backward_sync(self, data: List[Datum], loss_fn: str) -> None:
        model = self._model

        def _loss_fn(model, data):
            total_loss = mx.array(0.0)
            for datum in data:
                input_tokens = datum.model_input.tokens[None, :]
                targets = datum.loss_fn_inputs["target_tokens"].to_mlx()
                advantages = datum.loss_fn_inputs["advantages"].to_mlx()

                logits = model(input_tokens).squeeze(0)
                log_probs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
                token_lp = mx.take_along_axis(
                    log_probs, targets[:, None].astype(mx.int32), axis=-1
                ).squeeze(-1)

                if loss_fn in ("grpo", "policy_gradient", "opd"):
                    total_loss = total_loss + (-mx.sum(advantages * token_lp))
                else:
                    mask = (advantages != 0).astype(mx.float32)
                    total_loss = total_loss + (-mx.sum(mask * token_lp))

            return total_loss / max(len(data), 1)

        loss_grad_fn = nn.value_and_grad(model, _loss_fn)
        loss_val, grads = loss_grad_fn(model, data)
        mx.eval(loss_val)

        self._grads = grads
        self._last_loss = loss_val.item()
        logger.info("[MLX] forward_backward done — loss=%.4f", self._last_loss)

    async def optim_step_async(self, params: AdamParams) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._optim_step_sync, params)

    def _optim_step_sync(self, params: AdamParams) -> None:
        if self._grads is None:
            logger.warning("[MLX] optim_step called with no gradients — skipping")
            return

        if self._optimizer is None or self._optimizer.learning_rate != params.learning_rate:
            self._optimizer = optim.Adam(
                learning_rate=params.learning_rate,
                betas=[params.beta1, params.beta2],
                eps=params.eps,
            )

        self._optimizer.update(self._model, self._grads)
        mx.eval(self._model.trainable_parameters())

        self._grads = None
        self._step_count += 1
        logger.info("[MLX] optim_step done — step=%d", self._step_count)

    async def save_weights_and_get_sampling_client_async(
        self, name: str = "openclaw_lora"
    ) -> SamplingClient:
        adapter_dir = self._output_dir / name
        save_lora_weights(self._model, adapter_dir)
        return SamplingClient(
            model=self._model,
            tokenizer=self._tokenizer,
            adapter_path=adapter_dir,
        )

    async def save_state_async(self, name: str = "checkpoint") -> SaveStateResult:
        import json
        import numpy as np

        ckpt_dir = self._output_dir / "checkpoints" / name
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        save_lora_weights(self._model, ckpt_dir)

        if self._optimizer is not None:
            opt_state = dict(tree_flatten(self._optimizer.state))
            state_arrays = {k: np.array(v) for k, v in opt_state.items()}
            np.savez(str(ckpt_dir / "optimizer_state.npz"), **state_arrays)

        meta = {
            "step_count": self._step_count,
            "rank": self._rank,
            "base_model": self._base_model_name,
            "last_loss": self._last_loss,
        }
        (ckpt_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        path_str = str(ckpt_dir)
        logger.info("[MLX] save_state -> %s", path_str)
        return SaveStateResult(path=path_str)

    async def load_state_async(self, path: str) -> None:
        import json
        import numpy as np

        ckpt_dir = Path(path)
        load_lora_weights(self._model, ckpt_dir)

        opt_path = ckpt_dir / "optimizer_state.npz"
        if opt_path.exists() and self._optimizer is not None:
            npz = np.load(str(opt_path), allow_pickle=False)
            state_flat = [(k, mx.array(npz[k])) for k in npz.files]
            self._optimizer.state = tree_unflatten(state_flat)

        meta_path = ckpt_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            self._step_count = meta.get("step_count", 0)
            self._last_loss = meta.get("last_loss", 0.0)

        logger.info("[MLX] load_state <- %s (step=%d)", path, self._step_count)


class ServiceClient:
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model_path: str = "",
        output_dir: str = "",
    ):
        self._base_url = base_url
        self._api_key = api_key
        self._model_path = model_path
        self._output_dir = output_dir or "./mlx_metaclaw_output"

    async def create_lora_training_client_async(
        self, base_model: str, rank: int = 16
    ) -> TrainingClient:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._create_sync, base_model, rank
        )

    def _create_sync(self, base_model: str, rank: int) -> TrainingClient:
        from mlx_lm import load as mlx_load

        model_id = self._model_path or self._base_url or base_model
        logger.info("[MLX] loading model: %s", model_id)
        model, tokenizer = mlx_load(model_id)

        model.freeze()
        model = inject_lora(model, rank=rank, alpha=float(rank))

        return TrainingClient(
            model=model,
            tokenizer=tokenizer,
            rank=rank,
            base_model_name=base_model,
            output_dir=Path(self._output_dir),
        )
