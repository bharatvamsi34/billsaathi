"""Extraction and the Meta client, fully offline: a scripted fake model and a mock HTTP server."""

import json
import logging

import httpx
import pytest

from app.config import Settings
from app.extract import ExtractionFailed, extract
from app.extract.extract import SYSTEM_PROMPT, parse_json
from app.models.base import LLMError, LLMResponse, Message, Usage
from app.models.meta import MetaClient
from app.pii import mask_id, mask_phone

CONSUMER = "DP-4410-882761"


def good_output(**overrides) -> dict:
    fields = {
        "biller_name": "Demo Power Distribution Co. Ltd",
        "biller_category": "electricity",
        "consumer_number": CONSUMER,
        "amount": 1240.0,
        "due_date": "2026-11-05",
        "bill_date": "2026-10-12",
        "payment_destinations": [{"kind": "upi", "value": "demopower.bill@demobank"}],
        "languages": ["en", "hi"],
        "urgency_language": False,
    } | overrides
    return {k: {"value": v, "confidence": 0.95} for k, v in fields.items()}


class FakeClient:
    """Scripted model: returns the given replies in order (or raises them)."""

    provider = "fake"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[list[Message]] = []

    def respond(self, *, system, messages, model, effort="low", max_output_tokens=4096):
        assert system == SYSTEM_PROMPT and effort == "low"
        self.calls.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        usage = Usage(input_tokens=100, output_tokens=50, cost_usd=0.001)
        return LLMResponse(text=reply, model=model, provider="fake", latency_ms=10, usage=usage)


# --- extraction ---


def test_valid_first_try_from_image():
    client = FakeClient(json.dumps(good_output()))
    r = extract(client, image=b"\x89PNG fake", image_mime="image/png")
    assert r.attempts == 1 and r.output.amount.value == 1240.0
    assert r.output.to_fields().consumer_number == CONSUMER
    sent = client.calls[0][0]
    assert sent.image_data_url.startswith("data:image/png;base64,")


def test_visible_text_is_returned_separately_for_the_milestone_check():
    reply = good_output() | {"visible_text": "Pay at demopower.example/pay"}
    r = extract(FakeClient(json.dumps(reply)), image=b"img", image_mime="image/png")
    assert r.visible_text == "Pay at demopower.example/pay"
    assert "visible_text" not in r.output.model_dump()  # shared label format unchanged
    assert "visible_text" in SYSTEM_PROMPT


def test_text_input_and_fenced_json_with_prose():
    client = FakeClient("Sure!\n```json\n" + json.dumps(good_output()) + "\n```")
    r = extract(client, text="Dear consumer, your bill of Rs 1,240 ...")
    assert r.attempts == 1
    assert "Rs 1,240" in client.calls[0][0].text and client.calls[0][0].image_data_url is None


def test_invalid_output_is_retried_with_the_problem_fed_back():
    bad = good_output()
    bad["amount"] = {"value": "about twelve hundred", "confidence": 0.9}
    client = FakeClient("not json at all", json.dumps(bad), json.dumps(good_output()))
    r = extract(client, text="bill text")
    assert r.attempts == 3
    assert r.usage.input_tokens == 300 and r.usage.cost_usd == pytest.approx(0.003)
    feedback = client.calls[2][-1].text
    assert feedback.startswith("That reply was not valid: amount.value")
    assert client.calls[2][-2].role == "assistant"


def test_gives_up_after_three_invalid_replies():
    bad = json.dumps(good_output() | {"amount": {"value": 1240, "confidence": 7}})  # confidence > 1
    with pytest.raises(ExtractionFailed) as e:
        extract(FakeClient(bad, bad, bad), text="bill text")
    assert e.value.attempts == 3


def test_model_unavailable_becomes_extraction_failed():
    with pytest.raises(ExtractionFailed) as e:
        extract(FakeClient(LLMError("RateLimitError after 3 attempts")), text="bill text")
    assert "model unavailable" in str(e.value) and e.value.attempts == 1


def test_input_validation():
    with pytest.raises(ValueError):
        extract(FakeClient(), text="x", image=b"y", image_mime="image/png")
    with pytest.raises(ValueError):
        extract(FakeClient())
    with pytest.raises(ValueError):
        extract(FakeClient(), image=b"GIF89a", image_mime="image/gif")


def test_logs_mask_consumer_numbers(caplog):
    caplog.set_level(logging.INFO, logger="billsaathi.extract")
    extract(FakeClient(json.dumps(good_output())), text="bill text")
    logged = caplog.text
    assert "extraction ok" in logged and mask_id(CONSUMER) in logged
    assert CONSUMER not in logged and "4410882761" not in logged


def test_parse_json_and_masking_helpers():
    assert parse_json('noise {"a": {"b": 1}} trailing') == {"a": {"b": 1}}
    with pytest.raises(ValueError):
        parse_json("no braces here")
    assert mask_id("DP-4410-882761") == "**********2761"
    assert mask_phone("+91 90000 00000") == "91********00"


# --- Meta client against a mock HTTP server (real openai SDK parsing, no network) ---


def response_json(text: str, status: str = "completed") -> dict:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 0,
        "model": "muse-spark-1.3",
        "status": status,
        "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 2000,
            "output_tokens": 800,
            "total_tokens": 2800,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 500},
        },
    }


def meta_client(handler) -> MetaClient:
    settings = Settings(
        _env_file=None,
        meta_api_key="dummy-not-a-real-key",
        meta_api_base_url="https://meta.test/v1",
    )
    return MetaClient(
        settings, backoff_s=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_meta_client_request_shape_and_usage():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=response_json('{"ok": true}'))

    msgs = [Message(role="user", text="read this", image_data_url="data:image/png;base64,AAAA")]
    r = meta_client(handler).respond(system="sys", messages=msgs, model="muse-spark-1.3")
    assert seen["url"] == "https://meta.test/v1/responses"
    assert seen["auth"] == "Bearer dummy-not-a-real-key"
    body = seen["body"]
    assert body["model"] == "muse-spark-1.3" and body["reasoning"] == {"effort": "low"}
    assert body["max_output_tokens"] == 4096
    assert body["input"][0] == {"role": "system", "content": "sys"}
    assert body["input"][1]["content"][1] == {
        "type": "input_image",
        "image_url": "data:image/png;base64,AAAA",
    }
    assert r.text == '{"ok": true}'
    assert (r.usage.input_tokens, r.usage.output_tokens, r.usage.reasoning_tokens) == (
        2000,
        800,
        500,
    )
    assert r.usage.cost_usd == pytest.approx((2000 * 1.25 + 800 * 4.25) / 1e6)


def test_meta_client_retries_rate_limits_and_server_errors():
    replies = [httpx.Response(429, json={"error": "slow down"}), httpx.Response(503, json={}), None]

    def handler(request):
        reply = replies.pop(0)
        return reply or httpx.Response(200, json=response_json("{}"))

    r = meta_client(handler).respond(
        system="s", messages=[Message(role="user", text="t")], model="muse-spark-1.3"
    )
    assert r.transport_attempts == 3


def test_meta_client_errors():
    def bad_request(request):
        return httpx.Response(400, json={"error": "bad"})

    calls = []

    def always_429(request):
        calls.append(1)
        return httpx.Response(429, json={})

    msgs = [Message(role="user", text="t")]
    with pytest.raises(LLMError, match="HTTP 400"):
        meta_client(bad_request).respond(system="s", messages=msgs, model="muse-spark-1.3")
    with pytest.raises(LLMError, match="RateLimitError after 3"):
        meta_client(always_429).respond(system="s", messages=msgs, model="muse-spark-1.3")
    assert len(calls) == 3
    with pytest.raises(LLMError, match="max_output_tokens"):
        meta_client(lambda r: httpx.Response(200, json=response_json("{", "incomplete"))).respond(
            system="s", messages=msgs, model="muse-spark-1.3"
        )
    with pytest.raises(LLMError, match="Contributor"):
        meta_client(bad_request).respond(
            system="s", messages=msgs, model="muse-spark-1.3-contributor"
        )
