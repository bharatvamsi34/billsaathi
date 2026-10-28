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
