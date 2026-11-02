"""Warning-card background: tools off, no user data, cached, and failure is not an error page."""

import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.sharecard import PROMPTS, TOOLS_OFF, CardBackgrounds

WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 data"
GOOD = {
    "status": "completed",
    "usage": {"input_tokens": 1000, "output_tokens": 1000},
    "output": [
        {"type": "reasoning"},
        {"type": "image_generation_call", "result": base64.b64encode(WEBP).decode()},
    ],
}


@pytest.fixture
def cards():
    names = ("settings", "card_backgrounds", "spend_meter")
    saved = {n: getattr(app.state, n, None) for n in names}
    app.state.settings = Settings(_env_file=None, meta_api_key="k", meta_api_base_url="https://m.example/v1")  # fmt: skip
    app.state.spend_meter = None
    seen = []

    def install(handler):
        def recording(request):
            seen.append(json.loads(request.content))
            return handler(request)

        http = httpx.Client(transport=httpx.MockTransport(recording))
        app.state.card_backgrounds = CardBackgrounds(app.state.settings, http_client=http)

    yield TestClient(app), install, seen
    for n, v in saved.items():
        setattr(app.state, n, v)


def get(client, verdict="SCAM"):
    return client.get("/api/v1/share-card/background", params={"verdict": verdict})


def test_every_model_tool_is_off_and_the_prompt_has_no_user_data(cards):
    client, install, seen = cards
    install(lambda r: httpx.Response(200, json=GOOD))
    r = get(client)
    assert r.status_code == 200 and r.content == WEBP and r.headers["content-type"] == "image/webp"
    assert seen[0]["metadata"] == TOOLS_OFF
    assert set(TOOLS_OFF.values()) == {"false"}
    assert seen[0]["model"] == "muse-image-1.0" and seen[0]["input"] == PROMPTS["SCAM"]
    assert "no text" in seen[0]["input"].lower()


def test_one_picture_per_verdict_is_generated_once(cards):
    client, install, seen = cards
    install(lambda r: httpx.Response(200, json=GOOD))
    get(client)
    get(client)
    assert len(seen) == 1
    get(client, "CAUTION")
    assert len(seen) == 2 and seen[1]["input"] == PROMPTS["CAUTION"]


def test_spend_is_counted_only_for_a_new_picture(cards):
    client, install, _ = cards
    install(lambda r: httpx.Response(200, json=GOOD))
    get(client)
    first = app.state.spend_meter.spent
    get(client)
    assert first > 0 and app.state.spend_meter.spent == first


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500), httpx.Response(200, json={"status": "completed", "output": []})],
    ids=["error", "no-picture"],
)
def test_failure_returns_503_and_is_not_cached(cards, response):
    client, install, seen = cards
    install(lambda r: response)
    assert get(client).status_code == 503
    install(lambda r: httpx.Response(200, json=GOOD))
    assert get(client).status_code == 200


def test_safe_has_no_card(cards):
    client, install, _ = cards
    install(lambda r: httpx.Response(200, json=GOOD))
    assert get(client, "SAFE").status_code == 422


def test_over_the_cap_no_new_picture_but_a_cached_one_is_fine(cards):
    client, install, seen = cards
    install(lambda r: httpx.Response(200, json=GOOD))
    get(client)
    app.state.spend_meter.add(1000)
    assert get(client).status_code == 200
    assert get(client, "CAUTION").status_code == 503 and len(seen) == 1
