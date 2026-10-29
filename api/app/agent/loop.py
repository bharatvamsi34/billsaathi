"""The verification agent loop (docs/AGENT_DESIGN.md).

start() runs until the agent's verdict is accepted, the run is forced to an end, or the
agent asks the user one question (status "needs_user_input"; continue with resume()).
Every tool result, refusal, question, reply and verdict goes into the EvidenceRecord.
"""

import json
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.agent import control_tools
from app.agent.checks import CheckContext, claims_check, run_deterministic
from app.agent.evidence import EvidenceRecord, RecordEntry, ToolResult, make_id
from app.agent.milestones import reconcile
from app.agent.prompts import AGENT_SYSTEM, user_message
from app.agent.protocol import (
    AgentInput,
    AskUserArgs,
    FinalVerdict,
    Metrics,
    PendingQuestion,
    Reason,
    Refusal,
    RunStatus,
    SubmitVerdictArgs,
)
from app.agent.tools import TOOLS
from app.bbps_mock import service
from app.models.base import (
    AssistantTurn,
    ConvItem,
    LLMClient,
    LLMError,
    ToolCall,
    ToolOutput,
    ToolOutputs,
    Usage,
    UserText,
)
from app.pii import mask_id
from app.risk.policy import floor_verdict, stricter
from app.schemas import EvidenceCode, PaymentDestination, Verdict


@dataclass
class AgentConfig:
    model: str = "muse-spark-1.3"
    judge_model: str = "muse-spark-1.3"
    effort: str = "low"
    max_output_tokens: int = 4096
    max_tool_calls: int = 8
    max_submits: int = 3
    max_asks: int = 1
    max_model_turns: int = 6


@dataclass
class AgentSession:
    run_id: str
    input: AgentInput
    config: AgentConfig
    client: LLMClient
    judge: LLMClient
    record: EvidenceRecord
    destinations: list[PaymentDestination]
    conversation: list[ConvItem] = field(default_factory=list)
    status: RunStatus = "running"
    metrics: Metrics = field(default_factory=Metrics)
    submits: int = 0
    asks: int = 0
    nudged: bool = False
    pending: PendingQuestion | None = None
    pending_outputs: list[ToolOutput] = field(default_factory=list)
    final: FinalVerdict | None = None


TOOL_SPECS = [{"type": "function", **t.spec()} for t in TOOLS.values()] + [
    {"type": "function", **s} for s in control_tools.SPECS
]


def start(
    client: LLMClient,
    agent_input: AgentInput,
    *,
    judge: LLMClient | None = None,
    config: AgentConfig | None = None,
    run_id: str | None = None,
    listener: Callable[[RecordEntry], None] | None = None,
) -> AgentSession:
    run_id = run_id or uuid.uuid4().hex[:12]
    record = EvidenceRecord(run_id, listener=listener)
    destinations, missed = reconcile(
        agent_input.raw_text, agent_input.extraction.payment_destinations.value
    )
    session = AgentSession(
        run_id=run_id,
        input=agent_input,
        config=config or AgentConfig(),
        client=client,
        judge=judge or client,
        record=record,
        destinations=destinations,
    )
    record.append(
        "note",
        {
            "event": "run_started",
            "destinations": len(destinations),
            "language": agent_input.language,
        },
    )
    if missed is not None:
        record.add_tool_result(missed, origin="mandatory")
    t0 = time.perf_counter()
    mandatory = _mandatory_checks(session)
    session.metrics.latency_ms += (time.perf_counter() - t0) * 1000
    briefing = "\n\n".join(
        [
            user_message(agent_input, destinations),
            "Mandatory checks already run at fixed points (cite these evidence_id values):",
            *(
                f"{r.tool} {json.dumps(r.args, ensure_ascii=False, default=str)}\n-> {_tool_output(r)}"
                for r in mandatory
            ),
        ]
    )
    session.conversation.append(UserText(text=briefing))
    _run(session)
    return session


def _mandatory_checks(session: AgentSession) -> list[ToolResult]:
    """Fixed-point checks run by code before the agent's first turn; the agent cannot skip them.

    Wave 1 (parallel): lookup_biller, check_payment_destination for every destination
    (including any the milestone check added), match_scam_patterns on the raw text.
    Wave 2 (parallel, once the biller is verified): fetch_bill and get_bill_history.
    """
    e = session.input.extraction
    wave1: list[tuple[str, dict]] = [
        ("lookup_biller", {"name": e.biller_name.value, "category": e.biller_category.value}),
        *(
            ("check_payment_destination", {"kind": d.kind, "value": d.value})
            for d in session.destinations
        ),
    ]
    if session.input.raw_text:
        wave1.append(("match_scam_patterns", {"text": session.input.raw_text}))
    results = _run_waves(session, wave1)
    biller_id = (
        results[0].data.get("biller_id")
        if EvidenceCode.BILLER_VERIFIED in results[0].codes
        else None
    )
    consumer, amount = e.consumer_number.value, e.amount.value
    if biller_id and consumer and amount is not None:
        common = {"biller_id": biller_id, "consumer_number": consumer}
        results += _run_waves(
            session,
            [
                ("fetch_bill", common | {"claimed_amount": amount}),
                ("get_bill_history", common | {"current_amount": amount}),
            ],
        )
    return results


def _run_waves(session: AgentSession, calls: list[tuple[str, dict]]) -> list[ToolResult]:
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:  # pure functions
        results = list(pool.map(lambda c: TOOLS[c[0]](**c[1]), calls))
    for result in results:  # recorded in a fixed order
        session.record.add_tool_result(result, origin="mandatory")
    session.metrics.mandatory_calls += len(results)
    return results


def resume(session: AgentSession, reply: str | None) -> AgentSession:
    """Continue a run paused by ask_user. A missing or empty reply ends it as CAUTION."""
    if session.status != "needs_user_input" or session.pending is None:
        raise ValueError("this run is not waiting for the user")
    pending = session.pending
    session.pending = None
    session.status = "running"
    if not reply or not reply.strip():
        session.record.append("user_reply", {"field": pending.field, "answered": False})
        _force(session, "the user did not answer the question")
        return session
    reply = reply.strip()
    output = {"answer": reply}
    if pending.field == "consumer_number":
        biller_id = _verified_biller(session)
        biller = service.get_biller(biller_id) if biller_id else None
        if biller is not None:
            output["format_matches_biller"] = biller.valid_consumer(reply.upper())
    shown = mask_id(reply) if pending.field in ("consumer_number", "payment_destination") else reply
    session.record.append("user_reply", {"field": pending.field, "answered": True, "reply": shown})
    outputs = [
        *session.pending_outputs,
        ToolOutput(call_id=pending.call_id, output=json.dumps(output, ensure_ascii=False)),
    ]
    session.pending_outputs = []
    session.conversation.append(ToolOutputs(outputs=outputs))
    _run(session)
    return session


# --- the loop ---


def _run(session: AgentSession) -> None:
    t0 = time.perf_counter()
    try:
        while session.status == "running":
            if session.metrics.model_turns >= session.config.max_model_turns:
                _force(session, "too many model turns")
                break
            try:
                turn = session.client.step(
                    system=AGENT_SYSTEM,
                    conversation=session.conversation,
                    tools=TOOL_SPECS,
                    model=session.config.model,
                    effort=session.config.effort,
                    max_output_tokens=session.config.max_output_tokens,
                )
            except LLMError as e:
                _force(session, f"model unavailable: {e}")
                break
            session.metrics.model_turns += 1
            _add_usage(session, turn.usage)
            session.conversation.append(AssistantTurn(turn=turn))
            session.record.append(
                "note",
                {
                    "event": "agent_turn",
                    "turn": session.metrics.model_turns,
                    "tool_calls": [c.name for c in turn.tool_calls],
                    "latency_ms": round(turn.latency_ms),
                },
            )
            if not turn.tool_calls:
                if session.nudged:
                    _force(session, "the agent stopped without submitting a verdict")
                    break
                session.nudged = True
                session.conversation.append(
                    UserText(
                        text="Call submit_verdict now, citing evidence_id values from the tool results."
                    )
                )
                continue
            outputs = _handle_calls(session, turn.tool_calls)
            if session.status == "running":
                session.conversation.append(ToolOutputs(outputs=outputs))
            elif session.status == "needs_user_input":
                session.pending_outputs = outputs
    finally:
        session.metrics.latency_ms += (time.perf_counter() - t0) * 1000


def _handle_calls(session: AgentSession, calls: list[ToolCall]) -> list[ToolOutput]:
    outputs: dict[str, str] = {}
    verification = [c for c in calls if c.name in TOOLS]
    submits = [c for c in calls if c.name == control_tools.SUBMIT_VERDICT]
    asks = [c for c in calls if c.name == control_tools.ASK_USER]
    known = set(TOOLS) | {control_tools.SUBMIT_VERDICT, control_tools.ASK_USER}

    for c in calls:  # allowlist: anything else is refused and fed back
        if c.name not in known:
            session.metrics.tool_calls += 1
            _refuse(
                session,
                Refusal(rule="unknown_tool", message=f"There is no tool named {c.name!r}."),
                counts=False,
            )
            outputs[c.call_id] = json.dumps(
                {"error": f"unknown tool {c.name!r}; available: {sorted(known)}"}
            )

    budget = session.config.max_tool_calls - session.metrics.tool_calls
    if len(verification) > budget:
        _force(session, f"more than {session.config.max_tool_calls} tool calls")
        return []
    session.metrics.tool_calls += len(verification)
    with ThreadPoolExecutor(max_workers=max(len(verification), 1)) as pool:  # pure functions
        results = list(pool.map(_run_tool, verification))
    for c, result in zip(verification, results, strict=True):  # recorded in the requested order
        session.record.add_tool_result(result)
        outputs[c.call_id] = _tool_output(result)

    for i, c in enumerate(submits):
        if i > 0:
            outputs[c.call_id] = json.dumps(
                {"accepted": False, "message": "Only one submit_verdict per turn."}
            )
            continue
        outputs[c.call_id] = _submit(session, c)
        if session.status != "running":
            return []

    for i, c in enumerate(asks):
        if i > 0 or session.asks >= session.config.max_asks:
            _refuse(
                session,
                Refusal(rule="ask_limit", message="Only one question per run."),
                counts=False,
            )
            outputs[c.call_id] = json.dumps(
                {"error": "Only one question per run; continue without it."}
            )
            continue
        try:
            args = AskUserArgs.model_validate_json(c.arguments)
        except ValidationError as e:
            outputs[c.call_id] = json.dumps(
                {"error": f"invalid ask_user arguments: {e.error_count()} error(s)"}
            )
            continue
        session.asks += 1
        session.pending = PendingQuestion(
            call_id=c.call_id, field=args.field, question=args.question
        )
        session.record.append("ask_user", {"field": args.field, "question": args.question})
        session.status = "needs_user_input"

    return [
        ToolOutput(call_id=c.call_id, output=outputs[c.call_id])
        for c in calls
        if c.call_id in outputs
    ]


def _run_tool(call: ToolCall) -> ToolResult:
    tool = TOOLS[call.name]
    try:
        args = json.loads(call.arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except ValueError:
        return ToolResult(
            tool=call.name,
            call_id=make_id("call", call.name, call.arguments),
            args={},
            ok=False,
            error="arguments are not valid JSON",
        )
    return tool(**args)


def _tool_output(result: ToolResult) -> str:
    return json.dumps(
        {
            "ok": result.ok,
            "error": result.error,
            "evidence": [
                {"evidence_id": e.evidence_id, "code": e.code.value, "summary": e.summary}
                for e in result.evidence
            ],
            "data": result.data,
        },
        ensure_ascii=False,
        default=str,
    )


def _submit(session: AgentSession, call: ToolCall) -> str:
    try:
        args = SubmitVerdictArgs.model_validate_json(call.arguments)
    except ValidationError as e:
        refusal = Refusal(
            rule="invalid_arguments",
            message=f"submit_verdict arguments are invalid: {e.error_count()} error(s).",
        )
        return _refused_submit(session, refusal)
    ctx = CheckContext(
        args=args,
        record=session.record,
        destinations=session.destinations,
        low_confidence=session.input.low_confidence_fields(),
    )
    refusal = run_deterministic(ctx)
    if refusal is None:  # the judge runs only after every deterministic check passed
        refusal, judge_resp, feedback = claims_check(ctx, session.judge, session.config.judge_model)
        session.metrics.judge_calls += 1
        if judge_resp is not None:
            _add_usage(session, judge_resp.usage)
        session.record.append(
            "judge",
            {"verdict": args.verdict.value, "accepted": refusal is None, "reasons": feedback},
        )
    if refusal is not None:
        return _refused_submit(session, refusal)
    final = FinalVerdict(
        verdict=args.verdict, reasons=args.reasons, facts=args.facts, floor=ctx.floor()
    )
    _finish(session, final)
    return json.dumps({"accepted": True})


def _refused_submit(session: AgentSession, refusal: Refusal) -> str:
    session.submits += 1
    _refuse(session, refusal, counts=True)
    left = session.config.max_submits - session.submits
    if left <= 0:
        _force(
            session, f"verdict refused {session.config.max_submits} times (last: {refusal.rule})"
        )
    return json.dumps(
        {"accepted": False, "rule": refusal.rule, "message": refusal.message, "attempts_left": left}
    )


def _refuse(session: AgentSession, refusal: Refusal, *, counts: bool) -> None:
    session.metrics.refusals += 1
    session.record.append("refusal", {**refusal.model_dump(), "counts_toward_limit": counts})


def _force(session: AgentSession, why: str) -> None:
    """End the run as CAUTION, or the evidence floor if that is stricter. Never SAFE."""
    results = session.record.tool_results
    floor = floor_verdict(
        [e for r in results for e in r.evidence], tool_failures=sum(not r.ok for r in results)
    )
    verdict = stricter(Verdict.CAUTION, floor.verdict)
    reasons = [
        Reason(text="Could not verify this payment request. Do not pay yet.", evidence_ids=[])
    ]
    if floor.evidence_ids:
        reasons.insert(
            0,
            Reason(
                text=f"Risk found by the checks ({floor.rule}).", evidence_ids=floor.evidence_ids
            ),
        )
    _finish(
        session,
        FinalVerdict(verdict=verdict, reasons=reasons, forced=True, forced_reason=why, floor=floor),
    )


def _finish(session: AgentSession, final: FinalVerdict) -> None:
    session.final = final
    session.status = "done"
    refusals = [e.payload for e in session.record.entries if e.kind == "refusal"]
    session.record.append(
        "verdict",
        {
            **final.model_dump(mode="json"),
            "refusals": refusals,
            "metrics": session.metrics.model_dump(),
        },
    )


def _add_usage(session: AgentSession, usage: Usage) -> None:
    m = session.metrics
    m.input_tokens += usage.input_tokens
    m.output_tokens += usage.output_tokens
    m.cost_usd += usage.cost_usd


def _verified_biller(session: AgentSession) -> str | None:
    for r in session.record.tool_results:
        if EvidenceCode.BILLER_VERIFIED in r.codes:
            return r.data.get("biller_id")
    return None
