# Step 06 — The LLM-only way: give Gemini the message, the order record and the rules, and let it do the maths.
# Compare with: jev.py (JEV reads the claim, code checks it)
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import json

from google.genai import types

import kit

gemini = kit.gemini_client()

PROMPT = """Today is {today}. A customer wrote: "{message}"

Their order record:
{order}

1. claim: what are they claiming or asking for? charged_twice, return_item, late_delivery_credit,
   refund_not_received, or other.
2. verdict: is the claim true under these rules? (false if claim is "other")
   - charged_twice: the same amount was captured twice. A reversed (failed) attempt is not a charge.
   - return_item: delivered 30 days ago or less.
   - late_delivery_credit: delivered more than 3 days after the promised date.
   - refund_not_received: a refund has been pending for more than 7 working days (Mon–Fri)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "claim": {
            "type": "string",
            "enum": ["charged_twice", "return_item", "late_delivery_credit", "refund_not_received", "other"],
        },
        "verdict": {"type": "boolean"},
    },
    "required": ["claim", "verdict"],
}

FACT = {  # the same names jev.py uses, so both sides are graded the same way
    "charged_twice": "duplicate_charge",
    "return_item": "return_eligible",
    "late_delivery_credit": "late_credit_eligible",
    "refund_not_received": "refund_overdue",
}


def run(query):
    order = kit.data.order(query.order_id)
    response = gemini.models.generate_content(
        model=kit.GEMINI_MODEL,
        contents=PROMPT.format(today=kit.data.today(), message=query.text, order=json.dumps(order, indent=1)),
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=SCHEMA, thinking_config=kit.GEMINI_THINKING
        ),
    )
    answer = response.parsed
    result = {"claim": answer["claim"]}
    if answer["claim"] in FACT:
        result[FACT[answer["claim"]]] = answer["verdict"]
    return result
