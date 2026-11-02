"""WhatsApp reply text in English, Telugu and Hindi, built only from masked check events.

Telugu reviewed by BV (native speaker) for the web app strings this mirrors; Hindi approximate.
Evidence labels mirror web/src/lib/codes.ts. Helpline numbers come from app/facts.py only.
"""

import re
from typing import Any

from app.facts import verified_fact
from app.labels import CODE_LABELS, HEADLINES, LANGS, Lang  # noqa: F401

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
    lines = [f"{ICONS[v]} *{t(lang, f'verdict_{v}')}*", HEADLINES[v][lang]]
    if expired:
        lines.append(t(lang, "no_answer"))
    explanation = next((e for e in reversed(events) if e["type"] == "explanation"), None)
    if explanation:
        lines += ["", explanation["text"]]
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
