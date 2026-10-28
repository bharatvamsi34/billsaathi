"""Checked facts that may be shown to users. Never take such facts from model output.

A fact is usable only once a person has checked it against its source and filled in
verified_by / verified_on. The agent's submit_verdict refuses unverified facts (Day 3).
"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    value: str
    label: str
    source: str
    verified_by: str | None = None
    verified_on: date | None = None

    @property
    def verified(self) -> bool:
        return self.verified_by is not None and self.verified_on is not None


FACTS: dict[str, Fact] = {
    f.key: f
    for f in (
        Fact(
            key="cybercrime_helpline",
            value="1930",
            label="National Cyber Crime Helpline (India)",
            source="MHA / cybercrime.gov.in",
            verified_by="BV",
            verified_on=date(2026, 10, 28),
        ),
        Fact(
            key="cybercrime_portal",
            value="https://cybercrime.gov.in",
            label="National Cybercrime Reporting Portal (India)",
            source="MHA / cybercrime.gov.in",
            verified_by="BV",
            verified_on=date(2026, 10, 28),
        ),
    )
}


def verified_fact(key: str) -> Fact | None:
    fact = FACTS.get(key)
    return fact if fact is not None and fact.verified else None
