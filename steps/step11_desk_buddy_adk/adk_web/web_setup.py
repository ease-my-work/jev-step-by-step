"""Shared by the two `adk web` entry points: makes the step folder importable and loads a demo customer.

    adk web steps/step11_desk_buddy_adk/adk_web

In the dev UI you chat as Asha Rao (customer C-1042, order ORD-7731 — the double charge from q02).
"""

import sys
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parents[1]
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))

import tools  # noqa: E402

from kit import data  # noqa: E402

DEMO_CUSTOMER, DEMO_ORDER = "C-1042", "ORD-7731"


def load_demo_records(callback_context):
    """before_agent_callback: put the demo customer's records in the session state, as run.py does."""
    parts = callback_context.user_content.parts if callback_context.user_content else []
    text = "".join(p.text or "" for p in parts)
    query = data.Query("web", "custom", text, DEMO_CUSTOMER, DEMO_ORDER, {}, (), "")
    callback_context.state["records"] = tools.records(query)
    return None
