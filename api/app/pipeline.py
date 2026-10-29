"""One pipeline for every channel (web app, WhatsApp):

input -> extraction (image or text) -> milestone check -> mandatory checks -> agent -> verdict.

Each step is published as a masked event on the CheckState, so callers can stream progress.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.agent.loop import AgentSession, resume, start
from app.agent.protocol import AgentInput
from app.api.events import extracted_event, public_event, verdict_view
from app.api.store import CheckState, SpendMeter
from app.extract import ExtractionFailed, TranscriptionFailed, extract, transcribe
from app.models.base import LLMClient

log = logging.getLogger("billsaathi.pipeline")


@dataclass
class Clients:
    extract: LLMClient
    agent: LLMClient
    judge: LLMClient


@dataclass
class CheckInput:
    language: str
    text: str | None = None
    image: bytes | None = None
    image_mime: str | None = None


def run_check(state: CheckState, check: CheckInput, clients: Clients, spend: SpendMeter) -> None:
    try:
        _run(state, check, clients, spend)
    except Exception as e:  # never leave a check hanging; a crash is "could not verify"
        log.exception("check failed check_id=%s", state.check_id)
        _fail(state, f"internal error: {type(e).__name__}")


def answer(state: CheckState, reply: str, spend: SpendMeter) -> None:
    session = state.session
    try:
        before = session.metrics.cost_usd
        state.status = "verifying"
        if reply:
            state.secrets.append(reply)
        resume(session, reply)
        spend.add(session.metrics.cost_usd - before)
        _after_agent(state, session)
    except Exception as e:
        log.exception("answer failed check_id=%s", state.check_id)
        _fail(state, f"internal error: {type(e).__name__}")


def _run(state: CheckState, check: CheckInput, clients: Clients, spend: SpendMeter) -> None:
    state.emit({"type": "received", "input": state.input_kind, "language": check.language})
    state.status = "extracting"
    t0 = time.perf_counter()
    visible_text, unreadable, transcription_cost = None, False, 0.0
    try:
        if check.image is not None:
            # Fields and a verbatim transcription in parallel; time = the slower of the two.
            with ThreadPoolExecutor(max_workers=2) as pool:
                fields = pool.submit(
                    extract, clients.extract, image=check.image, image_mime=check.image_mime
                )
                text = pool.submit(
                    transcribe, clients.extract, image=check.image, image_mime=check.image_mime
                )
                ext = fields.result()
                try:
                    transcription = text.result()
                    visible_text, transcription_cost = (
                        transcription.text,
                        transcription.usage.cost_usd,
                    )
                except TranscriptionFailed:
                    unreadable = True  # recorded as a failed milestone check: no SAFE
        else:
            ext = extract(clients.extract, text=check.text)
    except ExtractionFailed as e:
        _fail(state, f"could not read the input: {e}")
        return
    state.extraction_ms = (time.perf_counter() - t0) * 1000
    state.extraction_cost = ext.usage.cost_usd + transcription_cost
    spend.add(state.extraction_cost)
    if ext.output.consumer_number.value:
        state.secrets.append(ext.output.consumer_number.value)
    event = extracted_event(ext.output, ext.attempts, state.extraction_ms)
    if check.image is not None:
        event["transcription"] = "failed" if unreadable else "ok"
    state.emit(event)

    state.status = "verifying"
    agent_input = AgentInput(
        extraction=ext.output,
        raw_text=check.text,
        visible_text=visible_text,
        text_unreadable=unreadable,
        language=check.language,
    )

    def on_entry(entry):
        event = public_event(entry, state.secrets)
        if event is not None:
            state.emit(event)

    session = start(
        clients.agent, agent_input, judge=clients.judge, run_id=state.check_id, listener=on_entry
    )
    state.session = session
    spend.add(session.metrics.cost_usd)
    _after_agent(state, session)


def _after_agent(state: CheckState, session: AgentSession) -> None:
    if session.status == "needs_user_input":
        state.status = "needs_user_input"
        return
    state.status = "done"
    state.finished = time.monotonic()
    state.emit({"type": "complete", **summary(state)})


def _fail(state: CheckState, why: str) -> None:
    state.error = why
    state.status = "failed"
    state.finished = time.monotonic()
    verdict = {
        "verdict": "CAUTION",
        "reasons": [
            {"text": "Could not verify this payment request. Do not pay yet.", "evidence_ids": []}
        ],
        "forced": True,
        "forced_reason": why,
    }
    state.emit(verdict_view(verdict, state.secrets))
    state.emit({"type": "complete", **summary(state)})


def summary(state: CheckState) -> dict:
    session = state.session
    agent_cost = session.metrics.cost_usd if session else 0.0
    agent_ms = session.metrics.latency_ms if session else 0.0
    end = state.finished or time.monotonic()
    return {
        "status": state.status,
        "timings_ms": {
            "extraction": round(state.extraction_ms),
            "agent": round(agent_ms),
            "total": round((end - state.created) * 1000),
        },
        "cost_usd": {
            "extraction": round(state.extraction_cost, 5),
            "agent": round(agent_cost, 5),
            "total": round(state.extraction_cost + agent_cost, 5),
        },
        "agent": session.metrics.model_dump() if session else None,
    }
