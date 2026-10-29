"""A scripted fake model: the agent loop and every safety rule tested with zero API calls."""

import itertools
import json
from collections.abc import Callable

from app.models.base import (
    LLMResponse,
    ModelTurn,
    ToolCall,
    ToolOutputs,
    Usage,
    UserText,
)

_ids = itertools.count(1)
TURN_USAGE = Usage(input_tokens=1000, output_tokens=200, cost_usd=0.002)

Step = ModelTurn | Exception | Callable[[list], ModelTurn]


def turn(*calls: tuple[str, dict | str], text: str = "") -> ModelTurn:
    """A model turn with these tool calls (args as a dict, or raw text to test bad JSON)."""
    return ModelTurn(
        text=text,
        tool_calls=[
            ToolCall(
                call_id=f"call_{next(_ids)}",
                name=name,
                arguments=args if isinstance(args, str) else json.dumps(args, default=str),
            )
            for name, args in calls
        ],
        usage=TURN_USAGE,
    )


def submit(verdict: str, *reasons: tuple[str, list[str]], facts=()) -> ModelTurn:
    return turn(
        (
            "submit_verdict",
            {
                "verdict": verdict,
                "reasons": [{"text": t, "evidence_ids": ids} for t, ids in reasons],
                "facts": list(facts),
            },
        )
    )


def tool_outputs(conversation: list) -> list[dict]:
    """Every tool output the model has seen so far, parsed: the mandatory results in the
    first message ("-> {json}" lines) and the outputs of its own tool calls."""
    seen = []
    for item in conversation:
        if isinstance(item, UserText):
            seen += [
                json.loads(line[3:]) for line in item.text.splitlines() if line.startswith("-> ")
            ]
        elif isinstance(item, ToolOutputs):
            seen += [json.loads(o.output) for o in item.outputs]
    return seen


def evidence(conversation: list, code: str | None = None) -> list[str]:
    """evidence_ids seen so far (optionally only one code)."""
    return [
        e["evidence_id"]
        for out in tool_outputs(conversation)
        for e in out.get("evidence", [])
        if code is None or e["code"] == code
    ]


def last_outputs(conversation: list) -> list[dict]:
    for item in reversed(conversation):
        if isinstance(item, ToolOutputs):
            return [json.loads(o.output) for o in item.outputs]
    return []


class ScriptedModel:
    provider = "scripted"

    def __init__(
        self, steps: list[Step], judge: list[str | Exception | Callable[[dict], str]] | None = None
    ):
        self.steps = list(steps)
        self.judge_replies = list(judge or [])
        self.judge_inputs: list[dict] = []
        self.conversations: list[list] = []

    def step(
        self, *, system, conversation, tools, model, effort="low", max_output_tokens=4096
    ) -> ModelTurn:
        self.conversations.append(list(conversation))
        self.tools = tools
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step(conversation) if callable(step) else step

    def respond(
        self, *, system, messages, model, effort="low", max_output_tokens=4096
    ) -> LLMResponse:
        payload = json.loads(messages[0].text)
        self.judge_inputs.append(payload)
        reply = self.judge_replies.pop(0) if self.judge_replies else None
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            reply = reply(payload)
        if reply is None:  # default: every reason supported
            reply = json.dumps(
                {
                    "reasons": [
                        {"index": r["index"], "supported": True, "why": "ok"}
                        for r in payload["reasons"]
                    ]
                }
            )
        return LLMResponse(
            text=reply, model=model, provider=self.provider, latency_ms=0, usage=TURN_USAGE
        )
