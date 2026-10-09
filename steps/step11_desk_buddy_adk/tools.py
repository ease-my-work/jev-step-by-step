# Step 11 — Plain-code helpers: the records an agent sees (with checks already worked out), and fixed replies.
# Compare with: ../step10_desk_buddy/replies.py and ../step06_judge_and_calculate/orders.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it. @kit.stage only draws a box on the flow chart.
import json
import re
from datetime import date, timedelta

import kit

BLOCKED = (
    "Sorry, I can't help with that message. For your safety, please never share card numbers, CVVs, OTPs or "
    "passwords in chat. A member of our team will review this conversation."
)
CARD_NUMBER = re.compile(r"\b(?:\d[ -]?){13,19}\b")
ASKS_FOR_PERSON = re.compile(r"\b(talk|speak|chat)\s+(to|with)\s+(someone|somebody|a\s+(person|human|agent))", re.I)


@kit.stage("Card number check (code)")
def has_card_number(text):
    return CARD_NUMBER.search(text) is not None


def _working_days_since(day, today):
    return sum(1 for n in range(1, (today - day).days + 1) if (day + timedelta(days=n)).weekday() < 5)


def _checks(message, order):
    """The step 06 and 10 checks: code does the dates, money and exact rules, so no agent has to."""
    asks_for_person = ASKS_FOR_PERSON.search(message) is not None
    if order is None:
        return {"asks_for_person": asks_for_person}
    today = kit.data.today()
    pending = [r for r in order["refunds"] if r["status"] == "pending"]
    captured = [c["amount"] for c in order["charges"] if c["status"] == "captured"]
    delivered = date.fromisoformat(order["delivered_on"]) if order["delivered_on"] else None
    promised = date.fromisoformat(order["promised_by"])
    return {
        "charged_twice": len(captured) > len(set(captured)),
        "days_since_delivery": (today - delivered).days if delivered else None,
        "within_30_day_return_window": bool(delivered) and (today - delivered).days <= 30,
        "days_late": max(0, ((delivered or today) - promised).days),
        "refund_overdue": bool(pending)
        and _working_days_since(date.fromisoformat(pending[0]["initiated_on"]), today) > 7,
        "asks_for_person": asks_for_person,
    }


@kit.stage("Load records (code)")
def records(query):
    """Everything an agent may use, as one JSON string for the session state."""
    order = kit.data.order(query.order_id)
    return json.dumps(
        {
            "today": str(kit.data.today()),
            "customer": kit.data.customer(query.customer_id),
            "order": order,
            "checks": _checks(query.text, order),
            "products": kit.data.store()["products"],
        },
        ensure_ascii=False,
    )


@kit.stage("Order lookup (code)")
def order_status(order):
    if order is None:
        return "I couldn't find an order on your account. Could you share the order number (it starts with ORD-)?"
    item = order["items"][0]["name"]
    promised = date.fromisoformat(order["promised_by"])
    if order["status"] == "delivered":
        return f"Your {item} (order {order['id']}) was delivered on {order['delivered_on']}."
    if order["status"] == "processing":
        return f"Your {item} (order {order['id']}) is being packed and is due by {promised:%d %b}."
    tracking = order["tracking"]
    text = (
        f"Your {item} (order {order['id']}) is with {order['carrier']}. Latest update, {tracking['last_update']}: "
        f"{tracking['last_location']}. It was due by {promised:%d %b}."
    )
    if promised < kit.data.today():
        text += " Sorry, it's running late. I've asked the carrier for an update; you'll hear from us within 24 hours."
    return text
