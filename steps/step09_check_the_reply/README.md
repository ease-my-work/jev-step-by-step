# Step 09 · Check the reply — JEV as judge

LLMs write good replies — and sometimes promise a refund "within the hour", or invent a product spec. Before Desk
Buddy sends anything an LLM wrote, JEV checks it: **does it answer the question? Does it follow the policy?** Any
doubt → a person looks first.

The LLM-only version uses **LLM-as-judge**: a second Gemini call checks the draft.

```bash
python steps/step09_check_the_reply/run.py
```

Each message in this step comes with a pre-written **draft reply** (shown on screen), so both judges check exactly
the same text, and we know the right verdict for each: two are good, three are flawed.

## What changed

| | |
|---|---|
| **Added** | `CHECKS` — two `Noul`s about the *draft*: `answers_question`, `on_policy` |
| **Changed** | The state now holds the customer message, the draft, the policy and the records |
| **Added** | `decision` — send only if every check passes |

## Why

Step 07 guarded the **input**. This guards the **output**. A judge runs on every reply, so — like the input guard —
it should be fast and cheap. An LLM-as-judge doubles your LLM calls.

## Key concepts

- **Output guardrail / judge** — a yes/no check on generated text before it reaches a customer.
- **Put the evidence in the state.** "Follows the policy" can only be checked if the policy and the records are there.
- **Escalate on doubt** — a failed check doesn't block the customer; it sends the draft to a person.

## Key code

```python
state = {
    "customer_message": query.text,
    "draft_reply": query.draft["text"],
    "policy": kit.data.policy(),
    "order": kit.data.order(query.order_id),
    "products": kit.data.store()["products"],
}
answers = jev.system_one(state=state, questions=CHECKS).answers
send = all(answer.noul >= 0.5 for answer in answers.values())
```

## Run it

```bash
python steps/step09_check_the_reply/run.py
python steps/step09_check_the_reply/run.py --all
python steps/step09_check_the_reply/run.py --replay
```

## What happened (2026-10-08)

| Draft | What's wrong | JEV answers / on_policy → decision | Gemini judge → decision |
|---|---|---|---|
| q02 "…back within the hour" | promises faster than policy (3–5 working days) | 0.85 / **0.02** → escalate ✔ | escalate ✔ |
| q05 lamp return, 5–7 working days | nothing | 0.94 / 0.80 → send ✔ | **escalate** ✘ (false alarm) |
| q07 "works on 110V" | invents a spec (it's 220–240V only) | 0.61 / **0.02** → escalate ✔ | escalate ✔ |
| q09 kettle: replacement or refund | nothing | 0.92 / 0.52 → send ✔ | send ✔ |
| q17 "read the refund policy on our website" | ignores the question; overdue refund should go to a person | **0.06** / 0.22 → escalate ✔ | escalate ✔ |

| | JEV judge | LLM-as-judge |
|---|---|---|
| Correct verdicts | 10/10 checks | 9/10 checks |
| Latency p50 | **815 ms** | 1,380 ms |
| Cost per 1,000 checks | **$0.064** | $2.048 |

Both judges caught every flawed draft. Gemini also blocked one good draft.

**How these drafts were checked.** Our first versions of the q05 and q09 "good" drafts said "free pickup" and "a
replacement is usually quicker" — claims the policy doesn't make. The judges flagged them, they were right, and we
rewrote the drafts. We also changed q17's expected verdict after both judges pointed out that the policy says an
overdue refund must go to a person. Writing a good test set is part of the work.

## When LLM-only wins

- **An LLM judge can explain itself** ("the policy says 3–5 working days, not one hour"), which helps the person who
  reviews the draft. JEV only says yes or no.
- q09's on_policy came in at 0.52 — a pass by a hair. A threshold of 0.6 would have escalated a good reply. Tune it
  with real drafts.

## Break it

**Remove the evidence.** Make one small mistake in q05's draft — refund **₹1,999** instead of ₹1,899 — and compare
the `on_policy` answer with and without the order record in the state (2026-10-08):

| q05 draft | with the order record | without it |
|---|---|---|
| correct amount (₹1,899) | 0.80 → send | 0.30 → escalate |
| wrong amount (₹1,999) | **0.04** → escalate | 0.28 → escalate |

With the record, JEV spots a ₹100 slip. Without it, it can't tell the right draft from the wrong one, so it doubts
both. (Obvious problems like "refund within the hour" are caught either way: they look wrong on their own.) A judge
can only check what's in the state.

## Recap

- Check the output, not just the input. Escalate on doubt.
- Put the policy and the records in the state; a judge can't check what it can't see.
- A JEV judge costs a fraction of an LLM judge, so you can afford to run it on every reply.

## Learn more

- [JEV-as-a-Judge (arXiv)](https://arxiv.org/pdf/2609.26550)
- [Citation verification / LLM guardrails cookbooks](https://docs.typesafe.ai/llms.txt)

Next: **[Step 10 · Desk Buddy — the full flow](../step10_desk_buddy/)**
