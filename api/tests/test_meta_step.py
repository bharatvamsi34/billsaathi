"""MetaClient.step: Responses-format function calling, offline (real SDK, mock HTTP server)."""

import json

import httpx

from app.agent.loop import TOOL_SPECS
from app.config import Settings
from app.models.base import AssistantTurn, ToolOutput, ToolOutputs, UserText
from app.models.meta import MetaClient


def response_with(items: list[dict], text_items: bool = False) -> dict:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 0,
        "model": "muse-spark-1.3",
        "status": "completed",
        "output": items,
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 3000,
            "output_tokens": 400,
            "total_tokens": 3400,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 300},
        },
    }


REASONING = {"type": "reasoning", "id": "rs_1", "summary": []}
CALL_A = {
    "type": "function_call",
    "id": "fc_1",
    "call_id": "call_a",
    "name": "lookup_biller",
    "arguments": '{"name": "Demo Power", "category": "electricity"}',
    "status": "completed",
}
CALL_B = {
    "type": "function_call",
    "id": "fc_2",
    "call_id": "call_b",
    "name": "check_payment_destination",
    "arguments": '{"kind": "url", "value": "demopower.example"}',
    "status": "completed",
}


def client_with(replies: list[dict], seen: list[dict]) -> MetaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=replies.pop(0))

    settings = Settings(
        _env_file=None,
        meta_api_key="dummy-not-a-real-key",
        meta_api_base_url="https://meta.test/v1",
    )
    return MetaClient(
        settings, backoff_s=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_step_returns_parallel_tool_calls_in_order():
    seen: list[dict] = []
    client = client_with([response_with([REASONING, CALL_A, CALL_B])], seen)
    t = client.step(
        system="sys",
        conversation=[UserText(text="check this")],
        tools=TOOL_SPECS,
        model="muse-spark-1.3",
    )
    assert [(c.call_id, c.name) for c in t.tool_calls] == [
        ("call_a", "lookup_biller"),
        ("call_b", "check_payment_destination"),
    ]
    assert json.loads(t.tool_calls[0].arguments)["name"] == "Demo Power"
    assert (t.usage.input_tokens, t.usage.output_tokens) == (3000, 400)
    body = seen[0]
    assert body["reasoning"] == {"effort": "low"} and body["max_output_tokens"] == 4096
    assert {tool["name"] for tool in body["tools"]} >= {
        "lookup_biller",
        "submit_verdict",
        "ask_user",
    }
    assert all(tool["type"] == "function" for tool in body["tools"])
    assert body["input"][1] == {
        "role": "user",
        "content": [{"type": "input_text", "text": "check this"}],
    }


def test_step_replays_model_items_and_sends_tool_outputs():
    seen: list[dict] = []
    final = {
        "type": "message",
        "id": "msg_1",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": "done", "annotations": []}],
    }
    client = client_with([response_with([REASONING, CALL_A, CALL_B]), response_with([final])], seen)
    first = client.step(
        system="s", conversation=[UserText(text="go")], tools=TOOL_SPECS, model="muse-spark-1.3"
    )
    conversation = [
        UserText(text="go"),
        AssistantTurn(turn=first),
        ToolOutputs(
            outputs=[
                ToolOutput(call_id="call_a", output='{"ok": true}'),
                ToolOutput(call_id="call_b", output='{"ok": true}'),
            ]
        ),
    ]
    second = client.step(
        system="s", conversation=conversation, tools=TOOL_SPECS, model="muse-spark-1.3"
    )
    assert second.text == "done" and second.tool_calls == []
    sent = seen[1]["input"]
    assert [i.get("type") for i in sent[2:]] == [
        "reasoning",
        "function_call",
        "function_call",
        "function_call_output",
        "function_call_output",
    ]
    assert sent[5] == {
        "type": "function_call_output",
        "call_id": "call_a",
        "output": '{"ok": true}',
    }
    assert all(None not in i.values() for i in sent[2:5])  # replayed items carry no null fields
