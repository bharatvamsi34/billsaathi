"""Generate the synthetic evaluation dataset: data/synthetic/labels.jsonl + images/.

Every item states its INTENT: which biller it names, whether its amount is genuine or
tampered, what each payment destination is meant to be (official, lookalike, ...), which
scam phrasings it uses, and a hand-assigned verdict. Expected evidence codes come from that
intent through the fixed DEST_CODES table below, NOT from running the tools.
api/tests/test_dataset.py then runs the real tools and checks they agree with the labels.

Everything is synthetic: fictional billers (*.example, @demobank), fictional consumers.

Run from the repo root:  api\\.venv\\Scripts\\python data\\generators\\make_dataset.py
"""

import shutil
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(Path(__file__).parent))

from render import box_to_polygon, esc, make_photo, render_html  # noqa: E402

from app.bbps_mock import service  # noqa: E402
from app.bbps_mock.registry import BY_ID, Biller  # noqa: E402
from app.schemas import (  # noqa: E402
    BillerCategory,
    BillFields,
    Channel,
    DestinationKind,
    Evidence,
    EvidenceCode,
    Expected,
    InputKind,
    Label,
    LabelInput,
    PaymentDestination,
    Region,
    Verdict,
)

OUT = ROOT / "data" / "synthetic"
IMAGES = OUT / "images"

C = EvidenceCode
U, L = DestinationKind.UPI, DestinationKind.URL
P = DestinationKind.PHONE

# Intent of a payment destination -> evidence check_payment_destination must report.
DEST_CODES: dict[str, set[EvidenceCode]] = {
    "official": {C.DESTINATION_OFFICIAL},
    "lookalike_url": {C.LOOKALIKE_DOMAIN, C.DESTINATION_NOT_OFFICIAL},
    "lookalike_apk": {C.APK_LINK, C.LOOKALIKE_DOMAIN, C.DESTINATION_NOT_OFFICIAL},
    "known_scam": {C.KNOWN_SCAM_DESTINATION, C.DESTINATION_NOT_OFFICIAL},
    "short_url": {C.SHORT_URL, C.DESTINATION_NOT_OFFICIAL},
    "personal_phone": {C.PERSONAL_PHONE_NUMBER, C.DESTINATION_NOT_OFFICIAL},
    "lookalike_vpa": {C.LOOKALIKE_VPA, C.DESTINATION_NOT_OFFICIAL},
    "other_vpa": {C.DESTINATION_NOT_OFFICIAL},
}
AMOUNT_CODES = {
    "match": C.AMOUNT_MATCHES_BILLER,
    "tampered": C.AMOUNT_MISMATCH,
    "unknown_consumer": C.CONSUMER_NOT_FOUND,
}
HISTORY_CODES = {
    "normal": C.AMOUNT_WITHIN_HISTORY,
    "spike": C.AMOUNT_SPIKE,
    "unknown_consumer": C.CONSUMER_NOT_FOUND,
}

# Bill layout and wording per biller (local language for headings, None = English only).
LOCAL = {
    "DEMO00000MAH01": "hi",
    "SVSL00000TEL01": "te",
    "EBNL00000UTP01": "hi",
    "EJBD00000DEL01": "hi",
}
COLORS = {
    "DEMO00000MAH01": "#1f4e9c",
    "SVSL00000TEL01": "#a33b20",
    "EBNL00000UTP01": "#0f6b3a",
    "EJBD00000DEL01": "#0b6e8a",
    "DGAS00000GUJ01": "#b5651d",
    "DMOB00000NAT01": "#6a1b9a",
    "SKYD00000NAT01": "#283593",
    "FIBR00000KAR01": "#00838f",
}
CITY = {
    "DEMO00000MAH01": "Pune 411001",
    "SVSL00000TEL01": "Hyderabad 500001",
    "EBNL00000UTP01": "Lucknow 226001",
    "EJBD00000DEL01": "New Delhi 110001",
    "DGAS00000GUJ01": "Ahmedabad 380001",
    "DMOB00000NAT01": "Mumbai 400001",
    "SKYD00000NAT01": "Mumbai 400050",
    "FIBR00000KAR01": "Bengaluru 560001",
}
DOC_TITLE = {
    BillerCategory.ELECTRICITY: ("ELECTRICITY BILL", {"hi": "बिजली बिल", "te": "విద్యుత్ బిల్లు"}),
    BillerCategory.WATER: ("WATER BILL", {"hi": "पानी का बिल"}),
    BillerCategory.GAS: ("GAS BILL", {}),
    BillerCategory.MOBILE_POSTPAID: ("POSTPAID BILL", {}),
    BillerCategory.DTH: ("DTH SUBSCRIPTION", {}),
    BillerCategory.BROADBAND: ("BROADBAND BILL", {}),
}
ROW_LABELS = {
    "en": {
        "name": "Consumer Name", "consumer": "Consumer No.", "address": "Address",
        "period": "Billing Period", "usage": "Usage", "plan": "Plan", "bill_date": "Bill Date",
        "due_date": "Due Date", "amount": "Amount Payable", "pay": "Pay only via official channels",
    },
    "hi": {
        "name": "उपभोक्ता का नाम", "consumer": "उपभोक्ता क्रमांक", "address": "पता",
        "period": "बिलिंग अवधि", "usage": "खपत", "plan": "प्लान", "bill_date": "बिल दिनांक",
        "due_date": "देय तिथि", "amount": "देय राशि", "pay": "केवल आधिकारिक माध्यम से भुगतान करें",
    },
    "te": {
        "name": "వినియోగదారుని పేరు", "consumer": "సర్వీస్ నంబర్", "address": "చిరునామా",
        "period": "బిల్లింగ్ కాలం", "usage": "వినియోగం", "plan": "ప్లాన్", "bill_date": "బిల్లు తేదీ",
        "due_date": "చెల్లింపు గడువు తేదీ", "amount": "చెల్లించవలసిన మొత్తం",
        "pay": "అధికారిక మార్గాల ద్వారా మాత్రమే చెల్లించండి",
    },
}  # fmt: skip


def money(amount: float) -> str:
    return f"{amount:,.2f}"


def day(d: date) -> str:
    return d.strftime("%d-%b-%Y")


@dataclass
class Item:
    id: str
    scenario: str
    channel: Channel
    verdict: Verdict
    languages: list[str]
    biller: Biller | None = None  # registered biller named by the item (None -> UNKNOWN_BILLER)
    biller_name: str | None = None  # as written
    category: BillerCategory | None = None
    consumer: str | None = None
    amount: float | None = None
    amount_intent: str | None = None
    history_intent: str | None = None
    destinations: list[tuple[DestinationKind, str, str]] = field(default_factory=list)
    patterns: set[EvidenceCode] = field(default_factory=set)
    text: str | None = None
    due: date | None = None
    bill_date: date | None = None
    urgency: bool = False
    image: str | None = None
    regions: list[Region] = field(default_factory=list)

    def evidence(self) -> list[Evidence]:
        ev = {(C.BILLER_VERIFIED if self.biller else C.UNKNOWN_BILLER, "lookup_biller")}
        if self.biller and self.consumer:
            if self.amount_intent:
                ev.add((AMOUNT_CODES[self.amount_intent], "fetch_bill"))
            if self.history_intent:
                ev.add((HISTORY_CODES[self.history_intent], "get_bill_history"))
        for _, _, intent in self.destinations:
            ev |= {(code, "check_payment_destination") for code in DEST_CODES[intent]}
        ev |= {(code, "match_scam_patterns") for code in self.patterns}
        return [Evidence(code=c, source=s) for c, s in sorted(ev, key=lambda x: (x[1], x[0].value))]

    def label(self, split: str) -> Label:
        fields = BillFields(
            biller_name=self.biller_name,
            biller_category=self.category,
            consumer_number=self.consumer,
            amount=self.amount,
            due_date=self.due,
            bill_date=self.bill_date,
            payment_destinations=[PaymentDestination(kind=k, value=v) for k, v, _ in self.destinations],
            languages=self.languages,
            urgency_language=self.urgency,
        )
        return Label(
            id=self.id,
            scenario=self.scenario,
            input=LabelInput(
                kind=InputKind.IMAGE if self.image else InputKind.TEXT,
                channel=self.channel,
                path=f"images/{self.image}" if self.image else None,
                text=self.text,
            ),
            expected=Expected(
                extracted=fields, verdict=self.verdict, evidence=self.evidence(), regions=self.regions
            ),
            split=split,
        )


def consumer(biller_id: str, idx: int) -> str:
    return service.consumers(biller_id)[idx]


def usual(biller_id: str, idx: int) -> float:
    return statistics.median(b.amount for b in service.bill_history(biller_id, consumer(biller_id, idx)))


# --- bills (images) ---


def bill_item(
    item_id: str,
    scenario: str,
    biller_id: str,
    idx: int,
    verdict: Verdict,
    *,
    history: str = "normal",
    amount: float | None = None,
    vpa: tuple[str, str] | None = None,
    photo_seed: int | None = None,
    layout: str = "layout-a",
) -> Item:
    biller = BY_ID[biller_id]
    c = consumer(biller_id, idx)
    bill = service.current_bill(biller_id, c)
    shown = amount if amount is not None else bill.amount
    local = LOCAL.get(biller_id)
    labels = ROW_LABELS["en"]

    def lab(key: str) -> str:
        return esc(labels[key] + (f" / {ROW_LABELS[local][key]}" if local else ""))

    usage = {
        BillerCategory.ELECTRICITY: f"{round(bill.amount / 7.2)} kWh",
        BillerCategory.WATER: f"{round(bill.amount / 25)} KL",
        BillerCategory.GAS: f"{round(bill.amount / 48)} SCM",
    }.get(biller.category)
    rows = [
        (lab("name"), esc(bill.consumer_name)),
        (lab("consumer"), f"<b>{esc(c)}</b>"),
        (lab("address"), esc(f"{10 + idx * 7}, Demo Nagar, {CITY[biller_id]}")),
        (lab("period"), esc(f"{day(bill.period_start)} to {day(bill.period_end)}")),
        (lab("usage"), esc(usage)) if usage else (lab("plan"), esc("Monthly plan")),
        (lab("bill_date"), esc(day(bill.bill_date))),
        (lab("due_date"), f"<b>{esc(day(bill.due_date))}</b>"),
        (lab("amount"), f'<span class="amount" data-region="amount">₹ {esc(money(shown))}</span>'),
    ]
    vpa_value, vpa_intent = vpa or (biller.official_vpas[0], "official")
    site = f"{biller.official_domains[0]}/pay"
    title, local_titles = DOC_TITLE[biller.category]
    local_alias = next((a for a in biller.aliases if not a.isascii()), "")
    local_line = " · ".join(x for x in (local_alias, local_titles.get(local or "", "")) if x)
    values = {
        "color": COLORS[biller_id],
        "layout": layout,
        "biller_name": esc(biller.name),
        "local_line": esc(local_line),
        "doc_title": esc(title),
        "bill_no": esc(bill.bill_number),
        "rows": "".join(f'<tr><td class="k">{k}</td><td>{v}</td></tr>' for k, v in rows),
        "pay_html": f"{lab('pay')}:<br>UPI: <b>{esc(vpa_value)}</b> &nbsp;·&nbsp; Website: <b>{esc(site)}</b>"
        f"<br>BBPS Biller ID: {esc(biller.biller_id)}",
    }
    name = f"{item_id}.png"
    regions_px = render_html("bill.html", values, (800, 1000), IMAGES / name)
    regions = [Region(kind="amount", polygon=box_to_polygon(regions_px["amount"]))]
    if photo_seed is not None:
        photo = f"{item_id}.jpg"
        corners = make_photo(IMAGES / name, IMAGES / photo, photo_seed)
        (IMAGES / name).unlink()
        name, regions = photo, [Region(kind="document", polygon=corners)]
    return Item(
        id=item_id,
        scenario=scenario,
        channel=Channel.PAPER_BILL,
        verdict=verdict,
        languages=["en", local] if local else ["en"],
        biller=biller,
        biller_name=biller.name,
        category=biller.category,
        consumer=c,
        amount=shown,
        amount_intent="tampered" if amount is not None else "match",
        history_intent=history,
        destinations=[(U, vpa_value, vpa_intent), (L, site, "official")],
        due=bill.due_date,
        bill_date=bill.bill_date,
        image=name,
        regions=regions,
    )


# --- messages (text, some rendered as screenshots) ---


def message_item(
    item_id: str,
    scenario: str,
    channel: Channel,
    verdict: Verdict,
    languages: list[str],
    text: str,
    *,
    biller_id: str | None = None,
    biller_name: str | None = None,
    category: BillerCategory | None = None,
    consumer_no: str | None = None,
    amount: float | None = None,
    amount_intent: str | None = None,
    history_intent: str | None = None,
    destinations: list[tuple[DestinationKind, str, str]] = (),
    patterns: set[EvidenceCode] = frozenset(),
    due: date | None = None,
    urgency: bool = False,
    screenshot: tuple[str, str] | None = None,  # (sender, time)
) -> Item:
    biller = BY_ID[biller_id] if biller_id else None
    item = Item(
        id=item_id,
        scenario=scenario,
        channel=channel,
        verdict=verdict,
        languages=languages,
        biller=biller,
        biller_name=biller_name,
        category=category or (biller.category if biller else None),
        consumer=consumer_no,
        amount=amount,
        amount_intent=amount_intent,
        history_intent=history_intent,
        destinations=list(destinations),
        patterns=set(patterns),
        text=text,
        due=due,
        urgency=urgency,
    )
    if screenshot:
        sender, time = screenshot
        links = [v for k, v, _ in destinations if k == L and text.rstrip().endswith(v)]
        body = text.rstrip()
        body_html = esc(body)
        if links:
            body_html = esc(body[: -len(links[0])]) + f'<a data-region="payment_link">{esc(links[0])}</a>'
        theme = "whatsapp" if channel == Channel.WHATSAPP else "sms"
        values = {
            "theme": theme,
            "sender": esc(sender),
            "sub": "WhatsApp" if theme == "whatsapp" else "Text message",
            "body_html": body_html,
            "time": esc(time),
        }
        name = f"{item_id}.png"
        regions_px = render_html("message.html", values, (420, 760), IMAGES / name)
        item.image = name
        if "payment_link" in regions_px:
            item.regions = [Region(kind="payment_link", polygon=box_to_polygon(regions_px["payment_link"]))]
    return item


def build() -> list[tuple[str, list[Item]]]:
    V = Verdict
    SAFE, CAUTION, SCAM = V.SAFE, V.CAUTION, V.SCAM
    S, W = Channel.SMS, Channel.WHATSAPP
    D, K, R, UR = C.DISCONNECTION_THREAT, C.KYC_UPDATE_LURE, C.REFUND_LURE, C.URGENCY_PRESSURE

    # Genuine bills: one per biller (consumer 1, Demo Power's spike consumer 0 as a photo).
    genuine = [
        bill_item(f"bill_genuine_{b[:4].lower()}", "genuine_bill", b, 1, SAFE, layout=lay)
        for b, lay in [
            ("DEMO00000MAH01", "layout-a"), ("SVSL00000TEL01", "layout-b"),
            ("EBNL00000UTP01", "layout-a"), ("EJBD00000DEL01", "layout-b"),
            ("DGAS00000GUJ01", "layout-a"), ("DMOB00000NAT01", "layout-b"),
            ("SKYD00000NAT01", "layout-a"), ("FIBR00000KAR01", "layout-b"),
        ]
    ] + [
        bill_item("photo_genuine_demo", "genuine_bill_photo", "DEMO00000MAH01", 0, SAFE, photo_seed=11),
        bill_item("photo_genuine_svsl", "genuine_bill_photo", "SVSL00000TEL01", 1, SAFE, photo_seed=12, layout="layout-b"),
        bill_item("photo_genuine_ejbd", "genuine_bill_photo", "EJBD00000DEL01", 1, SAFE, photo_seed=13, layout="layout-b"),
        bill_item("photo_genuine_fibr", "genuine_bill_photo", "FIBR00000KAR01", 1, SAFE, photo_seed=14),
    ]  # fmt: skip

    def cur(b: str, i: int) -> float:
        return service.current_bill(b, consumer(b, i)).amount

    tampered = [
        # Big changes: also stand out against history.
        bill_item("bill_tampered_demo", "tampered_amount", "DEMO00000MAH01", 2, CAUTION, history="spike", amount=cur("DEMO00000MAH01", 2) + 3000),
        bill_item("bill_tampered_ebnl", "tampered_amount", "EBNL00000UTP01", 2, CAUTION, history="spike", amount=round(cur("EBNL00000UTP01", 2) * 2.5)),
        bill_item("bill_tampered_ejbd", "tampered_amount", "EJBD00000DEL01", 2, CAUTION, history="spike", amount=cur("EJBD00000DEL01", 2) + 1000, layout="layout-b"),
        # Subtle changes: only the biller's own amount reveals them.
        bill_item("bill_tampered_svsl", "tampered_amount", "SVSL00000TEL01", 2, CAUTION, amount=cur("SVSL00000TEL01", 2) + 300, layout="layout-b"),
        bill_item("bill_tampered_dmob", "tampered_amount", "DMOB00000NAT01", 2, CAUTION, amount=cur("DMOB00000NAT01", 2) + 200),
        bill_item("bill_tampered_skyd", "tampered_amount", "SKYD00000NAT01", 2, CAUTION, amount=cur("SKYD00000NAT01", 2) + 100, layout="layout-b"),
        # Genuine amount, payment UPI ID swapped.
        bill_item("bill_swapped_vpa_dgas", "tampered_destination", "DGAS00000GUJ01", 2, SCAM, vpa=("demogas.billing@okdemo", "lookalike_vpa")),
        bill_item("bill_swapped_vpa_fibr", "tampered_destination", "FIBR00000KAR01", 2, CAUTION, vpa=("payments.desk@okdemo", "other_vpa"), layout="layout-b"),
    ]  # fmt: skip

    dg2, dm2, eb2 = consumer("DGAS00000GUJ01", 2), consumer("DEMO00000MAH01", 2), consumer("EBNL00000UTP01", 2)
    t4_amount = float(round(usual("DEMO00000MAH01", 2) * 2.6))
    h4_amount = float(round(usual("EBNL00000UTP01", 2) * 2.5))

    scams_en = [
        message_item("scam_en_disconnect_lookalike", "disconnection_scam", S, SCAM, ["en"],
            "Dear Consumer, your Demo Power electricity connection will be disconnected tonight at 9:30 PM "
            "as your last bill is not updated. Contact our officer immediately on 9000000001. "
            "Pay now: demopower-bill.example/pay",
            biller_id="DEMO00000MAH01", biller_name="Demo Power",
            destinations=[(P, "9000000001", "personal_phone"), (L, "demopower-bill.example/pay", "lookalike_url")],
            patterns={D, UR}, urgency=True, screenshot=("VK-ELCOFF", "6:42 PM")),
        message_item("scam_en_kyc_apk", "kyc_apk_scam", W, SCAM, ["en"],
            "Sample Vidyut Seva: Your KYC is pending. Download the official app and update KYC within 2 hours "
            "or your supply will be stopped: samplevidyut-kyc.example/SVS_Update.apk",
            biller_id="SVSL00000TEL01", biller_name="Sample Vidyut Seva",
            destinations=[(L, "samplevidyut-kyc.example/SVS_Update.apk", "lookalike_apk")],
            patterns={K, D, UR}, urgency=True),
        message_item("scam_en_refund_known", "refund_scam", S, SCAM, ["en"],
            "Example Bijli Nigam: You were overcharged Rs 1,180 last month. Claim your refund before tonight "
            "at bijli-bill-refund.example",
            biller_id="EBNL00000UTP01", biller_name="Example Bijli Nigam",
            destinations=[(L, "bijli-bill-refund.example", "known_scam")],
            patterns={R, UR}, urgency=True),
        message_item("scam_en_fake_bill_vpa", "fake_bill_scam", S, SCAM, ["en"],
            f"DemoGas: Gas bill of Rs 2,460.00 for consumer no {dg2} is overdue. Pay now to "
            "demogas.bill@okdemo to avoid disconnection.",
            biller_id="DGAS00000GUJ01", biller_name="DemoGas", consumer_no=dg2, amount=2460.0,
            amount_intent="tampered", history_intent="spike",
            destinations=[(U, "demogas.bill@okdemo", "lookalike_vpa")],
            patterns={D}, urgency=True, screenshot=("AX-DMOGAS", "11:05 AM")),
        message_item("scam_en_short_url", "disconnection_scam", S, SCAM, ["en"],
            "FiberDemo: Your FiberDemo service will be suspended today. Renew now: bit.ly/fd-renew",
            biller_id="FIBR00000KAR01", biller_name="FiberDemo",
            destinations=[(L, "bit.ly/fd-renew", "short_url")], patterns={D}, urgency=True),
        message_item("scam_en_known_vpa", "disconnection_scam", W, SCAM, ["en"],
            "Electricity Office: Pending bill Rs 3,150. Pay immediately to UPI electricityofficer@okdemo "
            "or your power supply will be cut.",
            biller_name="Electricity Office", category=BillerCategory.ELECTRICITY, amount=3150.0,
            destinations=[(U, "electricityofficer@okdemo", "known_scam")], patterns={D, UR}, urgency=True),
        message_item("scam_en_dth_phone", "disconnection_scam", S, SCAM, ["en"],
            "SkyDemo: Your DTH connection is deactivated. To reactivate call our executive at 8000000002 "
            "and pay Rs 499.",
            biller_id="SKYD00000NAT01", biller_name="SkyDemo", amount=499.0,
            destinations=[(P, "8000000002", "personal_phone")], patterns={D}, urgency=True),
        message_item("scam_en_mobile_kyc", "kyc_scam", S, SCAM, ["en"],
            "Demo Mobile: Your number will be blocked within 24 hours due to incomplete KYC. "
            "Update KYC now: demomobile-kyc.example",
            biller_id="DMOB00000NAT01", biller_name="Demo Mobile",
            destinations=[(L, "demomobile-kyc.example", "lookalike_url")], patterns={K, UR}, urgency=True),
    ]  # fmt: skip

    scams_te = [
        message_item("scam_te_disconnect_lookalike", "disconnection_scam", S, SCAM, ["te", "en"],
            "ప్రియమైన వినియోగదారా, మీ Sample Vidyut కరెంట్ కనెక్షన్ ఈ రాత్రి 9:30 కి కట్ చేయబడుతుంది. "
            "వెంటనే మా అధికారికి 9000000003 కు కాల్ చేయండి. చెల్లించండి: samplevidyut-pay.example",
            biller_id="SVSL00000TEL01", biller_name="Sample Vidyut",
            destinations=[(P, "9000000003", "personal_phone"), (L, "samplevidyut-pay.example", "lookalike_url")],
            patterns={D, UR}, urgency=True, screenshot=("VM-SVSLBL", "7:15 PM")),
        message_item("scam_te_kyc_apk", "kyc_apk_scam", W, SCAM, ["te", "en"],
            "Sample Vidyut Seva: మీ KYC అప్‌డేట్ కాలేదు. వెంటనే ఈ యాప్ డౌన్‌లోడ్ చేసి KYC పూర్తి చేయండి, "
            "లేకపోతే విద్యుత్ సరఫరా నిలిపివేయబడుతుంది: samplevidyut-kyc.example/SVSL.apk",
            biller_id="SVSL00000TEL01", biller_name="Sample Vidyut Seva",
            destinations=[(L, "samplevidyut-kyc.example/SVSL.apk", "lookalike_apk")],
            patterns={K, D, UR}, urgency=True),
        message_item("scam_te_refund_known", "refund_scam", S, SCAM, ["te", "en"],
            "Example Bijli: గత నెల మీరు అదనంగా ₹980 చెల్లించారు. మీ డబ్బు తిరిగి పొందడానికి ఈ రోజే "
            "క్లిక్ చేయండి: bijli-bill-refund.example",
            biller_id="EBNL00000UTP01", biller_name="Example Bijli",
            destinations=[(L, "bijli-bill-refund.example", "known_scam")], patterns={R}, urgency=True),
        message_item("scam_te_fake_bill_vpa", "fake_bill_scam", S, SCAM, ["te", "en"],
            f"Demo Power: కన్స్యూమర్ నంబర్ {dm2} బిల్లు ₹{money(t4_amount)} చెల్లించలేదు. కనెక్షన్ కట్ "
            "కాకుండా ఉండాలంటే వెంటనే demopower.bill@okdemo కు చెల్లించండి.",
            biller_id="DEMO00000MAH01", biller_name="Demo Power", consumer_no=dm2, amount=t4_amount,
            amount_intent="tampered", history_intent="spike",
            destinations=[(U, "demopower.bill@okdemo", "lookalike_vpa")],
            patterns={D, UR}, urgency=True, screenshot=("AD-DMOPWR", "9:48 AM")),
        message_item("scam_te_short_url", "disconnection_scam", S, SCAM, ["te", "en"],
            "FiberDemo: మీ broadband కనెక్షన్ ఈ రోజు ఆపివేయబడుతుంది. వెంటనే రీఛార్జ్ చేయండి: tinyurl.com/fdrenew",
            biller_id="FIBR00000KAR01", biller_name="FiberDemo",
            destinations=[(L, "tinyurl.com/fdrenew", "short_url")], patterns={D, UR}, urgency=True),
        message_item("scam_te_known_vpa", "disconnection_scam", W, SCAM, ["te", "en"],
            "విద్యుత్ కార్యాలయం: మీ బకాయి ₹2,750. వెంటనే electricityofficer@okdemo కు చెల్లించండి, "
            "లేకపోతే ఈ రాత్రి కరెంట్ కట్ అవుతుంది.",
            biller_name="విద్యుత్ కార్యాలయం", category=BillerCategory.ELECTRICITY, amount=2750.0,
            destinations=[(U, "electricityofficer@okdemo", "known_scam")], patterns={D, UR}, urgency=True),
        message_item("scam_te_dth_phone", "disconnection_scam", S, SCAM, ["te", "en"],
            "SkyDemo: మీ DTH కనెక్షన్ నిలిపివేయబడింది. మళ్లీ ప్రారంభించడానికి 8000000004 కు కాల్ చేసి ₹499 చెల్లించండి.",
            biller_id="SKYD00000NAT01", biller_name="SkyDemo", amount=499.0,
            destinations=[(P, "8000000004", "personal_phone")], patterns={D}, urgency=True),
        message_item("scam_te_gas_cashback", "refund_scam", W, SCAM, ["te", "en"],
            "DemoGas: మీకు గ్యాస్ సబ్సిడీ క్యాష్‌బ్యాక్ ₹1,200 వచ్చింది. వెంటనే మీ బ్యాంక్ వివరాలు నమోదు "
            "చేయండి: gas-subsidy-refund.example",
            biller_id="DGAS00000GUJ01", biller_name="DemoGas",
            destinations=[(L, "gas-subsidy-refund.example", "known_scam")], patterns={R, UR}, urgency=True),
    ]  # fmt: skip

    scams_hi = [
        message_item("scam_hi_disconnect_lookalike", "disconnection_scam", S, SCAM, ["hi", "en"],
            "प्रिय उपभोक्ता, आपका Example Bijli कनेक्शन आज रात 9:30 बजे काट दिया जाएगा। तुरंत बिजली "
            "अधिकारी से 9000000005 पर संपर्क करें। भुगतान करें: examp1ebijli-pay.example",
            biller_id="EBNL00000UTP01", biller_name="Example Bijli",
            destinations=[(P, "9000000005", "personal_phone"), (L, "examp1ebijli-pay.example", "lookalike_url")],
            patterns={D, UR}, urgency=True, screenshot=("VK-BIJLIX", "8:20 PM")),
        message_item("scam_hi_kyc_apk", "kyc_apk_scam", W, SCAM, ["hi", "en"],
            "Demo Power: आपका KYC अपडेट नहीं हुआ है। तुरंत ऐप डाउनलोड करें वरना बिजली सप्लाई बंद हो जाएगी: "
            "demopower-kyc.example/DemoPower_KYC.apk",
            biller_id="DEMO00000MAH01", biller_name="Demo Power",
            destinations=[(L, "demopower-kyc.example/DemoPower_KYC.apk", "lookalike_apk")],
            patterns={K, D, UR}, urgency=True),
        message_item("scam_hi_refund_known", "refund_scam", S, SCAM, ["hi", "en"],
            "Example Jal Board: आपने पिछले बिल में ₹640 ज़्यादा भरे हैं। रिफंड के लिए आज ही यहां क्लिक करें: "
            "kyc-update-portal.example/refund",
            biller_id="EJBD00000DEL01", biller_name="Example Jal Board",
            destinations=[(L, "kyc-update-portal.example/refund", "known_scam")], patterns={R}, urgency=True),
        message_item("scam_hi_fake_bill_vpa", "fake_bill_scam", S, SCAM, ["hi", "en"],
            f"Example Bijli Nigam: उपभोक्ता संख्या {eb2} का बिल ₹{money(h4_amount)} बकाया है। कनेक्शन कटने "
            "से बचने के लिए तुरंत examplebijli.pay@okdemo पर भुगतान करें।",
            biller_id="EBNL00000UTP01", biller_name="Example Bijli Nigam", consumer_no=eb2, amount=h4_amount,
            amount_intent="tampered", history_intent="spike",
            destinations=[(U, "examplebijli.pay@okdemo", "lookalike_vpa")],
            patterns={D, UR}, urgency=True, screenshot=("VM-EBNLPY", "10:02 AM")),
        message_item("scam_hi_short_url", "disconnection_scam", S, SCAM, ["hi", "en"],
            "DemoGas: Aapka gas connection aaj band ho jayega. Turant renew karein: cutt.ly/dg-pay",
            biller_id="DGAS00000GUJ01", biller_name="DemoGas",
            destinations=[(L, "cutt.ly/dg-pay", "short_url")], patterns={D, UR}, urgency=True),
        message_item("scam_hi_known_vpa", "disconnection_scam", W, SCAM, ["hi", "en"],
            "बिजली विभाग: आपका ₹2,980 बकाया है। तुरंत billupdate.refund@okdemo पर भुगतान करें वरना आज रात "
            "लाइट काट दी जाएगी।",
            biller_name="बिजली विभाग", category=BillerCategory.ELECTRICITY, amount=2980.0,
            destinations=[(U, "billupdate.refund@okdemo", "known_scam")], patterns={D, UR}, urgency=True),
        message_item("scam_hi_mobile_phone", "kyc_scam", S, SCAM, ["hi", "en"],
            "Demo Mobile: आपका नंबर 24 घंटे में बंद कर दिया जाएगा। KYC के लिए तुरंत 7000000006 पर कॉल करें।",
            biller_id="DMOB00000NAT01", biller_name="Demo Mobile",
            destinations=[(P, "7000000006", "personal_phone")], patterns={K, UR}, urgency=True),
        message_item("scam_hi_cashback", "refund_scam", W, SCAM, ["hi", "en"],
            "SkyDemo: Aapke account mein ₹350 cashback pending hai. Paise wapas paane ke liye abhi link "
            "kholein: skydemo-cashback.example",
            biller_id="SKYD00000NAT01", biller_name="SkyDemo",
            destinations=[(L, "skydemo-cashback.example", "lookalike_url")], patterns={R, UR}, urgency=True),
    ]  # fmt: skip

    def reminder(item_id, b, idx, lang, template, dests, patterns=frozenset(), name=None, scenario="genuine_reminder", verdict=SAFE, history="normal"):  # fmt: skip
        c = consumer(b, idx)
        bill = service.current_bill(b, c)
        text = template.format(c=c, amt=money(bill.amount), due=day(bill.due_date))
        return message_item(
            item_id, scenario, S, verdict, lang, text,
            biller_id=b, biller_name=name or BY_ID[b].name, consumer_no=c, amount=bill.amount,
            amount_intent="match", history_intent=history,
            destinations=[(k, v, "official") for k, v in dests], patterns=set(patterns), due=bill.due_date,
        )  # fmt: skip

    reminders = [
        reminder("reminder_en_demo", "DEMO00000MAH01", 3, ["en"],
            "Dear Consumer, your Demo Power bill of Rs {amt} for consumer no {c} is due on {due}. Pay at "
            "demopower.example or UPI demopower.bill@demobank. Ignore if already paid. -DEMOPW",
            [(L, "demopower.example"), (U, "demopower.bill@demobank")], name="Demo Power"),
        reminder("reminder_en_ejbd", "EJBD00000DEL01", 3, ["en"],
            "Example Jal Board: Water bill Rs {amt} for K.No. {c} is due on {due}. Pay securely at "
            "examplejal.example. -EXMJAL",
            [(L, "examplejal.example")]),
        reminder("reminder_en_fibr", "FIBR00000KAR01", 3, ["en"],
            "FiberDemo: Your broadband bill of Rs {amt} for account {c} has been generated. Due date {due}. "
            "Pay via fiberdemo.example/pay",
            [(L, "fiberdemo.example/pay")], name="FiberDemo"),
        reminder("reminder_en_dmob_polite_disconnect", "DMOB00000NAT01", 3, ["en"],
            "Demo Mobile: Bill Rs {amt} for account {c} is due on {due}. Please pay by the due date to avoid "
            "disconnection. Pay at demomobile.example",
            [(L, "demomobile.example")], patterns={D}, name="Demo Mobile"),
        reminder("reminder_te_svsl", "SVSL00000TEL01", 3, ["te", "en"],
            "Sample Vidyut Seva: మీ సర్వీస్ నంబర్ {c} కి ₹{amt} బిల్లు వచ్చింది. చెల్లింపు గడువు {due}. "
            "samplevidyut.example లో లేదా UPI samplevidyut@demobank ద్వారా చెల్లించండి.",
            [(L, "samplevidyut.example"), (U, "samplevidyut@demobank")]),
        reminder("reminder_te_svsl_short", "SVSL00000TEL01", 4, ["te", "en"],
            "Sample Vidyut: బిల్లు ₹{amt}, సర్వీస్ నంబర్ {c}, గడువు తేదీ {due}. అధికారిక వెబ్‌సైట్ "
            "samplevidyut.example లో మాత్రమే చెల్లించండి.",
            [(L, "samplevidyut.example")], name="Sample Vidyut"),
        reminder("reminder_te_skyd", "SKYD00000NAT01", 3, ["te", "en"],
            "SkyDemo: మీ DTH ఖాతా {c} కి ₹{amt} రీఛార్జ్ గడువు {due}. skydemo.example లో రీఛార్జ్ చేయండి.",
            [(L, "skydemo.example")], name="SkyDemo"),
        reminder("reminder_te_dgas_polite_disconnect", "DGAS00000GUJ01", 3, ["te", "en"],
            "DemoGas: మీ గ్యాస్ బిల్లు ₹{amt} (కన్స్యూమర్ నంబర్ {c}) గడువు {due}. సరఫరా నిలిపివేత "
            "నివారించడానికి గడువులోగా demogas.example లో చెల్లించండి.",
            [(L, "demogas.example")], patterns={D}, name="DemoGas"),
        reminder("reminder_hi_ebnl", "EBNL00000UTP01", 3, ["hi", "en"],
            "Example Bijli Nigam: उपभोक्ता संख्या {c} का बिल ₹{amt} है, अंतिम तिथि {due}। भुगतान केवल "
            "examplebijli.example या UPI examplebijli.pay@demobank पर करें।",
            [(L, "examplebijli.example"), (U, "examplebijli.pay@demobank")]),
        reminder("reminder_hi_demo", "DEMO00000MAH01", 4, ["hi", "en"],
            "Demo Power: उपभोक्ता क्रमांक {c} का बिजली बिल ₹{amt}, देय तिथि {due}। demopower.example पर "
            "भुगतान करें।",
            [(L, "demopower.example")], name="Demo Power"),
        reminder("reminder_hi_ejbd", "EJBD00000DEL01", 4, ["hi", "en"],
            "Example Jal Board: आपका पानी का बिल ₹{amt} (K.No. {c}) {due} तक देय है। examplejal.example पर "
            "भुगतान करें।",
            [(L, "examplejal.example")]),
        reminder("reminder_hi_fibr_polite_disconnect", "FIBR00000KAR01", 4, ["hi", "en"],
            "FiberDemo: खाता {c} का ब्रॉडबैंड बिल ₹{amt}, देय तिथि {due}। कनेक्शन बंद होने से बचने के लिए "
            "समय पर fiberdemo.example पर भुगतान करें।",
            [(L, "fiberdemo.example")], patterns={D}, name="FiberDemo"),
    ]  # fmt: skip

    edge = [
        # The biller really billed this, but it is ~3.4x the usual bill: verify before paying.
        bill_item("bill_spike_ebnl", "amount_spike", "EBNL00000UTP01", 0, CAUTION, history="spike"),
        reminder("reminder_en_dgas_spike", "DGAS00000GUJ01", 0, ["en"],
            "DemoGas: Your gas bill of Rs {amt} for consumer no {c} is due on {due}. Pay at demogas.example",
            [(L, "demogas.example")], name="DemoGas", scenario="amount_spike", verdict=CAUTION, history="spike"),
        message_item("edge_en_unknown_consumer", "unknown_consumer", S, CAUTION, ["en"],
            "Demo Power: Your bill of Rs 1,350.00 for consumer no DP-9999-123456 is due on 08-Nov-2026. "
            "Pay at demopower.example",
            biller_id="DEMO00000MAH01", biller_name="Demo Power", consumer_no="DP-9999-123456", amount=1350.0,
            amount_intent="unknown_consumer", history_intent="unknown_consumer",
            destinations=[(L, "demopower.example", "official")], due=date(2026, 11, 8)),
        message_item("edge_en_unknown_biller", "unknown_biller", S, CAUTION, ["en"],
            "Bharat Urja Board: Your electricity bill of Rs 1,860 is due on 07-Nov-2026. Pay via the official app.",
            biller_name="Bharat Urja Board", category=BillerCategory.ELECTRICITY, amount=1860.0,
            due=date(2026, 11, 7)),
    ]  # fmt: skip

    return [
        ("genuine_bills", genuine),
        ("tampered_bills", tampered),
        ("scams_en", scams_en),
        ("scams_te", scams_te),
        ("scams_hi", scams_hi),
        ("reminders", reminders),
        ("edge_cases", edge),
    ]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(IMAGES, ignore_errors=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    groups = build()
    labels = []
    seen: dict[str, int] = {}
    for _, items in groups:
        for item in items:
            # Stratified by scenario: the 2nd, 5th, 8th... item of each scenario is held out,
            # so every scenario with 2+ items appears in both splits.
            n = seen[item.scenario] = seen.get(item.scenario, -1) + 1
            labels.append(item.label("test" if n % 3 == 1 else "dev"))
    ids = [lbl.id for lbl in labels]
    assert len(ids) == len(set(ids)), "duplicate ids"
    with (OUT / "labels.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for lbl in labels:
            f.write(lbl.model_dump_json() + "\n")
    print(f"wrote {len(labels)} labels to {OUT / 'labels.jsonl'}")
    for name, items in groups:
        print(f"  {name}: {len(items)}")


if __name__ == "__main__":
    main()
