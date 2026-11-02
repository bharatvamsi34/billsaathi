"""SAM isolation: crops when sensible, and anything odd means the original image."""

import io

import pytest
from fakes import turn  # noqa: F401
from PIL import Image
from test_api_checks import BILL, FakeExtractor, api, cite_all, events_of, tiny_image  # noqa: F401

from app.main import app
from app.models.base import LLMError
from app.vision import crop, isolate, parse_box


def jpeg(size=(1000, 800)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, "white").save(out, format="JPEG")
    return out.getvalue()


def box_text(x1, y1, x2, y2, w=1000, h=800) -> str:
    return f"<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={w};h={h}|><|mask;x=0;y=0;data=4,4,abc|>"


class FakeSam:
    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def segment(self, image, mime):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_parse_takes_the_largest_valid_box():
    box = parse_box(box_text(0, 0, 10, 10) + box_text(100, 100, 900, 700))
    assert (box.x1, box.x2) == (100, 900)
    assert box.area == pytest.approx(0.6)


@pytest.mark.parametrize("text", ["", "no tokens", box_text(900, 100, 100, 700), box_text(0, 0, 2000, 700)])  # fmt: skip
def test_parse_ignores_missing_or_impossible_boxes(text):
    assert parse_box(text) is None


def test_a_bill_on_a_table_is_cropped():
    out = isolate(FakeSam(box_text(100, 100, 700, 700)), jpeg(), "image/jpeg")
    assert out.cropped and out.mime == "image/jpeg" and out.cost_usd == 0.0025
    with Image.open(io.BytesIO(out.image)) as im:
        assert im.size == (640, 632)  # the box plus a 2% margin


def test_a_bill_that_fills_the_image_is_not_recompressed():
    image = jpeg()
    out = isolate(FakeSam(box_text(0, 0, 999, 799)), image, "image/jpeg")
    assert not out.cropped and out.image == image and out.box is not None


@pytest.mark.parametrize(
    "reply",
    [
        "",  # nothing found
        box_text(10, 10, 100, 100),  # a tiny box is not the bill
        LLMError("down"),
        box_text(10, 10, 400, 400, w=500, h=500),  # the box belongs to another image size
    ],
    ids=["none", "tiny", "failure", "other-size"],
)
def test_anything_odd_uses_the_original_image(reply):
    image = jpeg()
    out = isolate(FakeSam(reply), image, "image/jpeg")
    assert out.image == image and out.mime == "image/jpeg" and not out.cropped and out.box is None


def test_crop_refuses_a_mismatched_box():
    with pytest.raises(ValueError):
        crop(jpeg((100, 100)), parse_box(box_text(0, 0, 500, 500)))


# --- in the pipeline ---


class Spy(FakeExtractor):
    """Records which image each call received."""

    def __init__(self, label):
        super().__init__(label)
        self.seen = {}

    def respond(self, *, system, messages, model, effort="low", max_output_tokens=4096):
        from app.extract.extract import TRANSCRIBE_PROMPT

        kind = "transcribe" if system == TRANSCRIBE_PROMPT else "fields"
        self.seen[kind] = messages[0].image_data_url
        return super().respond(
            system=system, messages=messages, model=model, effort=effort, max_output_tokens=max_output_tokens
        )  # fmt: skip


def post_image(client, data, name="b.jpg", mime="image/jpeg"):
    return client.post(
        "/api/v1/checks", data={"language": "en"}, files={"image": (name, data, mime)}
    )


def test_fields_read_the_crop_but_transcription_reads_the_original(api):  # noqa: F811
    client, install = api
    install(BILL, [cite_all("SAFE")])
    spy = app.state.clients.extract = Spy(BILL)
    sam = app.state.clients.sam = FakeSam(box_text(100, 100, 700, 700))
    r = post_image(client, jpeg())
    events = events_of(client, r.json()["check_id"])
    assert sam.calls == 1
    assert spy.seen["fields"] != spy.seen["transcribe"]
    event = next(e for e in events if e["type"] == "isolated")
    assert event["cropped"] is True and event["box"]["x2"] == 700 and event["model"] == "sam-3.1"
    assert [e["type"] for e in events][:3] == ["received", "isolated", "extracted"]
    assert events[-1]["cost_usd"]["isolation"] == 0.0025


def test_sam_failure_still_gives_a_normal_check(api):  # noqa: F811
    client, install = api
    install(BILL, [cite_all("SAFE")])
    spy = app.state.clients.extract = Spy(BILL)
    app.state.clients.sam = FakeSam(LLMError("down"))
    events = events_of(client, post_image(client, jpeg()).json()["check_id"])
    assert next(e for e in events if e["type"] == "isolated")["box"] is None
    assert next(e for e in events if e["type"] == "verdict")["verdict"] == "SAFE"
    assert spy.seen["fields"] == spy.seen["transcribe"]  # both read the original


def test_no_event_and_no_call_for_text_or_without_sam(api):  # noqa: F811
    client, install = api
    install(BILL, [cite_all("SAFE")])
    events = events_of(client, post_image(client, jpeg()).json()["check_id"])
    assert "isolated" not in [e["type"] for e in events]  # Privacy Mode has no SAM
