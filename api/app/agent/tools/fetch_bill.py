"""fetch_bill: ask the (MOCK) biller what it actually billed, and compare with the claimed amount."""

from pydantic import BaseModel, Field

from app.agent.tools.base import Finding, Outcome, ToolError, define_tool
from app.bbps_mock import service
from app.schemas import EvidenceCode

AMOUNT_TOLERANCE = 1.0  # INR; rounding on printed bills


class Args(BaseModel):
    biller_id: str = Field(description="Official biller_id from lookup_biller")
    consumer_number: str = Field(description="Consumer / account number as written on the bill")
    claimed_amount: float | None = Field(
        default=None, description="Amount the bill or message asks the user to pay, in INR"
    )


@define_tool(
    "fetch_bill",
    "Fetch the current bill the biller has on record (mock BBPS) for this consumer number. "
    "If claimed_amount is given, says whether it matches the biller's amount.",
    Args,
)
def fetch_bill(args: Args) -> Outcome:
    biller = service.get_biller(args.biller_id)
    if biller is None:
        raise ToolError(f"unknown biller_id {args.biller_id!r}; call lookup_biller first")
    bill = service.current_bill(args.biller_id, args.consumer_number)
    if bill is None:
        return Outcome(
            [
                Finding(
                    EvidenceCode.CONSUMER_NOT_FOUND,
                    f"{biller.name} has no bill for this consumer number.",
                    {"format_valid": biller.valid_consumer(args.consumer_number.strip().upper())},
                )
            ],
            {"found": False},
        )
    data = {
        "found": True,
        "biller_amount": bill.amount,
        "bill_date": bill.bill_date.isoformat(),
        "due_date": bill.due_date.isoformat(),
        "bill_number": bill.bill_number,
    }
    findings = []
    if args.claimed_amount is not None:
        detail = {"biller_amount": bill.amount, "claimed_amount": args.claimed_amount}
        if abs(args.claimed_amount - bill.amount) <= AMOUNT_TOLERANCE:
            findings.append(
                Finding(
                    EvidenceCode.AMOUNT_MATCHES_BILLER,
                    f"Biller's amount ₹{bill.amount:,.2f} matches the claimed amount.",
                    detail,
                )
            )
        else:
            findings.append(
                Finding(
                    EvidenceCode.AMOUNT_MISMATCH,
                    f"Biller says ₹{bill.amount:,.2f}; the bill or message says ₹{args.claimed_amount:,.2f}.",
                    detail,
                )
            )
    return Outcome(findings, data)
