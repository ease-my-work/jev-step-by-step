# Step 08 — JEV routes, then only the messages that need writing go to the LLM. Order status: code. Hard cases: humans.
# Compare with: llm_only.py (one big prompt classifies AND writes every reply) and order_status.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import json

import order_status
from google.genai import types
from typesafe_sdk import Choice, Noul

import kit

jev = kit.jev_client()
gemini = kit.gemini_client()  # NEW: JEV + LLM. The LLM only writes; it never decides the route.

TRIAGE = {
    "intent": Choice(
        instructions="What does the customer want done?",
        criteria={
            "order_status": "where is my order",
            "duplicate_charge": "charged twice",
            "refund_request": "money back, return, or a credit",
            "change_address": "change delivery address",
            "product_question": "question about a product",
            "complaint": "unhappy with item or service",
            "account_access": "can't log in or reset password",
            "tech_issue": "app or website error",
            "other": "anything else",
        },
    ),
    "needs_human": Noul(
        instructions="A human agent must handle this, not a bot.",
        criteria={
            "true": "Asks for a person; chargeback or legal threat; threatens staff; contacted support "
            "3+ times in 30 days; or the order is worth more than ₹10,000.",
            "false": "A bot can handle it.",
        },
    ),
}

HANDOVER = "Thanks for your patience. I'm passing this to a member of our team now; they'll reply within 4 hours."

WRITER = """You are Desk Buddy, a support assistant for Pebble Store. Write a short, warm reply (max 3 sentences)
to the customer. Follow the policy exactly; never promise more. Use only facts from the records below.

Policy:
{policy}

Records: {records}

Customer: {message}"""


def run(query):
    state = {
        "message": query.text,
        "customer": kit.data.customer(query.customer_id),
        "order": kit.data.order(query.order_id),
    }
    triage = jev.system_one(state=state, questions=TRIAGE).answers
    intent, human = triage["intent"], triage["needs_human"]
    # NEW: the route is decided by code, from JEV's answers
    if human.noul >= 0.5:
        handled_by, reply = "human", HANDOVER
    elif intent.choice == "order_status":
        handled_by, reply = "code", order_status.reply(state["order"])
    else:
        handled_by = "Gemini"
        records = json.dumps({**state, "products": kit.data.store()["products"]}, ensure_ascii=False)
        prompt = WRITER.format(policy=kit.data.policy(), records=records, message=query.text)
        config = types.GenerateContentConfig(thinking_config=kit.GEMINI_THINKING)
        reply = gemini.models.generate_content(model=kit.GEMINI_MODEL, contents=prompt, config=config).text
    return {"intent": intent, "needs_human": human.noul, "handled_by": handled_by, "reply": reply}
