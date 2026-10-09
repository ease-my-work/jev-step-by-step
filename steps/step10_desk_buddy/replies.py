# Step 10 — Every way Desk Buddy can reply: fixed texts, a code-written order update, or a Gemini-written reply.
# Compare with: jev.py (which picks one) and ../step08_route_then_reply/order_status.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it. @kit.stage only draws a box on the flow chart.
import json
from datetime import date

from google.genai import types

import kit

gemini = kit.gemini_client()

BLOCKED = (
    "Sorry, I can't help with that message. For your safety, please never share card numbers, CVVs, OTPs or "
    "passwords in chat. A member of our team will review this conversation."
)
HANDOVER = "Thanks for your patience. I'm passing this to a member of our team now; they'll reply within 4 hours."

WRITER = """You are Desk Buddy, a support assistant for Pebble Store. Write a short, warm reply (max 3 sentences)
to the customer. Follow the policy exactly; never promise more. Use only facts from the records below.

Policy:
{policy}

Records: {records}

Customer: {message}"""


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


def write(message, records):
    """Gemini writes the reply. It never decides anything — the route was already chosen."""
    prompt = WRITER.format(policy=kit.data.policy(), records=json.dumps(records, ensure_ascii=False), message=message)
    config = types.GenerateContentConfig(thinking_config=kit.GEMINI_THINKING)
    return gemini.models.generate_content(model=kit.GEMINI_MODEL, contents=prompt, config=config).text
