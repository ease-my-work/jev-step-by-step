# Step 09 — "LLM-as-judge": a second Gemini call checks the draft reply against the policy and records.
# Compare with: jev.py (JEV as judge)
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import json

from google.genai import types

import kit

gemini = kit.gemini_client()

PROMPT = """Check this draft reply from a support assistant before it is sent.
answers_question: does the draft deal with what the customer actually asked or needs? (false if generic or vague)
on_policy: does everything in it follow the policy and match the records? (false if it promises something faster or
  bigger than the policy allows, states a fact the records contradict or don't contain, or asks for a card number,
  CVV, OTP or password)

{case}"""

SCHEMA = {
    "type": "object",
    "properties": {"answers_question": {"type": "boolean"}, "on_policy": {"type": "boolean"}},
    "required": ["answers_question", "on_policy"],
}


def run(query):
    case = {
        "customer_message": query.text,
        "draft_reply": query.draft["text"],
        "policy": kit.data.policy(),
        "order": kit.data.order(query.order_id),
        "products": kit.data.store()["products"],
    }
    response = gemini.models.generate_content(
        model=kit.GEMINI_MODEL,
        contents=PROMPT.format(case=json.dumps(case, ensure_ascii=False, indent=1)),
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=SCHEMA, thinking_config=kit.GEMINI_THINKING
        ),
    )
    verdict = response.parsed
    return {**verdict, "decision": "send" if all(verdict.values()) else "escalate"}
