# Step 03 — The same task for Gemini: a frustration level 0, 1 or 2, as JSON.
# Compare with: jev.py and ../step02_choice/llm_only.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from google.genai import types

import kit

gemini = kit.gemini_client()

PROMPT = """How frustrated is the customer? Answer with a level:
0 = calm: no sign of annoyance
1 = annoyed: unhappy or impatient, but polite
2 = angry: shouting, insults, threats, or says they've written many times

Customer message:
{message}"""

SCHEMA = {
    "type": "object",
    "properties": {
        # CHANGED: an integer level. Gemini's schema only allows text in "enum", so we bound it instead.
        "frustration": {"type": "integer", "minimum": 0, "maximum": 2},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["frustration", "confidence"],
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
    return response.parsed  # e.g. {"frustration": 1, "confidence": "high"}
