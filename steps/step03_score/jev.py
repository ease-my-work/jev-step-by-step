# Step 03 — How frustrated is the customer? JEV rates it on an ordered scale (a Score).
# Compare with: llm_only.py (same task, Gemini only) and ../step02_choice/jev.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from typesafe_sdk import Score

import kit

jev = kit.jev_client()

# NEW: a Score question. The criteria are ordered levels: index 0 is the lowest, index 2 the highest.
FRUSTRATION = Score(
    instructions="How frustrated is the customer?",
    criteria=[
        "calm: no sign of annoyance",
        "annoyed: unhappy or impatient, but polite",
        "angry: shouting, insults, threats, or says they've written many times",
    ],
)


def run(query):
    response = jev.system_one(state=query.text, questions={"frustration": FRUSTRATION})  # CHANGED: Score
    frustration = response.answers["frustration"]
    # NEW: .score is the expected level (e.g. 1.3 = between annoyed and angry, closer to annoyed),
    # .probabilities has one value per level, and .legend maps each level back to your text.
    return {"frustration": frustration}
