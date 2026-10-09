# Step 02 — Which team should handle this message? JEV picks one option from your list (a Choice).
# Compare with: llm_only.py (same task, Gemini only) and ../step01_hello_noul/jev.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from typesafe_sdk import Choice

import kit

jev = kit.jev_client()

# NEW: a Choice question. JEV can only answer with one of these keys — it never invents a team.
TEAM = Choice(
    instructions="Which support team should handle this customer message?",
    criteria={
        "billing": "Payments, charges, refunds and returns.",
        "shipping": "Delivery, tracking, address changes, items damaged in transit.",
        "technical": "Errors in the app or website.",
        "account": "Login, password and profile.",
        "other": "Product questions, thanks, anything else.",
    },
)


def run(query):
    response = jev.system_one(state=query.text, questions={"team": TEAM})  # CHANGED: Choice instead of Noul
    team = response.answers["team"]  # NEW: .choice, .confidence, and .probabilities (one per team)
    return {"team": team}
