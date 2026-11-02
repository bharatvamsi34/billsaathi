"""Voice input: check the WAV the browser made, decode WhatsApp voice notes, and call
Muse Voice Transcribe. The user's language always goes along as languageBias.
"""

import io
import json
import logging
import time
import wave
from typing import Protocol

import httpx
import numpy as np
import soundfile
from pydantic import BaseModel

from app.config import Settings
from app.models.base import LLMError

log = logging.getLogger("billsaathi.voice")

MODEL = "muse-voice-transcribe-1.0"
PRICE_PER_SECOND = 0.18 / 3600
SAMPLE_RATE = 16_000
MAX_SECONDS = 60
MAX_WAV_BYTES = 44 + SAMPLE_RATE * 2 * MAX_SECONDS
MAX_NOTE_BYTES = 5_000_000  # a compressed WhatsApp voice note
BIAS = {"en": ["English"], "te": ["Telugu", "English"], "hi": ["Hindi", "English"]}
ALL_LANGUAGES = ["English", "Telugu", "Hindi"]  # WhatsApp sender with no language yet


class VoiceError(Exception):
    """The audio cannot be used (wrong format, too long, undecodable)."""


class Transcript(BaseModel):
    text: str
    latency_ms: float = 0.0
    cost_usd: float = 0.0


class SpeechClient(Protocol):
    def transcribe_audio(self, wav: bytes, language: str | None) -> Transcript: ...


def check_wav(data: bytes) -> float:
    """Seconds of audio, if this is the 16 kHz mono 16-bit WAV we ask for."""
    if len(data) > MAX_WAV_BYTES:
        raise VoiceError(f"longer than {MAX_SECONDS} seconds")
    try:
        with wave.open(io.BytesIO(data)) as w:
            shape = (w.getframerate(), w.getnchannels(), w.getsampwidth())
            frames = w.getnframes()
    except (wave.Error, EOFError) as e:
        raise VoiceError("not a WAV file") from e
    if shape != (SAMPLE_RATE, 1, 2):
        raise VoiceError("audio must be 16 kHz mono 16-bit")
    if frames == 0:
        raise VoiceError("empty recording")
    return frames / SAMPLE_RATE


def note_to_wav(data: bytes) -> bytes:
    """A WhatsApp voice note (OGG/Opus) as 16 kHz mono 16-bit WAV, at most MAX_SECONDS long."""
    try:
        samples, rate = soundfile.read(io.BytesIO(data), dtype="float32", always_2d=True)
    except Exception as e:  # libsndfile raises several types for bad input
        raise VoiceError("could not decode the voice note") from e
    mono = samples.mean(axis=1)[: rate * MAX_SECONDS]
    if mono.size == 0:
        raise VoiceError("empty recording")
    count = int(mono.size * SAMPLE_RATE / rate)
    resampled = np.interp(np.arange(count) * rate / SAMPLE_RATE, np.arange(mono.size), mono)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((np.clip(resampled, -1, 1) * 32767).astype("<i2").tobytes())
    return out.getvalue()


class MetaSpeech:
    """POST /asr/transcribe, multipart (the only Meta call that is not the Responses format)."""

    def __init__(self, settings: Settings, *, http_client: httpx.Client | None = None):
        if settings.meta_api_key is None or not settings.meta_api_base_url:
            raise LLMError("META_API_KEY and META_API_BASE_URL must be set")
        self._url = f"{settings.meta_api_base_url.rstrip('/')}/asr/transcribe"
        self._model = settings.meta_model_transcribe or MODEL
        self._http = http_client or httpx.Client(timeout=settings.model_timeout_seconds)
        self._headers = {"Authorization": f"Bearer {settings.meta_api_key.get_secret_value()}"}

    def transcribe_audio(self, wav: bytes, language: str | None) -> Transcript:
        request = {
            "mode": "PUSH_TO_TALK",
            "model": self._model,
            "audioEncoding": "WAV",
            "languageBias": BIAS.get(language or "", ALL_LANGUAGES),
        }
        files = {
            "request": (None, json.dumps(request), "application/json"),
            "audio": ("voice.wav", wav, "audio/wav"),
        }
        t0 = time.perf_counter()
        try:
            r = self._http.post(self._url, headers=self._headers, files=files)
        except httpx.HTTPError as e:
            raise LLMError(f"transcribe failed: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise LLMError(f"transcribe failed: HTTP {r.status_code}")
        body = r.json()
        latency_ms = (time.perf_counter() - t0) * 1000
        seconds = (body.get("audioDurationMs") or 0) / 1000
        cost = seconds * PRICE_PER_SECOND
        log.info("asr ok latency_ms=%.0f seconds=%.1f cost_usd=%.5f", latency_ms, seconds, cost)
        return Transcript(
            text=(body.get("transcript") or "").strip(), latency_ms=latency_ms, cost_usd=cost
        )
