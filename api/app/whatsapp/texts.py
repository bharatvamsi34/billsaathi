"""WhatsApp reply text in English, Telugu and Hindi, built only from masked check events.

Telugu reviewed by BV (native speaker) for the web app strings this mirrors; Hindi approximate.
Evidence labels mirror web/src/lib/codes.ts. Helpline numbers come from app/facts.py only.
"""

import re
from typing import Any

from app.facts import verified_fact
from app.labels import CODE_LABELS, LANGS, Lang  # noqa: F401

_TELUGU = re.compile(r"[ఀ-౿]")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Sending one of these words switches the reply language.
SWITCH: dict[str, Lang] = {
    "english": "en",
    "తెలుగు": "te",
    "telugu": "te",
    "हिंदी": "hi",
    "हिन्दी": "hi",
    "hindi": "hi",
}
SKIP_WORDS = {"skip", "స్కిప్", "తెలియదు", "नहीं पता", "छोड़ें"}


def detect_language(text: str | None) -> Lang | None:
    """Language from the script of the message; None when it is Latin-only or empty."""
    if not text:
        return None
    te, hi = len(_TELUGU.findall(text)), len(_DEVANAGARI.findall(text))
    if te == hi == 0:
        return None
    return "te" if te >= hi else "hi"


def is_details(text: str | None) -> bool:
    return (text or "").strip().strip(".!").lower() in DETAILS_WORDS


def switch_command(text: str | None) -> Lang | None:
    return SWITCH.get((text or "").strip().strip(".!").lower())


T: dict[str, dict[Lang, str]] = {
    "checking": {
        "en": "Checking now… ⏳ please don't pay while I check.",
        "te": "ఇప్పుడు తనిఖీ చేస్తున్నాను… ⏳ తనిఖీ పూర్తయ్యే వరకు చెల్లించవద్దు.",
        "hi": "अभी जाँच रहा हूँ… ⏳ जाँच पूरी होने तक भुगतान न करें।",
    },
    "early_scam": {
        "en": "⚠️ Scam signals found — confirming with the biller record…",
        "te": "⚠️ మోసం సంకేతాలు కనిపించాయి — బిల్లర్ రికార్డుతో నిర్ధారిస్తున్నాను…",
        "hi": "⚠️ धोखे के संकेत मिले — बिलर के रिकॉर्ड से पुष्टि कर रहा हूँ…",
    },
    "headline_SAFE": {
        "en": "✅ SAFE — matches the demo biller record",
        "te": "✅ సురక్షితం (SAFE) — డెమో బిల్లర్ రికార్డుతో సరిపోయింది",
        "hi": "✅ सुरक्षित (SAFE) — डेमो बिलर रिकॉर्ड से मेल खाता है",
    },
    "headline_CAUTION": {
        "en": "⚠️ CAUTION — do not pay yet",
        "te": "⚠️ జాగ్రత్త (CAUTION) — ఇప్పుడే చెల్లించవద్దు",
        "hi": "⚠️ सावधान (CAUTION) — अभी भुगतान न करें",
    },
    "headline_SCAM": {
        "en": "⛔ SCAM — do not pay",
        "te": "⛔ మోసం (SCAM) — డబ్బు చెల్లించవద్దు",
        "hi": "⛔ धोखा (SCAM) — पैसे मत भेजिए",
    },
    "action_SAFE": {
        "en": "You still decide before paying. Demo only, no real payment.",
        "te": "చెల్లించే ముందు నిర్ణయం మీదే. ఇది డెమో, నిజమైన చెల్లింపు కాదు.",
        "hi": "भुगतान से पहले फ़ैसला आपका। यह डेमो है, असली भुगतान नहीं।",
    },
    "action_CAUTION": {
        "en": "Check with the company's official app or website.",
        "te": "కంపెనీ అధికారిక యాప్ లేదా వెబ్‌సైట్‌లో సరిచూసుకోండి.",
        "hi": "कंपनी के आधिकारिक ऐप या वेबसाइट पर जाँच लें।",
    },
    "details_hint": {
        "en": "Reply DETAILS for full evidence.",
        "te": "పూర్తి ఆధారాల కోసం DETAILS అని పంపండి.",
        "hi": "पूरे सबूत के लिए DETAILS भेजें।",
    },
    "details_title": {
        "en": "Full evidence for your last check:",
        "te": "మీ చివరి తనిఖీ పూర్తి ఆధారాలు:",
        "hi": "आपकी पिछली जाँच के पूरे सबूत:",
    },
    "no_details": {
        "en": "I have no recent check for you. Send a bill or payment message first.",
        "te": "మీ ఇటీవలి తనిఖీ ఏదీ లేదు. ముందుగా బిల్లు లేదా చెల్లింపు సందేశం పంపండి.",
        "hi": "आपकी कोई हाल की जाँच नहीं है। पहले बिल या भुगतान संदेश भेजें।",
    },
    "unclear_photo": {
        "en": "I couldn't read the biller clearly from this photo. Please send a closer, straight photo showing the biller name, account number and amount. Don't pay until it's verified.",
        "te": "ఈ ఫోటోలో బిల్లర్ వివరాలు స్పష్టంగా చదవలేకపోయాను. బిల్లర్ పేరు, ఖాతా సంఖ్య, మొత్తం కనిపించేలా దగ్గరగా, నిటారుగా తీసిన ఫోటో పంపండి. నిర్ధారణ అయ్యే వరకు చెల్లించవద్దు.",
        "hi": "इस फ़ोटो से बिलर साफ़ नहीं पढ़ पाया। बिलर का नाम, खाता संख्या और राशि दिखाती हुई पास से, सीधी फ़ोटो भेजें। पुष्टि होने तक भुगतान न करें।",
    },
    "verdict_SAFE": {"en": "SAFE", "te": "సురక్షితం", "hi": "सुरक्षित"},
    "verdict_CAUTION": {"en": "CAUTION", "te": "జాగ్రత్త", "hi": "सावधान"},
    "verdict_SCAM": {"en": "SCAM", "te": "మోసం", "hi": "धोखा"},
    "could_not_verify": {
        "en": "Some checks could not be completed.",
        "te": "కొన్ని తనిఖీలు పూర్తి కాలేదు.",
        "hi": "कुछ जाँचें पूरी नहीं हो सकीं।",
    },
    "no_answer": {
        "en": "No answer within 10 minutes, so this check was closed.",
        "te": "10 నిమిషాల్లో సమాధానం రాలేదు, కాబట్టి ఈ తనిఖీ ముగించబడింది.",
        "hi": "10 मिनट में जवाब नहीं आया, इसलिए यह जाँच बंद कर दी गई।",
    },
    "report": {
        "en": "📞 Don't pay. Report fraud: call {value}",
        "te": "📞 చెల్లించవద్దు. మోసాన్ని ఫిర్యాదు చేయండి: {value} కు కాల్ చేయండి",
        "hi": "📞 भुगतान न करें। धोखाधड़ी की शिकायत: {value} पर कॉल करें",
    },
    "web": {
        "en": "Check bills on the web: {url}",
        "te": "వెబ్‌లో బిల్లులు తనిఖీ చేయండి: {url}",
        "hi": "वेब पर बिल जाँचें: {url}",
    },
    "footer": {
        "en": "Sandbox demo — billers are mock; no real payment.",
        "te": "డెమో మాత్రమే — బిల్లర్లు నమూనా; నిజమైన చెల్లింపు జరగదు.",
        "hi": "सिर्फ़ डेमो — बिलर नमूना हैं; कोई असली भुगतान नहीं।",
    },
    "question_hint": {
        "en": "Reply with the answer within 10 minutes, or send *skip* if you don't know.",
        "te": "10 నిమిషాల్లో సమాధానం పంపండి, తెలియకపోతే *skip* అని పంపండి.",
        "hi": "10 मिनट में जवाब भेजें, पता न हो तो *skip* भेजें।",
    },
    "switched": {
        "en": "OK, I will reply in English.",
        "te": "సరే, ఇకపై తెలుగులో సమాధానం ఇస్తాను.",
        "hi": "ठीक है, अब मैं हिंदी में जवाब दूँगा।",
    },
    "unsupported": {
        "en": "Please send the bill or payment message as text, a photo, a screenshot or a voice note.",
        "te": "దయచేసి బిల్లు లేదా చెల్లింపు సందేశాన్ని టెక్స్ట్, ఫోటో, స్క్రీన్‌షాట్ లేదా వాయిస్ నోట్‌గా పంపండి.",
        "hi": "कृपया बिल या भुगतान संदेश टेक्स्ट, फ़ोटो, स्क्रीनशॉट या वॉइस नोट के रूप में भेजें।",
    },
    "heard": {
        "en": "🎤 I heard: {text}",
        "te": "🎤 నేను విన్నది: {text}",
        "hi": "🎤 मैंने सुना: {text}",
    },
    "bad_voice": {
        "en": "I could not understand that voice note. Please try again, or send the message as text.",
        "te": "ఆ వాయిస్ నోట్ అర్థం కాలేదు. మళ్లీ ప్రయత్నించండి, లేదా సందేశాన్ని టెక్స్ట్‌గా పంపండి.",
        "hi": "वह वॉइस नोट समझ नहीं आया। फिर कोशिश करें, या संदेश टेक्स्ट में भेजें।",
    },
    "bad_image": {
        "en": "I could not open that image. Please send a PNG, JPEG or WebP photo up to 8 MB.",
        "te": "ఆ చిత్రాన్ని తెరవలేకపోయాను. దయచేసి 8 MB లోపు PNG, JPEG లేదా WebP ఫోటో పంపండి.",
        "hi": "वह चित्र नहीं खुला। कृपया 8 MB तक की PNG, JPEG या WebP फ़ोटो भेजें।",
    },
    "rate_limited": {
        "en": "Too many checks. Please wait a minute and try again.",
        "te": "చాలా ఎక్కువ తనిఖీలు. ఒక నిమిషం ఆగి మళ్లీ ప్రయత్నించండి.",
        "hi": "बहुत सारी जाँचें। एक मिनट रुककर फिर कोशिश करें।",
    },
    "busy": {
        "en": "BillSaathi is busy right now. Please try again later.",
        "te": "BillSaathi ఇప్పుడు బిజీగా ఉంది. తర్వాత మళ్లీ ప్రయత్నించండి.",
        "hi": "BillSaathi अभी व्यस्त है। बाद में फिर कोशिश करें।",
    },
}

# Sending one of these asks for the full evidence of the sender's last check.
DETAILS_WORDS = {"details", "detail", "వివరాలు", "विवरण", "ब्योरा"}

MAX_REPLY_CHARS = 450
SHORT_REASONS = 2
MAX_BULLETS = 8

# Real values from the evidence, in the words of web/src/lib/reasons.ts.
_REASONS: dict[str, dict[Lang, str]] = {
    "KNOWN_SCAM_DESTINATION": {
        "en": "“{v}” is on the known-scam list",
        "te": "“{v}” తెలిసిన మోసాల జాబితాలో ఉంది",
        "hi": "“{v}” ज्ञात धोखाधड़ी सूची में है",
    },
    "LOOKALIKE_VPA": {
        "en": "UPI ID “{v}” imitates the official “{other}”",
        "te": "UPI ID “{v}” అధికారిక “{other}” ను అనుకరిస్తోంది",
        "hi": "UPI ID “{v}” आधिकारिक “{other}” की नकल करती है",
    },
    "LOOKALIKE_DOMAIN": {
        "en": "Website “{v}” imitates the official “{other}”",
        "te": "వెబ్‌సైట్ “{v}” అధికారిక “{other}” ను అనుకరిస్తోంది",
        "hi": "वेबसाइट “{v}” आधिकारिक “{other}” की नकल करती है",
    },
    "APK_LINK": {
        "en": "Link “{v}” installs an app file (.apk)",
        "te": "లింక్ “{v}” యాప్ ఫైల్ (.apk) ఇన్‌స్టాల్ చేయిస్తుంది",
        "hi": "लिंक “{v}” ऐप फ़ाइल (.apk) इंस्टॉल कराता है",
    },
    "SHORT_URL": {
        "en": "Link “{v}” hides where it goes behind a link shortener",
        "te": "లింక్ “{v}” అసలు చిరునామాను షార్ట్ లింక్ వెనుక దాచింది",
        "hi": "लिंक “{v}” असली पता छोटे लिंक के पीछे छिपाता है",
    },
    "PERSONAL_PHONE_NUMBER": {
        "en": "Number “{v}” is a personal mobile, not the biller's",
        "te": "నంబర్ “{v}” వ్యక్తిగత మొబైల్, బిల్లర్‌ది కాదు",
        "hi": "नंबर “{v}” निजी मोबाइल है, बिलर का नहीं",
    },
    "DESTINATION_NOT_OFFICIAL": {
        "en": "“{v}” is not an official payment channel",
        "te": "“{v}” అధికారిక చెల్లింపు మార్గం కాదు",
        "hi": "“{v}” आधिकारिक भुगतान माध्यम नहीं है",
    },
    "DESTINATION_OFFICIAL": {
        "en": "“{v}” is an official channel of this biller",
        "te": "“{v}” ఈ బిల్లర్ అధికారిక మార్గం",
        "hi": "“{v}” इस बिलर का आधिकारिक माध्यम है",
    },
    "AMOUNT_MISMATCH": {
        "en": "It says {says} · biller record says {record}",
        "te": "ఇందులో {says} · బిల్లర్ రికార్డు ప్రకారం {record}",
        "hi": "इसमें {says} · बिलर के रिकॉर्ड में {record}",
    },
    "AMOUNT_MATCHES_BILLER": {
        "en": "{record} matches the biller record",
        "te": "{record} బిల్లర్ రికార్డుతో సరిపోతోంది",
        "hi": "{record} बिलर के रिकॉर्ड से मेल खाती है",
    },
    "AMOUNT_SPIKE": {
        "en": "{says} is {ratio}× this account's usual {usual}",
        "te": "{says} ఈ ఖాతా సాధారణ మొత్తం {usual} కు {ratio} రెట్లు",
        "hi": "{says} इस खाते की सामान्य राशि {usual} का {ratio} गुना है",
    },
    "AMOUNT_WITHIN_HISTORY": {
        "en": "{says} is normal for this account (usually {usual})",
        "te": "{says} ఈ ఖాతాకు సాధారణమే (సాధారణంగా {usual})",
        "hi": "{says} इस खाते के लिए सामान्य है (आमतौर पर {usual})",
    },
    "UNKNOWN_BILLER": {
        "en": "“{name}” is not in the biller registry",
        "te": "“{name}” బిల్లర్ రిజిస్ట్రీలో లేదు",
        "hi": "“{name}” बिलर रजिस्ट्री में नहीं है",
    },
    "PHRASE": {
        "en": "Phrase: “…{v}…”",
        "te": "పదబంధం: “…{v}…”",
        "hi": "वाक्यांश: “…{v}…”",
    },
}

# Most telling first; the short reply shows the top two.
_ORDER = (
    "KNOWN_SCAM_DESTINATION",
    "LOOKALIKE_VPA",
    "LOOKALIKE_DOMAIN",
    "APK_LINK",
    "AMOUNT_MISMATCH",
    "PERSONAL_PHONE_NUMBER",
    "SHORT_URL",
    "DISCONNECTION_THREAT",
    "KYC_UPDATE_LURE",
    "REFUND_LURE",
    "DESTINATION_NOT_OFFICIAL",
    "UNKNOWN_BILLER",
    "CONSUMER_NOT_FOUND",
    "AMOUNT_SPIKE",
    "URGENCY_PRESSURE",
    "MISSED_BY_EXTRACTION",
    "AMOUNT_MATCHES_BILLER",
    "DESTINATION_OFFICIAL",
    "BILLER_VERIFIED",
    "AMOUNT_WITHIN_HISTORY",
)


def t(lang: Lang, key: str, **values: str) -> str:
    text = T[key][lang]
    for name, value in values.items():
        text = text.replace(f"{{{name}}}", value)
    return text


def _money(value: Any) -> str:
    return f"₹{value:,.0f}" if isinstance(value, int | float) else ""


def _sentence(ev: dict[str, Any], check: dict[str, Any], lang: Lang) -> str:
    """One finding with its real values. Everything here was masked by the event layer."""
    d = ev.get("detail") or {}
    phrases = d.get("phrases") or []
    if phrases:
        return _REASONS["PHRASE"][lang].format(v=phrases[0])
    template = _REASONS.get(ev["code"], {}).get(lang)
    value = str((check.get("args") or {}).get("value") or d.get("vpa") or d.get("host") or "")
    name = d.get("query")
    needs_value = "{v}" in (template or "") and value in ("", "-")
    if template is None or needs_value or ("{name}" in template and not name):
        label = CODE_LABELS.get(ev["code"])
        return label[lang] if label else t(lang, "could_not_verify")
    ratio = d.get("ratio")
    return template.format(
        v=value,
        other=d.get("lookalike_of", ""),
        says=_money(d.get("claimed_amount", d.get("current_amount"))),
        record=_money(d.get("biller_amount")),
        usual=_money(d.get("usual_amount")),
        ratio=f"{ratio:.1f}" if isinstance(ratio, int | float) else "",
        name=name,
    )


def reason_lines(events: list[dict[str, Any]], verdict: dict[str, Any], lang: Lang) -> list[str]:
    """What the verdict cites, as sentences with real values, most telling first."""
    cited = {i for r in verdict["reasons"] for i in r["evidence_ids"]}
    found = [
        (ev, e)
        for e in events
        if e["type"] == "check"
        for ev in e.get("evidence", [])
        if ev["evidence_id"] in cited
    ]
    rank = {code: i for i, code in enumerate(_ORDER)}
    found.sort(key=lambda pair: rank.get(pair[0]["code"], len(_ORDER)))
    lines = dict.fromkeys(_sentence(ev, check, lang) for ev, check in found)
    return list(lines) or [t(lang, "could_not_verify")]


def unclear_photo(events: list[dict[str, Any]]) -> bool:
    """An image whose biller could not be read, and no scam found: ask for a better photo."""
    received = next((e for e in events if e["type"] == "received"), {})
    if received.get("input") != "image":
        return False
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    if verdict["verdict"] != "CAUTION":
        return False
    fields = next((e["fields"] for e in events if e["type"] == "extracted"), None)
    if fields is None:
        return True
    biller = fields["biller_name"]
    return not biller["value"] or biller["confidence"] < 0.5


def verdict_message(
    events: list[dict[str, Any]], lang: Lang, web_url: str, *, expired: bool = False
) -> str:
    """The short reply: verdict, two reasons with real values, one action, how to get the rest."""
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    v = verdict["verdict"]
    lines = [f"*{t(lang, f'headline_{v}')}*"]
    if expired:
        lines.append(t(lang, "no_answer"))
    if unclear_photo(events):
        lines.append(t(lang, "unclear_photo"))
        return "\n".join(lines)
    lines += [f"• {b}" for b in reason_lines(events, verdict, lang)[:SHORT_REASONS]]
    helpline = verified_fact("cybercrime_helpline")
    if v == "SCAM" and helpline is not None:
        lines.append(t(lang, "report", value=helpline.value))
    elif v != "SCAM":
        lines.append(t(lang, f"action_{v}"))
    lines.append(t(lang, "details_hint"))
    return "\n".join(lines)


def details_message(events: list[dict[str, Any]], lang: Lang, web_url: str) -> str:
    """The reply to DETAILS: the explanation and every finding of the sender's last check."""
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    lines = [t(lang, "details_title"), f"*{t(lang, 'headline_' + verdict['verdict'])}*"]
    explanation = next((e for e in reversed(events) if e["type"] == "explanation"), None)
    if explanation:
        lines += ["", explanation["text"]]
    lines += ["", *[f"• {b}" for b in reason_lines(events, verdict, lang)[:MAX_BULLETS]]]
    helpline = verified_fact("cybercrime_helpline")
    if verdict["verdict"] == "SCAM" and helpline is not None:
        lines += ["", t(lang, "report", value=helpline.value)]
    lines += ["", t(lang, "web", url=web_url), "", f"_{t(lang, 'footer')}_"]
    return "\n".join(lines)


def question_message(question: str, lang: Lang) -> str:
    return f"❓ {question}\n\n{t(lang, 'question_hint')}"
