"""End-to-end check against a deployed BillSaathi API: upload one image, follow the live
event stream, then read the result. Prints each step and the total time and cost.

  .venv\\Scripts\\python scripts\\e2e_check.py https://<app>.azurecontainerapps.io ..\\data\\synthetic\\images\\bill_genuine_demo.png
"""

import json
import mimetypes
import sys
import time
from pathlib import Path

import httpx


def main(base: str, image: Path, language: str = "en") -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    base = base.rstrip("/")
    t0 = time.perf_counter()
    with httpx.Client(timeout=120) as client:
        files = {"image": (image.name, image.read_bytes(), mimetypes.guess_type(image.name)[0])}
        r = client.post(f"{base}/api/v1/checks", files=files, data={"language": language})
        print(f"POST /api/v1/checks -> {r.status_code} {r.json()}")
        r.raise_for_status()
        check_id = r.json()["check_id"]
        with client.stream("GET", f"{base}/api/v1/checks/{check_id}/events") as stream:
            for line in stream.iter_lines():
                if not line.startswith("data: "):
                    continue
                e = json.loads(line[6:])
                at = time.perf_counter() - t0
                detail = {
                    "extracted": lambda: (
                        f"biller={e['fields']['biller_name']['value']} amount={e['fields']['amount']['value']} ({e['latency_ms']} ms)"
                    ),
                    "check": lambda: (
                        f"[{e['origin']}] {e['tool']} -> {[x['code'] for x in e['evidence']]}"
                    ),
                    "agent_turn": lambda: (
                        f"turn {e['turn']} calls={e['tool_calls']} ({e['latency_ms']} ms)"
                    ),
                    "judge": lambda: f"accepted={e['accepted']}",
                    "verdict": lambda: (
                        f"{e['verdict']} forced={e['forced']} reasons={[x['text'] for x in e['reasons']]}"
                    ),
                    "complete": lambda: f"timings={e['timings_ms']} cost={e['cost_usd']}",
                }.get(e["type"], lambda: "")()
                print(f"{at:6.1f}s  {e['type']:<20} {detail}")
        result = client.get(f"{base}/api/v1/checks/{check_id}").json()
    total = time.perf_counter() - t0
    print(
        f"\nverdict {result['verdict']['verdict']} · wall time {total:.1f}s "
        f"(server: extraction {result['timings_ms']['extraction'] / 1000:.1f}s, "
        f"agent {result['timings_ms']['agent'] / 1000:.1f}s, total {result['timings_ms']['total'] / 1000:.1f}s) · "
        f"cost ${result['cost_usd']['total']:.4f} "
        f"(extraction ${result['cost_usd']['extraction']:.4f}, agent ${result['cost_usd']['agent']:.4f})"
    )


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]), *(sys.argv[3:4]))
