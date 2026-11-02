"""Muse Spark Open (open weights) for Privacy Mode: Baseten, with Fireworks serverless as fallback.

Both speak OpenAI-compatible chat completions. The same LLMClient interface as the Meta client,
so tools, checks, refusals and the evidence record are unchanged. Reasoning comes back separately
and is never used. No Meta API call happens in this path.

Neither price is confirmed for this model, so the meter estimates at Spark 1.3 rates (it must
still count towards the daily cap); see app/models/pricing.py.
"""

import base64
import logging
import re
import time

import httpx
import openai
from openai import OpenAI

from app.config import Settings
from app.models.base import (
    AssistantTurn,
    ConvItem,
    Effort,
    LLMError,
    LLMResponse,
    Message,
    ModelTurn,
    ToolCall,
    ToolOutputs,
    Usage,
    UserText,
)
from app.models.pricing import cost_usd
from app.voice import Transcript

log = logging.getLogger("billsaathi.llm")

MODEL_LABEL = "muse-spark-open"
_RETRYABLE = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)
_THINK = re.compile(r"^\s*<think>.*?</think>", re.S)
_LANGUAGES = {"en": "English", "te": "Telugu", "hi": "Hindi"}


def _answer(text: str | None) -> str:
    """The final answer: some replies carry reasoning inline, before </think>."""
    return _THINK.sub("", text or "").strip()


class OpenWeightClient:
    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        *,
        timeout_s: float = 60.0,
        max_attempts: int = 3,
        backoff_s: float = 1.0,
        http_client: httpx.Client | None = None,
    ):
        if "contributor" in model.lower():
            raise LLMError(f"refusing {model!r}: Contributor models train on inputs")
        self.provider, self.model = provider, model
        self.max_attempts, self.backoff_s = max_attempts, backoff_s
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_s,
            max_retries=0,
            http_client=http_client,
        )

    def _create(self, kwargs: dict) -> tuple[object, Usage, float]:
        t0 = time.perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = self._client.chat.completions.create(model=self.model, **kwargs)
                break
            except _RETRYABLE as e:
                log.warning(
                    "llm retry provider=%s attempt=%d error=%s",
                    self.provider,
                    attempt,
                    type(e).__name__,
                )
                if attempt == self.max_attempts:
                    raise LLMError(f"{type(e).__name__} after {attempt} attempts") from e
                time.sleep(self.backoff_s * 2 ** (attempt - 1))
            except openai.APIStatusError as e:
                raise LLMError(f"HTTP {e.status_code} from {self.provider}") from e
        latency_ms = (time.perf_counter() - t0) * 1000
        if not resp.choices:
            raise LLMError(f"empty reply from {self.provider}")
        if resp.choices[0].finish_reason == "length":
            raise LLMError("model did not finish: length")
        u = resp.usage
        usage = Usage(
            input_tokens=u.prompt_tokens if u else 0,
            output_tokens=u.completion_tokens if u else 0,
        )
        usage.cost_usd = cost_usd(MODEL_LABEL, usage.input_tokens, usage.output_tokens)
        log.info(
            "llm ok provider=%s latency_ms=%.0f in=%d out=%d est_cost_usd=%.5f attempts=%d",
            self.provider, latency_ms, usage.input_tokens, usage.output_tokens, usage.cost_usd, attempt,
        )  # fmt: skip
        return resp, usage, latency_ms

    def respond(
        self,
        *,
        system: str,
        messages: list[Message],
        model: str = MODEL_LABEL,
        effort: Effort = "low",
        max_output_tokens: int = 4096,
    ) -> LLMResponse:
        items: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m.image_data_url:
                content = [
                    {"type": "text", "text": m.text},
                    {"type": "image_url", "image_url": {"url": m.image_data_url}},
                ]
                items.append({"role": m.role, "content": content})
            else:
                items.append({"role": m.role, "content": m.text})
        resp, usage, latency_ms = self._create({"messages": items, "max_tokens": max_output_tokens})
        return LLMResponse(
            text=_answer(resp.choices[0].message.content),
            model=self.model,
            provider=self.provider,
            latency_ms=latency_ms,
            usage=usage,
        )

    @staticmethod
    def _conversation(system: str, conversation: list[ConvItem]) -> list[dict]:
        items: list[dict] = [{"role": "system", "content": system}]
        for item in conversation:
            if isinstance(item, UserText):
                items.append({"role": "user", "content": item.text})
            elif isinstance(item, AssistantTurn):
                message: dict = {"role": "assistant", "content": item.turn.text or None}
                if item.turn.tool_calls:
                    message["tool_calls"] = [
                        {
                            "id": c.call_id,
                            "type": "function",
                            "function": {"name": c.name, "arguments": c.arguments},
                        }
                        for c in item.turn.tool_calls
                    ]
                items.append(message)
            elif isinstance(item, ToolOutputs):
                items.extend(
                    {"role": "tool", "tool_call_id": o.call_id, "content": o.output}
                    for o in item.outputs
                )
        return items

    def step(
        self,
        *,
        system: str,
        conversation: list[ConvItem],
        tools: list[dict],
        model: str = MODEL_LABEL,
        effort: Effort = "low",
        max_output_tokens: int = 4096,
    ) -> ModelTurn:
        specs = [
            {"type": "function", "function": {k: v for k, v in t.items() if k != "type"}}
            for t in tools
        ]
        resp, usage, latency_ms = self._create(
            {
                "messages": self._conversation(system, conversation),
                "tools": specs,
                "max_tokens": max_output_tokens,
            }
        )
        message = resp.choices[0].message
        calls = [
            ToolCall(call_id=c.id, name=c.function.name, arguments=c.function.arguments or "")
            for c in message.tool_calls or []
        ]
        return ModelTurn(
            text=_answer(message.content), tool_calls=calls, latency_ms=latency_ms, usage=usage
        )

    def transcribe_audio(self, wav: bytes, language: str | None) -> Transcript:
        """Speech to text on the open model itself (input_audio), for Privacy Mode."""
        said_in = _LANGUAGES.get(language or "", "English, Telugu or Hindi")
        content = [
            {
                "type": "text",
                "text": f"Transcribe this audio exactly, in its original script. The speaker uses "
                f"{said_in}. Reply with only the transcript.",
            },
            {
                "type": "input_audio",
                "input_audio": {"data": base64.b64encode(wav).decode("ascii"), "format": "wav"},
            },
        ]
        resp, usage, latency_ms = self._create(
            {"messages": [{"role": "user", "content": content}], "max_tokens": 2048}
        )
        return Transcript(
            text=_answer(resp.choices[0].message.content),
            latency_ms=latency_ms,
            cost_usd=usage.cost_usd,
        )


class FailoverClient:
    """Try the primary provider; if it cannot answer, try the fallback (same model, same weights)."""

    def __init__(self, primary: OpenWeightClient, fallback: OpenWeightClient | None):
        self.primary, self.fallback = primary, fallback
        self.provider = primary.provider

    def _call(self, name: str, *args, **kwargs):
        try:
            return getattr(self.primary, name)(*args, **kwargs)
        except LLMError as e:
            if self.fallback is None:
                raise
            log.warning("failover from %s: %s", self.primary.provider, e)
            return getattr(self.fallback, name)(*args, **kwargs)

    def respond(self, **kwargs) -> LLMResponse:
        return self._call("respond", **kwargs)

    def step(self, **kwargs) -> ModelTurn:
        return self._call("step", **kwargs)

    def transcribe_audio(self, wav: bytes, language: str | None) -> Transcript:
        return self._call("transcribe_audio", wav, language)


def privacy_client(settings: Settings) -> FailoverClient:
    """Baseten if configured, Fireworks as its fallback (or alone). Raises if neither is set."""
    timeout = max(settings.model_timeout_seconds, 60.0)
    clients = []
    if settings.baseten_api_key is not None:
        clients.append(
            OpenWeightClient(
                "baseten",
                settings.baseten_api_key.get_secret_value(),
                settings.baseten_base_url,
                settings.baseten_model,
                timeout_s=timeout,
            )
        )
    if settings.fireworks_api_key is not None:
        clients.append(
            OpenWeightClient(
                "fireworks",
                settings.fireworks_api_key.get_secret_value(),
                settings.fireworks_base_url,
                settings.fireworks_model,
                timeout_s=timeout,
            )
        )
    if not clients:
        raise LLMError("BASETEN_API_KEY or FIREWORKS_API_KEY must be set for Privacy Mode")
    return FailoverClient(clients[0], clients[1] if len(clients) > 1 else None)
