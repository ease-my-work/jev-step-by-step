# kit/ — course plumbing (you can skip this folder)

Everything in the lessons under `steps/` is JEV code or LLM code. Everything else lives here, so it
never gets in the way of learning.

| File | What it does |
|---|---|
| `settings.py` | Reads `.env`: models, gateway URL, LLM rate limit |
| `clients.py` | `jev_client()` → a real `TypeSafeClient` pinned to `JEV_MODEL`; `gemini_client()` → a real `google.genai.Client`. Both time every call; Gemini also waits for the free-tier rate limit (never counted as latency). Without a key they still import, so `--replay` works |
| `trace.py` | Records each stage (JEV call, Gemini call, `@kit.stage` code step) for the flow chart |
| `data.py` | Loads `data/`: queries, orders, policy |
| `compare.py` | Turns a lesson's return value into answers, checks them against gold labels, sums time / tokens / cost |
| `prices.py` | Per-token prices (with source and date) for the cost column |
| `replay.py` | `--record` saves answers + timings to `fixtures/`; `--replay` plays them back with no API keys |
| `ui.py` | Query picker, live flow chart, probability bars, comparison panel, `--all` summary |
| `runner.py` | `kit.run_step(...)`: flags, threads, live view, replay, `--all`, `--json` |
| `cli.py` | The flags every `run.py` accepts |
| `adk.py` | `kit.run_agent(...)`: runs a Google ADK agent for one message; a plugin times each Gemini call and applies the rate limit (step 11) |
| `benchmark.py` | `kit.run_benchmark(...)`: all messages, both pipelines, metrics and calibration → `report.md` (step 12) |

The clients are the real SDK objects, so a lesson's `client.system_one(...)` or
`gemini.models.generate_content(...)` is exactly what the official docs show.

## What a lesson returns

`run(query)` returns a dict. The UI understands three kinds of value:

| Value | Example | Shown as |
|---|---|---|
| JEV answer object | `response.answers["team"]` | decision + probability bars |
| a probability for a yes/no label | `{"urgent": 0.94}` | bar, decided at 0.5 |
| a plain value | `{"urgent": True}` | the value |

Keys named like a gold label (`team`, `urgent`, `frustration`, `intent`, `needs_human`, `unsafe`), a code fact
(`duplicate_charge`, `return_eligible`, …) or a draft check (`answers_question`, `on_policy`) are checked against
`data/queries.json`. `confidence` is shown as the LLM's self-reported confidence; `reply` and `handled_by` are shown
under the answers.
