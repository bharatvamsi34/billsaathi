"""get_bill_history: compare the amount asked for with the consumer's last 6 bills (MOCK BBPS)."""

import statistics

from pydantic import BaseModel, Field

from app.agent.tools.base import Finding, Outcome, ToolError, define_tool
from app.bbps_mock import service
from app.schemas import EvidenceCode

SPIKE_RATIO = 2.0  # current >= 2x the usual bill
SPIKE_RATIO_WITH_MAD = 1.5  # or >= 1.5x and far outside the usual spread
MAD_FACTOR = 6.0


class Args(BaseModel):
    biller_id: str = Field(description="Official biller_id from lookup_biller")
    consumer_number: str = Field(description="Consumer / account number")
    current_amount: float | None = Field(
        default=None,
        description="Amount being asked for now, in INR; defaults to the biller's current bill",
    )


@define_tool(
    "get_bill_history",
    "Get the consumer's last 6 bills (mock BBPS) and say whether the current amount is a "
    "sudden spike compared with their usual bill.",
    Args,
)
def get_bill_history(args: Args) -> Outcome:
    if service.get_biller(args.biller_id) is None:
        raise ToolError(f"unknown biller_id {args.biller_id!r}; call lookup_biller first")
    history = service.bill_history(args.biller_id, args.consumer_number)
    if not history:
        return Outcome(
            [Finding(EvidenceCode.CONSUMER_NOT_FOUND, "No bill history for this consumer number.")],
            {"found": False},
        )
    amounts = [b.amount for b in history]
    current = args.current_amount
    if current is None:
        current = service.current_bill(args.biller_id, args.consumer_number).amount
    median = statistics.median(amounts)
    mad = statistics.median(abs(a - median) for a in amounts)
    ratio = current / median if median else float("inf")
    spike = ratio >= SPIKE_RATIO or (
        ratio >= SPIKE_RATIO_WITH_MAD and mad > 0 and current > median + MAD_FACTOR * mad
    )
    detail = {"usual_amount": median, "current_amount": current, "ratio": round(ratio, 2)}
    data = {"found": True, "history": amounts, **detail}
    if spike:
        return Outcome(
            [
                Finding(
                    EvidenceCode.AMOUNT_SPIKE,
                    f"₹{current:,.2f} is {ratio:.1f}x the usual bill of about ₹{median:,.0f}.",
                    detail,
                )
            ],
            data,
        )
    return Outcome(
        [
            Finding(
                EvidenceCode.AMOUNT_WITHIN_HISTORY,
                f"₹{current:,.2f} is in line with the usual bill of about ₹{median:,.0f}.",
                detail,
            )
        ],
        data,
    )
