# Step 11 · Desk Buddy in Google ADK — JEV router vs LLM coordinator

The full Desk Buddy again, rebuilt as **Google ADK agents**. If you did the
[ADK course](https://github.com/ease-my-work/adk-step-by-step), you know the standard multi-agent pattern: a
**coordinator `LlmAgent`** reads each message and *transfers* it to a sub-agent. That routing decision is an LLM
call. Here we keep everything else identical and swap only the front desk:

```
LLM-only (coordinator.py)                       JEV (jev_router.py)
────────────────────────                        ───────────────────
LlmAgent "coordinator"                          JevRouter — a custom BaseAgent, no LLM
  │ Gemini decides: transfer_to_agent(...)        │ 1 JEV call: 3 guards + 5 triage questions
  │                                               │ + code rules, then plain `if`s decide
  ├─▶ billing_agent    ┐                          ├─ unsafe          → fixed reply (no LLM)
  ├─▶ shipping_agent   │ the SAME specialist      ├─ needs a person  → human_handoff
  ├─▶ technical_agent  │ LlmAgents on both        ├─ order status    → code
  ├─▶ account_agent    │ sides (sub_agents.py)    ├─▶ <team>_agent writes the reply
  ├─▶ other_agent      ┘                          └─ JEV checks the reply before it counts as sent
  ├─▶ human_handoff (no LLM)
  └─▶ safety_block  (no LLM)
```

```bash
python steps/step11_desk_buddy_adk/run.py
adk web steps/step11_desk_buddy_adk/adk_web       # chat with both in ADK's dev UI (as demo customer Asha)
```

## What changed

| File | What it holds |
|---|---|
| `sub_agents.py` | Five specialist `LlmAgent`s (one per team) + `HumanHandoff` and `SafetyBlock` custom agents with no LLM. Built by factory functions — in ADK an agent can only have one parent |
| `jev_router.py` | **New:** `JevRouter(BaseAgent)` — the JEV front desk |
| `coordinator.py` | The standard ADK `LlmAgent` coordinator with `sub_agents=[...]` |
| `tools.py` | Plain code: the records each agent sees (with dates and charges already checked), the order-status reply |
| `questions.py` | The JEV questions from step 10 |
| `jev.py` / `llm_only.py` | Run one message through each version with `kit.run_agent(...)` |
| `adk_web/` | Entry points for `adk web` |

## Why

In ADK, routing by transfer is convenient: describe your sub-agents and the coordinator LLM picks one. But every
message then pays for an LLM call **just to decide where it goes** — before anyone starts answering — and that
decision has no probability you can threshold. JEV makes the same decision as a typed answer, and the custom agent
pattern lets you drop it straight into an ADK app.

## Key concepts (ADK)

- **Custom agent** — subclass `BaseAgent` and write `_run_async_impl(self, ctx)`. Yield `Event`s; no LLM required.
- **Delegating** — `self.find_sub_agent("billing_agent").run_async(ctx)` runs a sub-agent inside your own agent.
- **Session state** — `EventActions(state_delta={"triage": ...})` records decisions; `{records}` in an instruction is
  filled from state.
- **Same specialists, different front desk** — the fair comparison changes one thing only.

## Key code

```python
class JevRouter(BaseAgent):
    async def _run_async_impl(self, ctx):
        answers = (await asyncio.to_thread(jev.system_one, state=state, questions=everything)).answers
        ...
        if triage["needs_human"] >= 0.5:
            async for event in self.find_sub_agent("human_handoff").run_async(ctx):
                yield event
            return
        specialist = self.find_sub_agent(f"{triage['team']}_agent")
        async for event in specialist.run_async(ctx):
            yield event
```

## Run it

```bash
python steps/step11_desk_buddy_adk/run.py
python steps/step11_desk_buddy_adk/run.py --all
python steps/step11_desk_buddy_adk/run.py --replay
```

## JEV vs LLM-only

Measured on 2026-10-08 over all 24 messages. JEV `typesafe/jev-1.13-20260917` via OpenRouter; Gemini
`gemini-3.5-flash` (minimal thinking) for the coordinator and every specialist; ADK 2.11.

| | JEV router | ADK LLM coordinator |
|---|---|---|
| Routing correct (team / person / unsafe) | 24/24 | 24/24 |
| **Time to the routing decision**, p50 | **616 ms** | 2,377 ms |
| Full reply time p50 / p95 | **3,828 ms** / 4,598 ms | 5,065 ms / 6,262 ms |
| Gemini calls per message | **0.58** | 1.75 |
| Cost per 1,000 messages | **$1.47** | $4.06 |
| Replies checked before sending | every specialist reply | none |

Both front desks routed every message correctly. The difference is what routing costs: the coordinator spends a
full Gemini call (~2.4 s, with ADK's long multi-agent prompt) deciding where to send each message, then the specialist
makes another. JEV decides in ~0.6 s, and 10 of 24 messages never reach an LLM at all (code, a person, or blocked).

JEV's router also checked one specialist draft and held it: for q15 the draft claimed *"our technical team is
actively…"* — nothing in the records says so.

## When LLM-only wins

- **Less code.** The coordinator is one `LlmAgent` with a paragraph of instructions; ADK handles the transfers.
  The JEV router is ~60 lines you own.
- **Flexible conversations.** A coordinator can ask a follow-up question or move a conversation between agents
  over many turns. This router makes one decision per message.

## Break it

**Give the coordinator vaguer agent descriptions.** Delete the team list from the coordinator's instruction and rely
on each specialist's one-line `description`. Routing now depends entirely on how ADK presents those descriptions to
the LLM — run `--all` and compare. The JEV router's team question is unaffected; its options are spelled out in
`questions.py`.

## Recap

- In ADK, routing by transfer is an LLM call per message. A JEV custom agent makes the same decision in a fraction of
  the time and cost.
- Custom `BaseAgent`s can mix JEV, code and `LlmAgent` sub-agents freely.
- Keep the specialists the same, and you can swap the front desk.

## Learn more

- [ADK custom agents](https://google.github.io/adk-docs/agents/custom-agents/)
- [ADK multi-agent systems](https://google.github.io/adk-docs/agents/multi-agents/)
- [TypeSafe intent routing](https://docs.typesafe.ai/patterns/intent-routing.md)

Next: **[Step 12 · Benchmark](../step12_benchmark/)**
