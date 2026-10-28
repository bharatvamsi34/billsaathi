"""match_scam_patterns: find known bill-scam phrasings in the message text.

Links and UPI IDs are masked first: words inside them ("kyc-update.example",
"bill.refund@bank") are judged by check_payment_destination, not as message wording.
"""

import re

from pydantic import BaseModel, Field

from app.agent.tools.base import Finding, Outcome, define_tool
from app.agent.tools.scam_patterns import PATTERNS
from app.schemas import EvidenceCode

_SUMMARY = {
    "DISCONNECTION_THREAT": "Threatens to cut the connection.",
    "KYC_UPDATE_LURE": "Asks to update KYC or documents.",
    "REFUND_LURE": "Promises a refund or cashback.",
    "URGENCY_PRESSURE": "Pushes the reader to act immediately.",
}


_DESTINATIONS = re.compile(
    r"[A-Za-z0-9._-]+@[A-Za-z0-9]+"  # UPI ID
    r"|(?:https?://)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?:/\S*)?"  # link / domain
)


class Args(BaseModel):
    text: str = Field(description="Full text of the message or bill")


@define_tool(
    "match_scam_patterns",
    "Search the message for known Indian bill-scam phrasings (disconnection threats, KYC "
    "update requests, refund lures, urgency) in English, Hinglish, Hindi and Telugu.",
    Args,
)
def match_scam_patterns(args: Args) -> Outcome:
    wording = _DESTINATIONS.sub(" ", args.text)
    by_code: dict[str, list[dict[str, str]]] = {}
    for p in PATTERNS:
        m = p.regex.search(wording)
        if m:
            by_code.setdefault(p.code.value, []).append(
                {"pattern_id": p.id, "match": m.group(0)[:80]}
            )
    findings = [
        Finding(EvidenceCode(code), _SUMMARY[code], {"matches": matches})
        for code, matches in by_code.items()
    ]
    return Outcome(findings, {"matched": bool(findings), "codes": sorted(by_code)})
