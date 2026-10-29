"""Checks API: start a check, stream its steps (Server-Sent Events), read the result, answer
the agent's one question. The web app and the WhatsApp webhook both use this pipeline.
"""

import asyncio
import io
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
from pydantic import BaseModel, Field

from app import pipeline
from app.api.store import CheckState, CheckStore, RateLimiter, SpendMeter
from app.config import Settings, get_settings
from app.models.base import LLMError
from app.models.meta import MetaClient

router = APIRouter(prefix="/api/v1/checks", tags=["checks"])

MAX_IMAGE_BYTES = 8_000_000
MAX_TEXT_CHARS = 4000
STREAM_MAX_SECONDS = 600
KEEPALIVE_SECONDS = 15
Language = Literal["en", "te", "hi"]


def sniff_image(data: bytes) -> str | None:
    """Image type from the bytes themselves (never trust the file name), then a Pillow check."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        return None
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:  # truncated or corrupt image
        return None
    return mime


# --- shared state, created lazily so tests can replace pieces on app.state ---


def _settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def _state(request: Request, name: str, factory):
    value = getattr(request.app.state, name, None)
    if value is None:
        value = factory(_settings(request))
        setattr(request.app.state, name, value)
    return value


def _store(request: Request) -> CheckStore:
    return _state(request, "check_store", lambda s: CheckStore(s.check_ttl_seconds))


def _limiter(request: Request) -> RateLimiter:
    return _state(request, "rate_limiter", lambda s: RateLimiter(s.rate_limit_per_minute))


def _spend(request: Request) -> SpendMeter:
    return _state(request, "spend_meter", lambda s: SpendMeter(s.daily_spend_cap_usd))


def _executor(request: Request):
    return _state(request, "executor", lambda s: ThreadPoolExecutor(max_workers=8))


def _clients(request: Request) -> pipeline.Clients:
    def build(s: Settings) -> pipeline.Clients:
        try:
            meta = MetaClient(s, timeout_s=s.model_timeout_seconds)
        except LLMError as e:
            raise HTTPException(503, {"error": "not_configured", "message": str(e)}) from e
        return pipeline.Clients(extract=meta, agent=meta, judge=meta)

    return _state(request, "clients", build)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message})


# --- endpoints ---


@router.post("", status_code=202)
async def create_check(
    request: Request,
    language: Annotated[Language, Form()] = "en",
    text: Annotated[str | None, Form()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    audio: Annotated[
        UploadFile | None, File(description="Voice input placeholder (not yet)")
    ] = None,
):
    client_ip = request.client.host if request.client else "unknown"
    if not _limiter(request).allow(client_ip):
        return _error(
            429, "rate_limited", "Too many checks from this address. Try again in a minute."
        )
    if _spend(request).exceeded():
        return _error(503, "service_busy", "BillSaathi is busy right now. Please try again later.")
    if audio is not None:
        return _error(
            501, "audio_not_supported_yet", "Voice input is coming soon. Send text or an image."
        )
    if (image is None) == (not text or not text.strip()):
        return _error(400, "bad_input", "Send exactly one of: text, image.")

    check = pipeline.CheckInput(language=language)
    if image is not None:
        data = await image.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            return _error(413, "image_too_large", "Images must be 8 MB or smaller.")
        mime = sniff_image(data)
        if mime is None:
            return _error(415, "unsupported_image", "Send a PNG, JPEG or WebP image.")
        check.image, check.image_mime = data, mime
    else:
        if len(text) > MAX_TEXT_CHARS:
            return _error(
                413, "text_too_long", f"Text must be {MAX_TEXT_CHARS} characters or fewer."
            )
        check.text = text.strip()

    clients = _clients(request)
    state = CheckState(
        check_id=uuid.uuid4().hex, language=language, input_kind="image" if image else "text"
    )
    _store(request).add(state)
    _executor(request).submit(pipeline.run_check, state, check, clients, _spend(request))
    return {
        "check_id": state.check_id,
        "status": state.status,
        "events_url": f"/api/v1/checks/{state.check_id}/events",
        "result_url": f"/api/v1/checks/{state.check_id}",
    }


def _get(request: Request, check_id: str) -> CheckState:
    state = _store(request).get(check_id)
    if state is None:
        raise HTTPException(
            404, {"error": "not_found", "message": "No such check, or it has expired."}
        )
    return state


@router.get("/{check_id}")
def get_check(request: Request, check_id: str):
    state = _get(request, check_id)
    verdict = next((e for e in reversed(state.events) if e["type"] == "verdict"), None)
    question = next((e for e in reversed(state.events) if e["type"] == "question"), None)
    return {
        "check_id": state.check_id,
        "language": state.language,
        **pipeline.summary(state),
        "verdict": verdict,
        "question": question if state.status == "needs_user_input" else None,
        "events": len(state.events),
    }


@router.get("/{check_id}/events")
async def stream_events(request: Request, check_id: str, after: int = -1):
    state = _get(request, check_id)
    last = request.headers.get("last-event-id")
    start_after = int(last) if last and last.isdigit() else after

    async def gen():
        sent = start_after
        started = last_ping = time.monotonic()
        while time.monotonic() - started < STREAM_MAX_SECONDS:
            for event in state.events_after(sent):
                sent = event["seq"]
                yield f"id: {sent}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
                last_ping = time.monotonic()
            # Close at the end, and also when the agent waits for the user: the client posts the
            # answer and reconnects with Last-Event-ID (EventSource does this automatically).
            if state.status in ("done", "failed", "needs_user_input") and not state.events_after(
                sent
            ):
                return
            if await request.is_disconnected():
                return
            if time.monotonic() - last_ping > KEEPALIVE_SECONDS:
                yield ": keep-alive\n\n"
                last_ping = time.monotonic()
            await asyncio.sleep(0.1)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class Answer(BaseModel):
    answer: str = Field(max_length=200)


@router.post("/{check_id}/answer", status_code=202)
def answer_check(request: Request, check_id: str, body: Answer):
    state = _get(request, check_id)
    if state.status != "needs_user_input":
        return _error(409, "not_waiting", "This check is not waiting for an answer.")
    state.status = "verifying"
    _executor(request).submit(pipeline.answer, state, body.answer.strip(), _spend(request))
    return {"check_id": check_id, "status": state.status}
