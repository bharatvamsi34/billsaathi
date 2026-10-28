"""Evidence types shared by tools, the agent loop and the audit log (see docs/AGENT_DESIGN.md).

Every tool call returns a ToolResult. Each finding inside it is a ToolEvidence with a
stable evidence_id, so a verdict can cite exactly which tool result supports each reason.
An EvidenceRecord is the append-only log of one agent run.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import EvidenceCode


def make_id(prefix: str, *parts: Any) -> str:
    """Deterministic short id: the same tool, arguments and code always give the same id."""
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:10]}"


class ToolEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    code: EvidenceCode
    source: str  # tool name, matches Evidence.source in labels
    summary: str  # one English line for the agent and the step-by-step UI
    detail: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str
    call_id: str
    args: dict[str, Any]
    ok: bool
    # Set when ok is False: the agent sees it; the risk engine treats it as "could not verify".
    error: str | None = None
    evidence: tuple[ToolEvidence, ...] = ()
    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def codes(self) -> set[EvidenceCode]:
        return {e.code for e in self.evidence}


EntryKind = Literal["tool_result", "refusal", "ask_user", "user_reply", "verdict", "note"]


class RecordEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    seq: int
    kind: EntryKind
    at: datetime
    payload: dict[str, Any]


class EvidenceRecord:
    """Append-only log of one run: every tool result, refusal, question and verdict.

    There is deliberately no way to edit or remove an entry. The same record later
    powers the live step-by-step UI and the audit log.
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._entries: list[RecordEntry] = []
        self._evidence: dict[str, ToolEvidence] = {}

    def append(self, kind: EntryKind, payload: dict[str, Any]) -> RecordEntry:
        entry = RecordEntry(
            seq=len(self._entries), kind=kind, at=datetime.now(UTC), payload=payload
        )
        self._entries.append(entry)
        return entry

    def add_tool_result(self, result: ToolResult) -> RecordEntry:
        for ev in result.evidence:
            self._evidence.setdefault(ev.evidence_id, ev)
        return self.append("tool_result", result.model_dump(mode="json"))

    @property
    def entries(self) -> tuple[RecordEntry, ...]:
        return tuple(self._entries)

    def evidence(self, evidence_id: str) -> ToolEvidence | None:
        """Evidence produced by a tool in THIS run, or None (e.g. an id the model invented)."""
        return self._evidence.get(evidence_id)

    @property
    def all_evidence(self) -> tuple[ToolEvidence, ...]:
        return tuple(self._evidence.values())
