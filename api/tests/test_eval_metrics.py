"""The evaluation's graders are deterministic code, so they are tested like any other code."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))

from metrics import by, confusion, grade, percentile, summarise  # noqa: E402


def row(expected, got, lang="en", latency=1.0, cost=0.01, expected_codes=(), codes=()):
    return {
        "expected": expected, "got": got, "lang": lang, "latency_s": latency, "cost_usd": cost,
        "expected_codes": list(expected_codes), "codes": list(codes),
    }  # fmt: skip


@pytest.mark.parametrize(
    "expected,got,flags",
    [
        ("SAFE", "SAFE", {"correct"}),
        ("SCAM", "SCAM", {"correct"}),
        ("SCAM", "SAFE", {"false_safe"}),
        ("CAUTION", "SAFE", {"false_safe"}),
        ("SAFE", "CAUTION", {"false_alarm"}),
        ("SAFE", "SCAM", {"false_alarm"}),
        ("SCAM", "CAUTION", {"scam_downgraded"}),
        ("CAUTION", "SCAM", set()),
    ],
)
def test_grades(expected, got, flags):
    graded = grade(row(expected, got))
    graded.pop("evidence_found")
    assert {k for k, v in graded.items() if v} == flags


def test_evidence_is_found_only_if_every_expected_code_is_there():
    assert grade(row("SCAM", "SCAM", expected_codes=["A"], codes=["A", "B"]))["evidence_found"]
    assert not grade(row("SCAM", "SCAM", expected_codes=["A", "C"], codes=["A"]))["evidence_found"]


def test_percentile_is_nearest_rank_and_a_measured_value():
    values = [1.0, 2.0, 3.0, 4.0, 10.0]
    assert percentile(values, 50) == 3.0
    assert percentile(values, 90) == 10.0
    assert percentile([], 50) is None


def test_summary_rates_use_the_right_denominators():
    rows = [row("SAFE", "SAFE"), row("SAFE", "CAUTION"), row("SCAM", "SAFE"), row("SCAM", "SCAM"), row("CAUTION", "CAUTION")]  # fmt: skip
    s = summarise(rows)
    assert s["n"] == 5 and s["correct"] == 3 and s["accuracy"] == 0.6
    assert s["false_safe"] == 1 and s["risky"] == 3 and s["false_safe_rate"] == pytest.approx(1 / 3)
    assert s["false_alarm"] == 1 and s["safe"] == 2 and s["false_alarm_rate"] == 0.5
    assert s["cost_per_check_usd"] == pytest.approx(0.01)


def test_groups_and_confusion():
    rows = [row("SAFE", "SAFE", lang="te"), row("SCAM", "CAUTION", lang="hi")]
    assert by(rows, "lang")["te"]["correct"] == 1 and by(rows, "lang")["hi"]["correct"] == 0
    assert confusion(rows)["SCAM"]["CAUTION"] == 1 and confusion(rows)["SAFE"]["SAFE"] == 1
