"""Offline tests for kit.benchmark: metrics and report. No API calls."""

import pytest

from kit import benchmark, data
from kit.compare import SideResult
from kit.trace import Stage


def stage(kind, ms, model=None, tokens=(0, 0)):
    return Stage(kind, kind, ms=ms, model=model, input_tokens=tokens[0], output_tokens=tokens[1])


def jev_result(urgent, handled_by, stages):
    return SideResult("jev", {"urgent": urgent, "handled_by": handled_by}, stages)


def test_handled_kind_reads_the_handled_by_text():
    def kind(text):
        return benchmark.handled_kind(SideResult("jev", {"handled_by": text}, []))

    assert kind("blocked (no LLM)") == "blocked"
    assert kind("human review (draft failed the check)") == "review"
    assert kind("human") == "human"
    assert kind("code") == "code"
    assert kind("Gemini, checked by JEV") == "llm"


def test_first_decision_is_the_first_model_call_not_code():
    result = jev_result(0.9, "code", [stage("code", 1), stage("jev", 500), stage("llm", 1500)])
    assert benchmark.first_decision_ms(result) == 500


def test_ece_is_zero_when_confidence_matches_accuracy():
    points = [benchmark.Point(0.95, True)] * 19 + [benchmark.Point(0.95, False)]
    assert benchmark.ece(points) == pytest.approx(0.0, abs=1e-9)


def test_ece_grows_when_overconfident():
    points = [benchmark.Point(0.95, True), benchmark.Point(0.95, False)]
    assert benchmark.ece(points) == pytest.approx(0.45)


def test_calibration_uses_noul_confidence_on_the_predicted_side():
    q = data.query("q08")  # urgent: false
    points = benchmark.calibration_points([(q, jev_result(0.1, "llm", []))])
    assert points == [benchmark.Point(0.9, True)]


def test_report_counts_handlers_unsafe_and_costs():
    q02, q19 = data.query("q02"), data.query("q19")  # q19 is unsafe
    jev_stages = [stage("jev", 500, "typesafe/jev-1.13", (1000, 0))]
    collected = {
        "jev": [
            (q02, jev_result(0.9, "Gemini, checked by JEV", [*jev_stages, stage("llm", 1500, "gemini-3.5-flash")])),
            (q19, jev_result(0.1, "blocked (no LLM)", jev_stages)),
        ],
        "llm": [
            (
                q02,
                SideResult("llm", {"urgent": True, "handled_by": "Gemini"}, [stage("llm", 1700, "gemini-3.5-flash")]),
            ),
            (
                q19,
                SideResult("llm", {"urgent": False, "handled_by": "blocked"}, [stage("llm", 1700, "gemini-3.5-flash")]),
            ),
        ],
    }
    report = benchmark.build_report(collected, replayed=True)
    assert "| Correct · urgent | 2/2 (100%) | 2/2 (100%) |" in report
    assert "| Unsafe messages kept away from the LLM | 1/1 (100%) | 0/1 (0%) |" in report
    assert "| LLM calls per message (avg) | 0.50 | 1.00 |" in report
    assert "| blocked as unsafe | 1 | 1 |" in report
    assert "Expected calibration error" in report
