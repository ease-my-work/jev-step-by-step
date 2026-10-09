# Step 01 — Is this customer message urgent? JEV answers a yes/no question (a Noul) with a probability.
# Compare with: llm_only.py (the same question, asked to Gemini).
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from typesafe_sdk import Noul

import kit

jev = kit.jev_client()  # NEW: a real TypeSafeClient, pinned to JEV_MODEL from .env

# NEW: a Noul is a yes/no question. JEV answers with the probability that the answer is "yes".
URGENT = Noul(
    instructions="The customer needs help today.",
    criteria={  # optional: say what "yes" and "no" mean, in plain words
        "true": "Money was taken wrongly, there is a deadline today or tomorrow, or they can't do something urgent.",
        "false": "A question, a request or feedback that can wait a day or two.",
    },
)


def run(query):
    response = jev.system_one(
        state=query.text,  # NEW: the "state" is what JEV looks at — here, just the customer's message
        questions={"urgent": URGENT},  # NEW: named questions; answers come back under the same names
    )
    return {"urgent": response.answers["urgent"].noul}  # e.g. 0.94 → 94% likely urgent
