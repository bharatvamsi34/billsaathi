"""Shared Pydantic schemas.

The label format (`Label`) is used unchanged by the Day 1 model spike
(api/spike/inputs/labels.jsonl) and the evaluation set (data/synthetic/labels.jsonl).
`ExtractionOutput` is what the vision model must return; its field names match
`BillFields` exactly so predictions and labels compare field by field.
"""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    SCAM = "SCAM"


class BillerCategory(StrEnum):
    ELECTRICITY = "electricity"
    WATER = "water"
    GAS = "gas"
    BROADBAND = "broadband"
    MOBILE_POSTPAID = "mobile_postpaid"
    DTH = "dth"
    OTHER = "other"


class DestinationKind(StrEnum):
    UPI = "upi"
    URL = "url"
    PHONE = "phone"
    QR = "qr"
    OTHER = "other"


class EvidenceCode(StrEnum):
    BILLER_VERIFIED = "BILLER_VERIFIED"
    UNKNOWN_BILLER = "UNKNOWN_BILLER"
    AMOUNT_MATCHES_BILLER = "AMOUNT_MATCHES_BILLER"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DESTINATION_OFFICIAL = "DESTINATION_OFFICIAL"
    DESTINATION_NOT_OFFICIAL = "DESTINATION_NOT_OFFICIAL"
    LOOKALIKE_DOMAIN = "LOOKALIKE_DOMAIN"
    KNOWN_SCAM_DESTINATION = "KNOWN_SCAM_DESTINATION"
    PERSONAL_PHONE_NUMBER = "PERSONAL_PHONE_NUMBER"
    APK_LINK = "APK_LINK"
    SHORT_URL = "SHORT_URL"
    DISCONNECTION_THREAT = "DISCONNECTION_THREAT"
    KYC_UPDATE_LURE = "KYC_UPDATE_LURE"
    AMOUNT_SPIKE = "AMOUNT_SPIKE"


class InputKind(StrEnum):
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"


class Channel(StrEnum):
    PAPER_BILL = "paper_bill"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"


class PaymentDestination(BaseModel):
    kind: DestinationKind
    value: str


class BillFields(BaseModel):
    """Fields extracted from a bill or payment request. Shared by labels and model output."""

    biller_name: str | None = None
    biller_category: BillerCategory | None = None
    consumer_number: str | None = None
    amount: float | None = None  # INR
    due_date: date | None = None
    bill_date: date | None = None
    payment_destinations: list[PaymentDestination] = Field(default_factory=list)
    language: str | None = None  # ISO 639-1 code of the main language
    urgency_language: bool = False


class Scored[T](BaseModel):
    value: T
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionOutput(BaseModel):
    """Vision-model extraction: every BillFields field, each with a confidence."""

    biller_name: Scored[str | None]
    biller_category: Scored[BillerCategory | None]
    consumer_number: Scored[str | None]
    amount: Scored[float | None]
    due_date: Scored[date | None]
    bill_date: Scored[date | None]
    payment_destinations: Scored[list[PaymentDestination]]
    language: Scored[str | None]
    urgency_language: Scored[bool]

    def to_fields(self) -> BillFields:
        return BillFields(**{name: getattr(self, name).value for name in BillFields.model_fields})


class Evidence(BaseModel):
    code: EvidenceCode
    source: str  # tool that should produce it, e.g. "check_payment_destination"


class Region(BaseModel):
    kind: Literal["document", "payment_link", "qr", "amount"]
    polygon: list[tuple[float, float]]  # pixel coordinates in the input image


class LabelInput(BaseModel):
    kind: InputKind
    channel: Channel
    path: str | None = None  # relative to the labels file
    text: str | None = None


class Expected(BaseModel):
    extracted: BillFields
    verdict: Verdict | None  # None for inputs that are only a question, not a payment request
    evidence: list[Evidence] = Field(default_factory=list)
    transcript: str | None = None
    regions: list[Region] = Field(default_factory=list)


class Label(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    scenario: str  # e.g. genuine_bill, tampered_amount, disconnection_scam, kyc_apk_scam
    input: LabelInput
    expected: Expected
    synthetic: Literal[True] = True
