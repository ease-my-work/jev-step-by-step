# Step 06 — JEV judges, code calculates: JEV reads what the customer claims; code checks it against the order.
# Compare with: llm_only.py (the LLM reads AND does the date maths) and orders.py (the checks)
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import orders  # NEW: plain-code checks — dates and charges
from typesafe_sdk import Choice

import kit

jev = kit.jev_client()

CLAIM = Choice(
    instructions="What is the customer claiming or asking for?",
    criteria={
        "charged_twice": "They say they were charged or debited twice for one order.",
        "return_item": "They want to return an item, or ask if they still can.",
        "late_delivery_credit": "They ask for compensation because delivery was late.",
        "refund_not_received": "They say a refund for a cancelled order hasn't arrived.",
        "other": "Anything else.",
    },
)

# NEW: each claim maps to ONE code check. JEV picks the claim; code decides if it's true.
CHECKS = {
    "charged_twice": ("duplicate_charge", orders.find_duplicate_charge),
    "return_item": ("return_eligible", orders.return_eligible),
    "late_delivery_credit": ("late_credit_eligible", orders.late_credit_eligible),
    "refund_not_received": ("refund_overdue", orders.refund_overdue),
}


def run(query):
    claim = jev.system_one(state=query.text, questions={"claim": CLAIM}).answers["claim"]
    result = {"claim": claim}
    if claim.choice in CHECKS:
        fact, check = CHECKS[claim.choice]
        result[fact] = check(kit.data.order(query.order_id))  # NEW: the order record, read by code
    return result
