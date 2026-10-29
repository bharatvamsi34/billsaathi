"""Run the verification agent live over labelled dataset items and report a table.

Run from api/:
  .venv\\Scripts\\python -m app.agent.cli                      (10 default dev items)
  .venv\\Scripts\\python -m app.agent.cli --ids reminder_en_demo,scam_te_known_vpa
  .venv\\Scripts\\python -m app.agent.cli --split dev --limit 20

Starts from each item's ground-truth fields, so this measures the agent alone (image
extraction excluded). Stops before the next item once --budget (USD) is spent.
"""

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

from app.agent.loop import start
from app.agent.protocol import AgentInput
from app.config import get_settings
from app.models.meta import MetaClient
from app.schemas import Label

ROOT = Path(__file__).resolve().parents[3]
LABELS_FILE = ROOT / "data" / "synthetic" / "labels.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"

# 3 SAFE / 3 CAUTION / 4 SCAM across EN, TE, HI; all from the dev split.
DEFAULT_IDS = [
    "reminder_en_demo",
    "reminder_te_svsl_short",
    "reminder_hi_fibr_polite_disconnect",
    "bill_tampered_demo",
    "bill_spike_ebnl",
    "edge_en_unknown_biller",
    "scam_te_known_vpa",
    "scam_hi_kyc_apk",
    "scam_en_fake_bill_vpa",
    "bill_swapped_vpa_dgas",
]
TARGET_TURNS, TARGET_SECONDS = 3, 10.0


def load_labels() -> dict[str, Label]:
    lines = LABELS_FILE.read_text(encoding="utf-8").splitlines()
    return {lbl.id: lbl for lbl in map(Label.model_validate_json, lines)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--ids", default="", help="comma-separated label ids (default: 10 dev items)")
    ap.add_argument("--split", choices=["dev", "test"], default=None)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--budget", type=float, default=1.0, help="stop once this many USD are spent")
    args = ap.parse_args()

    labels = load_labels()
    if args.ids:
        chosen = [labels[i] for i in args.ids.split(",")]
    elif args.split:
        chosen = [lbl for lbl in labels.values() if lbl.split == args.split][: args.limit]
    else:
        chosen = [labels[i] for i in DEFAULT_IDS]

    client = MetaClient(get_settings())
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"agent_live_{datetime.now():%Y-%m-%d_%H%M}.jsonl"
    rows, spent = [], 0.0
    for label in chosen:
        if spent >= args.budget:
            print(f"budget ${args.budget:.2f} reached; stopping")
            break
        agent_input = AgentInput.from_fields(
            label.expected.extracted,
            raw_text=label.input.text,
            language=label.expected.extracted.languages[0],
        )
        session = start(client, agent_input, run_id=label.id)
        m, final = session.metrics, session.final
        spent += m.cost_usd
        row = {
            "id": label.id,
            "split": label.split,
            "lang": agent_input.language,
            "expected": label.expected.verdict.value,
            "got": final.verdict.value if final else session.status,
            "forced": bool(final and final.forced),
            "forced_reason": final.forced_reason if final else None,
            "turns": m.model_turns,
            "judge_calls": m.judge_calls,
            "tool_calls": m.tool_calls,
            "refusals": [e.payload["rule"] for e in session.record.entries if e.kind == "refusal"],
            "latency_s": round(m.latency_ms / 1000, 2),
            "cost_usd": round(m.cost_usd, 5),
            "input_tokens": m.input_tokens,
            "output_tokens": m.output_tokens,
            "reasons": [r.text for r in final.reasons] if final else [],
        }
        rows.append(row)
        with out_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        ok = "✓" if row["got"] == row["expected"] else "✗"
        print(
            f"{ok} {row['id']:<38} {row['lang']}  exp {row['expected']:<7} got {row['got']:<7} "
            f"turns {row['turns']} judge {row['judge_calls']} tools {row['tool_calls']} "
            f"refusals {len(row['refusals'])}  {row['latency_s']:>5.1f}s  ${row['cost_usd']:.4f}"
            + ("  FORCED: " + row["forced_reason"] if row["forced"] else "")
        )
    if not rows:
        return
    correct = sum(r["got"] == r["expected"] for r in rows)
    false_safe = sum(r["got"] == "SAFE" and r["expected"] != "SAFE" for r in rows)
    on_target = sum(r["turns"] <= TARGET_TURNS and r["latency_s"] <= TARGET_SECONDS for r in rows)
    print(
        f"\n{correct}/{len(rows)} correct · false SAFE {false_safe} · "
        f"median turns {statistics.median(r['turns'] for r in rows)} · "
        f"median latency {statistics.median(r['latency_s'] for r in rows):.1f}s · "
        f"on target (≤{TARGET_TURNS} turns, ≤{TARGET_SECONDS:.0f}s) {on_target}/{len(rows)} · "
        f"total ${spent:.4f}\nresults: {out_path}"
    )


if __name__ == "__main__":
    main()
