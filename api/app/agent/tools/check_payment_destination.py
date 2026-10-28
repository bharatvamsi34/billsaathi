"""check_payment_destination: is this UPI ID / link / phone number an official channel of the biller?

Order of checks: official allowlist -> known-scam list -> lookalike detection -> other risk
signals (APK file, link shortener, personal mobile number). Anything not on the allowlist is
DESTINATION_NOT_OFFICIAL.
"""

import re
import unicodedata
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field

from app.agent.tools import scam_intel
from app.agent.tools.base import Finding, Outcome, ToolError, define_tool, edit_distance
from app.bbps_mock import service
from app.bbps_mock.registry import Biller
from app.schemas import DestinationKind, EvidenceCode


class Args(BaseModel):
    kind: DestinationKind = Field(description="upi, url, phone or qr (raw QR text)")
    value: str = Field(description="The destination exactly as written in the message")
    biller_id: str | None = Field(
        default=None, description="Official biller_id if known; checks against that biller only"
    )


# Characters attackers swap in to imitate a brand name (digits, Cyrillic look-alikes).
_CONFUSABLES = str.maketrans(
    {
        "0": "o", "1": "l", "i": "l", "!": "l", "|": "l", "3": "e", "5": "s", "$": "s", "4": "a",
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "l", "ӏ": "l",
    }
)  # fmt: skip


def skeleton(text: str) -> str:
    """Collapse look-alike spellings: 'dem0p0wer', 'demo-power' and 'dеmopower' all -> 'demopower'."""
    s = unicodedata.normalize("NFKC", text.lower()).replace("rn", "m").replace("vv", "w")
    return s.translate(_CONFUSABLES).replace("-", "").replace("_", "")


def _close(a: str, b: str) -> bool:
    return edit_distance(a, b) <= (2 if len(b) >= 6 else 1)


def _targets(biller_id: str | None) -> tuple[Biller, ...]:
    if biller_id is None:
        return service.list_billers()
    biller = service.get_biller(biller_id)
    if biller is None:
        raise ToolError(f"unknown biller_id {biller_id!r}; call lookup_biller first")
    return (biller,)


def _decode_host(host: str) -> str:
    labels = []
    for label in host.split("."):
        try:
            labels.append(
                label.encode("ascii").decode("idna") if label.startswith("xn--") else label
            )
        except UnicodeError:
            labels.append(label)
    return ".".join(labels)


def _check_url(value: str, targets: tuple[Biller, ...]) -> Outcome:
    raw = value.strip()
    parts = urlsplit(raw if "://" in raw else f"http://{raw}")
    host = _decode_host((parts.hostname or "").rstrip(".").removeprefix("www."))
    path = parts.path.lower()
    detail = {"host": host}
    if not host:
        raise ToolError("could not read a host name from this link")
    findings: list[Finding] = []

    official = next(
        (b for b in targets for d in b.official_domains if host == d or host.endswith(f".{d}")),
        None,
    )
    if path.endswith(".apk"):
        findings.append(
            Finding(EvidenceCode.APK_LINK, "The link downloads an Android app (.apk).", detail)
        )
    if official is not None and not findings:
        return Outcome(
            [Finding(EvidenceCode.DESTINATION_OFFICIAL, f"{host} is an official site of {official.name}.", {**detail, "biller_id": official.biller_id})],
            {"official": True, "biller_id": official.biller_id},
        )  # fmt: skip
    other = _official_elsewhere(host, targets)
    if other is not None:
        detail["belongs_to"] = other.biller_id
    if host in scam_intel.URL_SHORTENERS:
        findings.append(
            Finding(EvidenceCode.SHORT_URL, "The link is hidden behind a link shortener.", detail)
        )
    if host in scam_intel.KNOWN_SCAM_DOMAINS:
        findings.append(
            Finding(
                EvidenceCode.KNOWN_SCAM_DESTINATION, f"{host} is on the known-scam list.", detail
            )
        )
    lookalike = None if official or other else _lookalike_domain(host)
    if lookalike is not None:
        findings.append(
            Finding(
                EvidenceCode.LOOKALIKE_DOMAIN,
                f"{host} imitates the official site {lookalike}.",
                {**detail, "lookalike_of": lookalike},
            )
        )
    findings.append(
        Finding(
            EvidenceCode.DESTINATION_NOT_OFFICIAL,
            f"{host} is not an official payment channel.",
            detail,
        )
    )
    return Outcome(findings, {"official": False, "host": host, "lookalike_of": lookalike})


def _official_elsewhere(host: str, targets: tuple[Biller, ...]) -> Biller | None:
    """Official site of a *different* biller than the one being checked."""
    if len(targets) != 1:
        return None
    for b in service.list_billers():
        if b is not targets[0] and any(
            host == d or host.endswith(f".{d}") for d in b.official_domains
        ):
            return b
    return None


def _lookalike_domain(host: str) -> str | None:
    labels = host.split(".")
    for b in service.list_billers():
        for domain in b.official_domains:
            if domain in host:  # e.g. demopower.example.pay-now.example
                return domain
            brand = skeleton(domain.split(".")[0])
            for label in labels[:-1] or labels:
                s = skeleton(label)
                if s == brand or brand in s or _close(s, brand):
                    return domain
    return None


def _check_upi(value: str, targets: tuple[Biller, ...]) -> Outcome:
    vpa = value.strip().lower()
    detail = {"vpa": vpa}
    if not re.fullmatch(r"[a-z0-9._-]{2,256}@[a-z0-9]{2,64}", vpa):
        return Outcome(
            [Finding(EvidenceCode.DESTINATION_NOT_OFFICIAL, "This is not a valid UPI ID.", detail)],
            {"official": False, "valid": False},
        )
    for b in targets:
        if vpa in b.official_vpas:
            return Outcome(
                [Finding(EvidenceCode.DESTINATION_OFFICIAL, f"{vpa} is an official UPI ID of {b.name}.", {**detail, "biller_id": b.biller_id})],
                {"official": True, "biller_id": b.biller_id},
            )  # fmt: skip
    findings: list[Finding] = []
    if vpa in scam_intel.KNOWN_SCAM_VPAS:
        findings.append(
            Finding(
                EvidenceCode.KNOWN_SCAM_DESTINATION, f"{vpa} is on the known-scam list.", detail
            )
        )
    handle = skeleton(vpa.split("@")[0])
    for b in service.list_billers():
        for official in b.official_vpas:
            o_handle = skeleton(official.split("@")[0])
            brand = skeleton(b.official_domains[0].split(".")[0])
            if vpa != official and (
                handle == o_handle or _close(handle, o_handle) or brand in handle
            ):
                findings.append(
                    Finding(
                        EvidenceCode.LOOKALIKE_VPA,
                        f"{vpa} imitates the official UPI ID {official}.",
                        {**detail, "lookalike_of": official},
                    )
                )
                break
    findings.append(
        Finding(EvidenceCode.DESTINATION_NOT_OFFICIAL, f"{vpa} is not an official UPI ID.", detail)
    )
    return Outcome(findings, {"official": False, "valid": True})


def _check_phone(value: str, targets: tuple[Biller, ...]) -> Outcome:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    masked = digits[:2] + "*" * max(len(digits) - 4, 0) + digits[-2:]
    detail = {"phone_masked": masked}
    for b in targets:
        if digits in b.official_phones:
            return Outcome(
                [Finding(EvidenceCode.DESTINATION_OFFICIAL, f"Official helpline of {b.name}.", {**detail, "biller_id": b.biller_id})],
                {"official": True, "biller_id": b.biller_id},
            )  # fmt: skip
    findings: list[Finding] = []
    if digits in scam_intel.KNOWN_SCAM_PHONES:
        findings.append(
            Finding(
                EvidenceCode.KNOWN_SCAM_DESTINATION,
                "This number is on the known-scam list.",
                detail,
            )
        )
    if len(digits) == 10 and digits[0] in "6789":
        findings.append(
            Finding(
                EvidenceCode.PERSONAL_PHONE_NUMBER,
                "This is a personal mobile number, not a registered biller channel.",
                detail,
            )
        )
    findings.append(
        Finding(
            EvidenceCode.DESTINATION_NOT_OFFICIAL, "This number is not an official channel.", detail
        )
    )
    return Outcome(findings, {"official": False})


@define_tool(
    "check_payment_destination",
    "Check a UPI ID, payment link, phone number or QR text against the biller's official "
    "channels, the known-scam list and lookalike detection (e.g. 0 instead of o).",
    Args,
)
def check_payment_destination(args: Args) -> Outcome:
    targets = _targets(args.biller_id)
    if args.kind == DestinationKind.UPI:
        return _check_upi(args.value, targets)
    if args.kind == DestinationKind.URL:
        return _check_url(args.value, targets)
    if args.kind == DestinationKind.PHONE:
        return _check_phone(args.value, targets)
    if args.kind == DestinationKind.QR:
        text = args.value.strip()
        if text.lower().startswith("upi://"):
            pa = parse_qs(urlsplit(text).query).get("pa", [""])[0]
            outcome = _check_upi(pa, targets)
            outcome.data["from_qr"] = True
            return outcome
        if re.match(r"(https?://)?[\w.-]+\.[a-z]{2,}", text, re.IGNORECASE):
            return _check_url(text, targets)
    return Outcome(
        [
            Finding(
                EvidenceCode.DESTINATION_NOT_OFFICIAL, "This destination could not be recognised."
            )
        ],
        {"official": False},
    )
