"""Masking for logs: consumer numbers and phone numbers never appear in full."""

import re


def mask_id(value: str | None, keep: int = 4) -> str:
    """'DP-4410-882761' -> '**********2761'."""
    if not value:
        return "-"
    chars = re.sub(r"\s", "", value)
    return "*" * max(len(chars) - keep, 0) + chars[-keep:]


def mask_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[:2] + "*" * max(len(digits) - 4, 0) + digits[-2:] if digits else "-"
