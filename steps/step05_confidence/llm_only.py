# Step 05 — The LLM-only way to "know when you're unsure": ask the model to rate its own confidence.
# Compare with: jev.py and ../step02_choice/llm_only.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from google.genai import types

import kit

gemini = kit.gemini_client()

PROMPT = """Which support team should handle this customer message?
billing: Payments, charges, refunds and returns.
shipping: Delivery, tracking, address changes, items damaged in transit.
technical: Errors in the app or website.
account: Login, password and profile.
other: Product questions, thanks, anything else.

Be honest about how sure you are. If the message could fit more than one team, say "low" or "medium".

Customer message:
{message}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "team": {"type": "string", "enum": ["billing", "shipping", "technical", "account", "other"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["team", "confidence"],
}

ROUTE = {"high": "auto", "medium": "review", "low": "human"}  # NEW: the only thresholds an LLM label allows


def run(query):
    response = gemini.models.generate_content(
        model=kit.GEMINI_MODEL,
        contents=PROMPT.format(message=query.text),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA,
            thinking_config=kit.GEMINI_THINKING,
        ),
    )
    answer = response.parsed
    return {**answer, "route": ROUTE[answer["confidence"]]}
