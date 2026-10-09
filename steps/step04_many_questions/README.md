# Step 04 · Many questions — five answers, one call

Desk Buddy now triages properly: **team, urgent, frustration, intent, needs a human?** — all five in one JEV request,
looking at the message **and** the customer's record and order (JSON state).

```bash
python steps/step04_many_questions/run.py
```

## What changed

| | |
|---|---|
| **Added** | Five questions in one `QUESTIONS` dict: `Choice`, `Noul` and `Score` together |
| **Changed** | `state` is now JSON: `{"message", "customer", "order"}` |
| **Changed** | `llm_only.py` — one big JSON prompt with all five fields (the LLM's best equivalent) |

## Why

Steps 01–03 asked one question each. A real triage needs several. With an LLM you either make five calls (slow,
expensive) or one big prompt (one long answer). JEV answers **every question in parallel against the same state**, so
adding questions barely changes the time. TypeSafe's own benchmark: 13 questions in one call was 10× faster and 12×
cheaper than 13 separate calls, with the same answers.

Some answers also need more than the message. "Needs a human" depends on how many times the customer has written and
how much the order is worth, so the state now includes the customer and order records.

## Key concepts

- **Fan-out** — many named questions, one request. Each is answered independently, against the same state.
- **JSON state** — pass a dict. Give each part a clear name (`message`, `customer`, `order`); JEV reads them all.
- **Mixing primitives** — Choice, Noul and Score can sit in the same request.

## Key code

```python
QUESTIONS = {
    "team": Choice(...), "urgent": Noul(...), "frustration": Score(...),
    "intent": Choice(...), "needs_human": Noul(...),
}
state = {
    "message": query.text,
    "customer": kit.data.customer(query.customer_id),
    "order": kit.data.order(query.order_id),
}
response = jev.system_one(state=state, questions=QUESTIONS)   # one call, five answers
```

## Run it

```bash
python steps/step04_many_questions/run.py
python steps/step04_many_questions/run.py --all
python steps/step04_many_questions/run.py --replay
```

## Try these messages

| Message | Look for |
|---|---|
| **q16** "THIRD time I'm writing…" | needs_human 0.97: repeated contact + a ₹62,990 laptop + chargeback threat |
| **q11** "…my account and my last order?" | A customer with 9 orders. Two topics, one message |
| **q04** "Can I change my delivery address?…" | Not urgent (JEV 0.34). Gemini said urgent — "this weekend" |

## JEV vs LLM-only

Measured on 2026-10-08, `--all` over 7 messages × 5 labels. JEV `typesafe/jev-1.13-20260917` via OpenRouter; Gemini
`gemini-3.5-flash` (minimal thinking).

| | JEV | LLM-only |
|---|---|---|
| team / intent / frustration / needs_human | 7/7 each | 7/7 each |
| urgent | 7/7 | 6/7 (q04) |
| Latency p50 / p95 | **760 ms** / 975 ms | 1,416 ms / 1,522 ms |
| Cost per 1,000 messages | **$0.046** | $1.196 |

**More questions, same time.** Same message (q02) and state, asked 1, 5 and 8 questions in turn, five rounds
(2026-10-08):

| Questions in the request | Median latency | Input tokens |
|---|---|---|
| 1 | 470 ms | 762 |
| 5 | 499 ms | 1,179 |
| 8 | 477 ms | 1,272 |

The differences are network noise. Asking all your questions at once is nearly free.

The LLM's cost jumped (from $0.19 to $1.20 per 1,000) because the JSON state is now in its prompt. JEV reads the same
state for $0.046.

## When LLM-only wins

- One Gemini call with a good schema is a strong baseline: it matched JEV on every label except one urgency.
- If you need a sentence of reasoning per label, the LLM can give it in the same call; JEV can't.

## Break it

**Send everything.** Replace `"order"` with *all* of the customer's orders, plus the product catalogue, and run q11
(Neha Kulkarni has 9 orders).

On 2026-10-08 the state grew from ~820 to ~3,460 tokens (cost × 4), and JEV's team answer for q11 moved from
**account** to **shipping** — the orders crowded out the "account" half of the message. Latency barely changed. Other
messages held up, but TypeSafe documents large irrelevant state as a known weak spot: **send only what the decision
needs.** Filtering state is code's job.

**Shorten a question.** Our first version of this step trimmed step 01's urgency criteria to *"Money taken wrongly, a
deadline today or tomorrow, or can't do something urgent." / "Can wait a day or two."* It looked the same. Over all
24 messages (step 10) it got urgency right **17** times; step 01's full wording got **20**, with the misses all
landing near 0.5. Once you've tested a question's wording, reuse it exactly.

## Recap

- Ask all your questions in **one** request — it costs about the same time as one question.
- Pass JSON state with clear names; include the records a decision needs.
- Keep state focused: irrelevant data costs tokens and can pull answers off course.

## Learn more

- [Parallel questions cookbook (13 questions: 10× faster, 12× cheaper)](https://docs.typesafe.ai/cookbooks/parallel_questions.md)
- [State](https://docs.typesafe.ai/concepts/state)
- [jev-1.13 jaggedness: large irrelevant state](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)

Next: **[Step 05 · Confidence — reply, review, or hand over?](../step05_confidence/)**
