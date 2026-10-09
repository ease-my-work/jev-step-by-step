# Step 11 — Run the LLM-routed ADK Desk Buddy on one message. The team is whichever specialist it transferred to.
# Compare with: jev.py (the JEV-routed version) and coordinator.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import coordinator
import tools

import kit


def run(query):
    reply, author, state = kit.run_agent(coordinator.coordinator, query.text, state={"records": tools.records(query)})
    result = {"handled_by": author, "reply": reply}
    # Only grade what the transfer tells us. A blocked message says nothing about the team or a person.
    if author == "safety_block":
        return {**result, "unsafe": True}
    result.update(unsafe=False, needs_human=author == "human_handoff")
    if author.endswith("_agent"):
        result["team"] = author.removesuffix("_agent")  # billing_agent → billing
    return result
