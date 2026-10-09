# Step 06 · Judge and calculate — JEV reads, code checks

"I was charged twice." "Can I still return it?" "Do I get the late-delivery credit?" Each claim is either **true or
false**, and the answer is in the order record: charges, dates. Desk Buddy now splits the work: **JEV reads what the
customer is claiming; plain code checks whether it's true.**

```bash
python steps/step06_judge_and_calculate/run.py
```

## What changed

| | |
|---|---|
| **Added** | `orders.py` — four plain-Python checks: duplicate charge, return window, late delivery, overdue refund |
| **Changed** | `jev.py` — one `Choice` picks the **claim**; a dict maps each claim to its check |
| **Changed** | `llm_only.py` — Gemini gets the message, the order record, today's date and the rules, and decides itself |
| **New in the UI** | Code steps show up as boxes on the flow chart (`@kit.stage("Check charges")`) |

## Why

JEV is excellent at reading what someone *means*, and TypeSafe documents it as weak at **maths, counting and dates**
(see *Break it*). Code is perfect at those and useless at reading. So give each the job it's good at:

```
message ──▶ JEV: "what are they claiming?" ──▶ code: "is it true?" ──▶ answer
```

## Key concepts

- **Division of labour** — JEV judges meaning; code does arithmetic, dates and lookups.
- **Facts** — answers that only the order record can give (`duplicate_charge`, `return_eligible`, …). The dataset
  stores the true value for each (`facts` in `data/queries.json`), and both sides are graded on them.
- **A claim can be false.** q23 says "Did you charge me twice?" — the record shows one failed attempt and one real
  charge. JEV correctly reads the claim; code correctly says *no*.

## Key code

`jev.py`:

```python
CHECKS = {
    "charged_twice": ("duplicate_charge", orders.find_duplicate_charge),
    "return_item": ("return_eligible", orders.return_eligible),
    ...
}
claim = jev.system_one(state=query.text, questions={"claim": CLAIM}).answers["claim"]
fact, check = CHECKS[claim.choice]
result[fact] = check(kit.data.order(query.order_id))
```

`orders.py`:

```python
@kit.stage("Check return window")
def return_eligible(order):
    return (kit.data.today() - date.fromisoformat(order["delivered_on"])).days <= 30
```

## Run it

```bash
python steps/step06_judge_and_calculate/run.py
python steps/step06_judge_and_calculate/run.py --all
python steps/step06_judge_and_calculate/run.py --replay
```

## Try these messages

| Message | The facts |
|---|---|
| **q02** "debited amount 2 time" | Two UPI charges of ₹1,499, 1 minute apart → **true** |
| **q23** "Did you charge me twice?" | One *reversed* attempt + one charge → **false** |
| **q22** "I bought a mixer on 2 Sep, can I still return it?" | Delivered 4 Sep, today is 8 Oct: 34 days → **false** |
| **q24** "promised for 3 Oct and only came yesterday" | 4 days late → ₹99 credit, **true** |
| **q17** "money is still not back after 10 days" | Refund pending 8 working days (limit 7) → **true**, hand to a human |

## JEV vs LLM-only

Measured on 2026-10-08, `--all` over 7 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter; Gemini
`gemini-3.5-flash` (minimal thinking).

| | JEV + code | LLM-only |
|---|---|---|
| Facts correct | 7/7 | 7/7 |
| Latency p50 / p95 | **604 ms** / 894 ms | 1,370 ms / 1,968 ms |
| Cost per 1,000 messages | **$0.017** | $0.907 |
| Same answer every time? | the checks are code: **yes** | it's a model doing maths: usually |

## When LLM-only wins

- **Gemini did the date maths correctly on all 7**, including q22's 34 days. Modern LLMs are decent at this.
- It needed no code: one prompt with the rules. If the rules change weekly, a prompt is quicker to change than code.

Why we'd still split the work: the code checks are **exact and free** — no model can talk them out of the right
answer — and the LLM's cost per message was 50× higher because the whole order record went into its prompt.

## Break it

**Ask JEV to do the maths.** Replace the code check with a Noul and pass the dates in the state:

```python
Noul(instructions="The order was delivered 30 days ago or less (compare delivered_on with today).")
state = {"today": "2026-10-08", "order": {...}}
```

On 2026-10-08, for q22 (delivered **34** days earlier), JEV said **0.74** — "probably within 30 days". Wrong. It reads
dates as text, not as numbers on a calendar. It handled the charge list fine (q02: 0.96, q23: 0.06), but dates are
exactly the documented weak spot. **Maths, counting and dates go in code.**

## Recap

- JEV reads the claim; code checks it against the record.
- Keep arithmetic, dates and counting out of JEV.
- `@kit.stage("…")` puts a code step on the flow chart, so you can see where the time goes (code: ~0 ms).

## Learn more

- [jev-1.13 jaggedness: maths, dates, counting](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- [Data extraction cascade cookbook](https://docs.typesafe.ai/llms.txt)

Next: **[Step 07 · Guardrails — block unsafe messages](../step07_guardrails/)**
