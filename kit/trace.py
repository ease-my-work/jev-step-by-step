"""Records each stage of a run (JEV calls, Gemini calls, code steps) so the UI can draw the flow chart live.

Lesson code never touches this directly: the clients from `kit.jev_client()` / `kit.gemini_client()` record
their own calls, and `@kit.stage("…")` marks a plain-code step that should appear on the chart.
"""

import functools
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Kind = Literal["jev", "llm", "code"]


@dataclass
class Stage:
    kind: Kind
    label: str
    started: float = field(default_factory=time.perf_counter)
    ms: float | None = None
    """Time spent in this stage. `None` while it is still running. Rate-limit waiting is excluded."""
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    waiting: bool = False
    """True while the stage waits for the LLM rate limit (shown on screen, never counted as latency)."""
    waited_ms: float = 0.0
    error: str | None = None

    @property
    def done(self) -> bool:
        return self.ms is not None

    def elapsed_ms(self) -> float:
        return self.ms if self.ms is not None else (time.perf_counter() - self.started) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if k not in ("started", "waiting")}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Stage":
        return cls(**raw)


_stages: ContextVar[list[Stage] | None] = ContextVar("kit_stages", default=None)


@contextmanager
def recording(into: list[Stage] | None = None) -> Iterator[list[Stage]]:
    """Collect the stages run inside this block, in order. Pass `into` to fill a list someone else is watching."""
    stages = [] if into is None else into
    token = _stages.set(stages)
    try:
        yield stages
    finally:
        _stages.reset(token)


def current() -> list[Stage] | None:
    """The list the current `recording()` is filling, if any (to hand it to another thread or event loop)."""
    return _stages.get()


def begin(kind: Kind, label: str) -> Stage:
    """Start a stage and add it to the current recording. Pair with `finish()` (or use `track()`)."""
    stage = Stage(kind, label)
    stages = _stages.get()
    if stages is not None:
        stages.append(stage)
    return stage


def finish(stage: Stage, error: BaseException | None = None) -> None:
    if error is not None:
        stage.error = f"{type(error).__name__}: {error}"
    if stage.ms is None:
        stage.ms = (time.perf_counter() - stage.started) * 1000


@contextmanager
def track(kind: Kind, label: str) -> Iterator[Stage]:
    """Time one stage. Fill in model/tokens on the yielded `Stage`; `ms` is set when the block ends."""
    stage = begin(kind, label)
    try:
        yield stage
    except BaseException as error:
        finish(stage, error)
        raise
    finally:
        finish(stage)


def stage(label: str):
    """Decorator for lesson code: show this function as a box on the flow chart, e.g. `@kit.stage("Check dates")`."""

    def decorate(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            with track("code", label):
                return function(*args, **kwargs)

        return wrapper

    return decorate
