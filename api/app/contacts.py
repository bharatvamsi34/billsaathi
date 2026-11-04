"""Turn the many ways of writing a contact into one form, so a number cannot hide in its spelling."""

import re
import unicodedata

_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"))
_DOTS = dict.fromkeys(map(ord, "。．｡"), ".")


def ascii_digits(text: str) -> str:
    """Any decimal digit (Devanagari, Telugu, other Indic, full-width...) as 0-9."""
    return "".join(
        str(unicodedata.decimal(ch)) if not ch.isascii() and unicodedata.category(ch) == "Nd" else ch
        for ch in text
    )


def normalise_text(text: str) -> str:
    """Text for contact detection: same characters, one spelling of digits and dots, nothing hidden."""
    return ascii_digits(unicodedata.normalize("NFKC", text).translate(_INVISIBLE).translate(_DOTS))


def canonical_phone(value: str) -> str:
    """Digits only, without +91 or a leading 0. Toll-free numbers keep all their digits."""
    digits = re.sub(r"\D", "", ascii_digits(value))
    if digits.startswith("91") and (
        len(digits) == 12 or (len(digits) == 13 and digits[2:4] == "18")
    ):
        return digits[2:]
    if digits.startswith("0") and (len(digits) == 11 or (len(digits) == 12 and digits[1:3] == "18")):
        return digits[1:]
    return digits
