"""Muse Image draws the background of the "Warn my family" card.

The prompt is fixed and carries no user data. The picture has no text: the browser draws the
vetted warning on top, so Telugu and Hindi stay exact and facts never come from a model. All the
model's tools stay off (shell, web search, image search). One picture per verdict is cached in
memory, so a busy demo pays once; if generation fails the web app uses a plain card.
"""

import base64
import logging
import threading
import time
from typing import Literal

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.api.checks import _spend, _state
from app.config import Settings
from app.models.base import LLMError
from app.models.pricing import cost_usd

log = logging.getLogger("billsaathi.sharecard")

router = APIRouter(prefix="/api/v1/share-card", tags=["share-card"])

MODEL = "muse-image-1.0"
TOOLS_OFF = {"enable_shell": "false", "enable_web_search": "false", "enable_image_search": "false"}
_STYLE = (
    "Flat, calm editorial illustration in deep navy and teal with one saffron accent. Soft shapes, "
    "plenty of empty dark space in the middle for a caption. Absolutely no text, letters, numbers, "
    "logos or real people's faces."
)
PROMPTS = {
    "SCAM": f"A large shield stopping a fake bill-payment message on a phone, protecting a family's home. {_STYLE}",
    "CAUTION": f"A person pausing to look carefully at a paper bill through a magnifying glass. {_STYLE}",
}


def _mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/webp"


class CardBackgrounds:
    def __init__(self, settings: Settings, *, http_client: httpx.Client | None = None):
        if settings.meta_api_key is None or not settings.meta_api_base_url:
            raise LLMError("META_API_KEY and META_API_BASE_URL must be set")
        self._url = f"{settings.meta_api_base_url.rstrip('/')}/responses"
        self._http = http_client or httpx.Client(timeout=60.0)
        self._headers = {"Authorization": f"Bearer {settings.meta_api_key.get_secret_value()}"}
        self._cache: dict[str, bytes] = {}
        self._lock = threading.Lock()  # two viewers at once still make one picture

    def get(self, verdict: str) -> tuple[bytes, float]:
        """(image bytes, cost of this call). Raises LLMError if no picture came back."""
        with self._lock:
            if verdict in self._cache:
                return self._cache[verdict], 0.0
            data, cost = self._generate(verdict)
            self._cache[verdict] = data
            return data, cost

    def _generate(self, verdict: str) -> tuple[bytes, float]:
        t0 = time.perf_counter()
        body = {"model": MODEL, "input": PROMPTS[verdict], "metadata": TOOLS_OFF}
        try:
            r = self._http.post(self._url, headers=self._headers, json=body)
        except httpx.HTTPError as e:
            raise LLMError(f"Muse Image failed: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise LLMError(f"Muse Image failed: HTTP {r.status_code}")
        reply = r.json()
        image = next(
            (i.get("result") for i in reply.get("output", []) if i.get("type") == "image_generation_call"),
            None,
        )  # fmt: skip
        if not image:
            raise LLMError("Muse Image returned no picture")
        usage = reply.get("usage") or {}
        # Estimated from tokens at Spark rates: no per-image price is listed.
        cost = cost_usd(
            "muse-spark-1.3", usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        )
        log.info("card background verdict=%s ms=%.0f est_cost_usd=%.4f", verdict, (time.perf_counter() - t0) * 1000, cost)  # fmt: skip
        return base64.b64decode(image), cost


def _backgrounds(request: Request) -> CardBackgrounds:
    return _state(request, "card_backgrounds", CardBackgrounds)


@router.get("/background")
def background(request: Request, verdict: Literal["SCAM", "CAUTION"]):
    spend = _spend(request)
    try:
        cards = _backgrounds(request)
        # A cached picture costs nothing, so only a new one is refused over the daily cap.
        if verdict not in cards._cache and spend.exceeded():
            return JSONResponse({"error": "service_busy"}, status_code=503)
        data, cost = cards.get(verdict)
    except LLMError as e:
        log.warning("card background failed: %s", e)
        return JSONResponse({"error": "no_background"}, status_code=503)
    spend.add(cost)
    return Response(content=data, media_type=_mime(data), headers={"Cache-Control": "public, max-age=86400"})  # fmt: skip
