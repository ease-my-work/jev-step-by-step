# Step 02 · Choice — which team?

Desk Buddy can now **route** a message: billing, shipping, technical, account, or other. JEV picks one option from
your list and gives a probability for every option. The LLM picks one too, restricted by a JSON schema.

```bash
python steps/step02_choice/run.py
```

## What changed

| | |
|---|---|
| **Changed** | `jev.py` — a `Choice` question instead of a `Noul` |
| **Changed** | `llm_only.py` — the schema's `"enum"` restricts Gemini to the same five teams |

```bash
git diff --no-index steps/step01_hello_noul/jev.py steps/step02_choice/jev.py
```

## Why

Urgency was yes/no. Routing has **several** possible answers. With an LLM, the risk is an answer that isn't one of
your teams ("Payments Team", "Billing Dept."), which your code then can't route. JEV can't do that: it only scores the
options you gave it.

## Key concepts

- **`Choice`** — pick one option. `criteria` maps each option's key to a plain-words description.
- **`.choice`** — the winning key, always one of yours.
- **`.probabilities`** — one number per option, adding up to 1. You see *how close* the runner-up was.
- **`.confidence`** — how far the top answer is above an even split: `(p_top − 1/n) / (1 − 1/n)`. 0 = a coin toss
  between all options, 1 = certain. Step 05 uses it.

## Key code

```python
TEAM = Choice(
    instructions="Which support team should handle this customer message?",
    criteria={
        "billing": "Payments, charges, refunds and returns.",
        "shipping": "Delivery, tracking, address changes, items damaged in transit.",
        ...
    },
)
team = jev.system_one(state=query.text, questions={"team": TEAM}).answers["team"]
team.choice          # "billing"
team.probabilities   # {"billing": 0.97, "account": 0.01, ...}
```

## Run it

```bash
python steps/step02_choice/run.py                  # pick a message
python steps/step02_choice/run.py --all            # all 10 messages + summary
python steps/step02_choice/run.py --replay         # no API keys needed
```

## Try these messages

| Message | Look for |
|---|---|
| **q02** "My order debited amount 2 time…" | billing, nearly 1.00 |
| **q10** "The thing I ordered isn't what I expected." | Probabilities spread out: billing, shipping and other all plausible. JEV says "other"; Gemini says "billing". Both are accepted answers |
| **q15** "cant login app says error 503…" | technical vs account — a real tie-breaker |

## JEV vs LLM-only

Measured on 2026-10-08, `--all` over this step's 10 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter;
Gemini `gemini-3.5-flash` (minimal thinking).

| | JEV | LLM-only |
|---|---|---|
| Correct team | 10/10 | 10/10 |
| Valid output | 10/10 | 10/10 (thanks to `"enum"`) |
| Latency p50 / p95 | **611 ms** / 1,661 ms | 1,515 ms / 1,724 ms |
| Cost per 1,000 messages | **$0.017** | $0.237 |
| How close was it? | a probability per team | one word: "high" / "medium" / "low" |

JEV's p95 includes one slow call (2.1 s on q05) — network time through OpenRouter, not thinking time.

## When LLM-only wins

- With a schema `"enum"`, Gemini never invented a team either. We also tried it **without** the enum: with the five
  teams listed in the prompt, Gemini still used our exact names on all 10 messages. Modern structured output closes
  most of the "invalid label" gap. The remaining JEV advantages here are speed, cost, and the full probability spread.
  (JEV's guarantee still matters at scale: "can't" beats "didn't, in 10 tries".)

## Break it

**1. Delete the descriptions.** Change `criteria` to the bare team names,
`dict.fromkeys(["billing", "shipping", "technical", "account", "other"])`, and run `--all`.

On 2026-10-08 JEV then sent both *return* requests (q05, q22) to **other**, and the blender voltage question (q07) to
**technical** with 0.99 confidence. "billing" doesn't obviously include returns — until you say so. **The
descriptions are part of the question.**

**2. Shuffle the options.** JEV docs warn that a Choice can lean towards the option listed first. We moved each team
to the top in turn for seven hard messages: the answer **never changed**, but the winning probability moved by up to
0.3 (q11: 0.56 → 0.87). If a decision depends on a probability threshold, check it with the options in a different
order.

## Recap

- `Choice` returns one of **your** keys, plus a probability for every option.
- Option descriptions decide what the options mean.
- Option order can nudge probabilities; check important thresholds with a reorder.

## Learn more

- [Primitives: Choice](https://docs.typesafe.ai/primitives)
- [Confidence](https://docs.typesafe.ai/confidence)
- [jev-1.13 jaggedness: option order](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)

Next: **[Step 03 · Score — how frustrated?](../step03_score/)**
