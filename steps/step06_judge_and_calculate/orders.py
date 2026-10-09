# Step 06 — Plain-code checks on the order record. Dates and money are code's job, not JEV's.
# Compare with: jev.py (which decides WHICH check to run) and llm_only.py (where the LLM does this maths itself)
# kit/ is plumbing (picker, timing, replay) — you can ignore it. @kit.stage only draws a box on the flow chart.
from datetime import date, timedelta

import kit


@kit.stage("Check charges")
def find_duplicate_charge(order):
    """Policy §2: the same amount captured twice. A reversed (failed) attempt is not a charge."""
    captured = [c["amount"] for c in order["charges"] if c["status"] == "captured"]
    return len(captured) > len(set(captured))


@kit.stage("Check return window")
def return_eligible(order):
    """Policy §1: returns within 30 days of delivery."""
    if not order["delivered_on"]:
        return False
    return (kit.data.today() - date.fromisoformat(order["delivered_on"])).days <= 30


@kit.stage("Check delivery date")
def late_credit_eligible(order):
    """Policy §4: ₹99 credit if delivered more than 3 days after the promised date."""
    if not order["delivered_on"]:
        return False
    late = date.fromisoformat(order["delivered_on"]) - date.fromisoformat(order["promised_by"])
    return late.days > 3


@kit.stage("Check refund date")
def refund_overdue(order):
    """Policy §3: a pending refund older than 7 working days goes to a human."""
    pending = [r for r in order["refunds"] if r["status"] == "pending"]
    if not pending:
        return False
    started, today = date.fromisoformat(pending[0]["initiated_on"]), kit.data.today()
    days = (started + timedelta(days=n) for n in range(1, (today - started).days + 1))
    return sum(1 for day in days if day.weekday() < 5) > 7
