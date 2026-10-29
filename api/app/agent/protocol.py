"""Types for one agent run (see docs/AGENT_DESIGN.md)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.risk.policy import Floor
from app.schemas import BillFields, ExtractionOutput, Scored, Verdict

LOW_CONFIDENCE = 0.8


class AgentInput(BaseModel):
    extraction: ExtractionOutput
    raw_text: str | None = None  # text the user sent (SMS / WhatsApp paste)
    # Transcription of an image: used only by code (milestone check, scam wording), never shown
    # to the agent. text_unreadable means transcription failed, so links in the image could not
    # be cross-checked: recorded as a failed check (fail closed, no SAFE).
    visible_text: str | None = None
    text_unreadable: bool = False
    language: str = "en"  # user's language for questions and (later) explanations

    @property
    def text_for_checks(self) -> str | None:
        return self.raw_text or self.visible_text

    @classmethod
    def from_fields(cls, fields: BillFields, raw_text: str | None = None, language: str = "en"):
        """Ground-truth fields (tests, dataset runs) with confidence 1.0."""
        extraction = ExtractionOutput(
            **{
                name: Scored(value=getattr(fields, name), confidence=1.0)
                for name in BillFields.model_fields
            }
        )
        return cls(extraction=extraction, raw_text=raw_text, language=language)

    def low_confidence_fields(self) -> list[str]:
        """Fields whose low confidence blocks SAFE (never a reason FOR safe)."""
        e = self.extraction
        low = []
        if e.amount.confidence < LOW_CONFIDENCE:
            low.append("amount")
        if e.payment_destinations.confidence < LOW_CONFIDENCE:
            low.append("payment_destinations")
        return low


class Reason(BaseModel):
    text: str = Field(description="One short English sentence")
    evidence_ids: list[str] = Field(description="evidence_id values from this run's tool results")


class SubmitVerdictArgs(BaseModel):
    verdict: Verdict
    reasons: list[Reason] = Field(min_length=1)
    facts: list[str] = Field(
        default_factory=list,
        description="Keys of checked facts to show the user, e.g. cybercrime_helpline",
    )


AskField = Literal["consumer_number", "amount", "biller_name", "payment_destination"]


class AskUserArgs(BaseModel):
    field: AskField
    question: str = Field(description="One short question in the user's language")


class Refusal(BaseModel):
    rule: str
    message: str


class Metrics(BaseModel):
    model_turns: int = 0  # agent turns (judge calls counted separately)
    judge_calls: int = 0
    mandatory_calls: int = 0  # fixed-point checks run by code before the first turn
    tool_calls: int = 0  # extra calls requested by the agent (limit applies to these)
    refusals: int = 0
    latency_ms: float = 0.0  # model + tools + judge, excluding time paused for the user
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class FinalVerdict(BaseModel):
    verdict: Verdict
    reasons: list[Reason]
    facts: list[str] = Field(default_factory=list)
    forced: bool = False
    forced_reason: str | None = None
    floor: Floor


RunStatus = Literal["running", "needs_user_input", "done"]


class PendingQuestion(BaseModel):
    call_id: str
    field: AskField
    question: str
