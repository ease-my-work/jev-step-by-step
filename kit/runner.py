"""`kit.run_step(...)`: the whole CLI experience for one step — picker, live run, comparison, --all, --replay."""

import json
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from rich.live import Live

from kit import cli, clients, compare, data, replay, trace, ui
from kit.compare import SideResult
from kit.settings import SetupError
from kit.trace import Stage

Lesson = Callable[[data.Query], Any]
REPLAY_MAX_STAGE_SECONDS = 4.0


def run_step(
    title: str,
    *,
    jev: Lesson | None = None,
    llm: Lesson | None = None,
    show_draft: bool = False,
    argv: list[str] | None = None,
) -> None:
    """Run a lesson step from the command line.

    `title` starts with the step number, e.g. "01 · Noul — is this message urgent?".
    """
    args = cli.parse_args(title, argv)
    args.show_draft = show_draft
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ₹, ✔, bars on older Windows consoles
    match = re.match(r"\s*(\d+)", title)
    if not match:
        raise ValueError(f"Step title must start with its number, got {title!r}")
    step = int(match.group(1))
    lessons = {side: fn for side, fn in (("jev", jev), ("llm", llm)) if fn and args.mode in (side, "both")}
    queries = data.queries_for_step(step)

    try:
        if args.json:
            _run_json(step, args, lessons, queries)
        elif args.all:
            ui.header(title, args.replay)
            _run_all(step, args, lessons, queries)
        elif args.query:
            ui.header(title, args.replay)
            if not args.replay:
                clients.warm_up()
            _run_one(step, args, lessons, data.query(args.query))
        else:
            _interactive(title, step, args, lessons, queries)
    except KeyboardInterrupt:
        ui.console.print("\n[dim]Bye![/]")
    except KeyError as error:
        ui.error(str(error.args[0]))
        sys.exit(2)


# --- one run -----------------------------------------------------------------------------------------------


@dataclass
class _Run:
    side: str
    stages: list[Stage] = field(default_factory=list)
    result: SideResult | None = None
    thread: threading.Thread | None = None


def _start_live(side: str, lesson: Lesson, query: data.Query) -> _Run:
    run = _Run(side)

    def work() -> None:
        raw, error = None, None
        with trace.recording(into=run.stages):
            try:
                raw = lesson(query)
            except SetupError as e:
                error = str(e)
            except Exception as e:  # show any API error on screen instead of a traceback
                error = f"{type(e).__name__}: {str(e)[:300]}"
        run.result = SideResult(side, raw, run.stages, error)

    run.thread = threading.Thread(target=work, daemon=True)
    run.thread.start()
    return run


def _start_replay(side: str, recorded: SideResult, animate: bool) -> _Run:
    run = _Run(side)
    final = [replace(s, waited_ms=0.0, waiting=False) for s in recorded.stages]  # replays never wait

    def work() -> None:
        for stage in final:
            shown = Stage(stage.kind, stage.label)
            run.stages.append(shown)
            if animate:
                time.sleep(min((stage.ms or 0) / 1000, REPLAY_MAX_STAGE_SECONDS))
            run.stages[-1] = stage
        run.result = SideResult(side, recorded.raw, final, recorded.error)

    run.thread = threading.Thread(target=work, daemon=True)
    run.thread.start()
    return run


def _execute(
    step: int, args, lessons: dict[str, Lesson], query: data.Query, *, show: bool
) -> tuple[dict[str, SideResult], dict[str, str] | None]:
    """Run (or replay) both sides concurrently. With `show`, draw the live flow chart while they run."""
    recorded_at = None
    if args.replay:
        recorded, recorded_at = replay.load(step, query)
        runs = {side: _start_replay(side, recorded[side], animate=show) for side in lessons if side in recorded}
        if not runs:
            raise replay.NotRecorded(f"No recording of the requested side(s) for {query.id}.")
    else:
        runs = {side: _start_live(side, lesson, query) for side, lesson in lessons.items()}

    def view():
        return ui.live_view(query, {side: (r.stages, r.result) for side, r in runs.items()})

    if show:
        with Live(view(), console=ui.console, refresh_per_second=15, transient=False) as live:
            while any(r.result is None for r in runs.values()):
                live.update(view())
                time.sleep(1 / 15)
            live.update(view())
    for r in runs.values():
        r.thread.join()
    results = {side: r.result for side, r in runs.items()}
    if args.record and query.id != "custom":
        path = replay.save(step, query, results, with_draft=args.show_draft)
        if show:
            ui.console.print(f"[dim]Recorded → {path.relative_to(replay.ROOT)}[/]")
    return results, recorded_at


def _run_one(step: int, args, lessons: dict[str, Lesson], query: data.Query) -> None:
    ui.show_query(query, args.show_draft)
    try:
        results, recorded_at = _execute(step, args, lessons, query, show=True)
    except replay.NotRecorded as error:
        ui.error(str(error))
        return
    if all(r.error for r in results.values()):
        ui.console.print("\n[dim]Nothing to compare. Fix the error above, or add --replay to use recorded answers.[/]")
        return
    ui.console.print(ui.comparison(results, query, recorded_at))


# --- interactive ---------------------------------------------------------------------------------------------


def _interactive(title: str, step: int, args, lessons: dict[str, Lesson], queries: list[data.Query]) -> None:
    if not sys.stdin.isatty():
        ui.error("No terminal to show the picker in. Use --query qNN or --all.")
        sys.exit(2)
    ui.header(title, args.replay)
    if not args.replay:  # open connections while the learner is choosing, so the first timing is fair
        threading.Thread(target=clients.warm_up, daemon=True).start()
    recorded = replay.recorded_ids(step) if args.replay else None
    query = None
    while True:
        if query is None:
            picked = ui.pick_query(queries, recorded)
            if picked is None:
                return
            if picked == "custom":
                text = ui.ask_custom_text()
                if not text:
                    continue
                picked = data.Query("custom", "custom", text, "", None, {}, (), "")
            query = picked
        _run_one(step, args, lessons, query)
        action = ui.next_action()
        if action in (None, "quit"):
            return
        if action == "pick":
            query = None
        elif action == "all":
            _run_all(step, args, lessons, queries)
            query = None


# --- --all and --json ------------------------------------------------------------------------------------------


def _run_all(step: int, args, lessons: dict[str, Lesson], queries: list[data.Query]) -> None:
    if args.replay:
        recorded = replay.recorded_ids(step)
        queries = [q for q in queries if q.id in recorded]
        if not queries:
            ui.error(f"No recordings for step {step:02d} yet.")
            return
    else:
        clients.warm_up()
    ui.console.print()
    collected = collect(step, args, lessons, queries)
    summaries = [compare.summarize(side, runs) for side, runs in collected.items() if runs]
    models = {side: sorted({m for _, r in runs for m in r.models}) for side, runs in collected.items()}
    ui.console.print(ui.summary(summaries, models, args.replay))


def collect(
    step: int, args, lessons: dict[str, Lesson], queries: list[data.Query]
) -> dict[str, list[tuple[data.Query, SideResult]]]:
    """Run every query (one line of output each) and return the results per side."""
    collected: dict[str, list[tuple[data.Query, SideResult]]] = {side: [] for side in lessons}
    for n, query in enumerate(queries, 1):
        with ui.console.status(f"[dim]{query.id} ({n}/{len(queries)}): {query.text[:60]}[/]"):
            try:
                results, _ = _execute(step, args, lessons, query, show=False)
            except replay.NotRecorded as error:
                ui.error(str(error))
                continue
        ui.console.print(ui.all_row(query, results))
        for side, result in results.items():
            collected.setdefault(side, []).append((query, result))
    return collected


def _side_json(query: data.Query, result: SideResult) -> dict[str, Any]:
    answers = {}
    for label, a in result.answers.items():
        detail = {"value": a.value, "probability": a.probability, "confidence": a.confidence, "valid": a.valid}
        answers[label] = {k: v for k, v in detail.items() if v is not None}
    return {
        "answers": answers,
        "extras": result.extras,
        "correct": result.correct(query),
        "valid": result.valid,
        "ms": round(result.ms, 1),
        "waited_ms": round(result.waited_ms, 1),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": result.cost_usd,
        "models": result.models,
        "error": result.error,
    }


def _run_json(step: int, args, lessons: dict[str, Lesson], queries: list[data.Query]) -> None:
    if args.query:
        queries = [data.query(args.query)]
    elif args.replay:
        queries = [q for q in queries if q.id in replay.recorded_ids(step)]
    if not args.replay:
        clients.warm_up()
    rows = []
    collected: dict[str, list[tuple[data.Query, SideResult]]] = {side: [] for side in lessons}
    for query in queries:
        try:
            results, _ = _execute(step, args, lessons, query, show=False)
        except replay.NotRecorded as error:
            rows.append({"step": step, "query": query.id, "error": str(error)})
            continue
        rows.append(
            {"step": step, "query": query.id, "replay": args.replay}
            | {side: _side_json(query, r) for side, r in results.items()}
        )
        for side, result in results.items():
            collected[side].append((query, result))
    summary = {}
    for side, runs in collected.items():
        if runs:
            s = compare.summarize(side, runs)
            summary[side] = {
                "runs": s.runs,
                "valid": s.valid,
                "accuracy": s.accuracy,
                "p50_ms": s.p50,
                "p95_ms": s.p95,
                "cost_per_1k_usd": s.cost_per_1k,
            }
    json.dump({"step": step, "results": rows, "summary": summary}, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")
