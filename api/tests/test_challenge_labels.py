"""The challenge set is well formed, separate from the tuned dataset, and only synthetic."""

from pathlib import Path

from dataset_utils import LABELS

from app.schemas import Label

CHALLENGE = Path(__file__).resolve().parents[2] / "data" / "challenge"


def test_challenge_labels():
    lines = (CHALLENGE / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    labels = [Label.model_validate_json(line) for line in lines]
    assert len(labels) == 20
    assert not {x.id for x in labels} & {x.id for x in LABELS}
    assert all(x.split is None and x.synthetic for x in labels)  # in no dev or test split
    for label in labels:
        if label.input.kind == "image":
            assert (CHALLENGE / label.input.path).exists()
