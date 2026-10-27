"""Generate the spike's synthetic inputs and inputs/labels.jsonl.

Documents are HTML rendered by headless Edge (correct Devanagari shaping); the
"phone photo" is composited with Pillow so the bill's exact corners are known.
All names, numbers, domains and UPI IDs are fictional.

Run from api/:  .venv\\Scripts\\python -m spike.make_inputs
"""

import html
import json
import math
import random
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from string import Template

from PIL import Image, ImageDraw, ImageFilter

from app.schemas import (
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

HERE = Path(__file__).parent
TEMPLATES = HERE / "templates"
OUT = HERE / "inputs"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

BILL = {
    "bill_no": "DPB/2026/10/558213",
    "consumer_name": "Sample Consumer",
    "consumer_number": "DP-4410-882761",
    "address": "12, Demo Nagar, Pune 411001",
    "period": "01-Sep-2026 to 30-Sep-2026",
    "units": "186",
    "bill_date": "12-Oct-2026",
    "due_date": "05-Nov-2026",
    "amount": "1,240.00",
    "vpa": "demopower.bill@demobank",
    "site": "demopower.example/pay",
    "bbps_id": "DEMO00000MAH01",
}

SCAM_PHONE = "+91 90000 00000"
SCAM_LINK = "dem0power-update.example/pay"
SMS_SCAM_EN = (
    "Dear Consumer, Your electricity power will be disconnected tonight at 9:30 PM from "
    "electricity office because your previous month bill was not updated. Please immediately "
    f"contact our electricity officer {SCAM_PHONE}. Pay now:"
)
SMS_SCAM_HI = (
    "प्रिय उपभोक्ता, आपका बिजली कनेक्शन आज रात 9:30 बजे काट दिया जाएगा क्योंकि आपके पिछले महीने "
    f"का बिल अपडेट नहीं हुआ है। तुरंत बिजली अधिकारी से संपर्क करें {SCAM_PHONE}। "
    f"अभी भुगतान करें: {SCAM_LINK}"
)
WHATSAPP_HINGLISH = (
    "Namaste 🙏 Demo Power Customer Care. Aapka KYC update nahi hua hai, aaj raat connection "
    "cut ho jayega. Turant ye app download karke KYC complete karein: "
    f"demopower-kyc.example/DemoPower_KYC.apk  Help ke liye call karein {SCAM_PHONE}"
)
SMS_GENUINE_EN = (
    "Dear Consumer, your Demo Power bill for Sep-2026 of Rs 1,240.00 for consumer no "
    "DP-4410-882761 is due on 05-Nov-2026. Pay via the official Demo Power app or "
    "demopower.example/pay. Ignore if already paid. -DEMOPW"
)
VOICE_EN = "Is this electricity bill safe to pay?"


def render(template: str, values: dict[str, str], size: tuple[int, int], out: Path) -> dict:
    """Render an HTML template with headless Edge; return element regions measured in-page."""
    page = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(
        {k: html.escape(v) for k, v in values.items()}
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(page, encoding="utf-8")
        common = [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={size[0]},{size[1]}",
            f"--user-data-dir={Path(tmp) / 'profile'}",
        ]
        subprocess.run(
            [*common, f"--screenshot={out}", src.as_uri()],
            check=True,
            capture_output=True,
            timeout=60,
        )
        dom = subprocess.run(
            [*common, "--dump-dom", src.as_uri()],
            check=True,
            capture_output=True,
            timeout=60,
            text=True,
            encoding="utf-8",
        ).stdout
    match = re.search(r'data-regions="([^"]*)"', dom)
    if not match:
        raise RuntimeError(f"no regions found rendering {template}")
    img = Image.open(out)
    if img.size != size:
        raise RuntimeError(f"{out.name}: expected {size}, Edge produced {img.size}")
    return json.loads(html.unescape(match.group(1)))


def box_to_polygon(box: list[float]) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = box
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def make_photo(bill: Path, out: Path) -> list[tuple[float, float]]:
    """Tilt/skew the bill onto a cluttered table and return its four corners in the photo."""
    rng = random.Random(42)
    W, H = 1600, 1200
    bg = Image.new("RGB", (W, H), (150, 108, 72))
    d = ImageDraw.Draw(bg)
    for x in range(0, W, 3):  # wood grain
        shade = rng.randint(-18, 18)
        d.line([(x, 0), (x + rng.randint(-40, 40), H)], fill=(150 + shade, 108 + shade, 72 + shade))
    d.ellipse([1270, 120, 1520, 370], fill=(235, 235, 230))  # cup
    d.ellipse([1305, 155, 1485, 335], fill=(92, 58, 35))
    d.polygon([(90, 980), (560, 1120), (552, 1145), (82, 1004)], fill=(25, 60, 160))  # pen
    d.polygon(
        [(1180, 820), (1480, 790), (1510, 1080), (1210, 1110)], fill=(250, 226, 110)
    )  # sticky note
    bg = bg.filter(ImageFilter.GaussianBlur(1.2))

    src = Image.open(bill).convert("RGB")
    w, h = src.size
    scale, angle, shear = 0.98, math.radians(-7), 0.05
    ca, sa = math.cos(angle), math.sin(angle)
    # forward map p' = A p + t  (scale, then shear, then rotate)
    a, b = scale * ca, scale * (ca * shear - sa)
    c, e = scale * sa, scale * (sa * shear + ca)
    tx, ty = 330.0, 140.0
    corners = [
        (a * x + b * y + tx, c * x + e * y + ty) for x, y in [(0, 0), (w, 0), (w, h), (0, h)]
    ]
    det = a * e - b * c
    inv = (e / det, -b / det, (b * ty - e * tx) / det, -c / det, a / det, (c * tx - a * ty) / det)

    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).polygon([(x + 14, y + 16) for x, y in corners], fill=110)
    bg.paste((20, 14, 8), mask=shadow.filter(ImageFilter.GaussianBlur(14)))
    warped = src.transform((W, H), Image.Transform.AFFINE, inv, resample=Image.Resampling.BICUBIC)
    mask = Image.new("L", (w, h), 255).transform(
        (W, H), Image.Transform.AFFINE, inv, resample=Image.Resampling.BILINEAR
    )
    bg.paste(warped, mask=mask)

    light = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(v * 0.35))
    bg.paste((0, 0, 0), mask=light)  # vignette, darker toward the edges
    bg.save(out, quality=80)
    return corners


def make_voice_en(out: Path) -> None:
    """Windows text-to-speech, written as WAV mono 16-bit PCM 24 kHz (what Muse ASR accepts)."""
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000, "
        "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, "
        "[System.Speech.AudioFormat.AudioChannel]::Mono); "
        f"$s.SetOutputToWaveFile('{out}', $f); $s.Speak('{VOICE_EN}'); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, timeout=60)


def main() -> None:
    if not EDGE.exists():
        raise SystemExit(f"Edge not found at {EDGE}")
    OUT.mkdir(exist_ok=True)

    genuine = BillFields(
        biller_name="Demo Power Distribution Co. Ltd",
        biller_category=BillerCategory.ELECTRICITY,
        consumer_number=BILL["consumer_number"],
        amount=1240.00,
        due_date=date(2026, 11, 5),
        bill_date=date(2026, 10, 12),
        payment_destinations=[
            PaymentDestination(kind=DestinationKind.UPI, value=BILL["vpa"]),
            PaymentDestination(kind=DestinationKind.URL, value=BILL["site"]),
        ],
        language="en",
        urgency_language=False,
    )
    genuine_evidence = [
        Evidence(code=EvidenceCode.BILLER_VERIFIED, source="lookup_biller"),
        Evidence(code=EvidenceCode.AMOUNT_MATCHES_BILLER, source="fetch_bill"),
        Evidence(code=EvidenceCode.DESTINATION_OFFICIAL, source="check_payment_destination"),
    ]
    scam_dest = [
        PaymentDestination(kind=DestinationKind.PHONE, value=SCAM_PHONE),
        PaymentDestination(kind=DestinationKind.URL, value=SCAM_LINK),
    ]
    disconnection_evidence = [
        Evidence(code=EvidenceCode.DISCONNECTION_THREAT, source="match_scam_patterns"),
        Evidence(code=EvidenceCode.PERSONAL_PHONE_NUMBER, source="check_payment_destination"),
        Evidence(code=EvidenceCode.LOOKALIKE_DOMAIN, source="check_payment_destination"),
        Evidence(code=EvidenceCode.DESTINATION_NOT_OFFICIAL, source="check_payment_destination"),
    ]
    scam_fields = BillFields(
        biller_category=BillerCategory.ELECTRICITY,
        payment_destinations=scam_dest,
        language="en",
        urgency_language=True,
    )
    labels: list[Label] = []

    clean_regions = render("bill.html", BILL, (800, 1000), OUT / "bill_clean.png")
    labels.append(
        Label(
            id="bill_clean",
            scenario="genuine_bill",
            input=LabelInput(
                kind=InputKind.IMAGE, channel=Channel.PAPER_BILL, path="bill_clean.png"
            ),
            expected=Expected(
                extracted=genuine,
                verdict=Verdict.SAFE,
                evidence=genuine_evidence,
                regions=[
                    Region(kind="document", polygon=box_to_polygon([0, 0, 800, 1000])),
                    Region(kind="amount", polygon=box_to_polygon(clean_regions["amount"])),
                ],
            ),
        )
    )

    corners = make_photo(OUT / "bill_clean.png", OUT / "bill_photo.jpg")
    labels.append(
        Label(
            id="bill_photo",
            scenario="genuine_bill",
            input=LabelInput(
                kind=InputKind.IMAGE, channel=Channel.PAPER_BILL, path="bill_photo.jpg"
            ),
            expected=Expected(
                extracted=genuine,
                verdict=Verdict.SAFE,
                evidence=genuine_evidence,
                regions=[Region(kind="document", polygon=corners)],
            ),
        )
    )

    tampered_regions = render(
        "bill.html", BILL | {"amount": "4,240.00"}, (800, 1000), OUT / "bill_tampered.png"
    )
    labels.append(
        Label(
            id="bill_tampered",
            scenario="tampered_amount",
            input=LabelInput(
                kind=InputKind.IMAGE, channel=Channel.PAPER_BILL, path="bill_tampered.png"
            ),
            expected=Expected(
                extracted=genuine.model_copy(update={"amount": 4240.00}),
                verdict=Verdict.CAUTION,
                evidence=[
                    Evidence(code=EvidenceCode.BILLER_VERIFIED, source="lookup_biller"),
                    Evidence(code=EvidenceCode.AMOUNT_MISMATCH, source="fetch_bill"),
                    Evidence(
                        code=EvidenceCode.DESTINATION_OFFICIAL, source="check_payment_destination"
                    ),
                ],
                regions=[Region(kind="amount", polygon=box_to_polygon(tampered_regions["amount"]))],
            ),
        )
    )

    sms_regions = render(
        "sms.html",
        {"sender": "VK-ELCOFF", "body": SMS_SCAM_EN, "link": SCAM_LINK, "time": "6:42 PM"},
        (420, 760),
        OUT / "sms_scam_en.png",
    )
    labels.append(
        Label(
            id="sms_scam_en_img",
            scenario="disconnection_scam",
            input=LabelInput(kind=InputKind.IMAGE, channel=Channel.SMS, path="sms_scam_en.png"),
            expected=Expected(
                extracted=scam_fields,
                verdict=Verdict.SCAM,
                evidence=disconnection_evidence,
                regions=[
                    Region(kind="payment_link", polygon=box_to_polygon(sms_regions["payment_link"]))
                ],
            ),
        )
    )

    texts = [
        (
            "sms_scam_en_txt",
            "disconnection_scam",
            Channel.SMS,
            f"{SMS_SCAM_EN} {SCAM_LINK}",
            scam_fields,
            Verdict.SCAM,
            disconnection_evidence,
        ),
        (
            "sms_scam_hi_txt",
            "disconnection_scam",
            Channel.SMS,
            SMS_SCAM_HI,
            scam_fields.model_copy(update={"language": "hi"}),
            Verdict.SCAM,
            disconnection_evidence,
        ),
        (
            "whatsapp_scam_hinglish_txt",
            "kyc_apk_scam",
            Channel.WHATSAPP,
            WHATSAPP_HINGLISH,
            scam_fields.model_copy(
                update={
                    "biller_name": "Demo Power",
                    "language": "hi",
                    "payment_destinations": [
                        PaymentDestination(
                            kind=DestinationKind.URL,
                            value="demopower-kyc.example/DemoPower_KYC.apk",
                        ),
                        PaymentDestination(kind=DestinationKind.PHONE, value=SCAM_PHONE),
                    ],
                }
            ),
            Verdict.SCAM,
            [
                Evidence(code=EvidenceCode.KYC_UPDATE_LURE, source="match_scam_patterns"),
                Evidence(code=EvidenceCode.APK_LINK, source="check_payment_destination"),
                Evidence(code=EvidenceCode.DISCONNECTION_THREAT, source="match_scam_patterns"),
                Evidence(
                    code=EvidenceCode.PERSONAL_PHONE_NUMBER, source="check_payment_destination"
                ),
                Evidence(
                    code=EvidenceCode.DESTINATION_NOT_OFFICIAL, source="check_payment_destination"
                ),
            ],
        ),
        (
            "sms_genuine_en_txt",
            "genuine_reminder",
            Channel.SMS,
            SMS_GENUINE_EN,
            genuine.model_copy(
                update={
                    "biller_name": "Demo Power",
                    "bill_date": None,
                    "payment_destinations": [
                        PaymentDestination(kind=DestinationKind.URL, value=BILL["site"])
                    ],
                }
            ),
            Verdict.SAFE,
            genuine_evidence,
        ),
    ]
    for label_id, scenario, channel, text, fields, verdict, evidence in texts:
        path = f"{label_id.removesuffix('_txt')}.txt"
        (OUT / path).write_text(text + "\n", encoding="utf-8")
        labels.append(
            Label(
                id=label_id,
                scenario=scenario,
                input=LabelInput(kind=InputKind.TEXT, channel=channel, path=path, text=text),
                expected=Expected(extracted=fields, verdict=verdict, evidence=evidence),
            )
        )

    make_voice_en(OUT / "voice_en.wav")
    labels.append(
        Label(
            id="voice_en",
            scenario="voice_question",
            input=LabelInput(kind=InputKind.AUDIO, channel=Channel.VOICE, path="voice_en.wav"),
            expected=Expected(
                extracted=BillFields(language="en"), verdict=None, transcript=VOICE_EN
            ),
        )
    )
    # voice_hi is BV's own recording; its label is added once the exact words are known.

    with (OUT / "labels.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for lbl in labels:
            f.write(lbl.model_dump_json() + "\n")
    print(f"wrote {len(labels)} labels and inputs to {OUT}")


if __name__ == "__main__":
    main()
