"""Dataset checks: every query is well-formed, its gold labels are valid, and its facts match the order records."""

from collections import Counter
from datetime import date, timedelta

import pytest

from kit import data

QUERIES = data.queries()
EXPECTED_KINDS = {"clear": 8, "ambiguous": 4, "typos": 3, "angry": 3, "unsafe": 3, "needs_code": 3}


def test_there_are_24_queries_with_unique_sequential_ids():
    assert [q.id for q in QUERIES] == [f"q{n:02d}" for n in range(1, 25)]


def test_query_mix_matches_the_plan():
    assert Counter(q.kind for q in QUERIES) == EXPECTED_KINDS


def test_the_example_from_the_brief_is_q02_verbatim():
    assert data.query("q02").text == "My order debited amount 2 time. I want immediate help."


@pytest.mark.parametrize("q", QUERIES, ids=lambda q: q.id)
def test_gold_labels_use_allowed_values(q):
    assert set(q.gold) == set(data.LABELS)
    for label, value in q.gold.items():
        assert value in data.LABELS[label], f"{q.id}: {label}={value!r}"
        # bool vs int matters: frustration must be an int, flags must be real booleans
        assert type(value) is type(data.LABELS[label][0])


@pytest.mark.parametrize("q", QUERIES, ids=lambda q: q.id)
def test_also_ok_alternatives_are_valid_and_differ_from_gold(q):
    for label, values in q.also_ok.items():
        assert label in data.LABELS
        for value in values:
            assert value in data.LABELS[label]
            assert value != q.gold[label]


@pytest.mark.parametrize("q", QUERIES, ids=lambda q: q.id)
def test_customer_and_order_exist_and_belong_together(q):
    assert data.customer(q.customer_id), f"{q.id}: unknown customer {q.customer_id}"
    if q.order_id is not None:
        order = data.order(q.order_id)
        assert order, f"{q.id}: unknown order {q.order_id}"
        assert order["customer_id"] == q.customer_id


@pytest.mark.parametrize("q", QUERIES, ids=lambda q: q.id)
def test_steps_are_lesson_steps_and_text_is_short(q):
    assert q.steps, f"{q.id} is not used by any lesson step"
    assert all(1 <= s < data.ALL_QUERIES_FROM_STEP for s in q.steps)
    assert len(q.text) <= 140  # fits one line in the picker
    assert q.teaches


@pytest.mark.parametrize("step", range(1, 10))
def test_every_lesson_step_has_enough_queries(step):
    assert len(data.queries_for_step(step)) >= 2


def test_full_flow_steps_use_every_query():
    for step in (10, 11, 12):
        assert data.queries_for_step(step) == list(QUERIES)


def test_each_label_value_appears_somewhere():
    """So every team / intent / level has at least one example to learn from."""
    for label, allowed in data.LABELS.items():
        assert {q.gold[label] for q in QUERIES} == set(allowed), label


def test_unsafe_queries_are_the_unsafe_kind():
    assert {q.id for q in QUERIES if q.gold["unsafe"]} == {q.id for q in QUERIES if q.kind == "unsafe"}


def test_accepts_gold_and_alternatives_only():
    q = data.query("q09")
    assert q.accepts("team", "billing")
    assert q.accepts("team", "shipping")
    assert not q.accepts("team", "technical")


# --- facts: recompute from the order records, the same way step 06's code will ---


def _duplicate_charge(order):
    captured = [c["amount"] for c in order["charges"] if c["status"] == "captured"]
    return len(captured) > len(set(captured))


def _return_eligible(order):
    return (data.today() - date.fromisoformat(order["delivered_on"])).days <= 30


def _late_credit_eligible(order):
    late_by = date.fromisoformat(order["delivered_on"]) - date.fromisoformat(order["promised_by"])
    return late_by.days > 3


def _refund_overdue(order):
    started = date.fromisoformat(order["refunds"][0]["initiated_on"])
    working_days = sum(
        1 for n in range(1, (data.today() - started).days + 1) if (started + timedelta(days=n)).weekday() < 5
    )
    return order["refunds"][0]["status"] == "pending" and working_days > 7


FACT_CHECKS = {
    "duplicate_charge": _duplicate_charge,
    "return_eligible": _return_eligible,
    "late_credit_eligible": _late_credit_eligible,
    "refund_overdue": _refund_overdue,
}


@pytest.mark.parametrize("q", [q for q in QUERIES if q.facts], ids=lambda q: q.id)
def test_facts_match_the_order_record(q):
    order = data.order(q.order_id)
    for fact, expected in q.facts.items():
        assert FACT_CHECKS[fact](order) is expected, f"{q.id}: {fact}"


def test_needs_code_queries_cover_both_yes_and_no_answers():
    answers = [v for q in QUERIES if q.kind == "needs_code" for v in q.facts.values()]
    assert True in answers and False in answers


# --- store data ---


def test_order_totals_match_items():
    for order in data.store()["orders"]:
        assert order["total"] == sum(i["qty"] * i["price"] for i in order["items"]), order["id"]


def test_large_state_customer_has_many_orders():
    assert len(data.orders_of("C-2001")) >= 8


def test_today_is_fixed():
    assert data.today() == date(2026, 10, 8)


def test_policy_mentions_the_numbers_the_lessons_use():
    policy = data.policy()
    for needle in ("30 days", "3–5 working days", "₹99", "₹10,000", "7 working days"):
        assert needle in policy


# --- drafts (step 09) ---


def test_every_step_9_query_has_a_draft_with_valid_labels():
    for q in data.queries_for_step(9):
        assert q.draft, f"{q.id} is used in step 09 but has no draft"
        assert set(q.draft["gold"]) == set(data.DRAFT_LABELS)
        assert all(type(v) is bool for v in q.draft["gold"].values())


def test_drafts_include_good_and_flawed_replies():
    golds = [tuple(q.draft["gold"].values()) for q in QUERIES if q.draft]
    assert (True, True) in golds  # good: send it
    assert any(False in g for g in golds)  # flawed: escalate


def test_accepts_is_type_strict():
    q = data.query("q02")  # frustration 1, urgent True
    assert q.accepts("frustration", 1)
    assert not q.accepts("frustration", True)
    assert not q.accepts("urgent", 1)


def test_expected_merges_gold_facts_and_draft():
    expected = data.query("q02").expected()
    assert expected["team"] == "billing"
    assert expected["duplicate_charge"] is True
    assert expected["on_policy"] is False
