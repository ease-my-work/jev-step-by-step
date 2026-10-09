"""Offline tests for kit.run_step, replay, compare, prices and the UI. Lessons are faked; no API calls."""

import json

import pytest
from rich.console import Console
from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer

from kit import compare, data, prices, replay, runner, ui
from kit.trace import track


def fake_jev(query):
    with track("jev", "JEV · 1 question") as stage:
        stage.model, stage.input_tokens, stage.output_tokens = "typesafe/jev-1.13-20260917", 300, 20
    return {"urgent": 0.9 if "immediate" in query.text else 0.1}


def fake_llm(query):
    with track("llm", "Gemini call") as stage:
        stage.model, stage.input_tokens, stage.output_tokens, stage.thinking_tokens = "gemini-3.5-flash", 70, 9, 0
    return {"urgent": True, "confidence": "high"}


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(runner.clients, "warm_up", lambda: None)
    monkeypatch.setattr(replay, "FIXTURES_DIR", tmp_path / "fixtures")
    monkeypatch.setattr(ui, "console", Console(width=80, record=True, force_terminal=False))


def run_json(capsys, *argv, jev=fake_jev, llm=fake_llm):
    runner.run_step("01 · test", jev=jev, llm=llm, argv=["--json", *argv])
    return json.loads(capsys.readouterr().out)


def test_json_one_query_grades_both_sides(capsys):
    out = run_json(capsys, "--query", "q02")
    row = out["results"][0]
    assert row["jev"]["answers"]["urgent"] == {"value": True, "probability": 0.9, "valid": True}
    assert row["jev"]["correct"] == {"urgent": True}
    assert row["llm"]["extras"] == {"confidence": "high"}
    assert row["llm"]["correct"] == {"urgent": True}
    assert row["jev"]["cost_usd"] == pytest.approx(300 * 0.042 / 1e6)
    assert row["llm"]["cost_usd"] == pytest.approx((70 * 1.5 + 9 * 9) / 1e6)


def test_json_all_summarises_accuracy(capsys):
    out = run_json(capsys, "--all")
    assert len(out["results"]) == len(data.queries_for_step(1))
    llm = out["summary"]["llm"]  # fake LLM always says urgent=yes
    urgent_gold = [q.gold["urgent"] for q in data.queries_for_step(1)]
    assert llm["accuracy"]["urgent"] == pytest.approx(sum(urgent_gold) / len(urgent_gold))
    assert out["summary"]["jev"]["valid"] == len(urgent_gold)


def test_mode_runs_one_side_only(capsys):
    row = run_json(capsys, "--query", "q02", "--mode", "jev")["results"][0]
    assert "jev" in row and "llm" not in row


def test_errors_are_reported_not_raised(capsys):
    def broken(query):
        raise RuntimeError("quota exceeded")

    row = run_json(capsys, "--query", "q02", llm=broken)["results"][0]
    assert row["llm"]["error"] == "RuntimeError: quota exceeded"
    assert row["llm"]["valid"] is False
    assert row["jev"]["error"] is None


def test_invalid_llm_output_is_flagged(capsys):
    row = run_json(capsys, "--query", "q02", llm=lambda q: {"urgent": "maybe"})["results"][0]
    assert row["llm"]["valid"] is False
    assert row["llm"]["correct"] == {"urgent": False}


def test_record_then_replay_gives_the_same_answers_and_timings(capsys):
    live = run_json(capsys, "--query", "q02", "--record")["results"][0]
    assert replay.recorded_ids(1) == {"q02"}
    replayed = run_json(capsys, "--query", "q02", "--replay")["results"][0]
    for side in ("jev", "llm"):
        assert replayed[side]["answers"] == live[side]["answers"]
        assert replayed[side]["ms"] == live[side]["ms"]


def test_replay_of_unrecorded_query_says_so(capsys):
    row = run_json(capsys, "--query", "q07", "--replay")["results"][0]
    assert "No recording" in row["error"]


def test_failed_runs_are_never_recorded(capsys):
    run_json(capsys, "--query", "q02", "--record", llm=lambda q: 1 / 0)
    saved = json.loads((replay.FIXTURES_DIR / "step01" / "q02.json").read_text(encoding="utf-8"))
    assert "jev" in saved and "llm" not in saved


def test_interactive_needs_a_terminal(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit):
        runner.run_step("01 · test", jev=fake_jev, llm=fake_llm, argv=[])


# --- compare ---------------------------------------------------------------------------------------------------

CHOICE = ChoiceAnswer(type="choice", choice="billing", confidence=0.91, probabilities={"billing": 0.91, "other": 0.09})
SCORE = ScoreAnswer(
    type="score",
    score=1.2,
    confidence=0.7,
    legend={0: "calm", 1: "annoyed", 2: "angry"},
    probabilities={0: 0.1, 1: 0.6, 2: 0.3},
)


def test_jev_answer_objects_become_decisions():
    assert compare.to_answer("urgent", NoulAnswer(type="noul", noul=0.3)).value is False
    assert compare.to_answer("team", CHOICE).value == "billing"
    score = compare.to_answer("frustration", SCORE)
    assert (score.value, score.legend[1]) == (1, "annoyed")


def test_plain_values_are_checked_against_allowed_labels():
    assert compare.to_answer("team", "billing").valid
    assert not compare.to_answer("team", "Payments Team").valid
    assert not compare.to_answer("frustration", True).valid  # a bool is not a level
    assert compare.to_answer("route", "anything").valid  # not a graded label: not checked


def test_answer_objects_survive_a_fixture_round_trip():
    result = compare.SideResult("jev", {"team": CHOICE, "frustration": SCORE, "urgent": 0.8}, [])
    back = compare.SideResult.from_dict("jev", json.loads(json.dumps(result.to_dict())))
    assert back.raw == result.raw


def test_percentiles():
    assert compare.percentile([100.0, 200.0, 300.0], 50) == 200.0
    assert compare.percentile([], 50) is None


# --- prices ------------------------------------------------------------------------------------------------------


def test_prices_match_model_names_as_the_apis_report_them():
    assert prices.price_for("typesafe/jev-1.13-20260917") == (0.042, 0.0)
    assert prices.price_for("gemini-3.5-flash-lite") == (0.30, 2.50)  # not the plain Flash price
    assert prices.price_for("gemini-3.5-flash") == (1.50, 9.00)
    assert prices.price_for("some-other-model") is None


# --- ui -------------------------------------------------------------------------------------------------------------


def test_comparison_and_flow_chart_fit_80_columns():
    query = data.query("q02")
    results = {
        "jev": compare.SideResult("jev", {"urgent": 0.86}, []),
        "llm": compare.SideResult("llm", {"urgent": True, "confidence": "high"}, []),
    }
    with track("jev", "JEV · 1 question"):
        pass
    ui.console.print(ui.live_view(query, {side: ([], r) for side, r in results.items()}))
    ui.console.print(ui.comparison(results, query))
    text = ui.console.export_text()
    assert "urgent" in text and "Both match the gold label" in text
    assert max(len(line) for line in text.splitlines()) <= 80
