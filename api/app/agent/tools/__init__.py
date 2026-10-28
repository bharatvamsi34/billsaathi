"""The agent's verification tools. Each returns a ToolResult and never raises."""

from app.agent.tools.base import Tool
from app.agent.tools.check_payment_destination import check_payment_destination
from app.agent.tools.fetch_bill import fetch_bill
from app.agent.tools.get_bill_history import get_bill_history
from app.agent.tools.lookup_biller import lookup_biller
from app.agent.tools.match_scam_patterns import match_scam_patterns

TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        lookup_biller,
        fetch_bill,
        check_payment_destination,
        get_bill_history,
        match_scam_patterns,
    )
}
