"""Spike test cases: prompts, tool definitions and scorers.

Ground truth comes from inputs/labels.jsonl (app.schemas.Label).
"""

import difflib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw
from pydantic import BaseModel, ValidationError

from app.schemas import BillFields, ExtractionOutput, Label, Verdict

INPUTS = Path(__file__).parent / "inputs"
LABELS = INPUTS / "labels.jsonl"


def load_labels() -> dict[str, Label]:
    lines = LABELS.read_text(encoding="utf-8").splitlines()
    labels = [Label.model_validate_json(line) for line in lines if line.strip()]
    return {lbl.id: lbl for lbl in labels}


# --- T1: scam reasoning on text ---

SYSTEM_VERDICT = (
    "You are BillSaathi, a fraud-checking assistant for Indian bill payments. "
    "The user forwards a message they received. Decide whether paying it is safe. "
    "Reply with ONLY a JSON object, no prose: "
    '{"verdict": "SAFE" | "CAUTION" | "SCAM", "reasons": [string, ...], '
    '"urgency_language": true | false}'
)


class VerdictOutput(BaseModel):
    verdict: Verdict
    reasons: list[str]
    urgency_language: bool


def score_verdict(out: VerdictOutput, label: Label) -> dict[str, Any]:
    expected = label.expected.verdict
    return {
        "verdict": out.verdict.value,
        "verdict_correct": out.verdict == expected,
        "scam_flag_correct": (out.verdict == Verdict.SCAM) == (expected == Verdict.SCAM),
        "urgency_correct": out.urgency_language == label.expected.extracted.urgency_language,
    }


# --- T2: extraction from images ---

SYSTEM_EXTRACT = (
    "You extract structured data from Indian bills and payment requests (bills, SMS, "
    "WhatsApp screenshots). Return ONLY a JSON object matching this JSON Schema, no prose. "
    "Use null when a field is not present. Dates are YYYY-MM-DD. amount is a number in INR. "
    "confidence is 0..1 and must be low when you are unsure.\n"
    + json.dumps(ExtractionOutput.model_json_schema())
)


def _norm_id(v: str | None) -> str | None:
    return re.sub(r"[^0-9A-Z]", "", v.upper()) if v else None


def _norm_dest(kind: str, value: str) -> tuple[str, str]:
    v = value.lower().strip()
    if kind == "url":
        v = re.sub(r"^https?://", "", v).removeprefix("www.").rstrip("/")
    elif kind == "phone":
        v = re.sub(r"\D", "", v)[-10:]
    return kind, v


def score_fields(pred: BillFields, exp: BillFields) -> dict[str, Any]:
    def name_ok() -> bool:
        if exp.biller_name is None or pred.biller_name is None:
            return exp.biller_name == pred.biller_name
        ratio = difflib.SequenceMatcher(
            None, exp.biller_name.lower(), pred.biller_name.lower()
        ).ratio()
        return ratio >= 0.8

    amount_ok = (
        exp.amount == pred.amount
        if exp.amount is None or pred.amount is None
        else abs(exp.amount - pred.amount) < 0.01
    )
    want = {_norm_dest(d.kind, d.value) for d in exp.payment_destinations}
    got = {_norm_dest(d.kind, d.value) for d in pred.payment_destinations}
    fields = {
        "biller_name": name_ok(),
        "biller_category": pred.biller_category == exp.biller_category,
        "consumer_number": _norm_id(pred.consumer_number) == _norm_id(exp.consumer_number),
        "amount": amount_ok,
        "due_date": pred.due_date == exp.due_date,
        "bill_date": pred.bill_date == exp.bill_date,
        "payment_destinations": want <= got,
        "language": pred.language == exp.language,
        "urgency_language": pred.urgency_language == exp.urgency_language,
    }
    return {"field_correct": fields, "field_accuracy": sum(fields.values()) / len(fields)}


def parse_model(text: str, model: type[BaseModel]) -> tuple[BaseModel | None, str | None]:
    """Return (parsed, error). Never raises; error says whether JSON or schema failed."""
    from spike.transports import extract_json

    try:
        data = extract_json(text)
    except ValueError as e:
        return None, f"json: {e}"
    try:
        return model.model_validate(data), None
    except ValidationError as e:
        return None, f"schema: {e.error_count()} errors: {str(e)[:300]}"


# --- T3: native tool calling ---

TOOL_SPECS = [
    {
        "name": "lookup_biller",
        "description": "Look up a biller in the BBPS biller registry by name and category.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Biller name as written in the message"},
                "category": {
                    "type": "string",
                    "enum": ["electricity", "water", "gas", "broadband", "other"],
                },
            },
            "required": ["name", "category"],
        },
    },
    {
        "name": "check_payment_destination",
        "description": "Check whether a UPI ID, URL or phone number is an official channel of a biller.",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["upi", "url", "phone"]},
                "value": {"type": "string"},
            },
            "required": ["kind", "value"],
        },
    },
]

TOOLS_RESPONSES = [{"type": "function", **spec} for spec in TOOL_SPECS]
TOOLS_CHAT = [{"type": "function", "function": spec} for spec in TOOL_SPECS]

SYSTEM_TOOLS = (
    "You are BillSaathi, a fraud-checking agent for Indian bill payments. Use the tools to "
    "verify the biller and every payment destination in the message before deciding. "
    "When done, reply with ONLY a JSON object: "
    '{"verdict": "SAFE" | "CAUTION" | "SCAM", "reasons": [string, ...], "urgency_language": true | false}'
)


def run_fake_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Deterministic stand-ins for the real tools (synthetic data only)."""
    if name == "lookup_biller":
        if (
            "demo power" in str(args.get("name", "")).lower()
            or args.get("category") == "electricity"
        ):
            return {
                "found": True,
                "biller_id": "DEMO00000MAH01",
                "official_name": "Demo Power Distribution Co. Ltd",
                "official_domains": ["demopower.example"],
                "official_vpas": ["demopower.bill@demobank"],
            }
        return {"found": False}
    if name == "check_payment_destination":
        value = str(args.get("value", "")).lower()
        if (
            "demopower.example" in value
            and "dem0" not in value
            or value == "demopower.bill@demobank"
        ):
            return {"official": True, "biller_id": "DEMO00000MAH01"}
        if "dem0power" in value:
            return {"official": False, "lookalike_of": "demopower.example", "known_scam": True}
        if args.get("kind") == "phone":
            return {
                "official": False,
                "note": "personal mobile number, not a registered biller channel",
            }
        return {"official": False, "known_scam": False}
    return {"error": f"unknown tool {name}"}


def check_tool_args(name: str, raw: str | None) -> str | None:
    """Return an error string if the arguments are not valid JSON matching the tool schema."""
    spec = next((s for s in TOOL_SPECS if s["name"] == name), None)
    if spec is None:
        return f"unknown tool {name}"
    try:
        args = json.loads(raw or "")
    except json.JSONDecodeError as e:
        return f"arguments not JSON: {e}"
    missing = [k for k in spec["parameters"]["required"] if k not in args]
    return f"missing {missing}" if missing else None


# --- T4: multilingual explanation ---

EXPLAIN_LANGS = {"hi": "Hindi", "mr": "Marathi", "te": "Telugu", "ta": "Tamil"}
SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),
    "mr": (0x0900, 0x097F),
    "te": (0x0C00, 0x0C7F),
    "ta": (0x0B80, 0x0BFF),
}

FIXED_VERDICT = {
    "verdict": "SCAM",
    "evidence": [
        "The link dem0power-update.example imitates the official site demopower.example (zero instead of 'o').",
        "The phone number is a personal mobile number, not an official Demo Power channel.",
        "The message threatens disconnection tonight to rush you.",
    ],
}


def explain_prompt(lang: str) -> tuple[str, str]:
    system = (
        "You explain fraud-check results to ordinary people in India. Write in simple, warm "
        f"{EXPLAIN_LANGS[lang]} using its native script. 3-5 short sentences. Say clearly what to do next."
    )
    return system, "Explain this result to the user:\n" + json.dumps(
        FIXED_VERDICT, ensure_ascii=False
    )


def script_ratio(text: str, lang: str) -> float:
    lo, hi = SCRIPT_RANGES[lang]
    letters = [c for c in text if c.isalpha()]
    return sum(lo <= ord(c) <= hi for c in letters) / len(letters) if letters else 0.0


# --- T5 / T6 helpers ---


def edit_distance(a: list[str] | str, b: list[str] | str) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    return edit_distance(ref, hyp) / max(len(ref), 1)


def wer(ref: str, hyp: str) -> float:
    r = re.findall(r"\w+", ref.lower())
    return edit_distance(r, re.findall(r"\w+", hyp.lower())) / max(len(r), 1)


def polygon_iou(
    a: list[tuple[float, float]], b: list[tuple[float, float]], size: tuple[int, int]
) -> float:
    """IoU of two polygons, rasterised at image size (good enough for crop quality)."""
    masks = []
    for poly in (a, b):
        m = Image.new("1", size, 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        masks.append(m)

    def area(m: Image.Image) -> int:
        return m.convert("L").histogram()[255]

    union = area(ImageChops.logical_or(*masks))
    return area(ImageChops.logical_and(*masks)) / union if union else 0.0
