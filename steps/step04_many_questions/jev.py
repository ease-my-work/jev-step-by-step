# Step 04 — Five questions in one request, about the message AND the customer's order (JSON state).
# Compare with: llm_only.py (one big Gemini JSON call) and ../step03_score/jev.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from typesafe_sdk import Choice, Noul, Score

import kit

jev = kit.jev_client()

QUESTIONS = {  # NEW: all five are answered in parallel, in one request
    "team": Choice(
        instructions="Which support team should handle this?",
        criteria={
            "billing": "payments, charges, refunds, returns",
            "shipping": "delivery, tracking, address, damage",
            "technical": "app or website errors",
            "account": "login, password, profile",
            "other": "product questions, thanks, anything else",
        },
    ),
    "urgent": Noul(  # the exact wording tested in step 01 — shorter versions scored worse
        instructions="The customer needs help today.",
        criteria={
            "true": "Money was taken wrongly, there is a deadline today or tomorrow, "
            "or they can't do something urgent.",
            "false": "A question, a request or feedback that can wait a day or two.",
        },
    ),
    "frustration": Score(
        instructions="How frustrated is the customer?",
        criteria=["calm", "annoyed but polite", "angry: shouting, insults, threats, or many messages"],
    ),
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


def run(query):
    state = {  # NEW: JSON state. Give each part a clear name; JEV reads them all.
        "message": query.text,
        "customer": kit.data.customer(query.customer_id),
        "order": kit.data.order(query.order_id),
    }
    response = jev.system_one(state=state, questions=QUESTIONS)  # CHANGED: one call, five answers
    return dict(response.answers)
