"""Deterministic graders and metrics for an evaluation run. No model is involved in grading.

A row is one check: {"id", "lang", "kind", "scenario", "expected", "got", "expected_codes",
"codes", "latency_s", "cost_usd", ...}. Verdict order: SAFE < CAUTION < SCAM.
"""

import math
import statistics
from typing import Any


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile, so every reported value is a value that was really measured."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(p / 100 * len(ordered)) - 1)]


def grade(row: dict[str, Any]) -> dict[str, bool]:
    expected, got = row["expected"], row["got"]
    return {
        "correct": got == expected,
        # A risky request called SAFE: the failure we care about most.
        "false_safe": expected != "SAFE" and got == "SAFE",
        # A genuine bill not called SAFE: annoying, but no money is lost.
        "false_alarm": expected == "SAFE" and got != "SAFE",
        # A scam only called CAUTION: still "do not pay yet", but weaker than it should be.
        "scam_downgraded": expected == "SCAM" and got == "CAUTION",
        "evidence_found": set(row.get("expected_codes", [])) <= set(row.get("codes", [])),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    graded = [grade(r) for r in rows]
    risky = sum(r["expected"] != "SAFE" for r in rows)
    safe = len(rows) - risky
    count = lambda key: sum(g[key] for g in graded)  # noqa: E731
    latencies = [r["latency_s"] for r in rows if r.get("latency_s") is not None]
    costs = [r["cost_usd"] for r in rows]
    return {
        "n": len(rows),
        "correct": count("correct"),
        "accuracy": count("correct") / len(rows) if rows else None,
        "false_safe": count("false_safe"),
        "risky": risky,
        "false_safe_rate": count("false_safe") / risky if risky else None,
        "false_alarm": count("false_alarm"),
        "safe": safe,
        "false_alarm_rate": count("false_alarm") / safe if safe else None,
        "scam_downgraded": count("scam_downgraded"),
        "evidence_found": count("evidence_found"),
        "latency_p50_s": percentile(latencies, 50),
        "latency_p90_s": percentile(latencies, 90),
        "cost_per_check_usd": sum(costs) / len(costs) if costs else None,
        "cost_total_usd": sum(costs),
    }


def by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row)
    return {name: summarise(group) for name, group in sorted(groups.items())}


def confusion(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    labels = ("SAFE", "CAUTION", "SCAM")
    table = {e: dict.fromkeys(labels, 0) for e in labels}
    for row in rows:
        table[row["expected"]][row["got"]] += 1
    return table


def medians(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [r[key] for r in rows if r.get(key) is not None]
    return statistics.median(values) if values else None
