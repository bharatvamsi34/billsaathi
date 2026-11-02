"""Voice input: WAV checks, the Transcribe call, the checks API and WhatsApp voice notes."""

import io
import json
import math
import wave

import httpx
import numpy as np
import pytest
import soundfile
from test_api_checks import GENUINE, api, cite_all, events_of  # noqa: F401
from test_whatsapp import PHONE, message, payload, post, wa  # noqa: F401

from app.config import Settings
from app.main import app
from app.models.base import LLMError
from app.voice import (
    MAX_SECONDS,
    MetaSpeech,
    Transcript,
    VoiceError,
    check_wav,
    note_to_wav,
)
from app.whatsapp import texts


def tone(rate=16000, seconds=0.5, channels=1, width=2) -> bytes:
    frames = int(rate * seconds)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        peak = 8000 if width == 2 else 100
        sample = (int(peak * math.sin(i / 8)) for i in range(frames))
        pcm = b"".join(v.to_bytes(width, "little", signed=True) for v in sample for _ in range(channels))  # fmt: skip
        w.writeframes(pcm)
    return out.getvalue()


def voice_note() -> bytes:
    samples = np.sin(np.arange(48000) / 8).astype("float32")
    out = io.BytesIO()
    soundfile.write(out, samples, 48000, format="OGG", subtype="OPUS")
    return out.getvalue()


class FakeSpeech:
    def __init__(self, text="", error=None):
        self.text, self.error = text, error
        self.languages = []

    def transcribe_audio(self, wav, language):
        check_wav(wav)  # whatever the channel, the transcriber gets the agreed format
        self.languages.append(language)
        if self.error:
            raise self.error
        return Transcript(text=self.text, latency_ms=5, cost_usd=0.0001)


# --- format checks ---


def test_the_agreed_wav_passes():
    assert check_wav(tone(seconds=0.5)) == pytest.approx(0.5)


@pytest.mark.parametrize(
    "data",
    [tone(rate=8000), tone(channels=2), tone(width=1), b"not audio", tone(seconds=0)],
    ids=["8khz", "stereo", "8bit", "not-wav", "empty"],
)
def test_other_audio_is_refused(data):
    with pytest.raises(VoiceError):
        check_wav(data)


def test_too_long_is_refused():
    with pytest.raises(VoiceError):
        check_wav(b"\0" * (44 + 16000 * 2 * (MAX_SECONDS + 1)))


def test_voice_note_becomes_the_agreed_wav():
    assert check_wav(note_to_wav(voice_note())) == pytest.approx(1.0, abs=0.05)


def test_bad_voice_note_is_refused():
    with pytest.raises(VoiceError):
        note_to_wav(b"OggS not really")


# --- the Transcribe call ---


def _speech(handler):
    settings = Settings(_env_file=None, meta_api_key="k", meta_api_base_url="https://m.example/v1")
    return MetaSpeech(settings, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize(
    "language,bias",
    [
        ("te", ["Telugu", "English"]),
        ("hi", ["Hindi", "English"]),
        ("en", ["English"]),
        (None, ["English", "Telugu", "Hindi"]),
    ],
)
def test_language_bias_is_always_sent(language, bias):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        body = request.content.decode("latin-1")
        seen["request"] = json.loads(body[body.index('{"mode"') : body.index("}", body.index('{"mode"')) + 1])  # fmt: skip
        return httpx.Response(200, json={"transcript": " hello ", "audioDurationMs": 3600})

    out = _speech(handler).transcribe_audio(tone(), language)
    assert seen["url"] == "https://m.example/v1/asr/transcribe"
    assert seen["request"]["languageBias"] == bias and seen["request"]["audioEncoding"] == "WAV"
    assert out.text == "hello" and out.cost_usd == pytest.approx(0.18 / 1000)


def test_transcribe_failure_is_an_llm_error():
    with pytest.raises(LLMError):
        _speech(lambda r: httpx.Response(500)).transcribe_audio(tone(), "en")


# --- checks API ---


def post_audio(client, data, language="en"):
    files = {"audio": ("v.wav", data, "audio/wav")}
    return client.post("/api/v1/checks", data={"language": language}, files=files)


def test_recording_is_heard_then_checked_as_text(api):  # noqa: F811
    client, install = api
    install(GENUINE, [cite_all("SAFE")])
    speech = app.state.clients.speech = FakeSpeech(GENUINE.input.text)
    r = post_audio(client, tone(), "te")
    assert r.status_code == 202
    events = events_of(client, r.json()["check_id"])
    assert [e["type"] for e in events][:3] == ["received", "transcribed", "extracted"]
    assert speech.languages == ["te"]
    assert next(e for e in events if e["type"] == "verdict")["verdict"] == "SAFE"
    assert events[-1]["cost_usd"]["speech"] == 0.0001


def test_heard_text_is_masked_in_the_stream(api):  # noqa: F811
    client, install = api
    install(GENUINE, [cite_all("CAUTION")])
    app.state.clients.speech = FakeSpeech("Call 9123456780 to pay")
    events = events_of(client, post_audio(client, tone()).json()["check_id"])
    assert "9123456780" not in next(e for e in events if e["type"] == "transcribed")["text"]


@pytest.mark.parametrize(
    "speech", [FakeSpeech(""), FakeSpeech(error=LLMError("down")), None], ids=["silent", "down", "none"]
)  # fmt: skip
def test_unusable_recording_ends_as_caution_never_safe(api, speech):  # noqa: F811
    client, install = api
    install(GENUINE, [])
    app.state.clients.speech = speech
    events = events_of(client, post_audio(client, tone()).json()["check_id"])
    verdict = next(e for e in events if e["type"] == "verdict")
    assert verdict["verdict"] == "CAUTION" and verdict["forced"] is True


def test_wrong_audio_format_is_refused(api):  # noqa: F811
    client, install = api
    install(GENUINE, [])
    assert post_audio(client, tone(rate=44100)).status_code == 415


def test_exactly_one_input_is_allowed(api):  # noqa: F811
    client, install = api
    install(GENUINE, [])
    r = client.post(
        "/api/v1/checks", data={"text": "hello"}, files={"audio": ("v.wav", tone(), "audio/wav")}
    )
    assert r.status_code == 400


# --- WhatsApp voice notes ---


def _note_message():
    m = message("x") | {"type": "audio", "audio": {"id": "VOICE1", "mime_type": "audio/ogg; codecs=opus", "voice": True}}  # fmt: skip
    m.pop("text")
    return m


def _serve_note(graph, data):
    inner = graph.__call__
    graph.image = data  # the fake serves one media file for MEDIA1 only, so map VOICE1 too

    def handler(request):
        url = str(request.url)
        if url.endswith("/v25.0/VOICE1"):
            return httpx.Response(200, json={"url": "https://lookaside.example/media/abc", "mime_type": "audio/ogg", "file_size": len(data)})  # fmt: skip
        return inner(request)

    app.state.whatsapp.graph._http = httpx.Client(
        headers=app.state.whatsapp.graph._http.headers, transport=httpx.MockTransport(handler)
    )


def test_voice_note_is_transcribed_then_checked(wa):  # noqa: F811
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("SAFE")])
    speech = app.state.clients.speech = FakeSpeech(GENUINE.input.text)
    _serve_note(graph, voice_note())
    post(client, payload(_note_message()))
    assert speech.languages == [None]  # no language chosen yet: listens for all three
    assert graph.bodies[0].startswith("🎤 I heard: ")
    assert graph.bodies[1] == texts.t("en", "checking")
    assert graph.bodies[2].startswith("✅ *SAFE*")
    assert graph.sent[0]["to"] == PHONE


def test_voice_note_reply_language_follows_what_was_said(wa):  # noqa: F811
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("CAUTION")])
    app.state.clients.speech = FakeSpeech("మీ బిల్లు ₹941")
    _serve_note(graph, voice_note())
    post(client, payload(_note_message()))
    assert graph.bodies[0].startswith("🎤 నేను విన్నది")
    assert graph.bodies[1] == texts.t("te", "checking")


def test_chosen_language_is_used_as_the_bias(wa):  # noqa: F811
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("CAUTION")])
    speech = app.state.clients.speech = FakeSpeech("some words")
    _serve_note(graph, voice_note())
    post(client, payload(message("हिंदी")))
    post(client, payload(_note_message()))
    assert speech.languages == ["hi"]


def test_undecodable_voice_note_gets_a_hint_and_no_check(wa):  # noqa: F811
    client, install, graph, _ = wa
    agent = install(GENUINE, [])
    speech = app.state.clients.speech = FakeSpeech("words")
    _serve_note(graph, b"OggS but not really")
    post(client, payload(_note_message()))
    assert graph.bodies == [texts.t("en", "bad_voice")]
    assert speech.languages == [] and agent.conversations == []
