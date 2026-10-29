"""The agent loop and every safety rule, driven by a scripted model (no API calls)."""

import json

import pytest
from dataset_utils import LABELS, first_wave, second_wave
from fakes import ScriptedModel, evidence, last_outputs, submit, tool_outputs, turn

from app.agent.checks import CheckContext, destinations_checked
from app.agent.evidence import EvidenceRecord
from app.agent.loop import AgentConfig, resume, start
from app.agent.protocol import AgentInput, SubmitVerdictArgs
from app.agent.tools import TOOLS
from app.models.base import LLMError
from app.schemas import BillFields, EvidenceCode, PaymentDestination

BY_ID = {lbl.id: lbl for lbl in LABELS}
GENUINE = BY_ID["reminder_en_demo"]  # SAFE: verified biller, matching amount, official link + UPI
TAMPERED = BY_ID["bill_tampered_demo"]  # CAUTION: amount mismatch + spike
SCAM = BY_ID["scam_en_disconnect_lookalike"]  # SCAM: personal number + lookalike link


def agent_input(label, **field_overrides) -> AgentInput:
    fields = label.expected.extracted.model_copy(update=field_overrides)
    return AgentInput.from_fields(fields, raw_text=label.input.text)


def wave1(label):
    return turn(*first_wave(label))


def wave2(label):
    def step(conv):
        biller_id = next(
            (
                o["data"]["biller_id"]
                for o in tool_outputs(conv)
                if o.get("data", {}).get("matched")
            ),
            None,
        )
        return turn(*second_wave(label, biller_id))

    return step


def cite_all(verdict: str, facts=()):
    """Submit `verdict`, citing every evidence item seen so far (one reason each)."""

    def step(conv):
        ids = evidence(conv)
        return submit(
            verdict,
            *[(f"Finding {i + 1} from the checks.", [eid]) for i, eid in enumerate(ids)],
            facts=facts,
        )

    return step


def run(label, steps, judge=None, **kw):
    model = ScriptedModel(steps, judge)
    return start(model, kw.pop("agent_input", None) or agent_input(label), **kw), model


def refusal_rules(session):
    return [e.payload["rule"] for e in session.record.entries if e.kind == "refusal"]


# --- happy path and speed ---


def test_genuine_safe_in_three_turns_with_parallel_calls():
    session, model = run(GENUINE, [wave1(GENUINE), wave2(GENUINE), cite_all("SAFE")])
    assert session.status == "done" and session.final.verdict == "SAFE" and not session.final.forced
    m = session.metrics
    assert (m.model_turns, m.judge_calls, m.tool_calls, m.refusals) == (3, 1, 6, 0)
    assert m.cost_usd == pytest.approx(0.002 * 4) and m.input_tokens == 4000
    assert len(model.judge_inputs) == 1


def test_mandatory_checks_cannot_be_skipped():
    """An agent that calls no tools at all still gets every fixed-point check, before its first turn."""
    session, model = run(GENUINE, [cite_all("SAFE")])
    assert session.final.verdict == "SAFE" and not session.final.forced
    m = session.metrics
    assert (m.model_turns, m.mandatory_calls, m.tool_calls, m.judge_calls) == (1, 6, 0, 1)
    mandatory = session.record.tool_results_from("mandatory")
    f = GENUINE.expected.extracted
    assert [r.tool for r in mandatory] == [
        "lookup_biller",
        *["check_payment_destination"] * len(f.payment_destinations),
        "match_scam_patterns",
        "fetch_bill",
        "get_bill_history",
    ]
    assert {r.args["value"] for r in mandatory if r.tool == "check_payment_destination"} == {
        d.value for d in f.payment_destinations
    }
    # all recorded before anything the model did, and all shown to it in its first turn
    entries = session.record.entries
    last_mandatory = max(e.seq for e in entries if e.payload.get("origin") == "mandatory")
    first_model_effect = min(e.seq for e in entries if e.kind in ("judge", "refusal", "verdict"))
    assert last_mandatory < first_model_effect
    briefing = model.conversations[0][0].text
    assert all(e.evidence_id in briefing for r in mandatory for e in r.evidence)


def test_mandatory_checks_without_a_known_biller_skip_bill_fetch():
    unknown = BY_ID["edge_en_unknown_biller"]
    session, _ = run(unknown, [cite_all("CAUTION")])
    assert [r.tool for r in session.record.tool_results_from("mandatory")] == [
        "lookup_biller",
        "match_scam_patterns",
    ]
    assert session.final.verdict == "CAUTION"


def test_parallel_calls_are_recorded_in_the_requested_order():
    calls = first_wave(SCAM)
    session, _ = run(SCAM, [turn(*calls), cite_all("SCAM")])
    recorded = session.record.tool_results_from("agent")
    assert [(r.tool, r.args.get("value") or r.args.get("name") or "text") for r in recorded] == [
        (name, args.get("value") or args.get("name") or "text") for name, args in calls
    ]
    seqs = [e.seq for e in session.record.entries]
    assert seqs == sorted(seqs) == list(range(len(seqs)))
    assert session.final.verdict == "SCAM"


# --- submit_verdict checks ---


def test_invented_evidence_id_is_refused_then_fixed():
    steps = [
        wave1(GENUINE),
        wave2(GENUINE),
        submit("SAFE", ("Looks fine.", ["ev_made_up_123"])),
        cite_all("SAFE"),
    ]
    session, _ = run(GENUINE, steps)
    assert refusal_rules(session) == ["citations_exist"]
    assert session.final.verdict == "SAFE" and session.submits == 1


def test_safe_after_amount_mismatch_is_refused():
    session, _ = run(
        TAMPERED, [wave1(TAMPERED), wave2(TAMPERED), cite_all("SAFE"), cite_all("CAUTION")]
    )
    assert refusal_rules(session) == ["hard_rule_floor"]
    assert session.final.verdict == "CAUTION"


def test_destinations_checked_is_still_enforced_as_a_safety_net():
    """Mandatory checks cover every destination, but submit_verdict still verifies it."""
    record = EvidenceRecord("r")
    lookup = TOOLS["lookup_biller"](name="Demo Power", category="electricity")
    record.add_tool_result(lookup)
    args = SubmitVerdictArgs(
        verdict="CAUTION",
        reasons=[{"text": "Biller found.", "evidence_ids": [lookup.evidence[0].evidence_id]}],
    )
    ctx = CheckContext(
        args=args,
        record=record,
        destinations=[PaymentDestination(kind="url", value="demopower.example")],
        low_confidence=[],
    )
    refusal = destinations_checked(ctx)
    assert refusal.rule == "destinations_checked" and "demopower.example" in refusal.message


def test_caution_when_evidence_says_scam_is_refused():
    session, _ = run(SCAM, [wave1(SCAM), cite_all("CAUTION"), cite_all("SCAM")])
    assert refusal_rules(session) == ["hard_rule_floor"]
    assert session.final.verdict == "SCAM"


@pytest.mark.parametrize(
    "facts,text",
    [
        (["made_up_fact"], "Lookalike link found."),
        ([], "Call 1930 to report this."),
        ([], "Call our officer on 9876543210 instead."),
    ],
)
def test_unverified_facts_and_typed_numbers_are_refused(facts, text):
    def bad(conv):
        return submit("SCAM", (text, evidence(conv, "LOOKALIKE_DOMAIN")), facts=facts)

    session, _ = run(SCAM, [wave1(SCAM), bad, cite_all("SCAM", facts=["cybercrime_helpline"])])
    assert refusal_rules(session) == ["facts_verified"]
    assert session.final.facts == ["cybercrime_helpline"]


def test_three_refusals_force_caution_never_safe():
    bad = submit("SAFE", ("Fine.", ["ev_nope"]))
    session, _ = run(TAMPERED, [wave1(TAMPERED), wave2(TAMPERED), bad, bad, bad])
    assert session.final.forced and session.final.verdict == "CAUTION"
    assert "refused 3 times" in session.final.forced_reason
    assert refusal_rules(session) == ["citations_exist"] * 3


def test_forced_ending_keeps_a_scam_floor():
    bad = submit("SAFE", ("Fine.", ["ev_nope"]))
    session, _ = run(SCAM, [wave1(SCAM), bad, bad, bad])
    assert session.final.forced and session.final.verdict == "SCAM"
    assert session.final.reasons[0].evidence_ids  # cites the evidence behind the floor


def test_failed_tool_makes_safe_impossible():
    broken = turn(("fetch_bill", {"biller_id": "NOPE", "consumer_number": "x"}))
    session, _ = run(
        GENUINE, [wave1(GENUINE), wave2(GENUINE), broken, cite_all("SAFE"), cite_all("CAUTION")]
    )
    assert refusal_rules(session) == ["hard_rule_floor"]
    assert session.final.verdict == "CAUTION"


def test_invalid_submit_arguments_count_as_a_refusal():
    session, _ = run(
        GENUINE,
        [wave1(GENUINE), turn(("submit_verdict", "{not json")), wave2(GENUINE), cite_all("SAFE")],
    )
    assert refusal_rules(session) == ["invalid_arguments"] and session.final.verdict == "SAFE"


# --- claims check (LLM judge) ---


def test_judge_refusal_is_fed_back_then_fixed():
    def first_reason_unsupported(payload):
        return json.dumps(
            {
                "reasons": [
                    {
                        "index": r["index"],
                        "supported": r["index"] != 0,
                        "why": "the evidence is about the biller",
                    }
                    for r in payload["reasons"]
                ]
            }
        )

    steps = [wave1(GENUINE), wave2(GENUINE), cite_all("SAFE"), cite_all("SAFE")]
    session, model = run(GENUINE, steps, judge=[first_reason_unsupported])
    assert refusal_rules(session) == ["claims_check"]
    feedback = last_outputs(model.conversations[-1])[0]
    assert feedback["accepted"] is False and feedback["attempts_left"] == 2
    assert "Reason 1: the evidence is about the biller" in feedback["message"]
    assert session.final.verdict == "SAFE" and session.metrics.judge_calls == 2


@pytest.mark.parametrize(
    "bad_reply", ["not json", json.dumps({"reasons": []}), LLMError("timeout")]
)
def test_judge_fails_closed(bad_reply):
    session, _ = run(
        GENUINE,
        [wave1(GENUINE), wave2(GENUINE), cite_all("SAFE"), cite_all("SAFE")],
        judge=[bad_reply],
    )
    assert refusal_rules(session) == ["claims_check_unavailable"]
    assert session.final.verdict == "SAFE"  # accepted on the second try, when the judge works


def test_judge_runs_only_after_deterministic_checks_pass():
    bad = submit("SAFE", ("Fine.", ["ev_nope"]))
    session, model = run(TAMPERED, [wave1(TAMPERED), wave2(TAMPERED), bad, cite_all("CAUTION")])
    assert refusal_rules(session) == ["citations_exist"]
    assert (
        session.metrics.judge_calls == 1 and len(model.judge_inputs) == 1
    )  # only for the accepted submit


def test_judge_sees_only_reasons_and_cited_evidence():
    session, model = run(SCAM, [wave1(SCAM), cite_all("SCAM")])
    payload = model.judge_inputs[0]
    assert set(payload) == {"reasons"}
    first = payload["reasons"][0]
    assert set(first) == {"index", "text", "evidence"}
    assert set(first["evidence"][0]) == {"evidence_id", "code", "summary", "detail"}


# --- ask_user ---


def test_ask_user_pauses_and_resumes_with_the_new_value():
    no_consumer = agent_input(GENUINE, consumer_number=None)
    ask = turn(
        (
            "ask_user",
            {"field": "consumer_number", "question": "What is the consumer number on the bill?"},
        )
    )
    consumer = GENUINE.expected.extracted.consumer_number

    def checks_with_answer(conv):
        answer = last_outputs(conv)[-1]["answer"]
        return turn(*second_wave(GENUINE.model_copy(update={"expected": GENUINE.expected.model_copy(update={"extracted": GENUINE.expected.extracted.model_copy(update={"consumer_number": answer})})}), "DEMO00000MAH01"))  # fmt: skip

    session, _ = run(
        GENUINE,
        [wave1(GENUINE), ask, checks_with_answer, cite_all("SAFE")],
        agent_input=no_consumer,
    )
    assert session.status == "needs_user_input" and session.pending.field == "consumer_number"
    resume(session, consumer)
    assert session.status == "done" and session.final.verdict == "SAFE"
    kinds = [e.kind for e in session.record.entries]
    assert "ask_user" in kinds and "user_reply" in kinds
    reply = next(e for e in session.record.entries if e.kind == "user_reply")
    assert consumer not in json.dumps(reply.payload)  # masked in the record


def test_no_answer_ends_as_caution():
    ask = turn(("ask_user", {"field": "consumer_number", "question": "Consumer number?"}))
    session, _ = run(
        GENUINE, [wave1(GENUINE), ask], agent_input=agent_input(GENUINE, consumer_number=None)
    )
    resume(session, "  ")
    assert session.final.forced and session.final.verdict == "CAUTION"


def test_second_question_is_refused():
    ask = ("ask_user", {"field": "consumer_number", "question": "Consumer number?"})
    session, _ = run(
        GENUINE, [wave1(GENUINE), turn(ask)], agent_input=agent_input(GENUINE, consumer_number=None)
    )
    session.client.steps = [turn(ask), cite_all("CAUTION")]
    resume(session, "DP-0000-000000")
    assert "ask_limit" in refusal_rules(session)
    assert session.final.verdict == "CAUTION"


# --- limits, allowlist, outages ---


def test_unknown_tool_is_refused_recorded_and_fed_back():
    session, model = run(
        GENUINE,
        [turn(("transfer_money", {"to": "x"})), wave1(GENUINE), wave2(GENUINE), cite_all("SAFE")],
    )
    assert refusal_rules(session) == ["unknown_tool"]
    assert "unknown tool 'transfer_money'" in last_outputs(model.conversations[1])[0]["error"]
    assert session.final.verdict == "SAFE" and session.submits == 0


def test_more_than_eight_tool_calls_ends_as_caution():
    many = turn(*[("match_scam_patterns", {"text": f"message {i}"}) for i in range(9)])
    session, _ = run(GENUINE, [many])
    assert session.final.forced and session.final.verdict == "CAUTION"
    assert "more than 8 tool calls" in session.final.forced_reason


def test_model_outage_ends_as_caution():
    session, _ = run(GENUINE, [wave1(GENUINE), LLMError("RateLimitError after 3 attempts")])
    assert session.final.forced and session.final.verdict == "CAUTION"
    assert session.final.forced_reason.startswith("model unavailable")


def test_stopping_without_a_verdict_is_nudged_once_then_forced():
    session, _ = run(
        GENUINE, [wave1(GENUINE), turn(text="I think it is fine."), turn(text="Done.")]
    )
    assert session.final.forced and "without submitting" in session.final.forced_reason


# --- milestone check inside a run ---


def test_link_forgotten_by_extraction_is_checked_before_the_agent_starts():
    forgot = agent_input(
        SCAM, payment_destinations=[PaymentDestination(kind="phone", value="9000000001")]
    )
    session, model = run(SCAM, [cite_all("SCAM")], agent_input=forgot)
    mandatory = session.record.tool_results_from("mandatory")
    assert mandatory[0].tool == "milestone_check"
    assert mandatory[0].codes == {EvidenceCode.MISSED_BY_EXTRACTION}
    link = next(r for r in mandatory if r.args.get("value") == "demopower-bill.example/pay")
    assert EvidenceCode.LOOKALIKE_DOMAIN in link.codes
    assert "demopower-bill.example/pay" in model.conversations[0][0].text
    assert session.final.verdict == "SCAM" and session.metrics.model_turns == 1


def test_judge_feedback_is_saved_in_the_record():
    def first_reason_unsupported(payload):
        return json.dumps(
            {"reasons": [{"index": r["index"], "supported": r["index"] != 0, "why": f"why {r['index']}"} for r in payload["reasons"]]}
        )  # fmt: skip

    session, _ = run(SCAM, [cite_all("SCAM"), cite_all("SCAM")], judge=[first_reason_unsupported])
    judged = [e.payload for e in session.record.entries if e.kind == "judge"]
    assert [j["accepted"] for j in judged] == [False, True]
    first = judged[0]["reasons"][0]
    assert first["supported"] is False and first["why"] == "why 0"
    assert first["reason"].startswith("Finding 1") and first["evidence_ids"]


# --- the whole dataset ---


@pytest.mark.parametrize("label", LABELS, ids=[lbl.id for lbl in LABELS])
def test_agent_reaches_every_label_verdict_in_one_turn(label):
    """With mandatory checks prefetched, a correct agent can submit in its first turn."""
    session, _ = run(label, [cite_all(label.expected.verdict.value)])
    assert session.final.verdict == label.expected.verdict
    assert not session.final.forced and session.metrics.refusals == 0
    assert session.metrics.model_turns == 1 and session.metrics.tool_calls == 0


@pytest.mark.parametrize("label", LABELS[:10], ids=[lbl.id for lbl in LABELS[:10]])
def test_agent_may_repeat_checks_itself(label):
    biller_id = TOOLS["lookup_biller"](
        name=label.expected.extracted.biller_name, category=label.expected.extracted.biller_category
    ).data.get("biller_id")
    steps = [wave1(label)]
    if second_wave(label, biller_id):
        steps.append(wave2(label))
    steps.append(cite_all(label.expected.verdict.value))
    session, _ = run(label, steps)
    assert session.final.verdict == label.expected.verdict and session.metrics.refusals == 0


def test_agent_config_targets():
    c = AgentConfig()
    assert (c.model, c.effort, c.max_tool_calls, c.max_submits, c.max_asks) == (
        "muse-spark-1.3",
        "low",
        8,
        3,
        1,
    )
    assert BillFields  # schema import used by helpers
