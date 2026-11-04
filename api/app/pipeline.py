"""One pipeline for every channel (web app, WhatsApp):

input -> extraction (image or text) -> milestone check -> mandatory checks -> agent -> verdict.

Each step is published as a masked event on the CheckState, so callers can stream progress.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.agent.loop import AgentConfig, AgentSession, resume, start
from app.agent.protocol import AgentInput
from app.api.events import extracted_event, public_event, verdict_view
from app.api.store import CheckState, SpendMeter
from app.explain import explain
from app.extract import ExtractionFailed, TranscriptionFailed, extract, transcribe
from app.models.base import LLMClient, LLMError
from app.pii import scrub
from app.vision import Segmenter, isolate
from app.voice import SpeechClient

log = logging.getLogger("billsaathi.pipeline")


@dataclass
class Clients:
    extract: LLMClient
    agent: LLMClient
    judge: LLMClient
    explain: LLMClient | None = None  # None: template explanations, no model call
    speech: SpeechClient | None = None
    sam: Segmenter | None = None  # None: no isolation step (Privacy Mode stays off Meta's API)
    model: str = "muse-spark-1.3"
    effort: str = "low"
    judge_effort: str = "low"  # every published result used low; minimal gained nothing on dev
    privacy: bool = False  # open-weight model; no Meta API call anywhere on this path


@dataclass
class CheckInput:
    language: str
    text: str | None = None
    image: bytes | None = None
    image_mime: str | None = None
    audio: bytes | None = None  # 16 kHz mono 16-bit WAV; transcribed, then checked as text


def run_check(state: CheckState, check: CheckInput, clients: Clients, spend: SpendMeter) -> None:
    state.clients = clients
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
        _after_agent(state, session, spend)
    except Exception as e:
        log.exception("answer failed check_id=%s", state.check_id)
        _fail(state, f"internal error: {type(e).__name__}")


def _run(state: CheckState, check: CheckInput, clients: Clients, spend: SpendMeter) -> None:
    state.emit(
        {
            "type": "received",
            "input": state.input_kind,
            "language": check.language,
            "privacy": clients.privacy,
            "model": clients.model,
        }
    )
    if check.audio is not None and not _transcribe_audio(state, check, clients, spend):
        return
    state.status = "extracting"
    t0 = time.perf_counter()
    visible_text, unreadable, transcription_cost = None, False, 0.0
    try:
        if check.image is not None:
            # A verbatim transcription of the ORIGINAL image runs from the start, so a link
            # outside the crop still reaches the milestone check. Fields read the crop.
            with ThreadPoolExecutor(max_workers=2) as pool:
                text = pool.submit(
                    transcribe,
                    clients.extract,
                    image=check.image,
                    image_mime=check.image_mime,
                    model=clients.model,
                )
                image, image_mime = _isolate(state, check, clients, spend)
                fields = pool.submit(
                    extract,
                    clients.extract,
                    image=image,
                    image_mime=image_mime,
                    model=clients.model,
                    effort=clients.effort,
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
            ext = extract(
                clients.extract, text=check.text, model=clients.model, effort=clients.effort
            )
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
            if event["type"] == "early" and event["signal"] == "scam_signals":
                _start_early_explanation(state)

    session = start(
        clients.agent,
        agent_input,
        judge=clients.judge,
        config=AgentConfig(
            model=clients.model,
            judge_model=clients.model,
            effort=clients.effort,
            judge_effort=clients.judge_effort,
        ),
        run_id=state.check_id,
        listener=on_entry,
    )
    state.session = session
    spend.add(session.metrics.cost_usd)
    _after_agent(state, session, spend)


def _isolate(
    state: CheckState, check: CheckInput, clients: Clients, spend: SpendMeter
) -> tuple[bytes, str]:
    """The image for field extraction: the bill cropped by SAM, or the original."""
    if clients.sam is None:
        return check.image, check.image_mime
    result = isolate(clients.sam, check.image, check.image_mime)
    state.isolation_ms, state.isolation_cost = result.latency_ms, result.cost_usd
    spend.add(result.cost_usd)
    state.emit(
        {
            "type": "isolated",
            "model": "sam-3.1",
            "box": result.box.model_dump() if result.box else None,
            "cropped": result.cropped,
            "latency_ms": round(result.latency_ms),
        }
    )
    return result.image, result.mime


def _transcribe_audio(
    state: CheckState, check: CheckInput, clients: Clients, spend: SpendMeter
) -> bool:
    state.status = "transcribing"
    if clients.speech is None:
        _fail(state, "voice input is not available")
        return False
    try:
        heard = clients.speech.transcribe_audio(check.audio, check.language)
    except LLMError as e:
        _fail(state, f"could not hear the recording: {e}")
        return False
    state.speech_cost, state.speech_ms = heard.cost_usd, heard.latency_ms
    spend.add(heard.cost_usd)
    if not heard.text:
        _fail(state, "nothing could be heard in the recording")
        return False
    check.text = heard.text
    state.emit(
        {
            "type": "transcribed",
            "text": scrub(heard.text, state.secrets),
            "latency_ms": round(heard.latency_ms),
        }
    )
    return True


def _after_agent(state: CheckState, session: AgentSession, spend: SpendMeter) -> None:
    if session.status == "needs_user_input":
        state.status = "needs_user_input"
        return
    state.finished = time.monotonic()  # the verdict is out; the explanation follows it
    _explain(state, spend)
    _complete(state, "done")


# Findings that say nothing is wrong: left out of an early scam explanation.
_NOT_RISK = {"BILLER_VERIFIED", "DESTINATION_OFFICIAL", "AMOUNT_MATCHES_BILLER", "AMOUNT_WITHIN_HISTORY"}  # fmt: skip


def _start_early_explanation(state: CheckState) -> None:
    """The deterministic floor is already SCAM, and nothing can lower it, so the explanation can
    start while the agent and judge work. It is written from the code's findings only, never from
    the agent's unjudged reasons, and it is shown only after the verdict."""
    clients = state.clients
    if clients is None or clients.explain is None:
        return
    events = state.events_after(-1)
    reasons = [
        {"text": ev["summary"], "evidence_ids": [ev["evidence_id"]]}
        for e in events
        if e["type"] == "check"
        for ev in e.get("evidence", [])
        if ev["code"] not in _NOT_RISK
    ]
    assumed = {"type": "verdict", "verdict": "SCAM", "reasons": reasons, "forced": False}
    pool = ThreadPoolExecutor(max_workers=1)
    state.early_explanation = pool.submit(
        explain, clients.explain, clients.model, [*events, assumed], state.language
    )
    pool.shutdown(wait=False)


def _explain(state: CheckState, spend: SpendMeter | None) -> None:
    clients = state.clients
    events = state.events_after(-1)
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    early = state.early_explanation
    result = None
    if early is not None:
        try:
            result = early.result()
        except Exception:  # the normal path below still gives an explanation or a template
            log.exception("early explanation failed check_id=%s", state.check_id)
    if result is None or verdict["verdict"] != "SCAM" or verdict.get("forced"):
        spent = result.usage.cost_usd if result else 0.0
        result = explain(
            clients.explain if clients else None,
            clients.model if clients else "",
            events,
            state.language,
        )
        result.usage.cost_usd += spent
    state.explanation_ms, state.explanation_cost = result.latency_ms, result.usage.cost_usd
    if spend is not None:
        spend.add(result.usage.cost_usd)
    state.emit(
        {
            "type": "explanation",
            "language": state.language,
            "text": scrub(result.text, state.secrets),
            "source": result.source,
            "latency_ms": round(result.latency_ms),
        }
    )


def _complete(state: CheckState, status: str) -> None:
    # The stream closes on the status, so the last event goes out before it changes.
    state.emit({"type": "complete", **summary(state), "status": status})
    state.status = status


def _fail(state: CheckState, why: str) -> None:
    state.error = why
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
    state.clients = None  # template only: the model may be the thing that failed
    _explain(state, None)
    _complete(state, "failed")


def summary(state: CheckState) -> dict:
    session = state.session
    agent_cost = session.metrics.cost_usd if session else 0.0
    agent_ms = session.metrics.latency_ms if session else 0.0
    end = state.finished or time.monotonic()
    return {
        "status": state.status,
        "timings_ms": {
            "speech": round(state.speech_ms),
            "isolation": round(state.isolation_ms),
            "extraction": round(state.extraction_ms),
            "agent": round(agent_ms),
            "explanation": round(state.explanation_ms),
            "total": round((end - state.created) * 1000),
        },
        "cost_usd": {
            "speech": round(state.speech_cost, 5),
            "isolation": round(state.isolation_cost, 5),
            "extraction": round(state.extraction_cost, 5),
            "agent": round(agent_cost, 5),
            "explanation": round(state.explanation_cost, 5),
            "total": round(
                state.speech_cost
                + state.isolation_cost
                + state.extraction_cost
                + agent_cost
                + state.explanation_cost,
                5,
            ),
        },
        "agent": session.metrics.model_dump() if session else None,
    }
