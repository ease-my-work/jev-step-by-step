"""Offline tests for kit.adk's timing plugin. No API calls."""

import asyncio
from types import SimpleNamespace

from google.genai import types

import kit
from kit import adk, clients, trace


def test_plugin_times_each_model_call_and_sets_a_timeout(monkeypatch):
    monkeypatch.setattr(clients, "_llm_limiter", SimpleNamespace(wait=lambda: 1.5))
    hooks = adk._CourseHooks()
    context = SimpleNamespace(agent_name="billing_agent")
    request = SimpleNamespace(config=types.GenerateContentConfig())
    usage = SimpleNamespace(prompt_token_count=900, candidates_token_count=40, thoughts_token_count=0)
    response = SimpleNamespace(usage_metadata=usage, model_version="gemini-3.5-flash")

    async def call():
        await hooks.before_model_callback(callback_context=context, llm_request=request)
        await hooks.after_model_callback(callback_context=context, llm_response=response)

    with kit.recording() as stages:
        asyncio.run(call())
    stage = stages[0]
    assert (stage.kind, stage.label, stage.model) == ("llm", "Gemini · billing_agent", "gemini-3.5-flash")
    assert (stage.input_tokens, stage.output_tokens) == (900, 40)
    assert stage.waited_ms == 1500 and stage.ms < 1000  # waiting is not latency
    assert request.config.http_options.timeout == clients.LLM_TIMEOUT_MS


def test_unfinished_calls_are_closed_on_error():
    hooks = adk._CourseHooks()
    with kit.recording() as stages:
        hooks._open = {"x": [trace.begin("llm", "Gemini · x")]}
        hooks.close_all(RuntimeError("boom"))
    assert stages[0].done and "boom" in stages[0].error
