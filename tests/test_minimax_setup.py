"""Exercise setup, saved configuration, and the serialized proxy request offline."""

import json
import queue
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from metaclaw.api_server import MetaClawAPIServer
from metaclaw.config_store import ConfigStore
from metaclaw.setup_wizard import SetupWizard


@pytest.mark.parametrize(
    "provider,saved_model,saved_base,model_input,base_input,expected_model,expected_base,options",
    [
        ("minimax", "", "", "", "", "MiniMax-M3.1-Flash", "https://api.minimax.io/v1", {}),
        ("minimax", "", "", "MiniMax-M3", "", "MiniMax-M3", "https://api.minimax.io/v1",
         {"thinking": {"type": "disabled"}}),
        ("minimax", "MiniMax-M2.7", "https://api.minimax.chat/v1", "", "",
         "MiniMax-M2.7", "https://api.minimax.chat/v1", {}),
        ("minimax", "saved-model", "https://proxy.example/v1", "", "",
         "saved-model", "https://proxy.example/v1", {}),
        ("minimax", "", "", "custom-model", "https://custom.example/v1",
         "custom-model", "https://custom.example/v1", {}),
        ("minimax", "MiniMax-M3", "https://api.minimaxi.com/v1", "", "",
         "MiniMax-M3", "https://api.minimaxi.com/v1", {"thinking": {"type": "adaptive"}}),
        ("minimax", "", "", "", "https://api.minimaxi.com/v1",
         "MiniMax-M3.1-Flash", "https://api.minimaxi.com/v1", {}),
        ("custom", "custom-model", "https://custom.example/v1", "", "",
         "custom-model", "https://custom.example/v1", {}),
        ("openrouter", "minimax/minimax-m3.1-flash:free", "https://openrouter.ai/api/v1", "", "",
         "minimax/minimax-m3.1-flash:free", "https://openrouter.ai/api/v1", {}),
        ("openai", "", "", "", "", "gpt-4o", "https://api.openai.com/v1", {}),
        *[
            ("minimax", "", "", "", "", "MiniMax-M3.1-Flash", "https://api.minimax.io/v1",
             {"thinking": {"type": "adaptive"}, "reasoning_effort": effort})
            for effort in ("low", "medium", "high", "xhigh", "max")
        ],
    ],
)
def test_setup_to_http_request(
    monkeypatch, tmp_path, capsys,
    provider, saved_model, saved_base, model_input, base_input, expected_model, expected_base, options,
):
    store = ConfigStore(config_file=tmp_path / "config.yaml")
    if saved_model or saved_base:
        store.save({
            "mode": "skills_only",
            "llm": {"provider": provider, "model_id": saved_model, "api_base": saved_base},
        })
    monkeypatch.setattr("metaclaw.setup_wizard.ConfigStore", lambda: store)
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        if prompt.startswith("Operating mode"):
            return "skills_only"
        if prompt.startswith("Provider ("):
            return provider
        if prompt.startswith("Model ID"):
            return model_input
        if prompt.startswith("API base URL"):
            return base_input
        if prompt.startswith("Skills directory"):
            return str(tmp_path / "skills")
        if prompt.startswith(("Enable skill injection", "Auto-summarize skills")):
            return "n"
        return ""

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr("getpass.getpass", lambda prompt: "test-api-key")
    SetupWizard().run()

    assert store.get("llm.model_id") == expected_model
    assert store.get("llm.api_base") == expected_base
    if provider == "minimax":
        recommendation = "Recommended models: MiniMax-M3.1-Flash, MiniMax-M3 (or enter a custom model ID)."
        assert recommendation in capsys.readouterr().out
        default_model = saved_model or "MiniMax-M3.1-Flash"
        assert f"Model ID [{default_model}]: " in prompts

    config = store.to_metaclaw_config()
    assert config.llm_model_id == expected_model
    assert config.evolver_model_id == expected_model
    config.record_dir = str(tmp_path / "records")
    config.record_enabled = False
    monkeypatch.setattr(MetaClawAPIServer, "_load_tokenizer", lambda self: None)
    submission_enabled = threading.Event()
    submission_enabled.set()
    server = MetaClawAPIServer(config, queue.Queue(), submission_enabled)
    requests = []

    def upstream(request):
        requests.append(request)
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    original_client = httpx.AsyncClient

    def mock_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(upstream)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_client)
    messages = [{"role": "user", "content": [
        {"type": "text", "text": "Describe this image."},
        {"type": "image_url", "image_url": {"url": "https://example.test/image.png"}},
    ]}]
    tools = [{"type": "function", "function": {
        "name": "lookup", "parameters": {"type": "object", "properties": {}},
    }}]
    with TestClient(server.app) as client:
        response = client.post("/v1/chat/completions", json={
            "model": "metaclaw-model", "messages": messages, "tools": tools,
            "max_tokens": 128, "stream": False, **options,
        }, headers={"X-Session-Id": "test-session", "X-Turn-Type": "side"})
    assert response.status_code == 200
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == expected_base + "/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-api-key"
    assert json.loads(request.content) == {
        "model": expected_model, "messages": messages, "tools": tools,
        "max_tokens": 128, "stream": False, **options,
    }
