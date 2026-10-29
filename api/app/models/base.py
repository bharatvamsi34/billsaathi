"""One interface for every model provider (Meta Model API now, Baseten for Privacy Mode later)."""

from typing import Literal, Protocol

from pydantic import BaseModel, Field

Effort = Literal["low", "medium", "high"]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    image_data_url: str | None = None  # images go inline, so nothing is stored on the provider


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0


class LLMResponse(BaseModel):
    text: str
    model: str
    provider: str
    latency_ms: float
    usage: Usage = Field(default_factory=Usage)
    transport_attempts: int = 1  # >1 when a timeout / 429 / 5xx was retried


class LLMError(Exception):
    """The model could not be reached or did not finish (after retries)."""


# --- tool-calling conversations (agent loop) ---


class ToolCall(BaseModel):
    call_id: str
    name: str
    arguments: str  # raw JSON text as the model produced it; parsed and validated by the loop


class ModelTurn(BaseModel):
    """One model step: optional text plus zero or more tool calls (possibly several at once)."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # Opaque provider output (e.g. reasoning and function_call items), replayed to the same provider.
    provider_items: list[dict] = Field(default_factory=list)
    latency_ms: float = 0.0
    usage: Usage = Field(default_factory=Usage)


class UserText(BaseModel):
    kind: Literal["user"] = "user"
    text: str


class AssistantTurn(BaseModel):
    kind: Literal["assistant"] = "assistant"
    turn: ModelTurn


class ToolOutput(BaseModel):
    call_id: str
    output: str  # JSON text sent back to the model


class ToolOutputs(BaseModel):
    kind: Literal["tool_outputs"] = "tool_outputs"
    outputs: list[ToolOutput]


ConvItem = UserText | AssistantTurn | ToolOutputs


class LLMClient(Protocol):
    provider: str

    def respond(
        self,
        *,
        system: str,
        messages: list[Message],
        model: str,
        effort: Effort = "low",
        max_output_tokens: int = 4096,
    ) -> LLMResponse: ...

    def step(
        self,
        *,
        system: str,
        conversation: list[ConvItem],
        tools: list[dict],
        model: str,
        effort: Effort = "low",
        max_output_tokens: int = 4096,
    ) -> ModelTurn: ...
