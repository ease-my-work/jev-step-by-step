"""Real SDK clients, pinned to the course models and instrumented for timing.

`jev_client()` returns a real `TypeSafeClient` and `gemini_client()` a real `google.genai.Client`,
so lesson code calls them exactly as the official docs show. The only additions are timing,
token counts and (for Gemini) waiting for the free-tier rate limit.

Without a key, they return a stand-in that raises a friendly `SetupError` when used, so a lesson
can still be imported (and replayed with --replay) on a machine with no keys.
"""

import functools
import threading
import time

from google import genai
from google.genai import types
from typesafe_sdk import Noul, TypeSafeClient

from kit import settings
from kit.settings import SetupError
from kit.trace import track

GEMINI_THINKING = (
    None
    if settings.GEMINI_THINKING_LEVEL.lower() == "default"
    else types.ThinkingConfig(thinking_level=settings.GEMINI_THINKING_LEVEL.upper())
)
"""Thinking setting for every LLM-only call. Kept minimal so the baseline is fair (see .env.example)."""

JEV_KEY_MISSING = (
    "TYPESAFE_API_KEY is not set. Add it to .env (see .env.example), or add --replay to use recorded answers."
)
GEMINI_KEY_MISSING = (
    "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey and add it to .env, "
    "or add --replay to use recorded answers."
)


class _MissingKey:
    """Stands in for a client whose API key is missing. Any use raises `SetupError`."""

    def __init__(self, message: str) -> None:
        self._message = message

    def __getattr__(self, name: str):
        raise SetupError(self._message)


# --- JEV ---------------------------------------------------------------------------------------------


class _TimedTypeSafeClient(TypeSafeClient):
    def system_one(self, state, questions, **kwargs):
        count = len(questions)
        with track("jev", f"JEV · {count} question{'s' if count != 1 else ''}") as stage:
            response = super().system_one(state, questions, **kwargs)
            usage = getattr(response, "usage", None)
            stage.model = getattr(response, "model", kwargs.get("model") or settings.JEV_MODEL)
            stage.input_tokens = getattr(usage, "input_tokens", None)
            stage.output_tokens = getattr(usage, "output_tokens", None)
        return response


_shared_jev: TypeSafeClient | None = None


def jev_client(**overrides) -> TypeSafeClient:
    """A `TypeSafeClient` pinned to `JEV_MODEL`. Base URL and key come from `.env`.

    Without overrides, every caller shares one client (and its warm connection).
    """
    global _shared_jev
    if overrides:
        return _TimedTypeSafeClient(**{"model": settings.JEV_MODEL, **overrides})
    if not settings.env("TYPESAFE_API_KEY"):
        return _MissingKey(JEV_KEY_MISSING)  # type: ignore[return-value]
    if _shared_jev is None:
        _shared_jev = _TimedTypeSafeClient(model=settings.JEV_MODEL)
    return _shared_jev


# --- Gemini ------------------------------------------------------------------------------------------


class _RateLimiter:
    """Spaces calls at least 60/per_minute seconds apart. Thread-safe."""

    def __init__(self, per_minute: float) -> None:
        self.interval = 60 / per_minute if per_minute > 0 else 0.0
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> float:
        """Sleep until the next call is allowed. Returns the seconds waited."""
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.interval
        if delay:
            time.sleep(delay)
        return delay


_llm_limiter = _RateLimiter(settings.LLM_REQUESTS_PER_MINUTE)
LLM_TIMEOUT_MS = 60_000
_shared_gemini: genai.Client | None = None


def gemini_client(**overrides) -> genai.Client:
    """A `google.genai.Client` whose `models.generate_content` is timed and rate-limited.

    Without overrides, every caller shares one client (and its warm connection).
    """
    global _shared_gemini
    shared = not overrides
    if shared and _shared_gemini is not None:
        return _shared_gemini
    api_key = overrides.pop("api_key", None) or settings.env("GEMINI_API_KEY")
    if not api_key:
        return _MissingKey(GEMINI_KEY_MISSING)  # type: ignore[return-value]
    overrides.setdefault("http_options", types.HttpOptions(timeout=LLM_TIMEOUT_MS))  # never hang forever
    client = genai.Client(api_key=api_key, **overrides)
    models = client.models
    models.generate_content = _timed_generate_content(models.generate_content)
    if shared:
        _shared_gemini = client
    return client


def _timed_generate_content(generate_content):
    @functools.wraps(generate_content)
    def wrapper(*args, **kwargs):
        with track("llm", "Gemini call") as stage:
            stage.waiting = True
            waited = _llm_limiter.wait()
            stage.waiting = False
            stage.waited_ms = waited * 1000
            stage.started = time.perf_counter()  # latency starts after the rate-limit wait
            response = generate_content(*args, **kwargs)
            usage = response.usage_metadata
            stage.model = response.model_version or kwargs.get("model", settings.GEMINI_MODEL)
            stage.input_tokens = getattr(usage, "prompt_token_count", None)
            stage.output_tokens = getattr(usage, "candidates_token_count", None)
            stage.thinking_tokens = getattr(usage, "thoughts_token_count", None)
        return response

    return wrapper


# --- Warm-up -----------------------------------------------------------------------------------------


def warm_up() -> None:
    """Open both connections before anything is timed (the first HTTPS call pays for TLS setup).

    Runs outside any recording, so it never shows up in results. Errors are ignored here; the
    real run reports them properly.
    """
    jev = jev_client()
    if isinstance(jev, TypeSafeClient):
        try:
            jev.system_one(state="hello", questions={"warm_up": Noul(instructions="This is a greeting.")})
        except Exception:
            pass
    gemini = gemini_client()
    if isinstance(gemini, genai.Client):
        try:
            gemini.models.get(model=settings.GEMINI_MODEL)  # metadata only: no generation, no rate-limit slot
        except Exception:
            pass
