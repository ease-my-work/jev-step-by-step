"""Offline tests for kit.clients: timing, recording, rate limit, setup errors. No API keys needed."""

import json
from types import SimpleNamespace

import httpx2
import pytest
from typesafe_sdk import Choice, TypeSafeClient

import kit
from kit import clients

JEV_BODY = {
    "model": "jev-1.13-test",
    "usage": {"input_tokens": 12, "output_tokens": 3},
    "answers": {
        "team": {
            "type": "choice",
            "choice": "billing",
            "confidence": 0.9,
            "probabilities": {"billing": 0.9, "other": 0.1},
        }
    },
}


def fake_jev(**kwargs):
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        return httpx2.Response(200, json=JEV_BODY)

    client = kit.jev_client(api_key="test-key", transport=httpx2.MockTransport(handler), **kwargs)
    return client, sent


def ask(client):
    return client.system_one(
        state="charged twice",
        questions={"team": Choice(instructions="Team?", criteria={"billing": None, "other": None})},
    )


def test_jev_client_is_a_real_typesafe_client_pinned_to_jev_model():
    client, sent = fake_jev()
    assert isinstance(client, TypeSafeClient)
    response = ask(client)
    assert response.answers["team"].choice == "billing"
    assert sent[0]["model"] == kit.JEV_MODEL


def test_jev_calls_are_recorded_with_time_and_tokens():
    client, _ = fake_jev()
    with kit.recording() as calls:
        ask(client)
    assert len(calls) == 1
    call = calls[0]
    assert (call.kind, call.label, call.model) == ("jev", "JEV · 1 question", "jev-1.13-test")
    assert (call.input_tokens, call.output_tokens) == (12, 3)
    assert call.done and call.ms >= 0


def test_calls_outside_recording_are_not_kept():
    client, _ = fake_jev()
    ask(client)
    with kit.recording() as calls:
        pass
    assert calls == []


def test_missing_jev_key_imports_fine_but_using_it_gives_a_friendly_error(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(clients, "_shared_jev", None)
    client = kit.jev_client()  # a lesson can still be imported (needed for --replay)
    with pytest.raises(kit.SetupError, match="--replay"):
        client.system_one(state="hi", questions={})


def test_missing_gemini_key_imports_fine_but_using_it_gives_a_friendly_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(clients, "_shared_gemini", None)
    client = kit.gemini_client()
    with pytest.raises(kit.SetupError, match="aistudio"):
        client.models.generate_content(model="x", contents="hi")


def test_jev_client_is_shared_so_a_warm_up_helps_the_lesson(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(clients, "_shared_jev", None)
    assert kit.jev_client() is kit.jev_client()


def test_gemini_calls_are_recorded_and_wait_time_is_kept_separate(monkeypatch):
    monkeypatch.setattr(clients, "_llm_limiter", SimpleNamespace(wait=lambda: 2.0))
    usage = SimpleNamespace(prompt_token_count=20, candidates_token_count=5, thoughts_token_count=0)
    fake = lambda **kw: SimpleNamespace(usage_metadata=usage, model_version="gemini-test")  # noqa: E731
    with kit.recording() as calls:
        clients._timed_generate_content(fake)(model="gemini-test", contents="hi")
    call = calls[0]
    assert (call.kind, call.model, call.input_tokens, call.output_tokens) == ("llm", "gemini-test", 20, 5)
    assert call.waited_ms == 2000
    assert call.ms < 1000  # the wait is not part of latency


def test_rate_limiter_spaces_calls(monkeypatch):
    now = [100.0]
    slept = []
    monkeypatch.setattr(clients.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(clients.time, "sleep", slept.append)
    limiter = clients._RateLimiter(per_minute=30)  # one call every 2 s
    assert limiter.wait() == 0
    assert limiter.wait() == pytest.approx(2.0)
    assert slept == [pytest.approx(2.0)]


def test_rate_limiter_disabled_when_zero():
    limiter = clients._RateLimiter(per_minute=0)
    assert limiter.wait() == 0
    assert limiter.wait() == 0
