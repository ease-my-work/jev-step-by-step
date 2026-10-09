# Step 10 · Desk Buddy — the full flow in plain Python

Everything from steps 01–09, joined into one support assistant:

```
message ─▶ ① JEV: guard + triage (8 questions, 1 call) + code rules
             │
             ├─ unsafe ─────────────▶ blocked — fixed reply, no LLM ever sees it
             ├─ needs a person ─────▶ handed over (fixed reply)
             ├─ "where's my order?" ─▶ code writes the reply from tracking data
             └─ everything else ────▶ ② Gemini writes a reply
                                      ③ JEV checks it ─▶ send, or hold for a person
```

The LLM-only version is one big Gemini call per message that screens, triages and writes — the simplest thing that
works, and a strong baseline.

```bash
python steps/step10_desk_buddy/run.py
```

## What changed

| File | What it holds | From step |
|---|---|---|
| `questions.py` | Every JEV question: guards, triage, reply checks | 01–04, 07, 09 |
| `rules.py` | **New:** exact policy rules in code — card number, "talk to a person", refund overdue | 06, 07, 08 |
| `replies.py` | Fixed replies, the order-status reply in code, and the Gemini writer | 08 |
| `jev.py` | The pipeline: guard → triage → route → reply → check | all |
| `llm_only.py` | One Gemini call that does everything | — |

Two fixes went in after the first full run, and both are lessons in themselves:

- **Urgency now uses step 01's exact wording.** A shortened version scored 17/24 here; the tested wording scores
  20–21/24 (see step 04's *Break it*).
- **`rules.py`** catches what JEV missed in earlier steps: "talk to someone" (step 08's q12) and an overdue refund
  (step 06). Policy rules that can be checked exactly belong in code.

## Why

This is the shape of the whole course: **JEV decides, code calculates, the LLM writes.** Every decision — is it safe,
who handles it, is the reply OK to send — is a fast typed answer. The LLM is only called when there's writing to do,
and its output is checked before it goes out.

## Key code

```python
first = jev.system_one(state=state, questions={**questions.GUARDS, **questions.TRIAGE}).answers
rule = rules.check(query.text, order)
unsafe = 1.0 if rule["card_number"] else max(first[name].noul for name in questions.GUARDS)
...
if unsafe >= 0.5:            return blocked
if result["needs_human"] >= 0.5: return handed over
if intent == "order_status": return replies.order_status(order)      # code
draft = replies.write(query.text, records)                           # Gemini
checks = jev.system_one(state=check_state, questions=questions.CHECKS).answers
```

## Run it

```bash
python steps/step10_desk_buddy/run.py              # pick a message, watch every stage
python steps/step10_desk_buddy/run.py --all        # all 24 messages
python steps/step10_desk_buddy/run.py --replay     # no API keys needed
```

## JEV vs LLM-only

Measured on 2026-10-08 over all 24 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter; Gemini
`gemini-3.5-flash` (minimal thinking). Step 12 runs the same comparison again and writes a full report.

| | JEV + code + LLM | LLM-only |
|---|---|---|
| Labels correct (6 labels × 24) | 139/144 | 140/144 |
| — urgent | 21/24 | 23/24 |
| — frustration | 23/24 | 21/24 |
| Time to first decision p50 | **563 ms** | 1,725 ms |
| Full reply time p50 | 2,578 ms | **1,725 ms** |
| LLM calls per message | **0.58** | 1.00 |
| Cost per 1,000 messages | **$1.37** | $3.01 |
| Unsafe messages the LLM never saw | **3/3** | 0/3 |
| Replies checked before sending | **every LLM reply** | none |

**Who handled what:** JEV pipeline — 4 by code, 12 Gemini replies sent, 2 Gemini drafts held for review, 3 handed to
a person, 3 blocked. LLM-only — 18 Gemini replies, 3 handed over, 3 blocked.

**One draft the check stopped (q24, late-delivery credit):** Gemini's draft promised *"you will receive an email
confirmation… within the next few minutes"* — nothing in the policy says so. JEV held it for a person. The LLM-only
reply to the same message said *"I have credited this amount to your account"* — an action Desk Buddy can't take —
and went straight out.

## When LLM-only wins

- **Speed of the full reply.** When a reply must be written, LLM-only makes one call; the JEV pipeline makes three
  (triage → write → check). Its p50 is ~0.85 s faster. JEV wins on the *first decision* (routing, blocking, handing
  over), which is what a queue or a UI needs immediately.
- **Accuracy is a draw** on this set: 139 vs 140 labels.
- **Simplicity.** One prompt is less code than a pipeline. The pipeline buys you control: unsafe text never reaches
  the LLM, routine questions cost nothing, and every reply is checked.

## Break it

**Skip the check.** Return the draft straight after `replies.write(...)`. Run q24: the made-up "email confirmation
within minutes" goes to the customer. The check adds ~0.5 s and costs ~$0.06 per 1,000 messages.

## Recap

- JEV decides, code calculates, the LLM writes — and JEV checks what the LLM wrote.
- Put exact policy rules in code; use JEV for judgement.
- Measure both the first decision and the full reply; they tell different stories.

Next: **[Step 11 · Desk Buddy in Google ADK](../step11_desk_buddy_adk/)**
