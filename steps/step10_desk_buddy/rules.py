# Step 10 — Policy rules that code checks exactly, next to JEV's judgement (steps 06 and 07: code checks facts).
# Compare with: jev.py (which combines these with JEV's answers) and ../step06_judge_and_calculate/orders.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it. @kit.stage only draws a box on the flow chart.
import re
from datetime import date, timedelta

import kit

CARD_NUMBER = re.compile(r"\b(?:\d[ -]?){13,19}\b")
ASKS_FOR_PERSON = re.compile(r"\b(talk|speak|chat)\s+(to|with)\s+(someone|somebody|a\s+(person|human|agent))", re.I)


@kit.stage("Rules (code)")
def check(message, order):
    """NEW: exact checks for three policy rules. Steps 07 and 08 showed JEV can miss these."""
    return {
        "card_number": CARD_NUMBER.search(message) is not None,  # policy §6 — step 07's q20
        "asks_for_person": ASKS_FOR_PERSON.search(message) is not None,  # policy §5 — step 08's q12
        "refund_overdue": _refund_overdue(order),  # policy §3 — step 06
    }


def _refund_overdue(order):
    pending = [r for r in (order or {}).get("refunds", []) if r["status"] == "pending"]
    if not pending:
        return False
    started, today = date.fromisoformat(pending[0]["initiated_on"]), kit.data.today()
    days = (started + timedelta(days=n) for n in range(1, (today - started).days + 1))
    return sum(1 for day in days if day.weekday() < 5) > 7
