import asyncio
import queue
import threading
from types import SimpleNamespace

import metaclaw.utils as utils
from metaclaw.api_server import MetaClawAPIServer
from metaclaw.config import MetaClawConfig


class _FakeStore:
    def __init__(self, data):
        self._data = data

    def load(self):
        return self._data


def test_run_llm_uses_explicit_config_for_provider_selection(monkeypatch):
    monkeypatch.setattr(
        "metaclaw.config_store.ConfigStore",
        lambda: _FakeStore({"mode": "skills_only", "llm": {"provider": "bedrock"}}),
    )

    openai_calls = []
    bedrock_calls = []

    def fake_openai(messages, config=None):
        openai_calls.append((messages, config))
        return "openai"

    def fake_bedrock(messages, config=None):
        bedrock_calls.append((messages, config))
        return "bedrock"

    monkeypatch.setattr(utils, "_run_llm_openai", fake_openai)
    monkeypatch.setattr(utils, "_run_llm_bedrock", fake_bedrock)

    result = utils.run_llm(
        [{"role": "user", "content": "compress this"}],
        config=MetaClawConfig(mode="skills_only", llm_provider="custom"),
    )

    assert result == "openai"
    assert len(openai_calls) == 1
    assert bedrock_calls == []


def test_run_llm_uses_explicit_skills_only_endpoint(monkeypatch):
    monkeypatch.setattr(
        "metaclaw.config_store.ConfigStore",
        lambda: _FakeStore(
            {
                "mode": "rl",
                "rl": {
                    "prm_url": "https://wrong.example/v1",
                    "prm_api_key": "wrong-key",
                    "prm_model": "wrong-model",
                },
            }
        ),
    )

    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create)
            )

        def _create(self, **kwargs):
            captured["request_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="compressed"))]
            )

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    result = utils.run_llm(
        [{"role": "user", "content": "system prompt"}],
        config=MetaClawConfig(
            mode="skills_only",
            llm_provider="custom",
            llm_api_base="https://live.example/v1",
            llm_api_key="live-key",
            llm_model_id="live-model",
        ),
    )

    assert result == "compressed"
    assert captured["client_kwargs"] == {
        "api_key": "live-key",
        "base_url": "https://live.example/v1",
    }
    assert captured["request_kwargs"]["model"] == "live-model"


def test_run_llm_uses_explicit_rl_endpoint(monkeypatch):
    monkeypatch.setattr(
        "metaclaw.config_store.ConfigStore",
        lambda: _FakeStore(
            {
                "mode": "skills_only",
                "llm": {
                    "api_base": "https://wrong.example/v1",
                    "api_key": "wrong-key",
                    "model_id": "wrong-model",
                },
            }
        ),
    )

    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create)
            )

        def _create(self, **kwargs):
            captured["request_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="compressed"))]
            )

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    result = utils.run_llm(
        [{"role": "user", "content": "judge this"}],
        config=MetaClawConfig(
            mode="rl",
            prm_provider="openai",
            prm_url="https://judge.example/v1",
            prm_api_key="judge-key",
            prm_model="judge-model",
        ),
    )

    assert result == "compressed"
    assert captured["client_kwargs"] == {
        "api_key": "judge-key",
        "base_url": "https://judge.example/v1",
    }
    assert captured["request_kwargs"]["model"] == "judge-model"


def test_handle_request_falls_back_to_raw_system_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(
        MetaClawAPIServer,
        "_load_tokenizer",
        lambda self: None,
    )

    config = MetaClawConfig(
        mode="skills_only",
        claw_type="openclaw",
        llm_provider="custom",
        llm_api_base="https://live.example/v1",
        llm_api_key="live-key",
        llm_model_id="live-model",
        record_enabled=False,
        record_dir=str(tmp_path),
    )
    server = MetaClawAPIServer(
        config=config,
        output_queue=queue.Queue(),
        submission_enabled=threading.Event(),
    )

    def fail_run_llm(messages, config=None):
        raise RuntimeError("boom")

    monkeypatch.setattr("metaclaw.api_server.run_llm", fail_run_llm)

    forwarded = {}

    async def fake_forward(self, body):
        forwarded["body"] = body
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "ok",
                    }
                }
            ]
        }

    monkeypatch.setattr(MetaClawAPIServer, "_forward_to_llm", fake_forward)

    result = asyncio.run(
        server._handle_request(
            body={
                "messages": [
                    {"role": "system", "content": "raw system prompt"},
                    {"role": "user", "content": "hello"},
                ]
            },
            session_id="session-1",
            turn_type="main",
            session_done=False,
        )
    )

    assert forwarded["body"]["messages"][0]["content"] == "raw system prompt"
    assert result["response"]["choices"][0]["message"]["content"] == "ok"
