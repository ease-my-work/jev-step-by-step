"""Course plumbing. You never need to read this folder to follow the lessons — see kit/README.md.

Lesson code uses only:
    kit.jev_client()      a real TypeSafeClient, pinned to JEV_MODEL
    kit.gemini_client()   a real google.genai.Client
    kit.GEMINI_MODEL      the pinned Gemini model name
    kit.GEMINI_THINKING   the thinking setting for fair LLM-only calls
    kit.data              the queries, orders and policy in data/
    @kit.stage("…")       show a plain-code step as a box on the flow chart
    kit.run_step(...)     the CLI: picker, live flow chart, comparison (used by every run.py)
    kit.run_agent(...)    run a Google ADK agent for one message (step 11)
    kit.run_benchmark(...) run every message through both pipelines and write report.md (step 12)
"""

from kit import data
from kit.benchmark import run_benchmark
from kit.clients import GEMINI_THINKING, gemini_client, jev_client
from kit.runner import run_step
from kit.settings import GEMINI_MODEL, JEV_MODEL, SetupError
from kit.trace import Stage, recording, stage

__all__ = [
    "GEMINI_MODEL",
    "GEMINI_THINKING",
    "JEV_MODEL",
    "SetupError",
    "Stage",
    "data",
    "gemini_client",
    "jev_client",
    "recording",
    "run_agent",
    "run_benchmark",
    "run_step",
    "stage",
]


def __getattr__(name: str):
    if name == "run_agent":  # imported on first use: Google ADK is slow to import and only step 11 needs it
        from kit.adk import run_agent

        return run_agent
    raise AttributeError(f"module 'kit' has no attribute {name!r}")
