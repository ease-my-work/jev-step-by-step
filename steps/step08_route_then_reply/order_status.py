# Step 08 — Answering "where is my order?" with plain code: no model needed, instant, always correct.
# Compare with: jev.py (which decides when to use this) and llm_only.py (where the LLM writes every reply)
# kit/ is plumbing (picker, timing, replay) — you can ignore it. @kit.stage only draws a box on the flow chart.
from datetime import date

import kit


@kit.stage("Order lookup (code)")
def reply(order):
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
