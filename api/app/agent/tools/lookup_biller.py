"""lookup_biller: find a biller in the (MOCK) BBPS registry by the name written in the message."""

import difflib
import re
import unicodedata

from pydantic import BaseModel, Field

from app.agent.tools.base import Finding, Outcome, define_tool
from app.bbps_mock import service
from app.bbps_mock.registry import Biller
from app.schemas import BillerCategory, EvidenceCode

MATCH_THRESHOLD = 0.85
AMBIGUITY_MARGIN = 0.05
_STOPWORDS = {"ltd", "limited", "co", "company", "pvt", "private", "the", "of", "and"}


class Args(BaseModel):
    name: str | None = Field(description="Biller name exactly as written in the bill or message")
    category: BillerCategory | None = Field(default=None, description="Biller category, if known")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = re.sub(r"[^\w\s]", " ", text).split()
    return " ".join(t for t in tokens if t not in _STOPWORDS)


def _score(query: str, biller: Biller) -> float:
    q = _norm(query)
    best = 0.0
    for alias in (biller.name, *biller.aliases):
        a = _norm(alias)
        if not a:
            continue
        if q == a or q.replace(" ", "") == a.replace(" ", ""):
            return 1.0
        if len(a) >= 5 and (f" {a} " in f" {q} "):  # full alias inside a longer name
            best = max(best, 0.95)
        best = max(
            best,
            difflib.SequenceMatcher(None, q, a).ratio(),
            difflib.SequenceMatcher(None, q.replace(" ", ""), a.replace(" ", "")).ratio(),
        )
    return best


@define_tool(
    "lookup_biller",
    "Look up a biller in the BBPS biller registry (mock) by the name written in the message. "
    "Returns the official biller_id and its official payment channels, or UNKNOWN_BILLER.",
    Args,
)
def lookup_biller(args: Args) -> Outcome:
    if not args.name or not args.name.strip():
        return Outcome(
            [Finding(EvidenceCode.UNKNOWN_BILLER, "No biller name was found in the message.")],
            {"matched": False},
        )
    scored = sorted(
        ((_score(args.name, b), b) for b in service.list_billers()),
        key=lambda x: x[0],
        reverse=True,
    )
    candidates = [
        {"biller_id": b.biller_id, "name": b.name, "score": round(s, 3)} for s, b in scored[:3]
    ]
    in_category = [
        (s, b) for s, b in scored if args.category is None or b.category == args.category
    ]
    best_score, best = in_category[0] if in_category else (0.0, None)
    runner_up = in_category[1][0] if len(in_category) > 1 else 0.0

    if best is None or best_score < MATCH_THRESHOLD:
        note = "No registered biller matches this name"
        if args.category is not None and scored[0][0] >= MATCH_THRESHOLD:
            note += f" in category {args.category.value} (closest is {scored[0][1].name}, {scored[0][1].category.value})"
        return Outcome(
            [Finding(EvidenceCode.UNKNOWN_BILLER, f"{note}.", {"query": args.name})],
            {"matched": False, "candidates": candidates},
        )
    if best_score - runner_up < AMBIGUITY_MARGIN and best_score < 1.0:
        return Outcome(
            [
                Finding(
                    EvidenceCode.UNKNOWN_BILLER,
                    "The name matches more than one registered biller.",
                    {"query": args.name},
                )
            ],
            {"matched": False, "candidates": candidates},
        )
    return Outcome(
        [
            Finding(
                EvidenceCode.BILLER_VERIFIED,
                f"Registered biller {best.name} ({best.biller_id}).",
                {"biller_id": best.biller_id, "score": round(best_score, 3)},
            )
        ],
        {
            "matched": True,
            "biller_id": best.biller_id,
            "official_name": best.name,
            "category": best.category.value,
            "official_domains": list(best.official_domains),
            "official_vpas": list(best.official_vpas),
            "official_phones": list(best.official_phones),
            "candidates": candidates,
        },
    )
