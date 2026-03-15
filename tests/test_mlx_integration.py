"""
Integration tests for the MLX LoRA training backend.

Runs the real MLX backend against a small model to verify the full
trainer.py contract: ServiceClient → TrainingClient → SamplingClient.

Skipped automatically on machines without Apple Silicon / MLX.

Run via pytest:
    pytest tests/test_mlx_integration.py -v
    pytest tests/test_mlx_integration.py -v -k smoke
    pytest tests/test_mlx_integration.py -v -k training
    pytest tests/test_mlx_integration.py -v -k e2e

Run standalone:
    python tests/test_mlx_integration.py smoke
    python tests/test_mlx_integration.py training
    python tests/test_mlx_integration.py e2e
    python tests/test_mlx_integration.py all
    python tests/test_mlx_integration.py all --model mlx-community/Llama-3.2-3B-Instruct-4bit
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not (importlib.util.find_spec("mlx") and importlib.util.find_spec("mlx_lm")),
    reason="requires Apple Silicon with mlx and mlx_lm installed",
)

TEST_MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
OUTPUT_DIR = "/tmp/mlx_metaclaw_tests"


# ------------------------------------------------------------------ #
# Fixtures                                                           #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def training_client():
    """Create a TrainingClient once for the whole module."""
    from metaclaw.mlx_backend import ServiceClient

    async def _create():
        client = ServiceClient(output_dir=OUTPUT_DIR)
        return await client.create_lora_training_client_async(
            base_model=TEST_MODEL, rank=8
        )

    return asyncio.get_event_loop().run_until_complete(_create())


@pytest.fixture(scope="module")
def tokenizer(training_client):
    return training_client._tokenizer


# ------------------------------------------------------------------ #
# Helpers                                                            #
# ------------------------------------------------------------------ #

def _make_datums(tokenizer, sdk, prompts_and_responses):
    """Build Datum objects the same way data_formatter.py does."""
    import torch

    datums = []
    for prompt, response, advantage in prompts_and_responses:
        p_ids = tokenizer.encode(prompt)
        r_ids = tokenizer.encode(response)
        all_ids = p_ids + r_ids
        T = len(all_ids) - 1
        if T <= 0:
            continue

        advantages = [0.0] * (len(p_ids) - 1) + [advantage] * len(r_ids)
        logprobs = [0.0] * (len(p_ids) - 1) + [-0.5] * len(r_ids)

        def _fit(lst, length):
            return (lst[:length] + [0.0] * max(0, length - len(lst)))[:length]

        datums.append(sdk.Datum(
            model_input=sdk.ModelInput.from_ints(all_ids[:-1]),
            loss_fn_inputs={
                "target_tokens": sdk.TensorData.from_torch(
                    torch.tensor(all_ids[1:], dtype=torch.long)
                ),
                "logprobs": sdk.TensorData.from_torch(
                    torch.tensor(_fit(logprobs, T), dtype=torch.float32)
                ),
                "advantages": sdk.TensorData.from_torch(
                    torch.tensor(_fit(advantages, T), dtype=torch.float32)
                ),
            },
        ))
    return datums


def _make_batch(tokenizer):
    """Build ConversationSamples as the rollout worker would."""
    from metaclaw.data_formatter import ConversationSample

    samples = []
    for i, (q, a, reward) in enumerate([
        ("What is 2+2?", "4", 1.0),
        ("Capital of France?", "Paris", 1.0),
        ("Solve x^2=9", "x=2", -1.0),
        ("Hello", "Hi there!", 0.0),
    ]):
        p_ids = tokenizer.encode(q)
        r_ids = tokenizer.encode(a)
        samples.append(ConversationSample(
            session_id=f"test_{i}",
            turn_num=0,
            prompt_tokens=p_ids,
            response_tokens=r_ids,
            response_logprobs=[-0.5] * len(r_ids),
            loss_mask=[1] * len(r_ids),
            reward=reward,
        ))
    return samples


# ------------------------------------------------------------------ #
# Smoke tests                                                        #
# ------------------------------------------------------------------ #

class TestSmoke:
    def test_model_loads(self, training_client):
        assert training_client._model is not None
        assert training_client._tokenizer is not None

    def test_lora_injected(self, training_client):
        
        from mlx.utils import tree_flatten
        n_train = sum(p.size for _, p in tree_flatten(training_client._model.trainable_parameters()))
        assert n_train > 0, "No trainable (LoRA) parameters found"

    def test_forward_pass(self, training_client):
        import mlx.core as mx

        tokens = mx.array([[1, 2, 3, 4, 5]], dtype=mx.int32)
        logits = training_client._model(tokens)
        assert len(logits.shape) == 3

    def test_initial_sampling_client(self, training_client):
        sc = asyncio.get_event_loop().run_until_complete(
            training_client.save_weights_and_get_sampling_client_async()
        )
        assert sc.model is not None
        assert sc.tokenizer is not None
        assert sc.adapter_path is not None
        assert (sc.adapter_path / "adapters.safetensors").exists()


# ------------------------------------------------------------------ #
# Training step tests                                                #
# ------------------------------------------------------------------ #

class TestTraining:
    def test_forward_backward(self, training_client, tokenizer):
        import metaclaw.mlx_backend as sdk

        datums = _make_datums(tokenizer, sdk, [
            ("What is 2+2?", "4", 1.0),
            ("Capital of France?", "London", -1.0),
        ])
        assert len(datums) == 2

        asyncio.get_event_loop().run_until_complete(
            training_client.forward_backward_async(datums, loss_fn="policy_gradient")
        )
        assert training_client._grads is not None
        assert len(training_client._grads) > 0

    def test_optim_step(self, training_client):
        from metaclaw.mlx_backend import AdamParams

        asyncio.get_event_loop().run_until_complete(
            training_client.optim_step_async(AdamParams(learning_rate=1e-4))
        )
        assert training_client._grads is None
        assert training_client._step_count >= 1

    def test_save_weights_returns_sampling_client(self, training_client):
        sc = asyncio.get_event_loop().run_until_complete(
            training_client.save_weights_and_get_sampling_client_async(
                name="test_adapter"
            )
        )
        assert sc.adapter_path is not None
        assert (sc.adapter_path / "adapters.safetensors").exists()

    def test_checkpoint_roundtrip(self, training_client):
        async def _run():
            result = await training_client.save_state_async(name="test_ckpt")
            ckpt = Path(result.path)
            assert (ckpt / "adapters.safetensors").exists()
            assert (ckpt / "optimizer_state.npz").exists()
            assert (ckpt / "meta.json").exists()

            step_before = training_client._step_count
            await training_client.load_state_async(result.path)
            assert training_client._step_count == step_before

        asyncio.get_event_loop().run_until_complete(_run())


# ------------------------------------------------------------------ #
# End-to-end: uses real data_formatter.py like trainer.py does       #
# ------------------------------------------------------------------ #

class TestEndToEnd:
    def test_three_step_training_loop(self, training_client, tokenizer):
        """Simulate trainer.py _train_on_batch for 3 steps."""
        import metaclaw.mlx_backend as sdk
        from metaclaw.data_formatter import batch_to_datums, compute_advantages

        batch = _make_batch(tokenizer)

        async def _run():
            sampling_client = None
            for step in range(1, 4):
                advantages = compute_advantages(batch)
                datums = batch_to_datums(batch, advantages, sdk=sdk)
                assert len(datums) > 0, f"Step {step}: no datums"

                await training_client.forward_backward_async(datums, loss_fn="grpo")
                await training_client.optim_step_async(
                    sdk.AdamParams(learning_rate=1e-4)
                )
                sampling_client = (
                    await training_client.save_weights_and_get_sampling_client_async(
                        name="openclaw_lora"
                    )
                )

            assert sampling_client is not None
            assert sampling_client.adapter_path is not None
            assert (sampling_client.adapter_path / "adapters.safetensors").exists()

            result = await training_client.save_state_async(name="e2e_final")
            assert Path(result.path).exists()

        asyncio.get_event_loop().run_until_complete(_run())


# ------------------------------------------------------------------ #
# Standalone CLI runner                                              #
# ------------------------------------------------------------------ #

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"


def _cli_run(model_id: str = TEST_MODEL):
    """Run all tests outside pytest with human-readable output."""
    import metaclaw.mlx_backend as sdk
    from metaclaw.mlx_backend import ServiceClient, AdamParams
    from metaclaw.data_formatter import batch_to_datums, compute_advantages
    import mlx.core as mx

    passed, failed = 0, 0

    def _check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            print(f"  {PASS} {name}" + (f"  ({detail})" if detail else ""))
            passed += 1
        else:
            print(f"  {FAIL} {name}" + (f"  ({detail})" if detail else ""))
            failed += 1

    async def _run():
        # ---- Smoke ------------------------------------------------
        print(f"\n{'='*60}")
        print(f"  SMOKE — {model_id}")
        print(f"{'='*60}")

        t0 = time.time()
        client = ServiceClient(output_dir=OUTPUT_DIR)
        tc = await client.create_lora_training_client_async(
            base_model=model_id, rank=8
        )
        _check("Model loaded", tc._model is not None, f"{time.time()-t0:.1f}s")

        from mlx.utils import tree_flatten as tf
        n_train = sum(p.size for _, p in tf(tc._model.trainable_parameters()))
        n_total = sum(p.size for _, p in tf(tc._model.parameters()))
        _check("LoRA injected", n_train > 0, f"{n_train:,} trainable / {n_total:,} total params")

        tokens = mx.array([[1, 2, 3, 4, 5]], dtype=mx.int32)
        logits = tc._model(tokens)
        _check("Forward pass", len(logits.shape) == 3, f"shape={logits.shape}")

        sc = await tc.save_weights_and_get_sampling_client_async()
        _check("Initial SamplingClient", sc.adapter_path is not None)

        # ---- Training ---------------------------------------------
        print(f"\n{'='*60}")
        print(f"  TRAINING")
        print(f"{'='*60}")

        datums = _make_datums(tc._tokenizer, sdk, [
            ("What is 2+2?", "4", 1.0),
            ("Capital of France?", "London", -1.0),
        ])
        _check("Built datums", len(datums) == 2)

        t0 = time.time()
        await tc.forward_backward_async(datums, loss_fn="policy_gradient")
        _check("forward_backward_async", tc._grads is not None, f"{time.time()-t0:.2f}s")

        t0 = time.time()
        await tc.optim_step_async(AdamParams(learning_rate=1e-4))
        _check("optim_step_async", tc._grads is None, f"{time.time()-t0:.2f}s")

        sc = await tc.save_weights_and_get_sampling_client_async(name="test_adapter")
        _check("save_weights", (sc.adapter_path / "adapters.safetensors").exists())

        result = await tc.save_state_async(name="test_ckpt")
        ckpt = Path(result.path)
        _check("save_state", all(
            (ckpt / f).exists() for f in ("adapters.safetensors", "optimizer_state.npz", "meta.json")
        ), result.path)

        step_before = tc._step_count
        await tc.load_state_async(result.path)
        _check("load_state roundtrip", tc._step_count == step_before)


        # ---- INFERENCE (sample_async) --------------------------------
        print("\n" + "=" * 60)
        print(f"  INFERENCE (sample_async)")
        print("=" * 60)

        from metaclaw.mlx_backend import EncodedTextChunk, SamplingParams as SP
        from metaclaw.mlx_backend import ModelInput as MI

        prompt_text = "Hello, how are you?"
        prompt_ids = list(tc._tokenizer.encode(prompt_text, add_special_tokens=False))
        chunk = EncodedTextChunk(tokens=prompt_ids, type="encoded_text")
        model_input = MI(chunks=[chunk])

        _check("ModelInput.get_token_ids()", model_input.get_token_ids() == prompt_ids, f"{len(prompt_ids)} tokens")

        sampling_params = SP(temperature=0.7, max_tokens=32, top_k=50, top_p=0.95)

        t0 = time.time()
        response = await sc.sample_async(
            prompt=model_input,
            num_samples=1,
            sampling_params=sampling_params,
            include_prompt_logprobs=False,
            top_k_prompt_logprobs=0,
        )
        inf_time = time.time() - t0

        seq = response.sequences[0]
        _check(
            "sample_async",
            len(seq.tokens) > 0 and len(seq.logprobs) == len(seq.tokens),
            f"{len(seq.tokens)} tokens, stop={seq.stop_reason}, {inf_time:.2f}s",
        )

        decoded = tc._tokenizer.decode(seq.tokens, skip_special_tokens=True)
        _check("decode response", len(decoded) > 0, f"{repr(decoded[:80])}")

        # ---- End-to-end -------------------------------------------
        print(f"\n{'='*60}")
        print(f"  END-TO-END (3-step training loop)")
        print(f"{'='*60}")

        batch = _make_batch(tc._tokenizer)
        _check("Built batch", len(batch) == 4, f"{len(batch)} samples")

        for step in range(1, 4):
            t0 = time.time()
            advantages = compute_advantages(batch)
            datums = batch_to_datums(batch, advantages, sdk=sdk)

            await tc.forward_backward_async(datums, loss_fn="grpo")
            await tc.optim_step_async(AdamParams(learning_rate=1e-4))
            sc = await tc.save_weights_and_get_sampling_client_async(name="openclaw_lora")

            rewards = [s.reward for s in batch]
            mean_r = sum(rewards) / len(rewards)
            _check(
                f"Step {step}/3",
                sc.adapter_path is not None,
                f"datums={len(datums)} mean_r={mean_r:.2f} {time.time()-t0:.2f}s"
            )

        result = await tc.save_state_async(name="e2e_final")
        _check("Final checkpoint", Path(result.path).exists(), result.path)

    asyncio.run(_run())

    print(f"\n{'='*60}")
    if failed == 0:
        print(f"  \033[32m{passed} passed, 0 failed\033[0m")
    else:
        print(f"  \033[31m{passed} passed, {failed} failed\033[0m")
    print(f"{'='*60}")
    return failed


if __name__ == "__main__":
    args = sys.argv[1:]
    model = TEST_MODEL

    if "--model" in args:
        idx = args.index("--model")
        model = args[idx + 1]
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    sys.exit(_cli_run(model))
