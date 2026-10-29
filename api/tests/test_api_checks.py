"""Checks API end to end with a scripted agent and a fake extraction model (no API calls)."""

import io
import json

import pytest
from dataset_utils import DATA, LABELS
from fakes import ScriptedModel, evidence, last_outputs, submit, turn
from fastapi.testclient import TestClient
from PIL import Image

from app import pipeline
from app.config import Settings
from app.main import app
from app.models.base import LLMError, LLMResponse, Usage
from app.pii import mask_id

BY_ID = {lbl.id: lbl for lbl in LABELS}
GENUINE = BY_ID["reminder_en_demo"]
BILL = BY_ID["bill_genuine_demo"]
SCAM = BY_ID["scam_te_known_vpa"]


class InlineExecutor:
    """Runs submitted work immediately, so each request finishes its check before returning."""

    def submit(self, fn, *args):
        fn(*args)


class FakeExtractor:
    provider = "fake"

    def __init__(self, label=None, *, error: Exception | None = None, **overrides):
        self.label, self.error, self.overrides = label, error, overrides

    def respond(self, *, system, messages, model, effort="low", max_output_tokens=4096):
        if self.error:
            raise self.error
        fields = self.label.expected.extracted.model_dump(mode="json") | self.overrides
        reply = {k: {"value": v, "confidence": 0.95} for k, v in fields.items()}
        reply["visible_text"] = self.label.input.text or ""
        usage = Usage(input_tokens=2000, output_tokens=600, cost_usd=0.005)
        return LLMResponse(
            text=json.dumps(reply), model=model, provider="fake", latency_ms=5, usage=usage
        )


def cite_all(verdict):
    def step(conv):
        ids = evidence(conv)
        return submit(
            verdict, *[(f"Finding {i + 1} from the checks.", [eid]) for i, eid in enumerate(ids)]
        )

    return step


@pytest.fixture
def api():
    """A clean app state per test; returns a function to install the fake models."""
    names = ("settings", "executor", "clients", "check_store", "rate_limiter", "spend_meter")
    saved = {n: getattr(app.state, n, None) for n in names}
    app.state.settings = Settings(_env_file=None, rate_limit_per_minute=50, daily_spend_cap_usd=5.0)
    app.state.executor = InlineExecutor()
    for n in ("check_store", "rate_limiter", "spend_meter"):
        setattr(app.state, n, None)

    def install(label, steps, **extract_kw):
        agent = ScriptedModel(steps)
        app.state.clients = pipeline.Clients(
            extract=FakeExtractor(label, **extract_kw), agent=agent, judge=agent
        )
        return agent

    yield TestClient(app), install
    for n, v in saved.items():
        setattr(app.state, n, v)


def events_of(client, check_id, **headers):
    body = client.get(f"/api/v1/checks/{check_id}/events", headers=headers).text
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


def post_text(client, text, language="en"):
    return client.post("/api/v1/checks", data={"text": text, "language": language})


# --- happy paths and the event stream ---


def test_text_check_streams_every_step_in_order(api):
    client, install = api
    install(GENUINE, [cite_all("SAFE")])
    r = post_text(client, GENUINE.input.text)
    assert r.status_code == 202
    check_id = r.json()["check_id"]
    events = events_of(client, check_id)
    types = [e["type"] for e in events]
    assert types == [
        "received", "extracted", "verification_started",
        *["check"] * 6, "agent_turn", "judge", "verdict", "complete",
    ]  # fmt: skip
    assert [e["seq"] for e in events] == list(range(len(events)))
    checks = [e for e in events if e["type"] == "check"]
    assert all(c["origin"] == "mandatory" for c in checks)
    assert [c["tool"] for c in checks][0] == "lookup_biller"
    verdict = events[-2]
    assert verdict["verdict"] == "SAFE" and verdict["user_confirmation_required"] is True

    result = client.get(f"/api/v1/checks/{check_id}").json()
    assert result["status"] == "done" and result["verdict"]["verdict"] == "SAFE"
    assert result["cost_usd"]["extraction"] == 0.005 and result["cost_usd"]["total"] > 0.005
    assert result["agent"]["model_turns"] == 1 and result["agent"]["mandatory_calls"] == 6


def test_nothing_sensitive_leaves_the_server(api):
    client, install = api
    install(GENUINE, [cite_all("SAFE")])
    check_id = post_text(client, GENUINE.input.text).json()["check_id"]
    everything = (
        client.get(f"/api/v1/checks/{check_id}/events").text
        + client.get(f"/api/v1/checks/{check_id}").text
    )
    consumer = GENUINE.expected.extracted.consumer_number
    assert consumer not in everything and mask_id(consumer) in everything
    assert "Ignore if already paid" not in everything  # raw message text is never echoed


def test_image_check_and_last_event_id_resume(api):
    client, install = api
    install(BILL, [cite_all("SAFE")])
    png = (DATA / BILL.input.path).read_bytes()
    r = client.post(
        "/api/v1/checks", files={"image": ("bill.png", png, "image/png")}, data={"language": "te"}
    )
    check_id = r.json()["check_id"]
    events = events_of(client, check_id)
    assert events[0] == {**events[0], "type": "received", "input": "image", "language": "te"}
    assert events[-2]["verdict"] == "SAFE"
    later = events_of(client, check_id, **{"Last-Event-ID": "3"})
    assert [e["seq"] for e in later] == list(range(4, len(events)))


def test_scam_verdict_shows_checked_helpline_fact(api):
    client, install = api

    def scam_with_fact(conv):
        ids = evidence(conv, "KNOWN_SCAM_DESTINATION")
        return submit(
            "SCAM",
            ("The payment ID is on the known-scam list.", ids),
            facts=["cybercrime_helpline"],
        )

    install(SCAM, [scam_with_fact])
    check_id = post_text(client, SCAM.input.text, "te").json()["check_id"]
    verdict = client.get(f"/api/v1/checks/{check_id}").json()["verdict"]
    assert verdict["verdict"] == "SCAM"
    assert verdict["facts"] == [
        {"key": "cybercrime_helpline", "label": "National Cyber Crime Helpline (India)", "value": "1930", "source": "MHA / cybercrime.gov.in"}
    ]  # fmt: skip


# --- ask_user over the API ---


def test_question_pauses_the_check_and_an_answer_resumes_it(api):
    client, install = api
    consumer = GENUINE.expected.extracted.consumer_number
    ask = turn(
        ("ask_user", {"field": "consumer_number", "question": "What is the consumer number?"})
    )

    def fetch_with_answer(conv):
        answer = last_outputs(conv)[-1]["answer"]
        common = {"biller_id": "DEMO00000MAH01", "consumer_number": answer}
        return turn(("fetch_bill", common | {"claimed_amount": 1240.0}), ("get_bill_history", common | {"current_amount": 1240.0}))  # fmt: skip

    label = GENUINE.model_copy(deep=True)
    label.expected.extracted.amount = 1240.0
    install(label, [ask, fetch_with_answer, cite_all("SAFE")], consumer_number=None)
    check_id = post_text(
        client, "Demo Power bill Rs 1,240 due 05-Nov-2026. Pay at demopower.example"
    ).json()["check_id"]

    waiting = client.get(f"/api/v1/checks/{check_id}").json()
    assert waiting["status"] == "needs_user_input"
    assert waiting["question"]["field"] == "consumer_number"
    assert [e["type"] for e in events_of(client, check_id)][-2:] == ["agent_turn", "question"]

    assert (
        client.post(
            f"/api/v1/checks/{check_id}/answer", json={"answer": "DP-4410-882761"}
        ).status_code
        == 202
    )
    done = client.get(f"/api/v1/checks/{check_id}").json()
    assert done["status"] == "done" and done["verdict"]["verdict"] == "SAFE"
    tail = [e["type"] for e in events_of(client, check_id)]
    assert tail[tail.index("question") + 1] == "answer"
    assert tail[-2:] == ["verdict", "complete"]
    assert "DP-4410-882761" not in client.get(f"/api/v1/checks/{check_id}/events").text
    assert client.post(f"/api/v1/checks/{check_id}/answer", json={"answer": "x"}).status_code == 409
    assert consumer  # the dataset value is not what was answered here


# --- input validation ---


def tiny_image(fmt: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format=fmt)
    return buf.getvalue()


@pytest.mark.parametrize(
    "name,data,status",
    [
        ("bill.png", b"this is not an image", 415),  # extension lies
        ("bill.gif", tiny_image("GIF"), 415),  # real image, unsupported type
        ("bill.png", tiny_image("PNG")[:40], 415),  # truncated PNG
        ("huge.png", b"\x89PNG\r\n\x1a\n" + b"0" * 8_000_000, 413),
    ],
    ids=["not_an_image", "gif", "truncated_png", "over_8mb"],
)
def test_bad_images_are_rejected(api, name, data, status):
    client, install = api
    install(BILL, [])
    r = client.post("/api/v1/checks", files={"image": (name, data, "image/png")})
    assert r.status_code == status and "error" in r.json()


@pytest.mark.parametrize(
    "fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_supported_images_are_detected_by_content(fmt, mime):
    from app.api.checks import sniff_image

    assert sniff_image(tiny_image(fmt)) == mime


def test_input_shape_rules(api):
    client, install = api
    install(GENUINE, [])
    assert client.post("/api/v1/checks", data={"language": "en"}).status_code == 400
    both = client.post(
        "/api/v1/checks",
        data={"text": "hi"},
        files={"image": ("a.png", tiny_image("PNG"), "image/png")},
    )
    assert both.status_code == 400
    audio = client.post("/api/v1/checks", files={"audio": ("q.wav", b"RIFF....WAVE", "audio/wav")})
    assert audio.status_code == 501 and audio.json()["error"] == "audio_not_supported_yet"
    assert client.post("/api/v1/checks", data={"text": "hi", "language": "fr"}).status_code == 422
    assert post_text(client, "x" * 4001).status_code == 413
    assert client.get("/api/v1/checks/nope").status_code == 404


# --- protections ---


def test_rate_limit_per_ip(api):
    client, install = api
    app.state.settings = Settings(_env_file=None, rate_limit_per_minute=2, daily_spend_cap_usd=5.0)
    install(GENUINE, [cite_all("SAFE"), cite_all("SAFE")])
    assert post_text(client, GENUINE.input.text).status_code == 202
    assert post_text(client, GENUINE.input.text).status_code == 202
    third = post_text(client, GENUINE.input.text)
    assert third.status_code == 429 and third.json()["error"] == "rate_limited"


def test_daily_spend_cap_returns_service_busy(api):
    client, install = api
    # one check spends $0.009 (extraction $0.005 + agent turn and judge $0.004)
    app.state.settings = Settings(
        _env_file=None, rate_limit_per_minute=50, daily_spend_cap_usd=0.008
    )
    install(GENUINE, [cite_all("SAFE")])
    assert post_text(client, GENUINE.input.text).status_code == 202
    busy = post_text(client, GENUINE.input.text)
    assert busy.status_code == 503 and busy.json()["error"] == "service_busy"


def test_extraction_failure_ends_as_caution(api):
    client, install = api
    install(GENUINE, [], error=LLMError("RateLimitError after 3 attempts"))
    check_id = post_text(client, GENUINE.input.text).json()["check_id"]
    result = client.get(f"/api/v1/checks/{check_id}").json()
    assert result["status"] == "failed"
    assert result["verdict"]["verdict"] == "CAUTION" and result["verdict"]["forced"]
    assert [e["type"] for e in events_of(client, check_id)] == ["received", "verdict", "complete"]


def test_cors_allows_only_the_configured_origin():
    client = TestClient(app)
    preflight = {"Access-Control-Request-Method": "POST"}
    ok = client.options("/api/v1/checks", headers={"Origin": "http://localhost:3000", **preflight})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options("/api/v1/checks", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in bad.headers
