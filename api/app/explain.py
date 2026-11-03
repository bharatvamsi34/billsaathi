"""Explain a finished verdict in the user's language.

The model only rewords what the checks found; it can never change the verdict, which is shown
separately by code. Its text is checked by code before anyone sees it: every number, link and
UPI ID must already be in the evidence, and Telugu and Hindi must really be in that script.
Anything else (or a model failure, or a forced verdict) falls back to a template built from
the evidence labels, with no model call. Helplines come from app/facts.py, added by the channel.
"""

import json
import logging
import re
import time
import unicodedata
from typing import Any

from pydantic import BaseModel

from app.labels import CODE_LABELS, HEADLINES, Lang
from app.models.base import LLMClient, LLMError, Message, Usage

log = logging.getLogger("billsaathi.explain")

MAX_ATTEMPTS = 2
MAX_CHARS = 700
_NAMES = {"en": "simple English", "te": "simple Telugu (తెలుగు)", "hi": "simple Hindi (हिंदी)"}
_SCRIPTS = {"te": re.compile(r"[ఀ-౿]"), "hi": re.compile(r"[ऀ-ॿ]")}
_VERDICT_WORDS = {
    "SAFE": {"en": "safe", "te": "సురక్షితం", "hi": "सुरक्षित"},
    "CAUTION": {"en": "caution", "te": "జాగ్రత్త", "hi": "सावधान"},
    "SCAM": {"en": "scam", "te": "మోసం", "hi": "धोखा"},
}
_LINK = re.compile(r"(?:https?://)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?:/\S*)?")
_UPI = re.compile(r"[A-Za-z0-9._-]+@[A-Za-z0-9]+")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

SYSTEM = """\
You explain the result of a bill-payment safety check to an ordinary person in India who may be \
new to digital payments.
Write 2 to 4 short, plain sentences in {language}. Say what was found and what the person should \
do next. Common English words such as UPI, KYC, OTP and link may stay in English. Call the \
verdict by its own word in that language: {verdict_word}. Keep every UPI ID and link exactly as \
it is in the evidence.
Rules:
- Use ONLY the verdict and evidence given below. Never add a number, amount, date, name, link, \
UPI ID or phone number that is not in the evidence.
- Never write a helpline number or website; the app adds those itself.
- Never contradict or soften the verdict. SCAM means do not pay. CAUTION means do not pay yet. \
SAFE means the checks passed and the person still decides and confirms before any payment.
- Never say that a payment was made.
Reply with only the explanation text."""


class Explanation(BaseModel):
    text: str
    source: str  # "model" or "template"
    latency_ms: float = 0.0
    usage: Usage = Usage()


def _digits(text: str) -> str:
    """Telugu and Devanagari digits as ASCII, so they cannot slip past the number check."""
    return "".join(
        str(unicodedata.digit(ch)) if ch.isdigit() and not ch.isascii() else ch for ch in text
    )


def _normal_number(token: str) -> str:
    value = token.replace(",", "")
    return value.split(".")[0] if re.fullmatch(r"\d+\.0+", value) else value


def _cited(events: list[dict[str, Any]], verdict: dict[str, Any]) -> list[dict[str, Any]]:
    """The verdict's reasons with the evidence each one cites (all already masked)."""
    index = {
        ev["evidence_id"]: ev
        for e in events
        if e["type"] == "check"
        for ev in e.get("evidence", [])
    }
    return [
        {
            "reason": r["text"],
            "evidence": [
                {"code": index[i]["code"], "summary": index[i]["summary"]}
                for i in r["evidence_ids"]
                if i in index
            ],
        }
        for r in verdict["reasons"]
    ]


def problem(text: str, evidence_text: str, lang: Lang) -> str | None:
    """Why this explanation may not be shown; None if it passes."""
    if not text.strip():
        return "empty"
    if len(text) > MAX_CHARS:
        return "too long"
    source = _digits(evidence_text)
    if lang in _SCRIPTS and len(_SCRIPTS[lang].findall(text)) < len(text) * 0.4:
        return "not in the user's script"
    wording = _digits(text)
    for pattern, what in ((_UPI, "UPI ID"), (_LINK, "link")):
        for token in pattern.findall(wording):
            if token.rstrip(".,").lower() not in source.lower():
                return f"{what} not in the evidence"
        wording = pattern.sub(" ", wording)
    allowed = {_normal_number(n) for n in _NUMBER.findall(source)}
    for token in _NUMBER.findall(wording):
        if _normal_number(token.rstrip(",")) not in allowed:
            return "number not in the evidence"
    return None


def template(events: list[dict[str, Any]], verdict: dict[str, Any], lang: Lang) -> Explanation:
    """No model: the headline plus the labels of the cited evidence."""
    codes = dict.fromkeys(
        ev["code"] for reason in _cited(events, verdict) for ev in reason["evidence"]
    )
    labels = [CODE_LABELS[c][lang] for c in codes if c in CODE_LABELS]
    parts = [HEADLINES[verdict["verdict"]][lang], *labels]
    return Explanation(text=" · ".join(parts), source="template")


def explain(
    client: LLMClient | None, model: str, events: list[dict[str, Any]], lang: Lang
) -> Explanation:
    verdict = next(e for e in reversed(events) if e["type"] == "verdict")
    if client is None or verdict.get("forced"):
        return template(events, verdict, lang)
    cited = _cited(events, verdict)
    evidence_text = json.dumps(cited, ensure_ascii=False)
    messages = [
        Message(
            role="user",
            text=json.dumps({"verdict": verdict["verdict"], "findings": cited}, ensure_ascii=False),
        )
    ]
    usage, t0 = Usage(), time.perf_counter()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = client.respond(
                system=SYSTEM.format(
                    language=_NAMES[lang], verdict_word=_VERDICT_WORDS[verdict["verdict"]][lang]
                ),
                messages=messages,
                model=model,
                effort="low",
                max_output_tokens=4096,
            )
        except LLMError as e:
            log.warning("explanation failed: %s", e)
            break
        for field in ("input_tokens", "output_tokens", "reasoning_tokens", "cost_usd"):
            setattr(usage, field, getattr(usage, field) + getattr(resp.usage, field))
        text = resp.text.strip()
        why = problem(text, evidence_text, lang)
        if why is None:
            return Explanation(
                text=text,
                source="model",
                latency_ms=(time.perf_counter() - t0) * 1000,
                usage=usage,
            )
        log.warning("explanation rejected attempt=%d lang=%s: %s", attempt, lang, why)
    fallback = template(events, verdict, lang)
    fallback.latency_ms, fallback.usage = (time.perf_counter() - t0) * 1000, usage
    return fallback
