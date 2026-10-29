"""In-memory state for the checks API: checks, per-IP rate limit, daily spend.

Known limit (CLAUDE.md §11): everything lives in one process's memory, so it is lost on
restart and not shared between replicas (the app runs with max 1 replica).
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.agent.loop import AgentSession


@dataclass
class CheckState:
    check_id: str
    language: str
    input_kind: str
    created: float = field(default_factory=time.monotonic)
    touched: float = field(default_factory=time.monotonic)
    status: str = "queued"  # queued, extracting, verifying, needs_user_input, done, failed
    events: list[dict[str, Any]] = field(default_factory=list)
    session: AgentSession | None = None
    secrets: list[str] = field(default_factory=list)  # values to mask in every outgoing text
    extraction_ms: float = 0.0
    extraction_cost: float = 0.0
    finished: float | None = None
    error: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, event: dict[str, Any]) -> None:
        with self.lock:
            self.events.append(
                {
                    "seq": len(self.events),
                    "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                    **event,
                }
            )
            self.touched = time.monotonic()

    def events_after(self, seq: int) -> list[dict[str, Any]]:
        with self.lock:
            return self.events[seq + 1 :]


class CheckStore:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._checks: dict[str, CheckState] = {}
        self._lock = threading.Lock()

    def add(self, state: CheckState) -> None:
        with self._lock:
            self._expire()
            self._checks[state.check_id] = state

    def get(self, check_id: str) -> CheckState | None:
        with self._lock:
            self._expire()
            return self._checks.get(check_id)

    def _expire(self) -> None:
        now = time.monotonic()
        for cid in [c for c, s in self._checks.items() if now - s.touched > self.ttl]:
            del self._checks[cid]


class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False
            hits.append(now)
            return True


class SpendMeter:
    """Model spend per UTC day. New checks are refused once the cap is reached."""

    def __init__(self, cap_usd: float):
        self.cap = cap_usd
        self._day = ""
        self._spent = 0.0
        self._lock = threading.Lock()

    def _roll(self) -> None:
        today = datetime.now(UTC).date().isoformat()
        if today != self._day:
            self._day, self._spent = today, 0.0

    def add(self, usd: float) -> None:
        with self._lock:
            self._roll()
            self._spent += usd

    @property
    def spent(self) -> float:
        with self._lock:
            self._roll()
            return self._spent

    def exceeded(self) -> bool:
        return self.spent >= self.cap
