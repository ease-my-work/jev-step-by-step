"""`adk web` entry point for the LLM-routed Desk Buddy (see ../web_setup.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import web_setup  # noqa: E402
from coordinator import coordinator  # noqa: E402

coordinator.before_agent_callback = web_setup.load_demo_records
root_agent = coordinator
