"""In-memory async event bus keyed by scan_id.

Each scan keeps a full history of published events and supports multiple
concurrent or reconnecting subscribers. A new subscriber receives all
past events first, then live ones — so navigating away and back never
causes missed stages or a false FAILED state.

Single-process only — for multi-worker deployments swap this for Redis
pub/sub or NATS.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)

GRACE_SECONDS = 60  # keep history this long after a scan finishes


@dataclass(frozen=True)
class Event:
    name: str
    data: dict[str, Any]


_DONE = object()  # sentinel signalling end-of-stream


@dataclass
class _ScanState:
    history: list[Event] = field(default_factory=list)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    done: bool = False


class EventBus:
    def __init__(self) -> None:
        self._scans: dict[str, _ScanState] = {}
        self._lock = asyncio.Lock()

    def _state(self, scan_id: str) -> _ScanState:
        if scan_id not in self._scans:
            self._scans[scan_id] = _ScanState()
        return self._scans[scan_id]

    async def publish(self, scan_id: str, name: str, data: dict[str, Any]) -> None:
        async with self._lock:
            state = self._state(scan_id)
            event = Event(name=name, data=data)
            state.history.append(event)
            for q in state.subscribers:
                await q.put(event)

    async def close(self, scan_id: str) -> None:
        """Signal end-of-stream. History is kept for GRACE_SECONDS so
        reconnecting clients can still replay all events."""
        async with self._lock:
            state = self._state(scan_id)
            state.done = True
            for q in state.subscribers:
                await q.put(_DONE)
        asyncio.create_task(self._cleanup_after(scan_id))

    async def _cleanup_after(self, scan_id: str) -> None:
        await asyncio.sleep(GRACE_SECONDS)
        async with self._lock:
            self._scans.pop(scan_id, None)
        logger.debug("EventBus: removed history for scan %s", scan_id)

    async def subscribe(self, scan_id: str) -> AsyncIterator[Event]:
        """Yield all past events then live events until the scan finishes.

        Safe to call multiple times or after a disconnect — history is
        replayed from the beginning each time.
        """
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            state = self._state(scan_id)
            snapshot = list(state.history)
            already_done = state.done
            if not already_done:
                state.subscribers.add(queue)

        # Replay history so the reconnecting client catches up instantly.
        for event in snapshot:
            yield event

        if already_done:
            # All events are already in the snapshot; nothing left to wait for.
            return

        try:
            while True:
                item = await queue.get()
                if item is _DONE:
                    return
                yield item
        finally:
            async with self._lock:
                state = self._scans.get(scan_id)
                if state is not None:
                    state.subscribers.discard(queue)

    def has_active(self, scan_id: str) -> bool:
        """True while a scan is in-flight or within the post-completion grace period."""
        return scan_id in self._scans


def get_bus() -> EventBus:
    """Single-process singleton accessor."""
    global _BUS
    if _BUS is None:
        _BUS = EventBus()
    return _BUS


_BUS: Optional[EventBus] = None
