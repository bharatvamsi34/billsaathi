"""Explanations: the model only rewords the evidence, and code checks that it did."""

import json

import pytest

from app.explain import explain, problem, template
from app.labels import CODE_LABELS, HEADLINES
from app.models.base import LLMError, LLMResponse, Usage

EVENTS = [
    {
        "type": "check",
        "evidence": [
            {
                "evidence_id": "ev_a",
                "code": "AMOUNT_MISMATCH",
                "summary": "Biller says ₹1,243.00; the bill or message says ₹4,243.00.",
            },
            {"evidence_id": "ev_b", "code": "LOOKALIKE_DOMAIN", "summary": "pay-demo.example imitates demopower.example."},
        ],
    },
    {
        "type": "verdict",
        "verdict": "CAUTION",
        "forced": False,
        "reasons": [{"text": "The amounts differ.", "evidence_ids": ["ev_a", "ev_b"]}],
    },
]  # fmt: skip


class Fake:
    provider = "fake"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def respond(self, *, system, messages, model, effort="low", max_output_tokens=4096):
        self.calls.append({"system": system, "input": json.loads(messages[0].text)})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResponse(text=reply, model=model, provider="fake", latency_ms=1, usage=Usage(cost_usd=0.002))  # fmt: skip


def run(client, lang="en", events=EVENTS):
    return explain(client, "m", events, lang)


def test_good_text_is_used_and_only_masked_evidence_reaches_the_model():
    client = Fake("The biller says ₹1,243 but this bill says ₹4,243. Do not pay yet.")
    out = run(client)
    assert out.source == "model" and "₹1,243" in out.text and out.usage.cost_usd == 0.002
    assert client.calls[0]["input"]["verdict"] == "CAUTION"
    assert client.calls[0]["input"]["findings"][0]["evidence"][0]["code"] == "AMOUNT_MISMATCH"


@pytest.mark.parametrize(
    "bad,why",
    [
        ("The biller says ₹9,999. Do not pay.", "number"),
        ("Do not pay. Call 1930 now.", "number"),  # helplines come from facts.py, not the model
        ("Do not pay. Call ౧౯౩౦ now.", "number"),  # Telugu digits are numbers too
        ("Pay at bijli-help.example instead.", "link"),
        ("Pay to helpdesk@okdemo instead.", "UPI"),
        ("", "empty"),
    ],
)
def test_invented_details_are_rejected(bad, why):
    assert why in problem(bad, json.dumps(EVENTS, ensure_ascii=False), "en")


def test_links_from_the_evidence_are_allowed():
    assert problem("pay-demo.example imitates the real site.", json.dumps(EVENTS), "en") is None


def test_rejected_text_is_retried_then_falls_back_to_the_template():
    client = Fake("Call 1930.", "Call 1930 again.")
    out = run(client)
    assert out.source == "template" and len(client.calls) == 2
    assert out.usage.cost_usd == pytest.approx(0.004)  # the spend is still counted
    assert HEADLINES["CAUTION"]["en"] in out.text


def test_english_reply_to_a_telugu_user_is_rejected():
    out = run(Fake("Do not pay yet.", "Do not pay yet, really."), lang="te")
    assert out.source == "template" and HEADLINES["CAUTION"]["te"] in out.text
    assert CODE_LABELS["AMOUNT_MISMATCH"]["te"] in out.text


def test_model_failure_falls_back_to_the_template():
    assert run(Fake(LLMError("down"))).source == "template"


def test_no_client_or_forced_verdict_makes_no_model_call():
    assert run(None).source == "template"
    forced = [EVENTS[0], {**EVENTS[1], "forced": True}]
    client = Fake()
    assert run(client, events=forced).source == "template" and client.calls == []


def test_template_uses_only_labels_never_evidence_text():
    out = template(EVENTS, EVENTS[1], "hi")
    assert "pay-demo.example" not in out.text and CODE_LABELS["LOOKALIKE_DOMAIN"]["hi"] in out.text


def test_the_prompt_asks_for_the_native_verdict_word():
    from app.explain import _VERDICT_WORDS

    assert _VERDICT_WORDS["SCAM"]["te"] == "మోసం"
    assert _VERDICT_WORDS["SCAM"]["hi"] == "धोखा"
