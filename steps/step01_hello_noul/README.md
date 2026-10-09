# Step 01 · Noul — is this message urgent?

Desk Buddy's first skill: read a customer message and decide **is this urgent?** Same question, two ways:
JEV answers with a **probability**; an LLM (Gemini) answers with JSON.

```bash
python steps/step01_hello_noul/run.py
```

## What changed

| | |
|---|---|
| **Added** | `jev.py` — one JEV call with one `Noul` question |
| **Added** | `llm_only.py` — the same question to Gemini, with JSON-schema output |
| **Added** | `run.py` — picks a message, runs both, compares them |

## Why

Every support queue needs triage, and "is this urgent?" is the first question. It's a yes/no **decision**, not a
piece of writing. An LLM can answer it, but it writes text that you then parse. JEV is built for exactly this kind of
question: it returns a typed answer with a probability, and never writes text at all.

## Key concepts

- **State** — what JEV looks at. Here it's just the message text; later steps pass JSON (orders, policy).
- **Question** — a named thing to decide. You can send many in one request (step 04).
- **`Noul`** — a yes/no question. The answer `.noul` is the **probability of "yes"** (0 to 1). 0.94 means "94% sure
  it's urgent"; 0.53 means "honestly, a coin flip".
- **Criteria** — optional plain-words descriptions of what "yes" and "no" mean. They matter a lot (see *Break it*).

## Key code

`jev.py`:

```python
URGENT = Noul(
    instructions="The customer needs help today.",
    criteria={
        "true": "Money was taken wrongly, there is a deadline today or tomorrow, or they can't do something urgent.",
        "false": "A question, a request or feedback that can wait a day or two.",
    },
)

response = jev.system_one(state=query.text, questions={"urgent": URGENT})
response.answers["urgent"].noul  # 0.86
```

`llm_only.py` asks Gemini the same thing, with the same definitions, and forces the reply into a JSON schema:

```python
response = gemini.models.generate_content(
    model=kit.GEMINI_MODEL,
    contents=PROMPT.format(message=query.text),
    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=SCHEMA),
)
response.parsed  # {"urgent": true, "confidence": "high"}
```

## Run it

```bash
python steps/step01_hello_noul/run.py                  # pick a message, watch both sides answer
python steps/step01_hello_noul/run.py --query q02      # one message, no picker
python steps/step01_hello_noul/run.py --all            # every message for this step + a summary
python steps/step01_hello_noul/run.py --replay         # no API keys: recorded answers and timings
```

## Try these messages

| Message | Look for |
|---|---|
| **q02** "My order debited amount 2 time…" | Both say urgent. JEV gives P(yes) 0.86 in about a third of the time |
| **q08** "Thanks, the replacement arrived today…" | Says "today", but nothing is urgent. Both get it right |
| **q06** "I forgot my password and the reset email never arrives." | JEV says **0.53** — it's unsure, and says so. See below |
| **q18** "Urgent!! Ordered a birthday gift for tomorrow…" | A real deadline. JEV: 0.91 |

## JEV vs LLM-only

Measured on 2026-10-08 with `--all` over this step's 10 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter;
Gemini `gemini-3.5-flash` (minimal thinking) via the Gemini API. Prices from OpenRouter on the same day.

| | JEV | LLM-only |
|---|---|---|
| Correct (vs gold label) | 9/10 | 10/10 |
| Valid output | 10/10 (typed — can't be invalid) | 10/10 (JSON schema) |
| Latency p50 / p95 | **606 ms / 950 ms** | 1,372 ms / 2,107 ms |
| Cost per 1,000 messages | **$0.014** | $0.192 |
| How sure? | a probability, e.g. 0.86 or 0.53 | "high" on 9 of 10, "medium" once |

JEV went through OpenRouter, which adds a network hop; the direct TypeSafe API should be faster.

## When LLM-only wins

- **Accuracy on this tiny set.** Gemini got q06 right; JEV said 0.53, just over the line. Ten messages is far too
  few to call either side more accurate — step 12 measures that properly.
- **Flexibility.** With an LLM you can ask "why?" in the same call. JEV only decides; it never explains.

But look at *how* they were sure. Gemini said "high" on 9 of 10 messages, q06 included; its one "medium" was the
parcel question q01. A three-word label can't tell you *how* sure. JEV's 0.53 on q06 is an honest "not sure", and
step 05 turns that into a feature: send unsure cases to a human.

## Break it

Delete the `criteria` from `URGENT` in `jev.py`, so the question is just *"The customer needs help today."*, then run
`--all` again.

On 2026-10-08, JEV then marked **4 of the 5 non-urgent messages as urgent** (q01 parcel question: 0.37 → 0.88).
Read literally, "needs help today" is true of almost everyone writing to support. JEV reads questions literally, so
**say what yes and no mean**.

## Recap

- One JEV call = **state** + named **questions** → typed **answers**.
- A `Noul` answers yes/no with a **probability**, not a word to parse.
- Criteria in plain words are part of the question. Without them, JEV reads it literally.

## Learn more

- [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart)
- [Primitives: Noul, Choice, Score](https://docs.typesafe.ai/primitives)
- [jev-1.13 jaggedness: literal reading](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)

Next: **[Step 02 · Choice — which team?](../step02_choice/)**
