# Step 02 — The same task for Gemini: pick a team, as JSON restricted to the same five teams.
# Compare with: jev.py and ../step01_hello_noul/llm_only.py
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

Customer message:
{message}"""

SCHEMA = {
    "type": "object",
    "properties": {
        # CHANGED: "enum" keeps the answer to our five teams. Remove it and see "Break it" in the README.
        "team": {"type": "string", "enum": ["billing", "shipping", "technical", "account", "other"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["team", "confidence"],
}


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
    return response.parsed  # e.g. {"team": "billing", "confidence": "high"}
