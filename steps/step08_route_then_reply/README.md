# Step 08 · Route, then reply — the LLM only writes

Desk Buddy now **answers** customers. JEV decides *who* should answer; only the messages that need real writing go to
Gemini:

```
            ┌─ needs a human ──────▶ hand over (fixed text)
message ─▶ JEV ─ "where's my order?" ─▶ code: reply from tracking data
            └─ everything else ────▶ Gemini writes the reply
```

The LLM-only version sends every message to one big Gemini prompt that classifies **and** writes.

```bash
python steps/step08_route_then_reply/run.py
```

## What changed

| | |
|---|---|
| **Added** | `order_status.py` — writes "where is my order?" replies from tracking data, in plain code |
| **Added** | `jev.py` uses **both** clients: JEV to route, Gemini to write |
| **Changed** | Routing is an `if` in your code, based on JEV's answers |
| **New in the UI** | The `reply` panel and who handled it |

## Why

This is the **intent routing** pattern from TypeSafe's docs. Most support messages are routine; an LLM writing every
reply is slow and expensive for "where is my parcel?", which a database lookup answers exactly. And for anything a
human must handle, you don't want an LLM improvising at all. JEV makes the routing decision fast and cheap; the LLM
does only what it's best at — writing.

## Key concepts

- **Intent routing** — classify first, then send each message to the cheapest handler that can do it well.
- **The LLM never decides the route.** Code reads JEV's answers and chooses. The LLM only writes.
- **Three kinds of handler** — deterministic code, a specialist LLM, a human.

## Key code

```python
triage = jev.system_one(state=state, questions=TRIAGE).answers
intent, human = triage["intent"], triage["needs_human"]
if human.noul >= 0.5:
    handled_by, reply = "human", HANDOVER
elif intent.choice == "order_status":
    handled_by, reply = "code", order_status.reply(state["order"])
else:
    handled_by = "Gemini"
    reply = gemini.models.generate_content(model=kit.GEMINI_MODEL, contents=prompt, config=config).text
```

## Run it

```bash
python steps/step08_route_then_reply/run.py
python steps/step08_route_then_reply/run.py --all
python steps/step08_route_then_reply/run.py --replay
```

## JEV vs LLM-only

Measured on 2026-10-08, `--all` over 10 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter; Gemini
`gemini-3.5-flash` (minimal thinking).

| | JEV + code + LLM | LLM-only |
|---|---|---|
| intent correct | 10/10 | 10/10 |
| needs_human correct | 9/10 (missed q12) | 10/10 |
| Handled by code / Gemini / human | 4 / 5 / 1 | 0 / 10 / 0 |
| Latency, order status (q01, q14, q18) | **~0.5 s** | ~1.7 s |
| Latency, Gemini-written replies | ~2.2 s | ~1.6 s |
| Latency p50 / p95, all | 1,445 ms / 2,434 ms | 1,646 ms / 2,249 ms |
| Cost per 1,000 messages | **$1.13** | $2.52 |

## When LLM-only wins

- **When the LLM has to write anyway, one call beats two.** For the five messages Gemini wrote, JEV + LLM took
  ~0.5 s longer (the routing call, then the writing call). Routing pays off on messages that *don't* need an LLM.
- **q12** "I need to talk to someone about my order." JEV gave needs_human only 0.4 and routed it to the order-status
  code; Gemini spotted "talk to someone". A person asking for a person is one of the clearest policy rules — and JEV
  read the message as an order question. Step 10 keeps a JEV check on every LLM reply, but code replies (like this
  one) aren't checked. Consider a plain keyword rule for "speak to a person / human / agent" as well.

## Break it

**Route everything to Gemini.** Delete the `elif intent.choice == "order_status"` branch and run q01, q14 and q18.
Expect them to cost about what the Gemini-written replies above did (~2 s and Gemini tokens each, instead of ~0.5 s
and none) — and to answer from a paraphrase of the tracking record rather than the record itself.

## Recap

- Route first (JEV), then use the cheapest handler that can do the job.
- Code for lookups, the LLM for writing, people for the hard cases.
- Routing saves the most when many messages need no LLM at all.

## Learn more

- [Intent routing pattern](https://docs.typesafe.ai/patterns/intent-routing.md)

Next: **[Step 09 · Check the reply — JEV as judge](../step09_check_the_reply/)**
