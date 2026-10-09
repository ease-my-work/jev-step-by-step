# Step 04 — The LLM's best equivalent: one Gemini call that returns all five labels as JSON.
# Compare with: jev.py and ../step03_score/llm_only.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import json

from google.genai import types

import kit

gemini = kit.gemini_client()

PROMPT = """Label this customer-support case.
team: billing (payments, charges, refunds, returns), shipping (delivery, tracking, address, damage),
  technical (app or website errors), account (login, password, profile), other (product questions, thanks, else).
urgent: true if money was taken wrongly, there is a deadline today or tomorrow, or they can't do something
  urgent; false if it's a question, a request or feedback that can wait a day or two.
frustration: 0 calm, 1 annoyed but polite, 2 angry (shouting, insults, threats, or many messages).
intent: order_status, duplicate_charge, refund_request (money back, return, or a credit), change_address,
  product_question, complaint, account_access, tech_issue, or other.
needs_human: true if they ask for a person, threaten a chargeback or legal action, threaten staff,
  contacted support 3+ times in 30 days, or the order is worth more than ₹10,000.

Case:
{case}"""

SCHEMA = {
    "type": "object",
    "properties": {  # NEW: five fields in one JSON answer
        "team": {"type": "string", "enum": ["billing", "shipping", "technical", "account", "other"]},
        "urgent": {"type": "boolean"},
        "frustration": {"type": "integer", "minimum": 0, "maximum": 2},
        "intent": {
            "type": "string",
            "enum": [
                "order_status",
                "duplicate_charge",
                "refund_request",
                "change_address",
                "product_question",
                "complaint",
                "account_access",
                "tech_issue",
                "other",
            ],
        },
        "needs_human": {"type": "boolean"},
    },
    "required": ["team", "urgent", "frustration", "intent", "needs_human"],
}


def run(query):
    case = {
        "message": query.text,
        "customer": kit.data.customer(query.customer_id),
        "order": kit.data.order(query.order_id),
    }  # NEW: the same JSON state JEV gets
    response = gemini.models.generate_content(
        model=kit.GEMINI_MODEL,
        contents=PROMPT.format(case=json.dumps(case, ensure_ascii=False, indent=1)),
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=SCHEMA, thinking_config=kit.GEMINI_THINKING
        ),
    )
    return response.parsed
