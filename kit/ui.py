"""Everything the learner sees in the terminal: query picker, live flow chart, answers, comparison panel."""

import json
import time
from typing import Any

import questionary
from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from kit import data
from kit.compare import Answer, SideResult, Summary
from kit.trace import Stage

console = Console(highlight=False)

SIDE_NAME = {"jev": "JEV", "llm": "LLM-only"}
SIDE_STYLE = {"jev": "cyan", "llm": "orange3"}
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
PICKER_STYLE = questionary.Style([("qid", "fg:ansicyan bold"), ("kind", "fg:ansibrightblack")])


# --- small helpers ---------------------------------------------------------------------------------------


def fmt_ms(ms: float | None) -> str:
    return "—" if ms is None else f"{ms:,.0f} ms"


def fmt_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def bar(fraction: float, width: int = 30) -> str:
    filled = round(max(0.0, min(1.0, fraction)) * width)
    return "█" * filled + "░" * (width - filled)


def _spinner() -> str:
    return SPINNER[int(time.perf_counter() * 12) % len(SPINNER)]


def _gold_mark(query: data.Query | None, label: str, value: Any) -> Text:
    if query is None or label not in query.gold:
        return Text("")
    if query.accepts(label, value):
        return Text(" ✔", style="green")
    return Text(f" ✘ gold: {fmt_value(query.gold[label])}", style="red")


# --- header, picker, menus -----------------------------------------------------------------------------


def header(title: str, replay: bool) -> None:
    console.print()
    console.print(Rule(f"[bold]Step {title}[/]", style="cyan"))
    note = "  [yellow](replay: recorded answers and timings, no API calls)[/]" if replay else ""
    console.print(f"[dim]JEV and LLM-only answer the same customer message side by side. Ctrl+C quits.[/]{note}")


def pick_query(queries: list[data.Query], recorded: set[str] | None) -> data.Query | str | None:
    """Arrow-key list of this step's queries. Returns a Query, "custom", or None to quit."""
    width = max(40, console.width - 24)
    choices = []
    for q in queries:
        text = q.text if len(q.text) <= width else q.text[: width - 1] + "…"
        disabled = "not recorded" if recorded is not None and q.id not in recorded else None
        title = [("class:qid", f"{q.id}  "), ("", text), ("class:kind", f"  [{q.kind}]")]
        choices.append(questionary.Choice(title=title, value=q, disabled=disabled))
    if recorded is None:
        choices.append(questionary.Choice(title="✎   Type your own…", value="custom"))
    return questionary.select(
        "Pick a customer message", choices=choices, style=PICKER_STYLE, instruction="(↑/↓, Enter)"
    ).ask()


def ask_custom_text() -> str | None:
    return questionary.text("Customer message:").ask()


def next_action() -> str | None:
    return questionary.select(
        "Next?",
        choices=[
            questionary.Choice("↻  Run again", value="again"),
            questionary.Choice("☰  Pick another message", value="pick"),
            questionary.Choice("▶  Run all messages for this step", value="all"),
            questionary.Choice("✕  Quit", value="quit"),
        ],
    ).ask()


def show_query(query: data.Query, show_draft: bool = False) -> None:
    console.print()
    console.print(Text.assemble(("💬 ", ""), (query.id, "bold cyan"), "  ", (f'"{query.text}"', "bold")))
    if query.teaches:
        console.print(f"   [dim]Why this one: {query.teaches}[/]")
    if show_draft and query.draft:
        console.print(Panel(query.draft["text"], title="Draft reply to check", title_align="left", border_style="dim"))


def error(message: str) -> None:
    console.print(f"[red]✘ {message}[/]")


# --- live flow chart -------------------------------------------------------------------------------------


def _stage_status(stage: Stage) -> Text:
    if stage.error:
        return Text("✘ error", style="red")
    if stage.waiting:
        return Text(f"⏳ rate limit {(time.perf_counter() - stage.started):.1f}s", style="yellow")
    if stage.done:
        return Text(f"✔ {fmt_ms(stage.ms)}", style="green")
    return Text(f"{_spinner()} {fmt_ms(stage.elapsed_ms())}", style="yellow")


def _box(title: str, status: Text, border: str) -> Panel:
    return Panel(Text.assemble((title, "bold"), "\n", status), border_style=border, padding=(0, 1), expand=False)


def flow_chart(side: str, stages: list[Stage], finished: bool, failed: bool) -> RenderableType:
    """Query ─▶ stage ─▶ stage ─▶ Answer, one box per stage; falls back to a list on narrow terminals."""
    style = SIDE_STYLE[side]
    total = sum(s.elapsed_ms() for s in stages if not s.waiting)
    answer_status = (
        Text("✘ failed", style="red")
        if failed
        else Text("✔", style="green")
        if finished
        else Text(_spinner() if stages else "…", style="yellow")
    )
    boxes = [("Message", Text("✔", style="green"), style)]
    for s in stages:
        border = "red" if s.error else style if s.done else "yellow"
        boxes.append((s.label, _stage_status(s), border))
    boxes.append(("Answer", answer_status, "red" if failed else style if finished else "dim"))

    title = Text.assemble((f"{SIDE_NAME[side]} flow", f"bold {style}"), "   ", (f"⏱ {fmt_ms(total)}", "bold"))
    needed = sum(max(len(t), len(st.plain)) + 6 for t, st, _ in boxes) + 3 * (len(boxes) - 1)
    if needed > console.width:
        lines = [Text.assemble(("  • ", style), (t, "bold"), "  ", st) for t, st, _ in boxes]
        return Group(title, *lines)
    grid = Table.grid(padding=0)
    cells: list[RenderableType] = []
    for i, (t, st, border) in enumerate(boxes):
        if i:
            grid.add_column(vertical="middle")
            cells.append(Text(" ─▶ ", style="dim"))
        grid.add_column(vertical="middle")
        cells.append(_box(t, st, border))
    grid.add_row(*cells)
    return Group(title, grid)


# --- answers -----------------------------------------------------------------------------------------------


def _level_name(legend_entry: Any) -> str:
    """Short name of a Score level: the text before ":" ("angry: shouting, ..." → "angry")."""
    return str(legend_entry).split(":")[0].strip()


def _answer_lines(answer: Answer, query: data.Query | None) -> list[RenderableType]:
    label = Text(f"  {answer.label:<12}", style="bold")
    mark = _gold_mark(query, answer.label, answer.value)
    if answer.shape == "noul":
        p = answer.probability or 0.0
        return [Text.assemble(label, (bar(p), "cyan"), f"  {p:.2f} → ", (fmt_value(answer.value), "bold"), mark)]
    if answer.shape == "choice":
        lines: list[RenderableType] = [
            Text.assemble(
                label, "→ ", (str(answer.value), "bold"), (f"   confidence {answer.confidence:.2f}", "dim"), mark
            )
        ]
        ranked = sorted((answer.probabilities or {}).items(), key=lambda kv: -kv[1])[:6]
        for option, p in ranked:
            style = "cyan" if option == answer.value else "bright_black"
            lines.append(Text.assemble(f"    {option:<16}", (bar(p, 26), style), f"  {p:.2f}"))
        return lines
    if answer.shape == "score":
        legend = answer.legend or {}
        level_name = _level_name(legend.get(answer.value, ""))
        lines = [
            Text.assemble(
                label,
                "→ ",
                (f"{answer.value} {level_name}".strip(), "bold"),
                (f"   score {answer.score:.2f} · confidence {answer.confidence:.2f}", "dim"),
                mark,
            )
        ]
        for level, p in sorted((answer.probabilities or {}).items()):
            style = "cyan" if level == answer.value else "bright_black"
            name = f"{level} {_level_name(legend.get(level, ''))}"[:16]
            lines.append(Text.assemble(f"    {name:<16}", (bar(p, 26), style), f"  {p:.2f}"))
        return lines
    validity = Text("") if answer.valid else Text("  ✘ not an allowed value", style="red")
    return [Text.assemble(label, "→ ", (fmt_value(answer.value), "bold"), mark, validity)]


def answers(result: SideResult, query: data.Query | None) -> RenderableType:
    if result.error:
        return Text(f"  ✘ {result.error}", style="red")
    if not isinstance(result.raw, dict):
        return Text(f"  ✘ no valid JSON from the model: {result.raw!r}", style="red")
    lines: list[RenderableType] = []
    if result.side == "llm":
        lines.append(Text(f"  {json.dumps(result.raw, ensure_ascii=False)}", style="dim"))
    for answer in result.answers.values():
        lines.extend(_answer_lines(answer, query))
    if "handled_by" in result.extras:
        lines.append(Text.assemble("  handled by  → ", (str(result.extras["handled_by"]), "bold")))
    if result.extras.get("reply"):
        lines.append(Panel(str(result.extras["reply"]), title="reply", title_align="left", border_style="dim"))
    return Group(*lines)


def live_view(query: data.Query | None, runs: dict[str, tuple[list[Stage], SideResult | None]]) -> RenderableType:
    parts: list[RenderableType] = []
    for side, (stages, result) in runs.items():
        finished = result is not None
        failed = finished and (result.error is not None or not isinstance(result.raw, dict))
        parts.append(Text(""))
        parts.append(flow_chart(side, stages, finished, failed))
        if finished:
            parts.append(answers(result, query))
    return Group(*parts)


# --- comparison --------------------------------------------------------------------------------------------


def _confidence(result: SideResult) -> str:
    if result.side == "llm":
        c = result.extras.get("confidence")
        return f'"{c}" (self-reported)' if c is not None else "— (not asked)"
    parts = []
    for a in result.answers.values():
        if a.shape == "noul" and a.probability is not None:
            parts.append((a.label, f"P(yes) {a.probability:.2f}"))
        elif a.confidence is not None:
            parts.append((a.label, f"{a.confidence:.2f}"))
    if not parts:
        return "—"
    if len(parts) == 1:
        return f"{parts[0][1]} (from probabilities)"
    return "\n".join(f"{label}: {value}" for label, value in parts)


def _output_kind(result: SideResult) -> Text:
    if result.error:
        return Text("✘ failed", style="red")
    if not result.valid:
        return Text("✘ invalid output", style="red")
    if result.side == "jev":
        return Text("typed — always valid", style="green")
    return Text("valid output", style="green")


def _bar_width(columns: int) -> int:
    """Latency bar width that keeps the comparison table on one line per row."""
    column = (console.width - 20) // max(1, columns) - 3
    return max(6, min(22, column - 10))


def comparison(
    results: dict[str, SideResult], query: data.Query | None, recorded_at: dict[str, str] | None = None
) -> RenderableType:
    sides = list(results)
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold", expand=False, padding=(0, 1))
    table.add_column("")
    for side in sides:
        table.add_column(SIDE_NAME[side], header_style=f"bold {SIDE_STYLE[side]}")

    def row(name: str, cells: list[RenderableType]) -> None:
        table.add_row(Text(name, style="bold"), *cells)

    answer_cells = []
    for side in sides:
        r = results[side]
        lines = [
            Text.assemble(f"{a.label}: ", (fmt_value(a.value), "bold"), _gold_mark(query, a.label, a.value))
            for a in r.answers.values()
        ]
        answer_cells.append(Group(*lines) if lines else Text("—"))
    row("Answer", answer_cells)
    row("Output", [_output_kind(results[s]) for s in sides])
    row("Confidence", [Text(_confidence(results[s])) for s in sides])
    slowest = max((results[s].ms for s in sides), default=1) or 1
    row(
        "Latency",
        [
            Text.assemble(
                (bar(results[s].ms / slowest, _bar_width(len(sides))), SIDE_STYLE[s]), f" {fmt_ms(results[s].ms)}"
            )
            for s in sides
        ],
    )
    row("Tokens", [Text(_tokens(results[s])) for s in sides])
    row("Cost / 1k runs", [Text(_cost(results[s].cost_usd)) for s in sides])
    row("Model", [Text(", ".join(results[s].models) or "—", style="dim") for s in sides])

    notes = [verdict(results, query)]
    llm = results.get("llm")
    if llm and llm.waited_ms > 50:
        notes.append(f"LLM-only waited {llm.waited_ms / 1000:.1f} s for the free-tier rate limit (not counted).")
    if recorded_at:
        when = min(v for v in recorded_at.values() if v) if any(recorded_at.values()) else "?"
        notes.append(f"Replayed from a recording made {when[:10]}: timings are the recorded ones.")
    return Group(Text(""), table, *[Text(f"💡 {n}") for n in notes])


def _tokens(result: SideResult) -> str:
    if not result.stages:
        return "—"
    thinking = sum(s.thinking_tokens or 0 for s in result.stages)
    out = result.output_tokens - thinking
    text = f"{result.input_tokens:,} in / {out:,} out"
    return text + (f" / {thinking:,} thinking" if result.side == "llm" else "")


def _cost(cost: float | None) -> str:
    return "—" if cost is None else f"${cost * 1000:.3f}"


def verdict(results: dict[str, SideResult], query: data.Query | None) -> str:
    jev, llm = results.get("jev"), results.get("llm")
    if not (jev and llm):
        only = jev or llm
        return f"{SIDE_NAME[only.side]} took {fmt_ms(only.ms)}." if only else ""
    if jev.error or llm.error:
        return "One side failed — see the error above."
    speed = (
        f"JEV was {llm.ms / jev.ms:.1f}× faster"
        if jev.ms and jev.ms < llm.ms
        else f"LLM-only was faster this time ({fmt_ms(llm.ms)} vs {fmt_ms(jev.ms)})"
    )
    if query is None or not query.gold:
        return f"{speed}."
    jev_ok, llm_ok = all(jev.correct(query).values()), llm.valid and all(llm.correct(query).values())
    if jev_ok and llm_ok:
        return f"Both match the gold label. {speed}."
    if jev_ok:
        return f"JEV matches the gold label; LLM-only doesn't. {speed}."
    if llm_ok:
        return f"LLM-only matches the gold label; JEV doesn't. {speed}."
    return f"Neither matches the gold label — the README explains why this message is hard. {speed}."


# --- --all -------------------------------------------------------------------------------------------------


def all_row(query: data.Query, results: dict[str, SideResult]) -> Text:
    """One line per message: answers (✔/✘ against gold) and latency for each side."""
    line = Text.assemble((f"{query.id} ", "bold cyan"), (f"{query.kind:<10}", "dim"))
    # id+kind take 14 columns; each side takes 20 + the answer values ("│ JEV ✔ " … " 1,234 ms")
    room = max(8, (console.width - 15) // max(1, len(results)) - 20)
    for side, r in results.items():
        line.append(f" │ {'JEV' if side == 'jev' else 'LLM'} ", style=f"bold {SIDE_STYLE[side]}")
        if r.error:
            line.append(f"✘ {r.error[: room + 10]}", style="red")
            continue
        correct = r.correct(query)
        line.append(
            "✔" if correct and all(correct.values()) else "✘", style="green" if all(correct.values()) else "red"
        )
        if len(r.answers) > 1:  # several labels: say which ones were wrong
            wrong = [label for label, ok in correct.items() if not ok]
            values = f"{len(correct) - len(wrong)}/{len(correct)}" + (f" ✘ {','.join(wrong)}" if wrong else "")
        else:
            values = " ".join(fmt_value(a.value) for a in r.answers.values())
        values = values if len(values) <= room else values[: room - 1] + "…"
        line.append(f" {values:<{room}} {fmt_ms(r.ms):>9}")
    return line


def summary(summaries: list[Summary], models: dict[str, list[str]], replay: bool) -> RenderableType:
    table = Table(box=box.ROUNDED, title="Summary", title_style="bold", padding=(0, 1))
    table.add_column("")
    for s in summaries:
        table.add_column(SIDE_NAME[s.side], justify="right")
    labels = sorted({label for s in summaries for label in s.accuracy})
    for label in labels:
        cells = []
        for s in summaries:
            hits = s.correct.get(label, [])
            cells.append(f"{sum(hits)}/{len(hits)}  ({s.accuracy[label]:.0%})" if hits else "—")
        table.add_row(f"Accuracy · {label}", *cells)
    table.add_row("Valid outputs", *[f"{s.valid}/{s.runs}" for s in summaries])
    table.add_row("Latency p50", *[fmt_ms(s.p50) for s in summaries])
    table.add_row("Latency p95", *[fmt_ms(s.p95) for s in summaries])
    table.add_row("Cost / 1k runs", *[_cost(s.cost_per_1k / 1000 if s.cost_per_1k else None) for s in summaries])
    table.add_row("Model", *[", ".join(models.get(s.side, [])) or "—" for s in summaries])
    note = "[dim]Replay: recorded timings.[/]" if replay else f"[dim]Run {time.strftime('%Y-%m-%d %H:%M')}.[/]"
    return Group(Text(""), table, Text.from_markup(note))
