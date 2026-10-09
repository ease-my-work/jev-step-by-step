"""Turns what a lesson's `run()` returned into answers the UI can draw and check against the gold labels.

A lesson returns a dict. Each value can be:
  * a JEV answer object (`NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`) → drawn with probability bars
  * a float 0–1 for a yes/no label (e.g. `{"urgent": 0.94}`) → a probability, decided at 0.5
  * a plain value (`True`, `"billing"`, `1`) → the LLM-only shape
Keys in `EXTRA_KEYS` (e.g. an LLM's self-reported "confidence") are shown but not graded.
"""

import json
import statistics
from dataclasses import dataclass, field
from typing import Any

from pydantic import TypeAdapter
from typesafe_sdk import Answer as JevAnswer
from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer

from kit import data, prices
from kit.trace import Stage

EXTRA_KEYS = {"confidence", "reason", "reasoning", "reply", "handled_by"}
_JEV_ANSWER = TypeAdapter(JevAnswer)


@dataclass
class Answer:
    label: str
    value: Any
    """The decision compared with the gold label (bool for yes/no, label for choice, int level for score)."""
    shape: str
    """"noul", "choice", "score" or "plain"."""
    probability: float | None = None
    confidence: float | None = None
    probabilities: dict[Any, float] | None = None
    legend: dict[int, Any] | None = None
    score: float | None = None
    valid: bool = True


def _is_yes_no(label: str) -> bool:
    allowed = data.allowed_values(label)
    return allowed is not None and isinstance(allowed[0], bool)


def to_answer(label: str, value: Any) -> Answer:
    if isinstance(value, NoulAnswer):
        return Answer(label, value.noul >= 0.5, "noul", probability=value.noul)
    if isinstance(value, ChoiceAnswer):
        return Answer(
            label, value.choice, "choice", confidence=value.confidence, probabilities=dict(value.probabilities)
        )
    if isinstance(value, ScoreAnswer):
        return Answer(
            label,
            round(value.score),
            "score",
            confidence=value.confidence,
            probabilities=dict(value.probabilities),
            legend=dict(value.legend),
            score=value.score,
        )
    if isinstance(value, float) and _is_yes_no(label) and 0 <= value <= 1:
        return Answer(label, value >= 0.5, "noul", probability=value)
    allowed = data.allowed_values(label)
    valid = allowed is None or (value in allowed and type(value) is type(allowed[0]))
    return Answer(label, value, "plain", valid=valid)


@dataclass
class SideResult:
    side: str
    """"jev" or "llm"."""
    raw: Any
    stages: list[Stage]
    error: str | None = None
    answers: dict[str, Answer] = field(init=False, default_factory=dict)
    extras: dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.raw, dict):
            for key, value in self.raw.items():
                if key in EXTRA_KEYS:
                    self.extras[key] = value
                else:
                    self.answers[key] = to_answer(key, value)

    @property
    def valid(self) -> bool:
        return self.error is None and isinstance(self.raw, dict) and all(a.valid for a in self.answers.values())

    @property
    def ms(self) -> float:
        """Latency: time in API calls and code stages. Rate-limit waiting is excluded."""
        return sum(s.ms or 0 for s in self.stages)

    @property
    def waited_ms(self) -> float:
        return sum(s.waited_ms for s in self.stages)

    @property
    def input_tokens(self) -> int:
        return sum(s.input_tokens or 0 for s in self.stages)

    @property
    def output_tokens(self) -> int:
        return sum((s.output_tokens or 0) + (s.thinking_tokens or 0) for s in self.stages)

    @property
    def cost_usd(self) -> float | None:
        costs = [
            prices.cost_usd(s.model, s.input_tokens, (s.output_tokens or 0) + (s.thinking_tokens or 0))
            for s in self.stages
            if s.kind in ("jev", "llm")
        ]
        known = [c for c in costs if c is not None]
        return sum(known) if known else None

    @property
    def models(self) -> list[str]:
        return sorted({s.model for s in self.stages if s.model})

    def correct(self, query: data.Query) -> dict[str, bool]:
        """For each graded label this side answered: does it match the expected answer (or an accepted alternative)?

        If this side reported any code fact (step 06), every fact the query expects is graded, and a missing one
        counts as wrong (e.g. the wrong claim was picked, so the right check never ran).
        """
        expected = query.expected()
        graded = {label: query.accepts(label, a.value) for label, a in self.answers.items() if label in expected}
        if self.answers.keys() & set(data.FACT_LABELS):
            for fact in query.facts:
                graded.setdefault(fact, False)
        return graded

    # --- fixtures -------------------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {"raw": _raw_to_json(self.raw), "stages": [s.to_dict() for s in self.stages], "error": self.error}

    @classmethod
    def from_dict(cls, side: str, saved: dict[str, Any]) -> "SideResult":
        return cls(
            side,
            _raw_from_json(saved["raw"]),
            [Stage.from_dict(s) for s in saved["stages"]],
            saved.get("error"),
        )


def _raw_to_json(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw
    return {
        key: {"__jev_answer__": value.model_dump(mode="json")}
        if isinstance(value, NoulAnswer | ChoiceAnswer | ScoreAnswer)
        else value
        for key, value in raw.items()
    }


def _raw_from_json(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw
    return {
        key: _JEV_ANSWER.validate_json(json.dumps(value["__jev_answer__"]))
        if isinstance(value, dict) and "__jev_answer__" in value
        else value
        for key, value in raw.items()
    }


# --- summaries for --all ---------------------------------------------------------------------------------


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[round(pct) - 1]


@dataclass
class Summary:
    side: str
    runs: int
    valid: int
    correct: dict[str, list[bool]]
    latencies: list[float]
    costs: list[float]

    @property
    def accuracy(self) -> dict[str, float]:
        return {label: sum(hits) / len(hits) for label, hits in self.correct.items() if hits}

    @property
    def p50(self) -> float | None:
        return percentile(self.latencies, 50)

    @property
    def p95(self) -> float | None:
        return percentile(self.latencies, 95)

    @property
    def cost_per_1k(self) -> float | None:
        return statistics.mean(self.costs) * 1000 if self.costs else None


def summarize(side: str, runs: list[tuple[data.Query, SideResult]]) -> Summary:
    correct: dict[str, list[bool]] = {}
    for query, result in runs:
        for label, ok in result.correct(query).items():
            correct.setdefault(label, []).append(ok)
    ok_runs = [r for _, r in runs if r.error is None]
    return Summary(
        side=side,
        runs=len(runs),
        valid=sum(r.valid for _, r in runs),
        correct=correct,
        latencies=[r.ms for r in ok_runs],
        costs=[r.cost_usd for r in ok_runs if r.cost_usd is not None],
    )
