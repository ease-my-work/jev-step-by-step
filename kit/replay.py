"""--record saves real answers and timings to fixtures/; --replay plays them back with no API keys."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from kit import data
from kit.compare import SideResult
from kit.settings import ROOT

FIXTURES_DIR = ROOT / "fixtures"


def _path(step: int, query_id: str) -> Path:
    return FIXTURES_DIR / f"step{step:02d}" / f"{query_id}.json"


def recorded_ids(step: int) -> set[str]:
    folder = FIXTURES_DIR / f"step{step:02d}"
    return {p.stem for p in folder.glob("q*.json")} if folder.is_dir() else set()


def save(step: int, query: data.Query, results: dict[str, SideResult], with_draft: bool = False) -> Path:
    """Write (or update) one query's recording. Sides not in `results` keep their earlier recording.

    `with_draft` also stores the draft reply the step checked, so editing the draft makes the recording stale.
    """
    path = _path(step, query.id)
    saved: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    saved.update({"step": step, "query": query.id, "text": query.text})
    if with_draft and query.draft:
        saved["draft"] = query.draft["text"]
    for side, result in results.items():
        if result.error is None:  # never record a failure as the "expected" run
            saved[side] = {**result.to_dict(), "recorded_at": datetime.now().isoformat(timespec="seconds")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(saved, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


class NotRecorded(Exception):
    pass


def load(step: int, query: data.Query) -> tuple[dict[str, SideResult], dict[str, str]]:
    """Recorded results per side, and when each side was recorded."""
    path = _path(step, query.id)
    if not path.exists():
        raise NotRecorded(f"No recording for {query.id} in step {step:02d}. Run it live, or pick another query.")
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("text") != query.text:
        raise NotRecorded(f"The recording for {query.id} is out of date (the query text changed). Re-record it.")
    if "draft" in saved and (not query.draft or saved["draft"] != query.draft["text"]):
        raise NotRecorded(f"The recording for {query.id} is out of date (the draft reply changed). Re-record it.")
    results = {side: SideResult.from_dict(side, saved[side]) for side in ("jev", "llm") if side in saved}
    when = {side: saved[side].get("recorded_at", "") for side in results}
    return results, when
