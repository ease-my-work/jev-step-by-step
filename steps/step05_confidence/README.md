# Step 05 · Confidence — reply, review, or hand over?

Desk Buddy now knows **when it isn't sure**. Every routing decision gets a route: **auto** (reply automatically),
**review** (a person checks first) or **human** (a person takes over). JEV's confidence number drives it; the LLM
version uses Gemini's own "high / medium / low".

```bash
python steps/step05_confidence/run.py
```

## What changed

| | |
|---|---|
| **Added** | `AUTO` and `REVIEW` thresholds and a `route()` function — in your code |
| **Added** | `route` in the result of both versions |
| **Changed** | `llm_only.py` asks Gemini to be honest about how sure it is, and maps its label to a route |

## Why

Every classifier is sometimes wrong. The question is whether you can **tell** which answers to trust. If you can,
you automate the easy 80% and send the rest to people. That only works if "sure" means something.

## Key concepts

- **`.confidence`** on a Choice: `(p_top − 1/n) / (1 − 1/n)`. 0 = all options equally likely; 1 = certain.
- **For a Noul**, the probability itself is the confidence signal: near 0.5 = unsure. (`|2p − 1|` puts it on the
  same 0–1 scale.)
- **Thresholds are yours**, set by risk. Wrongly auto-replying costs more than an unneeded review, so `AUTO` is high.
- **Self-reported confidence** — an LLM's "high" is more generated text. It isn't derived from probabilities, and it
  only has three steps.

## Key code

```python
AUTO, REVIEW = 0.8, 0.4

def route(confidence):
    if confidence >= AUTO:
        return "auto"
    if confidence >= REVIEW:
        return "review"
    return "human"

team = jev.system_one(state=query.text, questions={"team": TEAM}).answers["team"]
return {"team": team, "route": route(team.confidence)}
```

## Run it

```bash
python steps/step05_confidence/run.py
python steps/step05_confidence/run.py --all
python steps/step05_confidence/run.py --replay
```

## What happened (2026-10-08)

| Message | Kind | JEV team · confidence → route | Gemini team · says → route |
|---|---|---|---|
| q02 "debited amount 2 time" | clear | billing · 1.00 → auto | billing · high → auto |
| q07 blender on 110V? | clear | other · 0.96 → auto | other · high → auto |
| q09 "money back or a new one" | ambiguous | billing · **1.00 → auto** | billing · medium → review |
| q10 "isn't what I expected" | ambiguous | other · 0.53 → review | billing · medium → review |
| q11 "my account and my last order" | ambiguous | account · 0.63 → review | account · medium → review |
| q12 "talk to someone about my order" | ambiguous | other · 0.68 → review | other · low → human |
| q15 "cant login… error 503" | typos | technical · 0.67 → review | technical · medium → review |

Both got every team right (7/7). JEV p50 609 ms vs Gemini 1,354 ms; $0.017 vs $0.274 per 1,000 messages.

## When LLM-only wins

- **q09.** JEV is 1.00 sure the *team* is billing — and for the team question, it's right. But the message is still
  ambiguous ("money back **or** a new one"). Confidence answers *the question you asked*, nothing more. Gemini, told to
  be honest, said "medium" here. If "is this message ambiguous?" matters, ask JEV that as its own question.
- With an explicit "be honest" instruction, Gemini's three labels were sensible on this set.

What JEV gives you that three labels can't: a **number you can tune**. Moving `AUTO` from 0.8 to 0.7 changes exactly
which messages get automated, and step 12 checks that the numbers mean what they say.

## Break it

**Trust a threshold you never checked.** Set `AUTO = 0.5` and run `--all`: q10 (0.53) is now answered automatically
by a bot, even though JEV's own probabilities split it between other (0.63) and shipping (0.20). A threshold is a
business decision. Pick it by looking at real answers like the table above.

## Recap

- Confidence turns "an answer" into "an answer you know how far to trust".
- JEV's confidence comes from its probabilities; an LLM's "high" is just more text.
- Confidence covers the question you asked. Ask separately about anything else you need to know.

## Learn more

- [Confidence](https://docs.typesafe.ai/confidence)
- [Pattern: classification using confidence](https://docs.typesafe.ai/llms.txt)

Next: **[Step 06 · Judge and calculate](../step06_judge_and_calculate/)**
