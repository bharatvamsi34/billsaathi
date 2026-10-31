"""WhatsApp reply text in English, Telugu and Hindi, built only from masked check events.

Telugu reviewed by BV (native speaker) for the web app strings this mirrors; Hindi approximate.
Evidence labels mirror web/src/lib/codes.ts. Helpline numbers come from app/facts.py only.
"""

import re
from typing import Any, Literal

from app.facts import verified_fact

Lang = Literal["en", "te", "hi"]
LANGS: tuple[Lang, ...] = ("en", "te", "hi")

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


def switch_command(text: str | None) -> Lang | None:
    return SWITCH.get((text or "").strip().strip(".!").lower())


T: dict[str, dict[Lang, str]] = {
    "checking": {
        "en": "Checking… ⏳ This takes about 15 seconds.",
        "te": "తనిఖీ చేస్తోంది… ⏳ సుమారు 15 సెకన్లు పడుతుంది.",
        "hi": "जाँच हो रही है… ⏳ लगभग 15 सेकंड लगेंगे।",
    },
    "verdict_SAFE": {"en": "SAFE", "te": "సురక్షితం", "hi": "सुरक्षित"},
    "verdict_CAUTION": {"en": "CAUTION", "te": "జాగ్రత్త", "hi": "सावधान"},
    "verdict_SCAM": {"en": "SCAM", "te": "మోసం", "hi": "धोखा"},
    "headline_SAFE": {
        "en": "Checks passed. Pay only after you confirm.",
        "te": "తనిఖీలు సరిపోయాయి. మీరు నిర్ధారించిన తర్వాతే చెల్లించండి.",
        "hi": "जाँचें सही रहीं। अपनी पुष्टि के बाद ही भुगतान करें।",
    },
    "headline_CAUTION": {
        "en": "We could not confirm this. Do not pay yet.",
        "te": "దీన్ని నిర్ధారించలేకపోయాం. ఇప్పుడే చెల్లించవద్దు.",
        "hi": "इसकी पुष्टि नहीं हो सकी। अभी भुगतान न करें।",
    },
    "headline_SCAM": {
        "en": "This looks like a scam. Do not pay.",
        "te": "ఇది మోసంలా ఉంది. చెల్లించవద్దు.",
        "hi": "यह धोखाधड़ी लगती है। भुगतान न करें।",
    },
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
        "en": "📞 Report fraud: call {value}",
        "te": "📞 మోసాన్ని ఫిర్యాదు చేయండి: {value} కు కాల్ చేయండి",
        "hi": "📞 धोखाधड़ी की शिकायत: {value} पर कॉल करें",
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
        "en": "Please send the bill or payment message as text, or a photo or screenshot.",
        "te": "దయచేసి బిల్లు లేదా చెల్లింపు సందేశాన్ని టెక్స్ట్‌గా, లేదా ఫోటో / స్క్రీన్‌షాట్‌గా పంపండి.",
        "hi": "कृपया बिल या भुगतान संदेश टेक्स्ट, फ़ोटो या स्क्रीनशॉट के रूप में भेजें।",
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

ICONS = {"SAFE": "✅", "CAUTION": "⚠️", "SCAM": "⛔"}

CODE_LABELS: dict[str, dict[Lang, str]] = {
    "BILLER_VERIFIED": {"en": "Registered biller", "te": "నమోదైన బిల్లర్", "hi": "पंजीकृत बिलर"},
    "UNKNOWN_BILLER": {"en": "Biller not found in the registry", "te": "బిల్లర్ రిజిస్ట్రీలో లేరు", "hi": "बिलर रजिस्ट्री में नहीं मिला"},
    "AMOUNT_MATCHES_BILLER": {"en": "Amount matches the biller's records", "te": "మొత్తం బిల్లర్ రికార్డుతో సరిపోతోంది", "hi": "राशि बिलर के रिकॉर्ड से मेल खाती है"},
    "AMOUNT_MISMATCH": {"en": "Amount is different from the biller's records", "te": "మొత్తం బిల్లర్ రికార్డుకు భిన్నంగా ఉంది", "hi": "राशि बिलर के रिकॉर्ड से अलग है"},
    "CONSUMER_NOT_FOUND": {"en": "Consumer number not found", "te": "వినియోగదారు సంఖ్య కనబడలేదు", "hi": "उपभोक्ता संख्या नहीं मिली"},
    "AMOUNT_WITHIN_HISTORY": {"en": "Amount is normal for this account", "te": "ఈ ఖాతాకు మొత్తం సాధారణంగా ఉంది", "hi": "इस खाते के लिए राशि सामान्य है"},
    "AMOUNT_SPIKE": {"en": "Amount is much higher than usual", "te": "మొత్తం సాధారణం కంటే చాలా ఎక్కువ", "hi": "राशि सामान्य से बहुत ज़्यादा है"},
    "DESTINATION_OFFICIAL": {"en": "Official payment channel", "te": "అధికారిక చెల్లింపు మార్గం", "hi": "आधिकारिक भुगतान माध्यम"},
    "DESTINATION_NOT_OFFICIAL": {"en": "Not an official payment channel", "te": "అధికారిక చెల్లింపు మార్గం కాదు", "hi": "आधिकारिक भुगतान माध्यम नहीं"},
    "LOOKALIKE_DOMAIN": {"en": "Fake website that imitates the real one", "te": "నిజమైన దాన్ని అనుకరించే నకిలీ వెబ్‌సైట్", "hi": "असली जैसी दिखने वाली नकली वेबसाइट"},
    "LOOKALIKE_VPA": {"en": "Fake UPI ID that imitates the real one", "te": "నిజమైన దాన్ని అనుకరించే నకిలీ UPI ID", "hi": "असली जैसी दिखने वाली नकली UPI ID"},
    "KNOWN_SCAM_DESTINATION": {"en": "On the known-scam list", "te": "తెలిసిన మోసాల జాబితాలో ఉంది", "hi": "ज्ञात धोखाधड़ी सूची में है"},
    "PERSONAL_PHONE_NUMBER": {"en": "Personal mobile number, not the biller's", "te": "వ్యక్తిగత మొబైల్ నంబర్, బిల్లర్‌ది కాదు", "hi": "निजी मोबाइल नंबर, बिलर का नहीं"},
    "APK_LINK": {"en": "Asks you to install an app file (.apk)", "te": "యాప్ ఫైల్ (.apk) ఇన్‌స్టాల్ చేయమంటోంది", "hi": "ऐप फ़ाइल (.apk) डाउनलोड करने को कहता है"},
    "SHORT_URL": {"en": "Link is hidden behind a short link", "te": "లింక్ షార్ట్ లింక్ వెనుక దాచబడింది", "hi": "लिंक छोटे लिंक के पीछे छिपा है"},
    "DISCONNECTION_THREAT": {"en": "Threatens to cut your connection", "te": "కనెక్షన్ కట్ చేస్తామని బెదిరిస్తోంది", "hi": "कनेक्शन काटने की धमकी"},
    "KYC_UPDATE_LURE": {"en": "Asks you to update KYC", "te": "KYC అప్‌డేట్ చేయమంటోంది", "hi": "KYC अपडेट करने को कहता है"},
    "REFUND_LURE": {"en": "Promises a refund or cashback", "te": "రీఫండ్ లేదా క్యాష్‌బ్యాక్ వాగ్దానం", "hi": "रिफंड या कैशबैक का वादा"},
    "URGENCY_PRESSURE": {"en": "Pressures you to act right now", "te": "వెంటనే చేయమని ఒత్తిడి చేస్తోంది", "hi": "तुरंत करने का दबाव"},
    "MISSED_BY_EXTRACTION": {"en": "Found an extra link or number in the image", "te": "చిత్రంలో అదనపు లింక్ లేదా నంబర్ కనబడింది", "hi": "चित्र में एक और लिंक या नंबर मिला"},
}  # fmt: skip

MAX_BULLETS = 5


def t(lang: Lang, key: str, **values: str) -> str:
    text = T[key][lang]
    for name, value in values.items():
        text = text.replace(f"{{{name}}}", value)
    return text


def _bullets(events: list[dict[str, Any]], verdict: dict[str, Any], lang: Lang) -> list[str]:
    """One bullet per reason. English: the agent's own (masked) reason. Telugu/Hindi: the
    labels of the evidence it cites, until translated explanations land."""
    codes = {
        ev["evidence_id"]: ev["code"]
        for e in events
        if e["type"] == "check"
        for ev in e.get("evidence", [])
    }
    out: list[str] = []
    for reason in verdict["reasons"]:
        if lang == "en":
            text = reason["text"]
        else:
            labels = dict.fromkeys(
                CODE_LABELS[c][lang]
                for c in (codes.get(i) for i in reason["evidence_ids"])
                if c in CODE_LABELS
            )
            text = " · ".join(labels) or t(lang, "could_not_verify")
        if text and text not in out:
            out.append(text)
    return out[:MAX_BULLETS]


def verdict_message(
    events: list[dict[str, Any]], lang: Lang, web_url: str, *, expired: bool = False
) -> str:
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    v = verdict["verdict"]
    lines = [f"{ICONS[v]} *{t(lang, f'verdict_{v}')}*", t(lang, f"headline_{v}")]
    if expired:
        lines.append(t(lang, "no_answer"))
    bullets = _bullets(events, verdict, lang)
    if bullets:
        lines += ["", *[f"• {b}" for b in bullets]]
    helpline = verified_fact("cybercrime_helpline")
    if v == "SCAM" and helpline is not None:
        lines += ["", t(lang, "report", value=helpline.value)]
    lines += ["", t(lang, "web", url=web_url), "", f"_{t(lang, 'footer')}_"]
    return "\n".join(lines)


def question_message(question: str, lang: Lang) -> str:
    return f"❓ {question}\n\n{t(lang, 'question_hint')}"
