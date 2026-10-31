"""WhatsApp conversations: one message in -> the same check pipeline as the web app -> replies.

State is in memory, like the checks API (CLAUDE.md §11 known limit, max 1 replica):
seen message ids, per-sender rate limit, language preference and the one open question.
Senders are known only by a keyed hash of their number; raw numbers are never logged.
"""

import hashlib
import hmac
import logging
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app import pipeline
from app.api.checks import MAX_IMAGE_BYTES, MAX_TEXT_CHARS, sniff_image
from app.api.store import CheckState, CheckStore, RateLimiter, SpendMeter
from app.config import Settings
from app.whatsapp import texts
from app.whatsapp.graph import GraphClient, GraphError
from app.whatsapp.texts import Lang

log = logging.getLogger("billsaathi.whatsapp")

SEEN_TTL_SECONDS = 24 * 3600  # Meta retries for up to a day
SEEN_MAX = 20_000


def sender_hash(phone: str, key: str) -> str:
    return hmac.new(key.encode(), f"wa-sender:{phone}".encode(), hashlib.sha256).hexdigest()[:16]


@dataclass
class Pending:
    state: CheckState
    lang: Lang
    phone: str
    asked: float


class WhatsAppService:
    def __init__(
        self,
        settings: Settings,
        graph: GraphClient,
        store: CheckStore,
        spend: SpendMeter,
        clients: Callable[[], pipeline.Clients],
        schedule: Callable[[float, Callable[[], None]], Any] | None = None,
    ):
        self.settings = settings
        self.graph = graph
        self.store = store
        self.spend = spend
        self.clients = clients
        self.schedule = schedule or _timer
        self.limiter = RateLimiter(settings.whatsapp_rate_limit_per_minute)
        self._key = settings.whatsapp_app_secret.get_secret_value()
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lang: dict[str, Lang] = {}
        self._pending: dict[str, Pending] = {}
        self._lock = threading.Lock()

    # --- webhook side (fast, in the request) ---

    def first_time(self, message_id: str) -> bool:
        """True once per message id: Meta may deliver the same message more than once."""
        now = time.monotonic()
        with self._lock:
            while self._seen and (
                len(self._seen) > SEEN_MAX
                or now - next(iter(self._seen.values())) > SEEN_TTL_SECONDS
            ):
                self._seen.popitem(last=False)
            if message_id in self._seen:
                return False
            self._seen[message_id] = now
            return True

    # --- background side ---

    def handle(self, message: dict[str, Any]) -> None:
        phone = message.get("from", "")
        sid = sender_hash(phone, self._key)
        try:
            self._handle(message, phone, sid)
        except Exception:
            log.exception("whatsapp message failed sender=%s", sid)

    def _handle(self, message: dict[str, Any], phone: str, sid: str) -> None:
        kind = message.get("type")
        msg_id = message.get("id")
        text = (message.get("text") or {}).get("body", "").strip() if kind == "text" else None
        log.info("whatsapp message sender=%s type=%s", sid, kind)

        if text is not None and (switch := texts.switch_command(text)):
            with self._lock:
                self._lang[sid] = switch
            self._send(phone, texts.t(switch, "switched"))
            return

        pending = self._take_pending(sid)
        if pending is not None:
            if kind == "text" and time.monotonic() - pending.asked <= self._question_ttl:
                reply = "" if text.lower() in texts.SKIP_WORDS else text[:200]
                self._send(phone, texts.t(pending.lang, "checking"), msg_id)
                pipeline.answer(pending.state, reply, self.spend)
                self._finish(phone, sid, pending.state, pending.lang)
                return
            self._close(phone, pending, expired=True)  # then treat this message as a new one

        lang = self._language(
            sid, text if kind == "text" else (message.get("image") or {}).get("caption")
        )
        if kind not in ("text", "image") or (kind == "text" and not text):
            self._send(phone, texts.t(lang, "unsupported"), msg_id)
            return
        if not self.limiter.allow(sid):
            self._send(phone, texts.t(lang, "rate_limited"), msg_id)
            return
        if self.spend.exceeded():
            self._send(phone, texts.t(lang, "busy"), msg_id)
            return

        check = pipeline.CheckInput(language=lang)
        if kind == "image":
            try:
                data, _ = self.graph.download_media(message["image"]["id"], MAX_IMAGE_BYTES)
            except (GraphError, KeyError) as e:
                log.warning("whatsapp media failed sender=%s: %s", sid, e)
                self._send(phone, texts.t(lang, "bad_image"), msg_id)
                return
            mime = sniff_image(data)  # the bytes decide, not the declared type
            if mime is None:
                self._send(phone, texts.t(lang, "bad_image"), msg_id)
                return
            check.image, check.image_mime = data, mime
        else:
            check.text = text[:MAX_TEXT_CHARS]

        self._send(phone, texts.t(lang, "checking"), msg_id)
        state = CheckState(check_id=uuid.uuid4().hex, language=lang, input_kind=kind)
        self.store.add(state)
        pipeline.run_check(state, check, self.clients(), self.spend)
        self._finish(phone, sid, state, lang)

    def _finish(self, phone: str, sid: str, state: CheckState, lang: Lang) -> None:
        if state.status == "needs_user_input":
            question = next(e for e in reversed(state.events) if e["type"] == "question")
            with self._lock:
                self._pending[sid] = Pending(state, lang, phone, time.monotonic())
            self.schedule(self._question_ttl, lambda: self.expire(sid, state.check_id))
            self._send(phone, texts.question_message(question["question"], lang))
            return
        log.info("whatsapp verdict sender=%s check=%s status=%s", sid, state.check_id, state.status)
        self._send(phone, texts.verdict_message(state.events, lang, self.settings.web_app_url))

    def expire(self, sid: str, check_id: str) -> None:
        """Called when the question timer runs out: close the check as CAUTION if still open."""
        with self._lock:
            pending = self._pending.get(sid)
            if pending is None or pending.state.check_id != check_id:
                return
            del self._pending[sid]
        self._close(pending.phone, pending, expired=True)

    def _close(self, phone: str, pending: Pending, *, expired: bool) -> None:
        pipeline.answer(pending.state, "", self.spend)  # no model call: forced CAUTION or floor
        self._send(
            phone,
            texts.verdict_message(
                pending.state.events, pending.lang, self.settings.web_app_url, expired=expired
            ),
        )

    # --- helpers ---

    @property
    def _question_ttl(self) -> float:
        return self.settings.whatsapp_question_ttl_seconds

    def _take_pending(self, sid: str) -> Pending | None:
        with self._lock:
            return self._pending.pop(sid, None)

    def _language(self, sid: str, text: str | None) -> Lang:
        with self._lock:
            chosen = self._lang.get(sid)
        return chosen or texts.detect_language(text) or "en"

    def _send(self, phone: str, body: str, reply_to: str | None = None) -> None:
        try:
            self.graph.send_text(phone, body, reply_to)
        except Exception as e:  # a failed reply must not crash the worker
            log.warning("whatsapp send failed: %s", e)


def _timer(delay: float, fn: Callable[[], None]) -> threading.Timer:
    timer = threading.Timer(delay, fn)
    timer.daemon = True
    timer.start()
    return timer
