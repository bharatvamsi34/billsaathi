"""The live events quote real evidence values for the screen, masked and by allowlist."""

from datetime import UTC, datetime

from app.agent.evidence import RecordEntry
from app.agent.tools import TOOLS
from app.api.events import public_event


def _event(tool: str, secrets: list[str] = (), **args):
    result = TOOLS[tool](**args)
    entry = RecordEntry(
        seq=0,
        kind="tool_result",
        at=datetime.now(UTC),
        payload={**result.model_dump(mode="json"), "origin": "mandatory"},
    )
    return public_event(entry, list(secrets))


def test_amount_mismatch_carries_both_amounts_and_masks_the_consumer():
    e = _event(
        "fetch_bill",
        biller_id="DEMO00000MAH01",
        consumer_number="DP-4410-882761",
        claimed_amount=4240.0,
    )
    detail = e["evidence"][0]["detail"]
    assert detail["claimed_amount"] == 4240.0
    assert detail["biller_amount"] == 1240.0
    assert e["record"]["amount"] == 1240.0
    assert "882761" not in str(e)


def test_lookup_gives_the_official_channels_and_only_when_matched():
    e = _event("lookup_biller", name="Demo Power Distribution Co. Ltd")
    assert e["record"]["name"] == "Demo Power Distribution Co. Ltd"
    assert "demopower.bill@demobank" in e["record"]["vpas"]
    assert _event("lookup_biller", name="Nobody Power")["record"] is None


def test_scam_phrases_are_short_masked_and_not_the_whole_message():
    text = "Your power will be cut tonight. Call 9000000003 now. " + "x" * 300
    e = _event("match_scam_patterns", text=text)
    phrases = [p for ev in e["evidence"] for p in ev["detail"].get("phrases", [])]
    assert phrases
    assert all(len(p) <= 80 for p in phrases)
    assert "9000000003" not in str(e)
    assert text not in str(e)


def test_destination_detail_keeps_the_value_but_never_a_full_phone():
    upi = _event("check_payment_destination", kind="upi", value="electricityofficer@okdemo")
    assert upi["evidence"][0]["detail"]["vpa"] == "electricityofficer@okdemo"
    phone = _event("check_payment_destination", kind="phone", value="9000000003")
    assert "9000000003" not in str(phone)


def test_unknown_detail_keys_stay_private():
    entry = RecordEntry(
        seq=0,
        kind="tool_result",
        at=datetime.now(UTC),
        payload={
            "tool": "fetch_bill",
            "ok": True,
            "args": {},
            "data": {},
            "evidence": [
                {
                    "evidence_id": "ev_1",
                    "code": "AMOUNT_MISMATCH",
                    "summary": "s",
                    "detail": {"biller_amount": 1.0, "consumer_name": "Secret Person"},
                }
            ],
        },
    )
    assert "Secret Person" not in str(public_event(entry))


def test_judge_events_name_the_evidence_and_verdicts_the_floor():
    judge = RecordEntry(
        seq=0,
        kind="judge",
        at=datetime.now(UTC),
        payload={
            "accepted": True,
            "reasons": [{"reason": "r", "supported": True, "why": "w", "evidence_ids": ["ev_1"]}],
        },
    )
    assert public_event(judge)["reasons"][0]["evidence_ids"] == ["ev_1"]
    verdict = RecordEntry(
        seq=1,
        kind="verdict",
        at=datetime.now(UTC),
        payload={"verdict": "SCAM", "reasons": [], "floor": {"verdict": "SCAM", "rule": "x"}},
    )
    assert public_event(verdict)["floor"] == "SCAM"
