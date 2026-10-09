# Step 12 · Benchmark — every message, both pipelines

The finale: run all 24 messages through the full Desk Buddy (a copy of step 10) and the LLM-only version, and write
down everything — accuracy, speed, cost, who handled what, and whether JEV's confidence can be trusted.

```bash
python steps/step12_benchmark/run.py            # live: runs all 24 messages and writes report.md
python steps/step12_benchmark/run.py --replay   # no API keys: the recorded run (report.md is left as is)
```

**→ The result: [`report.md`](report.md)** (run 2026-10-08).

## What changed

| | |
|---|---|
| **Same** | `jev.py`, `llm_only.py`, `questions.py`, `rules.py`, `replies.py` — copies of step 10 |
| **Changed** | `run.py` calls `kit.run_benchmark(...)` instead of `kit.run_step(...)` |

## What's measured, and why

| Metric | Why it matters |
|---|---|
| **Correct, per label** | Accuracy against the hand-checked gold labels |
| **Invalid outputs** | Answers your code can't use |
| **Time to first decision** | How soon you know *where a message goes* — what a queue or UI needs first |
| **Full reply time** | How long until the customer has an answer |
| **LLM calls per message** | The main driver of cost and latency |
| **Cost per 1,000 messages** | From real token counts and OpenRouter prices |
| **Handled with no person** | How much the assistant actually automates |
| **Unsafe messages kept away from the LLM** | Whether a guard ran *before* the LLM saw the text |
| **Calibration** | When JEV says 0.7, is it right ~70% of the time? Only then is a threshold (step 05) meaningful |

## The headline (2026-10-08)

| | JEV + code + LLM | LLM-only |
|---|---|---|
| Labels correct (6 × 24) | 137/144 | 139/144 |
| Time to first decision p50 | **549 ms** | 1,659 ms |
| Full reply time p50 | 2,545 ms | **1,659 ms** |
| LLM calls per message | **0.58** | 1.00 |
| Cost per 1,000 messages | **$1.38** | $2.97 |
| Unsafe messages the LLM never saw | **3/3** | 0/3 |
| Replies checked before sending | **every LLM reply** | none |

**Calibration.** In the 0.7–1.0 range, JEV's answers were right 100% of the time (55 answers). Between 0.5 and 0.7
it was right ~70% of the time — slightly *better* than it said. Expected calibration error: 0.081. JEV errs towards
under-confidence here, which is the safe direction for a threshold.

## How to read it

- **Accuracy is a draw.** On these 24 messages, a well-prompted Gemini call triages as well as JEV — sometimes a
  little better (urgency), sometimes worse (frustration). If accuracy were the only question, LLM-only would be fine.
- **JEV wins on what surrounds the answer:** it decides 3× sooner, costs half as much, keeps unsafe text away from the
  LLM, sends routine questions to code, checks every LLM reply, and its probabilities are honest enough to threshold.
- **LLM-only wins the full-reply race.** One call beats triage → write → check. If you need the fastest possible
  complete reply and trust the model's output unchecked, one LLM call is hard to beat.
- **The pattern matters more than the model:** JEV decides, code calculates, the LLM writes.

## Break it

**Run it twice.** Run the benchmark again and compare `report.md` with this one. LLM outputs and network latency
change from run to run; on 2026-10-08 two runs of the same pipeline (step 10 and step 12) differed by one or two
labels per side and up to ~70 ms in medians. Never trust a single run of 24 messages to more than a few percent.

## Recap

- Measure the first decision *and* the full reply; measure cost, safety and calibration, not just accuracy.
- Report where the baseline wins.
- Date every number, and name the models.

## Learn more

- [TypeSafe confidence](https://docs.typesafe.ai/confidence)
- [JEV-as-a-Judge (arXiv)](https://arxiv.org/pdf/2609.26550)

That's the course. Back to the [top](../../README.md).
