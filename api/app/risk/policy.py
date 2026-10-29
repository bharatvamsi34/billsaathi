"""Deterministic risk engine: the verdict floor that the model can never go below.

The floor comes only from tool evidence (and tool failures). The model may submit a
stricter verdict, never a weaker one. SAFE is never decided here on its own: the floor is
SAFE only when no evidence forbids it, and submit_verdict separately requires every item of
safe_requirements(). Policy: data/synthetic/README.md and docs/AGENT_DESIGN.md.
"""

import re
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from app.agent.evidence import ToolEvidence, ToolResult
from app.schemas import DestinationKind, PaymentDestination, Verdict
from app.schemas import EvidenceCode as C

SEVERITY = {Verdict.SAFE: 0, Verdict.CAUTION: 1, Verdict.SCAM: 2}

STRONG_SCAM = frozenset({C.LOOKALIKE_DOMAIN, C.LOOKALIKE_VPA, C.KNOWN_SCAM_DESTINATION, C.APK_LINK})
SCAM_PHRASING = frozenset({C.DISCONNECTION_THREAT, C.KYC_UPDATE_LURE, C.REFUND_LURE})
HARD_FAIL = frozenset(
    {
        C.UNKNOWN_BILLER,
        C.CONSUMER_NOT_FOUND,
        C.AMOUNT_MISMATCH,
        C.AMOUNT_SPIKE,
        C.DESTINATION_NOT_OFFICIAL,
        C.SHORT_URL,
        C.PERSONAL_PHONE_NUMBER,
    }
)
MIN_CONFIDENCE = (
    0.8  # below this on amount or a destination, SAFE is blocked (never a reason FOR safe)
)


def at_least(verdict: Verdict, floor: Verdict) -> bool:
    return SEVERITY[verdict] >= SEVERITY[floor]


def stricter(a: Verdict, b: Verdict) -> Verdict:
    return a if SEVERITY[a] >= SEVERITY[b] else b


class Floor(BaseModel):
    verdict: Verdict
    rule: str  # which policy rule set the floor
    evidence_ids: list[str]  # evidence behind it, for citations and the audit log


def floor_verdict(evidence: Iterable[ToolEvidence], tool_failures: int = 0) -> Floor:
    ev = list(evidence)
    strong = [e.evidence_id for e in ev if e.code in STRONG_SCAM]
    if strong:
        return Floor(verdict=Verdict.SCAM, rule="strong_scam_signal", evidence_ids=strong)
    unofficial = [e.evidence_id for e in ev if e.code == C.DESTINATION_NOT_OFFICIAL]
    wording = [e.evidence_id for e in ev if e.code in SCAM_PHRASING]
    if unofficial and wording:
        return Floor(
            verdict=Verdict.SCAM,
            rule="unofficial_destination_with_scam_wording",
            evidence_ids=unofficial + wording,
        )
    hard = [e.evidence_id for e in ev if e.code in HARD_FAIL]
    if hard:
        return Floor(verdict=Verdict.CAUTION, rule="hard_check_failed", evidence_ids=hard)
    if tool_failures:
        return Floor(verdict=Verdict.CAUTION, rule="could_not_verify", evidence_ids=[])
    return Floor(verdict=Verdict.SAFE, rule="no_risk_found", evidence_ids=[])


def destination_key(kind: DestinationKind | str, value: str) -> tuple[str, str]:
    """Compare a destination from extraction with the one a tool was called with."""
    v = value.strip().lower()
    if kind == DestinationKind.URL:
        v = re.sub(r"^https?://", "", v).removeprefix("www.").rstrip("/")
    elif kind == DestinationKind.PHONE:
        v = re.sub(r"\D", "", v)[-10:]
    return str(kind), v


def safe_requirements(
    results: Sequence[ToolResult],
    destinations: Sequence[PaymentDestination],
    low_confidence_fields: Sequence[str] = (),
) -> list[str]:
    """What is still missing before SAFE may be accepted. Empty list = SAFE allowed."""
    missing: list[str] = []
    codes = {e.code for r in results for e in r.evidence}
    if any(not r.ok for r in results):
        missing.append("a tool call failed")
    if floor_verdict(e for r in results for e in r.evidence).verdict != Verdict.SAFE:
        missing.append("risk evidence found")
    for code, label in (
        (C.BILLER_VERIFIED, "biller verified"),
        (C.AMOUNT_MATCHES_BILLER, "amount matches the biller's own amount"),
        (C.AMOUNT_WITHIN_HISTORY, "amount in line with bill history"),
    ):
        if code not in codes:
            missing.append(f"{label} (not shown by any tool)")
    verified_biller = next(
        (r.data.get("biller_id") for r in results if C.BILLER_VERIFIED in r.codes), None
    )
    checked = {
        destination_key(r.args["kind"], r.args["value"]): r
        for r in results
        if r.tool == "check_payment_destination" and r.ok
    }
    for d in destinations:
        result = checked.get(destination_key(d.kind, d.value))
        if result is None:
            missing.append(f"destination not checked: {d.kind} {d.value}")
        elif result.codes != {C.DESTINATION_OFFICIAL}:
            missing.append(f"destination not official: {d.kind} {d.value}")
        elif result.data.get("biller_id") != verified_biller:
            missing.append(f"destination belongs to another biller: {d.kind} {d.value}")
    for field in low_confidence_fields:
        missing.append(f"low extraction confidence on {field}")
    return missing


def final_floor(floor: Floor, missing: Sequence[str]) -> Verdict:
    """The weakest verdict the code allows: SAFE only if nothing is missing, else >= CAUTION."""
    if floor.verdict == Verdict.SAFE and not missing:
        return Verdict.SAFE
    return stricter(floor.verdict, Verdict.CAUTION)
