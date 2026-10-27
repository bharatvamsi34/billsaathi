"""Model spike runner. Run from api/:

  .venv\\Scripts\\python -m spike.run_spike --models wonder --cases smoke
  .venv\\Scripts\\python -m spike.run_spike --models wonder,spark,open --cases T1,T2 --runs 3
  .venv\\Scripts\\python -m spike.run_spike --report

Every call appends one row to results/spike_<date>.jsonl and updates the cost ledger.
The run stops before any call that could take total spend past --budget.
Files uploaded to Meta /v1/files are tracked in results/uploaded_files.json and deleted
at the end of every run (or with --cleanup).
"""

import argparse
import json
import statistics
import wave
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.schemas import ExtractionOutput, Label, Verdict
from spike import cases
from spike.cost import SAM_PER_IMAGE, TRANSCRIBE_PER_SECOND, BudgetExceeded, CostMeter
from spike.transports import (
    CallResult,
    Prompt,
    baseten_chat,
    chat_messages,
    delete_file,
    meta_httpx,
    meta_sam,
    meta_sdk,
    meta_transcribe,
    responses_input,
    shape,
    upload_file,
)

RESULTS = Path(__file__).parent / "results"
LEDGER = RESULTS / "cost_ledger.json"
UPLOADS = RESULTS / "uploaded_files.json"
MAX_OUT = 2048

# (label id, concept prompt); "QR code" on the bill photo is a negative control (no QR exists)
SAM_JOBS = [
    ("bill_photo", "bill"),
    ("bill_photo", "document"),
    ("bill_photo", "QR code"),
    ("sms_scam_en_img", "link"),
]

MODELS = {
    "wonder": ("meta", lambda s: s.meta_model_wonder or "muse-wonder-1.0"),
    "spark": ("meta", lambda s: s.meta_model_spark or "muse-spark-1.3"),
    "spark11": ("meta", lambda s: "muse-spark-1.1"),
    "open": ("baseten", lambda s: s.baseten_model),
}


def _strip_none(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if v is not None}


class Runner:
    def __init__(self, budget: float, runs: int, transports: list[str], efforts: list[str]):
        self.settings = get_settings()
        self.meter = CostMeter(LEDGER, budget)
        self.runs = runs
        self.transports = transports
        self.efforts = efforts
        self.labels = cases.load_labels()
        RESULTS.mkdir(exist_ok=True)
        self.rows_path = RESULTS / f"spike_{date.today().isoformat()}.jsonl"
        self.file_ids: dict[Path, str] = {}
        self.sam_done = False
        self.asr_done = False

    # --- plumbing ---

    def file_id(self, path: Path) -> str:
        """Upload once per run; every id goes in the ledger first so cleanup can find it."""
        if path not in self.file_ids:
            fid = upload_file(self.settings, path)
            uploads = json.loads(UPLOADS.read_text(encoding="utf-8")) if UPLOADS.exists() else {}
            uploads[fid] = path.name
            UPLOADS.write_text(json.dumps(uploads, indent=2), encoding="utf-8")
            self.file_ids[path] = fid
        return self.file_ids[path]

    def model_id(self, key: str) -> str:
        model = MODELS[key][1](self.settings)
        if not model:
            raise SystemExit(f"model ID for '{key}' is not set in api/.env")
        if "contributor" in model.lower():
            raise SystemExit(f"refusing '{model}': Contributor variants train on inputs")
        return model

    def transports_for(self, key: str) -> list[str]:
        return ["chat-stream"] if MODELS[key][0] == "baseten" else self.transports

    def call(
        self,
        key: str,
        transport: str,
        items: list[dict[str, Any]],
        est_in: int,
        tools: list[dict[str, Any]] | None = None,
        effort: str = "medium",
    ) -> tuple[CallResult, dict[str, Any]]:
        model = self.model_id(key)
        self.meter.check(model, est_in, MAX_OUT)
        if MODELS[key][0] == "meta":
            fn = meta_httpx if transport.startswith("httpx") else meta_sdk
            res = fn(
                self.settings,
                model,
                items,
                stream=transport.endswith("stream"),
                tools=tools,
                max_output_tokens=MAX_OUT,
                effort=effort,
            )
        else:
            res = baseten_chat(self.settings, items, tools=tools, max_tokens=MAX_OUT)
        reported = res.input_tokens is not None and res.output_tokens is not None
        tin = res.input_tokens if reported else est_in
        tout = res.output_tokens if reported else (len(res.text) + len(res.reasoning)) // 3
        cost = self.meter.record(model, tin, tout)
        return res, self.cost_info(cost, self.meter.price(model).assumed, reported)

    def cost_info(self, cost: float, assumed: bool, reported: bool) -> dict[str, Any]:
        return {
            "cost_usd": round(cost, 6),
            "cost_assumed_price": assumed,
            "usage_reported": reported,
            "spent_usd": round(self.meter.spent_usd, 6),
        }

    def prompt_items(self, key: str, prompt: Prompt) -> tuple[list[dict[str, Any]], int]:
        has_image = prompt.image is not None or prompt.image_file_id is not None
        est = (len(prompt.system) + len(prompt.user)) // 3 + (1500 if has_image else 0)
        est += 1000 if prompt.audio is not None else 0
        items = responses_input(prompt) if MODELS[key][0] == "meta" else chat_messages(prompt)
        return items, est

    def record(
        self,
        case: str,
        input_id: str,
        key: str,
        run: int,
        res: CallResult,
        cost: dict,
        scores: dict,
        extra: dict | None = None,
    ) -> None:
        row = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "case": case,
            "input_id": input_id,
            "model_key": key,
            "model": res.model,
            "provider": res.provider,
            "transport": res.transport,
            "run": run,
            "ok": res.ok,
            "http_status": res.http_status,
            "error": res.error,
            "ttft_ms": round(res.ttft_ms, 1) if res.ttft_ms is not None else None,
            "total_ms": round(res.total_ms, 1),
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "reasoning_tokens": res.reasoning_tokens,
            **cost,
            "scores": scores,
            "text": res.text[:2000],
            "reasoning": res.reasoning[:1000],
            **(extra or {}),
        }
        with self.rows_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        ttft = f"{res.ttft_ms:.0f}ms" if res.ttft_ms is not None else "-"
        print(
            f"[{case}] {key}/{res.transport} {input_id} run{run}: ok={res.ok} "
            f"total={res.total_ms:.0f}ms ttft={ttft} tok={res.input_tokens}/{res.output_tokens} "
            f"cost=${cost['cost_usd']:.4f}{' (assumed price)' if cost['cost_assumed_price'] else ''} "
            f"spent=${cost['spent_usd']:.4f} scores={json.dumps(scores, default=str)}"
            + (f" error={res.error}" if res.error else "")
        )

    # --- cases ---

    def verdict_case(
        self, case: str, key: str, label: Label, transports: list[str], effort: str = "medium"
    ):
        prompt = Prompt(cases.SYSTEM_VERDICT, label.input.text or "")
        items, est = self.prompt_items(key, prompt)
        for transport in transports:
            for run in range(1, self.runs + 1):
                res, cost = self.call(key, transport, items, est, effort=effort)
                parsed, err = (
                    cases.parse_model(res.text, cases.VerdictOutput)
                    if res.ok
                    else (None, "call failed")
                )
                scores = cases.score_verdict(parsed, label) if parsed else {"parse_error": err}
                self.record(case, label.id, key, run, res, cost, scores, {"effort": effort})

    def smoke(self, key: str) -> None:
        self.verdict_case("smoke", key, self.labels["sms_scam_en_txt"], self.transports_for(key))

    def t1(self, key: str) -> None:
        efforts = self.efforts if key == "spark" else ["medium"]
        for label in self.labels.values():
            if label.input.kind == "text":
                for effort in efforts:
                    self.verdict_case("T1", key, label, self.transports_for(key)[:1], effort)

    def t2(self, key: str) -> None:
        # Meta: try an uploaded file_id first, then an inline data URL. Baseten: data URL only.
        modes = ["file_id", "data_url"] if MODELS[key][0] == "meta" else ["data_url"]
        for label in self.labels.values():
            if label.input.kind != "image":
                continue
            for mode in modes:
                self.t2_one(key, label, mode)

    def t2_one(self, key: str, label: Label, mode: str) -> None:
        path = cases.INPUTS / label.input.path
        prompt = Prompt(cases.SYSTEM_EXTRACT, "Extract the fields from this image.", path)
        if mode == "file_id":
            try:
                prompt.image_file_id = self.file_id(path)
            except (RuntimeError, ValueError, KeyError) as e:
                print(f"[T2] {key} {label.id} file_id: upload failed: {e}")
                return
        items, est = self.prompt_items(key, prompt)
        for run in range(1, self.runs + 1):
            res, cost = self.call(key, self.transports_for(key)[0], items, est)
            parsed, err = (
                cases.parse_model(res.text, ExtractionOutput) if res.ok else (None, "call failed")
            )
            if parsed is None:
                scores = {"parse_error": err}
            else:
                scores = cases.score_fields(parsed.to_fields(), label.expected.extracted)
                conf = {name: getattr(parsed, name).confidence for name in scores["field_correct"]}
                right = [conf[n] for n, ok in scores["field_correct"].items() if ok]
                wrong = [conf[n] for n, ok in scores["field_correct"].items() if not ok]
                scores["mean_conf_correct"] = round(statistics.fmean(right), 3) if right else None
                scores["mean_conf_wrong"] = round(statistics.fmean(wrong), 3) if wrong else None
            self.record("T2", label.id, key, run, res, cost, scores, {"image_mode": mode})

    def t3(self, key: str) -> None:
        label = self.labels["sms_scam_en_txt"]
        meta = MODELS[key][0] == "meta"
        prompt = Prompt(cases.SYSTEM_TOOLS, label.input.text or "")
        items, est = self.prompt_items(key, prompt)
        tools = cases.TOOLS_RESPONSES if meta else cases.TOOLS_CHAT
        transport = self.transports_for(key)[0]
        problems: list[str] = []
        calls_made = 0
        steps: list[CallResult] = []
        cost: dict[str, Any] = {}
        for step in range(3):
            res, cost = self.call(key, transport, items, est, tools=tools)
            steps.append(res)
            if not res.ok:
                problems.append(f"step{step}: {res.error}")
                break
            if not res.tool_calls:
                break
            outputs = []
            for tc in res.tool_calls:
                calls_made += 1
                err = cases.check_tool_args(tc["name"], tc["arguments"])
                if err:
                    problems.append(f"{tc['name']}: {err}")
                out = (
                    {"error": err}
                    if err
                    else cases.run_fake_tool(tc["name"], json.loads(tc["arguments"]))
                )
                outputs.append((tc["call_id"], json.dumps(out)))
            if meta:
                items = (
                    items
                    + [_strip_none(i) for i in res.output_items]
                    + [
                        {"type": "function_call_output", "call_id": cid, "output": out}
                        for cid, out in outputs
                    ]
                )
            else:
                items = (
                    items
                    + res.output_items
                    + [
                        {"role": "tool", "tool_call_id": cid, "content": out}
                        for cid, out in outputs
                    ]
                )
            est = len(json.dumps(items)) // 3
        final = steps[-1]
        parsed, err = (
            cases.parse_model(final.text, cases.VerdictOutput)
            if final.ok and not final.tool_calls
            else (None, "no final answer")
        )
        if calls_made == 0:
            mentions = any(spec["name"] in final.text for spec in cases.TOOL_SPECS)
            problems.append(
                "tool syntax written as text, not native" if mentions else "model ignored tools"
            )
        if parsed is None:
            problems.append(f"final answer: {err}")
        elif parsed.verdict != Verdict.SCAM:
            problems.append(f"final verdict {parsed.verdict} (expected SCAM)")
        scores = {
            "tool_calling": "PASS" if not problems else "FAIL",
            "tool_calls": calls_made,
            "steps": len(steps),
            "problems": problems,
        }
        summary = CallResult(
            final.provider,
            final.transport,
            final.model,
            ok=final.ok,
            text=final.text,
            reasoning=final.reasoning,
            http_status=final.http_status,
            error=final.error,
            total_ms=sum(s.total_ms for s in steps),
            ttft_ms=steps[0].ttft_ms,
            input_tokens=sum(s.input_tokens or 0 for s in steps),
            output_tokens=sum(s.output_tokens or 0 for s in steps),
        )
        self.record(
            "T3",
            label.id,
            key,
            1,
            summary,
            cost,
            scores,
            {"tool_call_trace": [tc for s in steps for tc in s.tool_calls]},
        )

    def t4(self, key: str) -> None:
        for lang in cases.EXPLAIN_LANGS:
            system, user = cases.explain_prompt(lang)
            items, est = self.prompt_items(key, Prompt(system, user))
            res, cost = self.call(key, self.transports_for(key)[0], items, est)
            scores = {
                "lang": lang,
                "script_ratio": round(cases.script_ratio(res.text, lang), 3),
                "chars": len(res.text),
                "human_rating_1_5": None,
            }
            self.record("T4", f"explain_{lang}", key, 1, res, cost, scores)

    def t7(self, key: str) -> None:
        if MODELS[key][0] != "meta":
            return
        self.verdict_case(
            "T7", key, self.labels["sms_scam_en_txt"], ["httpx-stream", "sdk-stream", "sdk"]
        )

    def t5(self, key: str) -> None:
        """SAM 3.1 concept segmentation. Independent of --models, so it runs once per invocation."""
        if self.sam_done:
            return
        self.sam_done = True
        model = self.settings.meta_model_sam or "sam-3.1"
        for label_id, concept in SAM_JOBS:
            label = self.labels[label_id]
            try:
                fid = self.file_id(cases.INPUTS / label.input.path)
            except (RuntimeError, ValueError, KeyError) as e:
                print(f"[T5] {label_id} upload failed: {e}")
                continue
            self.meter.check_flat(SAM_PER_IMAGE)
            res = meta_sam(self.settings, model, fid, concept)
            cost = self.meter.record_flat(SAM_PER_IMAGE)  # priced per image, not per token
            cost_info = self.cost_info(cost, False, res.input_tokens is not None)
            scores = {
                "concept": concept,
                "n_events": len(res.events),
                "event_types": sorted({e.get("type", "?") for e in res.events}),
                "output_item_types": sorted({i.get("type", "?") for i in res.output_items}),
            }
            extra = {
                # Unknown output format: keep a shortened copy so IoU scoring can be written next.
                "format_first_events": shape(res.events[:3]),
                "format_last_events": shape(res.events[-2:]),
                "format_output_items": shape(res.output_items),
                "expected_regions": [r.model_dump() for r in label.expected.regions],
            }
            self.record("T5", label_id, "sam", 1, res, cost_info, scores, extra)

    @staticmethod
    def asr_scores(label: Label, text: str) -> dict[str, Any]:
        ref = label.expected.transcript or ""
        scores = {"cer": round(cases.cer(ref.lower(), text.lower().strip()), 3)}
        if label.expected.extracted.language == "en":
            scores["wer"] = round(cases.wer(ref, text), 3)
        return scores

    def t6(self, key: str) -> None:
        """Speech to text: Muse Voice Transcribe once per invocation; Spark Open via audio input."""
        voices = [lbl for lbl in self.labels.values() if lbl.input.kind == "audio"]
        if MODELS[key][0] == "baseten":
            for label in voices:
                prompt = Prompt(
                    "Transcribe the audio exactly, in the language and script spoken. "
                    "Reply with only the transcript.",
                    "Transcribe this audio.",
                    audio=cases.INPUTS / label.input.path,
                )
                items, est = self.prompt_items(key, prompt)
                res, cost = self.call(key, "chat-stream", items, est)
                self.record("T6", label.id, key, 1, res, cost, self.asr_scores(label, res.text))
            return
        if self.asr_done:
            return
        self.asr_done = True
        model = self.settings.meta_model_transcribe or "muse-voice-transcribe-1.0"
        for label in voices:
            wav = cases.INPUTS / label.input.path
            with wave.open(str(wav)) as w:
                seconds = w.getnframes() / w.getframerate()
            for bias in (None, ["Hindi", "English"]):
                self.meter.check_flat(seconds * TRANSCRIBE_PER_SECOND)
                res, duration_ms = meta_transcribe(self.settings, model, wav, language_bias=bias)
                billed_s = duration_ms / 1000 if duration_ms else seconds
                cost = self.meter.record_flat(billed_s * TRANSCRIBE_PER_SECOND)
                scores = self.asr_scores(label, res.text) | {
                    "language_bias": ",".join(bias) if bias else "none",
                    "audio_ms": duration_ms,
                }
                self.record(
                    "T6",
                    label.id,
                    "asr",
                    1,
                    res,
                    self.cost_info(cost, False, True),
                    scores,
                    {"format_response": res.events},
                )

    def cleanup(self) -> None:
        """Delete every file this or an earlier run uploaded to Meta."""
        if not UPLOADS.exists():
            return
        uploads: dict[str, str] = json.loads(UPLOADS.read_text(encoding="utf-8"))
        for fid, name in list(uploads.items()):
            status, body = delete_file(self.settings, fid)
            if status in (200, 202, 204, 404):
                uploads.pop(fid)
                print(f"[cleanup] {name} ({fid}): deleted (HTTP {status})")
            else:
                print(f"[cleanup] {name} ({fid}): NOT deleted — HTTP {status}: {body}")
        UPLOADS.write_text(json.dumps(uploads, indent=2), encoding="utf-8")
        if uploads:
            print(f"[cleanup] {len(uploads)} file(s) remain on Meta's servers; see {UPLOADS}")


CASES = {
    "smoke": Runner.smoke,
    "T1": Runner.t1,
    "T2": Runner.t2,
    "T3": Runner.t3,
    "T4": Runner.t4,
    "T5": Runner.t5,
    "T6": Runner.t6,
    "T7": Runner.t7,
}


def report() -> None:
    """Summarise every results/*.jsonl row into results/spike_<date>.md."""
    rows = [
        json.loads(line)
        for p in sorted(RESULTS.glob("spike_*.jsonl"))
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        # effort (T1/T7), image mode (T2) or concept prompt (T5)
        variant = (
            r.get("image_mode")
            or r["scores"].get("concept")
            or (f"bias={r['scores']['language_bias']}" if "language_bias" in r["scores"] else None)
            or r.get("effort")
            or "-"
        )
        groups.setdefault((r["case"], r["model_key"], r["transport"], variant), []).append(r)
    out = [
        "# Model spike results",
        "",
        f"Rows: {len(rows)} · Estimated spend: ${max((r['spent_usd'] for r in rows), default=0):.4f}"
        + (" (assumed prices)" if any(r["cost_assumed_price"] for r in rows) else ""),
        "",
        "| case | model | transport | variant | n | ok | median ms | max ms | median TTFT ms | quality |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (case, key, transport, effort), rs in sorted(groups.items()):
        ok = [r for r in rs if r["ok"]]
        totals = [r["total_ms"] for r in ok]
        ttfts = [r["ttft_ms"] for r in ok if r["ttft_ms"] is not None]
        quality = []
        for metric in (
            "verdict_correct",
            "scam_flag_correct",
            "field_accuracy",
            "script_ratio",
            "wer",
            "cer",
        ):
            vals = [r["scores"][metric] for r in rs if metric in r["scores"]]
            if vals:
                quality.append(f"{metric}={statistics.fmean(vals):.2f}")
        quality += [r["scores"]["tool_calling"] for r in rs if "tool_calling" in r["scores"]]
        parse_errors = sum("parse_error" in r["scores"] for r in rs)
        if parse_errors:
            quality.append(f"parse_errors={parse_errors}")
        out.append(
            f"| {case} | {key} | {transport} | {effort} | {len(rs)} | {len(ok)} | "
            f"{statistics.median(totals):.0f} | {max(totals):.0f} | "
            f"{(statistics.median(ttfts) if ttfts else float('nan')):.0f} | {'; '.join(quality)} |"
            if totals
            else f"| {case} | {key} | {transport} | {effort} | {len(rs)} | 0 | - | - | - | all failed |"
        )
    path = RESULTS / f"spike_{date.today().isoformat()}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--models", default="wonder", help="comma list of: " + ",".join(MODELS))
    ap.add_argument("--cases", default="smoke", help="comma list of: " + ",".join(CASES))
    ap.add_argument(
        "--transports",
        default="httpx-stream,sdk-stream",
        help="Meta transports: httpx-stream, httpx, sdk-stream, sdk",
    )
    ap.add_argument(
        "--efforts", default="low,medium", help="reasoning efforts compared for Spark in T1"
    )
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--budget", type=float, default=5.0, help="USD cap for all spike runs combined")
    ap.add_argument("--report", action="store_true", help="only write the markdown summary")
    ap.add_argument("--cleanup", action="store_true", help="only delete files uploaded to Meta")
    args = ap.parse_args()
    if args.report:
        report()
        return
    runner = Runner(args.budget, args.runs, args.transports.split(","), args.efforts.split(","))
    try:
        if not args.cleanup:
            for key in args.models.split(","):
                for case in args.cases.split(","):
                    CASES[case](runner, key)
    except BudgetExceeded as e:
        print(f"STOPPED — budget guard: {e}")
    finally:
        runner.cleanup()
    print(f"estimated spend so far: ${runner.meter.spent_usd:.4f} of ${args.budget:.2f}")


if __name__ == "__main__":
    main()
