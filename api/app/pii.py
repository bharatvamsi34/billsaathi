"""Masking: consumer numbers and phone numbers never appear in full in logs, events or
model prompts beyond what a step strictly needs."""

import re
from typing import Any

# Stand-alone digit runs only: never inside identifiers such as evidence ids ("ev_1234567890").
_LONG_DIGITS = re.compile(r"(?<![\w+])(\+?\d[\d\s-]{6,}\d)(?![\w])")


def mask_id(value: str | None, keep: int = 4) -> str:
    """'DP-4410-882761' -> '**********2761'."""
    if not value:
        return "-"
    chars = re.sub(r"\s", "", value)
    return "*" * max(len(chars) - keep, 0) + chars[-keep:]


def mask_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[:2] + "*" * max(len(digits) - 4, 0) + digits[-2:] if digits else "-"


def mask_destination(kind: str, value: str) -> str:
    return mask_phone(value) if kind == "phone" else value


def scrub(text: str | None, secrets: list[str] = ()) -> str | None:
    """Mask phone-like digit runs and any known consumer numbers inside free text."""
    if not text:
        return text
    for s in secrets:
        if s and len(s) >= 4:
            text = text.replace(s, mask_id(s))

    def mask(m: re.Match) -> str:  # 9+ digits: phones, consumer numbers; dates (8) stay readable
        run = m.group(1)
        return mask_phone(run) if sum(ch.isdigit() for ch in run) >= 9 else run

    return _LONG_DIGITS.sub(mask, text)


def mask_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Tool arguments safe to show: consumer and phone numbers masked, raw text replaced."""
    out = dict(args)
    if "consumer_number" in out:
        out["consumer_number"] = mask_id(out["consumer_number"])
    if "text" in out:  # the raw message never leaves the server
        out["text"] = f"<{len(out['text'] or '')} characters>"
    if tool == "check_payment_destination" and "value" in out:
        out["value"] = mask_destination(out.get("kind", ""), out["value"])
    return out
