"""Build the numbers behind the /eval page from the results files in eval/results.

Run: python eval/report.py (no API calls). Uses the latest file of each config, keeps only
complete runs of the test split, and writes web/src/eval.generated.json.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from metrics import by, confusion, medians, summarise

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"
OUT = ROOT / "web" / "src" / "eval.generated.json"
ORDER = ["spark-minimal", "spark-low", "spark-medium", "spark-high", "open"]
TITLES = {
    "spark-minimal": "Spark 1.3, minimal",
    "spark-low": "Spark 1.3, low (the product)",
    "spark-medium": "Spark 1.3, medium",
    "spark-high": "Spark 1.3, high",
    "open": "Muse Spark Open (Privacy Mode)",
}


def latest(config: str) -> Path | None:
    files = sorted(RESULTS.glob(f"test_{config}_*.jsonl"))
    return files[-1] if files else None


def main() -> None:
    n_test = sum(
        json.loads(line)["split"] == "test"
        for line in (ROOT / "data" / "synthetic" / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    )  # fmt: skip
    configs = {}
    for name in ORDER:
        path = latest(name)
        if path is None:
            continue
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert all(r["split"] == "test" for r in rows), f"{path.name} has non-test items"
        if len(rows) != n_test:
            print(f"skipping {path.name}: {len(rows)} of {n_test} items")
            continue
        configs[name] = {
            "title": TITLES[name],
            "file": f"eval/results/{path.name}",
            "date": re.search(r"(\d{4}-\d{2}-\d{2})", path.name).group(1),
            **summarise(rows),
            "turns_median": medians(rows, "turns"),
            "forced": sum(r["forced"] for r in rows),
            "asked_user": sum(r["asked_user"] for r in rows),
            "by_language": by(rows, "lang"),
            "by_kind": by(rows, "kind"),
            "by_expected": by(rows, "expected"),
            "confusion": confusion(rows),
            "misses": [
                {k: r[k] for k in ("id", "lang", "kind", "expected", "got", "forced", "forced_reason")}
                for r in rows
                if r["got"] != r["expected"]
            ],
            "evidence_gaps": [
                {
                    "id": r["id"],
                    "lang": r["lang"],
                    "got": r["got"],
                    "missing": sorted(set(r["expected_codes"]) - set(r["codes"])),
                    "codes": r["codes"],
                }
                for r in rows
                if not set(r["expected_codes"]) <= set(r["codes"])
            ],
            "explanation_cost_per_check_usd": sum(r["costs"].get("explanation", 0) for r in rows) / len(rows),
        }  # fmt: skip
    OUT.write_text(
        json.dumps(
            {"generated": datetime.now(UTC).date().isoformat(), "n_test": n_test, "configs": configs},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUT.name}: {list(configs)}")


if __name__ == "__main__":
    main()
