"""Shared helpers for tests that use the labelled dataset in data/synthetic."""

from pathlib import Path

from app.agent.evidence import ToolResult
from app.agent.tools import TOOLS
from app.schemas import Label

DATA = Path(__file__).resolve().parents[2] / "data" / "synthetic"
LABELS = [
    Label.model_validate_json(line)
    for line in (DATA / "labels.jsonl").read_text(encoding="utf-8").splitlines()
]


def first_wave(label: Label) -> list[tuple[str, dict]]:
    """Checks that need nothing but the extracted fields (one parallel model turn)."""
    f = label.expected.extracted
    calls = [("lookup_biller", {"name": f.biller_name, "category": f.biller_category})]
    calls += [
        ("check_payment_destination", {"kind": d.kind, "value": d.value})
        for d in f.payment_destinations
    ]
    if label.input.text:
        calls.append(("match_scam_patterns", {"text": label.input.text}))
    return calls


def second_wave(label: Label, biller_id: str | None) -> list[tuple[str, dict]]:
    """Checks that need the biller_id from lookup_biller."""
    f = label.expected.extracted
    if not (biller_id and f.consumer_number and f.amount is not None):
        return []
    common = {"biller_id": biller_id, "consumer_number": f.consumer_number}
    return [
        ("fetch_bill", common | {"claimed_amount": f.amount}),
        ("get_bill_history", common | {"current_amount": f.amount}),
    ]


def run_tools(label: Label) -> list[ToolResult]:
    """Run the real tools on the label's ground-truth fields, as the agent would."""
    results = [TOOLS[name](**args) for name, args in first_wave(label)]
    biller_id = results[0].data.get("biller_id")
    results += [TOOLS[name](**args) for name, args in second_wave(label, biller_id)]
    return results
