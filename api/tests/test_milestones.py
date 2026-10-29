import pytest
from dataset_utils import LABELS

from app.agent.milestones import find_destinations, reconcile
from app.schemas import EvidenceCode, PaymentDestination

SCAM_SMS = (
    "Dear Consumer, your Demo Power electricity connection will be disconnected tonight at 9:30 PM. "
    "Contact our officer immediately on +91 90000 00001. Pay now: demopower-bill.example/pay"
)


def test_finds_links_upi_ids_and_mobile_numbers():
    found = find_destinations(
        "Pay to demopower.bill@demobank or https://www.demopower.example/pay. Call 9000000001, "
        "+91 80000 00002 or 0 7000000003? Visit bit.ly/x1."
    )
    assert [(d.kind, d.value) for d in found] == [
        ("upi", "demopower.bill@demobank"),
        ("url", "https://www.demopower.example/pay"),
        ("url", "bit.ly/x1"),
        ("phone", "9000000001"),
        ("phone", "8000000002"),
        ("phone", "7000000003"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Water bill Rs 1,240.00 for K.No. EJB80004604 due on 05-Nov-2026.",
        "Demo Power Distribution Co. Ltd, bill no DPB/2026/10/558213, consumer 1205880911",
        "Toll-free 1800-000-1001. Amount ₹4,243.00. Pay by 9:30 PM.",
    ],
)
def test_ignores_things_that_are_not_destinations(text):
    assert find_destinations(text) == []


def test_link_forgotten_by_extraction_is_added_and_recorded():
    extracted = [PaymentDestination(kind="phone", value="9000000001")]  # model "forgot" the link
    destinations, result = reconcile(SCAM_SMS, extracted)
    assert [d.value for d in destinations] == ["9000000001", "demopower-bill.example/pay"]
    assert result.tool == "milestone_check" and result.codes == {EvidenceCode.MISSED_BY_EXTRACTION}
    assert "demopower-bill.example/pay" in result.evidence[0].summary


def test_formatting_differences_are_not_misses():
    extracted = [
        PaymentDestination(kind="phone", value="+91 90000 00001"),
        PaymentDestination(kind="url", value="https://demopower-bill.example"),
    ]
    destinations, result = reconcile(SCAM_SMS, extracted)
    assert result is None and destinations == extracted


def test_missed_phone_numbers_are_masked_in_the_record():
    _, result = reconcile("Call 9000000001 now", [])
    assert "9000000001" not in result.model_dump_json()


@pytest.mark.parametrize("label", [lbl for lbl in LABELS if lbl.input.text], ids=lambda lbl: lbl.id)
def test_no_false_misses_on_the_dataset(label):
    """Ground-truth destinations are complete, so the milestone check must find nothing extra."""
    _, result = reconcile(label.input.text, label.expected.extracted.payment_destinations)
    assert result is None, [e.summary for e in result.evidence]
