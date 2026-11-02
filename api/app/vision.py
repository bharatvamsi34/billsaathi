"""Isolate the bill in a photo with SAM 3.1 (concept "document") before reading it.

Never a reason to trust anything: any failure, timeout or implausible box means we use the
original image. The crop feeds field extraction only; the verbatim transcription always reads
the original, so a link outside the crop still reaches the milestone check.

Images go inline (data URL), so no file is stored on Meta's servers. Only the box leaves this
module in events; the web app draws it over the image the user already has.
"""

import base64
import io
import logging
import re
import time
from typing import Protocol

import httpx
from PIL import Image, ImageOps
from pydantic import BaseModel

from app.config import Settings
from app.models.base import LLMError

log = logging.getLogger("billsaathi.vision")

MODEL = "sam-3.1"
CONCEPT = "document"  # spike: "bill" finds nothing, "document" had IoU 0.98
PRICE_PER_IMAGE = 2.50 / 1000
MIN_AREA = 0.15  # smaller than this is not the bill: keep the whole image
FULL_AREA = 0.92  # the bill already fills the image: nothing to crop
MARGIN = 0.02
_BOX = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")


class Box(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    w: int
    h: int

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1) / (self.w * self.h)


class Isolation(BaseModel):
    image: bytes
    mime: str
    box: Box | None = None
    cropped: bool = False
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None


class Segmenter(Protocol):
    def segment(self, image: bytes, mime: str) -> str: ...


class MetaSam:
    def __init__(self, settings: Settings, *, http_client: httpx.Client | None = None):
        if settings.meta_api_key is None or not settings.meta_api_base_url:
            raise LLMError("META_API_KEY and META_API_BASE_URL must be set")
        self._url = f"{settings.meta_api_base_url.rstrip('/')}/responses"
        self._model = settings.meta_model_sam or MODEL
        self._http = http_client or httpx.Client(timeout=settings.sam_timeout_seconds)
        self._headers = {"Authorization": f"Bearer {settings.meta_api_key.get_secret_value()}"}

    def segment(self, image: bytes, mime: str) -> str:
        url = f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}"
        body = {
            "model": self._model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": CONCEPT},
                        {"type": "input_image", "image_url": url},
                    ],
                }
            ],
            "metadata": {"mask_encoding": "lossless"},
        }
        try:
            r = self._http.post(self._url, headers=self._headers, json=body)
        except httpx.HTTPError as e:
            raise LLMError(f"SAM failed: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise LLMError(f"SAM failed: HTTP {r.status_code}")
        return "".join(
            part.get("text", "")
            for item in r.json().get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
        )


def parse_box(text: str) -> Box | None:
    """The largest well-formed box in SAM's text tokens, if any."""
    boxes = []
    for groups in _BOX.findall(text):
        x1, y1, x2, y2, w, h = map(int, groups)
        if w > 0 and h > 0 and 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h:
            boxes.append(Box(x1=x1, y1=y1, x2=x2, y2=y2, w=w, h=h))
    return max(boxes, key=lambda b: b.area, default=None)


def crop(image: bytes, box: Box) -> bytes:
    """The box plus a small margin, as JPEG, with the phone's rotation already applied."""
    with Image.open(io.BytesIO(image)) as opened:
        im = ImageOps.exif_transpose(opened).convert("RGB")
    if im.size != (box.w, box.h):  # SAM saw another size or rotation: do not guess
        raise ValueError("box does not match the image size")
    dx, dy = int(box.w * MARGIN), int(box.h * MARGIN)
    area = (max(box.x1 - dx, 0), max(box.y1 - dy, 0), min(box.x2 + dx, box.w), min(box.y2 + dy, box.h))  # fmt: skip
    out = io.BytesIO()
    im.crop(area).save(out, format="JPEG", quality=92)
    return out.getvalue()


def isolate(segmenter: Segmenter, image: bytes, mime: str) -> Isolation:
    """Never raises: on any problem the original image comes back, with the reason."""
    t0 = time.perf_counter()
    result = Isolation(image=image, mime=mime, cost_usd=PRICE_PER_IMAGE)
    try:
        box = parse_box(segmenter.segment(image, mime))
        if box is not None and box.area >= MIN_AREA:
            result.box = box
            if box.area < FULL_AREA:
                result.image, result.mime, result.cropped = crop(image, box), "image/jpeg", True
    except Exception as e:  # any failure means the original image, never a failed check
        log.warning("isolate failed: %s", type(e).__name__)
        result.error = type(e).__name__
        result.box = None
    result.latency_ms = (time.perf_counter() - t0) * 1000
    return result
