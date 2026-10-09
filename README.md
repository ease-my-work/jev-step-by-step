# JEV step by step

Learn **JEV** — TypeSafe AI's "System One" decision model — by building a customer-support assistant, **Desk Buddy**,
one small step at a time. Every step runs the **same customer message** through two versions and shows them side by
side in your terminal:

- an **LLM-only** version (Gemini, with JSON-schema output — a fair, modern baseline), and
- a **JEV** version (JEV alone → JEV + code → JEV + LLM → JEV + LLM inside Google ADK).

You pick a message from a list, watch both pipelines run as a live flow chart, and compare the answers, the
milliseconds and the cost.

```
💬 q02  "My order debited amount 2 time. I want immediate help."

JEV flow   ⏱ 444 ms
┌─────────┐    ┌──────────────────┐    ┌────────┐
│ Message │ ─▶ │ JEV · 1 question │ ─▶ │ Answer │
│ ✔       │    │ ✔ 444 ms         │    │ ✔      │
└─────────┘    └──────────────────┘    └────────┘
  urgent      ██████████████████████████░░░░  0.86 → yes ✔

LLM-only flow   ⏱ 1,389 ms
┌─────────┐    ┌─────────────┐    ┌────────┐
│ Message │ ─▶ │ Gemini call │ ─▶ │ Answer │
│ ✔       │    │ ✔ 1,389 ms  │    │ ✔      │
└─────────┘    └─────────────┘    └────────┘
  {"urgent": true, "confidence": "high"}
💡 Both match the gold label. JEV was 3.1× faster.
```

Modelled on [`ease-my-work/adk-step-by-step`](https://github.com/ease-my-work/adk-step-by-step) — same step-folder
style, same README sections. If you did that course, step 11 rebuilds Desk Buddy in Google ADK.

## JEV in one minute

JEV turns messy input (the **state**) into **typed decisions with probabilities**. It doesn't write text.

| Question type | Asks | Returns | Desk Buddy example |
|---|---|---|---|
| `Noul` | Is this true? | `noul` — probability of yes | "Is this urgent?" → `0.94` |
| `Choice` | Which option? | `choice`, `probabilities`, `confidence` | "Which team?" → `billing` |
| `Score` | Which level on an ordered scale? | `score`, `legend`, `probabilities`, `confidence` | "How frustrated?" → `1.74` |

It can only answer with options **you** gave it, and many questions in one request cost about the same time as one.

```
JEV  = fast System 1  → route, classify, gate, judge          (hundreds of ms)
LLM  = slow System 2  → write replies, reason                 (seconds)
Code = in control     → maths, dates, lookups, exact rules    (microseconds)
```

## The course

| Step | Desk Buddy can now… | You learn | Headline (measured 2026-10-08) |
|---|---|---|---|
| [01](steps/step01_hello_noul/) | tell if a message is urgent | `Noul`, state, criteria | 606 vs 1,372 ms p50; $0.014 vs $0.19 per 1k |
| [02](steps/step02_choice/) | pick the team | `Choice`, probabilities | descriptions decide what options mean |
| [03](steps/step03_score/) | rate frustration 0–2 | `Score`, ordered levels | JEV steady over 5 runs; Gemini flipped once |
| [04](steps/step04_many_questions/) | ask five questions at once | fan-out, JSON state | 1, 5 or 8 questions: ~480 ms either way |
| [05](steps/step05_confidence/) | know when it's unsure | confidence → auto / review / human | a number you can tune vs three words |
| [06](steps/step06_judge_and_calculate/) | check claims against the order | JEV judges, code calculates | JEV says a 34-day-old delivery is "within 30 days" — so dates go in code |
| [07](steps/step07_guardrails/) | block unsafe messages | `Noul` guardrails + code | the regex caught a card number JEV missed |
| [08](steps/step08_route_then_reply/) | answer: code, LLM or human | intent routing | order status by code: 0.5 s, no LLM |
| [09](steps/step09_check_the_reply/) | check a reply before sending | JEV as judge | 10/10 checks; $0.06 vs $2.05 per 1k |
| [10](steps/step10_desk_buddy/) | **the whole flow** | guard → triage → route → reply → check | 139 vs 140 labels; ½ the cost; slower full reply |
| [11](steps/step11_desk_buddy_adk/) | run as Google ADK agents | custom `BaseAgent` router vs `LlmAgent` coordinator | routing decision 616 vs 2,377 ms; $1.47 vs $4.06 per 1k |
| [12](steps/step12_benchmark/) | prove it | accuracy, latency, cost, calibration | [`report.md`](steps/step12_benchmark/report.md) |

### The result

From the [step 12 benchmark](steps/step12_benchmark/report.md), all 24 messages, 2026-10-08:

| | JEV + code + LLM | LLM-only (one Gemini call) |
|---|---|---|
| Labels correct (6 × 24) | 137/144 | 139/144 |
| Time to first decision p50 | **549 ms** | 1,659 ms |
| Full reply time p50 | 2,545 ms | **1,659 ms** |
| Cost per 1,000 messages | **$1.38** | $2.97 |
| Unsafe messages the LLM never saw | **3/3** | 0/3 |
| Replies checked before sending | **all** | none |

Accuracy is a draw; a well-prompted LLM is a strong baseline. JEV's case is everything around the answer: decisions
3× sooner, half the cost, unsafe text kept away from the LLM, routine questions answered by code, every LLM reply
checked, and probabilities honest enough to set thresholds on.

About **2.5 hours** in total. Every step's README has the same sections: *What changed · Why · Key concepts · Key
code · Run it · JEV vs LLM-only · When LLM-only wins · Break it · Recap*.

## Quick start

You need **Python 3.10+**.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
```

**No API keys?** Every step can replay recorded answers and timings:

```bash
python steps/step01_hello_noul/run.py --replay
```

**With keys:** copy `.env.example` to `.env` and fill in

- `TYPESAFE_API_KEY` — from TypeSafe (waitlist), or an OpenRouter key with `TYPESAFE_BASE_URL=https://openrouter.ai/api`
  and `JEV_MODEL=typesafe/jev-1.13`;
- `GEMINI_API_KEY` — free from [AI Studio](https://aistudio.google.com/apikey).

Then check both work, and start:

```bash
python scripts/check_setup.py
python steps/step01_hello_noul/run.py
```

## How a step works — one example

Every step folder has the same four files. Here is step 02, which routes a message to a support team.

**`run.py`** — the whole entry point. It imports the two versions and hands them to `kit`, which does the picker,
the timing, the live flow chart and the comparison:

```python
import jev
import llm_only

import kit

kit.run_step("02 · Choice — which team?", jev=jev.run, llm=llm_only.run)
```

**`jev.py`** — the JEV version. One question, one call:

```python
TEAM = Choice(
    instructions="Which support team should handle this customer message?",
    criteria={
        "billing": "Payments, charges, refunds and returns.",
        "shipping": "Delivery, tracking, address changes, items damaged in transit.",
        ...
    },
)

def run(query):
    response = jev.system_one(state=query.text, questions={"team": TEAM})
    return {"team": response.answers["team"]}
```

**`llm_only.py`** — the same task for Gemini: the same five teams in the prompt, and a JSON schema so the answer
can only be one of them. It returns something like `{"team": "billing", "confidence": "high"}`.

**`README.md`** — the lesson: what changed since the last step, why, the measured results, and a *Break it*
experiment.

### Run it

```bash
python steps/step02_choice/run.py --query q02 --replay
```

(`--query q02` skips the picker; `--replay` uses the recorded answers, so this exact output needs no API keys.)

### What you see

```
───────────────────────────────── Step 02 · Choice — which team? ──────────────────────────────────

💬 q02  "My order debited amount 2 time. I want immediate help."
   Why this one: Clear billing case. Both sides get it right — JEV is faster and gives a
probability with every answer.

JEV flow   ⏱ 464 ms
┌─────────┐    ┌──────────────────┐    ┌────────┐
│ Message │ ─▶ │ JEV · 1 question │ ─▶ │ Answer │
│ ✔       │    │ ✔ 464 ms         │    │ ✔      │
└─────────┘    └──────────────────┘    └────────┘
  team        → billing   confidence 1.00 ✔
    billing         ██████████████████████████  1.00
    shipping        ░░░░░░░░░░░░░░░░░░░░░░░░░░  0.00
    technical       ░░░░░░░░░░░░░░░░░░░░░░░░░░  0.00
    account         ░░░░░░░░░░░░░░░░░░░░░░░░░░  0.00
    other           ░░░░░░░░░░░░░░░░░░░░░░░░░░  0.00

LLM-only flow   ⏱ 1,774 ms
┌─────────┐    ┌─────────────┐    ┌────────┐
│ Message │ ─▶ │ Gemini call │ ─▶ │ Answer │
│ ✔       │    │ ✔ 1,774 ms  │    │ ✔      │
└─────────┘    └─────────────┘    └────────┘
  {"team": "billing", "confidence": "high"}
  team        → billing ✔
┌────────────────┬───────────────────────────────┬─────────────────────────────────┐
│                │ JEV                           │ LLM-only                        │
├────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ Answer         │ team: billing ✔               │ team: billing ✔                 │
│ Output         │ typed — always valid          │ valid output                    │
│ Confidence     │ 1.00 (from probabilities)     │ "high" (self-reported)          │
│ Latency        │ ██████░░░░░░░░░░░░░░░░ 464 ms │ ██████████████████████ 1,774 ms │
│ Tokens         │ 395 in / 52 out               │ 85 in / 12 out / 0 thinking     │
│ Cost / 1k runs │ $0.017                        │ $0.236                          │
│ Model          │ typesafe/jev-1.13-20260917    │ gemini-3.5-flash                │
└────────────────┴───────────────────────────────┴─────────────────────────────────┘
💡 Both match the gold label. JEV was 3.8× faster.
💡 Replayed from a recording made 2026-10-08: timings are the recorded ones.
```

### How to read it

| Part | What it tells you |
|---|---|
| **💬 line** | The customer message (from `data/queries.json`) and why it was picked for this step |
| **Flow chart** | Each box is one stage, with its time. Live runs animate it; `⏱` is the total for that side |
| **Bars under JEV** | JEV's probability for **every** team, not just the winner — you can see how close the runner-up was |
| **JSON under LLM-only** | Exactly what Gemini returned |
| **✔ / ✘** | Whether the answer matches the correct answer stored for that message |
| **Answer** | The decision each side made |
| **Output** | JEV can only answer with your options; the LLM's JSON is checked against the allowed values |
| **Confidence** | JEV's comes from its probabilities; the LLM's is a word it chose to write |
| **Latency** | Time in API calls only. Waiting for Gemini's free-tier rate limit is never counted |
| **Tokens / Cost** | Real token counts × the prices in `kit/prices.py`, per 1,000 runs |
| **💡 lines** | A one-line verdict, plus notes (replay date, rate-limit waits) |

Without `--query`, you first get an arrow-key list of this step's messages (or type your own), and after each run a
menu: run again, pick another, run all, or quit.

## Running a step

```bash
python steps/step02_choice/run.py                 # pick a message from the list
python steps/step02_choice/run.py --query q02     # one message, no picker
python steps/step02_choice/run.py --all           # every message for the step + summary
python steps/step02_choice/run.py --mode jev      # only one side (jev | llm | both)
python steps/step02_choice/run.py --replay        # recorded answers, no API calls
python steps/step02_choice/run.py --all --json    # machine-readable
```

Step 11 can also be opened in ADK's dev UI: `adk web steps/step11_desk_buddy_adk/adk_web`.

## What's where

```
steps/      📚 LEARN HERE — each step: jev.py, llm_only.py, run.py, README.md (only JEV and LLM code)
data/       👀 the 24 customer messages (with correct answers), orders, and the store policy
kit/        🔧 plumbing: picker, flow chart, timing, replay, benchmark — you never need to open it
fixtures/   recorded answers and timings for --replay
scripts/    check_setup.py
tests/      checks the data, the plumbing, and that lessons stay plumbing-free
```

Step files are full copies, so `git diff --no-index steps/step01_hello_noul/jev.py steps/step02_choice/jev.py` shows
exactly what each step adds.

## Fair comparison

- **No straw man.** The LLM side uses JSON-schema output, the same option lists, the same definitions, and minimal
  thinking (the fastest fair setting for short decisions).
- **Same input** on both sides; **same Gemini model** wherever text is written.
- **Measured, not claimed.** Every number comes from a run, with model versions and the date. JEV ran through
  OpenRouter (a gateway hop) unless stated.
- **Where LLM-only wins, the README says so** — and on this dataset it often ties or wins on accuracy.
- **JEV's documented weak spots** (dates and maths, literal reading, adversarial text, large irrelevant state, option
  order) each get a *Break it* experiment.

## Troubleshooting

| Problem | Fix |
|---|---|
| `TYPESAFE_API_KEY is not set` | Add it to `.env`, or add `--replay` |
| `400 … Model ~typesafe/jev-1.13 does not exist` | On OpenRouter use `typesafe/jev-1.13` (no `~`) |
| `400 … invalid_union` from OpenRouter | A `Noul` with only `"false"` criteria — give both `"true"` and `"false"` |
| Gemini `404 … no longer available` | Set `GEMINI_MODEL` in `.env` to a current Flash model |
| `Thinking level MINIMAL is not supported` | Use a model that supports it (e.g. `gemini-3.5-flash`), or `GEMINI_THINKING_LEVEL=default` |
| `--all` pauses between messages | Free-tier Gemini rate limit; raise `LLM_REQUESTS_PER_MINUTE` on a paid key (waiting is never counted as latency) |
| `No recording for qNN` in `--replay` | Only some messages are recorded per step; pick one from the list |
| Picker says "No terminal" | Use `--query qNN` or `--all` when piping output |

## Learn more

- [TypeSafe docs](https://docs.typesafe.ai/introduction/quickstart) ·
  [Primitives](https://docs.typesafe.ai/primitives) · [Confidence](https://docs.typesafe.ai/confidence) ·
  [Intent routing](https://docs.typesafe.ai/patterns/intent-routing.md) ·
  [jev-1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- [Google ADK](https://google.github.io/adk-docs/) · [ADK step by step](https://github.com/ease-my-work/adk-step-by-step)

All customers, orders and messages in `data/` are fictional.

## License

[MIT](LICENSE) © 2026 Vipul Patel
