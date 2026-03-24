#!/usr/bin/env python3
"""
Smoke test: spin up the MetaClaw proxy with the MLX backend and send
fake OpenClaw chat requests via HTTP.  Verifies:

  1. sdk_backend auto-detects MLX when no cloud credentials are set
  2. api_server.py builds EncodedTextChunk / ModelInput / SamplingParams
     from our mlx_backend module and calls sample_async()
  3. Proxy returns valid OpenAI-compatible chat completions with logprobs
  4. Training samples flow through the output queue
  5. A full train_on_batch() step completes with hot-swapped weights

Usage:
    # Make sure no TINKER_API_KEY / MINT_API_KEY are set
    unset TINKER_API_KEY MINT_API_KEY TINKER_BASE_URL MINT_BASE_URL
    python3 tests/smoke_mlx_proxy.py
"""

import asyncio
import json
import os
import sys
import time

# ── Ensure no cloud credentials so auto-detect picks MLX ──────────
for var in ("TINKER_API_KEY", "MINT_API_KEY", "TINKER_BASE_URL", "MINT_BASE_URL"):
    os.environ.pop(var, None)

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
passed = failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  {PASS} {name}" + (f"  ({detail})" if detail else ""))
        passed += 1
    else:
        print(f"  {FAIL} {name}" + (f"  ({detail})" if detail else ""))
        failed += 1


TEST_MODEL = os.environ.get("MLX_TEST_MODEL", "mlx-community/Qwen2.5-0.5B-Instruct-4bit")
PROXY_PORT = int(os.environ.get("MLX_TEST_PORT", "18899"))


def _seed_system_prompt_cache(record_dir: str):
    """Pre-populate the system prompt cache so _handle_request never calls
    run_llm (which requires an external LLM API key we don't have in the
    MLX-only smoke test).  This mirrors the cache format written by
    api_server._write_cached_system_prompt().
    """
    os.makedirs(record_dir, exist_ok=True)
    cache_path = os.path.join(record_dir, "system_prompt_cache.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            {"compressed_system_prompt": "You are a helpful assistant."},
            f,
            ensure_ascii=False,
        )


async def main():
    # ── 1. Backend auto-detection ──────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  BACKEND AUTO-DETECTION")
    print(f"{'='*60}")

    from types import SimpleNamespace
    config = SimpleNamespace(
        backend="auto",
        api_key="",
        tinker_api_key="",
        base_url="",
        tinker_base_url="",
    )
    from metaclaw.sdk_backend import infer_backend_key
    detected = infer_backend_key(config)
    check("auto-detect picks MLX", detected == "mlx", f"got {detected!r}")

    from metaclaw.sdk_backend import resolve_sdk_backend
    backend = resolve_sdk_backend(config)
    check("resolve_sdk_backend", backend.key == "mlx" and backend.module is not None, backend.label)

    sdk = backend.module
    check("sdk exports EncodedTextChunk", hasattr(sdk, "EncodedTextChunk"))
    check("sdk exports SamplingParams", hasattr(sdk, "SamplingParams"))
    check("sdk exports ModelInput", hasattr(sdk, "ModelInput"))

    # ── 2. Proxy startup ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  PROXY STARTUP")
    print(f"{'='*60}")

    import queue
    import threading
    from metaclaw.config import MetaClawConfig

    record_dir = os.path.join(os.path.dirname(__file__), ".smoke_records")

    proxy_config = MetaClawConfig(
        backend="mlx",
        model_name=TEST_MODEL,
        lora_rank=16,
        proxy_host="127.0.0.1",
        proxy_port=PROXY_PORT,
        mode="rl",
        use_prm=False,
        record_enabled=False,
        served_model_name="test-qwen",
        record_dir=record_dir,
    )

    # Seed the system prompt cache so run_llm is never called
    _seed_system_prompt_cache(record_dir)

    # Create training client + sampling client
    t0 = time.time()
    service_client = sdk.ServiceClient()
    tc = await service_client.create_lora_training_client_async(
        base_model=TEST_MODEL, rank=16,
    )
    sc = await tc.save_weights_and_get_sampling_client_async()
    check("Model + LoRA loaded", sc is not None, f"{time.time()-t0:.1f}s")

    # Spin up api_server
    from metaclaw.api_server import MetaClawAPIServer

    output_queue = queue.Queue(maxsize=10000)
    submission_enabled = threading.Event()
    submission_enabled.set()

    server = MetaClawAPIServer(
        config=proxy_config,
        output_queue=output_queue,
        submission_enabled=submission_enabled,
        sampling_client=sc,
    )
    server.start()

    # Wait for proxy to be ready
    import httpx
    deadline = time.time() + 15
    ready = False
    while time.time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                r = await client.get(f"http://127.0.0.1:{PROXY_PORT}/healthz")
                if r.status_code == 200:
                    ready = True
                    break
        except Exception:
            pass
        await asyncio.sleep(0.3)

    check("Proxy /healthz", ready)
    if not ready:
        print("  !! Proxy did not start — aborting")
        server.stop()
        return

    # ── 3. Chat completions ───────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  CHAT COMPLETIONS")
    print(f"{'='*60}")

    sessions = [
        ("smoke-sess-1", "What is 2+2?"),
        ("smoke-sess-2", "Name three colors."),
        ("smoke-sess-3", "Say hello."),
    ]

    for sid, prompt in sessions:
        body = {
            "model": "test-qwen",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 64,
            "temperature": 0.7,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                t0 = time.time()
                resp = await client.post(
                    f"http://127.0.0.1:{PROXY_PORT}/v1/chat/completions",
                    json=body,
                    headers={
                        "X-Session-Id": sid,
                        "X-Turn-Type": "main",
                        "X-Session-Done": "true",
                    },
                )
            elapsed = time.time() - t0
            data = resp.json()

            has_response = "response" in data
            if has_response:
                data = data["response"]

            content = data["choices"][0]["message"]["content"]
            logprobs = data["choices"][0].get("logprobs", {}).get("content", [])

            check(
                f"Session {sid}",
                resp.status_code == 200 and len(content) > 0,
                f"{len(content)} chars, {len(logprobs)} logprobs, {elapsed:.2f}s",
            )
        except Exception as e:
            check(f"Session {sid}", False, str(e))

    # ── 4. Training samples queued ────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  TRAINING SAMPLE COLLECTION")
    print(f"{'='*60}")

    await asyncio.sleep(1.0)  # let background tasks finish

    samples = []
    while not output_queue.empty():
        try:
            samples.append(output_queue.get_nowait())
        except queue.Empty:
            break

    check(
        "Samples in output queue",
        len(samples) > 0,
        f"{len(samples)} sample groups",
    )

    if samples:
        _, first_sample = samples[0]
        if isinstance(first_sample, list):
            first_sample = first_sample[0]
        check(
            "Sample has prompt + response tokens",
            len(first_sample.prompt_tokens) > 0 and len(first_sample.response_tokens) > 0,
            f"prompt={len(first_sample.prompt_tokens)} response={len(first_sample.response_tokens)}",
        )

    # ── 5. Training step with hot-swap ────────────────────────────
    print(f"\n{'='*60}")
    print(f"  TRAINING STEP + HOT-SWAP")
    print(f"{'='*60}")

    if samples:
        from metaclaw.data_formatter import batch_to_datums, compute_advantages, ConversationSample

        batch = []
        for _, sample in samples:
            if isinstance(sample, list):
                batch.extend(sample)
            elif isinstance(sample, ConversationSample):
                batch.append(sample)

        if batch:
            advantages = compute_advantages(batch)
            datums = batch_to_datums(batch, advantages, sdk=sdk)
            check("Built datums from proxy samples", len(datums) > 0, f"{len(datums)} datums")

            t0 = time.time()
            await tc.forward_backward_async(datums, loss_fn="grpo")
            await tc.optim_step_async(sdk.AdamParams(learning_rate=1e-4))
            check("Training step", True, f"{time.time()-t0:.2f}s")

            new_sc = await tc.save_weights_and_get_sampling_client_async()
            server.update_sampling_client(new_sc)
            check("Hot-swap sampling client", server._sampling_client is new_sc)

            # Verify inference still works after swap
            body["messages"][1]["content"] = "Quick test after weight update"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"http://127.0.0.1:{PROXY_PORT}/v1/chat/completions",
                        json=body,
                        headers={
                            "X-Session-Id": "smoke-post-swap",
                            "X-Turn-Type": "main",
                            "X-Session-Done": "true",
                        },
                    )
                data = resp.json()
                if "response" in data:
                    data = data["response"]
                post_swap_content = data["choices"][0]["message"]["content"]
                check(
                    "Inference after hot-swap",
                    resp.status_code == 200 and len(post_swap_content) > 0,
                    f"{len(post_swap_content)} chars",
                )
            except Exception as e:
                check("Inference after hot-swap", False, str(e))
        else:
            check("Built datums from proxy samples", False, "no ConversationSamples found")
    else:
        print("  (skipping training — no samples collected)")

    # ── Cleanup ───────────────────────────────────────────────────
    server.stop()
    import shutil
    shutil.rmtree(record_dir, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
