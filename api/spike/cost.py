"""Running API cost for the spike, persisted across runs, with a hard budget guard.

Prices are USD per 1M tokens (dev.meta.ai Models page, 2026-10-27). Cached-input
discounts are ignored, so estimates err high. Models without a listed token price
(e.g. Baseten) use a deliberately high ASSUMED price so the guard stops early.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Price:
    input_per_m: float
    output_per_m: float
    assumed: bool = False


ASSUMED = Price(input_per_m=5.0, output_per_m=20.0, assumed=True)

_SPARK = Price(input_per_m=1.25, output_per_m=4.25)
PRICES: dict[str, Price] = {
    "muse-spark-1.3": _SPARK,
    "muse-spark-1.1": _SPARK,
    "muse-wonder-1.0": Price(input_per_m=4.00, output_per_m=20.00),
}

# Non-token pricing, USD per unit.
SAM_PER_IMAGE = 2.50 / 1000
TRANSCRIBE_PER_SECOND = 0.18 / 3600


class BudgetExceeded(RuntimeError):
    pass


class CostMeter:
    def __init__(self, ledger: Path, budget_usd: float = 5.0):
        self.ledger = ledger
        self.budget_usd = budget_usd
        self.spent_usd = 0.0
        if ledger.exists():
            self.spent_usd = json.loads(ledger.read_text(encoding="utf-8"))["spent_usd"]

    @staticmethod
    def price(model: str) -> Price:
        return PRICES.get(model, ASSUMED)

    def estimate(self, model: str, input_tokens: int, output_tokens: int) -> float:
        p = self.price(model)
        return (input_tokens * p.input_per_m + output_tokens * p.output_per_m) / 1_000_000

    def check(self, model: str, est_input_tokens: int, max_output_tokens: int) -> None:
        """Refuse a call whose worst case would take total spend past the budget."""
        worst = self.estimate(model, est_input_tokens, max_output_tokens)
        if self.spent_usd + worst > self.budget_usd:
            raise BudgetExceeded(
                f"spent ${self.spent_usd:.4f}; next call could cost up to ${worst:.4f}; "
                f"budget ${self.budget_usd:.2f}"
            )

    def check_flat(self, cost: float) -> None:
        if self.spent_usd + cost > self.budget_usd:
            raise BudgetExceeded(f"spent ${self.spent_usd:.4f}; next call costs ${cost:.4f}")

    def record_flat(self, cost: float) -> float:
        """Record a non-token charge (SAM per image, transcription per second)."""
        return self._add(cost)

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        return self._add(self.estimate(model, input_tokens, output_tokens))

    def _add(self, cost: float) -> float:
        self.spent_usd += cost
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps({"spent_usd": self.spent_usd}), encoding="utf-8")
        return cost
