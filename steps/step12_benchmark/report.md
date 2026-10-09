# Desk Buddy benchmark

- **Run:** 2026-10-08 23:51
- **Messages:** 24 (all of `data/queries.json`)
- **JEV + code + LLM:** gemini-3.5-flash, typesafe/jev-1.13-20260917
- **LLM-only:** gemini-3.5-flash
- **JEV endpoint:** https://openrouter.ai/api
- **Gemini thinking:** minimal
- **Prices:** OpenRouter, checked 2026-10-08

## Results

| | JEV + code + LLM | LLM-only |
|---|---|---|
| Correct · team | 24/24 (100%) | 24/24 (100%) |
| Correct · urgent | 20/24 (83%) | 22/24 (92%) |
| Correct · frustration | 23/24 (96%) | 21/24 (88%) |
| Correct · intent | 23/24 (96%) | 24/24 (100%) |
| Correct · needs_human | 24/24 (100%) | 24/24 (100%) |
| Correct · unsafe | 24/24 (100%) | 24/24 (100%) |
| Invalid outputs | 0 | 0 |
| Time to first decision p50 / p95 | 549 ms / 1,071 ms | 1,659 ms / 2,056 ms |
| Full reply time p50 / p95 | 2,545 ms / 3,565 ms | 1,659 ms / 2,056 ms |
| LLM calls per message (avg) | 0.58 | 1.00 |
| Cost per 1,000 messages | $1.38 | $2.97 |
| Handled with no person (code or LLM reply sent) | 16/24 (67%) | 18/24 (75%) |
| Unsafe messages kept away from the LLM | 3/3 (100%) | 0/3 (0%) |

## Who handled each message

| | JEV + code + LLM | LLM-only |
|---|---|---|
| code (no LLM) | 4 | 0 |
| LLM reply sent | 12 | 18 |
| LLM draft held for review | 2 | 0 |
| handed to a person | 3 | 3 |
| blocked as unsafe | 3 | 3 |

## Does JEV's confidence mean what it says?

JEV's own probabilities for `urgent`, `team` and `intent` (rule overrides excluded), grouped by how sure
it was. Well calibrated = the *right* column matches the *said* column.

| JEV said | answers | right |
|---|---|---|
| 0.5–0.6 (avg 0.54) | 9 | 67% |
| 0.6–0.7 (avg 0.66) | 8 | 75% |
| 0.7–0.8 (avg 0.74) | 9 | 100% |
| 0.8–0.9 (avg 0.84) | 7 | 100% |
| 0.9–1.0 (avg 0.99) | 39 | 100% |

Expected calibration error: **0.081** (0 = perfect).
The LLM-only pipeline gives no probabilities, so there is nothing to calibrate.

## Every message

| Message | JEV + code + LLM | LLM-only |
|---|---|---|
| q01 clear | ✔ · code · 471 ms | ✔ · llm · 1,666 ms |
| q02 clear | ✔ · llm · 3,337 ms | ✔ · llm · 1,681 ms |
| q03 clear | ✘ frustration · llm · 3,580 ms | ✘ frustration · llm · 1,612 ms |
| q04 clear | ✔ · llm · 4,216 ms | ✔ · llm · 1,609 ms |
| q05 clear | ✔ · llm · 2,935 ms | ✔ · llm · 1,818 ms |
| q06 clear | ✘ urgent · review · 2,559 ms | ✘ urgent · llm · 2,079 ms |
| q07 clear | ✔ · llm · 2,531 ms | ✔ · llm · 1,719 ms |
| q08 clear | ✔ · llm · 2,785 ms | ✔ · llm · 3,757 ms |
| q09 ambiguous | ✘ urgent · llm · 2,517 ms | ✔ · llm · 1,631 ms |
| q10 ambiguous | ✔ · llm · 2,827 ms | ✘ frustration · llm · 1,619 ms |
| q11 ambiguous | ✔ · code · 466 ms | ✔ · llm · 1,652 ms |
| q12 ambiguous | ✔ · human · 481 ms | ✔ · human · 1,479 ms |
| q13 typos | ✔ · llm · 3,065 ms | ✔ · llm · 1,630 ms |
| q14 typos | ✔ · code · 493 ms | ✔ · llm · 1,754 ms |
| q15 typos | ✔ · review · 3,481 ms | ✔ · llm · 1,671 ms |
| q16 angry | ✔ · human · 580 ms | ✔ · human · 1,623 ms |
| q17 angry | ✔ · human · 536 ms | ✔ · human · 1,924 ms |
| q18 angry | ✔ · code · 804 ms | ✔ · llm · 1,767 ms |
| q19 unsafe | ✔ · blocked · 637 ms | ✔ · blocked · 1,585 ms |
| q20 unsafe | ✘ intent, urgent · blocked · 1,119 ms | ✔ · blocked · 1,791 ms |
| q21 unsafe | ✔ · blocked · 821 ms | ✘ urgent · blocked · 1,626 ms |
| q22 needs_code | ✔ · llm · 3,194 ms | ✔ · llm · 1,638 ms |
| q23 needs_code | ✘ urgent · llm · 2,741 ms | ✔ · llm · 1,642 ms |
| q24 needs_code | ✔ · llm · 2,696 ms | ✘ frustration · llm · 1,892 ms |

## Read this before quoting the numbers

- 24 messages is a teaching set, not a benchmark suite: one message is 4 percentage points.
- Latency includes the network. JEV ran through the endpoint above; a gateway adds a hop.
- Gold labels were written by hand and reviewed where both models disagreed (see `data/README.md`).
- LLM output varies from run to run; run it yourself with `--all`, or `--replay` to see these exact runs.
