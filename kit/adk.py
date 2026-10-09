"""Runs a Google ADK agent for one customer message, with the course's timing, rate limit and flow chart.

Lesson code calls `kit.run_agent(agent, message, state)`. Everything ADK-specific that isn't about the agents
themselves (runner, session, plugin for timing) lives here.
"""

import asyncio
import logging
import threading
import time
import warnings
from contextlib import nullcontext
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.genai import types

from kit import clients, settings, trace

# ADK's tuning advice ("no context_cache_config …") and experimental-feature warnings would clutter the lesson UI.
logging.getLogger("google_adk").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]", category=UserWarning)

APP_NAME = "desk_buddy"
USER_ID = "customer"


class _CourseHooks(BasePlugin):
    """Draws every Gemini call an ADK agent makes on the flow chart, and respects the free-tier rate limit."""

    def __init__(self) -> None:
        super().__init__(name="course_hooks")
        self._open: dict[str, list[trace.Stage]] = {}

    async def before_model_callback(self, *, callback_context, llm_request):
        if llm_request.config is not None and llm_request.config.http_options is None:
            llm_request.config.http_options = types.HttpOptions(timeout=clients.LLM_TIMEOUT_MS)  # never hang forever
        stage = trace.begin("llm", f"Gemini · {callback_context.agent_name}")
        stage.waiting = True
        stage.waited_ms = await asyncio.to_thread(clients._llm_limiter.wait) * 1000
        stage.waiting = False
        stage.started = time.perf_counter()  # latency starts after the rate-limit wait
        self._open.setdefault(callback_context.agent_name, []).append(stage)
        return None

    async def after_model_callback(self, *, callback_context, llm_response):
        stages = self._open.get(callback_context.agent_name)
        if not stages:
            return None
        stage = stages.pop()
        usage = llm_response.usage_metadata
        stage.model = llm_response.model_version or settings.GEMINI_MODEL
        stage.input_tokens = getattr(usage, "prompt_token_count", None)
        stage.output_tokens = getattr(usage, "candidates_token_count", None)
        stage.thinking_tokens = getattr(usage, "thoughts_token_count", None)
        trace.finish(stage)
        return None

    def close_all(self, error: BaseException | None = None) -> None:
        for stages in self._open.values():
            for stage in stages:
                trace.finish(stage, error)


_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _event_loop() -> asyncio.AbstractEventLoop:
    """One event loop for every ADK run, kept alive in a background thread.

    `asyncio.run()` per message closes its loop while the Gemini SDK is still closing its connections, which prints
    "Event loop is closed" tracebacks. A long-lived loop lets them close quietly.
    """
    global _loop
    with _loop_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, name="adk-loop", daemon=True).start()
    return _loop


def run_agent(agent, message: str, state: dict[str, Any] | None = None) -> tuple[str, str, dict[str, Any]]:
    """Send one message to `agent`. Returns (final reply text, name of the agent that wrote it, session state)."""
    stages = trace.current()  # the flow chart's recording lives in this thread; hand it to the loop

    async def go() -> tuple[str, str, dict[str, Any]]:
        with trace.recording(into=stages) if stages is not None else nullcontext():
            return await _run(agent, message, state)

    return asyncio.run_coroutine_threadsafe(go(), _event_loop()).result()


async def _run(agent, message: str, state: dict[str, Any] | None) -> tuple[str, str, dict[str, Any]]:
    hooks = _CourseHooks()
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME, plugins=[hooks])
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID, state=state or {})
    reply, author = "", ""
    try:
        content = types.Content(role="user", parts=[types.Part(text=message)])
        async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=content):
            parts = event.content.parts if event.content and event.content.parts else []
            text = "".join(p.text or "" for p in parts if not p.thought)
            if text.strip() and event.author != "user":
                reply, author = text, event.author
    except BaseException as error:
        hooks.close_all(error)
        raise
    finally:
        hooks.close_all()
    final = await runner.session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session.id)
    await runner.close()
    return reply, author, dict(final.state)
