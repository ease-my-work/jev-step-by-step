# Step 09 — Check a reply before it's sent. JEV judges the draft; send only if both checks pass.
# Compare with: llm_only.py (an LLM judging the same draft) and ../step07_guardrails/jev.py (checks on the INPUT)
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
from typesafe_sdk import Noul

import kit

jev = kit.jev_client()

CHECKS = {  # NEW: output guardrails — the same Noul idea, pointed at the reply instead of the message
    "answers_question": Noul(
        instructions="The draft reply deals with what the customer actually asked or needs.",
        criteria={
            "true": "It responds to their actual request with a concrete answer or next step.",
            "false": "It is generic, vague, or ignores the customer's question.",
        },
    ),
    "on_policy": Noul(
        instructions="Everything in the draft reply follows the policy and matches the records.",
        criteria={
            "true": "Every promise and fact in it is allowed by the policy and backed by the records.",
            "false": "It promises something faster or bigger than the policy allows, states a fact that the "
            "records contradict or don't contain, or asks for a card number, CVV, OTP or password.",
        },
    ),
}


def run(query):
    state = {  # NEW: the draft is part of the state, next to everything it must agree with
        "customer_message": query.text,
        "draft_reply": query.draft["text"],
        "policy": kit.data.policy(),
        "order": kit.data.order(query.order_id),
        "products": kit.data.store()["products"],
    }
    answers = jev.system_one(state=state, questions=CHECKS).answers
    send = all(answer.noul >= 0.5 for answer in answers.values())  # NEW: any doubt → a person looks first
    return {
        "answers_question": answers["answers_question"].noul,
        "on_policy": answers["on_policy"].noul,
        "decision": "send" if send else "escalate",
    }
