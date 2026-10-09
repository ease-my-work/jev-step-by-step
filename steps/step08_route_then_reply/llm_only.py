# Step 08 — The LLM-only way: one big prompt that classifies the message AND writes the reply, every time.
# Compare with: jev.py (JEV routes; the LLM only writes when needed)
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import json

from google.genai import types

import kit

gemini = kit.gemini_client()

PROMPT = """You are Desk Buddy, a support assistant for Pebble Store.
1. intent: what does the customer want done? order_status, duplicate_charge, refund_request (money back, return,
   or a credit), change_address, product_question, complaint, account_access, tech_issue, or other.
2. needs_human: true if they ask for a person, threaten a chargeback or legal action, threaten staff, contacted
   support 3+ times in 30 days, or the order is worth more than ₹10,000.
3. reply: a short, warm reply (max 3 sentences). If needs_human, say a team member will reply within 4 hours.
   Follow the policy exactly; never promise more. Use only facts from the records below.

Policy:
{policy}

Records: {records}

Customer: {message}"""

INTENTS = ["order_status", "duplicate_charge", "refund_request", "change_address", "product_question", "complaint"]
SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": [*INTENTS, "account_access", "tech_issue", "other"]},
        "needs_human": {"type": "boolean"},
        "reply": {"type": "string"},
    },
    "required": ["intent", "needs_human", "reply"],
}


def run(query):
    records = {
        "customer": kit.data.customer(query.customer_id),
        "order": kit.data.order(query.order_id),
        "products": kit.data.store()["products"],
    }
    response = gemini.models.generate_content(
        model=kit.GEMINI_MODEL,
        contents=PROMPT.format(
            policy=kit.data.policy(), records=json.dumps(records, ensure_ascii=False), message=query.text
        ),
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=SCHEMA, thinking_config=kit.GEMINI_THINKING
        ),
    )
    return {**response.parsed, "handled_by": "Gemini"}
