"""MOCK BBPS lookups over the synthetic registry and bills (pure functions)."""

import re

from app.bbps_mock.bills import BILLS, HISTORY_MONTHS, Bill
from app.bbps_mock.registry import BILLERS, BY_ID, Biller


def consumer_key(consumer_number: str) -> str:
    """Compare consumer numbers ignoring case, spaces and punctuation ("dp 4410-882761")."""
    return re.sub(r"[^0-9A-Z]", "", consumer_number.upper())


_INDEX: dict[tuple[str, str], list[Bill]] = {
    (biller_id, consumer_key(consumer)): history for (biller_id, consumer), history in BILLS.items()
}


def list_billers() -> tuple[Biller, ...]:
    return BILLERS


def get_biller(biller_id: str) -> Biller | None:
    return BY_ID.get(biller_id)


def consumers(biller_id: str) -> list[str]:
    return [consumer for (b, consumer) in BILLS if b == biller_id]


def current_bill(biller_id: str, consumer_number: str) -> Bill | None:
    history = _INDEX.get((biller_id, consumer_key(consumer_number)))
    return history[-1] if history else None


def bill_history(biller_id: str, consumer_number: str) -> list[Bill] | None:
    """The previous HISTORY_MONTHS bills (oldest first), excluding the current one."""
    history = _INDEX.get((biller_id, consumer_key(consumer_number)))
    return history[-1 - HISTORY_MONTHS : -1] if history else None
