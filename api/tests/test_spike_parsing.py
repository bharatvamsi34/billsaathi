import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.schemas import BillFields, ExtractionOutput, Label, Verdict
from spike import cases
from spike.cost import BudgetExceeded, CostMeter
from spike.transports import (
    CallResult,
    Prompt,
    apply_completed_response,
    consume_events,
    extract_json,
    iter_sse,
    responses_input,
    shape,
    split_reasoning,
    upload_file,
)

DUMMY_KEY = "dummy-not-a-real-key"


def test_iter_sse_parses_events_and_stops_at_done():
    lines = [
        'data: {"type": "a"}',
        "",
        "event: x",
        'data: {"type": "b"}',
        "",
        "data: [DONE]",
        "",
        'data: {"type": "c"}',
    ]
    assert [e["type"] for e in iter_sse(lines)] == ["a", "b"]


def test_iter_sse_flushes_last_event_without_blank_line():
    assert list(iter_sse(['data: {"n": 1}'])) == [{"n": 1}]


@pytest.mark.parametrize(
    "text",
    [
        '{"verdict": "SCAM"}',
        '```json\n{"verdict": "SCAM"}\n```',
        'Sure! Here it is: {"verdict": "SCAM"} hope it helps',
    ],
)
def test_extract_json_tolerates_fences_and_prose(text):
    assert extract_json(text) == {"verdict": "SCAM"}


def test_extract_json_raises_without_json():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_split_reasoning():
    assert split_reasoning('<think>hmm</think>\n{"a": 1}') == ("hmm", '{"a": 1}')
    assert split_reasoning("plain answer") == ("", "plain answer")


def test_completed_response_extracts_text_tools_and_usage():
    resp = {
        "output": [
            {"type": "reasoning", "summary": [{"text": "thinking"}]},
            {
                "type": "function_call",
                "call_id": "c1",
                "name": "lookup_biller",
                "arguments": '{"name": "x"}',
            },
            {"type": "message", "content": [{"type": "output_text", "text": "done"}]},
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "output_tokens_details": {"reasoning_tokens": 3},
        },
    }
    r = CallResult("meta", "t", "m")
    apply_completed_response(resp, r)
    assert r.text == "done"
    assert r.reasoning == "thinking"
    assert r.tool_calls == [
        {"call_id": "c1", "name": "lookup_biller", "arguments": '{"name": "x"}'}
    ]
    assert (r.input_tokens, r.output_tokens, r.reasoning_tokens) == (10, 5, 3)


def test_consume_events_streams_text_and_marks_ok():
    events = [
        {"type": "response.output_text.delta", "delta": "he"},
        {"type": "response.output_text.delta", "delta": "llo"},
        {
            "type": "response.completed",
            "response": {"output": [], "usage": {"input_tokens": 1, "output_tokens": 2}},
        },
    ]
    r = CallResult("meta", "t", "m")
    consume_events(events, r, 0.0)
    assert r.ok and r.text == "hello" and r.ttft_ms is not None


def test_consume_events_records_failure():
    r = CallResult("meta", "t", "m")
    consume_events(
        [{"type": "response.failed", "response": {"error": {"message": "boom"}}}], r, 0.0
    )
    assert not r.ok and "boom" in r.error


def test_extraction_output_fields_match_label_fields():
    # Day 2 eval labels and model output must compare field by field.
    assert set(ExtractionOutput.model_fields) == set(BillFields.model_fields)


def test_score_fields_perfect_and_amount_mismatch():
    exp = BillFields(
        biller_name="Demo Power Distribution Co. Ltd",
        amount=1240.0,
        consumer_number="DP-4410-882761",
    )
    assert cases.score_fields(exp, exp)["field_accuracy"] == 1.0
    wrong = exp.model_copy(update={"amount": 4240.0, "consumer_number": "dp4410882761"})
    s = cases.score_fields(wrong, exp)
    assert s["field_correct"]["amount"] is False
    assert s["field_correct"]["consumer_number"] is True


def test_languages_main_required_secondary_optional():
    assert cases.languages_ok(["en", "hi"], ["en", "hi"])
    assert cases.languages_ok(["EN"], ["en", "hi"])  # missed secondary is fine
    assert not cases.languages_ok(["hi"], ["en", "hi"])  # main language missing
    assert not cases.languages_ok(["en", "mr"], ["en", "hi"])  # invented language


def test_score_verdict():
    label = cases.load_labels()["sms_scam_en_txt"]
    out = cases.VerdictOutput(verdict=Verdict.CAUTION, reasons=[], urgency_language=True)
    s = cases.score_verdict(out, label)
    assert (
        s["verdict_correct"] is False
        and s["scam_flag_correct"] is False
        and s["urgency_correct"] is True
    )


def test_parse_model_reports_schema_errors():
    parsed, err = cases.parse_model(
        '{"verdict": "MAYBE", "reasons": [], "urgency_language": false}', cases.VerdictOutput
    )
    assert parsed is None and err.startswith("schema")


def test_tool_args_checked_against_schema():
    assert (
        cases.check_tool_args("lookup_biller", '{"name": "Demo", "category": "electricity"}')
        is None
    )
    assert "missing" in cases.check_tool_args("lookup_biller", '{"name": "Demo"}')
    assert "not JSON" in cases.check_tool_args("lookup_biller", "{bad")


def test_fake_tool_flags_lookalike_domain():
    out = cases.run_fake_tool(
        "check_payment_destination", {"kind": "url", "value": "dem0power-update.example/pay"}
    )
    assert out["official"] is False and out["lookalike_of"] == "demopower.example"


def test_script_ratio():
    assert cases.script_ratio("यह धोखा है", "hi") == 1.0
    assert cases.script_ratio("this is fraud", "hi") == 0.0


def test_cer_and_wer():
    assert cases.cer("abcd", "abcd") == 0.0
    assert cases.cer("abcd", "abed") == 0.25
    assert cases.wer("is this bill safe", "is the bill safe") == 0.25


def test_polygon_iou():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert cases.polygon_iou(sq, sq, (20, 20)) == pytest.approx(1.0)
    assert cases.polygon_iou(sq, [(11, 11), (19, 11), (19, 19), (11, 19)], (20, 20)) == 0.0


def test_cost_meter_guard_and_ledger(tmp_path: Path):
    meter = CostMeter(tmp_path / "ledger.json", budget_usd=0.01)
    meter.record("m", 1000, 100)  # assumed price: 0.005 + 0.002
    with pytest.raises(BudgetExceeded):
        meter.check("m", 1000, 2048)
    assert CostMeter(tmp_path / "ledger.json").spent_usd == pytest.approx(meter.spent_usd)


def test_responses_input_prefers_file_id_over_data_url():
    prompt = Prompt("sys", "user", image=cases.INPUTS / "bill_clean.png", image_file_id="file-1")
    part = responses_input(prompt)[1]["content"][1]
    assert part == {"type": "input_image", "file_id": "file-1"}
    prompt.image_file_id = None
    assert responses_input(prompt)[1]["content"][1]["image_url"].startswith(
        "data:image/png;base64,"
    )


def test_shape_shortens_long_values():
    s = shape({"mask": "x" * 500, "boxes": list(range(8)), "score": 0.9})
    assert s["mask"].startswith("<str len=500")
    assert s["boxes"] == [0, 1, 2, 3, 4, "<3 more items>"]
    assert s["score"] == 0.9


def test_upload_file_sends_purpose_and_redacts_errors(monkeypatch):
    settings = Settings(_env_file=None, meta_api_key=DUMMY_KEY, meta_api_base_url="https://x/v1")
    seen = {}

    def fake_post(url, **kw):
        seen.update(url=url, **kw)
        return httpx.Response(200, json={"id": "file-123"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert upload_file(settings, cases.INPUTS / "bill_clean.png") == "file-123"
    assert seen["url"] == "https://x/v1/files"
    assert seen["data"] == {"purpose": "user_data"}
    assert seen["files"]["file"][0] == "bill_clean.png"

    monkeypatch.setattr(
        httpx, "post", lambda url, **kw: httpx.Response(401, text=f"bad key {DUMMY_KEY}")
    )
    with pytest.raises(RuntimeError) as e:
        upload_file(settings, cases.INPUTS / "bill_clean.png")
    assert DUMMY_KEY not in str(e.value)


def test_labels_file_is_valid():
    lines = cases.LABELS.read_text(encoding="utf-8").splitlines()
    labels = [Label.model_validate_json(line) for line in lines]
    assert len({lbl.id for lbl in labels}) == len(labels)
    for lbl in labels:
        if lbl.input.path:
            assert (cases.INPUTS / lbl.input.path).exists(), lbl.id
    assert json.loads(lines[0])["synthetic"] is True
