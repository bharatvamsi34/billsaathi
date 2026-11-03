"""When the evidence floor is already SCAM the explanation starts early, from the code's findings
only, and is never shown before the verdict. Every other verdict keeps the normal path."""

from dataset_utils import LABELS
from fakes import ScriptedModel
from test_api_checks import FakeExtractor, cite_all

from app import pipeline
from app.api.store import CheckState, SpendMeter
from app.models.base import LLMResponse, Usage

BY_ID = {lbl.id: lbl for lbl in LABELS}


class FakeExplainer:
    def __init__(self):
        self.calls = []

    def respond(self, *, system, messages, model, effort, max_output_tokens, **kw):
        self.calls.append(messages[0].text)
        return LLMResponse(text="This is a scam. Do not pay.", usage=Usage(cost_usd=0.001), model=model, provider="fake", latency_ms=1.0)  # fmt: skip


def _run(label, steps):
    explainer = FakeExplainer()
    agent = ScriptedModel(steps)
    clients = pipeline.Clients(
        extract=FakeExtractor(label), agent=agent, judge=agent, explain=explainer
    )
    state = CheckState(check_id="c1", language="en", input_kind="text")
    pipeline.run_check(
        state, pipeline.CheckInput(language="en", text=label.input.text), clients, SpendMeter(5.0)
    )
    return state, explainer


def test_scam_floor_explains_from_the_findings_alone():
    state, explainer = _run(BY_ID["scam_en_known_vpa"], [cite_all("SCAM")])
    assert state.early_explanation is not None
    assert len(explainer.calls) == 1  # one explanation, not two
    assert "Finding" not in explainer.calls[0]  # never the agent's unjudged reasons
    assert "known-scam list" in explainer.calls[0]
    types = [e["type"] for e in state.events]
    assert types.index("verdict") < types.index("explanation")  # never shown before the verdict
    assert next(e for e in state.events if e["type"] == "explanation")["text"].startswith(
        "This is a scam"
    )


def test_other_verdicts_use_the_normal_path():
    state, explainer = _run(BY_ID["reminder_en_demo"], [cite_all("SAFE")])
    assert state.early_explanation is None
    assert len(explainer.calls) == 1
    assert "Finding" in explainer.calls[0]  # the judged reasons
