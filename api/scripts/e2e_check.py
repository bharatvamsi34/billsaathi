"""End-to-end checks against a deployed BillSaathi API: upload images, follow the live event
stream, read each result. One image prints every step; several print one line each plus the
median and p90 of extraction, agent and total time.

  .venv\\Scripts\\python scripts\\e2e_check.py https://<app>.azurecontainerapps.io img1.png [img2.png ...]
"""

import argparse
import json
import math
import mimetypes
import statistics
import sys
import time
from pathlib import Path

import httpx


def describe(e: dict) -> str:
    kind = e["type"]
    if kind == "extracted":
        f = e["fields"]
        return f"biller={f['biller_name']['value']} amount={f['amount']['value']} ({e['latency_ms']} ms)"
    if kind == "check":
        return f"[{e['origin']}] {e['tool']} -> {[x['code'] for x in e['evidence']]}"
    if kind == "agent_turn":
        return f"turn {e['turn']} calls={e['tool_calls']} ({e['latency_ms']} ms)"
    if kind == "judge":
        return f"accepted={e['accepted']}"
    if kind == "verdict":
        return f"{e['verdict']} forced={e['forced']} reasons={[x['text'] for x in e['reasons']]}"
    if kind == "complete":
        return f"timings={e['timings_ms']} cost={e['cost_usd']}"
    return ""


def run_one(client: httpx.Client, base: str, image: Path, language: str, verbose: bool) -> dict:
    t0 = time.perf_counter()
    files = {"image": (image.name, image.read_bytes(), mimetypes.guess_type(image.name)[0])}
    r = client.post(f"{base}/api/v1/checks", files=files, data={"language": language})
    r.raise_for_status()
    check_id = r.json()["check_id"]
    with client.stream("GET", f"{base}/api/v1/checks/{check_id}/events") as stream:
        for line in stream.iter_lines():
            if verbose and line.startswith("data: "):
                e = json.loads(line[6:])
                print(f"{time.perf_counter() - t0:6.1f}s  {e['type']:<20} {describe(e)}")
    result = client.get(f"{base}/api/v1/checks/{check_id}").json()
    return {
        "image": image.name,
        "verdict": result["verdict"]["verdict"],
        "forced": result["verdict"]["forced"],
        "extraction_s": result["timings_ms"]["extraction"] / 1000,
        "agent_s": result["timings_ms"]["agent"] / 1000,
        "total_s": result["timings_ms"]["total"] / 1000,
        "wall_s": time.perf_counter() - t0,
        "cost": result["cost_usd"]["total"],
        "turns": result["agent"]["model_turns"] if result["agent"] else 0,
        "refusals": result["agent"]["refusals"] if result["agent"] else 0,
    }


def p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.9 * len(ordered)) - 1)]  # nearest-rank


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("base")
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--language", default="en")
    args = ap.parse_args()
    verbose = len(args.images) == 1
    rows = []
    with httpx.Client(timeout=120) as client:
        for image in args.images:
            row = run_one(client, args.base.rstrip("/"), image, args.language, verbose)
            rows.append(row)
            print(
                f"{row['image']:<36} {row['verdict']:<8}{' (forced)' if row['forced'] else ''} "
                f"extraction {row['extraction_s']:5.1f}s  agent {row['agent_s']:5.1f}s  "
                f"total {row['total_s']:5.1f}s  wall {row['wall_s']:5.1f}s  "
                f"turns {row['turns']} refusals {row['refusals']}  ${row['cost']:.4f}"
            )
    if len(rows) > 1:
        for key in ("extraction_s", "agent_s", "total_s"):
            values = [r[key] for r in rows]
            print(
                f"{key[:-2]:<11} median {statistics.median(values):5.1f}s  p90 {p90(values):5.1f}s"
            )
        print(f"cost total ${sum(r['cost'] for r in rows):.4f}")


if __name__ == "__main__":
    main()
