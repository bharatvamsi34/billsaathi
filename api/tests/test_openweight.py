"""Privacy Mode: the open-weight client, failover, and no Meta call anywhere on that path."""

import json

import httpx
import pytest
from test_api_checks import GENUINE, api, cite_all, events_of  # noqa: F401

from app import pipeline
from app.config import Settings
from app.main import app
from app.models.base import (  # fmt: skip
    AssistantTurn,
    LLMError,
    Message,
    ModelTurn,
    ToolCall,
    ToolOutput,
    ToolOutputs,
    UserText,
)
from app.models.openweight import FailoverClient, OpenWeightClient, privacy_client


def reply(content=None, tool_calls=None, finish="stop"):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "x", "object": "chat.completion", "created": 1, "model": "m",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100},
    }  # fmt: skip


def client(handler, provider="baseten", model="meta-models/muse-spark-open-1026"):
    return OpenWeightClient(
        provider, "key", "https://open.example/v1", model,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_attempts=2, backoff_s=0,
    )  # fmt: skip


def recording(seen, body):
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=body)

    return handler


def test_respond_sends_images_as_data_urls_and_strips_reasoning():
    seen = []
    out = client(recording(seen, reply("<think>hmm 1930</think> The answer"))).respond(
        system="S", messages=[Message(role="user", text="T", image_data_url="data:image/png;base64,AA")]
    )  # fmt: skip
    assert out.text == "The answer" and out.provider == "baseten"
    assert seen[0]["model"] == "meta-models/muse-spark-open-1026"
    assert seen[0]["messages"][0] == {"role": "system", "content": "S"}
    assert seen[0]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png")
    assert out.usage.cost_usd > 0  # estimated, so Privacy Mode still counts towards the daily cap


def test_step_converts_tools_and_the_whole_conversation():
    seen = []
    call = {"id": "c9", "type": "function", "function": {"name": "submit_verdict", "arguments": "{}"}}  # fmt: skip
    spec = {"type": "function", "name": "submit_verdict", "description": "d", "parameters": {}}
    conversation = [
        UserText(text="brief"),
        AssistantTurn(turn=ModelTurn(tool_calls=[ToolCall(call_id="c1", name="fetch_bill", arguments="{}")])),
        ToolOutputs(outputs=[ToolOutput(call_id="c1", output='{"ok":true}')]),
    ]  # fmt: skip
    turn = client(recording(seen, reply(None, [call], "tool_calls"))).step(
        system="S", conversation=conversation, tools=[spec]
    )
    assert turn.tool_calls[0].name == "submit_verdict" and turn.tool_calls[0].call_id == "c9"
    sent = seen[0]
    assert sent["tools"][0] == {"type": "function", "function": {"name": "submit_verdict", "description": "d", "parameters": {}}}  # fmt: skip
    roles = [m["role"] for m in sent["messages"]]
    assert roles == ["system", "user", "assistant", "tool"]
    assert sent["messages"][2]["tool_calls"][0]["function"]["name"] == "fetch_bill"
    assert sent["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": '{"ok":true}'}


def test_first_turn_is_free_and_the_retry_must_submit_a_verdict():
    seen = []
    call = {"id": "c9", "type": "function", "function": {"name": "submit_verdict", "arguments": "{}"}}  # fmt: skip
    spec = {"type": "function", "name": "submit_verdict", "description": "d", "parameters": {}}
    ow = client(recording(seen, reply(None, [call], "tool_calls")))
    ow.step(system="S", conversation=[UserText(text="brief")], tools=[spec])
    assert "tool_choice" not in seen[0]
    # A turn that did call a tool is not a retry.
    ow.step(
        system="S",
        conversation=[
            UserText(text="brief"),
            AssistantTurn(turn=ModelTurn(tool_calls=[ToolCall(call_id="c1", name="fetch_bill", arguments="{}")])),
            ToolOutputs(outputs=[ToolOutput(call_id="c1", output="{}")]),
        ],
        tools=[spec],
    )  # fmt: skip
    assert "tool_choice" not in seen[1]
    # The model answered in plain text and was nudged: this is the one retry.
    ow.step(
        system="S",
        conversation=[
            UserText(text="brief"),
            AssistantTurn(turn=ModelTurn(text="This looks like a scam.")),
            UserText(text="Call submit_verdict now."),
        ],
        tools=[spec],
    )
    assert seen[2]["tool_choice"] == {"type": "function", "function": {"name": "submit_verdict"}}


def test_cut_off_reply_is_an_error_not_an_answer():
    with pytest.raises(LLMError):
        client(lambda r: httpx.Response(200, json=reply("half", finish="length"))).respond(
            system="S", messages=[Message(role="user", text="T")]
        )


def test_contributor_models_are_refused():
    with pytest.raises(LLMError):
        client(lambda r: httpx.Response(200), model="muse-spark-open-contributor")


def test_transcribe_sends_input_audio_with_the_language():
    seen = []
    out = client(recording(seen, reply("మీ బిల్లు"))).transcribe_audio(b"RIFF", "te")
    content = seen[0]["messages"][0]["content"]
    assert "Telugu" in content[0]["text"] and content[1]["input_audio"]["format"] == "wav"
    assert out.text == "మీ బిల్లు"


# --- failover ---


def test_failover_uses_the_second_provider_when_the_first_fails():
    down = client(lambda r: httpx.Response(500))
    seen = []
    up = client(recording(seen, reply("ok")), provider="fireworks", model="accounts/fireworks/models/muse-spark-open")  # fmt: skip
    out = FailoverClient(down, up).respond(system="S", messages=[Message(role="user", text="T")])
    assert out.provider == "fireworks" and seen[0]["model"].startswith("accounts/fireworks")


def test_no_fallback_means_the_failure_is_seen():
    with pytest.raises(LLMError):
        FailoverClient(client(lambda r: httpx.Response(500)), None).respond(
            system="S", messages=[Message(role="user", text="T")]
        )


def test_providers_come_from_config():
    with pytest.raises(LLMError):
        privacy_client(Settings(_env_file=None))
    only_fireworks = privacy_client(Settings(_env_file=None, fireworks_api_key="k"))
    assert only_fireworks.primary.provider == "fireworks" and only_fireworks.fallback is None
    both = privacy_client(Settings(_env_file=None, baseten_api_key="a", fireworks_api_key="b"))
    assert both.primary.provider == "baseten" and both.fallback.provider == "fireworks"
    assert both.fallback.model == "accounts/fireworks/models/muse-spark-open"


# --- the checks API ---


class Boom:
    """Stands in for every Meta client: any call fails the test."""

    def __getattr__(self, name):
        raise AssertionError(f"Meta client used in Privacy Mode: {name}")


def post_private(client_, text):
    return client_.post("/api/v1/checks", data={"text": text, "language": "en", "privacy": "true"})


def test_privacy_mode_never_touches_the_normal_clients(api):  # noqa: F811
    client_, install = api
    open_agent = install(GENUINE, [cite_all("SAFE")])
    private = app.state.clients
    private.model = "muse-spark-open"
    private.privacy = True
    app.state.privacy_clients = private
    boom = Boom()
    app.state.clients = pipeline.Clients(extract=boom, agent=boom, judge=boom)
    try:
        r = post_private(client_, GENUINE.input.text)
        assert r.status_code == 202
        events = events_of(client_, r.json()["check_id"])
    finally:
        app.state.privacy_clients = None
    first = events[0]
    assert first["privacy"] is True and first["model"] == "muse-spark-open"
    assert next(e for e in events if e["type"] == "verdict")["verdict"] == "SAFE"
    assert open_agent.conversations  # the open-weight agent did the work


def test_normal_mode_says_so(api):  # noqa: F811
    client_, install = api
    install(GENUINE, [cite_all("SAFE")])
    r = client_.post("/api/v1/checks", data={"text": GENUINE.input.text, "language": "en"})
    assert events_of(client_, r.json()["check_id"])[0]["privacy"] is False


def test_privacy_mode_without_a_provider_is_refused_not_downgraded(api):  # noqa: F811
    client_, install = api
    install(GENUINE, [])
    app.state.privacy_clients = None
    r = post_private(client_, GENUINE.input.text)
    assert r.status_code == 503 and r.json()["error"] == "privacy_unavailable"
