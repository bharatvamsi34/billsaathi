"""Run the frozen challenge set ONCE on the product config. Refuses to run twice.

Run: api/.venv/Scripts/python eval/run_challenge.py   (live, about $0.60). See data/challenge/FROZEN.md.
"""

import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "eval"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "api" / ".env")
import run_eval  # noqa: E402

from app import pipeline  # noqa: E402
from app.api.store import CheckState, SpendMeter  # noqa: E402
from app.schemas import Label  # noqa: E402

DATA = ROOT / "data" / "challenge"
OUT = ROOT / "eval" / "results" / f"challenge_{date.today():%Y-%m-%d}.json"
BUDGET = 2.0


def run_item(label: Label, clients: pipeline.Clients) -> dict:
    lang = label.expected.extracted.languages[0]
    lang = lang if lang in ("en", "te", "hi") else "en"
    check = pipeline.CheckInput(language=lang)
    if label.input.kind == "image":
        path = DATA / label.input.path
        check.image = path.read_bytes()
        check.image_mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    else:
        check.text = label.input.text
    state = CheckState(check_id=uuid.uuid4().hex, language=lang, input_kind=label.input.kind)
    spend = SpendMeter(1000)
    t0 = time.perf_counter()
    pipeline.run_check(state, check, clients, spend)
    asked = state.status == "needs_user_input"
    if asked:  # same rule as the evaluation: nobody answers, so no answer ends the run
        pipeline.answer(state, "", spend)
    events = state.events_after(-1)
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    end = next(e for e in reversed(events) if e["type"] == "complete")
    read = next((e for e in events if e["type"] == "extracted"), {})
    codes = sorted({ev["code"] for e in events if e["type"] == "check" for ev in e["evidence"]})
    agent = end.get("agent") or {}
    expected_codes = [e.code.value for e in label.expected.evidence]
    return {
        "id": label.id,
        "scenario": label.scenario,
        "lang": lang,
        "kind": label.input.kind,
        "expected": label.expected.verdict.value,
        "got": verdict["verdict"],
        "correct": verdict["verdict"] == label.expected.verdict.value,
        "forced": verdict["forced"],
        "forced_reason": verdict.get("forced_reason"),
        "asked_user": asked,
        "expected_codes": expected_codes,
        "codes": codes,
        "missing_codes": sorted(set(expected_codes) - set(codes)),
        "reasons": [r["text"] for r in verdict["reasons"]],
        "read": {k: read.get(k) for k in ("biller_name", "category", "consumer", "amount", "destinations") if k in read},
        "turns": agent.get("model_turns"),
        "refusals": agent.get("refusals"),
        "seconds_to_verdict": round(end["timings_ms"]["total"] / 1000, 1),
        "cost_usd": end["cost_usd"]["total"],
    }  # fmt: skip


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if OUT.exists():
        raise SystemExit(f"{OUT.name} exists: the challenge set runs once.")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()  # fmt: skip
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "api", "data/challenge", "eval/run_challenge.py"], capture_output=True, text=True, cwd=ROOT).stdout.strip()  # fmt: skip
    if dirty:
        raise SystemExit(
            f"uncommitted changes, so the commit would not describe this run:\n{dirty}"
        )
    lines = (DATA / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    labels = [Label.model_validate_json(line) for line in lines]
    clients = run_eval.clients_for("spark-low")
    rows, spent = [], 0.0
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row in pool.map(lambda lbl: run_item(lbl, clients), labels):
            rows.append(row)
            spent += row["cost_usd"]
            mark = "ok " if row["correct"] else "XX "
            print(f"{mark}{row['id']:<34} exp {row['expected']:<7} got {row['got']:<7} {row['seconds_to_verdict']:>5}s ${row['cost_usd']:.4f}", flush=True)  # fmt: skip
            if spent > BUDGET:
                print("budget passed: stopping, results kept", flush=True)
                break
    OUT.write_text(
        json.dumps(
            {
                "commit": commit,
                "model": clients.model,
                "effort": clients.effort,
                "judge_effort": clients.judge_effort,
                "n": len(rows),
                "correct": sum(r["correct"] for r in rows),
                "cost_usd": round(spent, 4),
                "rows": rows,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"{sum(r['correct'] for r in rows)}/{len(rows)} correct, ${spent:.3f}, {OUT.name}",
        flush=True,
    )


if __name__ == "__main__":
    main()
