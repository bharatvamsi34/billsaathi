import pytest
from dataset_utils import LABELS, run_tools

from app.agent.tools import TOOLS
from app.risk.policy import (
    Floor,
    at_least,
    final_floor,
    floor_verdict,
    safe_requirements,
    stricter,
)
from app.schemas import PaymentDestination, Verdict

DEMO = "DEMO00000MAH01"
DEMO_CONSUMER = "DP-4410-882761"
OFFICIAL_UPI = PaymentDestination(kind="upi", value="demopower.bill@demobank")


def ev(*results):
    return [e for r in results for e in r.evidence]


def genuine_results(amount: float = 1240.0, destinations=(OFFICIAL_UPI,)):
    results = [TOOLS["lookup_biller"](name="Demo Power", category="electricity")]
    results += [
        TOOLS["check_payment_destination"](kind=d.kind, value=d.value) for d in destinations
    ]
    results += [
        TOOLS["fetch_bill"](biller_id=DEMO, consumer_number=DEMO_CONSUMER, claimed_amount=amount),
        TOOLS["get_bill_history"](
            biller_id=DEMO, consumer_number=DEMO_CONSUMER, current_amount=amount
        ),
    ]
    return results


def test_severity_order():
    assert at_least(Verdict.SCAM, Verdict.CAUTION) and at_least(Verdict.CAUTION, Verdict.CAUTION)
    assert not at_least(Verdict.SAFE, Verdict.CAUTION) and not at_least(
        Verdict.CAUTION, Verdict.SCAM
    )


def test_final_floor_and_stricter():
    safe = Floor(verdict=Verdict.SAFE, rule="no_risk_found", evidence_ids=[])
    scam = Floor(verdict=Verdict.SCAM, rule="strong_scam_signal", evidence_ids=["ev_x"])
    assert final_floor(safe, []) == Verdict.SAFE
    assert (
        final_floor(safe, ["amount in line with bill history (not shown by any tool)"])
        == Verdict.CAUTION
    )
    assert final_floor(scam, ["anything"]) == Verdict.SCAM
    assert stricter(Verdict.SAFE, Verdict.SCAM) == Verdict.SCAM


def test_floor_rules():
    lookalike = TOOLS["check_payment_destination"](kind="url", value="dem0power-update.example/pay")
    f = floor_verdict(ev(lookalike))
    assert f.verdict == Verdict.SCAM and f.rule == "strong_scam_signal"
    assert set(f.evidence_ids) == {
        e.evidence_id for e in lookalike.evidence if e.code == "LOOKALIKE_DOMAIN"
    }

    phone = TOOLS["check_payment_destination"](kind="phone", value="9000000001")
    threat = TOOLS["match_scam_patterns"](text="Your power supply will be cut tonight")
    assert floor_verdict(ev(phone)).verdict == Verdict.CAUTION  # unofficial number alone
    assert floor_verdict(ev(phone, threat)) == Floor(
        verdict=Verdict.SCAM,
        rule="unofficial_destination_with_scam_wording",
        evidence_ids=[e.evidence_id for e in phone.evidence if e.code == "DESTINATION_NOT_OFFICIAL"]
        + [e.evidence_id for e in threat.evidence if e.code == "DISCONNECTION_THREAT"],
    )
    assert floor_verdict(ev(threat)).verdict == Verdict.SAFE  # wording alone sets no floor
    assert floor_verdict([]).verdict == Verdict.SAFE
    assert floor_verdict([], tool_failures=1) == Floor(
        verdict=Verdict.CAUTION, rule="could_not_verify", evidence_ids=[]
    )
    tampered = TOOLS["fetch_bill"](
        biller_id=DEMO, consumer_number=DEMO_CONSUMER, claimed_amount=4240
    )
    assert floor_verdict(ev(tampered)).rule == "hard_check_failed"


def test_safe_requirements_all_met():
    assert safe_requirements(genuine_results(), [OFFICIAL_UPI]) == []


@pytest.mark.parametrize(
    "case,expected_fragment",
    [
        ("tampered", "risk evidence found"),
        ("unchecked_destination", "destination not checked"),
        ("other_billers_site", "belongs to another biller"),
        ("no_history", "bill history"),
        ("tool_failure", "a tool call failed"),
        ("low_confidence", "low extraction confidence on amount"),
    ],
)
def test_safe_requirements_block_safe(case, expected_fragment):
    destinations = [OFFICIAL_UPI]
    low = []
    results = genuine_results()
    if case == "tampered":
        results = genuine_results(amount=4240)
    elif case == "unchecked_destination":
        destinations = [OFFICIAL_UPI, PaymentDestination(kind="url", value="demopower.example/pay")]
    elif case == "other_billers_site":
        other = PaymentDestination(kind="url", value="demogas.example/pay")
        destinations = [other]
        results = genuine_results(destinations=[other])
    elif case == "no_history":
        results = [r for r in results if r.tool != "get_bill_history"]
    elif case == "tool_failure":
        results = [*results, TOOLS["fetch_bill"](biller_id="NOPE", consumer_number="x")]
    elif case == "low_confidence":
        low = ["amount"]
    missing = safe_requirements(results, destinations, low)
    assert any(expected_fragment in m for m in missing), missing


def test_destination_matching_ignores_formatting():
    results = genuine_results(
        destinations=[PaymentDestination(kind="url", value="https://www.demopower.example/pay/")]
    )
    assert (
        safe_requirements(results, [PaymentDestination(kind="url", value="demopower.example/pay")])
        == []
    )


@pytest.mark.parametrize("label", LABELS, ids=[lbl.id for lbl in LABELS])
def test_risk_engine_reproduces_every_label(label):
    """Floor + SAFE checklist on the real tool results must give the hand-assigned verdict."""
    results = run_tools(label)
    floor = floor_verdict(ev(*results), tool_failures=sum(not r.ok for r in results))
    missing = safe_requirements(results, label.expected.extracted.payment_destinations)
    assert final_floor(floor, missing) == label.expected.verdict, (floor, missing)
