"""WhatsApp webhook end to end with a mocked Graph API, a fake extractor and a scripted agent
(no network, no model calls)."""

import hashlib
import hmac
import json
import logging

import httpx
import pytest
from dataset_utils import DATA, LABELS
from fakes import ScriptedModel, last_outputs, turn
from fastapi.testclient import TestClient
from test_api_checks import FakeExtractor, InlineExecutor, cite_all

from app import pipeline
from app.api.store import CheckStore, SpendMeter
from app.config import Settings
from app.main import app
from app.schemas import EvidenceCode
from app.whatsapp import texts
from app.whatsapp.graph import GraphClient
from app.whatsapp.service import WhatsAppService, sender_hash

BY_ID = {lbl.id: lbl for lbl in LABELS}
GENUINE = BY_ID["reminder_en_demo"]
BILL = BY_ID["bill_genuine_demo"]
SCAM_TE = BY_ID["scam_te_known_vpa"]

SECRET = "test-app-secret"
VERIFY = "test-verify-token"
PHONE = "919900011122"  # synthetic
MEDIA_URL = "https://lookaside.example/media/abc"


class FakeGraph:
    """httpx transport standing in for graph.facebook.com: records sends, serves one image."""

    def __init__(self):
        self.sent: list[dict] = []
        self.media_auth: list[str] = []
        self.image = (DATA / BILL.input.path).read_bytes()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "POST" and url.endswith("/v25.0/PNID/messages"):
            self.sent.append(json.loads(request.content))
            return httpx.Response(200, json={"messages": [{"id": "wamid.out"}]})
        if url.endswith("/v25.0/MEDIA1"):
            return httpx.Response(
                200, json={"url": MEDIA_URL, "mime_type": "image/png", "file_size": len(self.image)}
            )
        if url == MEDIA_URL:
            self.media_auth.append(request.headers.get("authorization", ""))
            return httpx.Response(200, content=self.image)
        return httpx.Response(404)

    @property
    def bodies(self) -> list[str]:
        return [m["text"]["body"] for m in self.sent]


@pytest.fixture
def wa():
    names = ("settings", "executor", "clients", "check_store", "rate_limiter", "spend_meter", "whatsapp")  # fmt: skip
    saved = {n: getattr(app.state, n, None) for n in names}
    settings = Settings(
        _env_file=None,
        whatsapp_access_token="test-access-token",
        whatsapp_phone_number_id="PNID",
        whatsapp_app_secret=SECRET,
        whatsapp_verify_token=VERIFY,
        whatsapp_rate_limit_per_minute=5,
    )
    app.state.settings = settings
    app.state.executor = InlineExecutor()
    for n in ("check_store", "rate_limiter", "spend_meter", "whatsapp"):
        setattr(app.state, n, None)
    graph = FakeGraph()
    timers: list[tuple[float, object]] = []

    def install(label, steps, **extract_kw):
        agent = ScriptedModel(steps)
        app.state.clients = pipeline.Clients(
            extract=FakeExtractor(label, **extract_kw), agent=agent, judge=agent
        )
        # the same check store and spend meter the web API uses
        app.state.check_store = CheckStore(settings.check_ttl_seconds)
        app.state.spend_meter = SpendMeter(settings.daily_spend_cap_usd)
        app.state.whatsapp = WhatsAppService(
            settings,
            GraphClient(settings, transport=httpx.MockTransport(graph)),
            app.state.check_store,
            app.state.spend_meter,
            clients=lambda: app.state.clients,
            schedule=lambda delay, fn: timers.append((delay, fn)),
        )
        return agent

    yield TestClient(app), install, graph, timers
    for n, v in saved.items():
        setattr(app.state, n, v)


_ids = iter(range(10_000))


def message(text: str | None = None, *, image: str | None = None, msg_id: str | None = None):
    m = {"from": PHONE, "id": msg_id or f"wamid.in{next(_ids)}", "timestamp": "1761900000"}
    if image:
        m |= {"type": "image", "image": {"id": image, "mime_type": "image/png"}}
    else:
        m |= {"type": "text", "text": {"body": text}}
    return m


def payload(*messages) -> bytes:
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"phone_number_id": "PNID"},
        "contacts": [{"wa_id": PHONE, "profile": {"name": "Test"}}],
        "messages": list(messages),
    }
    body = {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": value}]}]}  # fmt: skip
    return json.dumps(body).encode()


def post(client, body: bytes, secret: str = SECRET):
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )


# --- verification handshake ---


def test_verification_returns_the_challenge(wa):
    client, *_ = wa
    params = {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "1158201444"}
    r = client.get("/api/v1/whatsapp/webhook", params=params)
    assert r.status_code == 200 and r.text == "1158201444"


@pytest.mark.parametrize(
    "params",
    [
        {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"},
        {"hub.mode": "unsubscribe", "hub.verify_token": VERIFY, "hub.challenge": "1"},
        {"hub.mode": "subscribe", "hub.challenge": "1"},
    ],
)
def test_verification_refuses_a_wrong_token_or_mode(wa, params):
    client, *_ = wa
    assert client.get("/api/v1/whatsapp/webhook", params=params).status_code == 403


# --- signature, duplicates, rate limit ---


def test_bad_or_missing_signature_is_rejected(wa):
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("SAFE")])
    body = payload(message(GENUINE.input.text))
    assert post(client, body, secret="not-the-secret").status_code == 401
    r = client.post("/api/v1/whatsapp/webhook", content=body, headers={"Content-Type": "application/json"})  # fmt: skip
    assert r.status_code == 401
    tampered = body.replace(b"Demo", b"Dem0")
    sig = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    r = client.post("/api/v1/whatsapp/webhook", content=tampered, headers={"X-Hub-Signature-256": sig})  # fmt: skip
    assert r.status_code == 401
    assert graph.sent == []


def test_duplicate_message_is_processed_once(wa):
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("SAFE")])
    body = payload(message(GENUINE.input.text, msg_id="wamid.same"))
    assert post(client, body).status_code == 200
    assert post(client, body).status_code == 200  # Meta's retry: acknowledged, not re-run
    assert len(graph.sent) == 2  # one "Checking…" and one verdict


def test_rate_limit_per_sender(wa):
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("SAFE")] * 6)
    app.state.whatsapp.limiter.per_minute = 1
    post(client, payload(message(GENUINE.input.text)))
    post(client, payload(message(GENUINE.input.text)))
    assert graph.bodies[-1] == texts.t("en", "rate_limited")


def test_status_updates_are_acknowledged_without_replies(wa):
    client, install, graph, _ = wa
    install(GENUINE, [])
    body = json.dumps({"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.out", "status": "read"}]}}]}]}).encode()  # fmt: skip
    assert post(client, body).status_code == 200
    assert graph.sent == []


# --- text and image through the same pipeline ---


def test_text_message_gets_checking_then_the_verdict(wa, caplog):
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("SAFE")])
    caplog.set_level(logging.INFO)
    msg = message(GENUINE.input.text)
    assert post(client, payload(msg)).status_code == 200

    checking, verdict = graph.sent
    assert checking["to"] == PHONE and checking["context"] == {"message_id": msg["id"]}
    assert checking["text"]["body"] == texts.t("en", "checking")
    body = verdict["text"]["body"]
    assert body.startswith("✅ *SAFE*\nChecks passed. Pay only after you confirm.")
    assert "• Finding 1 from the checks." in body
    assert "1930" not in body  # helpline only on SCAM
    assert "https://zealous-coast-09279dd00.1.azurestaticapps.net" in body
    assert body.endswith("_Sandbox demo — billers are mock; no real payment._")
    assert PHONE not in caplog.text and sender_hash(PHONE, SECRET) in caplog.text


def test_telugu_scam_message_gets_a_telugu_scam_verdict(wa):
    client, install, graph, _ = wa
    install(SCAM_TE, [cite_all("SCAM")])
    post(client, payload(message(SCAM_TE.input.text)))
    checking, verdict = graph.bodies
    assert checking == texts.t("te", "checking")
    assert verdict.startswith("⛔ *మోసం*\nఇది మోసంలా ఉంది. చెల్లించవద్దు.")
    assert "📞 మోసాన్ని ఫిర్యాదు చేయండి: 1930 కు కాల్ చేయండి" in verdict
    assert texts.CODE_LABELS["KNOWN_SCAM_DESTINATION"]["te"] in verdict  # cited evidence, in Telugu
    assert "Finding" not in verdict  # English agent text is not shown in Telugu
    assert "electricityofficer@okdemo" not in verdict


def test_image_message_is_downloaded_and_checked(wa):
    client, install, graph, _ = wa
    install(BILL, [cite_all("SAFE")])
    post(client, payload(message(image="MEDIA1")))
    assert graph.media_auth == ["Bearer test-access-token"]
    assert graph.bodies[0] == texts.t("en", "checking")
    assert graph.bodies[1].startswith("✅ *SAFE*")
    check = app.state.check_store.get(next(iter(app.state.check_store._checks)))
    assert check.input_kind == "image"


def test_unsupported_message_type_gets_a_hint(wa):
    client, install, graph, _ = wa
    install(GENUINE, [])
    audio = message("x") | {"type": "audio", "audio": {"id": "A1"}}
    audio.pop("text")
    post(client, payload(audio))
    assert graph.bodies == [texts.t("en", "unsupported")]


# --- language ---


def test_language_switch_is_remembered_per_sender(wa):
    client, install, graph, _ = wa
    install(GENUINE, [cite_all("SAFE")])
    post(client, payload(message("हिंदी")))
    assert graph.bodies == [texts.t("hi", "switched")]
    post(client, payload(message(GENUINE.input.text)))  # English text, Hindi preference
    assert graph.bodies[1] == texts.t("hi", "checking")
    assert graph.bodies[2].startswith("✅ *सुरक्षित*")
    post(client, payload(message("English")))
    assert graph.bodies[-1] == texts.t("en", "switched")


@pytest.mark.parametrize(
    "text,lang",
    [("Pay your bill", None), ("మీ బిల్లు ₹941", "te"), ("आपका बिल ₹464", "hi"), ("SVS905403060 కు బిల్లు", "te")],
)  # fmt: skip
def test_language_from_script(text, lang):
    assert texts.detect_language(text) == lang


def test_every_evidence_code_has_a_label_in_every_language():
    for code in EvidenceCode:
        if code.value in texts.CODE_LABELS:
            assert all(texts.CODE_LABELS[code.value][lang] for lang in texts.LANGS)
    assert set(texts.CODE_LABELS) <= {c.value for c in EvidenceCode}


# --- ask_user over WhatsApp ---


def _question_flow(install):
    ask = turn(("ask_user", {"field": "consumer_number", "question": "What is the consumer number?"}))  # fmt: skip

    def fetch_with_answer(conv):
        answer = last_outputs(conv)[-1]["answer"]
        common = {"biller_id": "DEMO00000MAH01", "consumer_number": answer}
        return turn(("fetch_bill", common | {"claimed_amount": 1240.0}), ("get_bill_history", common | {"current_amount": 1240.0}))  # fmt: skip

    label = GENUINE.model_copy(deep=True)
    label.expected.extracted.amount = 1240.0
    return install(label, [ask, fetch_with_answer, cite_all("SAFE")], consumer_number=None)


QUESTION_TEXT = "Demo Power bill Rs 1,240 due 05-Nov-2026. Pay at demopower.example"


def test_question_is_sent_and_the_next_message_answers_it(wa):
    client, install, graph, timers = wa
    _question_flow(install)
    post(client, payload(message(QUESTION_TEXT)))
    assert graph.bodies[-1] == texts.question_message("What is the consumer number?", "en")
    assert [d for d, _ in timers] == [600]

    post(client, payload(message("DP-4410-882761")))
    assert graph.bodies[-1].startswith("✅ *SAFE*")
    assert not any("DP-4410-882761" in b for b in graph.bodies)
    timers[0][1]()  # the timer fires later: the check is already closed, nothing more is sent
    assert graph.bodies[-1].startswith("✅ *SAFE*")


def test_unanswered_question_expires_as_caution(wa):
    client, install, graph, timers = wa
    agent = _question_flow(install)
    post(client, payload(message(QUESTION_TEXT)))
    turns_before = len(agent.conversations)
    timers[0][1]()  # 10 minutes pass
    body = graph.bodies[-1]
    assert body.startswith("⚠️ *CAUTION*") and texts.t("en", "no_answer") in body
    assert len(agent.conversations) == turns_before  # closing costs no model call
    post(client, payload(message("DP-4410-882761")))  # a late answer is a new check, not an answer
    assert graph.bodies[-2] == texts.t("en", "checking")


def test_skip_closes_the_question_as_caution(wa):
    client, install, graph, _ = wa
    _question_flow(install)
    post(client, payload(message(QUESTION_TEXT)))
    post(client, payload(message("skip")))
    assert graph.bodies[-1].startswith("⚠️ *CAUTION*")
