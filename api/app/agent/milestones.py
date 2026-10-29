"""Milestone check after extraction (deterministic, no model).

Every link, UPI ID and Indian mobile number in the raw text must be among the extracted
payment destinations. Anything extraction missed is added and recorded as
MISSED_BY_EXTRACTION, so the agent has to check it before any SAFE verdict.
"""

import re

from app.agent.evidence import ToolEvidence, ToolResult, make_id
from app.pii import mask_phone
from app.schemas import DestinationKind, EvidenceCode, PaymentDestination

SOURCE = "milestone_check"

_UPI = re.compile(
    r"(?<![\w.@-])[A-Za-z0-9][A-Za-z0-9._-]{1,255}@[A-Za-z][A-Za-z0-9]{1,63}(?![\w@])"
)
# Links need a scheme, "www." or a known top-level domain, so "K.No." or "Co. Ltd" never match.
_TLDS = "example|com|in|co\\.in|org|net|io|app|info|online|site|link|me|xyz|ly|gl|gd|at|cc|co"
_URL = re.compile(
    rf"(?:https?://\S+|www\.\S+|(?<![\w@.-])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:{_TLDS})(?![A-Za-z0-9-])(?:/[^\s]*)?)",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<![\d])(?:\+91[\s-]?|0)?([6-9]\d{4})[\s-]?(\d{5})(?!\d)")


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:!?)।")


def _host(url: str) -> str:
    v = re.sub(r"^https?://", "", url.strip().lower()).removeprefix("www.")
    return v.split("/")[0]


def find_destinations(text: str) -> list[PaymentDestination]:
    """Every UPI ID, link and mobile number in the text, in order, without duplicates."""
    found: list[PaymentDestination] = []
    rest = text
    for m in _UPI.finditer(text):
        found.append(PaymentDestination(kind=DestinationKind.UPI, value=m.group(0)))
    rest = _UPI.sub(" ", rest)  # so "demopower.bill@demobank" is not also read as a link
    for m in _URL.finditer(rest):
        found.append(PaymentDestination(kind=DestinationKind.URL, value=_clean_url(m.group(0))))
    for m in _PHONE.finditer(rest):
        found.append(PaymentDestination(kind=DestinationKind.PHONE, value=m.group(1) + m.group(2)))
    unique: dict[tuple[str, str], PaymentDestination] = {}
    for d in found:
        unique.setdefault(_key(d), d)
    return list(unique.values())


def _key(d: PaymentDestination) -> tuple[str, str]:
    if d.kind == DestinationKind.URL:
        return "url", _host(d.value)
    if d.kind == DestinationKind.PHONE:
        return "phone", re.sub(r"\D", "", d.value)[-10:]
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
