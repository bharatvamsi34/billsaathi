"""MOCK bills: 5 synthetic consumers per biller, each with a current bill (Oct 2026)
and 6 months of history. Generated deterministically, so tests and labels can rely on it.
"""

import random
import statistics
from collections.abc import Callable
from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict

from app.bbps_mock.registry import BILLERS, Biller
from app.schemas import BillerCategory


class Bill(BaseModel):
    model_config = ConfigDict(frozen=True)

    biller_id: str
    consumer_number: str
    consumer_name: str
    bill_number: str
    period_start: date
    period_end: date
    bill_date: date
    due_date: date
    amount: float  # INR


CURRENT = (2026, 10)
HISTORY_MONTHS = 6
CONSUMERS_PER_BILLER = 5

# The spike's Demo Power bill must stay exactly as rendered in api/spike/inputs.
FIXED_CONSUMER = ("DEMO00000MAH01", "DP-4410-882761")
FIXED_CURRENT = {
    "consumer_name": "Sample Consumer",
    "bill_number": "DPB/2026/10/558213",
    "bill_date": date(2026, 10, 12),
    "due_date": date(2026, 11, 5),
    "amount": 1240.00,
}

# First consumer of these billers gets a current bill far above their history.
SPIKE_FACTORS = {"EBNL00000UTP01": 3.4, "DGAS00000GUJ01": 2.8}

_RANGES: dict[BillerCategory, tuple[int, int]] = {
    BillerCategory.ELECTRICITY: (700, 2200),
    BillerCategory.WATER: (180, 650),
    BillerCategory.GAS: (380, 950),
}
_PLANS: dict[BillerCategory, tuple[int, ...]] = {
    BillerCategory.MOBILE_POSTPAID: (399, 599, 799, 999),
    BillerCategory.DTH: (299, 399, 499, 599),
    BillerCategory.BROADBAND: (699, 899, 999, 1199),
}
# Electricity usage is higher in summer (Apr-Jun).
_SEASON = {4: 1.15, 5: 1.35, 6: 1.30, 7: 1.05, 8: 1.0, 9: 1.05, 10: 1.0}


def _digits(rng: random.Random, n: int, first: str = "123456789") -> str:
    return rng.choice(first) + "".join(rng.choice("0123456789") for _ in range(n - 1))


_CONSUMER_MAKERS: dict[str, Callable[[random.Random], str]] = {
    "DEMO00000MAH01": lambda r: f"DP-{_digits(r, 4)}-{_digits(r, 6)}",
    "SVSL00000TEL01": lambda r: f"SVS{_digits(r, 9)}",
    "EBNL00000UTP01": lambda r: _digits(r, 10, first="12345"),  # never looks like a mobile number
    "EJBD00000DEL01": lambda r: f"EJB{_digits(r, 8)}",
    "DGAS00000GUJ01": lambda r: f"BP{_digits(r, 8)}",
    "DMOB00000NAT01": lambda r: f"DM{_digits(r, 9)}",
    "SKYD00000NAT01": lambda r: f"SD{_digits(r, 9)}",
    "FIBR00000KAR01": lambda r: f"FD{_digits(r, 8)}",
}


def _months() -> list[tuple[int, int]]:
    """Billing months, oldest first; the last one is the current bill."""
    year, month = CURRENT
    out = []
    for back in range(HISTORY_MONTHS, -1, -1):
        m = month - back
        y = year + (m - 1) // 12
        out.append((y, (m - 1) % 12 + 1))
    return out


def _amounts(biller: Biller, rng: random.Random, spike: float | None) -> list[float]:
    months = _months()
    if biller.category in _PLANS:
        plan = rng.choice(_PLANS[biller.category])
        amounts = [plan + rng.choice((0, 0, 0, 18, 49)) for _ in months]
    else:
        lo, hi = _RANGES[biller.category]
        base = rng.uniform(lo, hi)
        amounts = []
        for _, m in months:
            season = _SEASON.get(m, 1.0) if biller.category == BillerCategory.ELECTRICITY else 1.0
            amounts.append(round(base * season * rng.uniform(0.92, 1.08)))
    if spike:
        amounts[-1] = round(statistics.median(amounts[:-1]) * spike)
    return [float(a) for a in amounts]


def _generate() -> dict[tuple[str, str], list[Bill]]:
    bills: dict[tuple[str, str], list[Bill]] = {}
    for b_index, biller in enumerate(BILLERS):
        rng = random.Random(f"bbps-mock-{biller.biller_id}")
        for c_index in range(CONSUMERS_PER_BILLER):
            consumer = _CONSUMER_MAKERS[biller.biller_id](rng)
            if (biller.biller_id, c_index) == (FIXED_CONSUMER[0], 0):
                consumer = FIXED_CONSUMER[1]
            spike = SPIKE_FACTORS.get(biller.biller_id) if c_index == 0 else None
            amounts = _amounts(biller, rng, spike)
            if (
                biller.biller_id,
                consumer,
            ) == FIXED_CONSUMER:  # history scaled around the fixed bill
                scale = FIXED_CURRENT["amount"] / amounts[-1]
                amounts = [float(round(a * scale)) for a in amounts]
            name = f"Sample Consumer {'ABCDE'[c_index]}"
            history = []
            for (y, m), amount in zip(_months(), amounts, strict=True):
                period_start = date(y, m, 1) - timedelta(days=1)
                period_start = period_start.replace(day=1)
                period_end = date(y, m, 1) - timedelta(days=1)
                bill_date = date(y, m, 5 + b_index)
                history.append(
                    Bill(
                        biller_id=biller.biller_id,
                        consumer_number=consumer,
                        consumer_name=name,
                        bill_number=f"{biller.biller_id[:4]}/{y}/{m:02d}/{rng.randint(100000, 999999)}",
                        period_start=period_start,
                        period_end=period_end,
                        bill_date=bill_date,
                        due_date=bill_date + timedelta(days=21),
                        amount=amount,
                    )
                )
            if (biller.biller_id, consumer) == FIXED_CONSUMER:
                history[-1] = history[-1].model_copy(update=FIXED_CURRENT)
            bills[(biller.biller_id, consumer)] = history
    return bills


BILLS = _generate()
