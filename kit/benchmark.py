"""`kit.run_benchmark(...)`: run every message through both pipelines and write a dated `report.md`."""

import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from rich.markdown import Markdown

from kit import cli, clients, compare, data, prices, replay, runner, settings, ui
from kit.compare import SideResult

Runs = list[tuple[data.Query, SideResult]]
CALIBRATION_BINS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]


def run_benchmark(title: str, *, jev=None, llm=None, argv: list[str] | None = None) -> None:
    args = cli.parse_args(title, argv)
    args.show_draft = False
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    step = int(re.match(r"\s*(\d+)", title).group(1))
    lessons = {side: fn for side, fn in (("jev", jev), ("llm", llm)) if fn and args.mode in (side, "both")}
    queries = data.queries_for_step(step)
    if args.json:  # machine-readable results, same shape as every other step (used by CI)
        runner._run_json(step, args, lessons, queries)
        return
    if args.replay:
        queries = [q for q in queries if q.id in replay.recorded_ids(step)]
    ui.header(title, args.replay)
    if not args.replay:
        clients.warm_up()
    ui.console.print()
    try:
        collected = runner.collect(step, args, lessons, queries)
    except KeyboardInterrupt:
        ui.console.print("\n[dim]Stopped.[/]")
        return
    report = build_report(collected, args.replay)
    ui.console.print(Markdown(report))
    if args.replay:  # keep the committed report.md from the real run
        ui.console.print("\n[dim]Replay: report.md not changed.[/]")
        return
    path = Path(sys.argv[0]).resolve().parent / "report.md"
    path.write_text(report, encoding="utf-8")
    ui.console.print(f"\n[dim]Written to {path}[/]")


# --- metrics ---------------------------------------------------------------------------------------------


def handled_kind(result: SideResult) -> str:
    """Who dealt with the message in the end: code, llm (sent as written), review, human or blocked."""
    handled = str(result.extras.get("handled_by", "")).lower()
    for kind in ("blocked", "review", "human", "code"):
        if kind in handled:
            return kind
    return "llm"


def first_decision_ms(result: SideResult) -> float | None:
    """Time until the first model answered: JEV's triage, or the LLM's single all-in-one call."""
    models = [s for s in result.stages if s.kind in ("jev", "llm")]
    return models[0].ms if models else None


@dataclass
class Point:
    confidence: float
    correct: bool


def calibration_points(runs: Runs) -> list[Point]:
    """JEV's own probabilities (not code-overridden ones): urgent (a Noul), team and intent (Choices)."""
    points = []
    for query, result in runs:
        for label in ("urgent", "team", "intent"):
            answer = result.answers.get(label)
            if answer is None or label not in query.gold:
                continue
            if answer.shape == "noul":
                p = answer.probability
                points.append(Point(max(p, 1 - p), query.accepts(label, p >= 0.5)))
            elif answer.shape == "choice" and answer.probabilities:
                points.append(Point(answer.probabilities[answer.value], query.accepts(label, answer.value)))
    return points


def ece(points: list[Point]) -> float | None:
    """Expected calibration error: how far stated confidence is from actual accuracy, weighted by bin size."""
    if not points:
        return None
    total = 0.0
    for low, high in CALIBRATION_BINS:
        inside = [p for p in points if low <= p.confidence < high]
        if inside:
            gap = abs(statistics.mean(p.confidence for p in inside) - statistics.mean(p.correct for p in inside))
            total += len(inside) / len(points) * gap
    return total


# --- report ----------------------------------------------------------------------------------------------


def _ms(values: list[float], pct: int) -> str:
    v = compare.percentile([x for x in values if x is not None], pct)
    return "—" if v is None else f"{v:,.0f} ms"


def _pct(hits: int, total: int) -> str:
    return "—" if not total else f"{hits}/{total} ({hits / total:.0%})"


def build_report(collected: dict[str, Runs], replayed: bool) -> str:
    sides = [s for s in ("jev", "llm") if collected.get(s)]
    names = {"jev": "JEV + code + LLM", "llm": "LLM-only"}
    models = {s: ", ".join(sorted({m for _, r in collected[s] for m in r.models})) for s in sides}
    out = [
        "# Desk Buddy benchmark",
        "",
        f"- **Run:** {time.strftime('%Y-%m-%d %H:%M')}" + (" (replayed from recordings)" if replayed else ""),
        f"- **Messages:** {len(next(iter(collected.values()), []))} (all of `data/queries.json`)",
        *[f"- **{names[s]}:** {models[s]}" for s in sides],
        f"- **JEV endpoint:** {settings.env('TYPESAFE_BASE_URL', 'https://api.typesafe.ai')}",
        f"- **Gemini thinking:** {settings.GEMINI_THINKING_LEVEL}",
        f"- **Prices:** OpenRouter, checked {prices.PRICES_CHECKED_ON}",
        "",
        "## Results",
        "",
        "| | " + " | ".join(names[s] for s in sides) + " |",
        "|---|" + "---|" * len(sides),
    ]

    def row(name: str, values: list[str]) -> None:
        out.append(f"| {name} | " + " | ".join(values) + " |")

    labels = [label for label in data.LABELS if any(label in r.answers for s in sides for _, r in collected[s])]
    for label in labels:
        cells = []
        for s in sides:
            graded = [r.correct(q)[label] for q, r in collected[s] if label in r.correct(q)]
            cells.append(_pct(sum(graded), len(graded)))
        row(f"Correct · {label}", cells)
    row("Invalid outputs", [str(sum(not r.valid for _, r in collected[s])) for s in sides])
    first = {s: [first_decision_ms(r) for _, r in collected[s]] for s in sides}
    total = {s: [r.ms for _, r in collected[s] if r.error is None] for s in sides}
    row("Time to first decision p50 / p95", [f"{_ms(first[s], 50)} / {_ms(first[s], 95)}" for s in sides])
    row("Full reply time p50 / p95", [f"{_ms(total[s], 50)} / {_ms(total[s], 95)}" for s in sides])
    llm_calls = {s: [sum(st.kind == "llm" for st in r.stages) for _, r in collected[s]] for s in sides}
    row("LLM calls per message (avg)", [f"{statistics.mean(llm_calls[s]):.2f}" for s in sides])
    costs = {s: [r.cost_usd or 0 for _, r in collected[s]] for s in sides}
    row("Cost per 1,000 messages", [f"${statistics.mean(costs[s]) * 1000:,.2f}" for s in sides])
    kinds = {s: [handled_kind(r) for _, r in collected[s]] for s in sides}
    row(
        "Handled with no person (code or LLM reply sent)",
        [_pct(sum(k in ("code", "llm") for k in kinds[s]), len(kinds[s])) for s in sides],
    )
    unsafe = {s: [(q, r) for q, r in collected[s] if q.gold.get("unsafe")] for s in sides}
    row(
        "Unsafe messages kept away from the LLM",
        [_pct(sum(not any(st.kind == "llm" for st in r.stages) for _, r in unsafe[s]), len(unsafe[s])) for s in sides],
    )

    out += ["", "## Who handled each message", "", "| | " + " | ".join(names[s] for s in sides) + " |"]
    out.append("|---|" + "---|" * len(sides))
    for kind, meaning in (
        ("code", "code (no LLM)"),
        ("llm", "LLM reply sent"),
        ("review", "LLM draft held for review"),
        ("human", "handed to a person"),
        ("blocked", "blocked as unsafe"),
    ):
        row(meaning, [str(kinds[s].count(kind)) for s in sides])

    if "jev" in sides:
        points = calibration_points(collected["jev"])
        out += [
            "",
            "## Does JEV's confidence mean what it says?",
            "",
            "JEV's own probabilities for `urgent`, `team` and `intent` (rule overrides excluded), grouped by how sure",
            "it was. Well calibrated = the *right* column matches the *said* column.",
            "",
            "| JEV said | answers | right |",
            "|---|---|---|",
        ]
        for low, high in CALIBRATION_BINS:
            inside = [p for p in points if low <= p.confidence < high]
            if inside:
                said = statistics.mean(p.confidence for p in inside)
                right = statistics.mean(p.correct for p in inside)
                out.append(f"| {low:.1f}–{min(high, 1.0):.1f} (avg {said:.2f}) | {len(inside)} | {right:.0%} |")
        error = ece(points)
        out += ["", f"Expected calibration error: **{error:.3f}** (0 = perfect)." if error is not None else ""]
        out += ["The LLM-only pipeline gives no probabilities, so there is nothing to calibrate."]

    out += ["", "## Every message", "", "| Message | " + " | ".join(names[s] for s in sides) + " |"]
    out.append("|---|" + "---|" * len(sides))
    by_query = {q.id: {s: r for s in sides for qq, r in collected[s] if qq.id == q.id} for q, _ in collected[sides[0]]}
    for query, _ in collected[sides[0]]:
        cells = []
        for s in sides:
            r = by_query[query.id].get(s)
            if r is None or r.error:
                cells.append("error")
                continue
            wrong = [label for label, ok in r.correct(query).items() if not ok]
            mark = "✔" if not wrong else "✘ " + ", ".join(wrong)
            cells.append(f"{mark} · {handled_kind(r)} · {r.ms:,.0f} ms")
        out.append(f"| {query.id} {query.kind} | " + " | ".join(cells) + " |")

    out += [
        "",
        "## Read this before quoting the numbers",
        "",
        "- 24 messages is a teaching set, not a benchmark suite: one message is 4 percentage points.",
        "- Latency includes the network. JEV ran through the endpoint above; a gateway adds a hop.",
        "- Gold labels were written by hand and reviewed where both models disagreed (see `data/README.md`).",
        "- LLM output varies from run to run; run it yourself with `--all`, or `--replay` to see these exact runs.",
        "",
    ]
    return "\n".join(out)
