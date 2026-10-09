# Step 05 — Know when you're unsure: JEV's confidence decides auto-reply, human review, or human handover.
# Compare with: llm_only.py (Gemini's self-reported confidence) and ../step02_choice/jev.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from typesafe_sdk import Choice

import kit

jev = kit.jev_client()

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

# NEW: thresholds live in YOUR code. Pick them by risk: a wrong auto-reply costs more than a review.
AUTO = 0.8  # at least this confident → reply automatically
REVIEW = 0.4  # at least this confident → a person checks the draft first; below → a person handles it


def route(confidence):
    if confidence >= AUTO:
        return "auto"
    if confidence >= REVIEW:
        return "review"
    return "human"


def run(query):
    response = jev.system_one(state=query.text, questions={"team": TEAM})
    team = response.answers["team"]
    # NEW: .confidence is how far the top answer stands above an even split (0 = a coin toss, 1 = certain)
    return {"team": team, "route": route(team.confidence)}
