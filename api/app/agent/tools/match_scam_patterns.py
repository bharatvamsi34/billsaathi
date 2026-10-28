"""match_scam_patterns: find known bill-scam phrasings in the message text."""

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


class Args(BaseModel):
    text: str = Field(description="Full text of the message or bill")


@define_tool(
    "match_scam_patterns",
    "Search the message for known Indian bill-scam phrasings (disconnection threats, KYC "
    "update requests, refund lures, urgency) in English, Hinglish, Hindi and Telugu.",
    Args,
)
def match_scam_patterns(args: Args) -> Outcome:
    by_code: dict[str, list[dict[str, str]]] = {}
    for p in PATTERNS:
        m = p.regex.search(args.text)
        if m:
            by_code.setdefault(p.code.value, []).append(
                {"pattern_id": p.id, "match": m.group(0)[:80]}
            )
    findings = [
        Finding(EvidenceCode(code), _SUMMARY[code], {"matches": matches})
        for code, matches in by_code.items()
    ]
    return Outcome(findings, {"matched": bool(findings), "codes": sorted(by_code)})
