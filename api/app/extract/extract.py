"""Read a bill or payment request into validated, typed fields (step 1 of the pipeline).

Extraction only reads; deciding whether the request is genuine is the agent's job.
Images are sent inline as data URLs. Model output is never used unless it validates
against ExtractionOutput; invalid output is retried up to 2 times with the validation
error fed back to the model.
"""

import base64
import json
import logging
import re

from pydantic import BaseModel, ValidationError

from app.models.base import LLMClient, LLMError, Message, Usage
from app.pii import mask_id
from app.schemas import ExtractionOutput

log = logging.getLogger("billsaathi.extract")

DEFAULT_MODEL = "muse-spark-1.3"
MAX_ATTEMPTS = 3  # first try + 2 retries
MAX_OUTPUT_TOKENS = 4096
MAX_IMAGE_BYTES = 8_000_000
IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}

SYSTEM_PROMPT = (
    "You read Indian bills and payment requests (paper bills, SMS and WhatsApp messages) and "
    "return their fields as JSON. You only read; you do not judge whether the request is genuine.\n"
    "Rules:\n"
    "- Reply with ONLY one JSON object that matches the JSON Schema below. No prose, no code fences.\n"
    "- Copy values exactly as printed: biller name, consumer/account number, UPI IDs, links, phone "
    "numbers. Never guess or complete a value; use null when it is missing or unreadable.\n"
    "- amount: the amount the reader is asked to pay, as a number in INR (no commas, no ₹).\n"
    "- Dates as YYYY-MM-DD.\n"
    "- payment_destinations: every UPI ID, link or website, phone number or QR text where the "
    "reader is asked to pay or call. kind is upi, url, phone or qr.\n"
    '- languages: ISO 639-1 codes of the languages used, main language first, e.g. ["te", "en"].\n'
    "- urgency_language: true only if the text pressures the reader (threatens to cut the "
    "connection tonight, says 'immediately', sets a deadline of hours).\n"
    "- confidence: 0 to 1 for each field; give a low value when the text is blurred, cut off or "
    "ambiguous.\n"
    "JSON Schema:\n" + json.dumps(ExtractionOutput.model_json_schema())
)

TRANSCRIBE_PROMPT = (
    "Copy every piece of text you can see in this image, exactly as written, in reading order. "
    "Keep links, UPI IDs, phone numbers and amounts character for character. Do not translate, "
    "summarise or explain. Reply with only the text."
)


class ExtractionResult(BaseModel):
    output: ExtractionOutput
    model: str
    attempts: int
    latency_ms: float
    usage: Usage


class Transcription(BaseModel):
    text: str
    latency_ms: float
    usage: Usage


class ExtractionFailed(Exception):
    def __init__(self, message: str, attempts: int):
        super().__init__(message)
        self.attempts = attempts


class TranscriptionFailed(Exception):
    pass


def _image_message(image: bytes, image_mime: str | None, text: str) -> Message:
    if image_mime not in IMAGE_MIMES:
        raise ValueError(f"unsupported image type {image_mime!r}")
    if len(image) > MAX_IMAGE_BYTES:
        raise ValueError("image too large")
    url = f"data:{image_mime};base64,{base64.b64encode(image).decode('ascii')}"
    return Message(role="user", text=text, image_data_url=url)


def transcribe(
    client: LLMClient, *, image: bytes, image_mime: str | None, model: str = DEFAULT_MODEL
) -> Transcription:
    """Verbatim text of an image, used only by the milestone check (never shown to the agent).
    Runs in parallel with extract(); one retry on an empty answer."""
    message = _image_message(image, image_mime, "Transcribe this image.")
    latency_ms, usage = 0.0, Usage()
    for _ in range(2):
        try:
            resp = client.respond(
                system=TRANSCRIBE_PROMPT,
                messages=[message],
                model=model,
                effort="low",
                max_output_tokens=2048,
            )
        except LLMError as e:
            raise TranscriptionFailed(f"model unavailable: {e}") from e
        latency_ms += resp.latency_ms
        for field in ("input_tokens", "output_tokens", "reasoning_tokens", "cost_usd"):
            setattr(usage, field, getattr(usage, field) + getattr(resp.usage, field))
        if resp.text.strip():
            return Transcription(text=resp.text.strip(), latency_ms=latency_ms, usage=usage)
    raise TranscriptionFailed("empty transcription")


def parse_json(text: str) -> object:
    """First JSON object in the model's text (tolerates code fences and surrounding prose)."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch == "{":
            try:
                return decoder.raw_decode(cleaned[i:])[0]
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON object found")


def _problem(e: Exception) -> str:
    if isinstance(e, ValidationError):
        return "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:6]
        )
    return str(e)


def extract(
    client: LLMClient,
    *,
    image: bytes | None = None,
    image_mime: str | None = None,
    text: str | None = None,
    model: str = DEFAULT_MODEL,
) -> ExtractionResult:
    if (image is None) == (text is None):
        raise ValueError("give exactly one of image or text")
    if image is not None:
        messages = [_image_message(image, image_mime, "Extract the fields from this image.")]
    else:
        messages = [Message(role="user", text=f"Extract the fields from this message:\n\n{text}")]

    usage = Usage()
    latency_ms = 0.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = client.respond(
                system=SYSTEM_PROMPT,
                messages=messages,
                model=model,
                effort="low",
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
        except LLMError as e:
            raise ExtractionFailed(f"model unavailable: {e}", attempt) from e
        latency_ms += resp.latency_ms
        for field in ("input_tokens", "output_tokens", "reasoning_tokens", "cost_usd"):
            setattr(usage, field, getattr(usage, field) + getattr(resp.usage, field))
        try:
            output = ExtractionOutput.model_validate(parse_json(resp.text))
        except (ValueError, ValidationError) as e:
            problem = _problem(e)
            log.warning(
                "extraction invalid attempt=%d model=%s problem=%s",
                attempt,
                model,
                type(e).__name__,
            )
            messages = [
                *messages,
                Message(role="assistant", text=resp.text[:4000]),
                Message(
                    role="user",
                    text=f"That reply was not valid: {problem}. "
                    "Reply again with ONLY the corrected JSON object.",
                ),
            ]
            continue
        log.info(
            "extraction ok attempts=%d model=%s biller=%s consumer=%s amount=%s destinations=%d",
            attempt,
            model,
            output.biller_name.value,
            mask_id(output.consumer_number.value),
            output.amount.value,
            len(output.payment_destinations.value),
        )
        return ExtractionResult(
            output=output,
            model=model,
            attempts=attempt,
            latency_ms=latency_ms,
            usage=usage,
        )
    raise ExtractionFailed(f"no valid output after {MAX_ATTEMPTS} attempts", MAX_ATTEMPTS)
