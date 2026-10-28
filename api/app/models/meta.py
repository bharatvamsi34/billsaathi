"""Meta Model API client (OpenAI Responses format, official openai SDK, non-streaming).

Timeouts, retries with exponential backoff on timeouts / connection errors / 429 / 5xx,
and one log line per request with model, latency, tokens and estimated cost. Prompts and
outputs are never logged.
"""

import logging
import time

import openai
from openai import OpenAI

from app.config import Settings
from app.models.base import Effort, LLMError, LLMResponse, Message, Usage
from app.models.pricing import cost_usd

log = logging.getLogger("billsaathi.llm")

_RETRYABLE = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class MetaClient:
    provider = "meta"

    def __init__(
        self,
        settings: Settings,
        *,
        timeout_s: float = 60.0,
        max_attempts: int = 3,
        backoff_s: float = 1.0,
        http_client=None,  # tests inject an httpx.Client with a mock transport
    ):
        if settings.meta_api_key is None or not settings.meta_api_base_url:
            raise LLMError("META_API_KEY and META_API_BASE_URL must be set")
        self._client = OpenAI(
            api_key=settings.meta_api_key.get_secret_value(),
            base_url=settings.meta_api_base_url,
            timeout=timeout_s,
            max_retries=0,  # retries are ours, so every attempt is counted and logged
            http_client=http_client,
        )
        self.max_attempts = max_attempts
        self.backoff_s = backoff_s

    @staticmethod
    def _input(system: str, messages: list[Message]) -> list[dict]:
        items: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "assistant":
                items.append({"role": "assistant", "content": m.text})
                continue
            content: list[dict] = [{"type": "input_text", "text": m.text}]
            if m.image_data_url:
                content.append({"type": "input_image", "image_url": m.image_data_url})
            items.append({"role": "user", "content": content})
        return items

    def respond(
        self,
        *,
        system: str,
        messages: list[Message],
        model: str,
        effort: Effort = "low",
        max_output_tokens: int = 4096,
    ) -> LLMResponse:
        if "contributor" in model.lower():
            raise LLMError(f"refusing {model!r}: Contributor models train on inputs")
        kwargs = {
            "model": model,
            "input": self._input(system, messages),
            "reasoning": {"effort": effort},
            "max_output_tokens": max_output_tokens,
        }
        t0 = time.perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = self._client.responses.create(**kwargs)
                break
            except _RETRYABLE as e:
                log.warning(
                    "llm retry model=%s attempt=%d error=%s", model, attempt, type(e).__name__
                )
                if attempt == self.max_attempts:
                    raise LLMError(f"{type(e).__name__} after {attempt} attempts") from e
                time.sleep(self.backoff_s * 2 ** (attempt - 1))
            except openai.APIStatusError as e:  # 4xx other than 429: retrying will not help
                raise LLMError(f"HTTP {e.status_code} from model API") from e
        latency_ms = (time.perf_counter() - t0) * 1000
        if resp.status != "completed":
            reason = getattr(resp.incomplete_details, "reason", None) or resp.status
            raise LLMError(f"model did not finish: {reason}")
        u = resp.usage
        usage = Usage(
            input_tokens=u.input_tokens if u else 0,
            output_tokens=u.output_tokens if u else 0,
            reasoning_tokens=(
                u.output_tokens_details.reasoning_tokens if u and u.output_tokens_details else 0
            ),
        )
        usage.cost_usd = cost_usd(model, usage.input_tokens, usage.output_tokens)
        log.info(
            "llm ok provider=meta model=%s latency_ms=%.0f in=%d out=%d reasoning=%d cost_usd=%.5f attempts=%d",
            model, latency_ms, usage.input_tokens, usage.output_tokens, usage.reasoning_tokens,
            usage.cost_usd, attempt,
        )  # fmt: skip
        return LLMResponse(
            text=resp.output_text,
            model=model,
            provider=self.provider,
            latency_ms=latency_ms,
            usage=usage,
            transport_attempts=attempt,
        )
