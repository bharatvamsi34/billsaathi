"""Public, masked events for the live step-by-step stream.

Built from EvidenceRecord entries (and a few pipeline steps). Nothing here may carry a raw
image, the raw message text, or a full consumer or phone number.
"""

import re
from typing import Any

from app.agent.evidence import RecordEntry
from app.facts import verified_fact
from app.pii import mask_id, mask_phone
from app.schemas import DestinationKind, ExtractionOutput

_LONG_DIGITS = re.compile(r"(?<!\d)(\+?\d[\d\s-]{6,}\d)(?!\d)")


def scrub(text: str | None, secrets: list[str] = ()) -> str | None:
    """Mask phone-like digit runs and any known consumer numbers inside free text."""
    if not text:
        return text
    for s in secrets:
        if s and len(s) >= 4:
            text = text.replace(s, mask_id(s))

    def mask(m: re.Match) -> str:  # 9+ digits: phones, consumer numbers; dates (8) stay readable
        run = m.group(1)
        return mask_phone(run) if sum(ch.isdigit() for ch in run) >= 9 else run

    return _LONG_DIGITS.sub(mask, text)


def _destination(kind: str, value: str) -> str:
    return mask_phone(value) if kind == DestinationKind.PHONE else value


def _args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    out = dict(args)
    if "consumer_number" in out:
        out["consumer_number"] = mask_id(out["consumer_number"])
    if "text" in out:  # the raw message never leaves the server
        out["text"] = f"<{len(out['text'] or '')} characters>"
    if tool == "check_payment_destination" and "value" in out:
        out["value"] = _destination(out.get("kind", ""), out["value"])
    return out


def resolve_facts(keys: list[str]) -> list[dict[str, str]]:
    facts = []
    for key in keys:
        fact = verified_fact(key)
        if fact is not None:
            facts.append(
                {"key": fact.key, "label": fact.label, "value": fact.value, "source": fact.source}
            )
    return facts


def extracted_event(output: ExtractionOutput, attempts: int, latency_ms: float) -> dict[str, Any]:
    def field(name: str, value: Any) -> dict[str, Any]:
        return {"value": value, "confidence": getattr(output, name).confidence}

    return {
        "type": "extracted",
        "attempts": attempts,
        "latency_ms": round(latency_ms),
        "fields": {
            "biller_name": field("biller_name", output.biller_name.value),
            "biller_category": field("biller_category", output.biller_category.value),
            "consumer_number": field("consumer_number", mask_id(output.consumer_number.value) if output.consumer_number.value else None),
            "amount": field("amount", output.amount.value),
            "due_date": field("due_date", str(output.due_date.value) if output.due_date.value else None),
            "bill_date": field("bill_date", str(output.bill_date.value) if output.bill_date.value else None),
            "payment_destinations": field(
                "payment_destinations",
                [{"kind": d.kind.value, "value": _destination(d.kind, d.value)} for d in output.payment_destinations.value],
            ),
            "languages": field("languages", output.languages.value),
            "urgency_language": field("urgency_language", output.urgency_language.value),
        },
    }  # fmt: skip


def public_event(entry: RecordEntry, secrets: list[str] = ()) -> dict[str, Any] | None:
    p, kind = entry.payload, entry.kind
    if kind == "tool_result":
        return {
            "type": "check",
            "origin": p.get("origin", "agent"),
            "tool": p["tool"],
            "ok": p["ok"],
            "error": scrub(p.get("error"), secrets),
            "args": _args(p["tool"], p.get("args", {})),
            "evidence": [
                {
                    "evidence_id": e["evidence_id"],
                    "code": e["code"],
                    "summary": scrub(e["summary"], secrets),
                }
                for e in p.get("evidence", [])
            ],
        }
    if kind == "note" and p.get("event") == "run_started":
        return {"type": "verification_started", "destinations": p.get("destinations", 0)}
    if kind == "note" and p.get("event") == "agent_turn":
        return {
            "type": "agent_turn",
            "turn": p["turn"],
            "tool_calls": p["tool_calls"],
            "latency_ms": p["latency_ms"],
        }
    if kind == "refusal":
        return {"type": "refusal", "rule": p["rule"], "message": scrub(p["message"], secrets)}
    if kind == "ask_user":
        return {"type": "question", "field": p["field"], "question": p["question"]}
    if kind == "user_reply":
        return {"type": "answer", "field": p["field"], "answered": p["answered"]}
    if kind == "judge":
        return {
            "type": "judge",
            "accepted": p["accepted"],
            "reasons": [
                {
                    "reason": scrub(r["reason"], secrets),
                    "supported": r["supported"],
                    "why": scrub(r["why"], secrets),
                }
                for r in p.get("reasons", [])
            ],
        }
    if kind == "verdict":
        return verdict_view(p, secrets)
    return None


def verdict_view(p: dict[str, Any], secrets: list[str] = ()) -> dict[str, Any]:
    return {
        "type": "verdict",
        "verdict": p["verdict"],
        "reasons": [
            {"text": scrub(r["text"], secrets), "evidence_ids": r["evidence_ids"]}
            for r in p["reasons"]
        ],
        "facts": resolve_facts(p.get("facts", [])),
        "forced": p.get("forced", False),
        "forced_reason": scrub(p.get("forced_reason"), secrets),
        "user_confirmation_required": True,  # nothing is ever paid without the user's sign-off
    }
