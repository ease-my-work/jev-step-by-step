"""Reads `.env` once and exposes the course settings (models, limits)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class SetupError(Exception):
    """Something is missing from `.env`. The message says how to fix it."""


def env(name: str, default: str = "") -> str:
    """Read a stripped environment variable; empty values fall back to `default`."""
    return os.environ.get(name, "").strip() or default


def _float_env(name: str, default: float) -> float:
    raw = env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise SetupError(f"{name} must be a number, got {raw!r}. Fix it in .env.") from None


JEV_MODEL = env("JEV_MODEL", "jev-1.13")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_THINKING_LEVEL = env("GEMINI_THINKING_LEVEL", "minimal")
LLM_REQUESTS_PER_MINUTE = _float_env("LLM_REQUESTS_PER_MINUTE", 10)
