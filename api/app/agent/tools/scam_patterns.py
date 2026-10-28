"""Known Indian bill-scam phrasings in English, Hinglish, Hindi and Telugu.

Each pattern has a stable id so a finding can say exactly which phrasing matched. Indian
scripts have no reliable \\b word boundaries, so those patterns match substrings.
Telugu patterns are to be reviewed by a native speaker (BV).
"""

import re
from dataclasses import dataclass

from app.schemas import EvidenceCode


@dataclass(frozen=True)
class ScamPattern:
    id: str
    code: EvidenceCode
    lang: str
    regex: re.Pattern[str]


def _p(pid: str, code: EvidenceCode, lang: str, pattern: str) -> ScamPattern:
    return ScamPattern(pid, code, lang, re.compile(pattern, re.IGNORECASE))


D, K, R, U = (
    EvidenceCode.DISCONNECTION_THREAT,
    EvidenceCode.KYC_UPDATE_LURE,
    EvidenceCode.REFUND_LURE,
    EvidenceCode.URGENCY_PRESSURE,
)

PATTERNS: tuple[ScamPattern, ...] = (
    # Disconnection threats
    _p("disconnect_en", D, "en", r"\b(disconnect(ed|ion)?|deactivat(ed|ion)|power (supply )?(will be )?cut)\b"),
    _p("supply_cut_en", D, "en", r"\b(electricity|power|connection|supply|service)\b.{0,25}\b(cut|stopped|suspended|blocked)\b"),
    _p("cut_hinglish", D, "hi-Latn", r"\b(connection|light|bijli|power|current)\b.{0,20}\b(cut|kat|kaat|band)\b.{0,15}\b(ho|kar|diya|dega|jayega|jaega)"),
    _p("cut_hi", D, "hi", r"(कनेक्शन|बिजली|लाइट|सप्लाई).{0,30}(काट|कट|बंद)"),
    _p("cut_te", D, "te", r"(కనెక్షన్|కరెంట్|విద్యుత్|పవర్|సరఫరా).{0,30}(కట్|నిలిపి|తొలగి|ఆపి|ఆపేస్త)"),
    # KYC / document update lures
    _p("kyc_en", K, "en", r"\bkyc\b|\b(update|verify|link)\b.{0,20}\b(aadhaa?r|pan|kyc|account details)\b"),
    _p("kyc_hi", K, "hi", r"केवाईसी|(आधार|पैन).{0,20}(अपडेट|लिंक|सत्यापन)"),
    _p("kyc_te", K, "te", r"కేవైసీ|(ఆధార్|పాన్).{0,20}(అప్‌డేట్|అప్డేట్|లింక్|ధృవీకర)"),
    # Refund / cashback lures
    _p("refund_en", R, "en", r"\b(refund|cashback|excess (amount|payment)|overpaid|over-?charged)\b"),
    _p("refund_hinglish", R, "hi-Latn", r"\b(paise|paisa|amount|rakam)\b.{0,15}\b(wapas|vapas)\b"),
    _p("refund_hi", R, "hi", r"रिफंड|कैशबैक|(पैसे|राशि|रकम).{0,15}वापस"),
    _p("refund_te", R, "te", r"రీఫండ్|క్యాష్‌బ్యాక్|(డబ్బు|మొత్తం|నగదు).{0,20}(తిరిగి|వాపసు)"),
    # Urgency pressure
    _p("urgent_en", U, "en", r"\b(immediately|urgent(ly)?|right now|within \d+ (minutes?|mins?|hours?|hrs?)|last (chance|warning)|tonight)\b"),
    _p("urgent_hinglish", U, "hi-Latn", r"\b(turant|jaldi|aaj raat|abhi)\b"),
    _p("urgent_hi", U, "hi", r"तुरंत|फ़ौरन|फौरन|आज रात|अंतिम चेतावनी"),
    _p("urgent_te", U, "te", r"వెంటనే|తక్షణమే|ఈ రాత్రి|ఈరోజు రాత్రి|చివరి హెచ్చరిక"),
)  # fmt: skip
