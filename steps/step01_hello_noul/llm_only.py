# Step 01 — The same question asked to an LLM (Gemini), with JSON-schema output so the comparison is fair.
# Compare with: jev.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from google.genai import types

import kit

gemini = kit.gemini_client()  # a real google.genai.Client

PROMPT = """Does this customer need help today?
Yes: money was taken wrongly, there is a deadline today or tomorrow, or they can't do something urgent.
No: a question, a request or feedback that can wait a day or two.

Customer message:
{message}"""

# The LLM must reply in exactly this shape. We also ask how sure it is — compare that with JEV's probability.
SCHEMA = {
    "type": "object",
    "properties": {
        "urgent": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["urgent", "confidence"],
}


def run(query):
    response = gemini.models.generate_content(
        model=kit.GEMINI_MODEL,
        contents=PROMPT.format(message=query.text),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA,
            thinking_config=kit.GEMINI_THINKING,  # minimal thinking: the fastest fair setting for a yes/no answer
        ),
    )
    return response.parsed  # e.g. {"urgent": true, "confidence": "high"}
