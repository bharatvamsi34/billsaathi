"""Milestone check after extraction (deterministic, no model).

Every link, UPI ID and Indian phone number in the raw text must be among the extracted
payment destinations. Anything extraction missed is added and recorded as
MISSED_BY_EXTRACTION, so the agent has to check it before any SAFE verdict.

Detected: links on any domain ending, including punycode and non-Latin names; mobile, toll-free
(1800/1860) and landline numbers (landline needs its 0 or +91), in any Indian script's digits.
Not detected: contacts spelled out in words or "dot"; landlines without 0 or +91, which cannot
be told apart from consumer numbers.
"""

import re

from app.agent.evidence import ToolEvidence, ToolResult, make_id
from app.contacts import canonical_phone, normalise_text
from app.pii import mask_phone
from app.schemas import DestinationKind, EvidenceCode, PaymentDestination

SOURCE = "milestone_check"

_UPI = re.compile(
    r"(?<![\w.@-])[A-Za-z0-9][A-Za-z0-9._-]{1,255}@[A-Za-z][A-Za-z0-9]{1,63}(?![\w@])"
)
# A domain label: letters, digits and hyphens in any script. Indic vowel signs are not \\w, and the
# danda (sentence end) is left out.
_CH = r"[\w\-\u0900-\u0963\u0966-\u0DFF]"
_IDN_TLDS = "भारत|भारतम्|భారత్|ভারত|ভাৰত|ભારત|ਭਾਰਤ|இந்தியா|ಭಾರತ|ഭാരതം|ଭାରତ"
_URL = re.compile(
    rf"(?:https?://\S+|www\.\S+|(?<!{_CH})(?<![@.])(?:{_CH}+\.)+(?:xn--[A-Za-z0-9-]+|[A-Za-z]{{2,24}}|{_IDN_TLDS})(?!{_CH})(?:/[^\s]*)?)",
    re.IGNORECASE,
)
# Always links, whatever comes before them.
_COMMON_TLDS = frozenset("example com in org net io app info online site link me xyz ly gl gd at cc co".split())  # fmt: skip
# Bill wording joined by a dot, which only looks like a domain: "K.No", "Co.Ltd", "Mr.Rao", "Rs.Five".
_NO_WORDS = frozenset("k a c s sr ac acc ref bill cons consumer mtr meter mob ph tel tin".split())
_LTD_WORDS = frozenset("co pvt pte".split())
_PREFIXES = frozenset("mr mrs ms dr shri smt sri rs re inr".split())

_PHONES = (
    # Mobile: 98765 43210, 987 654 3210, 9876 543 210, with +91 or 0.
    re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?([6-9]\d{4})[\s-]?(\d{5})(?!\d)"),
    re.compile(r"(?<![\w-])(?:\+?91[\s-]?|0)?([6-9]\d{2})[\s-](\d{3})[\s-](\d{4})(?![\d-])"),
    re.compile(r"(?<![\w-])(?:\+?91[\s-]?|0)?([6-9]\d{3})[\s-](\d{3})[\s-](\d{3})(?![\d-])"),
    # Toll-free: 1800 123 4567, 1860-000-1001, 18001234567.
    re.compile(r"(?<![\w-])(?:\+?91[\s-]?|0)?(18(?:00|60))[\s-]?(\d{3})[\s-]?(\d{3,4})(?![\d-])"),
    # Landline: 040-2345-6789, 011 2345 6789, +91 40 2345 6789. 10 digits after the 0 or +91, checked below.
    re.compile(r"(?<![\w-])(?:\+91[\s-]?|0)\(?([1-5]\d{1,3})\)?[\s-]?(\d{2,4})[\s-]?(\d{2,4})(?![\d-])"),
)  # fmt: skip


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:!?)।")


def _host(url: str) -> str:
    v = re.sub(r"^https?://", "", url.strip().lower()).removeprefix("www.")
    return v.split("/")[0]


def _is_link(token: str) -> bool:
    """False only for what is plainly not a link. New false alarms are fine; missed links are not."""
    if "://" in token or token.lower().startswith("www."):
        return True
    labels = token.split("/")[0].lower().split(".")
    if labels[-1] in _COMMON_TLDS:
        return True
    if not any(ch.isalpha() for label in labels[:-1] for ch in label):
        return False  # "9.pm"
    if len(labels) == 2:
        first, last = labels
        written_last = token.split("/")[0].split(".")[-1]
        if (last == "no" and first in _NO_WORDS) or (last == "ltd" and first in _LTD_WORDS):
            return False
        if first in _PREFIXES and written_last[0].isupper():
            return False
    return True


def _is_phone(groups: tuple[str, ...]) -> bool:
    digits = "".join(groups)
    if digits.startswith(("1800", "1860")):
        return len(digits) in (10, 11)
    return len(digits) == 10


def find_destinations(text: str) -> list[PaymentDestination]:
    """Every UPI ID, link and phone number in the text, in order, without duplicates."""
    found: list[PaymentDestination] = []
    text = normalise_text(text)
    rest = text
    for m in _UPI.finditer(text):
        found.append(PaymentDestination(kind=DestinationKind.UPI, value=m.group(0)))
    rest = _UPI.sub(" ", rest)  # so "demopower.bill@demobank" is not also read as a link
    for m in _URL.finditer(rest):
        if _is_link(_clean_url(m.group(0))):
            found.append(PaymentDestination(kind=DestinationKind.URL, value=_clean_url(m.group(0))))
    for pattern in _PHONES:
        for m in pattern.finditer(rest):
            if _is_phone(m.groups()):
                found.append(PaymentDestination(kind=DestinationKind.PHONE, value="".join(m.groups())))  # fmt: skip
    unique: dict[tuple[str, str], PaymentDestination] = {}
    for d in found:
        unique.setdefault(_key(d), d)
    return list(unique.values())


def _key(d: PaymentDestination) -> tuple[str, str]:
    if d.kind == DestinationKind.URL:
        return "url", _host(d.value)
    if d.kind == DestinationKind.PHONE:
        return "phone", canonical_phone(d.value)
    return str(d.kind), d.value.strip().lower()


def reconcile(
    text: str | None, extracted: list[PaymentDestination]
) -> tuple[list[PaymentDestination], ToolResult | None]:
    """Destinations to check (extracted + missed), and a record entry if any were missed."""
    if not text:
        return list(extracted), None
    known = {_key(d) for d in extracted}
    missed = [d for d in find_destinations(text) if _key(d) not in known]
    if not missed:
        return list(extracted), None
    evidence = []
    for d in missed:
        shown = mask_phone(d.value) if d.kind == DestinationKind.PHONE else d.value
        evidence.append(
            ToolEvidence(
                evidence_id=make_id("ev", SOURCE, d.kind, d.value),
                code=EvidenceCode.MISSED_BY_EXTRACTION,
                source=SOURCE,
                summary=f"The text contains a {d.kind} that extraction missed: {shown}. It must be checked.",
                detail={"kind": str(d.kind), "value": shown},
            )
        )
    result = ToolResult(
        tool=SOURCE,
        call_id=make_id("call", SOURCE, [d.model_dump(mode="json") for d in missed]),
        args={"missed": len(missed)},
        ok=True,
        evidence=tuple(evidence),
    )
    return list(extracted) + missed, result
