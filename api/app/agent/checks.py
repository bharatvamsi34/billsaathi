"""submit_verdict's checks: five deterministic checks, then the LLM claims judge.

Every check returns a Refusal (the first one that fails is returned to the agent) or None.
The judge runs only after all deterministic checks pass; it can only refuse, and it fails
closed: if it cannot run or answers badly, the submission is refused.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.agent.evidence import EvidenceRecord, ToolResult
from app.agent.milestones import find_destinations
from app.agent.prompts import JUDGE_SYSTEM
from app.agent.protocol import Refusal, SubmitVerdictArgs
from app.extract.extract import parse_json
from app.facts import FACTS, verified_fact
from app.models.base import LLMClient, LLMError, LLMResponse, Message
from app.risk.policy import at_least, destination_key, floor_verdict, safe_requirements
from app.schemas import PaymentDestination, Verdict


@dataclass
class CheckContext:
    args: SubmitVerdictArgs
    record: EvidenceRecord
    destinations: list[PaymentDestination]
    low_confidence: list[str]

    @property
    def results(self) -> tuple[ToolResult, ...]:
        return self.record.tool_results

    def floor(self):
        evidence = [e for r in self.results for e in r.evidence]
        return floor_verdict(evidence, tool_failures=sum(not r.ok for r in self.results))


def citations_exist(ctx: CheckContext) -> Refusal | None:
    for i, reason in enumerate(ctx.args.reasons, 1):
        if not reason.evidence_ids:
            return Refusal(
                rule="citations_exist",
                message=f"Reason {i} cites no evidence_id. Every reason must cite evidence.",
            )
        unknown = [eid for eid in reason.evidence_ids if ctx.record.evidence(eid) is None]
        if unknown:
            return Refusal(
                rule="citations_exist",
                message=f"Reason {i} cites {', '.join(unknown)}, which no tool produced in this run. "
                "Cite evidence_id values from tool results.",
            )
    return None


def destinations_checked(ctx: CheckContext) -> Refusal | None:
    checked = {
        destination_key(r.args.get("kind", ""), r.args.get("value", ""))
        for r in ctx.results
        if r.tool == "check_payment_destination" and "kind" in r.args and "value" in r.args
    }
    missing = [d for d in ctx.destinations if destination_key(d.kind, d.value) not in checked]
    if missing:
        listed = "; ".join(f"{d.kind} {d.value}" for d in missing)
        return Refusal(
            rule="destinations_checked",
            message=f"These destinations were never checked: {listed}. Call check_payment_destination for each.",
        )
    return None


def hard_rule_floor(ctx: CheckContext) -> Refusal | None:
    floor = ctx.floor()
    if not at_least(ctx.args.verdict, floor.verdict):
        return Refusal(
            rule="hard_rule_floor",
            message=f"The evidence requires at least {floor.verdict.value} (rule {floor.rule}; "
            f"evidence {', '.join(floor.evidence_ids) or 'failed tool calls'}). A weaker verdict is not allowed.",
        )
    return None


def safe_needs_every_check(ctx: CheckContext) -> Refusal | None:
    if ctx.args.verdict != Verdict.SAFE:
        return None
    missing = safe_requirements(ctx.results, ctx.destinations, ctx.low_confidence)
    if missing:
        return Refusal(
            rule="safe_requirements",
            message="SAFE needs every check to pass. Missing: " + "; ".join(missing) + ".",
        )
    return None


def facts_verified(ctx: CheckContext) -> Refusal | None:
    bad_keys = [k for k in ctx.args.facts if verified_fact(k) is None]
    if bad_keys:
        return Refusal(
            rule="facts_verified",
            message=f"Unknown or unverified fact keys: {', '.join(bad_keys)}.",
        )
    cited_values = {
        destination_key(r.args["kind"], r.args["value"])
        for r in ctx.results
        for e in r.evidence
        if r.tool == "check_payment_destination"
        and any(e.evidence_id in reason.evidence_ids for reason in ctx.args.reasons)
    }
    for i, reason in enumerate(ctx.args.reasons, 1):
        for fact in FACTS.values():
            if fact.value in reason.text:
                return Refusal(
                    rule="facts_verified",
                    message=f"Reason {i} types {fact.label} itself. Add the fact key {fact.key!r} to facts instead.",
                )
        for d in find_destinations(reason.text):
            if destination_key(d.kind, d.value) not in cited_values:
                return Refusal(
                    rule="facts_verified",
                    message=f"Reason {i} contains a {d.kind} that is not in the evidence it cites. "
                    "Do not write phone numbers or links in reasons.",
                )
    return None


DETERMINISTIC_CHECKS: tuple[Callable[[CheckContext], Refusal | None], ...] = (
    citations_exist,
    destinations_checked,
    hard_rule_floor,
    safe_needs_every_check,
    facts_verified,
)


def run_deterministic(ctx: CheckContext) -> Refusal | None:
    for check in DETERMINISTIC_CHECKS:
        refusal = check(ctx)
        if refusal is not None:
            return refusal
    return None


# --- claims check (LLM judge) ---


class JudgeItem(BaseModel):
    index: int
    supported: bool
    why: str


class JudgeReply(BaseModel):
    reasons: list[JudgeItem]


def claims_check(
    ctx: CheckContext, judge: LLMClient, model: str
) -> tuple[Refusal | None, LLMResponse | None]:
    """One judge call. Returns (refusal or None, the judge's response for metrics)."""
    payload = {
        "reasons": [
            {
                "index": i,
                "text": reason.text,
                "evidence": [
                    {
                        "evidence_id": e.evidence_id,
                        "code": e.code.value,
                        "summary": e.summary,
                        "detail": e.detail,
                    }
                    for eid in reason.evidence_ids
                    if (e := ctx.record.evidence(eid)) is not None
                ],
            }
            for i, reason in enumerate(ctx.args.reasons)
        ]
    }
    unavailable = Refusal(
        rule="claims_check_unavailable",
        message="The claims check could not confirm your reasons. Submit again with clear reasons.",
    )
    try:
        resp = judge.respond(
            system=JUDGE_SYSTEM,
            messages=[
                Message(role="user", text=json.dumps(payload, ensure_ascii=False, default=str))
            ],
            model=model,
            effort="low",
            max_output_tokens=2048,
        )
    except LLMError:
        return unavailable, None
    try:
        reply = JudgeReply.model_validate(parse_json(resp.text))
    except (ValueError, ValidationError):
        return unavailable, resp
    if sorted(item.index for item in reply.reasons) != list(range(len(ctx.args.reasons))):
        return unavailable, resp
    unsupported = [
        item for item in sorted(reply.reasons, key=lambda x: x.index) if not item.supported
    ]
    if unsupported:
        detail = " ".join(f"Reason {item.index + 1}: {item.why}" for item in unsupported)
        return Refusal(
            rule="claims_check",
            message=f"Some reasons are not supported by the evidence they cite. {detail}",
        ), resp
    return None, resp
