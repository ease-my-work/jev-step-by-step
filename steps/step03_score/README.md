# Step 03 · Score — how frustrated?

Desk Buddy can now rate **how frustrated** a customer is: calm (0), annoyed (1) or angry (2). JEV answers an ordered
scale with a probability for each level; Gemini answers with one integer.

```bash
python steps/step03_score/run.py
```

## What changed

| | |
|---|---|
| **Changed** | `jev.py` — a `Score` question (ordered levels) instead of a `Choice` |
| **Changed** | `llm_only.py` — an integer 0–2 in the schema |

## Why

Some answers have an **order**: "annoyed" sits between "calm" and "angry". A `Choice` treats options as unrelated;
a `Score` knows level 2 is above level 1. That gives you an in-between number (1.7 = "between annoyed and angry,
closer to angry") and a sensible confidence: probability on a *neighbouring* level costs less confidence than
probability on a far-away one.

## Key concepts

- **`Score`** — `criteria` is a **list**, lowest level first. Level numbers are positions in that list: 0, 1, 2.
- **`.score`** — the expected level, e.g. `1.74`. Round it for a decision, keep it for sorting.
- **`.probabilities`** — one per level: `{0: 0.01, 1: 0.24, 2: 0.75}`.
- **`.legend`** — maps each level number back to your text.

## Key code

```python
FRUSTRATION = Score(
    instructions="How frustrated is the customer?",
    criteria=[
        "calm: no sign of annoyance",
        "annoyed: unhappy or impatient, but polite",
        "angry: shouting, insults, threats, or says they've written many times",
    ],
)
frustration = jev.system_one(state=query.text, questions={"frustration": FRUSTRATION}).answers["frustration"]
frustration.score   # 1.74
```

Gemini's side asks for `{"type": "integer", "minimum": 0, "maximum": 2}`. (Its schema doesn't allow numbers in
`"enum"` — a small gotcha we hit while building this.)

## Run it

```bash
python steps/step03_score/run.py
python steps/step03_score/run.py --all
python steps/step03_score/run.py --replay
```

## Try these messages

| Message | Look for |
|---|---|
| **q13** "paymnt cut 2 times pls refund fast!!!" | Annoyed or angry? JEV: 1.74 — leaning angry, and it tells you so |
| **q16** "THIRD time I'm writing…" | Clearly 2 |
| **q08** "Thanks, the replacement arrived today…" | Clearly 0 |

## JEV vs LLM-only

Measured on 2026-10-08, `--all` over 9 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter; Gemini
`gemini-3.5-flash` (minimal thinking).

| | JEV | LLM-only |
|---|---|---|
| Correct level | 9/9 | 9/9 |
| Latency p50 / p95 | **798 ms** / 1,314 ms | 1,307 ms / 1,890 ms |
| Cost per 1,000 messages | **$0.014** | $0.217 |
| Answer | a level **and** where it sits (1.74) | a level (1 or 2) |

**Same message, five times** (q13, on 2026-10-08):

| | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| JEV `.score` | 1.74 | 1.74 | 1.72 | 1.74 | 1.73 |
| Gemini level (confidence) | 1 (high) | 1 (high) | 1 (high) | 1 (high) | **2** (high) |

JEV's answer barely moves. Gemini changed its answer once — and said "high" confidence both times.

## When LLM-only wins

- Both got every message right. For a three-level scale on short messages, accuracy is not the difference.
- If you only need the rounded level, Gemini's integer is simpler to read.

## Break it

**Shuffle the levels.** Put the criteria in the order `angry, calm, annoyed` and run q16 ("THIRD time I'm
writing…").

On 2026-10-08 JEV still picked the right *description* — "angry" — but `.score` came back **0.00**, because "angry" is
now first in the list. Any code like `if frustration.score >= 2: escalate()` silently stops working. A `Score` is an
ordered scale: **lowest level first, always**.

## Recap

- `Score` = ordered levels, lowest first. Level number = position in your list.
- `.score` is an in-between number; `.probabilities` shows the spread.
- Repeated runs: JEV's numbers are steady; an LLM's single integer can flip.

## Learn more

- [Primitives: Score](https://docs.typesafe.ai/primitives)
- [Confidence (how Score confidence uses distance between levels)](https://docs.typesafe.ai/confidence)

Next: **[Step 04 · Many questions — five answers, one call](../step04_many_questions/)**
