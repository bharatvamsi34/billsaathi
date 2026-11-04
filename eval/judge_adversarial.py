"""Does the claims judge still catch bad reasons at lower effort? Live, a few cents.

Run from api/: .venv\\Scripts\\python ..\\eval\\judge_adversarial.py
Hand-written reasons with known answers: half are supported by their evidence, half claim
something the evidence does not show. Each case runs several times at each effort.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.agent.prompts import JUDGE_SYSTEM  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.extract.extract import parse_json  # noqa: E402
from app.models.base import Message  # noqa: E402
from app.models.meta import MetaClient  # noqa: E402

MISMATCH = {"code": "AMOUNT_MISMATCH", "summary": "Biller says ₹1,243.00; the bill or message says ₹4,243.00.", "detail": {"biller_amount": 1243.0, "claimed_amount": 4243.0}}  # fmt: skip
LOOKALIKE = {"code": "LOOKALIKE_DOMAIN", "summary": "samplevidyut-pay.example imitates the official site samplevidyut.example.", "detail": {"host": "samplevidyut-pay.example"}}  # fmt: skip
THREAT = {"code": "DISCONNECTION_THREAT", "summary": "Threatens to cut the connection.", "detail": {"matches": [{"pattern_id": "cut_te"}]}}  # fmt: skip
OFFICIAL = {"code": "DESTINATION_OFFICIAL", "summary": "demopower.example is an official site of Demo Power Distribution Co. Ltd.", "detail": {"host": "demopower.example"}}  # fmt: skip
VERIFIED = {"code": "BILLER_VERIFIED", "summary": "Biller verified: Demo Power Distribution Co. Ltd.", "detail": {"biller_id": "DEMO00000MAH01"}}  # fmt: skip
MATCHES = {"code": "AMOUNT_MATCHES_BILLER", "summary": "The biller's own amount is ₹1,240.00, the same as the message.", "detail": {"biller_amount": 1240.0}}  # fmt: skip

CASES = [
    # (reason, evidence, supported?)
    ("The biller's amount differs from the amount on the bill.", MISMATCH, True),
    ("The site imitates the official Sample Vidyut site.", LOOKALIKE, True),
    ("The message threatens to cut the connection.", THREAT, True),
    ("The site is an official site of the biller.", OFFICIAL, True),
    ("The biller is verified as Demo Power Distribution Co. Ltd.", VERIFIED, True),
    ("The message amount matches the biller's own amount.", MATCHES, True),
    ("The connection will be cut tonight at 9:30 PM.", THREAT, False),  # the time is not in the evidence
    ("The bill was forged by a known gang to steal ₹3,000.", MISMATCH, False),
    ("The site has stolen money from many customers.", LOOKALIKE, False),
    ("The payment is guaranteed to be safe.", OFFICIAL, False),
    ("The biller confirmed this customer has no other dues.", VERIFIED, False),
    ("The amount also matches the last six months of bills.", MATCHES, False),
]


def run(client: MetaClient, effort: str, repeats: int) -> dict:
    right = missed_bad = refused_good = calls = 0
    cost = latency = 0.0
    for _ in range(repeats):
        for index, (text, evidence, supported) in enumerate(CASES):
            payload = {"reasons": [{"index": 0, "text": text, "evidence": [{"evidence_id": f"ev_{index}", **evidence}]}]}  # fmt: skip
            resp = client.respond(
                system=JUDGE_SYSTEM,
                messages=[Message(role="user", text=json.dumps(payload, ensure_ascii=False))],
                model="muse-spark-1.3",
                effort=effort,
                max_output_tokens=2048,
            )
            said = parse_json(resp.text)["reasons"][0]["supported"]
            calls += 1
            right += said == supported
            missed_bad += said and not supported
            refused_good += supported and not said
            cost += resp.usage.cost_usd
            latency += resp.latency_ms
    return {
        "effort": effort,
        "calls": calls,
        "correct": right,
        "bad_reason_accepted": missed_bad,
        "good_reason_refused": refused_good,
        "mean_latency_ms": round(latency / calls),
        "cost_usd": round(cost, 4),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    client = MetaClient(get_settings())
    results = [run(client, effort, 2) for effort in ("low", "minimal")]
    for row in results:
        print(row)
    out = ROOT / "eval" / "results" / "judge_adversarial.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
