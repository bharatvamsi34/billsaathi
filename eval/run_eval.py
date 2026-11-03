"""Run the real pipeline over the held-out TEST split and write one results file per config.

Run from api/ (spends real money; each config stops at --budget):
  .venv\\Scripts\\python ..\\eval\\run_eval.py spark-low
  .venv\\Scripts\\python ..\\eval\\run_eval.py spark-minimal spark-medium spark-high open

Every item goes through the same code as the live app: SAM (Meta configs only), extraction,
milestone check, mandatory checks, agent, deterministic checks and judge. Nobody answers the
agent's question, so a question ends as "no answer" (forced CAUTION or the floor), as it would
for a user who walks away. Prompts and rules were tuned on the dev split only.
"""

import argparse
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import pipeline, voice  # noqa: E402
from app.api.store import CheckState, SpendMeter  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models.meta import MetaClient  # noqa: E402
from app.models.openweight import MODEL_LABEL, privacy_client  # noqa: E402
from app.schemas import Label  # noqa: E402
from app.vision import MetaSam  # noqa: E402

DATA = ROOT / "data" / "synthetic"
RESULTS = ROOT / "eval" / "results"
CONFIGS = {
    "spark-minimal": ("muse-spark-1.3", "minimal"),
    "spark-low": ("muse-spark-1.3", "low"),
    "spark-medium": ("muse-spark-1.3", "medium"),
    "spark-high": ("muse-spark-1.3", "high"),
    "open": (MODEL_LABEL, "default"),
    "judge-minimal": ("muse-spark-1.3", "low"),  # only used on the dev split, to choose the judge
    "all-minimal": ("muse-spark-1.3", "minimal"),  # dev split: reading, agent and judge at minimal
}


def clients_for(name: str) -> pipeline.Clients:
    settings = get_settings()
    settings.model_timeout_seconds = 90.0  # higher effort is slower; a timeout is not a finding
    model, effort = CONFIGS[name]
    if name == "open":
        c = privacy_client(settings)
        return pipeline.Clients(extract=c, agent=c, judge=c, model=model, privacy=True)
    meta = MetaClient(settings, timeout_s=90.0)
    return pipeline.Clients(
        extract=meta,
        agent=meta,
        judge=meta,
        # The explanation is not graded; only the product config pays for it, to report its cost.
        explain=meta if name == "spark-low" else None,
        speech=voice.MetaSpeech(settings),
        sam=MetaSam(settings),
        model=model,
        effort=effort,
        judge_effort="minimal" if name in ("judge-minimal", "all-minimal", "spark-low") else "low",
    )


def run_item(label: Label, clients: pipeline.Clients) -> dict:
    lang = label.expected.extracted.languages[0]
    if lang not in ("en", "te", "hi"):
        lang = "en"
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
    if asked:
        pipeline.answer(state, "", spend)  # nobody answers: no answer ends the run
    wall = time.perf_counter() - t0
    events = state.events_after(-1)
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    end = next(e for e in reversed(events) if e["type"] == "complete")
    codes = sorted({ev["code"] for e in events if e["type"] == "check" for ev in e["evidence"]})
    agent = end.get("agent") or {}
    return {
        "id": label.id,
        "split": label.split,
        "scenario": label.scenario,
        "lang": lang,
        "kind": label.input.kind,
        "expected": label.expected.verdict.value,
        "got": verdict["verdict"],
        "forced": verdict["forced"],
        "forced_reason": verdict.get("forced_reason"),
        "asked_user": asked,
        "expected_codes": [e.code.value for e in label.expected.evidence],
        "codes": codes,
        "latency_s": round(end["timings_ms"]["total"] / 1000, 2),
        "wall_s": round(wall, 2),
        "timings_ms": end["timings_ms"],
        "cost_usd": end["cost_usd"]["total"],
        "costs": end["cost_usd"],
        "turns": agent.get("model_turns"),
        "judge_calls": agent.get("judge_calls"),
        "refusals": agent.get("refusals"),
    }


def run_config(name: str, labels: list[Label], budget: float, workers: int, split: str) -> None:
    clients = clients_for(name)
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{split}_{name}_{datetime.now():%Y-%m-%d_%H%M}.jsonl"
    spent, right, done = 0.0, 0, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(lambda lbl: run_item(lbl, clients), labels):
            with out.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            spent += row["cost_usd"]
            done += 1
            right += row["got"] == row["expected"]
            mark = "ok " if row["got"] == row["expected"] else "XX "
            print(f"{mark}{name} {row['id']:<36} exp {row['expected']:<7} got {row['got']:<7} {row['latency_s']:>5}s ${row['cost_usd']:.4f}", flush=True)  # fmt: skip
            if spent > budget:
                raise SystemExit(f"budget ${budget} passed at ${spent:.2f}: stopping, results kept")
    print(f"== {name}: {right}/{done} correct, ${spent:.3f}, results {out.name}", flush=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    ap.add_argument("configs", nargs="+", choices=sorted(CONFIGS))
    ap.add_argument("--budget", type=float, default=2.5, help="USD per config")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--split", choices=["test", "dev"], default="test")
    args = ap.parse_args()
    lines = (DATA / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    labels = [lbl for lbl in map(Label.model_validate_json, lines) if lbl.split == args.split]
    print(f"{len(labels)} {args.split} items", flush=True)
    for name in args.configs:
        run_config(name, labels, args.budget, args.workers, args.split)


if __name__ == "__main__":
    main()
