"""`adk web` entry point for the JEV-routed Desk Buddy (see ../web_setup.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import web_setup  # noqa: E402
from jev_router import desk_buddy  # noqa: E402

desk_buddy.before_agent_callback = web_setup.load_demo_records
root_agent = desk_buddy
