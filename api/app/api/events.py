"""Public, masked events for the live step-by-step stream.

Built from EvidenceRecord entries (and a few pipeline steps). Nothing here may carry a raw
image, the whole message text, or a full consumer or phone number. A short matched scam phrase
may appear, masked, because the screen quotes it.
"""

from typing import Any

from app.agent.evidence import RecordEntry
from app.facts import verified_fact
from app.pii import mask_args as _args
from app.pii import mask_destination as _destination
from app.pii import mask_id, scrub
from app.schemas import ExtractionOutput


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


# Evidence values safe to show, so the screen can quote real values instead of restating a badge.
# An allowlist: a new detail key stays private until it is added here. Display only: nothing
# here feeds the risk engine, the agent or the judge.
_DETAIL_KEYS = (
    "biller_amount",
    "claimed_amount",
    "usual_amount",
    "current_amount",
    "ratio",
    "host",
    "vpa",
    "lookalike_of",
    "phone_masked",
    "query",
)


def _public_detail(detail: dict[str, Any], secrets: list[str]) -> dict[str, Any]:
    out = {k: detail[k] for k in _DETAIL_KEYS if k in detail}
    if isinstance(out.get("query"), str):
        out["query"] = scrub(out["query"], secrets)
    if "matches" in detail:  # the scam wording that matched: a short phrase, never the message
        out["phrases"] = [scrub(m["match"], secrets) for m in detail["matches"]]
    return out


def _biller_record(tool: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """What the (mock) biller's record says, for the comparison on the screen. Synthetic data."""
    if tool == "lookup_biller" and data.get("matched"):
        return {
            "name": data["official_name"],
            "domains": data.get("official_domains", []),
            "vpas": data.get("official_vpas", []),
            "phones": data.get("official_phones", []),
        }
    if tool == "fetch_bill" and data.get("found"):
        return {"amount": data["biller_amount"], "due_date": data.get("due_date")}
    return None


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
            "record": _biller_record(p["tool"], p.get("data") or {}),
            "evidence": [
                {
                    "evidence_id": e["evidence_id"],
                    "code": e["code"],
                    "summary": scrub(e["summary"], secrets),
                    "detail": _public_detail(e.get("detail") or {}, secrets),
                }
                for e in p.get("evidence", [])
            ],
        }
    if kind == "note" and p.get("event") == "run_started":
        return {"type": "verification_started", "destinations": p.get("destinations", 0)}
    if kind == "note" and p.get("event") == "mandatory_done":
        return {"type": "early", "signal": "scam_signals" if p["scam_signals"] else "checking"}
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
                    "evidence_ids": r.get("evidence_ids", []),
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
        "floor": (p.get("floor") or {}).get("verdict"),  # what the code enforced, for the trace
        "user_confirmation_required": True,  # nothing is ever paid without the user's sign-off
    }
