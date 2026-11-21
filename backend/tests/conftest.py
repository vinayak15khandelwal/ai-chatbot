"""Deterministic tests: a fake LiteLLM custom provider stands in for the real API.

The REAL litellm Router, fallback chain, cache and pre-call hook are exercised; only the final
network call to the provider is replaced. The provider's behaviour is chosen by the api_key it
receives, so key_1 / key_2 failures are real provider exceptions raised for that specific key.
"""
from __future__ import annotations

import asyncio

import litellm
import pytest
from fastapi.testclient import TestClient
from litellm import CustomLLM, ModelResponse

from app.config import Settings
from app.main import create_app

KEY_1, KEY_2 = "test-key-one", "test-key-two"
LIVE_DELAY = 0.25


class FakeProvider(CustomLLM):
    def __init__(self):
        self.calls: list[dict] = []  # {"api_key":..., "messages":[...]}
        self.failures: dict[str, Exception] = {}  # api_key -> exception to raise

    async def acompletion(self, model, messages, api_key=None, **kwargs):
        self.calls.append({"api_key": api_key, "messages": [dict(m) for m in messages]})
        if api_key in self.failures:
            raise self.failures[api_key]
        await asyncio.sleep(LIVE_DELAY)
        last = messages[-1]["content"]
        user_turns = [m for m in messages if m["role"] == "user"]
        earlier = "; ".join(m["content"] for m in user_turns[:-1]) or "nothing"
        reply = f"answer to '{last}' (earlier: {earlier})"
        prompt_tokens = sum(len(m["content"].split()) + 3 for m in messages)
        completion_tokens = len(reply.split())
        return ModelResponse(
            model="fake-model",
            choices=[{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": reply}}],
            usage={"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                   "total_tokens": prompt_tokens + completion_tokens},
        )


def rate_limit() -> Exception:
    return litellm.RateLimitError(message="429 quota", llm_provider="fake", model="m")


def server_error() -> Exception:
    return litellm.InternalServerError(message="500 boom", llm_provider="fake", model="m")


@pytest.fixture()
def provider():
    p = FakeProvider()
    litellm.custom_provider_map = [{"provider": "fake", "custom_handler": p}]
    litellm._custom_providers = ["fake"]
    return p


def make_settings(tmp_path, **overrides) -> Settings:
    base = dict(
        LLM_API_KEYS=f"{KEY_1},{KEY_2}",
        LLM_MODEL="fake/test-model",
        DATABASE_URL=f"sqlite:///{tmp_path}/app.db",
        ALLOWED_ORIGINS="http://localhost:3000",
        ENABLE_FAILURE_SIMULATION="true",
        CACHE_ENABLED="true",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


@pytest.fixture()
def make_client(tmp_path, provider):
    clients = []

    def _make(**overrides):
        app = create_app(make_settings(tmp_path, **overrides))
        c = TestClient(app, raise_server_exceptions=False)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture()
def client(make_client):
    return make_client()


def chat(client, session="s1", message="What is the capital of France?", headers=None, **extra):
    return client.post("/chat", json={"session_id": session, "message": message, **extra}, headers=headers or {})


def settle():
    """LiteLLM writes cache entries in a background task; give it a moment."""
    import time
    time.sleep(0.3)
