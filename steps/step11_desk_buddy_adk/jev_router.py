# Step 11 — The JEV front desk as an ADK custom agent: JEV guards and triages, then code picks the handler.
# Compare with: coordinator.py (an LlmAgent front desk that routes by LLM "transfer") and ../step10_desk_buddy/jev.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
# Handlers: code, a person, or a specialist agent — whose reply JEV checks before it counts as sent.
import asyncio
import json

import questions
import sub_agents
import tools
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.genai import types

import kit

jev = kit.jev_client()
RULES = ("asks_for_person", "refund_overdue")  # exact policy rules, already checked by code in tools.records()


def _say(ctx, author, text, **state):
    """An ADK event: a reply to the customer, plus anything to remember in the session state."""
    content = types.Content(role="model", parts=[types.Part(text=text)])
    return Event(
        invocation_id=ctx.invocation_id, author=author, content=content, actions=EventActions(state_delta=state)
    )


class JevRouter(BaseAgent):
    """NEW: a custom agent (no LLM) that makes every routing decision with one JEV call."""

    async def _run_async_impl(self, ctx):
        message = ctx.user_content.parts[0].text
        records = json.loads(ctx.session.state["records"])
        state = {"message": message, "customer": records["customer"], "order": records["order"]}

        # 1. Guard + triage — eight JEV questions, one call (JEV's client is synchronous, so run it in a thread)
        everything = {**questions.GUARDS, **questions.TRIAGE}
        answers = (await asyncio.to_thread(jev.system_one, state=state, questions=everything)).answers
        unsafe = 1.0 if tools.has_card_number(message) else max(answers[n].noul for n in questions.GUARDS)
        triage = {
            "unsafe": unsafe,
            "team": answers["team"].choice,
            "intent": answers["intent"].choice,
            "urgent": answers["urgent"].noul,
            "frustration": round(answers["frustration"].score),
            "needs_human": 1.0 if any(records["checks"].get(r) for r in RULES) else answers["needs_human"].noul,
        }
        yield Event(
            invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={"triage": triage})
        )

        # 2. Route — code decides, from JEV's answers
        if unsafe >= 0.5:
            yield _say(ctx, self.name, tools.BLOCKED, handled_by="blocked (no LLM)")
            return
        if triage["needs_human"] >= 0.5:
            async for event in self.find_sub_agent("human_handoff").run_async(ctx):  # NEW: hand over to a sub-agent
                yield event
            return
        if triage["intent"] == "order_status":
            yield _say(ctx, self.name, tools.order_status(records["order"]), handled_by="code")
            return

        # 3. The team's specialist (an LlmAgent) writes the reply
        specialist = self.find_sub_agent(f"{triage['team']}_agent")
        draft = ""
        async for event in specialist.run_async(ctx):
            if event.content and event.content.parts:
                draft = "".join(part.text or "" for part in event.content.parts) or draft
            yield event

        # 4. JEV checks the draft before it counts as sent
        check_state = {"customer_message": message, "draft_reply": draft, "policy": kit.data.policy(), **records}
        checks = (await asyncio.to_thread(jev.system_one, state=check_state, questions=questions.CHECKS)).answers
        passed = all(answer.noul >= 0.5 for answer in checks.values())
        handled_by = f"{specialist.name}, checked by JEV" if passed else "human review (draft failed the check)"
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            actions=EventActions(state_delta={"handled_by": handled_by}),
        )


desk_buddy = JevRouter(
    name="desk_buddy",
    description="Pebble Store support: JEV routes every message; specialists write the replies.",
    sub_agents=[*sub_agents.make_specialists(), sub_agents.make_human_handoff()],
)
