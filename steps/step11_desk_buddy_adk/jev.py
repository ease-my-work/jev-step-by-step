# Step 11 — Run the JEV-routed ADK Desk Buddy on one message and report what it decided.
# Compare with: llm_only.py (the LLM-routed version) and jev_router.py (where the decisions are made)
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import jev_router
import tools

import kit


def run(query):
    reply, author, state = kit.run_agent(jev_router.desk_buddy, query.text, state={"records": tools.records(query)})
    triage = state["triage"]
    return {**triage, "handled_by": state.get("handled_by", author), "reply": reply}
