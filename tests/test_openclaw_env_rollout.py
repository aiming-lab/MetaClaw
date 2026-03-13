import asyncio
from types import SimpleNamespace

import httpx as real_httpx

from metaclaw.config import MetaClawConfig
from metaclaw.openclaw_env_rollout import run_task_episode
from metaclaw.trainer import MetaClawTrainer

_ORIG_ASYNC_CLIENT = real_httpx.AsyncClient


def test_run_task_episode_forwards_proxy_auth_to_all_requests(monkeypatch):
    requests = []

    def handler(request: real_httpx.Request) -> real_httpx.Response:
        requests.append(request)
        return real_httpx.Response(
            200,
            json={"choices": [{"message": {"content": "No command this turn."}}]},
        )

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = real_httpx.MockTransport(handler)
        return _ORIG_ASYNC_CLIENT(*args, **kwargs)

    monkeypatch.setattr("metaclaw.openclaw_env_rollout.httpx.AsyncClient", fake_async_client)
    monkeypatch.setattr("metaclaw.openclaw_env_rollout._get_rollout_system_prompt", lambda: "system")

    result = asyncio.run(
        run_task_episode(
            task_id="task-auth",
            task_instruction="Check status",
            proxy_url="http://proxy.test",
            max_steps=1,
            proxy_api_key="proxy-key",
        )
    )

    assert result["success"] is True
    assert len(requests) == 2
    assert requests[0].headers.get("Authorization") == "Bearer proxy-key"
    assert requests[1].headers.get("Authorization") == "Bearer proxy-key"
    assert requests[0].headers.get("X-Session-Done") is None
    assert requests[1].headers.get("X-Session-Done") == "true"


def test_run_task_episode_skips_auth_header_when_unset(monkeypatch):
    requests = []

    def handler(request: real_httpx.Request) -> real_httpx.Response:
        requests.append(request)
        return real_httpx.Response(
            200,
            json={"choices": [{"message": {"content": "No command this turn."}}]},
        )

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = real_httpx.MockTransport(handler)
        return _ORIG_ASYNC_CLIENT(*args, **kwargs)

    monkeypatch.setattr("metaclaw.openclaw_env_rollout.httpx.AsyncClient", fake_async_client)
    monkeypatch.setattr("metaclaw.openclaw_env_rollout._get_rollout_system_prompt", lambda: "system")

    asyncio.run(
        run_task_episode(
            task_id="task-no-auth",
            task_instruction="Check status",
            proxy_url="http://proxy.test",
            max_steps=1,
        )
    )

    assert len(requests) == 2
    assert requests[0].headers.get("Authorization") is None
    assert requests[1].headers.get("Authorization") is None


def test_trainer_passes_proxy_api_key_to_rollout_loop(monkeypatch):
    captured = {}

    class FakeRolloutWorker:
        def start(self):
            return None

        def resume_submission(self):
            return None

        def pause_submission(self):
            return None

        def stop(self):
            return None

    async def fake_setup(self):
        self.rollout_worker = FakeRolloutWorker()
        self._wandb = None
        self.skill_evolver = None

    async def fake_wait_for_proxy_ready(self, timeout_s: float = 30.0):
        return None

    async def fake_drain_output_queue(batch_size, rollout_worker):
        await asyncio.sleep(0)
        return [[]]

    async def fake_train_on_batch(self, batch, step_idx: int):
        return None

    async def fake_rollout_loop(**kwargs):
        captured.update(kwargs)
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            return None

    monkeypatch.setattr(
        "metaclaw.trainer.resolve_sdk_backend",
        lambda config: SimpleNamespace(
            key="tinker",
            label="Tinker",
            module=SimpleNamespace(),
            api_key="",
            base_url="",
        ),
    )
    monkeypatch.setattr("metaclaw.trainer.MetaClawTrainer.setup", fake_setup)
    monkeypatch.setattr(
        "metaclaw.trainer.MetaClawTrainer._wait_for_proxy_ready",
        fake_wait_for_proxy_ready,
    )
    monkeypatch.setattr("metaclaw.trainer._drain_output_queue", fake_drain_output_queue)
    monkeypatch.setattr("metaclaw.trainer.MetaClawTrainer._train_on_batch", fake_train_on_batch)
    monkeypatch.setattr("metaclaw.trainer.rollout_loop", fake_rollout_loop)

    trainer = MetaClawTrainer(
        MetaClawConfig(
            max_steps=1,
            proxy_port=31234,
            proxy_api_key="proxy-key",
            openclaw_env_data_dir="/tmp/fake-data",
            served_model_name="test-model",
        )
    )

    asyncio.run(trainer.run())

    assert captured["proxy_api_key"] == "proxy-key"
    assert captured["proxy_url"] == "http://localhost:31234"
    assert captured["model_id"] == "test-model"
