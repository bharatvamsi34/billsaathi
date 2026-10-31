"""WhatsApp Cloud API webhook.

GET  /api/v1/whatsapp/webhook  Meta's verification handshake (hub.verify_token).
POST /api/v1/whatsapp/webhook  incoming messages: signature checked on the raw body,
                               duplicates dropped, 200 at once, work in the background.
"""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.checks import _clients, _executor, _settings, _spend, _store
from app.whatsapp.graph import GraphClient, GraphError
from app.whatsapp.service import WhatsAppService

log = logging.getLogger("billsaathi.whatsapp")

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])

MAX_BODY_BYTES = 1_000_000


def valid_signature(body: bytes, header: str | None, secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def _service(request: Request) -> WhatsAppService:
    service = getattr(request.app.state, "whatsapp", None)
    if service is None:
        settings = _settings(request)
        service = WhatsAppService(
            settings,
            GraphClient(settings),
            _store(request),
            _spend(request),
            clients=lambda: _clients(request),
        )
        request.app.state.whatsapp = service
    return service


@router.get("/webhook")
def verify(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    request: Request = None,
):
    expected = _settings(request).whatsapp_verify_token
    if (
        expected is None
        or mode != "subscribe"
        or token is None
        or challenge is None
        or not hmac.compare_digest(token.encode(), expected.get_secret_value().encode())
    ):
        return PlainTextResponse("forbidden", status_code=403)
    return PlainTextResponse(challenge)


@router.post("/webhook")
async def receive(request: Request):
    secret = _settings(request).whatsapp_app_secret
    if secret is None:
        return JSONResponse({"error": "not_configured"}, status_code=503)
    body = await request.body()
    if len(body) > MAX_BODY_BYTES or not valid_signature(
        body, request.headers.get("x-hub-signature-256"), secret.get_secret_value()
    ):
        log.warning("whatsapp webhook: invalid signature rejected")
        return JSONResponse({"error": "invalid_signature"}, status_code=401)
    try:
        payload = json.loads(body)
        service = _service(request)
    except (ValueError, GraphError) as e:
        log.warning("whatsapp webhook not processed: %s", type(e).__name__)
        return {"status": "ignored"}

    executor = _executor(request)
    for entry in payload.get("entry", []) if isinstance(payload, dict) else []:
        for change in entry.get("changes", []):
            for message in (change.get("value") or {}).get("messages", []):
                if message.get("id") and service.first_time(message["id"]):
                    executor.submit(service.handle, message)
    return {"status": "ok"}  # statuses (sent/delivered/read) and duplicates are acknowledged too
