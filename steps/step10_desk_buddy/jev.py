# Step 10 — The full Desk Buddy: guard → triage → route → reply → check → send or escalate.
# Compare with: llm_only.py (one big prompt does everything), questions.py, rules.py and replies.py
# kit/ is plumbing (picker, timing, replay) — you can ignore it.
import questions
import replies
import rules

import kit

jev = kit.jev_client()


def run(query):
    order = kit.data.order(query.order_id)
    state = {"message": query.text, "customer": kit.data.customer(query.customer_id), "order": order}

    # 1. Guard + triage: eight questions, ONE JEV call (steps 04 and 07)
    first = jev.system_one(state=state, questions={**questions.GUARDS, **questions.TRIAGE}).answers
    rule = rules.check(query.text, order)  # exact policy rules in code, next to JEV's judgement (step 06)
    unsafe = 1.0 if rule["card_number"] else max(first[name].noul for name in questions.GUARDS)
    human = 1.0 if rule["asks_for_person"] or rule["refund_overdue"] else first["needs_human"].noul
    result = {
        "unsafe": unsafe,
        "team": first["team"],
        "intent": first["intent"],
        "urgent": first["urgent"].noul,
        "frustration": first["frustration"],
        "needs_human": human,
    }

    # 2. Route — decided by code, from JEV's answers (step 08)
    if unsafe >= 0.5:
        return {**result, "handled_by": "blocked (no LLM)", "reply": replies.BLOCKED}
    if result["needs_human"] >= 0.5:
        return {**result, "handled_by": "human", "reply": replies.HANDOVER}
    if first["intent"].choice == "order_status":
        return {**result, "handled_by": "code", "reply": replies.order_status(order)}

    # 3. Reply — only now does the LLM run
    records = {**state, "products": kit.data.store()["products"]}
    draft = replies.write(query.text, records)

    # 4. Check the draft before sending (step 09)
    check_state = {"customer_message": query.text, "draft_reply": draft, "policy": kit.data.policy(), **records}
    checks = jev.system_one(state=check_state, questions=questions.CHECKS).answers
    if all(answer.noul >= 0.5 for answer in checks.values()):
        return {**result, "handled_by": "Gemini, checked by JEV", "reply": draft}
    return {**result, "handled_by": "human review (draft failed the check)", "reply": draft}
