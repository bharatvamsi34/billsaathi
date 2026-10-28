import pytest
from pydantic import ValidationError

from app.agent.evidence import EvidenceRecord
from app.agent.tools import TOOLS
from app.agent.tools.check_payment_destination import check_payment_destination, skeleton
from app.agent.tools.fetch_bill import fetch_bill
from app.agent.tools.get_bill_history import get_bill_history
from app.agent.tools.lookup_biller import lookup_biller
from app.agent.tools.match_scam_patterns import match_scam_patterns
from app.bbps_mock import service
from app.facts import FACTS, verified_fact
from app.schemas import EvidenceCode as C

DEMO = "DEMO00000MAH01"
DEMO_CONSUMER = "DP-4410-882761"


# --- lookup_biller ---


@pytest.mark.parametrize(
    "name,category,biller_id",
    [
        ("Demo Power Distribution Co. Ltd", "electricity", DEMO),
        ("DEMO POWER", None, DEMO),
        ("Demo Powr Distribution", "electricity", DEMO),  # typo
        ("డెమో", None, None),
        ("శాంపిల్ విద్యుత్ సేవ", None, "SVSL00000TEL01"),
        ("एग्ज़ाम्पल बिजली निगम", "electricity", "EBNL00000UTP01"),
        ("SkyDemo DTH", "dth", "SKYD00000NAT01"),
        ("Electricity Office", "electricity", None),
        ("Demo", None, None),
    ],
)
def test_lookup_biller(name, category, biller_id):
    r = lookup_biller(name=name, category=category)
    assert r.ok
    if biller_id is None:
        assert r.codes == {C.UNKNOWN_BILLER}
    else:
        assert r.codes == {C.BILLER_VERIFIED}
        assert r.data["biller_id"] == biller_id


def test_lookup_biller_without_name_or_with_wrong_category():
    assert lookup_biller(name=None).codes == {C.UNKNOWN_BILLER}
    r = lookup_biller(name="Demo Power", category="water")
    assert r.codes == {C.UNKNOWN_BILLER}
    assert "closest is Demo Power" in r.evidence[0].summary


# --- fetch_bill ---


def test_fetch_bill_amounts():
    assert fetch_bill(biller_id=DEMO, consumer_number=DEMO_CONSUMER, claimed_amount=1240).codes == {
        C.AMOUNT_MATCHES_BILLER
    }
    assert fetch_bill(
        biller_id=DEMO, consumer_number=DEMO_CONSUMER, claimed_amount=1240.5
    ).codes == {C.AMOUNT_MATCHES_BILLER}
    r = fetch_bill(biller_id=DEMO, consumer_number=DEMO_CONSUMER, claimed_amount=4240)
    assert r.codes == {C.AMOUNT_MISMATCH}
    assert r.evidence[0].detail == {"biller_amount": 1240.0, "claimed_amount": 4240.0}
    assert "₹1,240.00" in r.evidence[0].summary


def test_fetch_bill_without_claim_or_consumer():
    r = fetch_bill(biller_id=DEMO, consumer_number=DEMO_CONSUMER)
    assert r.ok and r.evidence == () and r.data["biller_amount"] == 1240.0
    assert fetch_bill(biller_id=DEMO, consumer_number="DP-0000-000000").codes == {
        C.CONSUMER_NOT_FOUND
    }
    r = fetch_bill(biller_id="NOPE", consumer_number=DEMO_CONSUMER)
    assert not r.ok and "unknown biller_id" in r.error


# --- check_payment_destination ---

NOT = C.DESTINATION_NOT_OFFICIAL


@pytest.mark.parametrize(
    "kind,value,biller_id,codes",
    [
        # official channels
        ("url", "https://demopower.example/pay", DEMO, {C.DESTINATION_OFFICIAL}),
        ("url", "www.demopower.example", None, {C.DESTINATION_OFFICIAL}),
        ("url", "pay.demopower.example/bill", DEMO, {C.DESTINATION_OFFICIAL}),
        ("upi", "DemoPower.Bill@DemoBank", DEMO, {C.DESTINATION_OFFICIAL}),
        ("phone", "1800-000-1001", DEMO, {C.DESTINATION_OFFICIAL}),
        (
            "qr",
            "upi://pay?pa=demopower.bill@demobank&pn=Demo%20Power&am=1240",
            DEMO,
            {C.DESTINATION_OFFICIAL},
        ),
        # lookalike domains
        ("url", "dem0power-update.example/pay", DEMO, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "demopovver.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "dernopower.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "demo-power.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "demopowerr.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "dеmopower.example", None, {C.LOOKALIKE_DOMAIN, NOT}),  # Cyrillic е
        ("url", "demopower.example.bill-pay.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "sample-vidyut-kyc.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        ("url", "examp1ebijli.example", None, {C.LOOKALIKE_DOMAIN, NOT}),
        # other risky links
        (
            "url",
            "demopower-kyc.example/DemoPower_KYC.apk",
            None,
            {C.APK_LINK, C.LOOKALIKE_DOMAIN, NOT},
        ),
        ("url", "https://bit.ly/3xYz", None, {C.SHORT_URL, NOT}),
        ("url", "kyc-update-portal.example/login", None, {C.KNOWN_SCAM_DESTINATION, NOT}),
        ("url", "unrelated-shop.example", None, {NOT}),
        # another biller's official site is not this biller's channel
        ("url", "demogas.example/pay", DEMO, {NOT}),
        # UPI
        ("upi", "demopower.bill@okdemo", DEMO, {C.LOOKALIKE_VPA, NOT}),
        ("upi", "dem0power.bi11@demobank", None, {C.LOOKALIKE_VPA, NOT}),
        ("upi", "electricityofficer@okdemo", DEMO, {C.KNOWN_SCAM_DESTINATION, NOT}),
        ("upi", "ramesh.k@okdemo", DEMO, {NOT}),
        ("upi", "not a vpa", DEMO, {NOT}),
        # phones
        ("phone", "+91 90000 00000", DEMO, {C.PERSONAL_PHONE_NUMBER, NOT}),
        ("phone", "09876500001", DEMO, {C.KNOWN_SCAM_DESTINATION, C.PERSONAL_PHONE_NUMBER, NOT}),
        ("phone", "1800-000-1002", DEMO, {NOT}),  # another biller's helpline
    ],
)
def test_check_payment_destination(kind, value, biller_id, codes):
    r = check_payment_destination(kind=kind, value=value, biller_id=biller_id)
    assert r.ok, r.error
    assert r.codes == codes


@pytest.mark.parametrize(
    "host",
    ["google.com", "paytm.com", "phonepe.com", "amazon.in", "sbi.co.in", "irctc.co.in",
     "example.com", "demo.example", "power.example", "mygas.example", "skyline.example"],
)  # fmt: skip
def test_ordinary_domains_are_not_called_lookalikes(host):
    assert check_payment_destination(kind="url", value=host).codes == {NOT}


def test_destination_lookalike_detail_and_phone_masking():
    r = check_payment_destination(kind="url", value="dem0power-update.example/pay")
    assert r.data["lookalike_of"] == "demopower.example"
    r = check_payment_destination(kind="phone", value="+91 90000 00000")
    assert "9000000000" not in str(r.model_dump())  # the full number never appears in evidence


def test_destination_unknown_biller_is_a_tool_error():
    r = check_payment_destination(kind="url", value="demopower.example", biller_id="NOPE")
    assert not r.ok and "unknown biller_id" in r.error


def test_skeleton():
    assert skeleton("Dem0-P0wer") == skeleton("demopower")
    assert skeleton("dernopower") == skeleton("demopower")


# --- get_bill_history ---


def test_bill_history_spike_and_normal():
    spike_consumer = service.consumers("EBNL00000UTP01")[0]
    r = get_bill_history(biller_id="EBNL00000UTP01", consumer_number=spike_consumer)
    assert r.codes == {C.AMOUNT_SPIKE} and r.data["ratio"] >= 2
    assert get_bill_history(biller_id=DEMO, consumer_number=DEMO_CONSUMER).codes == {
        C.AMOUNT_WITHIN_HISTORY
    }
    # a tampered amount on a genuine consumer also stands out against history
    r = get_bill_history(biller_id=DEMO, consumer_number=DEMO_CONSUMER, current_amount=4240)
    assert r.codes == {C.AMOUNT_SPIKE}
    assert get_bill_history(biller_id=DEMO, consumer_number="DP-0000-000000").codes == {
        C.CONSUMER_NOT_FOUND
    }
    assert not get_bill_history(biller_id="NOPE", consumer_number="x").ok


# --- match_scam_patterns ---


@pytest.mark.parametrize(
    "text,codes",
    [
        (
            "Dear Consumer, your electricity power will be disconnected tonight at 9:30 PM. "
            "Please immediately contact our officer.",
            {C.DISCONNECTION_THREAT, C.URGENCY_PRESSURE},
        ),
        ("Aapka KYC update nahi hua, aaj raat connection cut ho jayega", {C.KYC_UPDATE_LURE, C.URGENCY_PRESSURE, C.DISCONNECTION_THREAT}),
        ("आपका बिजली कनेक्शन आज रात काट दिया जाएगा। तुरंत संपर्क करें", {C.DISCONNECTION_THREAT, C.URGENCY_PRESSURE}),
        ("మీ కరెంట్ కనెక్షన్ ఈ రాత్రి కట్ చేయబడుతుంది. వెంటనే చెల్లించండి", {C.DISCONNECTION_THREAT, C.URGENCY_PRESSURE}),
        ("You were overcharged last month. Claim your refund of Rs 840 here", {C.REFUND_LURE}),
        ("అదనంగా చెల్లించిన డబ్బు తిరిగి పొందండి", {C.REFUND_LURE}),
        (
            "Dear Consumer, your Demo Power bill for Sep-2026 of Rs 1,240.00 is due on 05-Nov-2026. "
            "Pay via the official Demo Power app. Ignore if already paid.",
            set(),
        ),
    ],
)  # fmt: skip
def test_match_scam_patterns(text, codes):
    r = match_scam_patterns(text=text)
    assert r.ok
    assert r.codes == codes


def test_words_inside_links_and_upi_ids_are_not_phrasing():
    text = "Pay at https://kyc-update-portal.example/refund or to billupdate.refund@okdemo. Thanks."
    assert match_scam_patterns(text=text).codes == set()
    assert match_scam_patterns(text="Claim your refund at bijli-refund.example").codes == {
        C.REFUND_LURE
    }


# --- shared contract ---


def test_evidence_ids_are_stable_and_argument_specific():
    a = check_payment_destination(kind="url", value="dem0power-update.example/pay")
    b = check_payment_destination(kind="url", value="dem0power-update.example/pay")
    c = check_payment_destination(kind="url", value="demopovver.example")
    assert [e.evidence_id for e in a.evidence] == [e.evidence_id for e in b.evidence]
    assert a.call_id == b.call_id != c.call_id
    assert not {e.evidence_id for e in a.evidence} & {e.evidence_id for e in c.evidence}
    assert all(e.evidence_id.startswith("ev_") and e.source == a.tool for e in a.evidence)


def test_invalid_arguments_and_internal_errors_never_raise(monkeypatch):
    r = fetch_bill(biller_id=DEMO)  # consumer_number missing
    assert not r.ok and r.error.startswith("invalid arguments")
    r = check_payment_destination(kind="carrier-pigeon", value="x")
    assert not r.ok
    tool = TOOLS["get_bill_history"]

    def boom(args):
        raise ZeroDivisionError

    monkeypatch.setattr(tool, "fn", boom)
    r = tool(biller_id=DEMO, consumer_number=DEMO_CONSUMER)
    assert not r.ok and r.error == "internal error: ZeroDivisionError" and r.evidence == ()


def test_tool_specs_are_function_calling_ready():
    assert set(TOOLS) == {
        "lookup_biller",
        "fetch_bill",
        "check_payment_destination",
        "get_bill_history",
        "match_scam_patterns",
    }
    for tool in TOOLS.values():
        spec = tool.spec()
        assert spec["parameters"]["type"] == "object" and spec["description"]


def test_evidence_record_is_append_only_and_knows_this_runs_evidence():
    record = EvidenceRecord("run-1")
    r = check_payment_destination(kind="url", value="dem0power-update.example/pay")
    entry = record.add_tool_result(r)
    record.append("refusal", {"reason": "cited unknown evidence"})
    assert [e.seq for e in record.entries] == [0, 1]
    assert entry.kind == "tool_result"
    assert record.evidence(r.evidence[0].evidence_id) == r.evidence[0]
    assert record.evidence("ev_made_up_by_model") is None
    entries = record.entries
    assert isinstance(entries, tuple)  # callers cannot mutate the log
    with pytest.raises(ValidationError):
        entries[0].kind = "verdict"  # entries are frozen


def test_only_verified_facts_are_usable(monkeypatch):
    assert verified_fact("cybercrime_helpline").value == "1930"
    assert verified_fact("cybercrime_portal").value == "https://cybercrime.gov.in"
    assert all(f.verified for f in FACTS.values())
    assert verified_fact("made_up_fact") is None
    unverified = FACTS["cybercrime_helpline"].model_copy(update={"verified_by": None})
    monkeypatch.setitem(FACTS, "cybercrime_helpline", unverified)
    assert verified_fact("cybercrime_helpline") is None
