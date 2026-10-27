"""Model transports for the spike.

- Meta Model API, OpenAI Responses format: raw httpx (SSE) and the official openai SDK.
- Baseten (OpenAI-compatible chat completions) for Muse Spark Open.

Request headers are never logged; every stored error string goes through redact().
"""

import base64
import json
import mimetypes
import re
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from app.config import Settings


@dataclass
class Prompt:
    system: str
    user: str
    image: Path | None = None
    image_file_id: str | None = None  # Meta /v1/files id; used instead of a data URL when set
    audio: Path | None = None  # WAV; chat-completions input_audio (Baseten)


@dataclass
class CallResult:
    provider: str
    transport: str
    model: str
    ok: bool = False
    text: str = ""
    reasoning: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    output_items: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    ttft_ms: float | None = None
    total_ms: float = 0.0
    http_status: int | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)  # raw stream shape (SAM)


def redact(text: str | None, settings: Settings) -> str | None:
    if not text:
        return text
    for secret in (settings.meta_api_key, settings.baseten_api_key):
        if secret is not None and secret.get_secret_value():
            text = text.replace(secret.get_secret_value(), "***")
    return text


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


# --- parsing helpers (unit-tested offline) ---


def iter_sse(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield JSON payloads from server-sent-event lines ("data: ..." blocks)."""
    buf: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r\n")
        if line.startswith("data:"):
            buf.append(line[5:].lstrip())
        elif line == "" and buf:
            payload = "\n".join(buf)
            buf = []
            if payload == "[DONE]":
                return
            yield json.loads(payload)
    if buf and (payload := "\n".join(buf)) != "[DONE]":
        yield json.loads(payload)


def extract_json(text: str) -> Any:
    """Parse the first JSON object/array in model text (tolerates fences and prose)."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch in "{[":
            try:
                return decoder.raw_decode(cleaned[i:])[0]
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON object found in model output")


def split_reasoning(text: str) -> tuple[str, str]:
    """Split "<think>...</think>answer" into (reasoning, answer)."""
    if "</think>" not in text:
        return "", text.strip()
    head, _, answer = text.partition("</think>")
    return head.replace("<think>", "").strip(), answer.strip()


def apply_completed_response(resp: dict[str, Any], result: CallResult) -> None:
    """Fill text, tool calls, reasoning summary and usage from a Responses API object."""
    result.output_items = resp.get("output") or []
    texts: list[str] = []
    reasoning: list[str] = []
    result.tool_calls = []
    for item in result.output_items:
        kind = item.get("type")
        if kind == "message":
            texts += [
                p.get("text", "")
                for p in item.get("content") or []
                if p.get("type") == "output_text"
            ]
        elif kind == "function_call":
            result.tool_calls.append(
                {
                    "call_id": item.get("call_id"),
                    "name": item.get("name"),
                    "arguments": item.get("arguments"),
                }
            )
        elif kind == "reasoning":
            reasoning += [s.get("text", "") for s in item.get("summary") or []]
    if texts:
        result.text = "".join(texts)
    if reasoning and not result.reasoning:
        result.reasoning = "\n".join(reasoning)
    usage = resp.get("usage") or {}
    result.input_tokens = usage.get("input_tokens")
    result.output_tokens = usage.get("output_tokens")
    result.reasoning_tokens = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")


def consume_events(events: Iterable[dict[str, Any]], result: CallResult, t0: float) -> None:
    """Apply a stream of Responses API events (same shape from httpx and the SDK)."""
    text: list[str] = []
    reasoning: list[str] = []
    for ev in events:
        kind = ev.get("type", "")
        if kind == "response.output_text.delta":
            if result.ttft_ms is None:
                result.ttft_ms = (time.perf_counter() - t0) * 1000
            text.append(ev.get("delta", ""))
        elif kind.startswith("response.reasoning") and kind.endswith(".delta"):
            reasoning.append(ev.get("delta", ""))
        elif kind == "response.completed":
            apply_completed_response(ev.get("response") or {}, result)
            result.ok = True
        elif kind in ("response.failed", "response.incomplete", "error"):
            resp = ev.get("response") or {}
            if kind != "error":
                apply_completed_response(resp, result)
            detail = resp.get("error") or resp.get("incomplete_details") or ev
            result.error = f"{kind}: {json.dumps(detail)[:500]}"
    if not result.text:
        result.text = "".join(text)
    if not result.reasoning:
        result.reasoning = "".join(reasoning)


# --- Meta Model API (Responses format) ---


def responses_input(prompt: Prompt) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt.user}]
    if prompt.image_file_id is not None:
        content.append({"type": "input_image", "file_id": prompt.image_file_id})
    elif prompt.image is not None:
        content.append({"type": "input_image", "image_url": data_url(prompt.image)})
    return [{"role": "system", "content": prompt.system}, {"role": "user", "content": content}]


def _meta_creds(settings: Settings) -> tuple[str, str]:
    if settings.meta_api_key is None or not settings.meta_api_base_url:
        raise RuntimeError("META_API_KEY and META_API_BASE_URL must be set in api/.env")
    return settings.meta_api_key.get_secret_value(), settings.meta_api_base_url.rstrip("/")


def upload_file(settings: Settings, path: Path, timeout: float = 60.0) -> str:
    """Upload a (synthetic) file to Meta /v1/files and return its id."""
    key, base = _meta_creds(settings)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    r = httpx.post(
        f"{base}/files",
        headers={"Authorization": f"Bearer {key}"},
        data={"purpose": "user_data"},
        files={"file": (path.name, path.read_bytes(), mime)},
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(
            redact(f"upload {path.name}: HTTP {r.status_code}: {r.text[:300]}", settings)
        )
    return r.json()["id"]


def delete_file(settings: Settings, file_id: str, timeout: float = 30.0) -> tuple[int, str]:
    """DELETE /v1/files/{id}; returns (status, short body) so callers can tell 404/405 apart."""
    key, base = _meta_creds(settings)
    r = httpx.delete(
        f"{base}/files/{file_id}", headers={"Authorization": f"Bearer {key}"}, timeout=timeout
    )
    return r.status_code, redact(r.text[:200], settings) or ""


def shape(obj: Any, max_str: int = 120) -> Any:
    """Copy of a JSON value with long strings and lists shortened, to record an unknown format."""
    if isinstance(obj, dict):
        return {k: shape(v, max_str) for k, v in obj.items()}
    if isinstance(obj, list):
        head = [shape(v, max_str) for v in obj[:5]]
        return head + ([f"<{len(obj) - 5} more items>"] if len(obj) > 5 else [])
    if isinstance(obj, str) and len(obj) > max_str:
        return f"<str len={len(obj)}: {obj[:60]}...>"
    return obj


def meta_sam(
    settings: Settings, model: str, file_id: str, concept: str, timeout: float = 120.0
) -> CallResult:
    """SAM 3.1 concept segmentation, request shaped exactly like the dev.meta.ai snippet."""
    result = CallResult("meta", "httpx-stream", model)
    key, base = _meta_creds(settings)
    body = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": concept},
                    {"type": "input_image", "file_id": file_id},
                ],
            }
        ],
        "stream": True,
        "metadata": {"mask_encoding": "lossless"},
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    t0 = time.perf_counter()
    try:
        with httpx.stream(
            "POST", f"{base}/responses", headers=headers, json=body, timeout=timeout
        ) as r:
            result.http_status = r.status_code
            if r.status_code >= 400:
                r.read()
                result.error = f"HTTP {r.status_code}: {r.text[:500]}"
            else:
                for ev in iter_sse(r.iter_lines()):
                    if result.ttft_ms is None:
                        result.ttft_ms = (time.perf_counter() - t0) * 1000
                    result.events.append(ev)
                    if ev.get("type") == "response.completed":
                        apply_completed_response(ev.get("response") or {}, result)
                result.ok = result.error is None and bool(result.events)
    except (httpx.HTTPError, ValueError) as e:
        result.error = f"{type(e).__name__}: {e}"
    result.total_ms = (time.perf_counter() - t0) * 1000
    result.error = redact(result.error, settings)
    return result


def _responses_kwargs(model, input_items, tools, max_output_tokens, effort) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": effort},
    }
    if tools:
        kwargs["tools"] = tools
    return kwargs


def meta_httpx(
    settings: Settings,
    model: str,
    input_items: list[dict[str, Any]],
    *,
    stream: bool = True,
    tools: list[dict[str, Any]] | None = None,
    max_output_tokens: int = 2048,
    effort: str = "medium",
    timeout: float = 120.0,
) -> CallResult:
    result = CallResult("meta", "httpx-stream" if stream else "httpx", model)
    key, base = _meta_creds(settings)
    body = _responses_kwargs(model, input_items, tools, max_output_tokens, effort) | {
        "stream": stream
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
    }
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            if stream:
                with client.stream("POST", f"{base}/responses", headers=headers, json=body) as r:
                    result.http_status = r.status_code
                    if r.status_code >= 400:
                        r.read()
                        result.error = f"HTTP {r.status_code}: {r.text[:500]}"
                    else:
                        consume_events(iter_sse(r.iter_lines()), result, t0)
            else:
                r = client.post(f"{base}/responses", headers=headers, json=body)
                result.http_status = r.status_code
                if r.status_code >= 400:
                    result.error = f"HTTP {r.status_code}: {r.text[:500]}"
                else:
                    apply_completed_response(r.json(), result)
                    result.ok = True
    except (httpx.HTTPError, ValueError) as e:
        result.error = f"{type(e).__name__}: {e}"
    result.total_ms = (time.perf_counter() - t0) * 1000
    result.error = redact(result.error, settings)
    return result


def meta_sdk(
    settings: Settings,
    model: str,
    input_items: list[dict[str, Any]],
    *,
    stream: bool = True,
    tools: list[dict[str, Any]] | None = None,
    max_output_tokens: int = 2048,
    effort: str = "medium",
    timeout: float = 120.0,
) -> CallResult:
    result = CallResult("meta", "sdk-stream" if stream else "sdk", model)
    key, base = _meta_creds(settings)
    client = OpenAI(api_key=key, base_url=base, timeout=timeout, max_retries=0)
    kwargs = _responses_kwargs(model, input_items, tools, max_output_tokens, effort)
    t0 = time.perf_counter()
    try:
        if stream:
            with client.responses.create(**kwargs, stream=True) as events:
                consume_events((ev.model_dump() for ev in events), result, t0)
        else:
            apply_completed_response(client.responses.create(**kwargs).model_dump(), result)
            result.ok = True
        result.http_status = 200
    except Exception as e:  # spike: any SDK failure is a finding, not a crash
        result.http_status = getattr(e, "status_code", None)
        result.error = f"{type(e).__name__}: {e}"[:600]
    result.total_ms = (time.perf_counter() - t0) * 1000
    result.error = redact(result.error, settings)
    return result


# --- Baseten (OpenAI-compatible chat completions) ---


def chat_messages(prompt: Prompt) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt.user}]
    if prompt.image is not None:
        content.append({"type": "image_url", "image_url": {"url": data_url(prompt.image)}})
    if prompt.audio is not None:
        audio_b64 = base64.b64encode(prompt.audio.read_bytes()).decode("ascii")
        content.append({"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}})
    return [{"role": "system", "content": prompt.system}, {"role": "user", "content": content}]


def meta_transcribe(
    settings: Settings,
    model: str,
    wav: Path,
    *,
    language_bias: list[str] | None = None,
    keywords: list[str] | None = None,
    timeout: float = 60.0,
) -> tuple[CallResult, int | None]:
    """Muse Voice Transcribe: multipart `request` JSON + `audio` WAV. Returns (result, duration ms)."""
    result = CallResult("meta", "asr-multipart", model)
    key, base = _meta_creds(settings)
    request: dict[str, Any] = {"mode": "PUSH_TO_TALK", "model": model, "audioEncoding": "WAV"}
    if language_bias:
        request["languageBias"] = language_bias
    if keywords:
        request["keywords"] = keywords
    duration_ms = None
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            f"{base}/asr/transcribe",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            files={
                "request": (None, json.dumps(request), "application/json"),
                "audio": (wav.name, wav.read_bytes(), "audio/wav"),
            },
            timeout=timeout,
        )
        result.http_status = r.status_code
        if r.status_code >= 400:
            result.error = f"HTTP {r.status_code}: {r.text[:500]}"
        else:
            body = r.json()
            result.text = body.get("transcript") or ""
            duration_ms = body.get("audioDurationMs")
            result.events = [shape(body)]
            result.ok = True
    except (httpx.HTTPError, ValueError) as e:
        result.error = f"{type(e).__name__}: {e}"
    result.total_ms = (time.perf_counter() - t0) * 1000
    result.error = redact(result.error, settings)
    return result, duration_ms


def baseten_chat(
    settings: Settings,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 2048,
    timeout: float = 180.0,
) -> CallResult:
    result = CallResult("baseten", "chat-stream", settings.baseten_model)
    if settings.baseten_api_key is None:
        raise RuntimeError("BASETEN_API_KEY must be set in api/.env")
    client = OpenAI(
        api_key=settings.baseten_api_key.get_secret_value(),
        base_url=settings.baseten_base_url,
        timeout=timeout,
        max_retries=0,
    )
    kwargs: dict[str, Any] = {
        "model": settings.baseten_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if tools:
        kwargs["tools"] = tools
    text: list[str] = []
    reasoning: list[str] = []
    calls: dict[int, dict[str, Any]] = {}
    t0 = time.perf_counter()
    try:
        for chunk in client.chat.completions.create(**kwargs):
            if chunk.usage:
                result.input_tokens = chunk.usage.prompt_tokens
                result.output_tokens = chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.model_dump()
            if delta.get("content"):
                if result.ttft_ms is None:
                    result.ttft_ms = (time.perf_counter() - t0) * 1000
                text.append(delta["content"])
            if r := delta.get("reasoning_content") or delta.get("reasoning"):
                reasoning.append(r)
            for tc in delta.get("tool_calls") or []:
                slot = calls.setdefault(tc["index"], {"call_id": None, "name": "", "arguments": ""})
                slot["call_id"] = tc.get("id") or slot["call_id"]
                fn = tc.get("function") or {}
                slot["name"] += fn.get("name") or ""
                slot["arguments"] += fn.get("arguments") or ""
        result.http_status = 200
        result.ok = True
    except Exception as e:  # spike: any SDK failure is a finding, not a crash
        result.http_status = getattr(e, "status_code", None)
        result.error = f"{type(e).__name__}: {e}"[:600]
    inline_reasoning, answer = split_reasoning("".join(text))
    result.text = answer
    result.reasoning = "".join(reasoning) or inline_reasoning
    result.tool_calls = [calls[i] for i in sorted(calls)]
    result.output_items = [
        {
            "role": "assistant",
            "content": answer or None,
            "tool_calls": [
                {
                    "id": c["call_id"],
                    "type": "function",
                    "function": {"name": c["name"], "arguments": c["arguments"]},
                }
                for c in result.tool_calls
            ]
            or None,
        }
    ]
    result.total_ms = (time.perf_counter() - t0) * 1000
    result.error = redact(result.error, settings)
    return result
