"""The labelled dataset (data/synthetic) and the real tools must agree.

Labels are written from intent, not from tool output, so a disagreement means either a
label mistake or a tool bug. Verdicts are checked against the written verdict policy
(data/synthetic/README.md), which the Day 3 risk engine must implement.
"""

from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from app.agent.tools import TOOLS
from app.schemas import EvidenceCode as C
from app.schemas import Label, Verdict

DATA = Path(__file__).resolve().parents[2] / "data" / "synthetic"
LABELS = [
    Label.model_validate_json(line)
    for line in (DATA / "labels.jsonl").read_text(encoding="utf-8").splitlines()
]

STRONG_SCAM = {C.LOOKALIKE_DOMAIN, C.LOOKALIKE_VPA, C.KNOWN_SCAM_DESTINATION, C.APK_LINK}
SCAM_PHRASING = {C.DISCONNECTION_THREAT, C.KYC_UPDATE_LURE, C.REFUND_LURE}
NOT_SAFE = {
    C.UNKNOWN_BILLER, C.CONSUMER_NOT_FOUND, C.AMOUNT_MISMATCH, C.AMOUNT_SPIKE,
    C.DESTINATION_NOT_OFFICIAL, C.SHORT_URL, C.PERSONAL_PHONE_NUMBER,
}  # fmt: skip


def policy_verdict(codes: set[C]) -> Verdict:
    if codes & STRONG_SCAM or (C.DESTINATION_NOT_OFFICIAL in codes and codes & SCAM_PHRASING):
        return Verdict.SCAM
    if {C.BILLER_VERIFIED, C.AMOUNT_MATCHES_BILLER} <= codes and not codes & NOT_SAFE:
        return Verdict.SAFE
    return Verdict.CAUTION


def tool_evidence(label: Label) -> set[tuple[C, str]]:
    """Run the real tools on the label's ground-truth fields, as the agent would."""
    f = label.expected.extracted
    found: set[tuple[C, str]] = set()

    def run(tool: str, /, **args) -> dict:
        result = TOOLS[tool](**args)
        assert result.ok, f"{tool} failed: {result.error}"
        found.update((code, tool) for code in result.codes)
        return result.data

    biller_id = run("lookup_biller", name=f.biller_name, category=f.biller_category).get(
        "biller_id"
    )
    if biller_id and f.consumer_number and f.amount is not None:
        run(
            "fetch_bill",
            biller_id=biller_id,
            consumer_number=f.consumer_number,
            claimed_amount=f.amount,
        )
        run(
            "get_bill_history",
            biller_id=biller_id,
            consumer_number=f.consumer_number,
            current_amount=f.amount,
        )
    for d in f.payment_destinations:
        run("check_payment_destination", kind=d.kind, value=d.value, biller_id=biller_id)
    if label.input.text:
        run("match_scam_patterns", text=label.input.text)
    return found


@pytest.mark.parametrize("label", LABELS, ids=[lbl.id for lbl in LABELS])
def test_tools_agree_with_label(label):
    expected = {(e.code, e.source) for e in label.expected.evidence}
    assert tool_evidence(label) == expected


@pytest.mark.parametrize("label", LABELS, ids=[lbl.id for lbl in LABELS])
def test_verdict_follows_policy(label):
    codes = {e.code for e in label.expected.evidence}
    assert label.expected.verdict == policy_verdict(codes)


def test_dataset_composition():
    assert len(LABELS) == 60
    assert len({lbl.id for lbl in LABELS}) == 60
    verdicts = Counter(lbl.expected.verdict for lbl in LABELS)
    assert (
        verdicts[Verdict.SAFE] >= 15
        and verdicts[Verdict.SCAM] >= 20
        and verdicts[Verdict.CAUTION] >= 10
    )
    scam_langs = Counter(
        lbl.expected.extracted.languages[0] for lbl in LABELS if lbl.id.startswith("scam_")
    )
    assert scam_langs == {"en": 8, "te": 8, "hi": 8}
    splits = Counter(lbl.split for lbl in LABELS)
    assert 0.25 <= splits["test"] / len(LABELS) <= 0.40
    per_scenario = Counter(lbl.scenario for lbl in LABELS)
    for scenario, n in per_scenario.items():
        got = {lbl.split for lbl in LABELS if lbl.scenario == scenario}
        assert got == ({"dev", "test"} if n >= 2 else {"dev"}), scenario
    assert all(lbl.synthetic for lbl in LABELS)


def test_images_exist_and_regions_fit():
    for lbl in LABELS:
        if lbl.input.kind != "image":
            continue
        img = Image.open(DATA / lbl.input.path)
        for region in lbl.expected.regions:
            for x, y in region.polygon:
                assert -1 <= x <= img.width + 1 and -1 <= y <= img.height + 1, lbl.id


def test_everything_is_fictional():
    for lbl in LABELS:
        for d in lbl.expected.extracted.payment_destinations:
            if d.kind == "url":
                host = d.value.split("/")[0]
                assert host.endswith(".example") or host in {"bit.ly", "tinyurl.com", "cutt.ly"}, (
                    d.value
                )
            if d.kind == "upi":
                assert d.value.endswith(("@demobank", "@okdemo")), d.value
