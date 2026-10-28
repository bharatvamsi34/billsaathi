"""Live check of extraction on 5 dev images (~$0.05). Skipped unless run with: pytest -m live -s"""

import difflib
import mimetypes
import re
from pathlib import Path

import pytest

from app.config import get_settings
from app.extract import extract
from app.models.meta import MetaClient
from app.schemas import Label

pytestmark = pytest.mark.live

DATA = Path(__file__).resolve().parents[2] / "data" / "synthetic"
LIVE_IDS = [  # dev split, one per kind of image
    "bill_genuine_demo",
    "photo_genuine_demo",
    "bill_tampered_svsl",
    "bill_swapped_vpa_dgas",
    "scam_en_disconnect_lookalike",
]


def _labels() -> dict[str, Label]:
    lines = (DATA / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    return {lbl.id: lbl for lbl in map(Label.model_validate_json, lines)}


def _norm(value: str | None) -> str:
    return (
        re.sub(r"[^0-9a-z@.]", "", (value or "").lower()).removeprefix("https").removeprefix("http")
    )


@pytest.mark.parametrize("label_id", LIVE_IDS)
def test_live_extraction(label_id):
    if get_settings().meta_api_key is None:
        pytest.skip("META_API_KEY not set")
    label = _labels()[label_id]
    assert label.split == "dev"
    path = DATA / label.input.path
    result = extract(
        MetaClient(get_settings()),
        image=path.read_bytes(),
        image_mime=mimetypes.guess_type(path.name)[0],
    )
    got, want = result.output.to_fields(), label.expected.extracted
    checks = {
        "amount": got.amount == want.amount,
        "consumer": _norm(got.consumer_number) == _norm(want.consumer_number),
        "biller": difflib.SequenceMatcher(None, (got.biller_name or "").lower(), (want.biller_name or "").lower()).ratio() >= 0.8,
        "destinations": {_norm(d.value) for d in want.payment_destinations} <= {_norm(d.value) for d in got.payment_destinations},
    }  # fmt: skip
    print(
        f"\n{label_id}: attempts={result.attempts} {result.latency_ms:.0f}ms "
        f"in={result.usage.input_tokens} out={result.usage.output_tokens} "
        f"cost=${result.usage.cost_usd:.4f} checks={checks}"
    )
    assert all(checks.values()), checks
