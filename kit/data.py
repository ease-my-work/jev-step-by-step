"""Loads `data/` (queries, orders, policy) into simple objects for the lessons and the UI."""

import json
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from typing import Any

from kit.settings import ROOT

DATA_DIR = ROOT / "data"

LABELS: dict[str, tuple[Any, ...]] = {
    "team": ("billing", "shipping", "technical", "account", "other"),
    "urgent": (True, False),
    "frustration": (0, 1, 2),
    "intent": (
        "order_status",
        "duplicate_charge",
        "refund_request",
        "change_address",
        "product_question",
        "complaint",
        "account_access",
        "tech_issue",
        "other",
    ),
    "needs_human": (True, False),
    "unsafe": (True, False),
}
"""Every gold-label field and its allowed values (see data/README.md for how they are assigned)."""

FACT_LABELS = ("duplicate_charge", "return_eligible", "late_credit_eligible", "refund_overdue")
"""Ground truth that only code can work out from the order record (step 06). All yes/no."""

DRAFT_LABELS = ("answers_question", "on_policy")
"""Gold labels for the pre-written draft replies that step 09 checks. All yes/no."""


def allowed_values(label: str) -> tuple[Any, ...] | None:
    """The allowed values for any graded label, or None if the label isn't graded."""
    if label in LABELS:
        return LABELS[label]
    if label in FACT_LABELS or label in DRAFT_LABELS:
        return (True, False)
    return None


def _same(a: Any, b: Any) -> bool:
    """Equal and the same type, so True never counts as frustration level 1."""
    return type(a) is type(b) and a == b


KINDS = ("clear", "ambiguous", "typos", "angry", "unsafe", "needs_code")

ALL_QUERIES_FROM_STEP = 10
"""Steps 10–12 (full Desk Buddy, ADK, benchmark) use every query; earlier steps use their tagged subset."""


@dataclass(frozen=True)
class Query:
    id: str
    kind: str
    text: str
    customer_id: str
    order_id: str | None
    gold: dict[str, Any]
    steps: tuple[int, ...]
    teaches: str
    also_ok: dict[str, list[Any]] = field(default_factory=dict)
    """Other answers that are also correct for genuinely ambiguous queries."""
    facts: dict[str, bool] = field(default_factory=dict)
    """Ground truth that code can check from the order record (step 06)."""
    draft: dict[str, Any] | None = None
    """A pre-written reply for step 09 to check: {"text": ..., "gold": {"answers_question": ..., "on_policy": ...}}."""

    def expected(self) -> dict[str, Any]:
        """Every graded answer for this query: gold labels, code facts, and the draft's labels."""
        return {**self.gold, **self.facts, **(self.draft["gold"] if self.draft else {})}

    def accepts(self, label: str, value: Any) -> bool:
        """True if `value` is the expected answer for `label`, or an accepted alternative."""
        expected = self.expected()[label]
        return _same(value, expected) or any(_same(value, ok) for ok in self.also_ok.get(label, ()))

    def used_in(self, step: int) -> bool:
        return step >= ALL_QUERIES_FROM_STEP or step in self.steps


def _read_json(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@cache
def queries() -> tuple[Query, ...]:
    return tuple(Query(**{**raw, "steps": tuple(raw["steps"])}) for raw in _read_json("queries.json"))


def queries_for_step(step: int) -> list[Query]:
    return [q for q in queries() if q.used_in(step)]


def query(query_id: str) -> Query:
    for q in queries():
        if q.id == query_id:
            return q
    raise KeyError(f"No query {query_id!r} in data/queries.json")


@cache
def store() -> dict[str, Any]:
    """The whole of data/orders.json: customers, products, orders."""
    return _read_json("orders.json")


def today() -> date:
    """The course's fixed 'today', so date checks give the same answer on every run."""
    return date.fromisoformat(store()["as_of"])


def order(order_id: str | None) -> dict[str, Any] | None:
    return next((o for o in store()["orders"] if o["id"] == order_id), None)


def customer(customer_id: str) -> dict[str, Any] | None:
    return next((c for c in store()["customers"] if c["id"] == customer_id), None)


def orders_of(customer_id: str) -> list[dict[str, Any]]:
    return [o for o in store()["orders"] if o["customer_id"] == customer_id]


def product(name_or_sku: str) -> dict[str, Any] | None:
    return next((p for p in store()["products"] if name_or_sku in (p["sku"], p["name"])), None)


@cache
def policy() -> str:
    return (DATA_DIR / "policy.md").read_text(encoding="utf-8")
